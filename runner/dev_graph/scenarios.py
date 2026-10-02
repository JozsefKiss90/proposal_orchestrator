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

One route leads out of the sandbox. :func:`enact_scenario` records a
scenario's arms on the world itself, through the same change recorder, and
only after a sandbox run has shown every arm to be a change the contract
accepts. The prior version of each record is archived by the recorder, the
enactment is written once beside the scenario, and from then on the scenario
is replayed from those archived versions (:func:`materialise_sandbox` with
``record_versions``), so the record on disk keeps reproducing the change the
world holds. :func:`record_rerun` compares each enacted arm's advisory with
the reuse decisions of a run the operator dispatched afterwards, one immutable
record per run id, so a run that could only be refused does not stand in the
way of the one that can be compared.

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
from runner.dev_graph.changes import (
    ChangeRecord,
    load_snapshot,
    read_record_version,
    record_change,
)
from runner.dev_graph.impact import (
    ImpactPlan,
    plan_impact,
    read_run_records,
    write_impact_plan,
)
from runner.dev_graph.revisions import (
    ContractCheck,
    RevisionContract,
    check_revision,
    normalise_contract,
)
from runner.dev_graph.schema import DevGraphError
from runner.dev_graph.shadow import (
    advisory_verdicts,
    compare_shadow,
    read_reuse_decisions,
    write_shadow_comparison,
)
from runner.run_context import RUN_ID_RULE, is_plain_run_id

SCENARIO_SCHEMA_ID = "orch.dev_graph.change_scenario.v1"
SCENARIO_INDEX_SCHEMA_ID = "orch.dev_graph.change_scenario_index.v1"
#: Written once when a scenario's arms are recorded on the world itself.
ENACTMENT_SCHEMA_ID = "orch.dev_graph.scenario_enactment.v1"
#: Written once per dispatched run when it is compared with the enacted arms.
RERUN_SCHEMA_ID = "orch.dev_graph.scenario_rerun.v1"

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


def _month_arg(args: Mapping[str, Any], transform: str) -> int:
    to_month = args.get("to_month")
    if not isinstance(to_month, int) or isinstance(to_month, bool) or to_month < 1:
        raise _refuse(transform, f"{transform}: argument 'to_month' must be a month number")
    return to_month


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
    to_month = _month_arg(args, "move_deliverable_due_month")
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


