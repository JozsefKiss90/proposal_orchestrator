"""The instance-two architecture seeds, held to what they actually contain.

The ticket "Architecture seeds and the uncertainty ledger" in
`plans/dev_graph_demo_tickets.md` writes the six Tier 3 seeds Phases 3 to 6
read, appends to the uncertainty ledger, and freezes Tier 3. Its five
acceptance criteria are all mechanical, so all five are checked here rather
than asserted:

* **every objective maps to an expected outcome span in Tier 2B.**
  `TestObjectives` resolves each reference against the call extract and fails
  on one that lands nowhere.
* **every task names a lead partner, and one task per work package involves two
  or more partners.** `TestTasks` holds both halves against
  `consortium/partners.json`.
* **the ledger lists each unconfirmed partner and each Assumed value, with the
  reason.** `TestTheLedger`.
* **the leakage test passes on all Tier 3 files and the vault.**
  `TestAnonymity`, on the same `ok`-versus-`clean` split the source-materials
  ticket recorded.
* **Tier 3 is frozen and its fingerprint is recorded.** `TestTheFreeze` checks
  that every Tier 3 artifact is fingerprinted by exactly one freeze record, and
  that each fingerprint still matches.

Two further groups guard what the *next* ticket needs from these files.
`TestTheBuilderReadsThem` builds a real dev-graph snapshot twice, because the
first dev-graph snapshot on the demo world is the ticket this one unblocks.
`TestTheDesignIsRealEnough` pins the shape the ticket asks for: at least six
work packages, cross-partner tasks, and deliverables and milestones that depend
on each other across work packages.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from runner.dev_graph.builder import build_snapshot
from runner.leakage_scan import scan_tree
from runner.paths import find_repo_root
from tests._tier_sources import STATUSES, digest, resolve_ref

REPO = find_repo_root()

TIER3 = REPO / "docs/tier3_project_instantiation"
SEEDS = TIER3 / "architecture_inputs"

OBJECTIVES = SEEDS / "objectives.json"
OUTCOMES = SEEDS / "outcomes.json"
IMPACTS = SEEDS / "impacts.json"
WP_SEED = SEEDS / "workpackage_seed.json"
MILESTONES = SEEDS / "milestones_seed.json"
RISKS = SEEDS / "risks.json"

PARTNERS = TIER3 / "consortium/partners.json"
LEDGER = TIER3 / "working_assumptions.json"
CALL_EXTRACT = (
    REPO
    / "docs/tier2b_topic_and_call_sources/call_extracts"
    / "HORIZON-CL6-2027-01-BIODIV-01.json"
)

DECISION = (
    REPO
    / "docs/tier4_orchestration_state/decision_log"
    / "demo-architecture-seeds_2026-09-30.json"
)
CONCEPT_DECISION = (
    REPO
    / "docs/tier4_orchestration_state/decision_log"
    / "demo-concept_2026-09-30.json"
)
VALIDATION_REPORT = (
    REPO
    / "docs/tier4_orchestration_state/validation_reports"
    / "demo-architecture-seeds_2026-09-30.json"
)

#: The digest basis both freeze records declare, as the token `digest()` takes
#: and as the phrase the records state it in. core.autocrlf is true here, so a
#: raw digest would identify the platform rather than the content.
DIGEST_BASIS = "lf_normalised_bytes"
DIGEST_BASIS_PHRASE = "LF-normalised bytes"

#: Tier 3 files that carry no project fact and so are outside the freeze.
NOT_A_TIER3_ARTIFACT = frozenset(
    {".gitkeep", "working_assumptions.example.json"}
)

#: Tier 3 subtrees that belong to another instance. The MSCA-DN pre-evaluation
#: case keeps its originals and fidelity register beside the demo's source
#: materials (plans/msca_dn_pre_evaluation_spec.md, decision 2) but has its own
#: graph root under workspaces/msca_dn/ and its own records; the demo's freeze
#: rule does not govern it.
OTHER_INSTANCE_TIER3_DIRS = ("docs/tier3_project_instantiation/source_materials/msca_dn/",)


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _live_freeze_records() -> dict[str, dict]:
    """Every freeze record in the decision log that nothing supersedes.

    A freeze changes by a new entry that supersedes the old one and carries the
    fingerprints, never by an edit in place — the records say so themselves in
    their ``unfreezing`` clause. So the current freeze cannot be found at a fixed
    filename: it has to be resolved through the ``supersedes`` chain, or these
    tests read a stale record and pass on a freeze nobody is keeping.
    """
    records: dict[str, dict] = {}
    superseded: set[str] = set()
    for path in sorted((REPO / "docs/tier4_orchestration_state/decision_log").glob("*.json")):
        entry = _read(path)
        if not isinstance(entry, dict):
            continue
        superseded.update(entry.get("supersedes") or [])
        if isinstance(entry.get("freeze_record"), dict):
            records[path.relative_to(REPO).as_posix()] = entry["freeze_record"]
    return {rel: rec for rel, rec in records.items() if rel not in superseded}


def _live_freeze_for(artifact: Path) -> dict:
    """The one live freeze record that fingerprints *artifact*.

    Resolving by content rather than by filename is what makes the supersession
    chain usable: the record that holds a file's fingerprint is the record that
    governs it, whatever the entry is called.
    """
    rel = artifact.relative_to(REPO).as_posix()
    holders = {
        path: record
        for path, record in _live_freeze_records().items()
        if rel in record["artifacts"]
    }
    assert holders, f"no live freeze record fingerprints {rel}"
    assert len(holders) == 1, f"{rel} is fingerprinted by {sorted(holders)}"
    return next(iter(holders.values()))


@pytest.fixture(scope="module")
def objectives() -> list[dict[str, Any]]:
    return _read(OBJECTIVES)["objectives"]


@pytest.fixture(scope="module")
def work_packages() -> list[dict[str, Any]]:
    return _read(WP_SEED)["work_packages"]


@pytest.fixture(scope="module")
def milestones() -> list[dict[str, Any]]:
    return _read(MILESTONES)["milestones"]


@pytest.fixture(scope="module")
def partner_ids() -> set[str]:
    return {p["partner_id"] for p in _read(PARTNERS)["partners"]}


@pytest.fixture(scope="module")
def call() -> dict[str, Any]:
    return _read(CALL_EXTRACT)


@pytest.fixture(scope="module")
def tasks(work_packages: list[dict[str, Any]]) -> list[tuple[str, dict[str, Any]]]:
    return [(wp["wp_id"], t) for wp in work_packages for t in wp["tasks"]]


@pytest.fixture(scope="module")
def deliverables(
    work_packages: list[dict[str, Any]]
) -> dict[str, tuple[str, dict[str, Any]]]:
    return {
        d["deliverable_id"]: (wp["wp_id"], d)
        for wp in work_packages
        for d in wp["deliverables"]
    }


# ---------------------------------------------------------------------------
# The six seeds exist and say where they came from
# ---------------------------------------------------------------------------


class TestTheSeedsExist:
    @pytest.mark.parametrize(
        "path",
        [OBJECTIVES, OUTCOMES, IMPACTS, WP_SEED, MILESTONES, RISKS],
        ids=lambda p: p.name,
    )
    def test_the_seed_is_present_and_carries_its_collection(self, path: Path) -> None:
        assert path.is_file(), f"{path.name} is absent"
        record = _read(path)
        collection = record.get("_provenance", {}).get("collection_key")
        assert collection, f"{path.name} declares no collection_key"
        assert isinstance(record.get(collection), list) and record[collection], (
            f"{path.name} carries no {collection}"
        )

    @pytest.mark.parametrize(
        "path",
        [OBJECTIVES, OUTCOMES, IMPACTS, WP_SEED, MILESTONES, RISKS],
        ids=lambda p: p.name,
    )
    def test_the_seed_says_where_its_shape_comes_from(self, path: Path) -> None:
        """The convention partners.json, roles.json and sources.json set: a Tier 3
        artifact with no declared schema says so and names its consumers, rather
        than leaving a reader to guess whether the shape is canonical."""
        ref = _read(path)["_provenance"]["schema_ref"]
        assert ref.strip(), f"{path.name} declares no schema_ref"
        assert "artifact_schema_specification.yaml" in ref, path.name

    @pytest.mark.parametrize(
        "path",
        [OBJECTIVES, OUTCOMES, IMPACTS, WP_SEED, MILESTONES, RISKS],
        ids=lambda p: p.name,
    )
    def test_every_declared_status_is_one_of_the_four(self, path: Path) -> None:
        """A seed that invents a fifth status has left CLAUDE.md §12.2 behind."""
        bad = sorted(
            {
                value
                for key, value in _iter_pairs(_read(path))
                if key == "validation_status" and value not in STATUSES
            }
        )
        assert not bad, f"{path.name} carries statuses outside §12.2: {bad}"


def _iter_pairs(node: object):
    if isinstance(node, dict):
        for key, value in node.items():
            if isinstance(value, str):
                yield key, value
            else:
                yield from _iter_pairs(value)
    elif isinstance(node, list):
        for value in node:
            yield from _iter_pairs(value)


# ---------------------------------------------------------------------------
# Box 1 — every objective maps to an expected outcome span in Tier 2B
# ---------------------------------------------------------------------------


class TestObjectives:
    def test_every_objective_names_an_expected_outcome(
        self, objectives: list[dict[str, Any]], call: dict[str, Any]
    ) -> None:
        bare = [
            o["objective_id"]
            for o in objectives
            if not o.get("tier2b_expected_outcome_refs")
        ]
        assert not bare, f"objectives with no expected outcome reference: {bare}"

    def test_every_reference_resolves_to_call_text(
        self, objectives: list[dict[str, Any]], call: dict[str, Any]
    ) -> None:
        """A reference that lands nowhere is a citation nobody can follow."""
        dangling = []
        for o in objectives:
            for ref in o["tier2b_expected_outcome_refs"]:
                target = resolve_ref(call, ref)
                if not isinstance(target, str) or not target.strip():
                    dangling.append(f"{o['objective_id']} -> {ref}")
        assert not dangling, f"expected outcome references resolve nowhere: {dangling}"

    def test_the_references_point_at_expected_outcomes(
        self, objectives: list[dict[str, Any]]
    ) -> None:
        """The box asks for an expected outcome span, not any span at all."""
        wrong = [
            f"{o['objective_id']} -> {ref}"
            for o in objectives
            for ref in o["tier2b_expected_outcome_refs"]
            if not ref.startswith("$.expected_outcomes[")
        ]
        assert not wrong, f"references that are not expected outcomes: {wrong}"

    def test_every_expected_outcome_is_answered_by_an_objective(
        self, objectives: list[dict[str, Any]], call: dict[str, Any]
    ) -> None:
        """The other direction. An outcome no objective answers is a gap the
        Phase 2 gate would find later and more expensively."""
        claimed = {
            ref for o in objectives for ref in o["tier2b_expected_outcome_refs"]
        }
        unanswered = [
            f"$.expected_outcomes[{i}]"
            for i in range(len(call["expected_outcomes"]))
            if f"$.expected_outcomes[{i}]" not in claimed
        ]
        assert not unanswered, f"expected outcomes no objective answers: {unanswered}"

    def test_every_objective_is_carried_by_a_work_package(
        self, objectives: list[dict[str, Any]], work_packages: list[dict[str, Any]]
    ) -> None:
        carried = {obj for wp in work_packages for obj in wp["objectives"]}
        orphans = [
            o["objective_id"] for o in objectives if o["objective_id"] not in carried
        ]
        assert not orphans, f"objectives no work package contributes to: {orphans}"

    def test_no_work_package_names_an_objective_that_does_not_exist(
        self, objectives: list[dict[str, Any]], work_packages: list[dict[str, Any]]
    ) -> None:
        known = {o["objective_id"] for o in objectives}
        dangling = [
            f"{wp['wp_id']} -> {obj}"
            for wp in work_packages
            for obj in wp["objectives"]
            if obj not in known
        ]
        assert not dangling, f"work packages name unknown objectives: {dangling}"


# ---------------------------------------------------------------------------
# Box 2 — every task names a lead, and one task per WP involves two partners
# ---------------------------------------------------------------------------


class TestTasks:
    def test_every_task_names_a_responsible_partner(
        self, tasks: list[tuple[str, dict[str, Any]]], partner_ids: set[str]
    ) -> None:
        bad = [
            f"{wp}/{t['task_id']} -> {t.get('responsible_partner')!r}"
            for wp, t in tasks
            if t.get("responsible_partner") not in partner_ids
        ]
        assert not bad, f"tasks whose lead is not a partner pseudonym: {bad}"

    def test_every_contributing_partner_exists(
        self, tasks: list[tuple[str, dict[str, Any]]], partner_ids: set[str]
    ) -> None:
        bad = [
            f"{wp}/{t['task_id']} -> {c}"
            for wp, t in tasks
            for c in t.get("contributing_partners", [])
            if c not in partner_ids
        ]
        assert not bad, f"tasks naming unknown contributors: {bad}"

    def test_no_task_lists_its_own_lead_as_a_contributor(
        self, tasks: list[tuple[str, dict[str, Any]]]
    ) -> None:
        """The lead is already on the task. Repeating it would make a
        single-partner task read as a cross-partner one."""
        doubled = [
            f"{wp}/{t['task_id']}"
            for wp, t in tasks
            if t["responsible_partner"] in t.get("contributing_partners", [])
        ]
        assert not doubled, f"tasks listing their own lead as a contributor: {doubled}"

    def test_every_work_package_has_a_cross_partner_task(
        self, work_packages: list[dict[str, Any]]
    ) -> None:
        thin = [
            wp["wp_id"]
            for wp in work_packages
            if not any(t.get("contributing_partners") for t in wp["tasks"])
        ]
        assert not thin, f"work packages with no cross-partner task: {thin}"

    def test_every_work_package_lead_is_a_partner(
        self, work_packages: list[dict[str, Any]], partner_ids: set[str]
    ) -> None:
        bad = [
            f"{wp['wp_id']} -> {wp.get('lead_partner')!r}"
            for wp in work_packages
            if wp.get("lead_partner") not in partner_ids
        ]
        assert not bad, f"work packages whose lead is not a partner: {bad}"

    def test_every_partner_leads_at_least_one_task(
        self, tasks: list[tuple[str, dict[str, Any]]], partner_ids: set[str]
    ) -> None:
        """A partner in the consortium that leads nothing is a partner the
        evaluator will ask about."""
        leads = {t["responsible_partner"] for _, t in tasks}
        idle = sorted(partner_ids - leads)
        assert not idle, f"partners that lead no task: {idle}"


# ---------------------------------------------------------------------------
# The design the ticket asks for
# ---------------------------------------------------------------------------


class TestTheDesignIsRealEnough:
    """"Enough tasks and cross-partner assignments to exercise the planner"."""

    def test_there_are_at_least_six_work_packages(
        self, work_packages: list[dict[str, Any]]
    ) -> None:
        assert len(work_packages) >= 6, len(work_packages)

    def test_the_work_package_count_respects_the_instrument(
        self, work_packages: list[dict[str, Any]]
    ) -> None:
        """Tier 2A governs the maximum, per CLAUDE.md §11.2. It is null for RIA,
        and this check fails the moment a later extraction fills it in below the
        design."""
        registry = _read(
            REPO / "docs/tier2a_instrument_schemas/extracted/section_schema_registry.json"
        )
        ria = next(
            entry
            for entry in registry["instruments"]
            if entry["instrument_type"] == "RIA"
        )
        cap = ria["max_work_packages"]
        if cap is None:
            pytest.skip("Tier 2A states no maximum work package count for RIA")
        assert len(work_packages) <= cap

    def test_every_work_package_has_a_deliverable(
        self, work_packages: list[dict[str, Any]]
    ) -> None:
        bare = [wp["wp_id"] for wp in work_packages if not wp["deliverables"]]
        assert not bare, f"work packages with no deliverable: {bare}"

    def test_tasks_depend_on_tasks_in_other_work_packages(
        self, work_packages: list[dict[str, Any]]
    ) -> None:
        """Without a cross-WP edge the planner has nothing to propagate along,
        which is what this demo exists to exercise."""
        home = {
            t["task_id"]: wp["wp_id"] for wp in work_packages for t in wp["tasks"]
        }
        crossing = [
            f"{home[t['task_id']]}/{t['task_id']} <- {dep}"
            for wp in work_packages
            for t in wp["tasks"]
            for dep in t.get("dependencies", [])
            if home.get(dep) not in (None, wp["wp_id"])
        ]
        assert crossing, "no task depends on a task in another work package"

    def test_the_listed_cross_boundary_edges_are_the_real_ones(
        self, work_packages: list[dict[str, Any]]
    ) -> None:
        """The seed lists its cross-work-package edges with a reason each.

        The task `dependencies` arrays are authoritative; the list exists only
        to carry the reason, which an array of ids has no room for. Two copies
        of the same fact drift, so this holds them equal in both directions.
        """
        home = {
            t["task_id"]: wp["wp_id"] for wp in work_packages for t in wp["tasks"]
        }
        real = {
            (t["task_id"], dep)
            for wp in work_packages
            for t in wp["tasks"]
            for dep in t["dependencies"]
            if home[dep] != wp["wp_id"]
        }
        seed = _read(WP_SEED)
        listed = {
            (e["task"], e["depends_on"])
            for e in seed["cross_work_package_dependencies"]
        }
        assert listed == real, (
            f"listed but not real: {sorted(listed - real)}; "
            f"real but not listed: {sorted(real - listed)}"
        )

    def test_every_listed_edge_gives_a_reason(self) -> None:
        bare = [
            f"{e['task']} <- {e['depends_on']}"
            for e in _read(WP_SEED)["cross_work_package_dependencies"]
            if not e.get("why", "").strip()
        ]
        assert not bare, f"cross-boundary edges with no reason: {bare}"

    def test_every_task_dependency_names_a_task(
        self, work_packages: list[dict[str, Any]]
    ) -> None:
        known = {t["task_id"] for wp in work_packages for t in wp["tasks"]}
        dangling = [
            f"{t['task_id']} <- {dep}"
            for wp in work_packages
            for t in wp["tasks"]
            for dep in t.get("dependencies", [])
            if dep not in known
        ]
        assert not dangling, f"task dependencies naming no task: {dangling}"

    def test_no_task_depends_on_itself(
        self, work_packages: list[dict[str, Any]]
    ) -> None:
        loops = [
            t["task_id"]
            for wp in work_packages
            for t in wp["tasks"]
            if t["task_id"] in t.get("dependencies", [])
        ]
        assert not loops, f"tasks that depend on themselves: {loops}"

    def test_a_milestone_gathers_deliverables_from_more_than_one_work_package(
        self,
        milestones: list[dict[str, Any]],
        deliverables: dict[str, tuple[str, dict[str, Any]]],
    ) -> None:
        crossing = [
            m["milestone_id"]
            for m in milestones
            if len({deliverables[d][0] for d in m["deliverables"]}) > 1
        ]
        assert crossing, "no milestone gathers deliverables from two work packages"

    def test_every_milestone_names_deliverables_that_exist(
        self,
        milestones: list[dict[str, Any]],
        deliverables: dict[str, tuple[str, dict[str, Any]]],
    ) -> None:
        dangling = [
            f"{m['milestone_id']} -> {d}"
            for m in milestones
            for d in m["deliverables"]
            if d not in deliverables
        ]
        assert not dangling, f"milestones naming unknown deliverables: {dangling}"

    def test_every_deliverable_is_produced_by_a_task_of_its_own_work_package(
        self, work_packages: list[dict[str, Any]]
    ) -> None:
        stray = []
        for wp in work_packages:
            own = {t["task_id"] for t in wp["tasks"]}
            for d in wp["deliverables"]:
                produced = d.get("produced_by") or []
                if not produced:
                    stray.append(f"{wp['wp_id']}/{d['deliverable_id']}: no producer")
                for task_id in produced:
                    if task_id not in own:
                        stray.append(
                            f"{wp['wp_id']}/{d['deliverable_id']} <- {task_id}"
                        )
        assert not stray, f"deliverables and their producers disagree: {stray}"

    def test_every_deliverable_is_gathered_by_a_milestone(
        self,
        milestones: list[dict[str, Any]],
        deliverables: dict[str, tuple[str, dict[str, Any]]],
    ) -> None:
        gathered = {d for m in milestones for d in m["deliverables"]}
        loose = sorted(set(deliverables) - gathered)
        assert not loose, f"deliverables no milestone validates: {loose}"


# ---------------------------------------------------------------------------
# The timeline fits the duration the operator chose
# ---------------------------------------------------------------------------


class TestTheTimeline:
    @pytest.fixture(scope="class")
    def duration(self) -> int:
        bound = _read(TIER3 / "call_binding/selected_call.json")
        return bound["project_duration_months"]

    def test_every_work_package_fits_the_duration(
        self, work_packages: list[dict[str, Any]], duration: int
    ) -> None:
        over = [
            f"{wp['wp_id']} M{wp['start_month']}-M{wp['end_month']}"
            for wp in work_packages
            if not 1 <= wp["start_month"] <= wp["end_month"] <= duration
        ]
        assert not over, f"work packages outside M1-M{duration}: {over}"

    def test_every_task_fits_its_work_package(
        self, work_packages: list[dict[str, Any]]
    ) -> None:
        over = [
            f"{wp['wp_id']}/{t['task_id']} M{t['start_month']}-M{t['end_month']} "
            f"outside M{wp['start_month']}-M{wp['end_month']}"
            for wp in work_packages
            for t in wp["tasks"]
            if not (
                wp["start_month"] <= t["start_month"] <= t["end_month"] <= wp["end_month"]
            )
        ]
        assert not over, over

    def test_a_deliverable_is_not_due_before_its_producers_start(
        self, work_packages: list[dict[str, Any]]
    ) -> None:
        starts = {
            t["task_id"]: t["start_month"] for wp in work_packages for t in wp["tasks"]
        }
        early = [
            f"{d['deliverable_id']} due M{d['due_month']}, {task_id} starts "
            f"M{starts[task_id]}"
            for wp in work_packages
            for d in wp["deliverables"]
            for task_id in d["produced_by"]
            if d["due_month"] < starts[task_id]
        ]
        assert not early, early

    def test_at_least_one_producer_has_finished_by_the_due_month(
        self, work_packages: list[dict[str, Any]]
    ) -> None:
        """A deliverable whose every producer is still running has nothing
        finished behind it.

        Not every producer need be finished. A standing task — the coordination
        interface runs M1 to M48 — contributes to a plan due long before it
        ends. One producer finished is what makes the due month meaningful.
        """
        ends = {
            t["task_id"]: t["end_month"] for wp in work_packages for t in wp["tasks"]
        }
        empty = [
            d["deliverable_id"]
            for wp in work_packages
            for d in wp["deliverables"]
            if not any(ends[t] <= d["due_month"] for t in d["produced_by"])
        ]
        assert not empty, f"deliverables with no finished producer: {empty}"

    def test_a_task_does_not_start_before_the_task_it_depends_on_starts(
        self, work_packages: list[dict[str, Any]]
    ) -> None:
        """A dependency the schedule contradicts is a dependency the Phase 4
        gate would reject as an unresolved critical path.

        The rule is start-to-start, not finish-to-start. Dependent tasks here
        overlap deliberately: the crosswalk work begins while the protocol it
        builds on is still being agreed, which is how a protocol gets tested
        before it is frozen. A task starting *before* its dependency is the
        contradiction.
        """
        starts = {
            t["task_id"]: t["start_month"] for wp in work_packages for t in wp["tasks"]
        }
        broken = [
            f"{t['task_id']} starts M{starts[t['task_id']]}, {dep} starts "
            f"M{starts[dep]}"
            for wp in work_packages
            for t in wp["tasks"]
            for dep in t.get("dependencies", [])
            if starts[t["task_id"]] < starts[dep]
        ]
        assert not broken, broken

    def test_a_milestone_is_not_due_before_the_deliverables_it_gathers(
        self,
        milestones: list[dict[str, Any]],
        deliverables: dict[str, tuple[str, dict[str, Any]]],
    ) -> None:
        early = [
            f"{m['milestone_id']} due M{m['due_month']}, {d} due "
            f"M{deliverables[d][1]['due_month']}"
            for m in milestones
            for d in m["deliverables"]
            if m["due_month"] < deliverables[d][1]["due_month"]
        ]
        assert not early, early

    def test_the_last_milestone_lands_inside_the_duration(
        self, milestones: list[dict[str, Any]], duration: int
    ) -> None:
        assert max(m["due_month"] for m in milestones) <= duration


# ---------------------------------------------------------------------------
# The seed speaks to both of its consumers
# ---------------------------------------------------------------------------


class TestBothConsumersCanReadTheWorkPackages:
    """`workpackage_seed.json` has two readers that disagree on the key.

    `runner/dev_graph/builder.py` reads `wp_id`; `runner/dependency_normalizer.py`
    reads `id`. Neither is wrong and neither is changed by this ticket, so the
    seed carries both, and this pins them equal so a later edit cannot split
    them silently.
    """

    def test_every_work_package_carries_both_keys(
        self, work_packages: list[dict[str, Any]]
    ) -> None:
        mismatched = [
            f"{wp.get('wp_id')!r} / {wp.get('id')!r}"
            for wp in work_packages
            if wp.get("wp_id") != wp.get("id") or not wp.get("wp_id")
        ]
        assert not mismatched, f"wp_id and id disagree: {mismatched}"

    def test_the_dependency_normalizer_reads_every_work_package(
        self, work_packages: list[dict[str, Any]]
    ) -> None:
        from runner.dependency_normalizer import _build_wp_bounds

        bounds = _build_wp_bounds(_read(WP_SEED))
        assert set(bounds) == {wp["wp_id"] for wp in work_packages}


# ---------------------------------------------------------------------------
# What the next ticket needs
# ---------------------------------------------------------------------------


class TestTheBuilderReadsThem:
    @pytest.fixture(scope="class")
    def snapshot(self):
        return build_snapshot(REPO)

    def test_the_snapshot_builds_over_the_populated_repository(self, snapshot) -> None:
        assert snapshot.nodes

    def test_a_second_build_gives_the_same_snapshot_id(self, snapshot) -> None:
        assert build_snapshot(REPO).snapshot_id == snapshot.snapshot_id

    def test_the_seeds_are_among_the_inputs(self, snapshot) -> None:
        for path in (OBJECTIVES, WP_SEED, MILESTONES):
            rel = path.relative_to(REPO).as_posix()
            assert rel in snapshot.inputs, rel

    def test_every_work_package_and_task_becomes_a_node(
        self, snapshot, work_packages: list[dict[str, Any]]
    ) -> None:
        ids = {n["id"] for n in snapshot.nodes}
        missing = [wp["wp_id"] for wp in work_packages if wp["wp_id"] not in ids]
        missing += [
            t["task_id"]
            for wp in work_packages
            for t in wp["tasks"]
            if t["task_id"] not in ids
        ]
        assert not missing, f"records the builder did not turn into nodes: {missing}"

    def test_every_work_package_constraint_names_a_source(
        self, work_packages: list[dict[str, Any]]
    ) -> None:
        """`constrained_by` runs work_package -> source, so a constraint that
        names anything else fails the closed schema at build time."""
        known = {
            s["source_id"]
            for s in _read(TIER3 / "source_materials/sources.json")["sources"]
        }
        dangling = [
            f"{wp['wp_id']} -> {c}"
            for wp in work_packages
            for c in wp.get("constraints", [])
            if c not in known
        ]
        assert not dangling, f"constraints naming no source: {dangling}"


# ---------------------------------------------------------------------------
# The destination expected impacts, counted from the source
# ---------------------------------------------------------------------------

#: The bullet character the work programme uses in its expected-impact list.
BULLET = "•"


class TestTheDestinationExpectedImpacts:
    """How many expected impacts the destination sets, counted rather than stated.

    The first draft of impacts.json said seven. There are six. The fourth
    bullet straddles the page break, and its tail — "legislation and better
    valuation of ecosystem services…" — carries no bullet marker, so counting
    it as a separate impact invented a call constraint the source does not make
    (CLAUDE.md §13.2).

    Counting the markers in the replayed text is the only way to hold the number
    to the document. Every record that states it is checked against this count.
    """

    @pytest.fixture(scope="class")
    def pages(self) -> dict[str, str]:
        index = _read(TIER3 / "source_materials/sources.json")
        return {
            s["source_id"]: s["text"]
            for s in index["sources"]
            if s["kind"] == "call_document_page"
        }

    @pytest.fixture(scope="class")
    def counted(self, pages: dict[str, str]) -> int:
        """Bullets between the expected-impact lead-in and the next heading."""
        p47, p48 = pages["SRC-WP9-P47"], pages["SRC-WP9-P48"]
        start = p47.index("following expected impacts")
        end = p48.index("2026 Consolidating")
        return p47[start:].count(BULLET) + p48[:end].count(BULLET)

    def test_the_source_carries_six(self, counted: int) -> None:
        assert counted == 6

    def test_the_tail_after_the_page_break_carries_no_bullet(
        self, pages: dict[str, str]
    ) -> None:
        """This is what makes it a continuation and not a seventh impact."""
        p48 = pages["SRC-WP9-P48"]
        tail = p48.index("legislation and better valuation")
        assert BULLET not in p48[:tail]

    def test_the_seed_records_exactly_the_counted_impacts(
        self, counted: int
    ) -> None:
        declared = _read(IMPACTS)["destination_expected_impacts"]["impacts"]
        assert len(declared) == counted

    def test_every_declared_impact_quotes_a_span_that_resolves(self) -> None:
        index = _read(TIER3 / "source_materials/sources.json")
        spans = {
            sp["span_id"]: sp["quote"]
            for s in index["sources"]
            for sp in (s.get("spans") or [])
        }
        block = _read(IMPACTS)["destination_expected_impacts"]
        declared = list(block["impacts"]) + [block["pathway_statement"]]
        wrong = [
            d.get("impact_ref", "pathway_statement")
            for d in declared
            if spans.get(d["span_ref"]) != d["quote"]
        ]
        assert not wrong, f"impact quotes that are not their span's text: {wrong}"

    def test_the_continuation_span_is_not_also_a_separate_impact(self) -> None:
        """The double count was visible in the artifact: the tail span appeared
        both as the fourth impact's continuation and as a seventh impact."""
        block = _read(IMPACTS)["destination_expected_impacts"]
        continuations = {
            d["continues_in"] for d in block["impacts"] if d.get("continues_in")
        }
        as_impacts = {d["span_ref"] for d in block["impacts"]}
        assert not (continuations & as_impacts), (
            f"a continuation span is also recorded as an impact: "
            f"{sorted(continuations & as_impacts)}"
        )

    def test_every_impact_pathway_names_a_declared_impact(self) -> None:
        record = _read(IMPACTS)
        known = {
            d["impact_ref"] for d in record["destination_expected_impacts"]["impacts"]
        }
        dangling = [
            f"{p['impact_id']} -> {ref}"
            for p in record["impacts"]
            for ref in p["addresses_destination_impacts"]
            if ref not in known
        ]
        assert not dangling, f"pathways naming no declared impact: {dangling}"

    def test_the_span_requirement_refs_and_the_seed_agree(self) -> None:
        """The link from a span to an impact runs through requirement_refs, which
        runner/source_index.py does not validate. Nothing else checks that the
        two sides use the same identifiers, so this does."""
        index = _read(TIER3 / "source_materials/sources.json")
        in_spans = {
            ref
            for s in index["sources"]
            for sp in (s.get("spans") or [])
            for ref in sp.get("requirement_refs", [])
            if ref.startswith("DEST-IMPACT-")
        }
        in_seed = {
            d["impact_ref"]
            for d in _read(IMPACTS)["destination_expected_impacts"]["impacts"]
        }
        assert in_spans == in_seed, (
            f"spans carry {sorted(in_spans)}, the seed carries {sorted(in_seed)}"
        )

    def test_no_record_claims_seven(self) -> None:
        """Eight records stated the wrong number. This is the sweep that would
        have caught it."""
        paths = [
            IMPACTS,
            LEDGER,
            TIER3 / "source_materials/sources.json",
            VALIDATION_REPORT,
            DECISION,
            REPO / "docs/tier4_orchestration_state/validation_reports"
            / "demo-source-materials_2026-09-30.json",
            REPO / "tools/author_demo_sources.py",
        ]
        offenders = [
            p.relative_to(REPO).as_posix()
            for p in paths
            if "seven expected impacts" in p.read_text(encoding="utf-8-sig")
        ]
        assert not offenders, f"records still claiming seven: {offenders}"


