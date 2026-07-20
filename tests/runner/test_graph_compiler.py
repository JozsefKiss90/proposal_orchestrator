"""
Tests for runner.graph_compiler — the graph→docs Tier 3 compiler (ticket 3).

Two layers:

* **Contract on a controlled fixture vault** — the extraction record shape,
  the Appendix-B computed status (never read), determinism/byte-stability,
  non-destructiveness, fail-closed on inconsistent bindings, and the diff report
  (converged vs residual).  This is the walking skeleton's substantive proof.
* **MSCA oracle** — compiling the *real* vault.  Ticket 8 authored the Tier-3
  binding nodes (folders 11-16), so the compile now **converges** against the
  ticket-14 hand-lift (record id-sets match, residual 0).  The hand-lift is
  never touched (non-destructive; the ticket-10 cutover chooses the source).

All fixture vaults are written to tmp_path; the MSCA oracle reads the real vault
and hand-lift but stages to tmp_path so the repo is never mutated.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from runner.graph_compiler import (
    APPENDIX_B_MAPPING,
    GraphCompileError,
    compile_and_diff,
    compile_tier3,
    diff_against_hand_lift,
    extract_record,
)
from runner.graph_config import GraphConfigError, load_graph_config
from runner.vault_reader import VaultReadError, read_vault

_FIXED_NOW = "2026-07-16T00:00:00+00:00"


# ---------------------------------------------------------------------------
# Helpers — a controlled fixture vault + config
# ---------------------------------------------------------------------------


def _write_node(path: Path, fm: dict, body: str = "") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fm_text = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True)
    path.write_text(f"---\n{fm_text}---\n\n{body}", encoding="utf-8")
    return path


def _obj_fm(node_id: str, evidence: str = "source_grounded", **overrides) -> dict:
    fm = {
        "id": node_id,
        "title": node_id.replace("-", " ").title(),
        "node_type": "objective",
        "evidence_strength": evidence,
    }
    fm.update(overrides)
    return fm


_FIXTURE_CONFIG = """\
project_id: fixture-instance
vault_path: nodes
bindings:
  - match:
      folder: "11_objectives"
      node_type: objective
    tier: tier3
    artifact_path: docs/tier3_project_instantiation/architecture_inputs/objectives.json
    collection_key: objectives
  - match:
      folder: "16_risks"
      node_type: risk
    tier: tier3
    artifact_path: docs/tier3_project_instantiation/architecture_inputs/risks.json
    collection_key: risks
  - match:
      node_type: proposal_section
    tier: tier5
    artifact_path: docs/tier5_deliverables/proposal_sections
