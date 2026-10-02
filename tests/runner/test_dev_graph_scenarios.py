"""
Dev-graph change scenarios: scripted approved changes, their advisory and
their shadow comparison.

Every test works on a copy of ``tests/fixtures/dev_graph_synthetic``, whose
Tier 3 set is the handoff's T03 world: three participants, one work package,
tasks T01 to T03, one deliverable, one milestone and two sources. Nothing
here dispatches a phase, evaluates a gate or writes reuse metadata.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from runner.dev_graph.builder import build_snapshot
from runner.dev_graph.documents import import_document
from runner.dev_graph.impact import plan_identity
from runner.dev_graph.scenarios import (
    SCENARIO_SCHEMA_ID,
    SCENARIOS_REL,
    Arm,
    Scenario,
    ScenarioResult,
    apply_transform,
    materialise_sandbox,
    run_scenario,
    shadow_label,
    write_scenario_records,
)
from runner.dev_graph.schema import DevGraphError
from runner.dev_graph.shadow import DIAGNOSTICS
from runner.paths import find_repo_root

FIXTURE = find_repo_root() / "tests" / "fixtures" / "dev_graph_synthetic"
CANDIDATE = "docs/tier5_deliverables/candidates/synthetic_candidate.json"
WP_SEED = "docs/tier3_project_instantiation/architecture_inputs/workpackage_seed.json"
PARTNERS = "docs/tier3_project_instantiation/consortium/partners.json"
SOURCES = "docs/tier3_project_instantiation/source_materials/sources.json"


@pytest.fixture()
def world(tmp_path: Path) -> Path:
    """A writable copy of the synthetic fixture tree."""
    root = tmp_path / "world"
    shutil.copytree(FIXTURE, root)
    return root


def _read(root: Path, rel: str) -> dict:
    return json.loads((root / rel).read_text(encoding="utf-8-sig"))


def _task(content: dict, task_id: str) -> dict:
    return next(
        t
        for wp in content["work_packages"]
        for t in wp["tasks"]
        if t["task_id"] == task_id
    )


class TestMoveTaskResponsibility:
    """The handoff's first operational milestone: T03 moves from B to C."""

    def test_hands_the_task_to_its_first_contributing_partner(self, world: Path) -> None:
        content = _read(world, WP_SEED)

        new = apply_transform("move_task_responsibility", content, {"task_id": "T03"})

        assert _task(content, "T03")["responsible_partner"] == "P-B"
        assert _task(new, "T03")["responsible_partner"] == "P-C"

    def test_swaps_the_two_roles_and_keeps_the_partner_set(self, world: Path) -> None:
        # No task in these records lists its lead among its contributors, and
        # the move must isolate the responsibility change: the same two
        # partners stay on the task, with their roles exchanged.
        new = apply_transform("move_task_responsibility", _read(world, WP_SEED), {"task_id": "T03"})

        assert _task(new, "T03")["contributing_partners"] == ["P-B"]

    def test_leaves_the_content_it_was_given_untouched(self, world: Path) -> None:
        content = _read(world, WP_SEED)
        before = json.dumps(content, sort_keys=True)

        apply_transform("move_task_responsibility", content, {"task_id": "T03"})

        assert json.dumps(content, sort_keys=True) == before

    def test_refuses_an_unknown_task(self, world: Path) -> None:
        with pytest.raises(DevGraphError) as exc:
            apply_transform("move_task_responsibility", _read(world, WP_SEED), {"task_id": "T99"})

        assert exc.value.kind == "malformed_request"
        assert "T99" in str(exc.value)

    def test_refuses_a_task_with_no_contributing_partner_to_hand_it_to(self, world: Path) -> None:
        # T02 carries an empty contributing list, so there is no declared
        # partner to move the task to and nothing may be invented (§13.3).
        with pytest.raises(DevGraphError) as exc:
            apply_transform("move_task_responsibility", _read(world, WP_SEED), {"task_id": "T02"})

        assert exc.value.kind == "malformed_request"
        assert "T02" in str(exc.value)


