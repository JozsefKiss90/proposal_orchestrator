"""
Tests for runner.graph_determinism_check — the ``--from-graph`` determinism
re-check (milestone 2, ticket 8.3 / DOD-1c).

Two layers, mirroring the other graph tests:

* **Contract on controlled fixtures** — the pure comparison seam
  (``_strip_exclusions`` + ``compare_staging_trees``) proven red-capable on
  hand-written staging trees (byte-identical, compiled_at-only float, a real
  content divergence, a missing file, a non-JSON divergence), plus
  ``verify_compile_determinism`` end-to-end on a fixture vault (both the
  byte-identical Part B path and the compiled_at-normalised Tier-3 path) and its
  fail-closed preconditions.
* **Real-vault oracle** — the DOD-1c confirmation: the real MSCA vault compiled
  twice is byte-identical modulo ``compiled_at`` (3 sections byte-identical, 6
  Tier-3 artifacts float only ``compiled_at``, zero findings).

Two structural facts are pinned: the tool **must** depend on the compiler (its
honesty is running it twice, the inverse of the DOD-1b auditor's independence),
and as a ``runner/graph_*.py`` module it carries no project noun (auto-covered by
the agnosticism lint, D15).
"""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath

import pytest
import yaml

from runner.graph_config import GraphConfigError
from runner.graph_determinism_check import (
    KIND_BYTE_DIVERGENCE,
    KIND_MISSING_FILE,
    REPLAY_INVARIANT_EXCLUSIONS,
    DeterminismCheckError,
    _strip_exclusions,
    compare_staging_trees,
    format_report,
    main,
    verify_compile_determinism,
)

# ---------------------------------------------------------------------------
# Helpers — a controlled fixture repo (Tier-3 objective + Part B section)
# ---------------------------------------------------------------------------

# A config with BOTH a Tier-3 objectives binding (→ objectives.json, which carries
# _provenance.compiled_at) and the tier5 proposal_section binding (→ a section
# with no timestamp).  So verify exercises BOTH comparison paths: the Tier-3
# artifact floats compiled_at (normalised), the section is byte-identical.
_CONFIG = """\
project_id: fixture-determinism
vault_path: nodes
bindings:
  - match:
      node_type: proposal_section
    tier: tier5
    artifact_path: docs/tier5_deliverables/proposal_sections
  - match:
      folder: "11_objectives"
      node_type: objective
    tier: tier3
    artifact_path: docs/tier3_project_instantiation/architecture_inputs/objectives.json
    collection_key: objectives
"""

# A config that compiles to nothing (a source-only tier3 binding, no artifact) —
# for the vacuous-pass fail-closed precondition.
_EMPTY_CONFIG = """\
project_id: fixture-empty
vault_path: nodes
bindings:
  - match:
      folder: "90_notes"
    tier: tier3
"""

_SCHEMA_SPEC = {
    "artifacts": {
        "excellence_section": {
            "schema_id_value": "orch.tier5.excellence_section.v1",
            "fields": {
                "schema_id": {"required": True},
                "run_id": {"required": True},
                "criterion": {"required": True},
                "sub_sections": {"required": True},
                "validation_status": {"required": True},
                "traceability_footer": {"required": True},
            },
        }
    }
}


def _write_node(path: Path, fm: dict, body: str = "") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fm_text = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True)
    path.write_text(f"---\n{fm_text}---\n\n{body}", encoding="utf-8")
    return path


@pytest.fixture
def fixture_repo(tmp_path) -> Path:
    """A repo: config + schema spec + a 1-objective + 1-section vault."""
    root = tmp_path / "repo"
    (root / "graph.config.yaml").parent.mkdir(parents=True, exist_ok=True)
    (root / "graph.config.yaml").write_text(_CONFIG, encoding="utf-8")
    spec = root / ".claude/workflows/system_orchestration/artifact_schema_specification.yaml"
    spec.parent.mkdir(parents=True, exist_ok=True)
    spec.write_text(yaml.safe_dump(_SCHEMA_SPEC, sort_keys=False), encoding="utf-8")
    _write_node(
        root / "nodes" / "11_objectives" / "OBJ-1.md",
        {
            "id": "OBJ-1",
            "title": "First Objective",
            "node_type": "objective",
            "evidence_strength": "source_grounded",
            "measurable_target": "A calibrated model.",
        },
    )
    _write_node(
        root / "nodes" / "20_excellence" / "PS-1-1.md",
        {
            "id": "PS-EXC-11",
            "title": "PS-EXC-11 title",
            "node_type": "proposal_section",
            "evidence_strength": "source_grounded",
            "section_slug": "excellence",
            "criterion": "Excellence",
            "sub_section_id": "1.1",
            "source_refs": [
                {
                    "tier": 3,
                    "source_path": "docs/tier3_project_instantiation/architecture_inputs/objectives.json",
                }
            ],
        },
        "## 1.1 Objectives\n\nThe sub-section prose body.",
    )
    return root


