"""
Dev-graph change scenarios — a scripted approved change, its advisory and its
shadow comparison, run without touching the frozen world.

A scenario is a named sequence of arms over the records the snapshot
declares as its inputs. Each arm either records an approved change or probes a
refusal the operator expects. A recorded arm is checked against the
scenario's revision contract, planned by the shadow impact planner, and
compared against the reuse decisions a named run actually holds.

Two properties make a scenario replayable:

* **The frozen world is never edited in place.** Every arm runs against a
  sandbox: a copy of the snapshot's own declared inputs, materialised so
  that the sandbox's first snapshot id equals the live one. The freeze rule
  of the operator manual stands; the change lands on the copy.
* **A transformation that finds nothing refuses.** Each transformation in
  :data:`TRANSFORMS` is a pure function over the record content with a
  closed argument set. It raises rather than returning the content
  unchanged, so a scenario can never become a silent no-op and no
  transformation ever invents a partner, a task or a month (§13.3).

Constitutional authority:
    Subordinate to CLAUDE.md. Evaluates no gate, invokes no Claude, invents
    no facts (§13.3). The scenario catalogue — which records, which ids —
    is project data and lives with the operator tool, not here.
"""

from __future__ import annotations

import copy
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from runner.atomic_write import atomic_write_json
from runner.dev_graph.builder import Snapshot, build_snapshot
from runner.dev_graph.changes import ChangeRecord, load_snapshot, record_change
from runner.dev_graph.impact import ImpactPlan, plan_impact, read_run_records
from runner.dev_graph.revisions import (
    ContractCheck,
    RevisionContract,
    check_revision,
    normalise_contract,
)
from runner.dev_graph.schema import DevGraphError
from runner.dev_graph.shadow import compare_shadow, read_reuse_decisions

SCENARIO_SCHEMA_ID = "orch.dev_graph.change_scenario.v1"
SCENARIO_INDEX_SCHEMA_ID = "orch.dev_graph.change_scenario_index.v1"

_DEV_GRAPH = "docs/tier4_orchestration_state/dev_graph"
#: One directory per scenario: its record, and one advisory per recorded arm.
SCENARIOS_REL = f"{_DEV_GRAPH}/change_scenarios"

#: Each transformation: ``(content, args) -> new content``. Pure, total over
#: its declared arguments, and refusing when the target is absent.
Transform = Callable[[Mapping[str, Any], Mapping[str, Any]], dict[str, Any]]


def _refuse(offender: str, message: str) -> DevGraphError:
    return DevGraphError("malformed_request", offender, message)


def _arg(args: Mapping[str, Any], key: str, transform: str) -> str:
    value = args.get(key)
    if not isinstance(value, str) or not value:
        raise _refuse(transform, f"{transform}: argument {key!r} must be a non-empty string")
    return value