class TestReleasePartnerFromWorkPlan:
    """The first step of a withdrawal: the work plan stops naming the partner."""

    def test_drops_the_partner_from_every_contributing_list(self, world: Path) -> None:
        new = apply_transform(
            "release_partner_from_work_plan", _read(world, WP_SEED), {"partner_id": "P-C"}
        )

        assert _task(new, "T03")["contributing_partners"] == []

    def test_hands_a_task_the_partner_led_to_its_first_contributor(self, world: Path) -> None:
        new = apply_transform(
            "release_partner_from_work_plan", _read(world, WP_SEED), {"partner_id": "P-A"}
        )

        assert _task(new, "T01")["responsible_partner"] == "P-B"
        assert _task(new, "T01")["contributing_partners"] == []

    def test_refuses_when_the_work_plan_never_named_the_partner(self, world: Path) -> None:
        with pytest.raises(DevGraphError) as exc:
            apply_transform(
                "release_partner_from_work_plan", _read(world, WP_SEED), {"partner_id": "P-Z"}
            )

        assert exc.value.kind == "malformed_request"
        assert "P-Z" in str(exc.value)

    def test_refuses_when_a_task_it_leads_has_no_other_partner(self, world: Path) -> None:
        # T02 is led by P-B and lists no contributor, so releasing P-B would
        # leave the task unassigned. A withdrawal that cannot be expressed
        # must refuse, not leave a hole.
        with pytest.raises(DevGraphError) as exc:
            apply_transform(
                "release_partner_from_work_plan", _read(world, WP_SEED), {"partner_id": "P-B"}
            )

        assert exc.value.kind == "malformed_request"
        assert "T02" in str(exc.value)

    def test_leaves_the_work_package_it_leads_unchanged(self, world: Path) -> None:
        # The transformation covers task roles only. A partner that leads a
        # work package is a separate fact, and a silent reassignment there
        # would hide the structural refusal the scenario is meant to show.
        new = apply_transform(
            "release_partner_from_work_plan", _read(world, WP_SEED), {"partner_id": "P-A"}
        )

        assert new["work_packages"][0]["lead_partner"] == "P-A"


class TestRemovePartner:
    """The second step of a withdrawal: the consortium record drops the entry."""

    def test_drops_the_partner_entry(self, world: Path) -> None:
        new = apply_transform("remove_partner", _read(world, PARTNERS), {"partner_id": "P-C"})

        assert [p["partner_id"] for p in new["partners"]] == ["P-A", "P-B"]

    def test_refuses_a_partner_the_record_does_not_hold(self, world: Path) -> None:
        with pytest.raises(DevGraphError) as exc:
            apply_transform("remove_partner", _read(world, PARTNERS), {"partner_id": "P-Z"})

        assert exc.value.kind == "malformed_request"
        assert "P-Z" in str(exc.value)


class TestSetPartnerField:
    """A gap partner's participation is confirmed, or its status is corrected."""

    def test_sets_the_declared_field(self, world: Path) -> None:
        new = apply_transform(
            "set_partner_field",
            _read(world, PARTNERS),
            {"partner_id": "P-C", "field": "participation_status", "value": "Confirmed"},
        )

        entry = next(p for p in new["partners"] if p["partner_id"] == "P-C")
        assert entry["participation_status"] == "Confirmed"

    def test_refuses_when_the_field_already_holds_that_value(self, world: Path) -> None:
        # A scenario must change something. A set that is already true would
        # make the arm a silent no-op.
        content = _read(world, PARTNERS)
        next(p for p in content["partners"] if p["partner_id"] == "P-C")["x"] = "y"

        with pytest.raises(DevGraphError) as exc:
            apply_transform(
                "set_partner_field",
                content,
                {"partner_id": "P-C", "field": "x", "value": "y"},
            )

        assert exc.value.kind == "malformed_request"


