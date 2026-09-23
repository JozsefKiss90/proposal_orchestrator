"""
Tests for same-run-id resume with durable-evidence verification
(Phase 8 stepwise ticket 3).

A persisted ``released`` state string in ``.claude/runs/`` is runtime memory,
not source truth (§9.2).  When a node-scoped step counts a predecessor as
released, that claim must be backed by the predecessor's durable Tier 4 gate
result artifact — present, schema-valid, ``status: pass``, and content-fresh
(``is_gate_fresh``).  A ``RunContext`` that says released without durable,
fresh evidence fails the step closed (§6.3/§9.4) with a distinct reason per
failure mode.  Verification is read-only and scheduler-side: no gate result
is written or re-stamped (§17.6.3).

Coverage:
  1. verify_released_predecessors() unit behaviour — all-verified,
     missing / unreadable / malformed / non-pass / stale evidence,
     transitive predecessors, pending predecessors ignored,
     released node without exit gate is unverifiable.
  2. Scheduler integration — scoped step with durable fresh evidence
     proceeds; each violation class aborts fail-closed before dispatch
     (no gate evaluated, violations durable in run_summary.json).
  3. Same-run-id resume — a→d stepped across four invocations via
     RunContext.load_or_initialize, gate evidence written per step.
  4. Scope boundaries — phase scope and full-DAG runs are unaffected;
     an already-released scoped node is not verified here (rerun policy
     is ticket 4).
  5. CLI — [BLOCKED] output names evidence violations; upstream-phase
     acceptance via accepted_upstream_gates works unchanged alongside.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import yaml

from runner.dag_scheduler import (
    DAGScheduler,
    ManifestGraph,
    RunAbortedError,
    format_evidence_violation,
    verify_released_predecessors,
)
from runner.fingerprints import compute_fingerprints
from runner.gate_result_registry import (
    GATE_RESULT_PATHS,
    GATE_RESULT_SCHEMA_ID,
    TIER4_ROOT_REL,
)
from runner.run_context import RunContext
from runner.runtime_models import AgentResult
from runner.upstream_inputs import UPSTREAM_REQUIRED_INPUTS
from runner.versions import (
    CONSTITUTION_VERSION,
    LIBRARY_VERSION,
    MANIFEST_VERSION,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_GATE_PASS = {"status": "pass"}
_RA_TARGET = "runner.dag_scheduler.run_agent"
_SUCCESS_AGENT = AgentResult(status="success", can_evaluate_exit_gate=True)


@pytest.fixture(autouse=True)
def _mock_run_agent():
    """Patch ``run_agent`` — these tests exercise scheduling, not agents."""
    with patch(_RA_TARGET, return_value=_SUCCESS_AGENT):
        yield


def write_gate_evidence(
    repo: Path,
    gate_id: str,
    run_id: str = "evidence-run",
    *,
    status: str = "pass",
    evaluated_at: str | None = None,
    omit_fields: tuple[str, ...] = (),
    schema_id: str = GATE_RESULT_SCHEMA_ID,
) -> Path:
    """Write a durable gate result artifact at its canonical Tier 4 path.

    Records per-artifact fingerprints of the gate's upstream required inputs
    (as the real gate evaluator does), so freshness is content-confirmed.
    """
    path = repo / TIER4_ROOT_REL / GATE_RESULT_PATHS[gate_id]
    path.parent.mkdir(parents=True, exist_ok=True)
    fps, combined = compute_fingerprints(
        UPSTREAM_REQUIRED_INPUTS.get(gate_id, []), repo
    )
    data: dict = {
        "schema_id": schema_id,
        "gate_id": gate_id,
        "run_id": run_id,
        "status": status,
        "evaluated_at": (
            evaluated_at or datetime.now(timezone.utc).isoformat()
        ),
        "input_fingerprint": combined,
        "input_artifact_fingerprints": fps,
        "manifest_version": MANIFEST_VERSION,
        "library_version": LIBRARY_VERSION,
        "constitution_version": CONSTITUTION_VERSION,
    }
    for f in omit_fields:
        data.pop(f, None)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def _write_manifest(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "manifest.yaml"
    path.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")
    return path


def _seed_tier3_tier4(repo: Path) -> None:
    """Write minimal Tier 3/4 sources so the canonical reference pack builds."""
    _obj = repo / "docs/tier3_project_instantiation/architecture_inputs/objectives.json"
    _wp = repo / "docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json"
    _pt = repo / "docs/tier3_project_instantiation/consortium/partners.json"
    for p in (_obj, _wp, _pt):
        p.parent.mkdir(parents=True, exist_ok=True)
    _obj.write_text('{"objectives":[{"id":"OBJ-1","title":"T","measurable_target":"≥1"}]}', encoding="utf-8")
    _wp.write_text('{"work_packages":[{"wp_id":"WP1","title":"T","lead_partner":"P","deliverables":[{"deliverable_id":"D1-01","title":"D","due_month":3}]}]}', encoding="utf-8")
    _pt.write_text('{"partners":[{"short_name":"P","legal_name":"Partner One"}]}', encoding="utf-8")


def _phase8_substep_manifest() -> dict:
    """n07 → (n08a, n08b, n08c) → n08d → n08e → n08f, real gate ids."""
    def _node(nid, pn, sub, gate, terminal=False):
        return {
            "node_id": nid,
            "phase_number": pn,
            "substep": sub,
            "phase_id": f"phase_{pn:02d}{sub or ''}",
            "agent": "a",
            "skills": [],
            "exit_gate": gate,
            "terminal": terminal,
        }

    return {
        "name": "test",
        "version": "1.1",
        "node_registry": [
            {
                "node_id": "n07_budget_gate",
                "phase_number": 7,
                "phase_id": "phase_07",
                "agent": "a",
                "skills": [],
                "exit_gate": "gate_09_budget_consistency",
                "terminal": False,
            },
            _node("n08a_excellence_drafting", 8, "a", "gate_10a_excellence_completeness"),
            _node("n08b_impact_drafting", 8, "b", "gate_10b_impact_completeness"),
            _node("n08c_implementation_drafting", 8, "c", "gate_10c_implementation_completeness"),
            _node("n08d_assembly", 8, "d", "gate_10d_cross_section_consistency"),
            _node("n08e_evaluator_review", 8, "e", "gate_11_review_closure"),
            _node("n08f_revision", 8, "f", "gate_12_constitutional_compliance", terminal=True),
        ],
        "edge_registry": [
            {"edge_id": "e1", "from_node": "n07_budget_gate", "to_node": "n08a_excellence_drafting", "gate_condition": "gate_09_budget_consistency"},
            {"edge_id": "e2", "from_node": "n07_budget_gate", "to_node": "n08b_impact_drafting", "gate_condition": "gate_09_budget_consistency"},
            {"edge_id": "e3", "from_node": "n07_budget_gate", "to_node": "n08c_implementation_drafting", "gate_condition": "gate_09_budget_consistency"},
            {"edge_id": "e4", "from_node": "n08a_excellence_drafting", "to_node": "n08d_assembly", "gate_condition": "gate_10a_excellence_completeness"},
            {"edge_id": "e5", "from_node": "n08b_impact_drafting", "to_node": "n08d_assembly", "gate_condition": "gate_10b_impact_completeness"},
            {"edge_id": "e6", "from_node": "n08c_implementation_drafting", "to_node": "n08d_assembly", "gate_condition": "gate_10c_implementation_completeness"},
            {"edge_id": "e7", "from_node": "n08d_assembly", "to_node": "n08e_evaluator_review", "gate_condition": "gate_10d_cross_section_consistency"},
            {"edge_id": "e8", "from_node": "n08e_evaluator_review", "to_node": "n08f_revision", "gate_condition": "gate_11_review_closure"},
        ],
    }


def _graph() -> ManifestGraph:
    data = _phase8_substep_manifest()
    return ManifestGraph(data["node_registry"], data["edge_registry"])


# ---------------------------------------------------------------------------
# 1. verify_released_predecessors — unit behaviour
# ---------------------------------------------------------------------------


class TestVerifyReleasedPredecessors:
    def test_no_released_predecessors_is_clean(self, tmp_path: Path):
        """Pending predecessors are the ready-check's concern, not ours."""
        graph = _graph()
        ctx = RunContext.initialize(tmp_path, "v-clean")
        violations = verify_released_predecessors(
            ctx, graph, tmp_path, "n08a_excellence_drafting"
        )
        assert violations == []

    def test_released_with_durable_fresh_evidence_is_clean(self, tmp_path: Path):
        graph = _graph()
        ctx = RunContext.initialize(tmp_path, "v-ok")
        ctx.set_node_state("n07_budget_gate", "released")
        write_gate_evidence(tmp_path, "gate_09_budget_consistency")
        violations = verify_released_predecessors(
            ctx, graph, tmp_path, "n08a_excellence_drafting"
        )
        assert violations == []

    def test_released_without_artifact_is_missing_evidence(self, tmp_path: Path):
        graph = _graph()
        ctx = RunContext.initialize(tmp_path, "v-missing")
        ctx.set_node_state("n07_budget_gate", "released")
        violations = verify_released_predecessors(
            ctx, graph, tmp_path, "n08a_excellence_drafting"
        )
        assert len(violations) == 1
        v = violations[0]
        assert v["node_id"] == "n07_budget_gate"
        assert v["gate_id"] == "gate_09_budget_consistency"
        assert v["reason_code"] == "missing_evidence"
        assert "gate_result.json" in v["evidence_path"]

    def test_unreadable_evidence_is_distinct(self, tmp_path: Path):
        graph = _graph()
        ctx = RunContext.initialize(tmp_path, "v-unreadable")
        ctx.set_node_state("n07_budget_gate", "released")
        path = (
            tmp_path / TIER4_ROOT_REL
            / GATE_RESULT_PATHS["gate_09_budget_consistency"]
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{not valid json", encoding="utf-8")
        violations = verify_released_predecessors(
            ctx, graph, tmp_path, "n08a_excellence_drafting"
        )
        assert [v["reason_code"] for v in violations] == ["unreadable_evidence"]

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"omit_fields": ("run_id",)},
            {"omit_fields": ("evaluated_at",)},
            {"omit_fields": ("input_fingerprint",)},
            {"schema_id": "orch.wrong_schema.v9"},
        ],
        ids=["no-run-id", "no-evaluated-at", "no-fingerprint", "wrong-schema-id"],
    )
    def test_malformed_evidence_is_distinct(self, tmp_path: Path, kwargs: dict):
        graph = _graph()
        ctx = RunContext.initialize(tmp_path, "v-malformed")
        ctx.set_node_state("n07_budget_gate", "released")
        write_gate_evidence(tmp_path, "gate_09_budget_consistency", **kwargs)
        violations = verify_released_predecessors(
            ctx, graph, tmp_path, "n08a_excellence_drafting"
        )
        assert [v["reason_code"] for v in violations] == ["malformed_evidence"]

    def test_gate_id_mismatch_is_malformed(self, tmp_path: Path):
        """Evidence at gate_09's canonical path claiming another gate id."""
        graph = _graph()
        ctx = RunContext.initialize(tmp_path, "v-gateid")
        ctx.set_node_state("n07_budget_gate", "released")
        path = write_gate_evidence(tmp_path, "gate_09_budget_consistency")
        data = json.loads(path.read_text(encoding="utf-8"))
        data["gate_id"] = "gate_11_review_closure"
        path.write_text(json.dumps(data), encoding="utf-8")
        violations = verify_released_predecessors(
            ctx, graph, tmp_path, "n08a_excellence_drafting"
        )
        assert [v["reason_code"] for v in violations] == ["malformed_evidence"]

    def test_non_pass_status_is_distinct(self, tmp_path: Path):
        graph = _graph()
        ctx = RunContext.initialize(tmp_path, "v-nonpass")
        ctx.set_node_state("n07_budget_gate", "released")
        write_gate_evidence(tmp_path, "gate_09_budget_consistency", status="fail")
        violations = verify_released_predecessors(
            ctx, graph, tmp_path, "n08a_excellence_drafting"
        )
        assert [v["reason_code"] for v in violations] == ["non_pass_status"]
        assert "fail" in violations[0]["detail"]

    def test_stale_evidence_is_distinct(self, tmp_path: Path):
        """Upstream input rewritten after evaluation → content-stale (ST-1)."""
        graph = _graph()
        ctx = RunContext.initialize(tmp_path, "v-stale")
        ctx.set_node_state("n07_budget_gate", "released")
        _seed_tier3_tier4(tmp_path)
        past = (
            datetime.now(timezone.utc) - timedelta(hours=1)
        ).isoformat()
        write_gate_evidence(
            tmp_path, "gate_09_budget_consistency", evaluated_at=past
        )
        # Genuinely change a tracked upstream input after evaluation.
        wp = (
            tmp_path
            / "docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json"
        )
        wp.write_text('{"work_packages": []}', encoding="utf-8")
        violations = verify_released_predecessors(
            ctx, graph, tmp_path, "n08a_excellence_drafting"
        )
        assert [v["reason_code"] for v in violations] == ["stale_evidence"]
        assert "wp_structure.json" in str(violations[0]["detail"])

    def test_crashed_freshness_check_is_unverifiable_not_stale(
        self, tmp_path: Path
    ):
        """A freshness check that cannot run proves nothing — fail closed
        as unreadable evidence, not as a demonstrated mismatch."""
        graph = _graph()
        ctx = RunContext.initialize(tmp_path, "v-fresh-crash")
        ctx.set_node_state("n07_budget_gate", "released")
        write_gate_evidence(tmp_path, "gate_09_budget_consistency")
        with patch(
            "runner.dag_scheduler.is_gate_fresh",
            side_effect=OSError("disk unreadable"),
        ):
            violations = verify_released_predecessors(
                ctx, graph, tmp_path, "n08a_excellence_drafting"
            )
        assert [v["reason_code"] for v in violations] == ["unreadable_evidence"]
        assert "freshness check failed" in violations[0]["detail"]

    def test_spurious_mtime_bump_stays_fresh(self, tmp_path: Path):
        """Content-identical rewrite after evaluation does not stale (ST-1)."""
        graph = _graph()
        ctx = RunContext.initialize(tmp_path, "v-spurious")
        ctx.set_node_state("n07_budget_gate", "released")
        _seed_tier3_tier4(tmp_path)
        past = (
            datetime.now(timezone.utc) - timedelta(hours=1)
        ).isoformat()
        write_gate_evidence(
            tmp_path, "gate_09_budget_consistency", evaluated_at=past
        )
        wp = (
            tmp_path
            / "docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json"
        )
        wp.write_text(wp.read_text(encoding="utf-8"), encoding="utf-8")
        violations = verify_released_predecessors(
            ctx, graph, tmp_path, "n08a_excellence_drafting"
        )
        assert violations == []

    def test_transitive_predecessors_are_verified(self, tmp_path: Path):
        """Scoping n08d verifies n07 too, not only the direct a/b/c edges."""
        graph = _graph()
        ctx = RunContext.initialize(tmp_path, "v-transitive")
        for nid, gate in (
            ("n08a_excellence_drafting", "gate_10a_excellence_completeness"),
            ("n08b_impact_drafting", "gate_10b_impact_completeness"),
            ("n08c_implementation_drafting", "gate_10c_implementation_completeness"),
        ):
            ctx.set_node_state(nid, "released")
            write_gate_evidence(tmp_path, gate)
        # n07 claims released with no durable evidence at all.
        ctx.set_node_state("n07_budget_gate", "released")
        violations = verify_released_predecessors(
            ctx, graph, tmp_path, "n08d_assembly"
        )
        assert [(v["node_id"], v["reason_code"]) for v in violations] == [
            ("n07_budget_gate", "missing_evidence")
        ]

    def test_released_node_without_exit_gate_is_unverifiable(self, tmp_path: Path):
        registry = [
            {"node_id": "na", "phase_number": 1},
            {"node_id": "nb", "phase_number": 2, "exit_gate": "g_b"},
        ]
        edges = [
            {"edge_id": "e", "from_node": "na", "to_node": "nb", "gate_condition": "g_a"},
        ]
        graph = ManifestGraph(registry, edges)
        ctx = RunContext.initialize(tmp_path, "v-nogate")
        ctx.set_node_state("na", "released")
        violations = verify_released_predecessors(ctx, graph, tmp_path, "nb")
        assert [v["reason_code"] for v in violations] == [
            "unverifiable_no_exit_gate"
        ]

    def test_format_evidence_violation_names_the_parts(self):
        text = format_evidence_violation(
            {
                "node_id": "n07_budget_gate",
                "gate_id": "gate_09_budget_consistency",
                "evidence_path": "docs/tier4_orchestration_state/x.json",
                "reason_code": "missing_evidence",
                "detail": "no artifact on disk",
            }
        )
        assert "n07_budget_gate" in text
        assert "gate_09_budget_consistency" in text
        assert "missing_evidence" in text