# ---------------------------------------------------------------------------
# Box 3 — the uncertainty ledger
# ---------------------------------------------------------------------------


class TestTheLedger:
    @pytest.fixture(scope="class")
    def declarations(self) -> list[dict[str, Any]]:
        return _read(LEDGER)["declarations"]

    def test_the_engine_may_not_write_it(self) -> None:
        assert _read(LEDGER)["provenance_class"] == "manually_placed"

    def test_every_key_is_unique(self, declarations: list[dict[str, Any]]) -> None:
        keys = [d["key"] for d in declarations]
        assert len(keys) == len(set(keys)), "a declaration key is declared twice"

    def test_every_declaration_carries_a_reason(
        self, declarations: list[dict[str, Any]]
    ) -> None:
        bare = [d["key"] for d in declarations if not d.get("rationale", "").strip()]
        assert not bare, f"declarations with no reason: {bare}"

    def test_every_unconfirmed_partner_is_declared(
        self, declarations: list[dict[str, Any]], partner_ids: set[str]
    ) -> None:
        declared = {d["key"] for d in declarations}
        missing = sorted(
            f"{pid}_participation"
            for pid in partner_ids
            if f"{pid}_participation" not in declared
        )
        assert not missing, f"partners with no declaration: {missing}"

    def test_the_declared_scale_matches_the_work_plan(
        self,
        declarations: list[dict[str, Any]],
        work_packages: list[dict[str, Any]],
        milestones: list[dict[str, Any]],
        deliverables: dict[str, tuple[str, dict[str, Any]]],
    ) -> None:
        """The scale declaration states counts, so it goes stale like any other
        derived statement. It said 34 tasks when there were 35."""
        declared = next(
            d["value"] for d in declarations if d["key"] == "project_scale"
        )
        tasks = sum(len(wp["tasks"]) for wp in work_packages)
        for count, noun in (
            (len(work_packages), "work packages"),
            (tasks, "tasks"),
            (len(deliverables), "deliverables"),
            (len(milestones), "milestones"),
        ):
            assert f"{count} {noun}" in declared, (
                f"the scale declaration does not say '{count} {noun}': {declared!r}"
            )

    def test_the_effort_shares_this_ticket_leaves_open_are_declared(
        self, declarations: list[dict[str, Any]]
    ) -> None:
        """The seeds carry an effort split nobody has agreed. Undeclared, it
        would read as a Confirmed consortium decision."""
        declared = {d["key"] for d in declarations}
        assert "effort_shares" in declared

    def test_the_shared_reader_accepts_it(self) -> None:
        from runner.working_assumptions import load_working_assumptions

        assert load_working_assumptions(REPO)

    def test_no_seed_claims_a_partner_fact_the_ledger_does_not_carry(
        self, declarations: list[dict[str, Any]], partner_ids: set[str]
    ) -> None:
        """Every partner in the seeds is Assumed, so every partner the seeds
        name must be in the ledger. The reverse of the box, and cheaper to
        check than to review."""
        declared = {
            d["key"].removesuffix("_participation")
            for d in declarations
            if d["key"].endswith("_participation")
        }
        assert partner_ids <= declared