"""


@pytest.fixture
def fixture_repo(tmp_path) -> Path:
    """A repo root holding a config + a 2-objective binding vault."""
    root = tmp_path / "repo"
    cfg_path = root / "graph.config.yaml"
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(_FIXTURE_CONFIG, encoding="utf-8")
    _write_node(
        root / "nodes" / "11_objectives" / "OBJ-1.md",
        _obj_fm(
            "OBJ-1",
            measurable_target="A calibrated model.",
            target_month=12,
            responsible_partner="FELLOW",
            source_vault_nodes=["METH-CORE-002"],
        ),
        "# OBJ-1\n\nProse body.",
    )
    _write_node(
        root / "nodes" / "11_objectives" / "OBJ-2.md",
        _obj_fm("OBJ-2", evidence="synthesis", target_month=24),
        "# OBJ-2\n\nSynthesis framing.",
    )
    return root


def _config_path(repo: Path) -> Path:
    return repo / "graph.config.yaml"


# ---------------------------------------------------------------------------
# extract_record — the extraction contract
# ---------------------------------------------------------------------------


def test_extract_record_passthrough_and_shape(tmp_path):
    root = tmp_path / "v"
    node = read_vault(
        _write_node(
            root / "OBJ-1.md",
            _obj_fm("OBJ-1", measurable_target="X", target_month=12),
            "body",
        ).parent
    ).by_id["OBJ-1"]
    rec = extract_record(node)
    # id/title first, then passthrough FM fields in order, then status/evidence.
    assert list(rec.keys()) == [
        "id",
        "title",
        "measurable_target",
        "target_month",
        "validation_status",
        "evidence_strength",
    ]
    assert rec["id"] == "OBJ-1"
    assert rec["measurable_target"] == "X"
    assert rec["target_month"] == 12


def test_extract_record_excludes_reserved_keys(tmp_path):
    root = tmp_path / "v"
    node = read_vault(
        _write_node(
            root / "OBJ-1.md",
            _obj_fm(
                "OBJ-1",
                aliases=["OBJ1"],
                tier="tier3",
                artifact_path="docs/x.json",
                sub_section_id="B1.1",
                phase=3,
            ),
        ).parent
    ).by_id["OBJ-1"]
    rec = extract_record(node)
    for reserved in ("node_type", "aliases", "tier", "artifact_path", "sub_section_id", "phase"):
        assert reserved not in rec


def test_extract_record_computes_status_never_reads_injected(tmp_path):
    # A node that tries to inject validation_status: Confirmed while being only
    # synthesis must still compute Inferred (anti-fabrication).
    root = tmp_path / "v"
    node = read_vault(
        _write_node(
            root / "OBJ-1.md",
            _obj_fm("OBJ-1", evidence="synthesis", validation_status="Confirmed"),
        ).parent
    ).by_id["OBJ-1"]
    rec = extract_record(node)
    assert rec["validation_status"] == "Inferred"
    assert rec["evidence_strength"] == "synthesis"


@pytest.mark.parametrize(
    "evidence,status",
    [
        ("source_grounded", "Confirmed"),
        ("synthesis", "Inferred"),
        ("inference", "Inferred"),
        ("unconfirmed", "Unresolved"),
    ],
)
def test_extract_record_appendix_b(tmp_path, evidence, status):
    root = tmp_path / "v"
    node = read_vault(
        _write_node(root / "N.md", _obj_fm("N-1", evidence=evidence)).parent
    ).by_id["N-1"]
    assert extract_record(node)["validation_status"] == status


# ---------------------------------------------------------------------------
# compile_tier3 — staging, shape, determinism
# ---------------------------------------------------------------------------


def test_compile_writes_staging_for_each_tier3_artifact(fixture_repo, tmp_path):
    staging = tmp_path / "staging"
    result = compile_tier3(
        _config_path(fixture_repo), fixture_repo, staging_root=staging, now=_FIXED_NOW
    )
    # objectives.json + risks.json are the two tier3 artifacts (proposal_section is tier5).
    paths = {a.artifact_path for a in result.artifacts}
    assert paths == {
        "docs/tier3_project_instantiation/architecture_inputs/objectives.json",
        "docs/tier3_project_instantiation/architecture_inputs/risks.json",
    }
    for a in result.artifacts:
        assert a.staging_path.is_file()
        assert a.staging_path.is_relative_to(staging)


def test_compile_objectives_records(fixture_repo, tmp_path):
    result = compile_tier3(
        _config_path(fixture_repo), fixture_repo, staging_root=tmp_path / "s", now=_FIXED_NOW
    )
    obj = next(
        a for a in result.artifacts if a.artifact_path.endswith("objectives.json")
    )
    assert obj.collection_key == "objectives"
    assert [r["id"] for r in obj.records] == ["OBJ-1", "OBJ-2"]  # vault path order
    assert obj.records[0]["validation_status"] == "Confirmed"  # source_grounded
    assert obj.records[1]["validation_status"] == "Inferred"  # synthesis


def test_compile_empty_artifact_when_no_bound_nodes(fixture_repo, tmp_path):
    # No risk nodes exist in the fixture → risks.json compiles to an empty list.
    result = compile_tier3(
        _config_path(fixture_repo), fixture_repo, staging_root=tmp_path / "s", now=_FIXED_NOW
    )
    risks = next(a for a in result.artifacts if a.artifact_path.endswith("risks.json"))
    assert risks.records == ()
    written = json.loads(risks.staging_path.read_text(encoding="utf-8"))
    assert written["risks"] == []
    assert written["_provenance"]["node_count"] == 0
    assert written["_provenance"]["appendix_b_mapping"] == APPENDIX_B_MAPPING


def test_compile_deterministic_modulo_timestamp(fixture_repo, tmp_path):
    r1 = compile_tier3(_config_path(fixture_repo), fixture_repo, staging_root=tmp_path / "a")
    r2 = compile_tier3(_config_path(fixture_repo), fixture_repo, staging_root=tmp_path / "b")
    for a1, a2 in zip(r1.artifacts, r2.artifacts):
        o1 = json.loads(a1.staging_path.read_text(encoding="utf-8"))
        o2 = json.loads(a2.staging_path.read_text(encoding="utf-8"))
        o1["_provenance"].pop("compiled_at")
        o2["_provenance"].pop("compiled_at")
        assert o1 == o2


def test_compile_byte_identical_with_fixed_now(fixture_repo, tmp_path):
    a = compile_tier3(_config_path(fixture_repo), fixture_repo, staging_root=tmp_path / "a", now=_FIXED_NOW)
    b = compile_tier3(_config_path(fixture_repo), fixture_repo, staging_root=tmp_path / "b", now=_FIXED_NOW)
    for aa, bb in zip(a.artifacts, b.artifacts):
        assert aa.staging_path.read_bytes() == bb.staging_path.read_bytes()


# ---------------------------------------------------------------------------
# Non-destructive
# ---------------------------------------------------------------------------


def test_compile_does_not_touch_hand_lift(fixture_repo, tmp_path):
    # Place a hand-lift objectives.json in the fixture repo; compile must not touch it.
    hand = (
        fixture_repo
        / "docs/tier3_project_instantiation/architecture_inputs/objectives.json"
    )
    hand.parent.mkdir(parents=True, exist_ok=True)
    original = '{"objectives": ["DO NOT TOUCH"]}'
    hand.write_text(original, encoding="utf-8")
    compile_tier3(_config_path(fixture_repo), fixture_repo, staging_root=tmp_path / "s", now=_FIXED_NOW)
    assert hand.read_text(encoding="utf-8") == original


# ---------------------------------------------------------------------------
# Fail-closed
# ---------------------------------------------------------------------------


def test_fail_closed_node_tier_contradicts_binding(tmp_path):
    root = tmp_path / "repo"
    _config_path(root).parent.mkdir(parents=True, exist_ok=True)
    _config_path(root).write_text(_FIXTURE_CONFIG, encoding="utf-8")
    _write_node(
        root / "nodes" / "11_objectives" / "OBJ-1.md",
        _obj_fm("OBJ-1", tier="tier5"),  # config routes this to tier3
    )
    with pytest.raises(GraphCompileError, match=r"OBJ-1\.md.*tier"):
        compile_tier3(_config_path(root), root, staging_root=tmp_path / "s")


def test_fail_closed_node_artifact_path_contradicts_binding(tmp_path):
    root = tmp_path / "repo"
    _config_path(root).parent.mkdir(parents=True, exist_ok=True)
    _config_path(root).write_text(_FIXTURE_CONFIG, encoding="utf-8")
    _write_node(
        root / "nodes" / "11_objectives" / "OBJ-1.md",
        _obj_fm("OBJ-1", artifact_path="docs/tier3_project_instantiation/architecture_inputs/WRONG.json"),
    )
    with pytest.raises(GraphCompileError, match=r"artifact_path"):
        compile_tier3(_config_path(root), root, staging_root=tmp_path / "s")


def test_fail_closed_self_declared_artifact_path_with_no_binding(tmp_path):
    # A node that declares an extraction target no config binding routes to must
    # fail closed — the declared intent is never silently dropped.
    root = tmp_path / "repo"
    _config_path(root).parent.mkdir(parents=True, exist_ok=True)
    _config_path(root).write_text(_FIXTURE_CONFIG, encoding="utf-8")
    _write_node(
        root / "nodes" / "99_stray" / "OBJ-9.md",  # no binding matches this folder+type
        _obj_fm(
            "OBJ-9",
            artifact_path="docs/tier3_project_instantiation/architecture_inputs/objectives.json",
        ),
    )
    with pytest.raises(GraphCompileError, match=r"OBJ-9\.md.*no graph\.config\.yaml binding"):
        compile_tier3(_config_path(root), root, staging_root=tmp_path / "s")


def test_fail_closed_conflicting_collection_keys(tmp_path):
    root = tmp_path / "repo"
    cfg = """\