def move_milestone_due_month(
    content: Mapping[str, Any], args: Mapping[str, Any]
) -> dict[str, Any]:
    """Move the milestone ``milestone_id`` to month ``to_month``.

    The milestone record's own change. A deliverable that moves past the
    milestone that gathers it leaves the milestone due before what it
    checks; this is the arm that follows it.
    """
    milestone_id = _arg(args, "milestone_id", "move_milestone_due_month")
    to_month = _month_arg(args, "move_milestone_due_month")
    out = copy.deepcopy(dict(content))
    found = _entry(out, "milestones", "milestone_id", milestone_id)
    if found.get("due_month") == to_month:
        raise _refuse(
            milestone_id,
            f"{milestone_id} is already due in month {to_month}; the arm would change nothing",
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
    "move_milestone_due_month": move_milestone_due_month,
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


def materialise_sandbox(
    repo_root: Path | str,
    dest: Path | str,
    *,
    record_versions: Mapping[str, str] | None = None,
    expected_snapshot_id: str | None = None,
) -> Sandbox:
    """Copy *repo_root*'s snapshot inputs into *dest* and build there.

    The copy covers exactly the files the snapshot declares as its inputs,
    so the sandbox's own snapshot id equals the live one and every later
    arm is anchored to the real world rather than to a reduction of it.
    That equality is checked, not assumed.

    *record_versions* (``{record path: archived content version}``) starts
    the sandbox from the world as it was before a recorded change: each
    named record is replaced by the version the change recorder archived
    under :data:`runner.dev_graph.changes.RECORD_VERSIONS_REL`, and the
    sandbox must then build *expected_snapshot_id* (the change's before
    snapshot) rather than the live id. This is how an enacted scenario is
    replayed over the world it was enacted on.

    Raises :class:`DevGraphError` with kind ``malformed_request`` when the
    source world declares no inputs, when *dest* already holds records, when
    *record_versions* is given without *expected_snapshot_id* (the live id
    can never be what archived versions build), when an archived version is
    not held, or when the copy does not reproduce the expected snapshot id.
    """
    source = Path(repo_root)
    target = Path(dest)
    if record_versions and expected_snapshot_id is None:
        raise _refuse(
            target.as_posix(),
            "record_versions name the world before a change; pass the expected_snapshot_id "
            "that world builds",
        )
    live = build_snapshot(source)
    if not live.inputs:
        raise _refuse(
            source.as_posix(), f"{source.as_posix()} declares no snapshot input to copy"
        )
    if target.exists() and any(target.rglob("*")):
        raise _refuse(target.as_posix(), f"{target.as_posix()} is not an empty sandbox")
    # Read every archived version before writing anything, so a version the
    # world does not hold refuses with an empty sandbox behind it.
    archived = {
        rel: read_record_version(source, version)
        for rel, version in sorted((record_versions or {}).items())
    }
    for rel in live.inputs:
        out = target / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / rel, out)
    for rel, content in archived.items():
        atomic_write_json(content, target / rel)
    expected = live.snapshot_id if expected_snapshot_id is None else expected_snapshot_id
    built = build_snapshot(target)
    if built.snapshot_id != expected:
        raise _refuse(
            target.as_posix(),
            f"the sandbox builds {built.snapshot_id} but was expected to build {expected}"
            + ("" if expected_snapshot_id is not None else f" ({source.as_posix()}'s own)"),
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
    enacted: dict[str, Any] | None = None
    """What the record says about the enactment this run replayed, or
    ``None`` for a scenario the world does not hold."""

    @property
    def arms_matched_expectations(self) -> bool:
        """Whether every arm did what the scenario declared it would.

        This says nothing about whether a ticket criterion is met. An arm
        that refused exactly as expected matched its expectation, and a
        scenario can match every one of them while the question it was run
        to answer stays open. A replay of an enacted scenario that does not
        reproduce the enacted snapshots did not do what was declared either.
        """
        reproduced = self.enacted is None or self.enacted["reproduced"]
        return reproduced and all(a.expectation_met for a in self.arms)

    def to_dict(self) -> dict[str, Any]:
        sid = self.scenario.scenario_id
        return {
            "schema_id": SCENARIO_SCHEMA_ID,
            **self.scenario.to_dict(),
            "before_snapshot_id": self.before_snapshot_id,
            "contract": self.contract.to_dict(),
            "arms_matched_expectations": self.arms_matched_expectations,
            "enacted": dict(self.enacted) if self.enacted is not None else None,
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
    enactment: Enactment | None = None,
) -> ScenarioResult:
    """Run the arms of *scenario* in a sandbox over *repo_root*, in order.

    *repo_root* is read and never written: the records change in the
    sandbox, while the run records and the run manifests are read from the
    real world.

    With *enactment*, the sandbox starts from the archived versions the
    enactment names rather than from the live records, and the result says
    whether the replay reproduced the enacted snapshots arm for arm. Without
    it, a scenario the world already holds finds nothing to change and its
    arms refuse, which is reported as an unmet expectation.

    An arm whose expectation is not met is reported, not raised, so one
    surprising arm does not hide the arms after it. Raises
    :class:`DevGraphError` only on a malformed scenario: an unknown arm
    kind, a contract the checker refuses, or an absent sandbox record.
    """
    root = Path(repo_root)
    contract = normalise_contract(dict(scenario.contract))
    if enactment is None:
        sandbox = materialise_sandbox(root, sandbox_dir)
    else:
        sandbox = materialise_sandbox(
            root,
            sandbox_dir,
            record_versions=versions_before(enactment),
            expected_snapshot_id=enactment.before_snapshot_id,
        )
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
        enacted=None if enactment is None else _enacted_summary(root, enactment, results),
    )


def versions_before(enactment: Enactment) -> dict[str, str]:
    """Each touched record's archived version before the first arm that touched it.

    The ``record_versions`` a sandbox needs to start from the world the
    enactment was made on.
    """
    versions: dict[str, str] = {}
    for arm in enactment.arms:
        versions.setdefault(arm["record_path"], arm["before_record_version"])
    return versions


