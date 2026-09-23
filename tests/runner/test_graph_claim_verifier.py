"""
Tests for runner.graph_claim_verifier — independent claim→node re-verification
(milestone 2, ticket 8.2 / DOD-1b).

Two layers, mirroring the other graph tests:

* **Contract on controlled fixture repos** — a happy path where every published
  claim traces to a bound ``proposal_section`` node, plus one red-capable fixture
  per finding kind (untraceable claim, status drift, dropped node, cross-section
  trace, malformed claim, missing ledger) and the fail-closed preconditions
  (no tier5 binding, missing/empty sections dir, unparseable section, bad
  config/vault).  The status-map direction is pinned both ways (a correct
  ``source_grounded``→``confirmed`` / ``unconfirmed``→``unresolved`` passes; a
  drifted one is caught).
* **Real-vault oracle** — the committed sections and vault.  The DOD-1b
  confirmation: every published Part B claim traces to its node, 1:1.

Two structural guards keep the tool honest: it must not import the compiler
(independence — it audits the committed artifacts, it does not re-run
``compile_part_b``), and as a ``runner/graph_*.py`` module it must carry no
project noun (auto-covered by the agnosticism lint, D15).
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path, PurePosixPath

import pytest
import yaml

from runner.graph_claim_verifier import (
    KIND_DROPPED_NODE,
    KIND_MALFORMED_CLAIM,
    KIND_MISSING_CLAIM_BLOCK,
    KIND_SECTION_MISMATCH,
    KIND_STATUS_MISMATCH,
    KIND_UNTRACEABLE_CLAIM,
    GraphClaimVerificationError,
    format_report,
    main,
    verify_claim_traceability,
)
from runner.graph_config import GraphConfigError
from runner.vault_reader import VaultReadError

# ---------------------------------------------------------------------------
# Helpers — a controlled fixture repo (vault + published sections + config)
# ---------------------------------------------------------------------------

_CONFIG = """\
project_id: fixture-claims
vault_path: nodes
bindings:
  - match:
      node_type: proposal_section
    tier: tier5
    artifact_path: docs/tier5_deliverables/proposal_sections