def _tasks(content: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [t for wp in content.get("work_packages", []) for t in wp.get("tasks", [])]


def move_task_responsibility(
    content: Mapping[str, Any], args: Mapping[str, Any]
) -> dict[str, Any]:
    """Hand the task named by ``task_id`` to its first contributing partner.

    The new responsible partner is the lowest contributing partner id that
    is not already responsible, so the move is determined by the record and
    nothing is chosen. It leaves the contributing list and the partner that
    held the task joins it, which is how these records express the role: no
    task lists its lead among its contributors.

    Refuses when the task is absent or when it declares no other partner to
    hand the work to.
    """
    task_id = _arg(args, "task_id", "move_task_responsibility")
    out = copy.deepcopy(dict(content))
    task = next((t for t in _tasks(out) if t.get("task_id") == task_id), None)
    if task is None:
        raise _refuse(task_id, f"no task {task_id} in the record")
    current = task.get("responsible_partner")
    candidates = sorted(
        p for p in task.get("contributing_partners") or [] if p != current
    )
    if not candidates:
        raise _refuse(
            task_id,
            f"task {task_id} declares no contributing partner to hand the work to",
        )
    new_lead = candidates[0]
    task["responsible_partner"] = new_lead
    contributing = {p for p in task.get("contributing_partners") or [] if p != new_lead}
    if isinstance(current, str) and current:
        contributing.add(current)
    task["contributing_partners"] = sorted(contributing)
    return out


def release_partner_from_work_plan(
    content: Mapping[str, Any], args: Mapping[str, Any]
) -> dict[str, Any]:
    """Stop the work plan naming the partner ``partner_id`` in any task role.

    Every contributing list loses the partner, and every task it is
    responsible for passes to the lowest remaining contributing partner id.
    Work-package leadership is a separate fact and is left alone, so a
    scenario that withdraws a lead partner still meets the builder's
    refusal rather than a silent reassignment.

    Refuses when no task names the partner, or when a task it leads
    declares no other partner to pass the work to.
    """
    partner_id = _arg(args, "partner_id", "release_partner_from_work_plan")
    out = copy.deepcopy(dict(content))
    tasks = _tasks(out)
    named = [
        t
        for t in tasks
        if t.get("responsible_partner") == partner_id
        or partner_id in (t.get("contributing_partners") or [])
    ]
    if not named:
        raise _refuse(partner_id, f"no task in the record names {partner_id}")
    for task in tasks:
        remaining = sorted(
            p for p in task.get("contributing_partners") or [] if p != partner_id
        )
        if task.get("responsible_partner") == partner_id:
            if not remaining:
                raise _refuse(
                    str(task.get("task_id")),
                    f"task {task.get('task_id')} is led by {partner_id} and declares "
                    "no other partner to pass the work to",
                )
            # No task in these records lists its lead among its contributors,
            # so the partner taking the work leaves the contributing list.
            task["responsible_partner"] = remaining[0]
            remaining = remaining[1:]
        if "contributing_partners" in task:
            task["contributing_partners"] = remaining
    return out


def _entry(
    out: Mapping[str, Any], list_key: str, id_key: str, wanted: str
) -> dict[str, Any]:
    """The one object under ``out[list_key]`` whose *id_key* is *wanted*."""
    found = next(
        (e for e in out.get(list_key, []) if e.get(id_key) == wanted), None
    )
    if found is None:
        raise _refuse(wanted, f"no {list_key} entry with {id_key} {wanted}")
    return found


def _set_field(
    content: Mapping[str, Any],
    args: Mapping[str, Any],
    *,
    transform: str,
    id_arg: str,
    list_key: str,
    id_key: str,
) -> dict[str, Any]:
    """Set one declared top-level field of one entry, or refuse.

    A set whose value the field already holds refuses: an arm that changes
    nothing is not a scenario.
    """
    wanted = _arg(args, id_arg, transform)
    field = _arg(args, "field", transform)
    if "value" not in args:
        raise _refuse(transform, f"{transform}: argument 'value' is required")
    value = args["value"]
    out = copy.deepcopy(dict(content))
    entry = _entry(out, list_key, id_key, wanted)
    if entry.get(field) == value:
        raise _refuse(
            wanted, f"{wanted}: {field} already holds {value!r}; the arm would change nothing"
        )
    entry[field] = value
    return out


def remove_partner(content: Mapping[str, Any], args: Mapping[str, Any]) -> dict[str, Any]:
    """Drop the partner ``partner_id`` from the consortium record.

    The work plan is a separate record and is not touched, so a withdrawal
    the work plan still names meets the builder's dangling-edge refusal.
    """
    partner_id = _arg(args, "partner_id", "remove_partner")
    out = copy.deepcopy(dict(content))
    _entry(out, "partners", "partner_id", partner_id)
    out["partners"] = [p for p in out["partners"] if p.get("partner_id") != partner_id]
    return out


def set_partner_field(content: Mapping[str, Any], args: Mapping[str, Any]) -> dict[str, Any]:
    """Set one declared field of one partner — a confirmed participation, say."""
    return _set_field(
        content,
        args,
        transform="set_partner_field",
        id_arg="partner_id",
        list_key="partners",
        id_key="partner_id",
    )


def set_source_field(content: Mapping[str, Any], args: Mapping[str, Any]) -> dict[str, Any]:
    """Set one declared field of one source — its own status, say."""
    return _set_field(
        content,
        args,
        transform="set_source_field",
        id_arg="source_id",
        list_key="sources",
        id_key="source_id",
    )


def drop_source_span(content: Mapping[str, Any], args: Mapping[str, Any]) -> dict[str, Any]:
    """Remove the span ``span_id`` from the spans the source declares."""
    source_id = _arg(args, "source_id", "drop_source_span")
    span_id = _arg(args, "span_id", "drop_source_span")
    out = copy.deepcopy(dict(content))
    source = _entry(out, "sources", "source_id", source_id)
    spans = source.get("spans") or []
    if not any(s.get("span_id") == span_id for s in spans):
        raise _refuse(span_id, f"source {source_id} declares no span {span_id}")
    source["spans"] = [s for s in spans if s.get("span_id") != span_id]
    return out


def move_deliverable_due_month(
    content: Mapping[str, Any], args: Mapping[str, Any]
) -> dict[str, Any]:
    """Move the deliverable ``deliverable_id`` to month ``to_month``."""
    deliverable_id = _arg(args, "deliverable_id", "move_deliverable_due_month")
    to_month = args.get("to_month")
    if not isinstance(to_month, int) or isinstance(to_month, bool) or to_month < 1:
        raise _refuse(
            "move_deliverable_due_month",
            "move_deliverable_due_month: argument 'to_month' must be a month number",
        )
    out = copy.deepcopy(dict(content))
    found = next(
        (
            d
            for wp in out.get("work_packages", [])
            for d in wp.get("deliverables", [])
            if d.get("deliverable_id") == deliverable_id
        ),
        None,
    )
    if found is None:
        raise _refuse(deliverable_id, f"no deliverable {deliverable_id} in the record")
    if found.get("due_month") == to_month:
        raise _refuse(
            deliverable_id,
            f"{deliverable_id} is already due in month {to_month}; the arm would change nothing",
        )
    found["due_month"] = to_month
    return out


def add_work_package_objective(
    content: Mapping[str, Any], args: Mapping[str, Any]
) -> dict[str, Any]:
    """Add ``objective_id`` to the objectives the work package ``wp_id`` serves."""
    wp_id = _arg(args, "wp_id", "add_work_package_objective")
    objective_id = _arg(args, "objective_id", "add_work_package_objective")
    out = copy.deepcopy(dict(content))
    wp = _entry(out, "work_packages", "wp_id", wp_id)
    objectives = list(wp.get("objectives") or [])
    if objective_id in objectives:
        raise _refuse(
            wp_id, f"{wp_id} already serves {objective_id}; the arm would change nothing"
        )
    wp["objectives"] = sorted({*objectives, objective_id})
    return out


#: The closed transformation registry. A scenario may name nothing else.
TRANSFORMS: Mapping[str, Transform] = {
    "add_work_package_objective": add_work_package_objective,
    "drop_source_span": drop_source_span,
    "move_deliverable_due_month": move_deliverable_due_month,
    "move_task_responsibility": move_task_responsibility,
    "release_partner_from_work_plan": release_partner_from_work_plan,
    "remove_partner": remove_partner,
    "set_partner_field": set_partner_field,
    "set_source_field": set_source_field,
}


def apply_transform(
    name: str, content: Mapping[str, Any], args: Mapping[str, Any]
) -> dict[str, Any]:
    """Apply the transformation *name* to *content*, or refuse.

    Raises :class:`DevGraphError` with kind ``malformed_request`` on an
    unknown transformation, a malformed argument, or a target the record
    does not hold. *content* is never mutated.
    """
    transform = TRANSFORMS.get(name)
    if transform is None:
        raise _refuse(str(name), f"transformation {name!r} is not one of {sorted(TRANSFORMS)}")
    if not isinstance(content, Mapping):
        raise _refuse(str(name), f"{name}: record content must be a JSON object")
    return transform(content, args or {})


# ---------------------------------------------------------------------------
# The sandbox
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Sandbox:
    """A copy of one world's snapshot inputs, and the snapshot it builds."""

    root: Path
    snapshot: Snapshot
    source_root: Path
    inputs: tuple[str, ...]


def materialise_sandbox(repo_root: Path | str, dest: Path | str) -> Sandbox:
    """Copy *repo_root*'s snapshot inputs into *dest* and build there.

    The copy covers exactly the files the snapshot declares as its inputs,
    so the sandbox's own snapshot id equals the live one and every later
    arm is anchored to the real world rather than to a reduction of it.
    That equality is checked, not assumed.

    Raises :class:`DevGraphError` with kind ``malformed_request`` when the
    source world declares no inputs, when *dest* already holds records, or
    when the copy does not reproduce the source snapshot id.
    """
    source = Path(repo_root)
    target = Path(dest)
    live = build_snapshot(source)
    if not live.inputs:
        raise _refuse(
            source.as_posix(), f"{source.as_posix()} declares no snapshot input to copy"
        )
    if target.exists() and any(target.rglob("*")):
        raise _refuse(target.as_posix(), f"{target.as_posix()} is not an empty sandbox")
    for rel in live.inputs:
        out = target / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / rel, out)
    built = build_snapshot(target)
    if built.snapshot_id != live.snapshot_id:
        raise _refuse(
            target.as_posix(),
            f"the sandbox builds {built.snapshot_id} but {source.as_posix()} "
            f"builds {live.snapshot_id}",
        )
    return Sandbox(
        root=target, snapshot=built, source_root=source, inputs=tuple(live.inputs)
    )