def _cfg(root: Path) -> Path:
    return root / "graph.config.yaml"


def _write_staged(root: Path, rel: str, obj: dict) -> Path:
    """Write *obj* as pretty JSON at ``root/rel`` (creating parents)."""
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2), encoding="utf-8")
    return p


_STAGED_REL = "docs/tier3_project_instantiation/architecture_inputs/objectives.json"


def _staged_obj(compiled_at: str = "2026-07-16T00:00:00+00:00") -> dict:
    return {
        "_provenance": {
            "record_type": "tier3_graph_compile",
            "node_count": 1,
            "compiled_at": compiled_at,
        },
        "objectives": [{"id": "OBJ-1", "title": "First Objective"}],
    }


# ---------------------------------------------------------------------------
# _strip_exclusions — the normaliser (pure)
# ---------------------------------------------------------------------------


def test_strip_exclusions_removes_compiled_at():
    obj = _staged_obj("A")
    stripped = _strip_exclusions(obj)
    assert "compiled_at" not in stripped["_provenance"]
    # the rest is untouched
    assert stripped["objectives"] == obj["objectives"]
    assert stripped["_provenance"]["node_count"] == 1


def test_strip_exclusions_is_non_mutating():
    obj = _staged_obj("A")
    _strip_exclusions(obj)
    assert obj["_provenance"]["compiled_at"] == "A"  # original untouched


def test_strip_exclusions_no_provenance_is_noop():
    obj = {"objectives": [{"id": "OBJ-1"}]}
    assert _strip_exclusions(obj) == obj


def test_exclusion_path_is_compiled_at():
    # Guard the documented contract: the sole exclusion is _provenance.compiled_at.
    assert REPLAY_INVARIANT_EXCLUSIONS == (("_provenance", "compiled_at"),)


# ---------------------------------------------------------------------------
# compare_staging_trees — the comparison seam (red-capable)
# ---------------------------------------------------------------------------