# ---------------------------------------------------------------------------
# 2. Scheduler integration — fail-closed before dispatch
# ---------------------------------------------------------------------------


def _scoped_scheduler(tmp_path: Path, manifest_path: Path, ctx, node: str):
    graph = ManifestGraph.load(manifest_path)
    return DAGScheduler(
        graph, ctx, tmp_path, manifest_path=manifest_path, node=node
    )


class TestScopedStepEvidenceEnforcement:
    def test_resume_with_durable_fresh_evidence_proceeds(self, tmp_path: Path):
        _seed_tier3_tier4(tmp_path)
        manifest_path = _write_manifest(tmp_path, _phase8_substep_manifest())
        ctx = RunContext.initialize(tmp_path, "s-ok")
        ctx.set_node_state("n07_budget_gate", "released")
        ctx.save()
        write_gate_evidence(tmp_path, "gate_09_budget_consistency")

        with patch("runner.dag_scheduler.evaluate_gate", return_value=_GATE_PASS):
            summary = _scoped_scheduler(
                tmp_path, manifest_path, ctx, "8a"
            ).run()

        assert summary.overall_status == "pass"
        assert summary.dispatched_nodes == ["n08a_excellence_drafting"]

    def test_released_without_durable_artifact_fails_closed(self, tmp_path: Path):
        manifest_path = _write_manifest(tmp_path, _phase8_substep_manifest())
        ctx = RunContext.initialize(tmp_path, "s-missing")
        ctx.set_node_state("n07_budget_gate", "released")
        ctx.save()

        gate_calls: list[str] = []

        def _record(gate_id, *a, **kw):
            gate_calls.append(gate_id)
            return _GATE_PASS

        with patch("runner.dag_scheduler.evaluate_gate", side_effect=_record):
            sched = _scoped_scheduler(tmp_path, manifest_path, ctx, "8a")
            with pytest.raises(RunAbortedError) as exc_info:
                sched.run()

        summary = exc_info.value.summary
        # Never dispatched, no gate evaluated (§17.6.3 read-only).
        assert summary.dispatched_nodes == []
        assert gate_calls == []
        assert summary.node_states["n08a_excellence_drafting"] == "pending"
        # Violations are durable in the stall report.
        entry = next(
            e for e in summary.stalled_nodes
            if e["node_id"] == "n08a_excellence_drafting"
        )
        violations = entry["predecessor_evidence_violations"]
        assert [(v["node_id"], v["reason_code"]) for v in violations] == [
            ("n07_budget_gate", "missing_evidence")
        ]
        # The abort message names the violation distinctly.
        assert "evidence" in str(exc_info.value)
        assert "missing_evidence" in str(exc_info.value)
        # And run_summary.json carries it durably.
        data = json.loads(
            (ctx.run_dir / "run_summary.json").read_text(encoding="utf-8")
        )
        durable = next(
            e for e in data["stalled_nodes"]
            if e["node_id"] == "n08a_excellence_drafting"
        )
        assert durable["predecessor_evidence_violations"] == violations

    def test_stale_durable_artifact_fails_closed(self, tmp_path: Path):
        _seed_tier3_tier4(tmp_path)
        manifest_path = _write_manifest(tmp_path, _phase8_substep_manifest())
        ctx = RunContext.initialize(tmp_path, "s-stale")
        ctx.set_node_state("n07_budget_gate", "released")
        ctx.save()
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        evidence = write_gate_evidence(
            tmp_path, "gate_09_budget_consistency", evaluated_at=past
        )
        before = evidence.read_bytes()
        wp = (
            tmp_path
            / "docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json"
        )
        wp.write_text('{"work_packages": []}', encoding="utf-8")

        with patch("runner.dag_scheduler.evaluate_gate", return_value=_GATE_PASS):
            sched = _scoped_scheduler(tmp_path, manifest_path, ctx, "8a")
            with pytest.raises(RunAbortedError) as exc_info:
                sched.run()

        summary = exc_info.value.summary
        assert summary.dispatched_nodes == []
        entry = next(
            e for e in summary.stalled_nodes
            if e["node_id"] == "n08a_excellence_drafting"
        )
        assert [
            v["reason_code"] for v in entry["predecessor_evidence_violations"]
        ] == ["stale_evidence"]
        assert "stale_evidence" in str(exc_info.value)
        # Read-only: the stale evidence was not re-stamped or repaired.
        assert evidence.read_bytes() == before

    def test_failed_durable_artifact_fails_closed(self, tmp_path: Path):
        manifest_path = _write_manifest(tmp_path, _phase8_substep_manifest())
        ctx = RunContext.initialize(tmp_path, "s-nonpass")
        ctx.set_node_state("n07_budget_gate", "released")
        ctx.save()
        write_gate_evidence(
            tmp_path, "gate_09_budget_consistency", status="fail"
        )

        with patch("runner.dag_scheduler.evaluate_gate", return_value=_GATE_PASS):
            sched = _scoped_scheduler(tmp_path, manifest_path, ctx, "8a")
            with pytest.raises(RunAbortedError) as exc_info:
                sched.run()

        entry = next(
            e for e in exc_info.value.summary.stalled_nodes
            if e["node_id"] == "n08a_excellence_drafting"
        )
        assert [
            v["reason_code"] for v in entry["predecessor_evidence_violations"]
        ] == ["non_pass_status"]

    def test_stepped_resume_same_run_id_across_invocations(self, tmp_path: Path):
        """a→b→c→d as four scoped invocations resuming one run-id.

        Each invocation's mocked exit gate writes durable evidence (as the
        real evaluator does), so the next step's verification passes on
        durable state, not in-memory carry-over.
        """
        _seed_tier3_tier4(tmp_path)
        manifest_path = _write_manifest(tmp_path, _phase8_substep_manifest())
        run_id = "s-sequence"

        ctx0 = RunContext.initialize(tmp_path, run_id)
        ctx0.set_node_state("n07_budget_gate", "released")
        ctx0.save()
        write_gate_evidence(tmp_path, "gate_09_budget_consistency")

        def _eval(gate_id, rid, root, **kw):
            write_gate_evidence(tmp_path, gate_id, run_id=rid)
            return _GATE_PASS

        for step, expect_node in (
            ("8a", "n08a_excellence_drafting"),
            ("8b", "n08b_impact_drafting"),
            ("8c", "n08c_implementation_drafting"),
            ("8d", "n08d_assembly"),
        ):
            ctx = RunContext.load_or_initialize(tmp_path, run_id)
            with patch(
                "runner.dag_scheduler.evaluate_gate", side_effect=_eval
            ):
                summary = _scoped_scheduler(
                    tmp_path, manifest_path, ctx, step
                ).run()
            assert summary.overall_status == "pass", step
            assert summary.dispatched_nodes == [expect_node], step

        final = RunContext.load(tmp_path, run_id)
        for nid in (
            "n08a_excellence_drafting",
            "n08b_impact_drafting",
            "n08c_implementation_drafting",
            "n08d_assembly",
        ):
            assert final.get_node_state(nid) == "released"

    def test_resume_step_fails_closed_when_prior_step_evidence_deleted(
        self, tmp_path: Path
    ):
        """Released-in-context n08a whose durable gate result vanished."""
        _seed_tier3_tier4(tmp_path)
        manifest_path = _write_manifest(tmp_path, _phase8_substep_manifest())
        run_id = "s-vanished"
        ctx0 = RunContext.initialize(tmp_path, run_id)
        for nid in (
            "n07_budget_gate",
            "n08a_excellence_drafting",
            "n08b_impact_drafting",
            "n08c_implementation_drafting",
        ):
            ctx0.set_node_state(nid, "released")
        ctx0.save()
        write_gate_evidence(tmp_path, "gate_09_budget_consistency")
        write_gate_evidence(tmp_path, "gate_10b_impact_completeness")
        write_gate_evidence(tmp_path, "gate_10c_implementation_completeness")
        # gate_10a evidence deliberately absent.

        ctx = RunContext.load_or_initialize(tmp_path, run_id)
        with patch("runner.dag_scheduler.evaluate_gate", return_value=_GATE_PASS):
            sched = _scoped_scheduler(tmp_path, manifest_path, ctx, "8d")
            with pytest.raises(RunAbortedError) as exc_info:
                sched.run()

        entry = next(
            e for e in exc_info.value.summary.stalled_nodes
            if e["node_id"] == "n08d_assembly"
        )
        assert [
            (v["node_id"], v["reason_code"])
            for v in entry["predecessor_evidence_violations"]
        ] == [("n08a_excellence_drafting", "missing_evidence")]