# ---------------------------------------------------------------------------
# Box 4 — anonymity
# ---------------------------------------------------------------------------


class TestAnonymity:
    def test_the_seeds_introduce_no_new_leak(self) -> None:
        report = scan_tree(REPO)
        seeds = {
            path.relative_to(REPO).as_posix()
            for path in (OBJECTIVES, OUTCOMES, IMPACTS, WP_SEED, MILESTONES, RISKS,
                         LEDGER)
        }
        offenders = [v for v in report.new_violations if v.path in seeds]
        assert not offenders, [f"{v.path}:{v.line} {v.snippet}" for v in offenders]

    def test_the_branch_is_no_less_ok_than_before(self) -> None:
        """`ok` is the regression guard; `clean` is the constraint. The branch
        holds one recorded pre-existing leak in a Tier 4 purge record, and this
        ticket does not change that."""
        report = scan_tree(REPO)
        assert report.ok, [f"{v.path}:{v.line} {v.snippet}" for v in report.new_violations]

    def test_no_seed_names_a_person(self) -> None:
        """The convention is a role at a partner, never an individual. A seed
        that names a person would be the first place it breaks."""
        for path in (OBJECTIVES, OUTCOMES, IMPACTS, WP_SEED, MILESTONES, RISKS):
            text = path.read_text(encoding="utf-8-sig")
            assert " Dr " not in text and " Prof" not in text, path.name