def _enacted_summary(
    repo_root: Path, enactment: Enactment, results: list[ArmResult]
) -> dict[str, Any]:
    replayed = [a.change["after_snapshot_id"] if a.change else None for a in results]
    enacted = [arm["after_snapshot_id"] for arm in enactment.arms]
    return {
        "path": enactment.path,
        "before_snapshot_id": enactment.before_snapshot_id,
        "after_snapshot_id": enactment.after_snapshot_id,
        "change_ids": [arm["change_id"] for arm in enactment.arms],
        "reproduced": replayed == enacted,
        "reruns": [
            {
                "path": rerun_rel(enactment.scenario_id, rerun["run_id"]),
                "run_id": rerun["run_id"],
                "diagnostics": [shadow_label(c) for c in rerun["comparisons"]],
                "planner_narrower_rows": len(rerun["planner_narrower_rows"]),
                "investigated": rerun["investigation"] is not None,
            }
            for rerun in read_reruns(repo_root, enactment.scenario_id)
        ],
    }


# ---------------------------------------------------------------------------
# Enacting a scenario on the world itself
# ---------------------------------------------------------------------------


def enactment_rel(scenario_id: str) -> str:
    """Where a scenario's enactment is written, relative to the repo root."""
    return f"{SCENARIOS_REL}/{scenario_id}/enactment.json"


def reruns_rel(scenario_id: str) -> str:
    """The directory holding one rerun record per dispatched run."""
    return f"{SCENARIOS_REL}/{scenario_id}/reruns"


def rerun_rel(scenario_id: str, run_id: str) -> str:
    """Where the comparison against *run_id* is written, relative to the repo root."""
    return f"{reruns_rel(scenario_id)}/{run_id}.json"


@dataclass(frozen=True)
class Enactment:
    """A scenario recorded on the world itself: one change record per arm."""

    scenario_id: str
    before_snapshot_id: str
    after_snapshot_id: str
    arms: tuple[dict[str, Any], ...]
    """Per arm, in order: ``arm_id``, ``change_id``, ``change_record``,
    ``record_path``, the before and after snapshot ids and record versions,
    ``contract_verdict``, the advisory ``plan`` path and ``plan_id``, and
    ``scheduler_verdicts`` (what the advisory asks of each reuse-eligible
    node)."""
    path: str
    """Repo-relative POSIX path of the enactment record."""

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_id": ENACTMENT_SCHEMA_ID,
            "scenario_id": self.scenario_id,
            "before_snapshot_id": self.before_snapshot_id,
            "after_snapshot_id": self.after_snapshot_id,
            "arms": [dict(a) for a in self.arms],
        }


def enact_scenario(
    repo_root: Path | str,
    scenario: Scenario,
    *,
    sandbox_dir: Path | str,
    run_records: list[dict[str, Any]] | None = None,
) -> Enactment:
    """Record every arm of *scenario* on *repo_root* itself, in order.

    The scenario is first run in a sandbox under *sandbox_dir*. Only when
    every arm is a change the contract accepts does anything reach the
    world: each arm's transformation is then applied to the live record
    through :func:`runner.dev_graph.changes.record_change`, which archives
    the prior version, stores both snapshots and writes the change record.
    Each arm's advisory plan is written at its canonical path and the
    enactment record once beside the scenario.

    Raises :class:`DevGraphError` with kind ``immutable_record`` when the
    scenario is already enacted, and ``malformed_request`` when the scenario
    has no arm or an arm is a refusal probe, refused, or not accepted by the
    contract; nothing is written in those cases.

    The arms are recorded one by one, and each is a change record the moment
    it is written. Should a later arm fail (``malformed_record`` when the
    live change does not rebuild the rehearsed snapshot, which the copy
    rules out, or a plan writer refusal), the arms already recorded stay
    recorded, no enactment is written, and the error names the change ids
    on disk so the operator can reconcile them from their archived versions.
    """
    root = Path(repo_root)
    sid = scenario.scenario_id
    rel = enactment_rel(sid)
    if (root / rel).is_file():
        raise DevGraphError("immutable_record", rel, f"scenario {sid} is already enacted")
    if not scenario.arms:
        raise _refuse(sid, f"scenario {sid} has no arm to enact")

    rehearsal = run_scenario(root, scenario, sandbox_dir, run_records=run_records)
    for result in rehearsal.arms:
        where = f"{sid}/{result.arm.arm_id}"
        if result.arm.kind != "change":
            raise _refuse(where, f"arm {where} is a {result.arm.kind}; only a change is enacted")
        if result.outcome != RECORDED or result.check is None:
            assert result.refusal is not None
            raise _refuse(where, f"arm {where} refused in rehearsal: {result.refusal['message']}")
        if result.check.verdict != "accepted":
            raise _refuse(
                where,
                f"arm {where} is {result.check.verdict} by contract "
                f"{rehearsal.contract.contract_id}; only an accepted change is enacted",
            )

    arms: list[dict[str, Any]] = []
    try:
        for result in rehearsal.arms:
            arms.append(_enact_arm(root, sid, result))
    except DevGraphError as exc:
        if not arms:
            raise
        recorded = ", ".join(a["change_id"] for a in arms)
        raise DevGraphError(
            exc.kind,
            exc.offender,
            f"{exc} [partial enactment of {sid}: change records {recorded} are on the world "
            f"and no enactment was written; reconcile them from their archived versions]",
        ) from exc

    enactment = Enactment(
        scenario_id=sid,
        before_snapshot_id=arms[0]["before_snapshot_id"],
        after_snapshot_id=arms[-1]["after_snapshot_id"],
        arms=tuple(arms),
        path=rel,
    )
    atomic_write_json(enactment.to_dict(), root / rel)
    return enactment


