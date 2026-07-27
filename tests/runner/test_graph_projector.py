"""
Tests for runner.graph_projector — the docs→graph projector (ticket 4, D6).

Covers reading durable Tier-4 gate state, rendering/writing the phase_gate_state
mirror nodes (schema-valid, deterministic, idempotent, scoped to the owned
folder, never writing docs/**), and the enforced ``sync_direction`` no-overlap
invariant — including a cross-check against the ticket-3 compiler write-set.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from runner.graph_compiler import compile_tier3
from runner.graph_config import load_graph_config
from runner.graph_projector import (
    PROJECTOR_NODE_TYPE,
    PROJECTOR_OWNED_FOLDER,
    GraphProjectionError,
    SyncOverlapError,
    check_no_overlap,
    compute_sync_partition,
    project,
    read_tier4_gate_states,
    scan_tier4_gate_states,
)
from runner.vault_reader import read_vault


# ---------------------------------------------------------------------------
# Helpers — synthetic Tier-4 gate results
# ---------------------------------------------------------------------------


def _phase_output_path(repo_root: Path, phase_folder: str, filename: str) -> Path:
    """Resolve (and mkdir the parent of) a Tier-4 phase-output artifact path."""
    p = repo_root / "docs/tier4_orchestration_state/phase_outputs" / phase_folder / filename
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _write_gate_result(
    repo_root: Path,
    phase_folder: str,
    filename: str,
    gate_id: str,
    status: str,
    **extra,
) -> Path:
    p = _phase_output_path(repo_root, phase_folder, filename)
    obj = {
        "gate_id": gate_id,
        "gate_kind": "exit",
        "run_id": "test-run",
        "evaluated_at": "2026-07-16T10:00:00+00:00",
        "status": status,
        "deterministic_predicates": {"passed": ["p1", "p2"], "failed": []},
        "semantic_predicates": {"passed": [], "failed": []},
    }
    obj.update(extra)
    p.write_text(json.dumps(obj), encoding="utf-8")
    return p


def _write_non_gate(repo_root: Path, phase_folder: str, filename: str) -> Path:
    p = _phase_output_path(repo_root, phase_folder, filename)
    p.write_text(json.dumps({"schema_id": "some.summary.v1", "data": 1}), encoding="utf-8")
    return p


#: A gate-result file corrupted by committed git conflict markers (the real
#: bffe89d corruption class) — parses as neither a JSON object nor anything else.
_CONFLICTED_GATE_JSON = (
    "{\n"
    '  "gate_id": "phase_02_gate",\n'
    "<<<<<<< Updated upstream\n"
    '  "run_id": "run-a",\n'
    "=======\n"
    '  "run_id": "run-b",\n'
    ">>>>>>> Stashed changes\n"
    '  "status": "pass"\n'
    "}\n"
)


def _write_corrupt_gate(repo_root: Path, phase_folder: str, filename: str) -> Path:
    p = _phase_output_path(repo_root, phase_folder, filename)
    p.write_text(_CONFLICTED_GATE_JSON, encoding="utf-8")
    return p


@pytest.fixture
def tier4_repo(tmp_path) -> Path:
    root = tmp_path / "repo"
    _write_gate_result(root, "phase1_call_analysis", "gate_01_result.json", "gate_01_source_integrity", "pass", gate_kind="entry")
    _write_gate_result(root, "phase1_call_analysis", "gate_result.json", "phase_01_gate", "pass")
    _write_gate_result(root, "phase3_wp_design", "gate_result.json", "phase_03_gate", "pass")
    _write_gate_result(root, "phase8_drafting_review", "gate_10a_result.json", "gate_10a_excellence_completeness", "fail")
    _write_non_gate(root, "phase1_call_analysis", "call_analysis_summary.json")
    _write_non_gate(root, "phase3_wp_design", "wp_structure.json")
    return root


# ---------------------------------------------------------------------------
# read_tier4_gate_states
# ---------------------------------------------------------------------------


def test_reads_only_gate_result_files(tier4_repo):
    states = read_tier4_gate_states(tier4_repo)
    ids = [s.gate_id for s in states]
    assert ids == [
        "gate_01_source_integrity",
        "phase_01_gate",
        "phase_03_gate",
        "gate_10a_excellence_completeness",
    ]  # ordered by (phase, gate_id); summaries skipped


def test_gate_state_fields(tier4_repo):
    states = {s.gate_id: s for s in read_tier4_gate_states(tier4_repo)}
    g = states["phase_03_gate"]
    assert g.phase == 3
    assert g.status == "pass"
    assert g.deterministic_passed == 2
    assert g.deterministic_failed == 0
    assert g.source_artifact.endswith("phase3_wp_design/gate_result.json")


def test_missing_phase_outputs_returns_empty(tmp_path):
    assert read_tier4_gate_states(tmp_path / "nonexistent") == ()


def test_real_tier4_gate_states(repo_root):
    # The real repo carries gate results from prior runs; every one has an id+status.
    states = read_tier4_gate_states(repo_root)
    assert len(states) >= 1
    assert all(s.gate_id and s.status for s in states)


def test_real_tier4_has_no_unreadable_gate_json(repo_root):
    # Regression guard for the DOD-1 data repair: the committed phase-output corpus
    # must carry NO unparseable gate-result JSON.  A future conflict-marker commit
    # (the bffe89d failure mode) would repopulate `unreadable` and fail here — the
    # only place that pins the real mirror is complete, not silently narrowed.
    scan = scan_tier4_gate_states(repo_root)
    assert scan.unreadable == (), (
        "Corrupt gate-result JSON reappeared under phase_outputs/: "
        f"{scan.unreadable}"
    )


# ---------------------------------------------------------------------------
# scan_tier4_gate_states — surfaces corrupt gate JSON instead of dropping it
# ---------------------------------------------------------------------------


def test_scan_surfaces_unreadable_gate_json(tier4_repo):
    # A gate-result file corrupted by committed conflict markers must be reported
    # in `unreadable`, NOT silently dropped — while readable gates still parse.
    _write_corrupt_gate(tier4_repo, "phase2_concept_refinement", "gate_result.json")
    scan = scan_tier4_gate_states(tier4_repo)
    assert scan.unreadable == (
        "docs/tier4_orchestration_state/phase_outputs/"
        "phase2_concept_refinement/gate_result.json",
    )
    # the four readable gate results from the fixture are still present
    assert {s.gate_id for s in scan.gate_states} == {
        "gate_01_source_integrity",
        "phase_01_gate",
        "phase_03_gate",
        "gate_10a_excellence_completeness",
    }


def test_scan_unreadable_empty_when_all_readable(tier4_repo):
    scan = scan_tier4_gate_states(tier4_repo)
    assert scan.unreadable == ()
    assert len(scan.gate_states) == 4


def test_read_tier4_gate_states_is_readable_subset(tier4_repo):
    # The back-compat wrapper returns exactly the readable states, even with a
    # corrupt file present (which it silently omits — callers wanting the gap use
    # scan_tier4_gate_states).
    _write_corrupt_gate(tier4_repo, "phase2_concept_refinement", "gate_result.json")
    states = read_tier4_gate_states(tier4_repo)
    scan = scan_tier4_gate_states(tier4_repo)
    assert states == scan.gate_states


def test_scan_non_object_json_is_unreadable(tmp_path):
    # A *.json that parses but is not an object (e.g. a bare list) is corrupt for
    # gate-mirror purposes and surfaced, not confused with a non-gate summary.
    root = tmp_path / "repo"
    p = root / "docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/gate_result.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("[1, 2, 3]", encoding="utf-8")
    scan = scan_tier4_gate_states(root)
    assert scan.gate_states == ()
    assert scan.unreadable == (
        "docs/tier4_orchestration_state/phase_outputs/"
        "phase1_call_analysis/gate_result.json",
    )


# ---------------------------------------------------------------------------
# project — writes schema-valid, deterministic, scoped mirror nodes
# ---------------------------------------------------------------------------


def test_project_writes_mirror_nodes(tier4_repo, tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    result = project(tier4_repo, vault)
    assert len(result.written) == 4
    assert result.removed == ()
    # every written node lives in the owned folder
    for p in result.written:
        assert p.parent.name == PROJECTOR_OWNED_FOLDER


def test_projected_nodes_are_schema_valid(tier4_repo, tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    project(tier4_repo, vault)
    parsed = read_vault(vault)
    assert len(parsed.nodes) == 4
    for node in parsed.nodes:
        assert node.node_type == PROJECTOR_NODE_TYPE
        assert node.status == "Confirmed"  # source_grounded → Confirmed
        assert node.front_matter["derived"] is True
        assert node.front_matter["read_only"] is True
        assert node.front_matter["sync_direction"] == "docs_to_graph"
        assert node.tier == "tier4"


def test_projected_node_mirrors_gate_status(tier4_repo, tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    project(tier4_repo, vault)
    parsed = read_vault(vault)
    by_gate = {n.front_matter["gate_id"]: n for n in parsed.nodes}
    assert by_gate["gate_10a_excellence_completeness"].front_matter["gate_status"] == "fail"
    assert by_gate["phase_03_gate"].front_matter["gate_status"] == "pass"


def test_project_is_idempotent(tier4_repo, tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    project(tier4_repo, vault)
    first = {p.name: p.read_bytes() for p in (vault / PROJECTOR_OWNED_FOLDER).glob("*.md")}
    result2 = project(tier4_repo, vault)
    second = {p.name: p.read_bytes() for p in (vault / PROJECTOR_OWNED_FOLDER).glob("*.md")}
    assert first == second
    assert result2.removed == ()


def test_project_prunes_stale_mirror_nodes(tier4_repo, tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    project(tier4_repo, vault)
    # A stale mirror node from a prior state (a gate no longer present):
    stale = vault / PROJECTOR_OWNED_FOLDER / "PGS-phase_99_gate.md"
    stale.write_text("---\nid: PGS-phase_99_gate\n---\n", encoding="utf-8")
    result = project(tier4_repo, vault)
    assert stale in result.removed
    assert not stale.exists()


def test_project_only_touches_owned_folder(tier4_repo, tmp_path):
    vault = tmp_path / "vault"
    # a graph_to_docs-owned node elsewhere in the vault must be untouched
    other = vault / "11_objectives" / "OBJ-1.md"
    other.parent.mkdir(parents=True, exist_ok=True)
    other_content = "---\nid: OBJ-1\ntitle: Obj\nnode_type: objective\nevidence_strength: source_grounded\n---\nbody"
    other.write_text(other_content, encoding="utf-8")
    project(tier4_repo, vault)
    assert other.read_text(encoding="utf-8") == other_content


def test_project_writes_no_docs_path(tier4_repo, tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    result = project(tier4_repo, vault)
    # the projector never writes docs/** — every path is under the vault mirror
    for p in result.written:
        assert "docs" not in p.relative_to(vault).parts


def test_project_missing_vault_fails_closed(tier4_repo, tmp_path):
    with pytest.raises(GraphProjectionError, match="Vault directory not found"):
        project(tier4_repo, tmp_path / "no-such-vault")


def test_project_deterministic_no_fresh_timestamp(tier4_repo, tmp_path):
    # Two independent vaults from the same Tier-4 must be byte-identical (no now()).
    v1, v2 = tmp_path / "v1", tmp_path / "v2"
    v1.mkdir()
    v2.mkdir()
    project(tier4_repo, v1)
    project(tier4_repo, v2)
    a = {p.name: p.read_bytes() for p in (v1 / PROJECTOR_OWNED_FOLDER).glob("*.md")}
    b = {p.name: p.read_bytes() for p in (v2 / PROJECTOR_OWNED_FOLDER).glob("*.md")}
    assert a == b


def test_real_tier4_projects_into_tmp_vault(repo_root, tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    result = project(repo_root, vault)
    assert len(result.written) == len(result.gate_states) >= 1
    assert result.unreadable == ()  # real corpus is clean → complete mirror
    read_vault(vault)  # parses without error


def test_project_surfaces_unreadable_and_mirrors_the_rest(tier4_repo, tmp_path):
    # A corrupt gate-result present alongside good ones: the readable four still
    # mirror, and the corruption is surfaced on the result (never silently lost).
    _write_corrupt_gate(tier4_repo, "phase2_concept_refinement", "gate_result.json")
    vault = tmp_path / "vault"
    vault.mkdir()
    result = project(tier4_repo, vault)
    assert len(result.written) == 4
    assert result.unreadable == (
        "docs/tier4_orchestration_state/phase_outputs/"
        "phase2_concept_refinement/gate_result.json",
    )


def test_project_all_readable_reports_no_unreadable(tier4_repo, tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    result = project(tier4_repo, vault)
    assert result.unreadable == ()


def test_project_fails_closed_on_schema_invalid_node(tier4_repo, tmp_path, monkeypatch):
    # The projector guarantees schema-valid mirror nodes; if a regression made it
    # emit an invalid node_type, project() must fail closed, not write garbage.
    import runner.graph_projector as gp

    monkeypatch.setattr(gp, "PROJECTOR_NODE_TYPE", "not_a_real_node_type")
    vault = tmp_path / "vault"
    vault.mkdir()
    with pytest.raises(GraphProjectionError, match="schema-invalid mirror node"):
        project(tier4_repo, vault)


# ---------------------------------------------------------------------------
# D6 no-overlap invariant
# ---------------------------------------------------------------------------


@pytest.fixture
def msca_config(repo_root):
    cfg = repo_root / "MSCA" / "graph.config.yaml"
    if not cfg.is_file():
        pytest.skip("MSCA graph.config.yaml not present")
    return load_graph_config(cfg)


def test_msca_config_has_no_overlap(msca_config):
    check_no_overlap(msca_config)  # must not raise


def test_sync_partition_projector_writes_no_docs(msca_config):
    part = compute_sync_partition(msca_config)
    assert part.docs_to_graph_writes_docs == ()
    assert part.docs_to_graph_writes_graph == ((PROJECTOR_OWNED_FOLDER, PROJECTOR_NODE_TYPE),)
    # the compiler writes real docs/** artifacts
    assert any(p.startswith("docs/tier3") for p in part.graph_to_docs_writes_docs)


def test_no_overlap_cross_check_vs_compiler_writeset(msca_config, repo_root, tmp_path):
    # The projector's docs write-set (empty) is disjoint from the compiler's; and
    # the projector's owned folder/node_type is never extracted by the compiler.
    part = compute_sync_partition(msca_config)
    result = compile_tier3(
        repo_root / "MSCA" / "graph.config.yaml", repo_root, staging_root=tmp_path / "s"
    )
    compiler_docs = {a.artifact_path for a in result.artifacts}
    assert compiler_docs.isdisjoint(set(part.docs_to_graph_writes_docs))
    # no compiled artifact was sourced from the projector-owned folder
    for binding in msca_config.bindings:
        if binding.artifact_path is not None:
            assert not binding.matches(PROJECTOR_OWNED_FOLDER, PROJECTOR_NODE_TYPE)


def test_check_no_overlap_detects_docs_extraction_of_mirror(tmp_path):
    # A config that routes the phase_gate_state mirror to a docs artifact must fail.
    cfg_text = f"""\