class TestSourceTransforms:
    """Two changes to a source: its own status, and a span it declares."""

    def test_set_source_field_sets_the_declared_field(self, world: Path) -> None:
        new = apply_transform(
            "set_source_field",
            _read(world, SOURCES),
            {"source_id": "SRC-2", "field": "status", "value": "Unresolved"},
        )

        assert next(s for s in new["sources"] if s["source_id"] == "SRC-2")["status"] == "Unresolved"

    def test_drop_source_span_removes_the_named_span(self, world: Path) -> None:
        content = _read(world, SOURCES)
        source = next(s for s in content["sources"] if s["source_id"] == "SRC-1")
        source["spans"] = [{"span_id": "SRC-1#0-13"}, {"span_id": "SRC-1#14-20"}]

        new = apply_transform(
            "drop_source_span", content, {"source_id": "SRC-1", "span_id": "SRC-1#0-13"}
        )

        kept = next(s for s in new["sources"] if s["source_id"] == "SRC-1")["spans"]
        assert [s["span_id"] for s in kept] == ["SRC-1#14-20"]

    def test_drop_source_span_refuses_a_span_the_source_does_not_declare(self, world: Path) -> None:
        with pytest.raises(DevGraphError) as exc:
            apply_transform(
                "drop_source_span", _read(world, SOURCES), {"source_id": "SRC-1", "span_id": "SRC-1#9-9"}
            )

        assert exc.value.kind == "malformed_request"
        assert "SRC-1#9-9" in str(exc.value)


class TestMoveDeliverableDueMonth:
    """A deliverable's month moves, which may cross the milestone that checks it."""

    def test_moves_the_month(self, world: Path) -> None:
        new = apply_transform(
            "move_deliverable_due_month", _read(world, WP_SEED), {"deliverable_id": "D1.1", "to_month": 19}
        )

        deliverable = new["work_packages"][0]["deliverables"][0]
        assert deliverable["due_month"] == 19

    def test_refuses_a_month_the_deliverable_already_holds(self, world: Path) -> None:
        with pytest.raises(DevGraphError) as exc:
            apply_transform(
                "move_deliverable_due_month",
                _read(world, WP_SEED),
                {"deliverable_id": "D1.1", "to_month": 18},
            )

        assert exc.value.kind == "malformed_request"


class TestAddWorkPackageObjective:
    """The probe that must meet a protected objective."""

    def test_adds_the_objective_to_the_work_package(self, world: Path) -> None:
        content = _read(world, WP_SEED)
        content["work_packages"][0]["objectives"] = ["OBJ-2"]

        new = apply_transform(
            "add_work_package_objective", content, {"wp_id": "WP1", "objective_id": "OBJ-1"}
        )

        assert new["work_packages"][0]["objectives"] == ["OBJ-1", "OBJ-2"]

    def test_refuses_an_objective_the_work_package_already_carries(self, world: Path) -> None:
        with pytest.raises(DevGraphError) as exc:
            apply_transform(
                "add_work_package_objective",
                _read(world, WP_SEED),
                {"wp_id": "WP1", "objective_id": "OBJ-1"},
            )

        assert exc.value.kind == "malformed_request"


