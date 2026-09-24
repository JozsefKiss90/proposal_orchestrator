"""
Gate invariant pins for Dev Graph milestone 1.

The milestone adds an advisory planner and a shadow comparison beside the
scheduler. These tests prove it weakens no gate:

* the gate evaluator has exactly two call sites, both in the scheduler;
* the Phase 8 reuse decision is identical with and without a planner
  advisory and a shadow comparison on disk;
* the budget-before-Phase-8 hard block behaves as before with those
  advisory artifacts present.

Every test builds its own synthetic world under a temporary directory and
patches only at the scheduler boundary (``run_agent``, ``evaluate_gate``).
No runner phase is dispatched.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from runner.dag_scheduler import _HARD_BLOCK_GATE
from runner.dev_graph import (
    IMPACT_PLANS_REL,
    PLAN_SCHEMA_ID,
    SHADOW_COMPARISONS_REL,
    SHADOW_SCHEMA_ID,
)
from runner.paths import find_repo_root
from runner.phase8_reuse import (
    FINGERPRINT_INPUTS,
    REUSE_ELIGIBLE_NODES,
    ReuseDecision,
    artifact_sha256,
    compute_input_fingerprint,
    validate_reuse_candidate,
    write_reuse_metadata,
)
from runner.run_context import PHASE_8_NODE_IDS, RunContext
from runner.runtime_models import AgentResult
from tests.runner.test_dag_scheduler import _gate09_node_manifest, _make_scheduler

REPO = find_repo_root()
_RA_TARGET = "runner.dag_scheduler.run_agent"
_EG_TARGET = "runner.dag_scheduler.evaluate_gate"
_GATE_FAIL = {"status": "fail"}
_SUCCESS_AGENT = AgentResult(status="success", can_evaluate_exit_gate=True)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _plant_advisory_artifacts(repo: Path, artifact_path: str) -> None:
    """A planner advisory saying *rerun* for the artifact, plus a shadow
    comparison that disagrees with a reuse. Both are the shape the writers
    emit; neither is read by anything at runtime."""
    plan = {
        "schema_id": PLAN_SCHEMA_ID,
        "plan_id": "sha256:" + "a" * 64,
        "advisory": True,
        "mode": "shadow",
        "change_id": "CR-PLANTED",
        "nothing_changed": False,
        "origins": ["T03"],
        "entries": [
            {
                "kind": "artifact",
                "id": "ART-1",
                "path": artifact_path,
                "hit": "coverage_unknown",
                "action": "rerun",
                "reason_path": ["coverage_unknown:ART-1"],
                "detail": "no declared inputs",
            }
        ],
        "newly_relevant_sources": [],
    }
    _write_json(repo / IMPACT_PLANS_REL / ("a" * 16) / "plan.json", plan)
    comparison = {
        "schema_id": SHADOW_SCHEMA_ID,
        "comparison_id": "sha256:" + "b" * 64,
        "advisory": True,
        "mode": "shadow",
        "consumed_at_runtime": False,
        "plan_id": plan["plan_id"],
        "run_id": "run-prev",
        "diagnostic": "planner_broader",
        "rows": [],
    }
    _write_json(repo / SHADOW_COMPARISONS_REL / ("b" * 16) / "comparison.json", comparison)


def _make_full_reuse_env(repo: Path, node_id: str, run_id: str = "prev-run-001") -> str:
    """A complete reuse-eligible environment; returns the input fingerprint."""
    from runner.gate_result_registry import GATE_RESULT_PATHS

    cfg = REUSE_ELIGIBLE_NODES[node_id]
    for rel in FINGERPRINT_INPUTS[node_id]:
        target = repo / rel / "data.json" if rel.endswith("/") else repo / rel
        _write_json(target, {"input": "value"})
    _write_json(
        repo / cfg["artifact_path"],
        {
            "schema_id": cfg["schema_id"],
            "run_id": run_id,
            "criterion": "Test",
            "sub_sections": [],
            "validation_status": {"overall_status": "confirmed", "claim_statuses": []},
            "traceability_footer": {"primary_sources": [], "no_unsupported_claims_declaration": True},
        },
    )
    gate_rel = GATE_RESULT_PATHS[cfg["gate_id"]]
    _write_json(
        repo / "docs/tier4_orchestration_state" / gate_rel,
        {"status": "pass", "gate_id": cfg["gate_id"], "run_id": run_id},
    )
    fp = compute_input_fingerprint(node_id, repo)
    assert fp is not None
    art_hash = artifact_sha256(repo / cfg["artifact_path"])
    assert art_hash is not None
    write_reuse_metadata(
        node_id=node_id,
        repo_root=repo,
        source_run_id=run_id,
        artifact_path=cfg["artifact_path"],
        schema_id=cfg["schema_id"],
        gate_id=cfg["gate_id"],
        input_fingerprint=fp,
        artifact_hash=art_hash,
    )
    return fp


def _tree_bytes(root: Path, rel: str) -> dict[str, bytes]:
    base = root / rel
    if not base.exists():
        return {}
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in base.rglob("*") if p.is_file()}


# --------------------------------------------------------------------------- #
# Pin 1: the gate evaluator has exactly two call sites, both in the scheduler
# --------------------------------------------------------------------------- #


_SKIP_PARTS = frozenset({"tests", ".git", ".venv", "venv", "node_modules", "__pycache__", "worktrees", ".scratch"})


def _python_files() -> list[Path]:
    """Every Python file in the repository outside tests, worktrees and
    vendored trees, hooks and top-level scripts included."""
    out = []
    for path in REPO.rglob("*.py"):
        rel = path.relative_to(REPO)
        if _SKIP_PARTS.intersection(rel.parts):
            continue
        out.append(path)
    return sorted(out)


def _evaluate_gate_call_sites() -> list[tuple[str, int]]:
    """Calls of the gate evaluator by its own name or by any alias bound
    from ``runner.gate_evaluator`` (``import ... as``, ``from ... import
    ... as``, module aliases)."""
    hits: list[tuple[str, int]] = []
    for path in _python_files():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (SyntaxError, UnicodeDecodeError):
            continue
        names = {"evaluate_gate"}
        modules: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.endswith("gate_evaluator"):
                names.update(a.asname or a.name for a in node.names if a.name == "evaluate_gate")
            if isinstance(node, ast.Import):
                modules.update(a.asname or a.name for a in node.names if a.name.endswith("gate_evaluator"))
            if isinstance(node, ast.ImportFrom) and node.module:
                modules.update(a.asname or a.name for a in node.names if a.name == "gate_evaluator")
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            hit = False
            if isinstance(func, ast.Name):
                hit = func.id in names
            elif isinstance(func, ast.Attribute):
                owner = func.value
                hit = func.attr in names or (
                    func.attr == "evaluate_gate" and isinstance(owner, ast.Name) and owner.id in modules
                )
            if hit:
                hits.append((path.relative_to(REPO).as_posix(), node.lineno))
    return hits


class TestGateEvaluatorCallSites:
    def test_exactly_two_call_sites_both_in_the_scheduler(self):
        sites = _evaluate_gate_call_sites()
        assert len(sites) == 2, sites
        assert {path for path, _ in sites} == {"runner/dag_scheduler.py"}, sites

    def test_the_dev_graph_package_names_no_gate_evaluation(self):
        for path in sorted((REPO / "runner" / "dev_graph").glob("*.py")):
            text = path.read_text(encoding="utf-8")
            assert "evaluate_gate" not in text, path.name
            assert "gate_evaluator" not in text, path.name


# --------------------------------------------------------------------------- #
# Pin 2: the reuse decision is the same with and without an advisory
# --------------------------------------------------------------------------- #


class TestReuseDecisionIgnoresAdvisory:
    @pytest.mark.parametrize("node_id", sorted(REUSE_ELIGIBLE_NODES))
    def test_reusable_decision_is_identical(self, tmp_path: Path, node_id: str):
        fp = _make_full_reuse_env(tmp_path, node_id)
        without = validate_reuse_candidate(node_id, tmp_path, current_fingerprint=fp)
        assert isinstance(without, ReuseDecision) and without.reusable is True

        _plant_advisory_artifacts(tmp_path, REUSE_ELIGIBLE_NODES[node_id]["artifact_path"])

        fp_after = compute_input_fingerprint(node_id, tmp_path)
        with_advisory = validate_reuse_candidate(node_id, tmp_path, current_fingerprint=fp_after)
        # The advisory says rerun and the comparison says planner_broader;
        # the fingerprint and the decision do not move.
        assert fp_after == fp
        assert with_advisory == without

    def test_not_reusable_decision_is_identical(self, tmp_path: Path):
        node_id = "n08b_impact_drafting"
        fp = _make_full_reuse_env(tmp_path, node_id)
        stale = "0" * 64
        assert stale != fp
        without = validate_reuse_candidate(node_id, tmp_path, current_fingerprint=stale)
        assert without.reusable is False
        _plant_advisory_artifacts(tmp_path, REUSE_ELIGIBLE_NODES[node_id]["artifact_path"])
        with_advisory = validate_reuse_candidate(node_id, tmp_path, current_fingerprint=stale)
        assert with_advisory == without

    def test_fingerprint_inputs_exclude_the_dev_graph_index(self):
        for node_id, inputs in FINGERPRINT_INPUTS.items():
            assert not any("dev_graph" in rel for rel in inputs), node_id


# --------------------------------------------------------------------------- #
# Pin 3: the budget-before-Phase-8 hard block is unchanged
# --------------------------------------------------------------------------- #


class TestBudgetHardBlockUnchanged:
    def test_gate_and_phase8_node_set_are_pinned(self):
        assert _HARD_BLOCK_GATE == "gate_09_budget_consistency"
        assert set(PHASE_8_NODE_IDS) == {
            "n08a_excellence_drafting",
            "n08b_impact_drafting",
            "n08c_implementation_drafting",
            "n08d_assembly",
            "n08e_evaluator_review",
            "n08f_revision",
        }

    @staticmethod
    def _run_gate09_failure(repo: Path, run_id: str) -> tuple[dict, int]:
        """Run the gate_09 manifest with the exit gate failing; return the
        manifest and the number of gate evaluations."""
        sched = _make_scheduler(repo, _gate09_node_manifest(), run_id=run_id)
        with patch(_RA_TARGET, return_value=_SUCCESS_AGENT), patch(_EG_TARGET, return_value=_GATE_FAIL) as mock_eg:
            try:
                sched.run()
            except Exception:  # RunAbortedError is the documented outcome
                pass
        return RunContext.load(repo, run_id).to_dict(), mock_eg.call_count

    def test_gate09_failure_is_the_same_with_and_without_advisory_artifacts(self, tmp_path: Path):
        without_root = tmp_path / "without"
        with_root = tmp_path / "with"
        for root in (without_root, with_root):
            root.mkdir()
            _make_full_reuse_env(root, "n08a_excellence_drafting")
        _plant_advisory_artifacts(with_root, REUSE_ELIGIBLE_NODES["n08a_excellence_drafting"]["artifact_path"])

        manifest_without, calls_without = self._run_gate09_failure(without_root, "run-hb")
        manifest_with, calls_with = self._run_gate09_failure(with_root, "run-hb")

        assert calls_with == calls_without == 1
        comparable = ("node_states", "hard_block_gate", "hard_block_reason", "reuse_decisions", "node_failure_details")
        for key in comparable:
            assert manifest_with.get(key) == manifest_without.get(key), key
        assert manifest_with["node_states"]["n07_budget_gate"] == "blocked_at_exit"
        assert all(manifest_with["node_states"][n] == "hard_block_upstream" for n in PHASE_8_NODE_IDS)

    def test_gate09_failure_freezes_phase8_with_advisory_artifacts_present(self, tmp_path: Path):
        # A reuse-eligible environment, an advisory plan and a comparison
        # are all on disk, and a prior run manifest records a reuse.
        fp = _make_full_reuse_env(tmp_path, "n08a_excellence_drafting")
        _plant_advisory_artifacts(tmp_path, REUSE_ELIGIBLE_NODES["n08a_excellence_drafting"]["artifact_path"])
        prev = RunContext.initialize(tmp_path, "run-prev")
        prev.record_reuse_decision(
            "n08a_excellence_drafting",
            {"status": "reused", "artifact_path": REUSE_ELIGIBLE_NODES["n08a_excellence_drafting"]["artifact_path"], "input_fingerprint": fp},
        )
        prev.save()
        reuse_before = _tree_bytes(tmp_path, "docs/tier4_orchestration_state/reuse")
        plans_before = _tree_bytes(tmp_path, IMPACT_PLANS_REL)
        comparisons_before = _tree_bytes(tmp_path, SHADOW_COMPARISONS_REL)

        sched = _make_scheduler(tmp_path, _gate09_node_manifest(), run_id="run-hb")
        with patch(_RA_TARGET, return_value=_SUCCESS_AGENT), patch(_EG_TARGET, return_value=_GATE_FAIL) as mock_eg:
            try:
                sched.run()
            except Exception:  # RunAbortedError is the documented outcome
                pass

        ctx = RunContext.load(tmp_path, "run-hb")
        assert ctx.get_node_state("n07_budget_gate") == "blocked_at_exit"
        for node_id in PHASE_8_NODE_IDS:
            assert ctx.get_node_state(node_id) == "hard_block_upstream", node_id
        manifest = ctx.to_dict()
        assert manifest["hard_block_gate"] == "gate_09_budget_consistency"
        assert "hard_block_reason" in manifest
        # Only the budget gate was evaluated; no Phase 8 gate and no Phase 8 body.
        assert mock_eg.call_count == 1
        assert not set(manifest.get("reuse_decisions", {}))
        # The advisory artifacts and reuse metadata are untouched by the run.
        assert _tree_bytes(tmp_path, "docs/tier4_orchestration_state/reuse") == reuse_before
        assert _tree_bytes(tmp_path, IMPACT_PLANS_REL) == plans_before
        assert _tree_bytes(tmp_path, SHADOW_COMPARISONS_REL) == comparisons_before
