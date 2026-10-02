"""Run the demo's change scenarios, their advisories and their comparisons.

The ticket 'Change scenarios and shadow comparison' names six approved changes
and asks that each run as a pair: the planner's advisory first, then a real
rerun, then the shadow comparison. This tool is the scripted half. The reruns
are operator work — the engine's phases cost subscription quota and are
dispatched by hand — and what blocks them in this world is recorded in the
decision log rather than simulated here.

Every scenario runs in a sandbox copy of the files the snapshot declares as
its inputs, so the frozen founding documents are never edited in place
(the operator manual's freeze rule, §3.1) and the demo snapshot id never moves.
The sandbox's first snapshot id is checked against the live one, so a scenario
is anchored to the real world rather than to a reduction of it.

The catalogue below is this project's data: which record, which id, which
contract. The machinery — the transformations, the sandbox, the arms, the
record writer — is generic and lives in ``runner/dev_graph/scenarios.py``.

What each scenario demonstrates, and where the ticket's six map:

1. ``task_lead_moves`` — a task's lead moves between two partners.
2. ``gap_partner_withdraws`` — an Assumed gap partner withdraws. Three arms: the
   single-record withdrawal refuses, because the work plan still names the
   partner; then the work plan releases it; then the consortium record drops it.
3. ``gap_partner_confirmed`` — a gap partner's participation is confirmed. Two
   arms: the partner record changes, and the matching edit to
   ``working_assumptions.json`` is probed and refused, because the ledger is not
   a record the change recorder covers.
4. ``claim_loses_its_span`` — the source span a claim would rest on is dropped.
5. ``tier2b_fact_changes`` — a Tier 2B fact changes. Two arms: naming
   ``selected_call.json`` to the change recorder refuses, and the graph-visible
   proxy is the project's own confidence in the call page it transcribed.
6. ``deliverable_month_moves`` — a deliverable's month crosses its milestone.

A seventh, ``protected_objective_probe``, is the ticket's fourth criterion: a
change that touches a protected objective must be rejected with the node named.

Run it from the repository root::

    py -3.10 -m tools.run_demo_change_scenarios            # write
    py -3.10 -m tools.run_demo_change_scenarios --check    # exit 1 if anything differs

Constitutional standing: an authoring tool, not a runtime component and not a
manifest-bound deterministic component. It reads Tier 3, Tier 4 and the run
manifests, writes Tier 4 scenario records and advisories, evaluates no gate
(§17.6.2), invokes no Claude, and writes no reuse metadata.
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from runner.dev_graph.builder import (  # noqa: E402
    PARTNERS_REL,
    SOURCES_REL,
    WP_SEED_REL,
)
from runner.dev_graph.scenarios import (  # noqa: E402
    RECORDED,
    SCENARIOS_REL,
    Arm,
    Scenario,
    ScenarioResult,
    run_scenario,
    shadow_label,
    write_scenario_records,
)
from runner.dev_graph.impact import read_run_records  # noqa: E402

WP_SEED = WP_SEED_REL.as_posix()
PARTNERS = PARTNERS_REL.as_posix()
SOURCES = SOURCES_REL.as_posix()
SELECTED_CALL = "docs/tier3_project_instantiation/call_binding/selected_call.json"
WORKING_ASSUMPTIONS = "docs/tier3_project_instantiation/working_assumptions.json"

#: The runs whose recorded reuse decisions each advisory is compared against.
#: Both are runs this world actually holds: the Phases 1 to 6 run, and the run
#: that carried Phase 8. The second was dispatched under a mis-pasted shell
#: command as its run id. The live layout cannot be addressed with that id, so
#: the comparison's reader finds the run through the record
#: ``tools/preserve_run_manifests.py`` keeps under its slug, with the true run
#: id inside; the comparison names the run by that true id. What it finds there
#: is recorded, not worked around: the run's manifest holds no reuse decision,
#: because the scheduler persists one only when it reuses (subticket D).
COMPARED_RUN_IDS: tuple[str, ...] = (
    "d68acaef-e9b2-412e-bc09-4b34c386d5fd",
    "import uuid; print(uuid.uuid4())",
)

#: The objectives every contract protects. The handoff's revision contract
#: permits responsibility-related changes while protecting the objective, the
#: output and the timing; these are this world's six objectives.
PROTECTED_OBJECTIVES: tuple[str, ...] = ("O1", "O2", "O3", "O4", "O5", "O6")

#: The gap partner the withdrawal and confirmation scenarios use. P07 is one of
#: the six partners ``working_assumptions.json`` declares with checklist_ref
#: CONSORTIUM_GAP, and it leads no work package, so a withdrawal reaches the
#: consortium record rather than stopping at a work-package lead.
GAP_PARTNER = "P07"

#: The call page the project transcribed and relies on for the topic scope.
CALL_PAGE = "SRC-WP9-P75"


def _contract(
    contract_id: str, permitted: tuple[str, ...], *, unresolved: tuple[dict, ...] = ()
) -> dict:
    return {
        "contract_id": contract_id,
        "permitted_change_classes": list(permitted),
        "protected_node_ids": list(PROTECTED_OBJECTIVES),
        "unresolved_items": [dict(i) for i in unresolved],
    }


#: The unresolved item the handoff asks to keep explicit: nobody has confirmed
#: that either partner has the capacity for the task. It names no node, so it
#: bears on every change under its contract.
PARTICIPANT_CAPACITY = {
    "item_id": "participant_capacity",
    "description": (
        "No partner's capacity is confirmed. All twelve participations are "
        "operator declarations in working_assumptions.json."
    ),
}

SCENARIOS: tuple[Scenario, ...] = (
    Scenario(
        scenario_id="task_lead_moves",
        title="A task's lead moves between two partners",
        purpose=(
            "The handoff's first operational milestone at this world's scale. The "
            "two partners swap roles on T3.1, so the change isolates "
            "responsibility and the partner set stays the same."
        ),
        contract=_contract(
            "responsibility_move",
            ("responsibility", "contribution"),
            unresolved=(PARTICIPANT_CAPACITY,),
        ),
        arms=(
            Arm(
                arm_id="a1_move_t3_1",
                kind="change",
                record_path=WP_SEED,
                transform="move_task_responsibility",
                args={"task_id": "T3.1"},
                expects=RECORDED,
                purpose=(
                    "T3.1 passes from its lead to its lowest contributing partner, "
                    "and the unresolved capacity item stays explicit."
                ),
            ),
        ),
    ),
    Scenario(
        scenario_id="gap_partner_withdraws",
        title="An Assumed gap partner withdraws before confirmation",
        purpose=(
            "A withdrawal is two records, not one. The work plan must release the "
            "partner before the consortium record can drop it, and the builder "
            "enforces that rather than leaving a dangling role."
        ),
        contract=_contract(
            "withdrawal", ("participant", "responsibility", "contribution")
        ),
        arms=(
            Arm(
                arm_id="a1_drop_from_consortium_first",
                kind="refusal_probe",
                record_path=PARTNERS,
                transform="remove_partner",
                args={"partner_id": GAP_PARTNER},
                expects="dangling_edge",
                purpose=(
                    "The work plan still names the partner, so the snapshot would "
                    "carry an edge with no endpoint. The change recorder restores "
                    "the record and writes nothing."
                ),
            ),
            Arm(
                arm_id="a2_release_from_work_plan",
                kind="change",
                record_path=WP_SEED,
                transform="release_partner_from_work_plan",
                args={"partner_id": GAP_PARTNER},
                expects=RECORDED,
                purpose=(
                    "Every task role the partner held passes to a partner the task "
                    "already names."
                ),
            ),
            Arm(
                arm_id="a3_drop_from_consortium",
                kind="change",
                record_path=PARTNERS,
                transform="remove_partner",
                args={"partner_id": GAP_PARTNER},
                expects=RECORDED,
                purpose="The consortium record drops the entry and the build holds.",
            ),
        ),
    ),
    Scenario(
        scenario_id="gap_partner_confirmed",
        title="An Assumed gap partner is confirmed",
        purpose=(
            "Confirmation is a change to the partner record and a declaration "
            "leaving the uncertainty ledger. Only the first is a change the graph "
            "can see, and the second is probed rather than assumed."
        ),
        contract=_contract("confirmation", ("participant",)),
        arms=(
            Arm(
                arm_id="a1_confirm_participation",
                kind="change",
                record_path=PARTNERS,
                transform="set_partner_field",
                args={
                    "partner_id": GAP_PARTNER,
                    "field": "participation_status",
                    "value": "Confirmed",
                },
                expects=RECORDED,
                purpose="The partner's declared participation status moves to Confirmed.",
            ),
            Arm(
                arm_id="a2_ledger_declaration_leaves",
                kind="refusal_probe",
                record_path=WORKING_ASSUMPTIONS,
                transform=None,
                args={},
                payload={"record_type": "working_assumptions", "declarations": []},
                expects="malformed_request",
                purpose=(
                    "The uncertainty ledger is not one of the five records the "
                    "change recorder covers, so the declaration leaving it is "
                    "invisible to the planner. The operator must carry that half."
                ),
            ),
        ),
    ),
    Scenario(
        scenario_id="claim_loses_its_span",
        title="A claim loses its verified source span",
        purpose=(
            "The span a claim would rest on is dropped from the source that "
            "declares it. The planner reports nothing changed, because a span "
            "list is a nested structure and the source's own content is equal."
        ),
        contract=_contract("evidence_withdrawal", ("evidence",)),
        arms=(
            Arm(
                arm_id="a1_drop_the_span",
                kind="change",
                record_path=SOURCES,
                transform="drop_source_span",
                args={"source_id": CALL_PAGE, "span_id": f"{CALL_PAGE}#133-305"},
                expects=RECORDED,
                purpose=(
                    "The source version moves, the change is classified contained, "
                    "and the advisory has no origin to walk from."
                ),
            ),
        ),
    ),
    Scenario(
        scenario_id="tier2b_fact_changes",
        title="A Tier 2B fact changes",
        purpose=(
            "The call's own facts live in Tier 2B and the call binding, neither of "
            "which the change recorder covers. The nearest graph-visible change is "
            "the project's confidence in the page it transcribed."
        ),
        contract=_contract("call_correction", ("evidence",)),
        arms=(
            Arm(
                arm_id="a1_correct_the_call_binding",
                kind="refusal_probe",
                record_path=SELECTED_CALL,
                transform=None,
                args={},
                payload={"record_type": "selected_call"},
                expects="malformed_request",
                purpose=(
                    "The call binding is not a record the change recorder covers, "
                    "so a date correction or a topic amendment cannot be planned."
                ),
            ),
            Arm(
                arm_id="a2_call_page_no_longer_confirmed",
                kind="change",
                record_path=SOURCES,
                transform="set_source_field",
                args={"source_id": CALL_PAGE, "field": "status", "value": "Unresolved"},
                expects=RECORDED,
                purpose=(
                    "The transcribed call page stops being Confirmed. The advisory "
                    "then reaches every work package constrained by it."
                ),
            ),
        ),
    ),
    Scenario(
        scenario_id="deliverable_month_moves",
        title="A deliverable's month moves across a milestone",
        purpose=(
            "D3.2 is due in the month MS4 checks it. Moving it one month later "
            "puts it past the milestone, and the milestone record does not change."
        ),
        contract=_contract("timing", ("timing",)),
        arms=(
            Arm(
                arm_id="a1_move_d3_2",
                kind="change",
                record_path=WP_SEED,
                transform="move_deliverable_due_month",
                args={"deliverable_id": "D3.2", "to_month": 29},
                expects=RECORDED,
                purpose=(
                    "The timing change is permitted, and the milestone is reached "
                    "over the edge it was already validated by."
                ),
            ),
        ),
    ),
    Scenario(
        scenario_id="protected_objective_probe",
        title="A change that touches a protected objective",
        purpose=(
            "The ticket's fourth criterion. WP1 starts serving O1, which adds a "
            "contributes_to edge whose endpoint the contract protects."
        ),
        contract={
            "contract_id": "objective_protected",
            "permitted_change_classes": ["contribution"],
            "protected_node_ids": ["O1"],
        },
        arms=(
            Arm(
                arm_id="a1_add_protected_objective",
                kind="change",
                record_path=WP_SEED,
                transform="add_work_package_objective",
                args={"wp_id": "WP1", "objective_id": "O1"},
                expects=RECORDED,
                purpose="The contract rejects the change and names O1.",
            ),
        ),
    ),
)


def run_all(repo_root: Path | str, sandbox_base: Path | str) -> list[ScenarioResult]:
    """Run every scenario in its own sandbox under *sandbox_base*.

    *repo_root* is read only: the records change in the sandboxes and the run
    manifests and run records come from the real world.
    """
    root = Path(repo_root)
    base = Path(sandbox_base)
    records = read_run_records(root)
    return [
        run_scenario(
            root,
            scenario,
            base / scenario.scenario_id,
            run_ids=COMPARED_RUN_IDS,
            run_records=records,
        )
        for scenario in SCENARIOS
    ]


def _report(results: list[ScenarioResult]) -> None:
    for result in results:
        print(f"{result.scenario.scenario_id}:")
        for arm in result.arms:
            verdict = "-" if arm.check is None else arm.check.verdict
            advisory = (
                "-"
                if arm.plan is None
                else f"{len(arm.plan.entries)} entries, origins {len(arm.plan.origins)}"
            )
            diagnostics = ",".join(shadow_label(s) for s in arm.shadow)
            met = "ok" if arm.expectation_met else "UNMET"
            print(
                f"  {arm.arm.arm_id}: {arm.outcome} ({met})"
                f" | contract {verdict} | advisory {advisory} | shadow {diagnostics}"
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="compare with the written records and exit 1 on any difference",
    )
    parser.add_argument("--repo-root", default=None, help="defaults to this file's repository")
    args = parser.parse_args(argv)

    root = Path(args.repo_root) if args.repo_root else Path(__file__).resolve().parents[1]
    base = Path(tempfile.mkdtemp(prefix="change-scenarios-"))
    try:
        results = run_all(root, base)
        _report(results)
        unmet = [
            (r.scenario.scenario_id, a.arm.arm_id)
            for r in results
            for a in r.arms
            if not a.expectation_met
        ]
        if unmet:
            # Fail closed in both modes. A frozen-in wrong expectation must not
            # pass --check just because the written bytes match it.
            print("UNMET EXPECTATIONS: " + ", ".join(f"{s}/{a}" for s, a in unmet))
            return 1
        if args.check:
            staging = Path(tempfile.mkdtemp(prefix="change-scenarios-check-"))
            try:
                differences = 0
                for staged in write_scenario_records(staging, results):
                    rel = staged.relative_to(staging)
                    live = root / rel
                    if not live.is_file():
                        print(f"MISSING {rel.as_posix()}")
                        differences += 1
                    elif live.read_bytes() != staged.read_bytes():
                        print(f"DIFFERS {rel.as_posix()}")
                        differences += 1
                if differences:
                    return 1
                print(f"OK {SCENARIOS_REL} ({len(results)} scenarios)")
                return 0
            finally:
                shutil.rmtree(staging, ignore_errors=True)

        written = write_scenario_records(root, results)
        print(f"WROTE {len(written)} files under {SCENARIOS_REL}")
        return 0
    finally:
        shutil.rmtree(base, ignore_errors=True)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
