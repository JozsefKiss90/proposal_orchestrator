"""
Dev-graph shadow comparison: the planner's advisory against the reuse
decision the scheduler actually recorded.

Every test copies ``tests/fixtures/dev_graph_synthetic`` into a temporary
root, seeds a run manifest with a reuse decision, and drives the public
``runner.dev_graph`` entry points. Nothing here dispatches a phase, evaluates
a gate, or writes reuse metadata; the tests pin that the comparison does not
either.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from runner.deterministic_components import COMPONENT_REGISTRY, invoke_component
from runner.dev_graph import (
    DIAGNOSTICS,
    IMPACT_PLANS_REL,
    IMPACT_REQUEST_REL,
    SHADOW_COMPARISONS_REL,
    SHADOW_REQUEST_REL,
    SHADOW_SCHEMA_ID,
    VERDICTS,
    DevGraphError,
    ImpactPlan,
    ShadowComparison,
    compare_shadow,
    import_document,
    load_snapshot,
    plan_impact,
    read_run_records,
    record_change,
    write_impact_plan,
    write_shadow_comparison,
)
from runner.dev_graph.builder import WP_SEED_REL
from runner.dev_graph.identity import HASH_PREFIX
from runner.paths import find_repo_root

FIXTURE = find_repo_root() / "tests" / "fixtures" / "dev_graph_synthetic"
CANDIDATE = Path("docs/tier5_deliverables/candidates/synthetic_candidate.json")
REUSE_DIR = Path("docs/tier4_orchestration_state/reuse/phase8")
RUNS_DIR = Path(".claude/runs")
NODE = "n08a_excellence_drafting"
#: The fixture artifact record the planner knows about; the seeded scheduler
#: decision is bound to it explicitly so the comparison has a path to match.
SECTION_PATH = "docs/tier5_deliverables/proposal_sections/synthetic_section_two.json"
NOT_REUSED = {"status": "not_reused", "reason": "fingerprint_mismatch"}
REUSED = {
    "status": "reused",
    "mode": "drafting_skipped_audit_executed",
    "source_run_id": "run-prev",
    "artifact_run_id": "run-prev",
    "artifact_path": SECTION_PATH,
    "input_fingerprint": "abc",
    "gate_id": "gate_10a_excellence_completeness",
}


@pytest.fixture
def world(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    shutil.copytree(FIXTURE, root)
    import_document(root, CANDIDATE)
    (root / REUSE_DIR).mkdir(parents=True)
    (root / REUSE_DIR / f"{NODE}.reuse.json").write_text('{"sentinel": "reuse metadata"}', encoding="utf-8")
    return root


def _load(root: Path, rel: Path | str) -> dict:
    return json.loads((root / rel).read_text(encoding="utf-8"))


def _tree_bytes(root: Path, rel: Path) -> dict[str, bytes]:
    base = root / rel
    if not base.exists():
        return {}
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in base.rglob("*") if p.is_file()}


def _seed_manifest(root: Path, run_id: str, decisions: dict) -> Path:
    path = root / RUNS_DIR / run_id / "run_manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"run_id": run_id, "reuse_decisions": decisions}), encoding="utf-8")
    return path


def _plan_for(root: Path, new_seed: dict, change_id: str) -> ImpactPlan:
    change = record_change(root, WP_SEED_REL, new_seed, change_id=change_id)
    before = load_snapshot(root, change.before_snapshot_id)
    after = load_snapshot(root, change.after_snapshot_id)
    return plan_impact(before, after, read_run_records(root), change_id=change_id)


def _t03_moved_plan(root: Path) -> ImpactPlan:
    seed = _load(root, WP_SEED_REL)
    t03 = next(t for t in seed["work_packages"][0]["tasks"] if t["task_id"] == "T03")
    t03["responsible_partner"] = "P-C"
    return _plan_for(root, seed, "CR-1")


def _nothing_changed_plan(root: Path) -> ImpactPlan:
    plan = _plan_for(root, _load(root, WP_SEED_REL), "CR-NOOP")
    assert plan.nothing_changed
    return plan


# --------------------------------------------------------------------------- #
# The three diagnostics
# --------------------------------------------------------------------------- #


class TestDiagnostics:
    def test_vocabularies_are_closed(self):
        assert DIAGNOSTICS == {"agreed", "planner_narrower", "planner_broader"}
        assert VERDICTS == {"rerun", "reuse"}

    def test_not_reused_against_a_nothing_changed_advisory_is_planner_narrower(self, world: Path):
        before_reuse = _tree_bytes(world, REUSE_DIR)
        plan = _nothing_changed_plan(world)
        _seed_manifest(world, "run-a", {NODE: NOT_REUSED})

        cmp = compare_shadow(plan, {NODE: NOT_REUSED}, run_id="run-a")

        assert isinstance(cmp, ShadowComparison)
        assert cmp.diagnostic == "planner_narrower"
        assert cmp.plan_id == plan.plan_id and cmp.run_id == "run-a"
        [row] = cmp.rows
        assert row["node_id"] == NODE
        assert row["scheduler"] == "rerun" and row["scheduler_status"] == "not_reused"
        assert row["planner"] == "reuse" and row["diagnostic"] == "planner_narrower"
        assert row["planner_actions"] == [] and row["record_ids"] == []
        assert _tree_bytes(world, REUSE_DIR) == before_reuse

    def test_not_reused_against_a_rerun_advisory_is_agreed(self, world: Path):
        plan = _t03_moved_plan(world)
        cmp = compare_shadow(plan, {NODE: NOT_REUSED}, run_id="run-b", artifact_paths={NODE: SECTION_PATH})
        assert cmp.diagnostic == "agreed"
        [row] = cmp.rows
        assert row["scheduler"] == "rerun" and row["planner"] == "rerun"
        assert row["record_ids"] == ["ART-SECTION-2"] and row["planner_actions"] == ["rerun"]
        assert row["artifact_path"] == SECTION_PATH

    def test_reused_against_a_rerun_advisory_is_planner_broader(self, world: Path):
        plan = _t03_moved_plan(world)
        # The reused decision carries its own artifact path; no binding needed.
        cmp = compare_shadow(plan, {NODE: REUSED}, run_id="run-c")
        assert cmp.diagnostic == "planner_broader"
        [row] = cmp.rows
        assert row["scheduler"] == "reuse" and row["scheduler_status"] == "reused"
        assert row["planner"] == "rerun" and row["diagnostic"] == "planner_broader"

    def test_reused_against_a_nothing_changed_advisory_is_agreed(self, world: Path):
        plan = _nothing_changed_plan(world)
        cmp = compare_shadow(plan, {NODE: REUSED}, run_id="run-d")
        assert cmp.diagnostic == "agreed"
        assert cmp.rows[0]["planner"] == "reuse" and cmp.rows[0]["scheduler"] == "reuse"

    def test_an_artifact_without_a_run_record_cannot_be_vouched_for(self, world: Path):
        plan = _t03_moved_plan(world)
        unknown = dict(REUSED, artifact_path="docs/tier5_deliverables/proposal_sections/not_in_run_records.json")
        cmp = compare_shadow(plan, {NODE: unknown}, run_id="run-e")
        [row] = cmp.rows
        assert row["planner"] == "rerun" and row["record_ids"] == []
        assert "no run record" in row["detail"]
        assert cmp.diagnostic == "planner_broader"

    def test_broader_outranks_narrower_and_every_row_is_kept(self, world: Path):
        plan = _t03_moved_plan(world)
        decisions = {
            NODE: REUSED,
            "n08b_impact_drafting": NOT_REUSED,
        }
        # The second node is bound to the deliverable check, which the T03
        # plan reaches over unchanged edges only (reuse-under-policy).
        deliverable = "docs/tier4_orchestration_state/validation_reports/synthetic_deliverable_check.json"
        paths = {NODE: SECTION_PATH, "n08b_impact_drafting": deliverable}
        cmp = compare_shadow(plan, decisions, run_id="run-f", artifact_paths=paths)
        by_node = {r["node_id"]: r for r in cmp.rows}
        assert by_node[NODE]["diagnostic"] == "planner_broader"
        narrower = by_node["n08b_impact_drafting"]
        assert narrower["diagnostic"] == "planner_narrower"
        assert narrower["planner_actions"] == ["reuse-under-policy"] and narrower["record_ids"] == ["CHK-DELIVERABLE"]
        assert cmp.diagnostic == "planner_broader"
        assert [r["node_id"] for r in cmp.rows] == sorted(decisions)

    def test_the_comparison_is_advisory_and_content_addressed(self, world: Path):
        plan = _t03_moved_plan(world)
        a = compare_shadow(plan, {NODE: REUSED}, run_id="run-g")
        b = compare_shadow(plan.to_dict(), {NODE: REUSED}, run_id="run-g")
        assert a == b and a.comparison_id == b.comparison_id
        assert a.comparison_id.startswith(HASH_PREFIX)
        doc = a.to_dict()
        assert doc["schema_id"] == SHADOW_SCHEMA_ID
        assert doc["advisory"] is True and doc["mode"] == "shadow" and doc["consumed_at_runtime"] is False
        assert doc["diagnostic"] in DIAGNOSTICS
        for row in doc["rows"]:
            assert row["planner"] in VERDICTS and row["scheduler"] in VERDICTS and row["diagnostic"] in DIAGNOSTICS
        c = compare_shadow(plan, {NODE: REUSED}, run_id="run-other")
        assert c.comparison_id != a.comparison_id


class TestRefusals:
    def test_no_recorded_decision_is_refused(self, world: Path):
        plan = _t03_moved_plan(world)
        with pytest.raises(DevGraphError) as exc:
            compare_shadow(plan, {}, run_id="run-x")
        assert exc.value.kind == "malformed_request"

    def test_a_decision_without_a_closed_status_is_refused(self, world: Path):
        plan = _t03_moved_plan(world)
        with pytest.raises(DevGraphError) as exc:
            compare_shadow(plan, {NODE: {"reused": False}}, run_id="run-x")
        assert exc.value.kind == "malformed_record" and NODE in exc.value.offender

    def test_a_node_with_no_artifact_binding_is_refused(self, world: Path):
        plan = _t03_moved_plan(world)
        with pytest.raises(DevGraphError) as exc:
            compare_shadow(plan, {"n99_unknown": NOT_REUSED}, run_id="run-x", artifact_paths={})
        assert exc.value.kind == "malformed_request" and "n99_unknown" in exc.value.offender

    def test_a_malformed_plan_is_refused(self, world: Path):
        with pytest.raises(DevGraphError) as exc:
            compare_shadow({"schema_id": "other", "plan_id": "x"}, {NODE: REUSED}, run_id="run-x")
        assert exc.value.kind == "malformed_record"
        with pytest.raises(DevGraphError):
            compare_shadow(None, {NODE: REUSED}, run_id="run-x")  # type: ignore[arg-type]

    def test_a_bad_run_id_is_refused(self, world: Path):
        plan = _t03_moved_plan(world)
        with pytest.raises(DevGraphError) as exc:
            compare_shadow(plan, {NODE: REUSED}, run_id="bad id")
        assert exc.value.kind == "malformed_request"


# --------------------------------------------------------------------------- #
# The registered writer
# --------------------------------------------------------------------------- #


def _write_plan(world: Path, change_id: str = "CR-1") -> str:
    (world / IMPACT_REQUEST_REL).write_text(json.dumps({"change_id": change_id}), encoding="utf-8")
    [path] = write_impact_plan(world)
    return json.loads(path.read_text(encoding="utf-8"))["plan_id"]


class TestShadowComparisonWriter:
    def test_registered_and_claude_free(self):
        """The forbidden list is narrower than the planner's pin on purpose:
        the comparison reads the reuse layer's eligibility table and the run
        manifest layout as data (``phase8_reuse``, ``run_context``), which the
        planner never does. It still names no scheduler, gate or transport
        module and never calls the reuse metadata writer."""
        assert "dev_graph_shadow_comparison_writer" in COMPONENT_REGISTRY
        text = (find_repo_root() / "runner" / "dev_graph" / "shadow.py").read_text(encoding="utf-8")
        for forbidden in ("dag_scheduler", "gate_evaluator", "claude_transport", "write_reuse_metadata"):
            assert forbidden not in text, f"shadow.py names {forbidden}"

    def test_byte_equal_replay_through_the_registry(self, world: Path):
        _t03_moved_plan(world)
        plan_id = _write_plan(world)
        _seed_manifest(world, "run-a", {NODE: NOT_REUSED})
        (world / SHADOW_REQUEST_REL).write_text(json.dumps({"plan_id": plan_id, "run_id": "run-a"}), encoding="utf-8")

        rec = invoke_component("dev_graph_shadow_comparison_writer", "run-1", world)
        assert rec.status == "success", rec.failure_reason
        [rel] = rec.outputs_written
        assert rel.startswith(SHADOW_COMPARISONS_REL) and rel.startswith("docs/tier4_orchestration_state/")
        first = (world / rel).read_bytes()
        direct = write_shadow_comparison(world)
        assert [p.as_posix() for p in direct] == [(world / rel).as_posix()]
        rec2 = invoke_component("dev_graph_shadow_comparison_writer", "run-2", world)
        assert rec2.status == "success"
        assert (world / rel).read_bytes() == first
        doc = json.loads(first)
        assert doc["schema_id"] == SHADOW_SCHEMA_ID and doc["plan_id"] == plan_id and doc["run_id"] == "run-a"
        # The default binding (the reuse layer's table) has no run record in
        # the fixture, so the planner says rerun and agrees with not_reused.
        assert doc["diagnostic"] == "agreed"
        assert doc["rows"][0]["record_ids"] == [] and "no run record" in doc["rows"][0]["detail"]
        assert doc["comparison_id"][len(HASH_PREFIX):][:16] in rel
        assert "run_id" in doc and doc["run_id"] != "run-1"

    def test_nothing_changed_seed_writes_no_reuse_metadata(self, world: Path):
        before_reuse = _tree_bytes(world, REUSE_DIR)
        _nothing_changed_plan(world)
        plan_id = _write_plan(world, "CR-NOOP")
        manifest = _seed_manifest(world, "run-a", {NODE: NOT_REUSED})
        manifest_bytes = manifest.read_bytes()
        (world / SHADOW_REQUEST_REL).write_text(json.dumps({"plan_id": plan_id, "run_id": "run-a"}), encoding="utf-8")

        rec = invoke_component("dev_graph_shadow_comparison_writer", "run-1", world)
        assert rec.status == "success", rec.failure_reason
        doc = _load(world, rec.outputs_written[0])
        assert doc["diagnostic"] == "planner_narrower"
        assert _tree_bytes(world, REUSE_DIR) == before_reuse
        assert manifest.read_bytes() == manifest_bytes
        assert {p.name for p in (world / RUNS_DIR / "run-a").iterdir()} == {"run_manifest.json"}

    def test_missing_plan_or_manifest_refuses_and_writes_nothing(self, world: Path):
        _seed_manifest(world, "run-a", {NODE: NOT_REUSED})
        (world / SHADOW_REQUEST_REL).write_text(
            json.dumps({"plan_id": HASH_PREFIX + "0" * 64, "run_id": "run-a"}), encoding="utf-8"
        )
        rec = invoke_component("dev_graph_shadow_comparison_writer", "run-1", world)
        assert rec.status == "failure" and "plan" in (rec.failure_reason or "")
        assert not (world / SHADOW_COMPARISONS_REL).exists()

        _t03_moved_plan(world)
        plan_id = _write_plan(world)
        (world / SHADOW_REQUEST_REL).write_text(json.dumps({"plan_id": plan_id, "run_id": "run-absent"}), encoding="utf-8")
        rec = invoke_component("dev_graph_shadow_comparison_writer", "run-1", world)
        assert rec.status == "failure" and "run manifest" in (rec.failure_reason or "")
        assert not (world / SHADOW_COMPARISONS_REL).exists()

    def test_a_plan_whose_content_does_not_match_its_id_is_refused(self, world: Path):
        _t03_moved_plan(world)
        plan_id = _write_plan(world)
        plan_path = world / IMPACT_PLANS_REL / plan_id[len(HASH_PREFIX):][:16] / "plan.json"
        doc = json.loads(plan_path.read_text(encoding="utf-8"))
        doc["nothing_changed"] = True
        plan_path.write_text(json.dumps(doc), encoding="utf-8")
        _seed_manifest(world, "run-a", {NODE: NOT_REUSED})
        (world / SHADOW_REQUEST_REL).write_text(json.dumps({"plan_id": plan_id, "run_id": "run-a"}), encoding="utf-8")
        with pytest.raises(DevGraphError) as exc:
            write_shadow_comparison(world)
        assert exc.value.kind == "malformed_record"


class TestAgnosticism:
    def test_lint_covers_the_new_module(self):
        from runner.agnosticism_lint import lint_generic_layer

        report = lint_generic_layer(find_repo_root())
        assert "runner/dev_graph/shadow.py" in set(report.scanned_files)
        assert not [v for v in report.violations if v.path.startswith("runner/dev_graph/")]


class TestDecisionLog:
    def test_shadow_mode_rule_entry_exists(self):
        log = find_repo_root() / "docs/tier4_orchestration_state/decision_log"
        entries = list(log.glob("dev-graph-shadow-mode-rule_*.json"))
        assert len(entries) == 1
        rec = json.loads(entries[0].read_text(encoding="utf-8"))
        assert rec["record_type"] == "decision"
        text = json.dumps(rec)
        for diagnostic in DIAGNOSTICS:
            assert diagnostic in text
        assert "evaluate_gate" in text and "gate_09" in text