project_id: bad
bindings:
  - match:
      folder: "{PROJECTOR_OWNED_FOLDER}"
      node_type: {PROJECTOR_NODE_TYPE}
    tier: tier4
    artifact_path: docs/tier4_orchestration_state/leak.json
    collection_key: leaked
"""
    p = tmp_path / "graph.config.yaml"
    p.write_text(cfg_text, encoding="utf-8")
    cfg = load_graph_config(p)
    with pytest.raises(SyncOverlapError, match="overlap"):
        check_no_overlap(cfg)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def test_cli_projects_into_config_vault(tier4_repo, tmp_path, capsys):
    from runner.graph_projector import main as projector_main

    # a config whose vault lives beside it, inside the tier4 repo
    cfg = tier4_repo / "graph.config.yaml"
    cfg.write_text(
        "project_id: cli-test\n"
        "vault_path: vault\n"
        "bindings:\n"
        f"  - match: {{folder: \"{PROJECTOR_OWNED_FOLDER}\", node_type: {PROJECTOR_NODE_TYPE}}}\n"
        "    tier: tier4\n",
        encoding="utf-8",
    )
    (tier4_repo / "vault").mkdir()
    code = projector_main(["--config", str(cfg), "--repo-root", str(tier4_repo)])
    assert code == 0
    assert "project=cli-test" in capsys.readouterr().out
    assert (tier4_repo / "vault" / PROJECTOR_OWNED_FOLDER).is_dir()


def test_cli_reports_unreadable_gate_files(tier4_repo, tmp_path, capsys):
    from runner.graph_projector import main as projector_main

    _write_corrupt_gate(tier4_repo, "phase2_concept_refinement", "gate_result.json")
    cfg = tier4_repo / "graph.config.yaml"
    cfg.write_text(
        "project_id: cli-corrupt\n"
        "vault_path: vault\n"
        "bindings:\n"
        f"  - match: {{folder: \"{PROJECTOR_OWNED_FOLDER}\", node_type: {PROJECTOR_NODE_TYPE}}}\n"
        "    tier: tier4\n",
        encoding="utf-8",
    )
    (tier4_repo / "vault").mkdir()
    code = projector_main(["--config", str(cfg), "--repo-root", str(tier4_repo)])
    out = capsys.readouterr()
    assert code == 0  # best-effort mirror still succeeds…
    assert "unreadable=1" in out.out  # …but the gap is surfaced on stdout…
    assert "phase2_concept_refinement/gate_result.json" in out.err  # …and named on stderr


def test_cli_fail_closed_on_overlap_config(tmp_path, capsys):
    from runner.graph_projector import main as projector_main

    cfg = tmp_path / "graph.config.yaml"
    cfg.write_text(
        "project_id: bad\n"
        "vault_path: vault\n"
        "bindings:\n"
        f"  - match: {{folder: \"{PROJECTOR_OWNED_FOLDER}\", node_type: {PROJECTOR_NODE_TYPE}}}\n"
        "    tier: tier4\n"
        "    artifact_path: docs/leak.json\n",
        encoding="utf-8",
    )
    (tmp_path / "vault").mkdir()
    code = projector_main(["--config", str(cfg), "--repo-root", str(tmp_path)])
    assert code == 2  # SyncOverlapError → fail-closed, before any write