# ---------------------------------------------------------------------------
# The scripted scenario
# ---------------------------------------------------------------------------

#: What an arm does: record an approved change, or probe a refusal.
ARM_KINDS: frozenset[str] = frozenset({"change", "refusal_probe"})
#: What an arm whose expectation is a recorded change declares.
RECORDED = "recorded"


@dataclass(frozen=True)
class Arm:
    """One step of a scenario, and what the operator expects of it."""

    arm_id: str
    kind: str
    record_path: str
    transform: str | None
    args: Mapping[str, Any]
    expects: str
    """:data:`RECORDED`, or the refusal kind the arm is expected to meet."""
    purpose: str
    payload: Mapping[str, Any] | None = None
    """Record content to offer instead of a transformation, for a probe whose
    point is the path rather than the content."""

    def to_dict(self) -> dict[str, Any]:
        return {
            "arm_id": self.arm_id,
            "kind": self.kind,
            "record_path": self.record_path,
            "transform": self.transform,
            "args": dict(self.args),
            # The offered content is an input of the arm, so it belongs in the
            # record (§9.5). Null when a transformation produced the content.
            "payload": dict(self.payload) if self.payload is not None else None,
            "expects": self.expects,
            "purpose": self.purpose,
        }


def check_arm(arm: Arm, source_root: Path) -> None:
    """Check one arm is well formed against the world it will run over, or refuse.

    This runs **before** the arm does, so that a malformed arm raises instead
    of being recorded as the refusal it happened to declare. Without it a
    `refusal_probe` expecting ``malformed_request`` would pass identically on
    a record path that is simply misspelled: the change recorder refuses an
    unknown path either way, and the record would assert that the engine
    declined a real Tier 3 fact when nobody had named one.

    Three checks, each a :class:`DevGraphError` with kind ``malformed_request``:

    * the kind is in :data:`ARM_KINDS`, and agrees with the expectation — a
      ``change`` expects :data:`RECORDED` and a ``refusal_probe`` does not;
    * the arm offers exactly one of a transformation and a payload;
    * ``record_path`` names a file that exists in *source_root*, so a probe
      about a record the change recorder does not cover is distinguishable
      from a probe about a path that does not exist.
    """
    where = arm.arm_id
    if arm.kind not in ARM_KINDS:
        raise _refuse(where, f"arm kind {arm.kind!r} is not one of {sorted(ARM_KINDS)}")
    expects_recorded = arm.expects == RECORDED
    if (arm.kind == "change") != expects_recorded:
        raise _refuse(
            where,
            f"arm {where} is a {arm.kind!r} but expects {arm.expects!r}; a change "
            f"expects {RECORDED!r} and a refusal_probe expects a refusal kind",
        )
    if (arm.transform is None) == (arm.payload is None):
        raise _refuse(
            where, f"arm {where} must declare exactly one of a transform and a payload"
        )
    if not (Path(source_root) / arm.record_path).is_file():
        raise _refuse(
            arm.record_path,
            f"arm {where} names {arm.record_path}, which is not a file in "
            f"{Path(source_root).as_posix()}",
        )