class TestMaterialiseSandbox:
    """The frozen world is copied, never edited in place."""

    def test_the_sandbox_reproduces_the_live_snapshot_id(self, world: Path, tmp_path: Path) -> None:
        import_document(world, CANDIDATE, state="draft")
        live = build_snapshot(world)

        sandbox = materialise_sandbox(world, tmp_path / "sandbox")

        assert sandbox.snapshot.snapshot_id == live.snapshot_id

    def test_the_sandbox_holds_the_snapshot_inputs_and_nothing_else(
        self, world: Path, tmp_path: Path
    ) -> None:
        import_document(world, CANDIDATE, state="draft")
        live = build_snapshot(world)

        sandbox = materialise_sandbox(world, tmp_path / "sandbox")

        copied = sorted(
            p.relative_to(sandbox.root).as_posix()
            for p in sandbox.root.rglob("*")
            if p.is_file()
        )
        assert copied == sorted(live.inputs)

    def test_a_change_in_the_sandbox_leaves_the_world_untouched(
        self, world: Path, tmp_path: Path
    ) -> None:
        before = (world / WP_SEED).read_bytes()
        sandbox = materialise_sandbox(world, tmp_path / "sandbox")

        content = apply_transform(
            "move_task_responsibility",
            json.loads((sandbox.root / WP_SEED).read_text(encoding="utf-8-sig")),
            {"task_id": "T03"},
        )
        (sandbox.root / WP_SEED).write_text(json.dumps(content), encoding="utf-8")

        assert (world / WP_SEED).read_bytes() == before

    def test_refuses_a_destination_that_already_holds_records(
        self, world: Path, tmp_path: Path
    ) -> None:
        dest = tmp_path / "sandbox"
        materialise_sandbox(world, dest)

        with pytest.raises(DevGraphError) as exc:
            materialise_sandbox(world, dest)

        assert exc.value.kind == "malformed_request"

    def test_refuses_a_world_whose_snapshot_has_no_inputs(self, tmp_path: Path) -> None:
        # An empty world builds an empty snapshot. Copying nothing and
        # calling it a sandbox would make every later arm vacuous.
        with pytest.raises(DevGraphError) as exc:
            materialise_sandbox(tmp_path / "empty", tmp_path / "sandbox")

        assert exc.value.kind == "malformed_request"


#: The fixture's own section artifact, which its run records name.
SECTION_PATH = "docs/tier5_deliverables/proposal_sections/synthetic_section_two.json"
RUN_WITH_DECISION = "run-with-decision"
RUN_WITHOUT_DECISION = "run-without-decision"


def _seed_run(root: Path, run_id: str, decisions: dict | None) -> None:
    """Write a run manifest the shadow comparison can read."""
    manifest: dict[str, object] = {"run_id": run_id, "node_states": {}}
    if decisions is not None:
        manifest["reuse_decisions"] = decisions
    path = root / ".claude" / "runs" / run_id / "run_manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest), encoding="utf-8")