def _enact_arm(root: Path, sid: str, result: ArmResult) -> dict[str, Any]:
    """Record one rehearsed arm on the world and plan it."""
    arm = result.arm
    assert arm.transform is not None and result.check is not None  # rehearsed by the caller
    live = json.loads((root / arm.record_path).read_text(encoding="utf-8-sig"))
    record = record_change(
        root,
        arm.record_path,
        apply_transform(arm.transform, live, arm.args),
        change_id=f"{sid}__{arm.arm_id}",
    )
    rehearsed = result.change["after_snapshot_id"] if result.change else None
    if record.after_snapshot_id != rehearsed:
        raise DevGraphError(
            "malformed_record",
            record.path,
            f"the live change builds {record.after_snapshot_id} but the rehearsal built {rehearsed}",
        )
    plan_path = write_impact_plan(root, change_id=record.change_id)[0]
    plan = json.loads(plan_path.read_text(encoding="utf-8-sig"))
    return {
        "arm_id": arm.arm_id,
        "change_id": record.change_id,
        "change_record": record.path,
        "record_path": record.record_path,
        "before_snapshot_id": record.before_snapshot_id,
        "after_snapshot_id": record.after_snapshot_id,
        "before_record_version": record.before_record_version,
        "after_record_version": record.after_record_version,
        "contract_verdict": result.check.verdict,
        "plan": plan_path.relative_to(root).as_posix(),
        "plan_id": plan["plan_id"],
        "scheduler_verdicts": advisory_verdicts(plan),
    }


def read_enactment(repo_root: Path | str, scenario_id: str) -> Enactment | None:
    """The enactment of *scenario_id*, or ``None`` when the world holds none.

    Raises :class:`DevGraphError` with kind ``malformed_record`` on a record
    of another schema or naming another scenario.
    """
    root = Path(repo_root)
    rel = enactment_rel(scenario_id)
    path = root / rel
    if not path.is_file():
        return None
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(doc, dict) or doc.get("schema_id") != ENACTMENT_SCHEMA_ID:
        raise DevGraphError("malformed_record", rel, f"not a {ENACTMENT_SCHEMA_ID} document")
    if doc.get("scenario_id") != scenario_id:
        raise DevGraphError(
            "malformed_record", rel, f"enactment names {doc.get('scenario_id')!r}, not {scenario_id!r}"
        )
    arms = doc.get("arms")
    if not isinstance(arms, list) or not arms or not all(isinstance(a, dict) for a in arms):
        raise DevGraphError("malformed_record", rel, "enactment holds no arms")
    return Enactment(
        scenario_id=scenario_id,
        before_snapshot_id=str(doc["before_snapshot_id"]),
        after_snapshot_id=str(doc["after_snapshot_id"]),
        arms=tuple(dict(a) for a in arms),
        path=rel,
    )