@dataclass(frozen=True)
class Scenario:
    """A named sequence of arms run under one revision contract."""

    scenario_id: str
    title: str
    purpose: str
    contract: Mapping[str, Any]
    arms: tuple[Arm, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "title": self.title,
            "purpose": self.purpose,
            "arms": [a.to_dict() for a in self.arms],
        }


def _plan_summary(plan: Mapping[str, Any], path: str) -> dict[str, Any]:
    """What the scenario record says about one advisory, and where it is.

    The entries themselves stay in the plan document at *path*, in the
    schema the planner's own writer uses, so the reason paths have one
    home. The record carries the counts and the one property the ticket
    asks after: whether every entry carries a reason path.
    """
    entries = list(plan["entries"])
    counts: dict[str, int] = {}
    for entry in entries:
        key = f"{entry['kind']}/{entry['hit']}/{entry['action']}"
        counts[key] = counts.get(key, 0) + 1
    return {
        "path": path,
        "plan_id": plan["plan_id"],
        "nothing_changed": plan["nothing_changed"],
        "origins": list(plan["origins"]),
        "entry_count": len(entries),
        "entries_by_kind_hit_action": dict(sorted(counts.items())),
        "every_entry_has_a_reason_path": all(e["reason_path"] for e in entries),
        "newly_relevant_source_count": len(plan["newly_relevant_sources"]),
    }