# ---------------------------------------------------------------------------
# 3. Scope boundaries — verification applies to node scope only
# ---------------------------------------------------------------------------


class TestScopeBoundaries:
    def test_phase_scope_run_is_unaffected(self, tmp_path: Path):
        """--phase dispatch does not require durable predecessor evidence.

        (Phase-scope continuation already verifies evidence at bootstrap
        time for nodes it seeds; states loaded as released are the
        operator's phase-scope contract, unchanged by this ticket.)
        """
        _seed_tier3_tier4(tmp_path)
        manifest_path = _write_manifest(tmp_path, _phase8_substep_manifest())
        graph = ManifestGraph.load(manifest_path)
        ctx = RunContext.initialize(tmp_path, "b-phase")
        ctx.set_node_state("n07_budget_gate", "released")
        ctx.save()

        with patch("runner.dag_scheduler.evaluate_gate", return_value=_GATE_PASS):
            sched = DAGScheduler(
                graph, ctx, tmp_path, manifest_path=manifest_path, phase=8
            )
            summary = sched.run()

        assert summary.overall_status == "pass"
        assert len(summary.dispatched_nodes) == 6

    def test_full_dag_run_is_unaffected(self, tmp_path: Path):
        _seed_tier3_tier4(tmp_path)
        manifest_path = _write_manifest(tmp_path, _phase8_substep_manifest())
        graph = ManifestGraph.load(manifest_path)
        ctx = RunContext.initialize(tmp_path, "b-full")

        with patch("runner.dag_scheduler.evaluate_gate", return_value=_GATE_PASS):
            sched = DAGScheduler(
                graph, ctx, tmp_path, manifest_path=manifest_path
            )
            summary = sched.run()

        assert summary.overall_status == "pass"
        assert len(summary.dispatched_nodes) == 7

    def test_already_released_scoped_node_is_not_verified_here(
        self, tmp_path: Path
    ):
        """Rerun of an already-gated sub-phase is ticket 4's refusal policy;
        ticket 3 verifies only steps that would actually dispatch."""
        manifest_path = _write_manifest(tmp_path, _phase8_substep_manifest())
        ctx = RunContext.initialize(tmp_path, "b-released")
        ctx.set_node_state("n07_budget_gate", "released")
        ctx.set_node_state("n08a_excellence_drafting", "released")
        ctx.save()
        # No durable evidence anywhere — but the scoped node is not pending,
        # so nothing is dispatched and nothing counts predecessors.

        with patch("runner.dag_scheduler.evaluate_gate", return_value=_GATE_PASS):
            summary = _scoped_scheduler(
                tmp_path, manifest_path, ctx, "8a"
            ).run()

        assert summary.overall_status == "pass"
        assert summary.dispatched_nodes == []