"""

_SECTIONS_REL = "docs/tier5_deliverables/proposal_sections"


def _write_node(path: Path, fm: dict, body: str = "body") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fm_text = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True)
    path.write_text(f"---\n{fm_text}---\n\n{body}", encoding="utf-8")
    return path


def _mk(node_id: str, slug: str, evidence: str = "synthesis") -> dict:
    """A ``proposal_section`` node front-matter dict."""
    return {
        "id": node_id,
        "title": f"{node_id} title",
        "node_type": "proposal_section",
        "evidence_strength": evidence,
        "section_slug": slug,
    }


def _claim(claim_id: str, status: str = "inferred") -> dict:
    return {"claim_id": claim_id, "claim_summary": f"{claim_id} summary", "status": status}


def _repo(tmp_path: Path, nodes: list[dict], sections: dict[str, list[dict]]) -> Path:
    """Build a repo: a config, a vault of *nodes*, and published *sections*.

    ``sections`` maps a slug → its published ``claim_statuses`` list; each becomes
    ``{slug}_section.json`` under the config's tier5 artifact dir.  The vault and
    the sections dir always exist even when empty (so a test can add a malformed
    file itself).
    """
    root = tmp_path / "repo"
    root.mkdir(parents=True, exist_ok=True)
    (root / "graph.config.yaml").write_text(_CONFIG, encoding="utf-8")
    (root / "nodes").mkdir(parents=True, exist_ok=True)
    for fm in nodes:
        _write_node(root / "nodes" / "sections" / f"{fm['id']}.md", fm)
    sd = root / _SECTIONS_REL
    sd.mkdir(parents=True, exist_ok=True)
    for slug, claims in sections.items():
        obj = {
            "schema_id": f"orch.tier5.{slug}_section.v1",
            "run_id": "fixture-claims",
            "criterion": slug.capitalize(),
            "validation_status": {"overall_status": "inferred", "claim_statuses": claims},
        }
        (sd / f"{slug}_section.json").write_text(json.dumps(obj, indent=2), encoding="utf-8")
    return root


def _cfg(root: Path) -> Path:
    return root / "graph.config.yaml"


def _only(result, kind: str):
    matches = [f for f in result.findings if f.kind == kind]
    assert len(matches) == 1, (
        f"expected exactly one {kind!r}, got {[f.kind for f in result.findings]}"
    )
    return matches[0]


# ---------------------------------------------------------------------------
# Happy path — every claim traces
# ---------------------------------------------------------------------------


def test_happy_path_all_claims_trace(tmp_path):
    root = _repo(
        tmp_path,
        nodes=[_mk("PS-x-1", "excellence"), _mk("PS-x-1.1", "excellence")],
        sections={"excellence": [_claim("PS-x-1"), _claim("PS-x-1.1")]},
    )
    result = verify_claim_traceability(_cfg(root), root)
    assert result.ok
    assert result.claims_checked == 2
    assert result.vault_section_node_count == 2
    assert result.sections_checked == (f"{_SECTIONS_REL}/excellence_section.json",)


def test_result_is_deterministic(tmp_path):
    root = _repo(
        tmp_path,
        nodes=[_mk("PS-x-1", "excellence")],
        sections={"excellence": [_claim("PS-x-1"), _claim("GHOST")]},
    )
    a = verify_claim_traceability(_cfg(root), root)
    b = verify_claim_traceability(_cfg(root), root)
    assert a == b


# ---------------------------------------------------------------------------
# Status-map fidelity — both directions
# ---------------------------------------------------------------------------


def test_status_mismatch_flagged(tmp_path):
    # node is synthesis -> 'inferred'; published claims 'confirmed' -> drift.
    root = _repo(
        tmp_path,
        nodes=[_mk("PS-x-1", "excellence", evidence="synthesis")],
        sections={"excellence": [_claim("PS-x-1", status="confirmed")]},
    )
    result = verify_claim_traceability(_cfg(root), root)
    assert not result.ok
    finding = _only(result, KIND_STATUS_MISMATCH)
    assert finding.claim_id == "PS-x-1"
    assert "confirmed" in finding.detail and "inferred" in finding.detail


def test_source_grounded_maps_confirmed_ok(tmp_path):
    root = _repo(
        tmp_path,
        nodes=[_mk("PS-x-1", "excellence", evidence="source_grounded")],
        sections={"excellence": [_claim("PS-x-1", status="confirmed")]},
    )
    assert verify_claim_traceability(_cfg(root), root).ok


def test_unconfirmed_maps_unresolved_ok(tmp_path):
    # unconfirmed -> 'unresolved' (never confirmed): the anti-fabrication direction.
    root = _repo(
        tmp_path,
        nodes=[_mk("PS-x-1", "excellence", evidence="unconfirmed")],
        sections={"excellence": [_claim("PS-x-1", status="unresolved")]},
    )
    assert verify_claim_traceability(_cfg(root), root).ok


# ---------------------------------------------------------------------------
# Traceability + completeness findings
# ---------------------------------------------------------------------------


def test_untraceable_claim_flagged(tmp_path):
    root = _repo(
        tmp_path,
        nodes=[_mk("PS-x-1", "excellence")],
        sections={"excellence": [_claim("PS-x-1"), _claim("PS-x-GHOST")]},
    )
    result = verify_claim_traceability(_cfg(root), root)
    assert not result.ok
    finding = _only(result, KIND_UNTRACEABLE_CLAIM)
    assert finding.claim_id == "PS-x-GHOST"
    # The genuine claim still traces and is counted.
    assert result.claims_checked == 2


def test_dropped_node_flagged(tmp_path):
    # Two bound nodes for 'excellence', but the published ledger lists only one.
    root = _repo(
        tmp_path,
        nodes=[_mk("PS-x-1", "excellence"), _mk("PS-x-1.1", "excellence")],
        sections={"excellence": [_claim("PS-x-1")]},
    )
    result = verify_claim_traceability(_cfg(root), root)
    assert not result.ok
    finding = _only(result, KIND_DROPPED_NODE)
    assert finding.claim_id == "PS-x-1.1"


def test_section_mismatch_flagged(tmp_path):
    # A claim in excellence_section.json traces to an *impact* node.
    root = _repo(
        tmp_path,
        nodes=[_mk("PS-x-1", "excellence"), _mk("PS-i-2", "impact")],
        sections={"excellence": [_claim("PS-x-1"), _claim("PS-i-2")]},
    )
    result = verify_claim_traceability(_cfg(root), root)
    assert not result.ok
    finding = _only(result, KIND_SECTION_MISMATCH)
    assert finding.claim_id == "PS-i-2"
    assert "impact" in finding.detail


def test_malformed_claim_missing_id(tmp_path):
    root = _repo(
        tmp_path,
        nodes=[_mk("PS-x-1", "excellence")],
        sections={"excellence": [_claim("PS-x-1"), {"claim_summary": "no id", "status": "inferred"}]},
    )
    result = verify_claim_traceability(_cfg(root), root)
    finding = _only(result, KIND_MALFORMED_CLAIM)
    assert finding.claim_id == ""


def test_malformed_claim_missing_status(tmp_path):
    root = _repo(
        tmp_path,
        nodes=[_mk("PS-x-1", "excellence")],
        sections={"excellence": [{"claim_id": "PS-x-1", "claim_summary": "x"}]},
    )
    result = verify_claim_traceability(_cfg(root), root)
    finding = _only(result, KIND_MALFORMED_CLAIM)
    assert finding.claim_id == "PS-x-1"


def test_missing_claim_block_flagged(tmp_path):
    root = _repo(tmp_path, nodes=[_mk("PS-x-1", "excellence")], sections={})
    sd = root / _SECTIONS_REL
    (sd / "excellence_section.json").write_text(
        json.dumps({"schema_id": "x", "criterion": "Excellence"}), encoding="utf-8"
    )
    result = verify_claim_traceability(_cfg(root), root)
    finding = _only(result, KIND_MISSING_CLAIM_BLOCK)
    assert finding.slug == "excellence"


# ---------------------------------------------------------------------------
# Fail-closed preconditions (the audit cannot run — never a vacuous pass)
# ---------------------------------------------------------------------------


def test_no_tier5_binding_fails_closed(tmp_path):
    root = tmp_path / "repo"
    (root / "nodes").mkdir(parents=True, exist_ok=True)
    (root / "graph.config.yaml").write_text(
        "project_id: x\n"
        "vault_path: nodes\n"
        "bindings:\n"
        "  - match:\n"
        "      folder: '11_objectives'\n"
        "      node_type: objective\n"
        "    tier: tier3\n"
        "    artifact_path: docs/a/objectives.json\n"
        "    collection_key: objectives\n",
        encoding="utf-8",
    )
    with pytest.raises(GraphClaimVerificationError, match="no tier5 binding"):
        verify_claim_traceability(_cfg(root), root)


def test_missing_sections_dir_fails_closed(tmp_path):
    root = _repo(
        tmp_path, nodes=[_mk("PS-x-1", "excellence")], sections={"excellence": [_claim("PS-x-1")]}
    )
    shutil.rmtree(root / "docs")
    with pytest.raises(GraphClaimVerificationError, match="directory not found"):
        verify_claim_traceability(_cfg(root), root)


def test_empty_sections_dir_fails_closed(tmp_path):
    root = _repo(tmp_path, nodes=[_mk("PS-x-1", "excellence")], sections={})
    with pytest.raises(GraphClaimVerificationError, match="refusing to vacuously pass"):
        verify_claim_traceability(_cfg(root), root)


def test_unparseable_section_fails_closed(tmp_path):
    root = _repo(tmp_path, nodes=[_mk("PS-x-1", "excellence")], sections={})
    (root / _SECTIONS_REL / "excellence_section.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(GraphClaimVerificationError, match="not readable JSON"):
        verify_claim_traceability(_cfg(root), root)


def test_bad_config_fails_closed(tmp_path):
    with pytest.raises(GraphConfigError):
        verify_claim_traceability(tmp_path / "nope.yaml", tmp_path)


def test_malformed_vault_fails_closed(tmp_path):
    root = _repo(
        tmp_path, nodes=[_mk("PS-x-1", "excellence")], sections={"excellence": [_claim("PS-x-1")]}
    )
    (root / "nodes" / "sections" / "Broken.md").write_text("no front matter", encoding="utf-8")
    with pytest.raises(VaultReadError, match=r"Broken\.md"):
        verify_claim_traceability(_cfg(root), root)


# ---------------------------------------------------------------------------
# Structural guards — independence from the compiler, and agnosticism
# ---------------------------------------------------------------------------


def test_verifier_does_not_import_the_compiler():
    # DOD-1b demands an *independent* check, not a re-run of compile_part_b: the
    # auditor must not reach for the compiler at all.  Checked at the AST level so
    # a docstring that *names* the compiler (to explain the independence) is not a
    # false hit — only a real import or reference to it is.
    import ast

    import runner.graph_claim_verifier as mod

    tree = ast.parse(Path(mod.__file__).read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
    assert not any("graph_compiler" in name for name in imported), imported
    referenced = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    assert "compile_part_b" not in referenced


def test_module_carries_no_project_noun(repo_root):
    from runner.agnosticism_lint import lint_generic_layer

    report = lint_generic_layer(repo_root)
    rel = "runner/graph_claim_verifier.py"
    assert rel in report.scanned_files, "new graph_* module must be covered by the lint"
    assert [v for v in report.violations if v.path == rel] == []


# ---------------------------------------------------------------------------
# Real-vault oracle — the DOD-1b confirmation
# ---------------------------------------------------------------------------


@pytest.fixture
def real_config(repo_root) -> Path:
    cfg = repo_root / "MSCA" / "graph.config.yaml"
    if not cfg.is_file():
        pytest.skip("reference graph.config.yaml not present")
    return cfg


def test_real_vault_every_claim_traces(real_config, repo_root):
    result = verify_claim_traceability(real_config, repo_root)
    assert result.ok, format_report(result)
    assert result.claims_checked == 12
    assert result.vault_section_node_count == 12
    names = {PurePosixPath(s).name for s in result.sections_checked}
    assert names == {
        "excellence_section.json",
        "impact_section.json",
        "implementation_section.json",
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def test_cli_ok_exit_0(tmp_path, capsys):
    root = _repo(
        tmp_path, nodes=[_mk("PS-x-1", "excellence")], sections={"excellence": [_claim("PS-x-1")]}
    )
    code = main(["--config", str(_cfg(root)), "--repo-root", str(root)])
    assert code == 0
    assert "OK" in capsys.readouterr().out


def test_cli_findings_exit_1(tmp_path, capsys):
    root = _repo(
        tmp_path,
        nodes=[_mk("PS-x-1", "excellence")],
        sections={"excellence": [_claim("PS-x-1"), _claim("GHOST")]},
    )
    code = main(["--config", str(_cfg(root)), "--repo-root", str(root)])
    assert code == 1
    assert KIND_UNTRACEABLE_CLAIM in capsys.readouterr().err


def test_cli_fail_closed_exit_2(tmp_path, capsys):
    code = main(["--config", str(tmp_path / "nope.yaml"), "--repo-root", str(tmp_path)])
    assert code == 2
    assert "FAIL-CLOSED" in capsys.readouterr().err


def test_cli_real_vault_exit_0(real_config, repo_root):
    code = main(["--config", str(real_config), "--repo-root", str(repo_root)])
    assert code == 0