@dataclass(frozen=True)
class ArmResult:
    """What one arm did, and whether that is what the operator expected."""

    arm: Arm
    outcome: str
    """:data:`RECORDED` or ``refused``."""
    expectation_met: bool
    sandbox_snapshot_id: str
    refusal: dict[str, str] | None = None
    change: dict[str, Any] | None = None
    check: ContractCheck | None = None
    plan: ImpactPlan | None = None
    shadow: tuple[dict[str, Any], ...] = ()

    def to_dict(self, scenario_id: str) -> dict[str, Any]:
        plan = self.plan.to_dict() if self.plan is not None else None
        return {
            **self.arm.to_dict(),
            "outcome": self.outcome,
            "expectation_met": self.expectation_met,
            "sandbox_snapshot_id": self.sandbox_snapshot_id,
            "refusal": dict(self.refusal) if self.refusal else None,
            "change": dict(self.change) if self.change else None,
            "contract_check": self.check.to_dict() if self.check is not None else None,
            "advisory": (
                None
                if plan is None
                else _plan_summary(plan, advisory_rel(scenario_id, self.arm.arm_id))
            ),
            "shadow_comparisons": [dict(s) for s in self.shadow],
        }


@dataclass(frozen=True)
class ScenarioResult:
    """One scenario's arms, and the snapshot they all started from."""

    scenario: Scenario
    before_snapshot_id: str
    contract: RevisionContract
    arms: tuple[ArmResult, ...]

    @property
    def arms_matched_expectations(self) -> bool:
        """Whether every arm did what the scenario declared it would.

        This says nothing about whether a ticket criterion is met. An arm
        that refused exactly as expected matched its expectation, and a
        scenario can match every one of them while the question it was run
        to answer stays open.
        """
        return all(a.expectation_met for a in self.arms)

    def to_dict(self) -> dict[str, Any]:
        sid = self.scenario.scenario_id
        return {
            "schema_id": SCENARIO_SCHEMA_ID,
            **self.scenario.to_dict(),
            "before_snapshot_id": self.before_snapshot_id,
            "contract": self.contract.to_dict(),
            "arms_matched_expectations": self.arms_matched_expectations,
            "arms": [a.to_dict(sid) for a in self.arms],
        }


def shadow_label(comparison: Mapping[str, Any]) -> str:
    """One comparison as a word: its diagnostic, or ``refused:<kind>``.

    The one definition, so a roll-up and a console report cannot disagree
    about how a refusal reads.
    """
    diagnostic = comparison.get("diagnostic")
    if isinstance(diagnostic, str) and diagnostic:
        return diagnostic
    return f"refused:{comparison['refused']['kind']}"