# ---------------------------------------------------------------------------
# 4. CLI — [BLOCKED] evidence violations and bootstrap coexistence
# ---------------------------------------------------------------------------

_TRANSPORT_PC = SimpleNamespace(
    backend_name="mock", model="mock-model", preset_name="MOCK"
)


def _cli_patches():
    return (
        patch(
            "runner.transport.config.resolve_provider_config",
            return_value=_TRANSPORT_PC,
        ),
        patch("runner.transport.config.is_production_mode", return_value=False),
        patch("runner.dag_scheduler.evaluate_gate", return_value=_GATE_PASS),
    )


class TestCLIResumeEvidence:
    def test_cli_blocked_report_names_evidence_violation(
        self, tmp_path: Path, capsys
    ):
        from runner.__main__ import main

        manifest_path = _write_manifest(tmp_path, _phase8_substep_manifest())
        ctx = RunContext.initialize(tmp_path, "cli-evidence-blocked")
        ctx.set_node_state("n07_budget_gate", "released")
        ctx.save()

        p1, p2, p3 = _cli_patches()
        with p1, p2, p3:
            code = main([
                "--run-id", "cli-evidence-blocked",
                "--repo-root", str(tmp_path),
                "--manifest-path", str(manifest_path),
                "--node", "8a",
            ])
        assert code == 2
        out = capsys.readouterr().out
        assert "[BLOCKED] n08a_excellence_drafting" in out
        assert "missing_evidence" in out
        assert "gate_09_budget_consistency" in out

    def test_cli_json_blocked_report_carries_violations(
        self, tmp_path: Path, capsys
    ):
        from runner.__main__ import main

        manifest_path = _write_manifest(tmp_path, _phase8_substep_manifest())
        ctx = RunContext.initialize(tmp_path, "cli-evidence-json")
        ctx.set_node_state("n07_budget_gate", "released")
        ctx.save()

        p1, p2, p3 = _cli_patches()
        with p1, p2, p3:
            code = main([
                "--run-id", "cli-evidence-json",
                "--repo-root", str(tmp_path),
                "--manifest-path", str(manifest_path),
                "--node", "8a",
                "--json",
            ])
        assert code == 2
        events = [
            json.loads(line)
            for line in capsys.readouterr().out.splitlines()
            if line.strip().startswith("{")
        ]
        blocked = next(
            e for e in events if e["event"] == "node_scope_blocked"
        )
        assert blocked["node_id"] == "n08a_excellence_drafting"
        codes = [
            v["reason_code"]
            for v in blocked["predecessor_evidence_violations"]
        ]
        assert codes == ["missing_evidence"]

    def test_upstream_phase_acceptance_still_works_alongside(
        self, tmp_path: Path, capsys
    ):
        """Fresh run-id + durable gate_09 evidence: the continuation
        bootstrap seeds n07 (recording accepted_upstream_gates), and the
        scoped step's verification accepts the same durable evidence."""
        from runner.__main__ import main

        _seed_tier3_tier4(tmp_path)
        manifest_path = _write_manifest(tmp_path, _phase8_substep_manifest())
        write_gate_evidence(
            tmp_path, "gate_09_budget_consistency", run_id="original-run"
        )

        p1, p2, p3 = _cli_patches()
        with p1, p2, p3:
            code = main([
                "--run-id", "cli-evidence-bootstrap",
                "--repo-root", str(tmp_path),
                "--manifest-path", str(manifest_path),
                "--node", "8a",
            ])
        assert code == 0
        out = capsys.readouterr().out
        assert "[BOOTSTRAP]" in out
        ctx = RunContext.load(tmp_path, "cli-evidence-bootstrap")
        assert ctx.get_node_state("n08a_excellence_drafting") == "released"
        accepted = ctx.get_accepted_upstream_gate("gate_09_budget_consistency")
        assert accepted is not None
        assert accepted["original_run_id"] == "original-run"