def test_compare_byte_identical_trees_ok(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    _write_staged(a, _STAGED_REL, _staged_obj("SAME"))
    _write_staged(b, _STAGED_REL, _staged_obj("SAME"))
    result = compare_staging_trees(a, b)
    assert result.ok
    assert result.byte_identical_files == (_STAGED_REL,)
    assert result.timestamp_normalized_files == ()
    assert result.compared_files == (_STAGED_REL,)


def test_compare_compiled_at_only_is_normalized_not_a_finding(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    _write_staged(a, _STAGED_REL, _staged_obj("EARLY"))
    _write_staged(b, _STAGED_REL, _staged_obj("LATE"))
    result = compare_staging_trees(a, b)
    assert result.ok, [f.detail for f in result.findings]
    assert result.timestamp_normalized_files == (_STAGED_REL,)
    assert result.byte_identical_files == ()


def test_compare_real_content_divergence_is_a_finding(tmp_path):
    # A divergence in a NON-excluded field must be caught — the red-capable core.
    a, b = tmp_path / "a", tmp_path / "b"
    oa = _staged_obj("SAME")
    ob = _staged_obj("SAME")
    ob["objectives"][0]["title"] = "Mutated Objective"  # real content drift
    _write_staged(a, _STAGED_REL, oa)
    _write_staged(b, _STAGED_REL, ob)
    result = compare_staging_trees(a, b)
    assert not result.ok
    assert len(result.findings) == 1
    assert result.findings[0].kind == KIND_BYTE_DIVERGENCE
    assert result.findings[0].staged_file == _STAGED_REL
    assert "objectives" in result.findings[0].detail


def test_compare_provenance_non_timestamp_divergence_is_a_finding(tmp_path):
    # A _provenance field OTHER than compiled_at drifting is still a finding —
    # only compiled_at is excluded, not the whole block.
    a, b = tmp_path / "a", tmp_path / "b"
    oa = _staged_obj("SAME")
    ob = _staged_obj("SAME")
    ob["_provenance"]["node_count"] = 999
    _write_staged(a, _STAGED_REL, oa)
    _write_staged(b, _STAGED_REL, ob)
    result = compare_staging_trees(a, b)
    assert not result.ok
    assert result.findings[0].kind == KIND_BYTE_DIVERGENCE
    assert "_provenance" in result.findings[0].detail
    assert "node_count" in result.findings[0].detail


def test_compare_missing_file_is_a_finding(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    _write_staged(a, _STAGED_REL, _staged_obj("SAME"))
    b.mkdir(parents=True, exist_ok=True)  # b has no staged files
    result = compare_staging_trees(a, b)
    assert not result.ok
    assert result.findings[0].kind == KIND_MISSING_FILE
    assert result.findings[0].staged_file == _STAGED_REL


def test_compare_non_json_divergence_is_a_finding(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    (a / _STAGED_REL).parent.mkdir(parents=True, exist_ok=True)
    (b / _STAGED_REL).parent.mkdir(parents=True, exist_ok=True)
    (a / _STAGED_REL).write_text("not json {{{", encoding="utf-8")
    (b / _STAGED_REL).write_text("also not json }}}", encoding="utf-8")
    result = compare_staging_trees(a, b)
    assert not result.ok
    assert result.findings[0].kind == KIND_BYTE_DIVERGENCE


def test_compare_empty_trees_is_ok_but_empty(tmp_path):
    # compare is a pure utility; the vacuous-pass guard lives in verify, not here.
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir(parents=True, exist_ok=True)
    b.mkdir(parents=True, exist_ok=True)
    result = compare_staging_trees(a, b)
    assert result.ok
    assert result.compared_files == ()


def test_compare_key_reorder_is_a_finding(tmp_path):
    # Red-capable against plain dict-equality: two JSON files identical in content
    # but with reordered keys are NOT the same bytes, so the compiler would not be
    # deterministic -- the order-preserving canonical comparison must flag it
    # rather than mask it (dict == dict would wrongly say 'equal').
    a, b = tmp_path / "a", tmp_path / "b"
    (a / _STAGED_REL).parent.mkdir(parents=True, exist_ok=True)
    (b / _STAGED_REL).parent.mkdir(parents=True, exist_ok=True)
    (a / _STAGED_REL).write_text('{"a": 1, "b": 2}', encoding="utf-8")
    (b / _STAGED_REL).write_text('{"b": 2, "a": 1}', encoding="utf-8")
    result = compare_staging_trees(a, b)
    assert not result.ok, "key reorder must be flagged, not masked by dict-equality"
    assert result.findings[0].kind == KIND_BYTE_DIVERGENCE


def test_compare_numeric_type_drift_is_a_finding(tmp_path):
    # 1 vs 1.0 are dict-equal but not byte-equal; canonical serialisation flags it.
    a, b = tmp_path / "a", tmp_path / "b"
    (a / _STAGED_REL).parent.mkdir(parents=True, exist_ok=True)
    (b / _STAGED_REL).parent.mkdir(parents=True, exist_ok=True)
    (a / _STAGED_REL).write_text('{"x": 1}', encoding="utf-8")
    (b / _STAGED_REL).write_text('{"x": 1.0}', encoding="utf-8")
    result = compare_staging_trees(a, b)
    assert not result.ok
    assert result.findings[0].kind == KIND_BYTE_DIVERGENCE


def test_compare_globs_non_json_files(tmp_path):
    # A non-JSON staged artifact is globbed and compared, never silently skipped.
    a, b = tmp_path / "a", tmp_path / "b"
    (a / "docs/notes.md").parent.mkdir(parents=True, exist_ok=True)
    (b / "docs/notes.md").parent.mkdir(parents=True, exist_ok=True)
    (a / "docs/notes.md").write_text("same prose", encoding="utf-8")
    (b / "docs/notes.md").write_text("same prose", encoding="utf-8")
    result = compare_staging_trees(a, b)
    assert result.compared_files == ("docs/notes.md",)  # globbed, not skipped
    assert result.byte_identical_files == ("docs/notes.md",)
    assert result.ok


def test_compare_non_json_divergence_when_bytes_differ(tmp_path):
    # A non-JSON staged artifact that differs is a finding (cannot be normalised).
    a, b = tmp_path / "a", tmp_path / "b"
    (a / "docs/notes.md").parent.mkdir(parents=True, exist_ok=True)
    (b / "docs/notes.md").parent.mkdir(parents=True, exist_ok=True)
    (a / "docs/notes.md").write_text("prose A", encoding="utf-8")
    (b / "docs/notes.md").write_text("prose B", encoding="utf-8")
    result = compare_staging_trees(a, b)
    assert not result.ok
    assert result.findings[0].kind == KIND_BYTE_DIVERGENCE


# ---------------------------------------------------------------------------
# verify_compile_determinism — end-to-end on the fixture vault
# ---------------------------------------------------------------------------


def test_verify_fixture_is_deterministic(fixture_repo, tmp_path):
    result = verify_compile_determinism(
        _cfg(fixture_repo), fixture_repo,
        staging_root_a=tmp_path / "a", staging_root_b=tmp_path / "b",
    )
    assert result.ok, format_report(result)
    assert result.config_project_id == "fixture-determinism"
    assert result.run_id == "fixture-determinism"
    c = result.comparison
    # 2 files: the section is byte-identical; objectives.json floats compiled_at.
    assert result.staged_file_count == 2
    section_rel = "docs/tier5_deliverables/proposal_sections/excellence_section.json"
    assert section_rel in c.byte_identical_files
    assert _STAGED_REL in c.timestamp_normalized_files


def test_verify_writes_only_to_staging_roots_not_docs(fixture_repo, tmp_path):
    # Non-destructive: the bare compile_* functions write no repo report, so
    # neither diff_report.json nor part_b_report.json appear under the repo root.
    verify_compile_determinism(
        _cfg(fixture_repo), fixture_repo,
        staging_root_a=tmp_path / "a", staging_root_b=tmp_path / "b",
    )
    gc = fixture_repo / "docs/tier4_orchestration_state/graph_compile"
    assert not (gc / "diff_report.json").exists()
    assert not (gc / "part_b_report.json").exists()


def test_verify_cleans_up_default_tempdirs(fixture_repo, monkeypatch):
    # With no explicit staging roots, verify makes two tempdirs and removes them.
    import runner.graph_determinism_check as mod

    made: list[Path] = []
    real_mkdtemp = mod.tempfile.mkdtemp

    def _spy(*a, **k):
        p = real_mkdtemp(*a, **k)
        made.append(Path(p))
        return p

    monkeypatch.setattr(mod.tempfile, "mkdtemp", _spy)
    result = verify_compile_determinism(_cfg(fixture_repo), fixture_repo)
    assert result.ok
    assert len(made) == 2
    for d in made:
        assert not d.exists(), f"temp staging root {d} was not cleaned up"


def test_verify_same_staging_root_fails_closed(fixture_repo, tmp_path):
    shared = tmp_path / "shared"
    with pytest.raises(DeterminismCheckError, match="distinct"):
        verify_compile_determinism(
            _cfg(fixture_repo), fixture_repo,
            staging_root_a=shared, staging_root_b=shared,
        )


def test_verify_empty_compile_fails_closed(tmp_path):
    root = tmp_path / "repo"
    (root).mkdir(parents=True, exist_ok=True)
    (root / "graph.config.yaml").write_text(_EMPTY_CONFIG, encoding="utf-8")
    (root / "nodes").mkdir(parents=True, exist_ok=True)
    with pytest.raises(DeterminismCheckError, match="nothing to re-check"):
        verify_compile_determinism(
            _cfg(root), root, staging_root_a=tmp_path / "a", staging_root_b=tmp_path / "b"
        )


def test_verify_bad_config_propagates_config_error(tmp_path):
    with pytest.raises(GraphConfigError):
        verify_compile_determinism(
            tmp_path / "nope.yaml", tmp_path,
            staging_root_a=tmp_path / "a", staging_root_b=tmp_path / "b",
        )


# ---------------------------------------------------------------------------
# Structural guards — the tool DEPENDS on the compiler; carries no project noun
# ---------------------------------------------------------------------------


def test_tool_depends_on_the_compiler():
    # The inverse of the DOD-1b auditor's independence: this tool's honesty is
    # re-running the compiler, so it MUST import it.
    import ast

    import runner.graph_determinism_check as mod

    tree = ast.parse(Path(mod.__file__).read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
    assert any("graph_compiler" in name for name in imported), imported


def test_module_carries_no_project_noun(repo_root):
    from runner.agnosticism_lint import lint_generic_layer

    report = lint_generic_layer(repo_root)
    rel = "runner/graph_determinism_check.py"
    assert rel in report.scanned_files, "new graph_* module must be covered by the lint"
    assert [v for v in report.violations if v.path == rel] == []


# ---------------------------------------------------------------------------
# Real-vault oracle — the DOD-1c confirmation
# ---------------------------------------------------------------------------


@pytest.fixture
def real_config(repo_root) -> Path:
    cfg = repo_root / "MSCA" / "graph.config.yaml"
    if not cfg.is_file():
        pytest.skip("reference graph.config.yaml not present")
    return cfg


def test_real_vault_is_byte_identical_modulo_compiled_at(real_config, repo_root, tmp_path):
    result = verify_compile_determinism(
        real_config, repo_root,
        staging_root_a=tmp_path / "a", staging_root_b=tmp_path / "b",
    )
    assert result.ok, format_report(result)
    c = result.comparison
    # 9 staged artifacts: 3 Part B sections + 6 Tier-3 architecture_inputs.
    assert result.staged_file_count == 9
    section_names = {
        PurePosixPath(r).name for r in c.byte_identical_files
    }
    assert section_names == {
        "excellence_section.json",
        "impact_section.json",
        "implementation_section.json",
    }
    # The 6 Tier-3 architecture_inputs float only compiled_at.
    assert len(c.timestamp_normalized_files) == 6
    tier3_names = {PurePosixPath(r).name for r in c.timestamp_normalized_files}
    assert tier3_names == {
        "objectives.json",
        "outcomes.json",
        "impacts.json",
        "workpackage_seed.json",
        "milestones_seed.json",
        "risks.json",
    }
    assert c.findings == ()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def test_cli_ok_exit_0(fixture_repo, capsys):
    code = main(["--config", str(_cfg(fixture_repo)), "--repo-root", str(fixture_repo)])
    assert code == 0
    assert "OK" in capsys.readouterr().out


def test_cli_fail_closed_exit_2(tmp_path, capsys):
    code = main(["--config", str(tmp_path / "nope.yaml"), "--repo-root", str(tmp_path)])
    assert code == 2
    assert "FAIL-CLOSED" in capsys.readouterr().err


def test_cli_findings_exit_1(fixture_repo, monkeypatch, capsys):
    # Findings require nondeterminism the compiler will not produce; inject a
    # findings-bearing result to prove the CLI maps it to exit 1 on stderr.
    import runner.graph_determinism_check as mod

    finding = mod.DeterminismFinding(
        kind=KIND_BYTE_DIVERGENCE, staged_file="x.json", detail="x.json: injected"
    )
    fake = mod.DeterminismResult(
        config_project_id="fixture-determinism",
        run_id="fixture-determinism",
        comparison=mod.StagingComparison(
            compared_files=("x.json",),
            byte_identical_files=(),
            timestamp_normalized_files=(),
            findings=(finding,),
        ),
    )
    monkeypatch.setattr(mod, "verify_compile_determinism", lambda *a, **k: fake)
    code = main(["--config", str(_cfg(fixture_repo)), "--repo-root", str(fixture_repo)])
    assert code == 1
    err = capsys.readouterr().err
    assert KIND_BYTE_DIVERGENCE in err


def test_cli_real_vault_exit_0(real_config, repo_root):
    code = main(["--config", str(real_config), "--repo-root", str(repo_root)])
    assert code == 0