def _refusal(exc: DevGraphError) -> dict[str, str]:
    return {"kind": exc.kind, "offender": str(exc.offender), "message": str(exc)}


def _change_summary(record: ChangeRecord) -> dict[str, Any]:
    cs = record.change_set
    return {
        "change_id": record.change_id,
        "record_path": record.record_path,
        "before_snapshot_id": record.before_snapshot_id,
        "after_snapshot_id": record.after_snapshot_id,
        "nodes_added": [n["id"] for n in cs["nodes"]["added"]],
        "nodes_removed": [n["id"] for n in cs["nodes"]["removed"]],
        "nodes_changed": [
            {"id": c["id"], "kind": c["kind"], "changed_fields": c["changed_fields"]}
            for c in cs["nodes"]["changed"]
        ],
        "edges_added": [e["label"] for e in cs["edges"]["added"]],
        "edges_removed": [e["label"] for e in cs["edges"]["removed"]],
    }


def _record_content(sandbox: Sandbox, rel: str) -> dict[str, Any]:
    path = sandbox.root / rel
    if not path.is_file():
        raise _refuse(rel, f"the sandbox holds no record at {rel}")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _compare_one(repo_root: Path, plan: ImpactPlan, run_id: str) -> dict[str, Any]:
    """One shadow comparison, with a refusal recorded rather than raised.

    A comparison that cannot be made is a result: the run holds no reuse
    decision to compare against, or its id is not one the reader accepts.
    Reporting agreement over an absent decision set would be the
    fabrication this whole lane exists to avoid.
    """
    try:
        decisions = read_reuse_decisions(repo_root, run_id)
        comparison = compare_shadow(plan, decisions, run_id=run_id)
    except DevGraphError as exc:
        return {"run_id": run_id, "refused": _refusal(exc)}
    return {
        "run_id": run_id,
        "comparison_id": comparison.comparison_id,
        "diagnostic": comparison.diagnostic,
        "rows": list(comparison.rows),
    }


def _run_arm(
    repo_root: Path,
    sandbox: Sandbox,
    scenario: Scenario,
    contract: RevisionContract,
    arm: Arm,
    *,
    run_ids: tuple[str, ...],
    run_records: list[dict[str, Any]] | None,
) -> ArmResult:
    """Run one arm against *sandbox*, recording an expected refusal.

    The arm is checked by :func:`check_arm` first, so a malformed arm raises
    here rather than being recorded as the refusal it declared.
    """
    check_arm(arm, sandbox.source_root)
    change_id = f"{scenario.scenario_id}__{arm.arm_id}"
    try:
        if arm.transform is not None:
            new_content = apply_transform(
                arm.transform, _record_content(sandbox, arm.record_path), arm.args
            )
        else:
            assert arm.payload is not None  # check_arm guarantees one of the two
            new_content = dict(arm.payload)
        record = record_change(
            sandbox.root, arm.record_path, new_content, change_id=change_id
        )
    except DevGraphError as exc:
        return ArmResult(
            arm=arm,
            outcome="refused",
            expectation_met=arm.expects == exc.kind,
            sandbox_snapshot_id=build_snapshot(sandbox.root).snapshot_id,
            refusal=_refusal(exc),
        )

    check = check_revision(contract, record.change_set)
    plan = plan_impact(
        load_snapshot(sandbox.root, record.before_snapshot_id),
        load_snapshot(sandbox.root, record.after_snapshot_id),
        run_records if run_records is not None else read_run_records(repo_root),
        change_id=record.change_id,
    )
    return ArmResult(
        arm=arm,
        outcome=RECORDED,
        expectation_met=arm.expects == RECORDED,
        sandbox_snapshot_id=record.after_snapshot_id,
        change=_change_summary(record),
        check=check,
        plan=plan,
        shadow=tuple(_compare_one(repo_root, plan, rid) for rid in run_ids),
    )