# ---------------------------------------------------------------------------
# Box 5 — Tier 3 is frozen
# ---------------------------------------------------------------------------


def _tier3_artifacts() -> set[str]:
    """Every Tier 3 file that carries a project fact, repo-relative."""
    return {
        path.relative_to(REPO).as_posix()
        for path in TIER3.rglob("*")
        if path.is_file()
        and path.name not in NOT_A_TIER3_ARTIFACT
        and path.suffix.lower() not in {".pdf", ".docx"}
        and not path.relative_to(REPO).as_posix().startswith(OTHER_INSTANCE_TIER3_DIRS)
    }


class TestTheFreeze:
    """The manual's freeze rule over the whole of Tier 3, not just the brief.

    The concept ticket fingerprinted the three brief artifacts. This one covers
    the rest, so between the two records every Tier 3 artifact is either
    fingerprinted or named as exempt with a reason.
    """

    @pytest.fixture(scope="class")
    def freeze(self) -> dict:
        assert DECISION.is_file(), f"{DECISION.name} is absent"
        return _live_freeze_for(OBJECTIVES)

    @pytest.fixture(scope="class")
    def concept_freeze(self) -> dict:
        return _live_freeze_for(TIER3 / "project_brief/concept_note.md")

    def test_every_live_freeze_record_is_reachable(self) -> None:
        """Two live records, no more: the seeds scope and the project brief."""
        live = _live_freeze_records()
        assert len(live) == 2, f"live freeze records: {sorted(live)}"

    def test_the_brief_is_still_governed_by_the_concept_record(self) -> None:
        """Resolving by content must not drift from the record that claims it."""
        brief = (TIER3 / "project_brief/concept_note.md").relative_to(REPO).as_posix()
        live = _live_freeze_records()
        holders = [rel for rel, rec in live.items() if brief in rec["artifacts"]]
        assert holders == [CONCEPT_DECISION.relative_to(REPO).as_posix()]

    def test_a_superseded_freeze_record_is_not_read(self) -> None:
        """The seeds entry's own freeze record is superseded, so it is not live."""
        seeds_rel = DECISION.relative_to(REPO).as_posix()
        superseding = [
            path
            for path in (REPO / "docs/tier4_orchestration_state/decision_log").glob("*.json")
            if seeds_rel in (_read(path).get("supersedes") or [])
        ]
        if not superseding:
            pytest.skip("nothing supersedes the seeds freeze record yet")
        assert seeds_rel not in _live_freeze_records()

    def test_the_digest_basis_is_declared_and_shared(
        self, freeze: dict, concept_freeze: dict
    ) -> None:
        assert DIGEST_BASIS_PHRASE in freeze["digest_basis"]
        assert DIGEST_BASIS_PHRASE in concept_freeze["digest_basis"]

    def test_every_tier3_artifact_is_fingerprinted_or_exempt(
        self, freeze: dict, concept_freeze: dict
    ) -> None:
        covered = set(freeze["artifacts"]) | set(concept_freeze["artifacts"])
        exempt = set(freeze["not_frozen"])
        loose = sorted(_tier3_artifacts() - covered - exempt)
        assert not loose, f"Tier 3 artifacts no freeze record covers: {loose}"

    def test_the_two_records_do_not_fingerprint_the_same_file(
        self, freeze: dict, concept_freeze: dict
    ) -> None:
        """Two fingerprints of one file drift apart the moment one is reissued."""
        both = set(freeze["artifacts"]) & set(concept_freeze["artifacts"])
        assert not both, f"fingerprinted twice: {sorted(both)}"

    def test_every_frozen_artifact_still_matches_its_fingerprint(
        self, freeze: dict
    ) -> None:
        mismatched = [
            f"{rel}\n  recorded {recorded}\n  actual   {digest(REPO / rel, DIGEST_BASIS)}"
            for rel, recorded in freeze["artifacts"].items()
            if digest(REPO / rel, DIGEST_BASIS) != recorded
        ]
        assert not mismatched, (
            "a frozen Tier 3 artifact was edited after the freeze:\n"
            + "\n".join(mismatched)
        )

    def test_the_six_seeds_are_all_listed(self, freeze: dict) -> None:
        listed = set(freeze["artifacts"])
        for path in (OBJECTIVES, OUTCOMES, IMPACTS, WP_SEED, MILESTONES, RISKS):
            assert path.relative_to(REPO).as_posix() in listed, path.name

    def test_the_ledger_stays_out_of_the_freeze(self, freeze: dict) -> None:
        """Step ⑦ of the manual is the one input the operator keeps touching."""
        rel = LEDGER.relative_to(REPO).as_posix()
        assert rel in freeze["not_frozen"]
        assert rel not in freeze["artifacts"]
        for path, reason in freeze["not_frozen"].items():
            assert reason.strip(), f"{path} is exempt without a reason"

    def test_unfreezing_is_named_as_an_operator_decision(self, freeze: dict) -> None:
        assert "operator decision" in freeze["unfreezing"].lower()


