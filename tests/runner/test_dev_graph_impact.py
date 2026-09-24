"""
Dev-graph approved change recording and the shadow impact planner.

Every test copies ``tests/fixtures/dev_graph_synthetic`` into a temporary root,
imports the fixture candidate, and drives the public ``runner.dev_graph``
entry points. The scenario is the milestone's: responsibility for task T03
moves from Participant B to Participant C. Nothing here touches a real
project, the scheduler, a gate, or the Phase 8 reuse layer.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from runner.deterministic_components import COMPONENT_REGISTRY, invoke_component
from runner.dev_graph import (
    ACTIONS,
    CHANGES_REL,
    ENTRY_KINDS,
    HITS,
    IMPACT_PLANS_REL,
    IMPACT_REQUEST_REL,
    PLAN_SCHEMA_ID,
    RECORD_VERSIONS_REL,
    RUN_RECORDS_REL,
    SNAPSHOTS_REL,
    ChangeRecord,
    DevGraphError,
    ImpactPlan,
    Snapshot,
    build_snapshot,
    import_document,
    load_snapshot,
    plan_impact,
    read_record_version,
    read_run_records,
    record_change,
    write_impact_plan,
)
from runner.dev_graph.builder import SOURCES_REL, WP_SEED_REL
from runner.dev_graph.identity import HASH_PREFIX
from runner.paths import find_repo_root

FIXTURE = find_repo_root() / "tests" / "fixtures" / "dev_graph_synthetic"
CANDIDATE = Path("docs/tier5_deliverables/candidates/synthetic_candidate.json")
REUSE_DIR = Path("docs/tier4_orchestration_state/reuse/phase8")
RUN_MANIFEST = Path(".claude/runs/run-seed/run_manifest.json")


@pytest.fixture
def world(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    shutil.copytree(FIXTURE, root)
    import_document(root, CANDIDATE)
    # Sentinels the planner must never touch: reuse metadata and a run
    # manifest carrying a reuse decision.
    (root / REUSE_DIR).mkdir(parents=True)
    (root / REUSE_DIR / "n08a_excellence_drafting.reuse.json").write_text(
        '{"sentinel": "reuse metadata"}', encoding="utf-8"
    )
    (root / RUN_MANIFEST).parent.mkdir(parents=True)
    (root / RUN_MANIFEST).write_text(
        json.dumps({"run_id": "run-seed", "reuse_decisions": {"n08a_excellence_drafting": {"reused": False}}}),
        encoding="utf-8",
    )
    return root


def _load(root: Path, rel: Path) -> dict:
    return json.loads((root / rel).read_text(encoding="utf-8"))


def _tree_bytes(root: Path, rel: Path) -> dict[str, bytes]:
    base = root / rel
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in base.rglob("*") if p.is_file()}


def _seed_with_t03_moved(root: Path) -> dict:
    seed = _load(root, WP_SEED_REL)
    t03 = next(t for t in seed["work_packages"][0]["tasks"] if t["task_id"] == "T03")
    t03["responsible_partner"] = "P-C"
    return seed


def _move_t03(root: Path, change_id: str = "CR-1") -> ChangeRecord:
    return record_change(root, WP_SEED_REL, _seed_with_t03_moved(root), change_id=change_id)


def _plan(root: Path, change: ChangeRecord) -> ImpactPlan:
    before = load_snapshot(root, change.before_snapshot_id)
    after = load_snapshot(root, change.after_snapshot_id)
    return plan_impact(before, after, read_run_records(root), change_id=change.change_id)


def _entry(plan: ImpactPlan, entry_id: str) -> dict:
    matches = [e for e in plan.entries if e["id"] == entry_id]
    assert len(matches) == 1, f"{entry_id}: {matches}"
    return matches[0]


def _passage_id(snap: Snapshot, section: str) -> str:
    return next(n["id"] for n in snap.nodes if n["type"] == "passage" and n["id"].endswith("#" + section))


# --------------------------------------------------------------------------- #
# Approved change recording
# --------------------------------------------------------------------------- #


class TestRecordChange:
    def test_old_version_stays_retrievable_and_tier3_carries_the_new_one(self, world: Path):
        original = _load(world, WP_SEED_REL)
        pristine = build_snapshot(world)
        change = _move_t03(world)

        assert change.before_snapshot_id == pristine.snapshot_id
        assert change.after_snapshot_id != pristine.snapshot_id
        assert read_record_version(world, change.before_record_version) == original
        assert _load(world, WP_SEED_REL) == _seed_with_t03_moved(FIXTURE)
        # Both snapshots are stored content-addressed and load back unchanged.
        assert load_snapshot(world, change.before_snapshot_id).snapshot_id == pristine.snapshot_id
        assert load_snapshot(world, change.after_snapshot_id).snapshot_id == change.after_snapshot_id
        assert (world / SNAPSHOTS_REL).is_dir()
        assert (world / RECORD_VERSIONS_REL).is_dir()

    def test_change_set_lists_the_assigned_to_edge_including_the_removal(self, world: Path):
        change = _move_t03(world)
        cs = change.change_set
        removed = {e["label"] for e in cs["edges"]["removed"]}
        added = {e["label"] for e in cs["edges"]["added"]}
        assert removed == {"T03 -assigned_to-> P-B"}
        assert added == {"T03 -assigned_to-> P-C"}
        changed = {c["id"]: c for c in cs["nodes"]["changed"]}
        assert changed["T03"]["kind"] == "direct"
        assert changed["T03"]["before_version"] != changed["T03"]["after_version"]
        # WP1 changed only because it contains T03; that is not a change of WP1.
        assert changed["WP1"]["kind"] == "contained"
        assert cs["nodes"]["added"] == [] and cs["nodes"]["removed"] == []

    def test_change_record_is_durable_and_immutable(self, world: Path):
        change = _move_t03(world)
        rec = _load(world, Path(CHANGES_REL) / "CR-1.json")
        assert rec["change_id"] == "CR-1"
        assert rec["approval"] == "approved"
        assert rec["before"]["snapshot_id"] == change.before_snapshot_id
        assert rec["change_set"] == change.change_set
        with pytest.raises(DevGraphError) as exc:
            record_change(world, WP_SEED_REL, _load(world, WP_SEED_REL), change_id="CR-1")
        assert exc.value.kind == "immutable_record"
        assert "CR-1" in exc.value.offender

    def test_refuses_an_unknown_record_path_and_a_bad_change_id(self, world: Path):
        with pytest.raises(DevGraphError) as exc:
            record_change(world, Path("docs/somewhere/else.json"), {}, change_id="CR-2")
        assert exc.value.kind == "malformed_request"
        with pytest.raises(DevGraphError) as exc:
            record_change(world, WP_SEED_REL, _seed_with_t03_moved(world), change_id="bad id/")
        assert exc.value.kind == "malformed_request"

    def test_an_invalid_new_version_is_rolled_back(self, world: Path):
        original_bytes = (world / WP_SEED_REL).read_bytes()
        seed = _load(world, WP_SEED_REL)
        seed["work_packages"][0]["tasks"][2]["responsible_partner"] = "P-NOBODY"
        with pytest.raises(DevGraphError) as exc:
            record_change(world, WP_SEED_REL, seed, change_id="CR-3")
        assert exc.value.kind == "dangling_edge"
        assert (world / WP_SEED_REL).read_bytes() == original_bytes
        assert not (world / CHANGES_REL / "CR-3.json").exists()

    def test_recording_the_same_content_yields_an_empty_change_set(self, world: Path):
        change = record_change(world, WP_SEED_REL, _load(world, WP_SEED_REL), change_id="CR-0")
        assert change.before_snapshot_id == change.after_snapshot_id
        assert change.change_set["edges"] == {"added": [], "removed": []}
        assert change.change_set["nodes"] == {"added": [], "removed": [], "changed": []}


# --------------------------------------------------------------------------- #
# The planner on the T03 scenario
# --------------------------------------------------------------------------- #


class TestPlanT03:
    def test_vocabularies_are_closed(self):
        assert ACTIONS == {"rerun", "reuse-under-policy", "reconsider"}
        assert HITS == {"origin", "direct", "transitive", "coverage_unknown"}
        assert ENTRY_KINDS == {"record", "passage", "evidence", "artifact", "check"}

    def test_plan_lists_task_passages_evidence_and_checks_with_reason_paths(self, world: Path):
        change = _move_t03(world)
        plan = _plan(world, change)
        after = load_snapshot(world, change.after_snapshot_id)

        assert plan.change_id == "CR-1"
        assert plan.before_snapshot_id == change.before_snapshot_id
        assert plan.after_snapshot_id == change.after_snapshot_id
        assert plan.origins == ["T03"]
        assert not plan.nothing_changed

        # The task description itself.
        task = _entry(plan, "T03")
        assert task["kind"] == "record" and task["hit"] == "origin" and task["action"] == "reconsider"

        # The responsibility table passage (S2 addresses T03) and its wording.
        s2 = _passage_id(after, "S2")
        passage = _entry(plan, s2)
        assert passage["kind"] == "passage" and passage["action"] == "reconsider"
        assert passage["reason_path"] == ["changed:T03", f"{s2} -addresses-> T03"]
        commitment = _entry(plan, s2.split("#")[0] + "#CM-1")
        assert commitment["kind"] == "evidence" and commitment["action"] == "reconsider"
        assert commitment["reason_path"][0] == "changed:T03"
        assert len(commitment["reason_path"]) == 3
        claim = _entry(plan, s2.split("#")[0] + "#CL-1")
        assert claim["kind"] == "evidence"

        # Passages that address the work package are reached through the
        # task's work package, not through the document container, and the
        # route is on record. The work package itself is not an origin.
        for section in ("S1", "S3"):
            other = _entry(plan, _passage_id(after, section))
            assert other["hit"] == "transitive"
            assert other["reason_path"][:2] == ["changed:T03", "T03 -contributes_to-> WP1"]
        assert "WP1" not in {e["id"] for e in plan.entries}
        # The document is affected as a whole; its passages are not reached
        # through it (the only route to S2's siblings is the work package).
        doc = _entry(plan, s2.split("#")[0])
        assert doc["kind"] == "artifact" and doc["action"] == "reconsider"
        doc_edge = lambda step: step.startswith(doc["id"] + " -") or step.endswith("-> " + doc["id"])  # noqa: E731
        for e in plan.entries:
            assert not any(doc_edge(step) for step in e["reason_path"][:-1]), e

        # Schedule and resource checks: direct hits, rerun.
        schedule = _entry(plan, "CHK-SCHEDULE")
        assert schedule["kind"] == "check" and schedule["action"] == "rerun" and schedule["hit"] == "direct"
        assert schedule["reason_path"] == ["changed:T03", "input_of:CHK-SCHEDULE"]
        resource = _entry(plan, "CHK-RESOURCE")
        assert resource["action"] == "rerun" and resource["hit"] == "direct"
        assert resource["reason_path"][1] in {"T03 -assigned_to-> P-B", "T03 -assigned_to-> P-C"}
        assert resource["reason_path"][-1] == "input_of:CHK-RESOURCE"

        # A check on the deliverable is reached through an unchanged edge only.
        deliverable = _entry(plan, "CHK-DELIVERABLE")
        assert deliverable["hit"] == "transitive" and deliverable["action"] == "reuse-under-policy"
        assert deliverable["reason_path"] == ["changed:T03", "T03 -produces-> D1.1", "input_of:CHK-DELIVERABLE"]

        # Every entry carries a non-empty reason path and a closed-set action.
        for e in plan.entries:
            assert e["reason_path"]
            assert e["reason_path"][0].startswith("changed:" if e["hit"] != "coverage_unknown" else "coverage_unknown:")
            assert e["action"] in ACTIONS and e["hit"] in HITS and e["kind"] in ENTRY_KINDS

    def test_unknown_dependency_coverage_yields_rerun(self, world: Path):
        change = _move_t03(world)
        plan = _plan(world, change)
        # The fixture artifact declares no inputs at all.
        art = _entry(plan, "ART-SECTION-2")
        assert art["kind"] == "artifact" and art["hit"] == "coverage_unknown" and art["action"] == "rerun"
        assert art["reason_path"] == ["coverage_unknown:ART-SECTION-2"]

    def test_a_removed_dependency_edge_makes_coverage_unknown(self, world: Path):
        seed = _load(world, WP_SEED_REL)
        t03 = next(t for t in seed["work_packages"][0]["tasks"] if t["task_id"] == "T03")
        t03["dependencies"] = []
        change = record_change(world, WP_SEED_REL, seed, change_id="CR-EDGE")
        assert {e["label"] for e in change.change_set["edges"]["removed"]} == {"T03 -consumes-> T02"}
        plan = _plan(world, change)
        schedule = _entry(plan, "CHK-SCHEDULE")
        assert schedule["hit"] == "coverage_unknown" and schedule["action"] == "rerun"
        assert "T03 -consumes-> T02" in schedule["detail"]
        # The resource check is reached over unchanged edges only.
        resource = _entry(plan, "CHK-RESOURCE")
        assert resource["hit"] == "transitive" and resource["action"] == "reuse-under-policy"

    def test_a_newly_relevant_source_is_flagged(self, world: Path):
        change = _move_t03(world)
        plan = _plan(world, change)
        flagged = {s["id"]: s for s in plan.newly_relevant_sources}
        # SRC-1 supports the claim in the responsibility passage and no run
        # record or package ever listed it.
        assert "SRC-1" in flagged
        assert flagged["SRC-1"]["reason_path"][0] == "changed:T03"
        assert flagged["SRC-1"]["reason_path"][-1].endswith("-supported_by-> SRC-1")
        # SRC-2 is reachable too but the deliverable check's package included it.
        assert "SRC-2" not in flagged

    def test_a_source_that_enters_scope_with_the_change_is_flagged(self, world: Path):
        # A new source is registered, then the work package is constrained by
        # it. The plan for the second change flags the source: it is reached
        # from the changed work package and no run record or package lists it.
        sources = _load(world, SOURCES_REL)
        sources["sources"].append(
            {"source_id": "SRC-3", "title": "Source three", "kind": "partner_input", "text": "Participant C provides the test bed."}
        )
        record_change(world, SOURCES_REL, sources, change_id="CR-SRC")
        seed = _load(world, WP_SEED_REL)
        seed["work_packages"][0]["constraints"].append("SRC-3")
        change = record_change(world, WP_SEED_REL, seed, change_id="CR-CONSTRAINT")
        assert {e["label"] for e in change.change_set["edges"]["added"]} == {"WP1 -constrained_by-> SRC-3"}
        plan = _plan(world, change)
        flagged = {s["id"]: s for s in plan.newly_relevant_sources}
        assert flagged["SRC-3"]["reason_path"] == ["changed:WP1", "WP1 -constrained_by-> SRC-3"]
        assert "SRC-2" not in flagged

    def test_the_walk_honours_the_planning_view_policy(self, world: Path, monkeypatch: pytest.MonkeyPatch):
        from runner.dev_graph import impact as impact_module
        from runner.dev_graph.policies import ViewPolicy

        change = _move_t03(world)
        narrow = ViewPolicy(
            "change_impact_planning",
            permitted_types=frozenset({"task", "participant", "passage"}),
            permitted_traversals=frozenset({"assigned_to", "addresses"}),
            max_depth=4,
        )
        monkeypatch.setitem(impact_module.VIEW_POLICIES, "change_impact_planning", narrow)
        plan = _plan(world, change)
        after = load_snapshot(world, change.after_snapshot_id)
        listed = {e["id"] for e in plan.entries}
        assert _passage_id(after, "S2") in listed
        # Not permitted: evidence behind expressed_in, passages behind the
        # work package, the deliverable check behind produces.
        assert not any(e["kind"] == "evidence" for e in plan.entries)
        assert _passage_id(after, "S1") not in listed
        assert "CHK-DELIVERABLE" not in listed
        assert plan.newly_relevant_sources == []

    def test_no_change_yields_an_empty_plan(self, world: Path):
        change = record_change(world, WP_SEED_REL, _load(world, WP_SEED_REL), change_id="CR-0")
        plan = _plan(world, change)
        assert plan.nothing_changed
        assert plan.origins == []
        # Unknown coverage is still reported: a missing input record never
        # becomes "unchanged" by silence.
        assert [e["id"] for e in plan.entries] == ["ART-SECTION-2"]
        assert plan.newly_relevant_sources == []

    def test_identical_inputs_yield_the_same_plan_id(self, world: Path):
        change = _move_t03(world)
        assert _plan(world, change).plan_id == _plan(world, change).plan_id


# --------------------------------------------------------------------------- #
# Refusals: a broken index never yields a narrower plan
# --------------------------------------------------------------------------- #


class TestRefusals:
    def test_missing_snapshot_is_refused(self, world: Path):
        change = _move_t03(world)
        with pytest.raises(DevGraphError) as exc:
            load_snapshot(world, HASH_PREFIX + "0" * 64)
        assert exc.value.kind == "missing_snapshot"
        after = load_snapshot(world, change.after_snapshot_id)
        with pytest.raises(DevGraphError) as exc:
            plan_impact(None, after, read_run_records(world), change_id="CR-1")  # type: ignore[arg-type]
        assert exc.value.kind == "malformed_snapshot"

    def test_tampered_snapshot_is_refused(self, world: Path):
        change = _move_t03(world)
        hexid = change.before_snapshot_id[len(HASH_PREFIX):]
        path = world / SNAPSHOTS_REL / f"{hexid}.json"
        doc = json.loads(path.read_text(encoding="utf-8"))
        doc["nodes"] = [n for n in doc["nodes"] if n["id"] != "T03"]
        doc["edges"] = [e for e in doc["edges"] if "T03" not in (e["source"]["id"], e["target"]["id"])]
        path.write_text(json.dumps(doc), encoding="utf-8")
        with pytest.raises(DevGraphError) as exc:
            load_snapshot(world, change.before_snapshot_id)
        assert exc.value.kind == "malformed_snapshot"

    def test_malformed_run_records_are_refused(self, world: Path):
        change = _move_t03(world)
        (world / RUN_RECORDS_REL).write_text('{"records": [{"kind": "check"}]}', encoding="utf-8")
        with pytest.raises(DevGraphError) as exc:
            read_run_records(world)
        assert exc.value.kind == "malformed_record"
        before = load_snapshot(world, change.before_snapshot_id)
        after = load_snapshot(world, change.after_snapshot_id)
        with pytest.raises(DevGraphError):
            plan_impact(before, after, [{"record_id": "X"}], change_id="CR-1")

    def test_component_refuses_a_missing_snapshot_and_writes_nothing(self, world: Path):
        change = _move_t03(world)
        (world / SNAPSHOTS_REL / f"{change.before_snapshot_id[len(HASH_PREFIX):]}.json").unlink()
        (world / IMPACT_REQUEST_REL).write_text(json.dumps({"change_id": "CR-1"}), encoding="utf-8")
        rec = invoke_component("dev_graph_impact_plan_writer", "run-1", world)
        assert rec.status == "failure"
        assert "missing_snapshot" in (rec.failure_reason or "")
        assert not (world / IMPACT_PLANS_REL).exists()


# --------------------------------------------------------------------------- #
# The registered writer
# --------------------------------------------------------------------------- #


class TestImpactPlanWriter:
    def test_registered_and_claude_free(self):
        assert "dev_graph_impact_plan_writer" in COMPONENT_REGISTRY

    def test_byte_equal_replay_through_the_registry(self, world: Path):
        _move_t03(world)
        (world / IMPACT_REQUEST_REL).write_text(json.dumps({"change_id": "CR-1"}), encoding="utf-8")
        rec = invoke_component("dev_graph_impact_plan_writer", "run-1", world)
        assert rec.status == "success", rec.failure_reason
        assert len(rec.outputs_written) == 1
        plan_rel = rec.outputs_written[0]
        assert plan_rel.startswith(IMPACT_PLANS_REL)
        assert plan_rel.startswith("docs/tier4_orchestration_state/")
        first = (world / plan_rel).read_bytes()
        direct = write_impact_plan(world)
        assert [p.as_posix() for p in direct] == [(world / plan_rel).as_posix()]
        rec2 = invoke_component("dev_graph_impact_plan_writer", "run-2", world)
        assert rec2.status == "success"
        assert (world / plan_rel).read_bytes() == first
        doc = json.loads(first)
        assert doc["schema_id"] == PLAN_SCHEMA_ID
        assert doc["advisory"] is True and doc["mode"] == "shadow"
        assert doc["plan_id"][len(HASH_PREFIX):][:16] in plan_rel
        assert "run_id" not in doc

    def test_reuse_metadata_and_run_manifest_are_untouched(self, world: Path):
        before_reuse = _tree_bytes(world, REUSE_DIR)
        before_runs = _tree_bytes(world, Path(".claude/runs"))
        _move_t03(world)
        (world / IMPACT_REQUEST_REL).write_text(json.dumps({"change_id": "CR-1"}), encoding="utf-8")
        assert invoke_component("dev_graph_impact_plan_writer", "run-1", world).status == "success"
        assert _tree_bytes(world, REUSE_DIR) == before_reuse
        assert _tree_bytes(world, Path(".claude/runs")) == before_runs

    def test_planner_modules_import_no_scheduler_or_reuse_layer(self):
        pkg = find_repo_root() / "runner" / "dev_graph"
        for name in ("impact.py", "changes.py"):
            text = (pkg / name).read_text(encoding="utf-8")
            for forbidden in ("dag_scheduler", "phase8_reuse", "run_context", "gate_evaluator", "claude_transport"):
                assert forbidden not in text, f"{name} names {forbidden}"


class TestAgnosticism:
    def test_lint_covers_the_new_modules(self):
        from runner.agnosticism_lint import lint_generic_layer

        report = lint_generic_layer(find_repo_root())
        scanned = set(report.scanned_files)
        assert {"runner/dev_graph/impact.py", "runner/dev_graph/changes.py"} <= scanned
        assert not [v for v in report.violations if v.path.startswith("runner/dev_graph/")]


class TestDecisionLog:
    def test_impact_planner_entry_exists_and_names_the_actions(self):
        log = find_repo_root() / "docs/tier4_orchestration_state/decision_log"
        entries = list(log.glob("dev-graph-impact-planner_*.json"))
        assert len(entries) == 1
        rec = json.loads(entries[0].read_text(encoding="utf-8"))
        assert rec["record_type"] == "decision"
        assert set(rec["planner"]["hit_and_action"]) == HITS
        for action in ACTIONS:
            assert action in json.dumps(rec)