def run_scenario(
    repo_root: Path | str,
    scenario: Scenario,
    sandbox_dir: Path | str,
    *,
    run_ids: tuple[str, ...] = (),
    run_records: list[dict[str, Any]] | None = None,
) -> ScenarioResult:
    """Run the arms of *scenario* in a sandbox over *repo_root*, in order.

    *repo_root* is read and never written: the records change in the
    sandbox, while the run records and the run manifests are read from the
    real world.

    An arm whose expectation is not met is reported, not raised, so one
    surprising arm does not hide the arms after it. Raises
    :class:`DevGraphError` only on a malformed scenario: an unknown arm
    kind, a contract the checker refuses, or an absent sandbox record.
    """
    root = Path(repo_root)
    contract = normalise_contract(dict(scenario.contract))
    sandbox = materialise_sandbox(root, sandbox_dir)
    results = [
        _run_arm(
            root,
            sandbox,
            scenario,
            contract,
            arm,
            run_ids=tuple(run_ids),
            run_records=run_records,
        )
        for arm in scenario.arms
    ]
    return ScenarioResult(
        scenario=scenario,
        before_snapshot_id=sandbox.snapshot.snapshot_id,
        contract=contract,
        arms=tuple(results),
    )


# ---------------------------------------------------------------------------
# The one durable write
# ---------------------------------------------------------------------------


def advisory_rel(scenario_id: str, arm_id: str) -> str:
    """Where one arm's advisory plan is written, relative to the repo root.

    The scenario's own directory, not ``impact_plans/``: a scenario's change
    never lands in the frozen Tier 3, so its advisory must not sit where a
    reader would take it for a plan over a change the world holds.
    """
    return f"{SCENARIOS_REL}/{scenario_id}/{arm_id}/plan.json"


def scenario_rel(scenario_id: str) -> str:
    """Where one scenario's record is written, relative to the repo root."""
    return f"{SCENARIOS_REL}/{scenario_id}/scenario.json"


def write_scenario_records(
    repo_root: Path | str, results: list[ScenarioResult] | tuple[ScenarioResult, ...]
) -> list[Path]:
    """Write one record per scenario, one advisory per recorded arm, one index.

    Returns the absolute paths written, sorted. No wall-clock field: the
    same scenarios over the same world rewrite the same bytes, so a replay
    is byte-equal and a difference is a real difference.

    Raises :class:`DevGraphError` with kind ``malformed_request`` when two
    results share a scenario id, since the second would overwrite the first.
    """
    root = Path(repo_root)
    ids = [r.scenario.scenario_id for r in results]
    duplicate = next((i for i in ids if ids.count(i) > 1), None)
    if duplicate is not None:
        raise _refuse(duplicate, f"scenario id {duplicate!r} is recorded more than once")

    written: list[Path] = []
    index: list[dict[str, Any]] = []
    for result in results:
        sid = result.scenario.scenario_id
        doc = result.to_dict()
        for arm in result.arms:
            if arm.plan is None:
                continue
            target = root / advisory_rel(sid, arm.arm.arm_id)
            atomic_write_json(arm.plan.to_dict(), target)
            written.append(target)
        target = root / scenario_rel(sid)
        atomic_write_json(doc, target)
        written.append(target)
        index.append(
            {
                "scenario_id": sid,
                "title": result.scenario.title,
                "path": scenario_rel(sid),
                "before_snapshot_id": result.before_snapshot_id,
                "arms_matched_expectations": result.arms_matched_expectations,
                "arms": [
                    {
                        "arm_id": a.arm.arm_id,
                        "outcome": a.outcome,
                        "expectation_met": a.expectation_met,
                        "contract_verdict": None if a.check is None else a.check.verdict,
                        "advisory": None if a.plan is None else advisory_rel(sid, a.arm.arm_id),
                        "shadow_diagnostics": [shadow_label(s) for s in a.shadow],
                    }
                    for a in result.arms
                ],
            }
        )

    target = root / SCENARIOS_REL / "index.json"
    atomic_write_json(
        {
            "schema_id": SCENARIO_INDEX_SCHEMA_ID,
            "advisory": True,
            "mode": "shadow",
            "consumed_at_runtime": False,
            "arms_matched_expectations": all(
                r.arms_matched_expectations for r in results
            ),
            "scenarios": index,
        },
        target,
    )
    written.append(target)
    return sorted(written)