project_id: x
vault_path: nodes
bindings:
  - match: {node_type: objective}
    tier: tier3
    artifact_path: docs/a.json
    collection_key: objectives
  - match: {folder: "z"}
    tier: tier3
    artifact_path: docs/a.json
    collection_key: other
"""
    _config_path(root).parent.mkdir(parents=True, exist_ok=True)
    _config_path(root).write_text(cfg, encoding="utf-8")
    (root / "nodes").mkdir(parents=True, exist_ok=True)
    with pytest.raises(GraphCompileError, match=r"conflicting collection_key"):
        compile_tier3(_config_path(root), root, staging_root=tmp_path / "s")


def test_malformed_vault_fails_closed(tmp_path):
    root = tmp_path / "repo"
    _config_path(root).parent.mkdir(parents=True, exist_ok=True)
    _config_path(root).write_text(_FIXTURE_CONFIG, encoding="utf-8")
    # a node with no front-matter block
    p = root / "nodes" / "11_objectives" / "Broken.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("no front matter here", encoding="utf-8")
    with pytest.raises(VaultReadError, match=r"Broken\.md"):
        compile_tier3(_config_path(root), root, staging_root=tmp_path / "s")


# ---------------------------------------------------------------------------
# Diff report
# ---------------------------------------------------------------------------


def _write_hand_lift(repo: Path, rel: str, collection_key: str, ids: list[str]) -> None:
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps({collection_key: [{"id": i, "title": i} for i in ids]}),
        encoding="utf-8",
    )


def test_diff_converged_when_ids_match(fixture_repo, tmp_path):
    _write_hand_lift(
        fixture_repo,
        "docs/tier3_project_instantiation/architecture_inputs/objectives.json",
        "objectives",
        ["OBJ-1", "OBJ-2"],
    )
    _write_hand_lift(
        fixture_repo,
        "docs/tier3_project_instantiation/architecture_inputs/risks.json",
        "risks",
        [],
    )
    result = compile_tier3(_config_path(fixture_repo), fixture_repo, staging_root=tmp_path / "s", now=_FIXED_NOW)
    report = diff_against_hand_lift(result, fixture_repo)
    obj = next(a for a in report["artifacts"] if a["artifact"].endswith("objectives.json"))
    assert obj["status"] == "converged"
    assert obj["in_both"] == ["OBJ-1", "OBJ-2"]
    assert report["converged"] is True


def test_diff_residual_is_explained(fixture_repo, tmp_path):
    _write_hand_lift(
        fixture_repo,
        "docs/tier3_project_instantiation/architecture_inputs/risks.json",
        "risks",
        ["RISK-01", "RISK-02"],
    )
    result = compile_tier3(_config_path(fixture_repo), fixture_repo, staging_root=tmp_path / "s", now=_FIXED_NOW)
    report = diff_against_hand_lift(result, fixture_repo)
    risks = next(a for a in report["artifacts"] if a["artifact"].endswith("risks.json"))
    assert risks["status"] == "residual"
    assert sorted(risks["only_in_hand_lift"]) == ["RISK-01", "RISK-02"]
    # The residual is explained in authoring-state-agnostic terms (a pre-authoring
    # vault yields an empty compile → residual), and the hand-lift is not overwritten.
    assert "pre-authoring" in risks["explanation"]
    assert "ticket 10 cutover" in risks["explanation"]
    assert report["converged"] is False


def test_compile_and_diff_writes_report(fixture_repo, tmp_path):
    result, report = compile_and_diff(
        _config_path(fixture_repo), fixture_repo, staging_root=tmp_path / "s", now=_FIXED_NOW
    )
    report_path = fixture_repo / "docs/tier4_orchestration_state/graph_compile/diff_report.json"
    assert report_path.is_file()
    on_disk = json.loads(report_path.read_text(encoding="utf-8"))
    assert on_disk["record_type"] == "tier3_graph_compile_diff"
    assert on_disk["project_id"] == "fixture-instance"


# ---------------------------------------------------------------------------
# MSCA oracle — the real vault
# ---------------------------------------------------------------------------


@pytest.fixture
def msca_config(repo_root) -> Path:
    cfg = repo_root / "MSCA" / "graph.config.yaml"
    if not cfg.is_file():
        pytest.skip("MSCA graph.config.yaml not present")
    return cfg


def test_msca_config_loads_and_resolves_vault(msca_config, repo_root):
    cfg = load_graph_config(msca_config)
    assert cfg.project_id == "msca-pf-reference"
    assert cfg.resolve_vault_dir() == repo_root / "MSCA" / "methodology_graph"


def test_msca_compiles_tier3_from_authored_nodes(msca_config, repo_root, tmp_path):
    # Ticket 8 authored the Tier-3 binding nodes (folders 11-16), so every
    # architecture_input now compiles to its populated collection.
    result = compile_tier3(msca_config, repo_root, staging_root=tmp_path / "s", now=_FIXED_NOW)
    assert result.project_id == "msca-pf-reference"
    assert len(result.artifacts) == 6  # objectives, outcomes, impacts, wp, milestones, risks
    counts = {a.collection_key: len(a.records) for a in result.artifacts}
    assert counts == {
        "objectives": 5,
        "outcomes": 6,
        "impacts": 4,
        "work_packages": 5,
        "milestones": 6,
        "risks": 10,
    }


def test_msca_oracle_converged_after_ticket_8(msca_config, repo_root, tmp_path):
    # Ticket 8 authored the binding nodes, so the compile now CONVERGES against
    # the ticket-14 hand-lift: the record id-sets match exactly, residual 0.
    result = compile_tier3(msca_config, repo_root, staging_root=tmp_path / "s", now=_FIXED_NOW)
    report = diff_against_hand_lift(result, repo_root)
    assert report["converged"] is True
    assert report["residual_total"] == 0
    for entry in report["artifacts"]:
        assert entry["status"] == "converged"
        assert entry["only_in_hand_lift"] == []
        assert entry["only_in_compiled"] == []


def test_msca_compile_does_not_mutate_hand_lift(msca_config, repo_root, tmp_path):
    hand_dir = repo_root / "docs/tier3_project_instantiation/architecture_inputs"
    before = {p.name: p.read_bytes() for p in hand_dir.glob("*.json")}
    compile_tier3(msca_config, repo_root, staging_root=tmp_path / "s", now=_FIXED_NOW)
    after = {p.name: p.read_bytes() for p in hand_dir.glob("*.json")}
    assert before == after


def test_msca_compile_deterministic(msca_config, repo_root, tmp_path):
    r1 = compile_tier3(msca_config, repo_root, staging_root=tmp_path / "a", now=_FIXED_NOW)
    r2 = compile_tier3(msca_config, repo_root, staging_root=tmp_path / "b", now=_FIXED_NOW)
    for a1, a2 in zip(r1.artifacts, r2.artifacts):
        assert a1.staging_path.read_bytes() == a2.staging_path.read_bytes()


# ---------------------------------------------------------------------------
# CLI — runner.graph_compiler.main and the --from-graph entry
# ---------------------------------------------------------------------------


def test_module_cli_compiles_and_reports(fixture_repo, capsys):
    from runner.graph_compiler import main as compiler_main

    code = compiler_main(["--config", str(_config_path(fixture_repo)), "--repo-root", str(fixture_repo)])
    assert code == 0
    out = capsys.readouterr().out
    assert "project=fixture-instance" in out
    report = fixture_repo / "docs/tier4_orchestration_state/graph_compile/diff_report.json"
    assert report.is_file()


def test_module_cli_fail_closed_returns_2(tmp_path, capsys):
    from runner.graph_compiler import main as compiler_main

    code = compiler_main(["--config", str(tmp_path / "nope.yaml"), "--repo-root", str(tmp_path)])
    assert code == 2  # GraphConfigError (missing file) is a fail-closed, not a crash


def test_from_graph_entry_runs_before_dispatch_and_skips_scheduler(fixture_repo, monkeypatch):
    # --from-graph must compile-and-diff and return WITHOUT constructing the scheduler.
    from runner import __main__ as cli

    def _boom(*a, **k):  # pragma: no cover - must never be called
        raise AssertionError("DAGScheduler must not be constructed for --from-graph")

    monkeypatch.setattr(cli, "DAGScheduler", _boom)
    code = cli.main(
        [
            "--run-id",
            "preview",
            "--repo-root",
            str(fixture_repo),
            "--from-graph",
            str(_config_path(fixture_repo)),
        ]
    )
    assert code == 0
    staged = fixture_repo / "docs/tier4_orchestration_state/graph_compile/staging"
    assert (staged / "docs/tier3_project_instantiation/architecture_inputs/objectives.json").is_file()


def test_from_graph_fail_closed_returns_1(fixture_repo, monkeypatch):
    from runner import __main__ as cli

    monkeypatch.setattr(cli, "DAGScheduler", lambda *a, **k: None)
    code = cli.main(
        ["--run-id", "preview", "--repo-root", str(fixture_repo), "--from-graph", str(fixture_repo / "missing.yaml")]
    )
    assert code == 1  # GraphConfigError → fail-closed exit 1, not a crash (3)