def _tree(root: Path) -> dict[str, bytes]:
    return {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def _move_t03() -> Scenario:
    return Scenario(
        scenario_id="responsibility_move",
        title="Task T03 moves to its contributing partner",
        purpose="The handoff's first operational milestone at this world's scale.",
        contract={
            "contract_id": "responsibility_only",
            "permitted_change_classes": ["responsibility", "contribution"],
            "protected_node_ids": ["OBJ-1", "OBJ-2"],
        },
        arms=(
            Arm(
                arm_id="a1_move",
                kind="change",
                record_path=WP_SEED,
                transform="move_task_responsibility",
                args={"task_id": "T03"},
                expects="recorded",
                purpose="The responsibility moves and the objective is untouched.",
            ),
        ),
    )


@pytest.fixture()
def planning_world(world: Path) -> Path:
    """The fixture world with its candidate imported and two runs seeded."""
    import_document(world, CANDIDATE, state="draft")
    _seed_run(
        world,
        RUN_WITH_DECISION,
        {"n08a_excellence_drafting": {"status": "reused", "artifact_path": SECTION_PATH}},
    )
    _seed_run(world, RUN_WITHOUT_DECISION, None)
    return world


class TestRunScenario:
    """One arm: record the change, check the contract, plan, compare."""

    def test_records_the_change_and_meets_the_expectation(
        self, planning_world: Path, tmp_path: Path
    ) -> None:
        result = run_scenario(
            planning_world,
            _move_t03(),
            tmp_path / "sandbox",
            run_ids=(RUN_WITH_DECISION,),
        )

        arm = result.arms[0]
        assert arm.outcome == "recorded"
        assert arm.expectation_met is True

    def test_the_advisory_carries_a_non_empty_reason_path_for_every_entry(
        self, planning_world: Path, tmp_path: Path
    ) -> None:
        result = run_scenario(
            planning_world, _move_t03(), tmp_path / "sandbox", run_ids=(RUN_WITH_DECISION,)
        )

        plan = result.arms[0].plan
        assert plan is not None
        assert plan.entries
        assert all(e["reason_path"] for e in plan.entries)

    def test_the_contract_verdict_is_recorded(
        self, planning_world: Path, tmp_path: Path
    ) -> None:
        result = run_scenario(
            planning_world, _move_t03(), tmp_path / "sandbox", run_ids=(RUN_WITH_DECISION,)
        )

        check = result.arms[0].check
        assert check is not None
        assert check.verdict == "accepted"
        assert check.change_classes == ("contribution", "responsibility")

    def test_one_shadow_comparison_per_named_run(
        self, planning_world: Path, tmp_path: Path
    ) -> None:
        result = run_scenario(
            planning_world,
            _move_t03(),
            tmp_path / "sandbox",
            run_ids=(RUN_WITH_DECISION, RUN_WITHOUT_DECISION),
        )

        shadow = result.arms[0].shadow
        assert [s["run_id"] for s in shadow] == [RUN_WITH_DECISION, RUN_WITHOUT_DECISION]
        assert shadow[0]["diagnostic"] in DIAGNOSTICS

    def test_a_run_with_no_recorded_decision_is_a_recorded_refusal(
        self, planning_world: Path, tmp_path: Path
    ) -> None:
        # The comparison refuses rather than reporting agreement over an
        # empty decision set. That refusal is the result, not an error.
        result = run_scenario(
            planning_world,
            _move_t03(),
            tmp_path / "sandbox",
            run_ids=(RUN_WITHOUT_DECISION,),
        )

        shadow = result.arms[0].shadow[0]
        assert shadow.get("diagnostic") is None
        assert shadow["refused"]["kind"] == "malformed_request"

    def test_the_world_is_byte_for_byte_unchanged(
        self, planning_world: Path, tmp_path: Path
    ) -> None:
        before = _tree(planning_world)

        run_scenario(
            planning_world, _move_t03(), tmp_path / "sandbox", run_ids=(RUN_WITH_DECISION,)
        )

        assert _tree(planning_world) == before

    def test_two_sandboxes_yield_the_same_record(
        self, planning_world: Path, tmp_path: Path
    ) -> None:
        first = run_scenario(
            planning_world, _move_t03(), tmp_path / "one", run_ids=(RUN_WITH_DECISION,)
        )
        second = run_scenario(
            planning_world, _move_t03(), tmp_path / "two", run_ids=(RUN_WITH_DECISION,)
        )

        assert first.to_dict() == second.to_dict()


class TestRunScenarioRefusalProbe:
    """An arm whose point is the refusal the operator expects."""

    def _withdrawal(self) -> Scenario:
        return Scenario(
            scenario_id="withdrawal",
            title="A partner withdraws",
            purpose="A withdrawal the work plan still names cannot be one change.",
            contract={
                "contract_id": "withdrawal",
                "permitted_change_classes": ["participant", "contribution", "responsibility"],
                "protected_node_ids": ["OBJ-1"],
            },
            arms=(
                Arm(
                    arm_id="a1_direct",
                    kind="refusal_probe",
                    record_path=PARTNERS,
                    transform="remove_partner",
                    args={"partner_id": "P-C"},
                    expects="dangling_edge",
                    purpose="The work plan still names the partner.",
                ),
                Arm(
                    arm_id="a2_release",
                    kind="change",
                    record_path=WP_SEED,
                    transform="release_partner_from_work_plan",
                    args={"partner_id": "P-C"},
                    expects="recorded",
                    purpose="The work plan releases the partner first.",
                ),
                Arm(
                    arm_id="a3_remove",
                    kind="change",
                    record_path=PARTNERS,
                    transform="remove_partner",
                    args={"partner_id": "P-C"},
                    expects="recorded",
                    purpose="The consortium record then drops the entry.",
                ),
            ),
        )

    def test_the_probe_records_the_refusal_it_expected(
        self, planning_world: Path, tmp_path: Path
    ) -> None:
        result = run_scenario(
            planning_world, self._withdrawal(), tmp_path / "sandbox", run_ids=()
        )

        probe = result.arms[0]
        assert probe.outcome == "refused"
        assert probe.refusal is not None
        assert probe.refusal["kind"] == "dangling_edge"
        assert probe.expectation_met is True

    def test_the_probe_leaves_the_sandbox_snapshot_where_it_was(
        self, planning_world: Path, tmp_path: Path
    ) -> None:
        result = run_scenario(
            planning_world, self._withdrawal(), tmp_path / "sandbox", run_ids=()
        )

        assert result.arms[0].sandbox_snapshot_id == result.before_snapshot_id

    def test_the_two_step_route_then_records_both_arms(
        self, planning_world: Path, tmp_path: Path
    ) -> None:
        result = run_scenario(
            planning_world, self._withdrawal(), tmp_path / "sandbox", run_ids=()
        )

        assert [a.outcome for a in result.arms] == ["refused", "recorded", "recorded"]
        assert all(a.expectation_met for a in result.arms)

    def test_an_expectation_the_arm_does_not_meet_is_recorded_not_raised(
        self, planning_world: Path, tmp_path: Path
    ) -> None:
        scenario = Scenario(
            scenario_id="wrong_expectation",
            title="A probe that does not refuse",
            purpose="A scenario record must say when its own expectation failed.",
            contract={"contract_id": "any", "permitted_change_classes": [], "protected_node_ids": []},
            arms=(
                Arm(
                    arm_id="a1",
                    kind="refusal_probe",
                    record_path=WP_SEED,
                    transform="move_task_responsibility",
                    args={"task_id": "T03"},
                    expects="dangling_edge",
                    purpose="This change is admissible, so the probe is wrong.",
                ),
            ),
        )

        result = run_scenario(planning_world, scenario, tmp_path / "sandbox", run_ids=())

        assert result.arms[0].outcome == "recorded"
        assert result.arms[0].expectation_met is False


class TestRunScenarioProtectedObjective:
    """Criterion 4: a change that touches a protected objective is rejected."""

    def test_the_rejection_names_the_protected_node(
        self, planning_world: Path, tmp_path: Path
    ) -> None:
        content = _read(planning_world, WP_SEED)
        content["work_packages"][0]["objectives"] = ["OBJ-2"]
        (planning_world / WP_SEED).write_text(json.dumps(content), encoding="utf-8")
        scenario = Scenario(
            scenario_id="protected_objective",
            title="A work package starts serving a protected objective",
            purpose="The contract protects the objective, so the change is rejected.",
            contract={
                "contract_id": "objective_protected",
                "permitted_change_classes": ["contribution"],
                "protected_node_ids": ["OBJ-1"],
            },
            arms=(
                Arm(
                    arm_id="a1",
                    kind="change",
                    record_path=WP_SEED,
                    transform="add_work_package_objective",
                    args={"wp_id": "WP1", "objective_id": "OBJ-1"},
                    expects="recorded",
                    purpose="The added contributes_to edge names the protected objective.",
                ),
            ),
        )

        result = run_scenario(planning_world, scenario, tmp_path / "sandbox", run_ids=())

        check = result.arms[0].check
        assert check is not None
        assert check.verdict == "rejected"
        assert [h["node_id"] for h in check.protected_hits] == ["OBJ-1"]


class TestCheckArm:
    """A malformed arm raises; it is never recorded as the refusal it declared."""

    def _probe(self, **over: Any) -> Scenario:
        arm: dict[str, Any] = {
            "arm_id": "a1",
            "kind": "refusal_probe",
            "record_path": "docs/tier3_project_instantiation/call_binding/selected_call.json",
            "transform": None,
            "args": {},
            "payload": {"record_type": "selected_call"},
            "expects": "malformed_request",
            "purpose": "The change recorder does not cover the call binding.",
        }
        arm.update(over)
        return Scenario(
            scenario_id="probe",
            title="A probe",
            purpose="A probe.",
            contract={"contract_id": "any", "permitted_change_classes": [], "protected_node_ids": []},
            arms=(Arm(**arm),),
        )

    def test_a_record_path_the_change_recorder_does_not_cover_is_a_real_refusal(
        self, planning_world: Path, tmp_path: Path
    ) -> None:
        result = run_scenario(planning_world, self._probe(), tmp_path / "sandbox", run_ids=())

        assert result.arms[0].outcome == "refused"
        assert result.arms[0].refusal is not None
        assert result.arms[0].expectation_met is True

    def test_a_misspelled_record_path_raises_instead_of_passing_the_probe(
        self, planning_world: Path, tmp_path: Path
    ) -> None:
        # Both paths make the change recorder refuse with malformed_request, so
        # without this check the probe would report expectation_met on a typo
        # and the record would claim the engine declined a fact nobody named.
        scenario = self._probe(record_path="docs/tier3_project_instantiation/call_binding/selected_cal.json")

        with pytest.raises(DevGraphError) as exc:
            run_scenario(planning_world, scenario, tmp_path / "sandbox", run_ids=())

        assert exc.value.kind == "malformed_request"
        assert "selected_cal.json" in str(exc.value)

    def test_refuses_an_arm_that_offers_both_a_transform_and_a_payload(
        self, planning_world: Path, tmp_path: Path
    ) -> None:
        scenario = self._probe(transform="remove_partner", args={"partner_id": "P-C"})

        with pytest.raises(DevGraphError) as exc:
            run_scenario(planning_world, scenario, tmp_path / "sandbox", run_ids=())

        assert exc.value.kind == "malformed_request"

    def test_refuses_an_arm_that_offers_neither(
        self, planning_world: Path, tmp_path: Path
    ) -> None:
        scenario = self._probe(payload=None)

        with pytest.raises(DevGraphError) as exc:
            run_scenario(planning_world, scenario, tmp_path / "sandbox", run_ids=())

        assert exc.value.kind == "malformed_request"

    def test_refuses_a_change_arm_that_expects_a_refusal(
        self, planning_world: Path, tmp_path: Path
    ) -> None:
        # The kind and the expectation must agree, or the record's own
        # vocabulary stops meaning anything.
        scenario = self._probe(kind="change")

        with pytest.raises(DevGraphError) as exc:
            run_scenario(planning_world, scenario, tmp_path / "sandbox", run_ids=())

        assert exc.value.kind == "malformed_request"
        assert "a1" in str(exc.value)

    def test_refuses_a_refusal_probe_that_expects_a_recorded_change(
        self, planning_world: Path, tmp_path: Path
    ) -> None:
        scenario = self._probe(expects="recorded")

        with pytest.raises(DevGraphError) as exc:
            run_scenario(planning_world, scenario, tmp_path / "sandbox", run_ids=())

        assert exc.value.kind == "malformed_request"

    def test_refuses_an_unknown_arm_kind(
        self, planning_world: Path, tmp_path: Path
    ) -> None:
        scenario = self._probe(kind="experiment")

        with pytest.raises(DevGraphError) as exc:
            run_scenario(planning_world, scenario, tmp_path / "sandbox", run_ids=())

        assert exc.value.kind == "malformed_request"
        assert "experiment" in str(exc.value)


class TestShadowLabel:
    def test_a_made_comparison_reads_as_its_diagnostic(self) -> None:
        assert shadow_label({"diagnostic": "agreed"}) == "agreed"

    def test_a_refusal_reads_as_its_kind(self) -> None:
        assert (
            shadow_label({"refused": {"kind": "malformed_request"}})
            == "refused:malformed_request"
        )


class TestWriteScenarioRecords:
    """The one durable write: a record per scenario, an advisory per arm."""

    def _results(self, world: Path, tmp_path: Path) -> list[ScenarioResult]:
        return [
            run_scenario(
                world, _move_t03(), tmp_path / "sandbox", run_ids=(RUN_WITH_DECISION,)
            )
        ]

    def test_writes_one_record_and_one_advisory(
        self, planning_world: Path, tmp_path: Path
    ) -> None:
        written = write_scenario_records(
            planning_world, self._results(planning_world, tmp_path)
        )

        rel = sorted(p.relative_to(planning_world).as_posix() for p in written)
        assert rel == [
            f"{SCENARIOS_REL}/index.json",
            f"{SCENARIOS_REL}/responsibility_move/a1_move/plan.json",
            f"{SCENARIOS_REL}/responsibility_move/scenario.json",
        ]

    def test_the_advisory_is_the_plan_document_the_component_writes(
        self, planning_world: Path, tmp_path: Path
    ) -> None:
        results = self._results(planning_world, tmp_path)
        write_scenario_records(planning_world, results)

        written = json.loads(
            (
                planning_world / SCENARIOS_REL / "responsibility_move" / "a1_move" / "plan.json"
            ).read_text(encoding="utf-8-sig")
        )
        plan = results[0].arms[0].plan
        assert plan is not None
        assert written == plan.to_dict()
        assert plan_identity(written) == written["plan_id"]

    def test_the_record_points_at_its_advisory(
        self, planning_world: Path, tmp_path: Path
    ) -> None:
        write_scenario_records(planning_world, self._results(planning_world, tmp_path))

        record = json.loads(
            (planning_world / SCENARIOS_REL / "responsibility_move" / "scenario.json").read_text(
                encoding="utf-8-sig"
            )
        )
        assert record["schema_id"] == SCENARIO_SCHEMA_ID
        assert (
            record["arms"][0]["advisory"]["path"]
            == f"{SCENARIOS_REL}/responsibility_move/a1_move/plan.json"
        )

    def test_a_second_write_leaves_the_same_bytes(
        self, planning_world: Path, tmp_path: Path
    ) -> None:
        first = write_scenario_records(planning_world, self._results(planning_world, tmp_path))
        before = {p: p.read_bytes() for p in first}

        write_scenario_records(
            planning_world,
            [
                run_scenario(
                    planning_world,
                    _move_t03(),
                    tmp_path / "second",
                    run_ids=(RUN_WITH_DECISION,),
                )
            ],
        )

        assert {p: p.read_bytes() for p in first} == before

    def test_the_index_names_every_scenario_and_whether_its_arms_matched(
        self, planning_world: Path, tmp_path: Path
    ) -> None:
        write_scenario_records(planning_world, self._results(planning_world, tmp_path))

        index = json.loads(
            (planning_world / SCENARIOS_REL / "index.json").read_text(encoding="utf-8-sig")
        )
        assert [s["scenario_id"] for s in index["scenarios"]] == ["responsibility_move"]
        assert index["scenarios"][0]["arms_matched_expectations"] is True
        assert index["arms_matched_expectations"] is True

    def test_refuses_two_scenarios_under_one_id(
        self, planning_world: Path, tmp_path: Path
    ) -> None:
        results = self._results(planning_world, tmp_path) * 2

        with pytest.raises(DevGraphError) as exc:
            write_scenario_records(planning_world, results)

        assert exc.value.kind == "malformed_request"


class TestTransformRegistry:
    def test_refuses_a_transformation_it_does_not_hold(self, world: Path) -> None:
        with pytest.raises(DevGraphError) as exc:
            apply_transform("rewrite_everything", _read(world, WP_SEED), {})

        assert exc.value.kind == "malformed_request"
        assert "rewrite_everything" in str(exc.value)