def read_rerun(repo_root: Path | str, scenario_id: str, run_id: str) -> dict[str, Any] | None:
    """The recorded comparison of *scenario_id* against *run_id*, or ``None``.

    Raises :class:`DevGraphError` with kind ``malformed_record`` on a record
    of another schema or naming another scenario or run.
    """
    root = Path(repo_root)
    rel = rerun_rel(scenario_id, run_id)
    path = root / rel
    if not path.is_file():
        return None
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(doc, dict) or doc.get("schema_id") != RERUN_SCHEMA_ID:
        raise DevGraphError("malformed_record", rel, f"not a {RERUN_SCHEMA_ID} document")
    if doc.get("scenario_id") != scenario_id or doc.get("run_id") != run_id:
        raise DevGraphError(
            "malformed_record",
            rel,
            f"rerun names {doc.get('scenario_id')!r} against {doc.get('run_id')!r}, "
            f"not {scenario_id!r} against {run_id!r}",
        )
    return doc


def read_reruns(repo_root: Path | str, scenario_id: str) -> list[dict[str, Any]]:
    """Every recorded rerun of *scenario_id*, ordered by run id.

    Run ids carry no order in time; the record itself is the order-free
    account of what each dispatched run was found to hold.
    """
    root = Path(repo_root)
    directory = root / reruns_rel(scenario_id)
    if not directory.is_dir():
        return []
    reruns = [read_rerun(root, scenario_id, p.stem) for p in sorted(directory.glob("*.json"))]
    return [r for r in reruns if r is not None]


def record_rerun(
    repo_root: Path | str,
    scenario_id: str,
    run_id: str,
    *,
    investigation: str | None = None,
) -> str:
    """Compare each enacted arm's advisory with the reuse decisions of *run_id*.

    One shadow comparison per arm, written at its canonical path by
    :func:`runner.dev_graph.shadow.write_shadow_comparison`; a comparison
    that cannot be made is recorded as a refusal, never as agreement. Every
    ``planner_narrower`` row is listed for investigation, and
    *investigation* is the operator's recorded reason once there is one.
    Returns the repo-relative path of the rerun record, written once per
    run id: a run that could only be refused stays recorded and does not
    stand in the way of recording the next run.

    Raises :class:`DevGraphError` with kind ``malformed_request`` when the
    scenario is not enacted or *run_id* is not a plain identifier (it names
    the record file), and ``immutable_record`` when that run is already
    recorded.
    """
    root = Path(repo_root)
    if not is_plain_run_id(run_id):
        raise _refuse(str(run_id), f"run id {run_id!r} is not a plain identifier: {RUN_ID_RULE}")
    rel = rerun_rel(scenario_id, run_id)
    if (root / rel).is_file():
        raise DevGraphError(
            "immutable_record", rel, f"the rerun of {scenario_id} against {run_id} is already recorded"
        )
    enactment = read_enactment(root, scenario_id)
    if enactment is None:
        raise _refuse(enactment_rel(scenario_id), f"scenario {scenario_id} is not enacted")

    comparisons: list[dict[str, Any]] = []
    for arm in enactment.arms:
        entry: dict[str, Any] = {
            "arm_id": arm["arm_id"],
            "change_id": arm["change_id"],
            "plan_id": arm["plan_id"],
            "comparison": None,
            "diagnostic": None,
            "rows": [],
            "refused": None,
        }
        try:
            written = write_shadow_comparison(root, plan_id=arm["plan_id"], run_id=run_id)[0]
        except DevGraphError as exc:
            entry["refused"] = _refusal(exc)
        else:
            comparison = json.loads(written.read_text(encoding="utf-8-sig"))
            entry["comparison"] = written.relative_to(root).as_posix()
            entry["diagnostic"] = comparison["diagnostic"]
            entry["rows"] = list(comparison["rows"])
        comparisons.append(entry)

    doc = {
        "schema_id": RERUN_SCHEMA_ID,
        "scenario_id": scenario_id,
        "enactment": enactment.path,
        "run_id": run_id,
        "comparisons": comparisons,
        "planner_narrower_rows": [
            {"arm_id": c["arm_id"], **row}
            for c in comparisons
            for row in c["rows"]
            if row.get("diagnostic") == "planner_narrower"
        ],
        "investigation": investigation,
    }
    atomic_write_json(doc, root / rel)
    return rel


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
                "enacted": None if result.enacted is None else result.enacted["path"],
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