# ---------------------------------------------------------------------------
# The record of the work
# ---------------------------------------------------------------------------


class TestTheRecord:
    def test_the_validation_report_exists(self) -> None:
        assert VALIDATION_REPORT.is_file()

    def test_the_authoring_route_is_recorded(self) -> None:
        """The ticket offers two routes and asks for the decision either way."""
        entry = _read(DECISION)
        route = json.dumps(entry, ensure_ascii=False).lower()
        assert "vault" in route and "json" in route

    def test_the_report_counts_match_the_seeds(
        self,
        objectives: list[dict[str, Any]],
        work_packages: list[dict[str, Any]],
        milestones: list[dict[str, Any]],
        deliverables: dict[str, tuple[str, dict[str, Any]]],
        partner_ids: set[str],
    ) -> None:
        """A report that states derived counts must state the real ones.

        The first draft of this record said 34 tasks and eleven cross-work-package
        dependencies. There are 35 and twelve. A Tier 4 record that misstates the
        artifact it reports on is worse than no record, so the counts are
        recomputed here rather than trusted.
        """
        home = {
            t["task_id"]: wp["wp_id"] for wp in work_packages for t in wp["tasks"]
        }
        actual = {
            "objectives": len(objectives),
            "work_packages": len(work_packages),
            "tasks": len(home),
            "deliverables": len(deliverables),
            "milestones": len(milestones),
            "risks": len(_read(RISKS)["risks"]),
            "impact_pathways": len(_read(IMPACTS)["impacts"]),
            "kpis": len(_read(IMPACTS)["kpis"]),
            "duration_months": _read(TIER3 / "call_binding/selected_call.json")[
                "project_duration_months"
            ],
            "partners": len(partner_ids),
            "cross_work_package_task_dependencies": sum(
                1
                for wp in work_packages
                for t in wp["tasks"]
                for dep in t["dependencies"]
                if home[dep] != wp["wp_id"]
            ),
            "milestones_gathering_more_than_one_work_package": sum(
                1
                for m in milestones
                if len({deliverables[d][0] for d in m["deliverables"]}) > 1
            ),
        }
        recorded = _read(VALIDATION_REPORT)["design_summary"]
        assert {k: recorded[k] for k in actual} == actual

    def test_the_report_and_the_decision_name_each_other(self) -> None:
        report_rel = VALIDATION_REPORT.relative_to(REPO).as_posix()
        decision_rel = DECISION.relative_to(REPO).as_posix()
        assert report_rel in json.dumps(_read(DECISION), ensure_ascii=False)
        assert decision_rel in json.dumps(_read(VALIDATION_REPORT), ensure_ascii=False)

    def test_every_repo_path_the_decision_names_exists(self) -> None:
        entry = _read(DECISION)
        named = {
            value
            for value in _iter_strings(entry)
            if value.startswith("docs/") and " " not in value
        }
        missing = sorted(rel for rel in named if not (REPO / rel).exists())
        assert not missing, f"the record names paths that do not exist: {missing}"


def _iter_strings(node: object):
    if isinstance(node, dict):
        for value in node.values():
            yield from _iter_strings(value)
    elif isinstance(node, list):
        for value in node:
            yield from _iter_strings(value)
    elif isinstance(node, str):
        yield node
