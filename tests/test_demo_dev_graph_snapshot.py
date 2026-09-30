"""The first dev-graph snapshot on the instance-two demo world.

The ticket "First dev-graph snapshot on the demo world" in
`plans/dev_graph_demo_tickets.md` runs the builder on the populated repository
root, before any runner phase, and then builds one evidence package per view
policy for three named tasks. Its five acceptance criteria are mechanical, so
each is checked here against the committed artifacts rather than asserted:

* **the snapshot builds, and two builds give the same snapshot id.**
  `TestTheSnapshot` builds twice in process and compares both the id and the
  bytes, and holds the committed `snapshot.json` to the same build.
* **every fail-closed error is listed with its cause and its record fix.**
  The build raised none. `TestTheBuildWasClean` pins what the builder actually
  read, so a later ticket that widens the node-type set fails here first.
* **each package manifest reports completeness, and an incomplete one names
  the item that did not fit.** `TestThePackages`.
* **Assumed partners and Unresolved claims appear in the unresolved lists.**
  `TestHonesty`, which is the criterion the first build failed: the manifest
  read document claims alone, so a package of Assumed Tier 3 records rolled up
  to Confirmed.
* **node and edge counts are recorded.** `TestTheCounts`.

`TestWhatThePolicyKeptOut` pins every exclusion count the ticket's report
cites. It exists because a first draft of that report claimed no manifest
records a policy exclusion, generalising from one seed that records none; it is
false for three of the eighteen. `TestAnonymity` holds the new Tier 4 artifacts
to the branch's recorded ok-versus-clean split.
"""
from __future__ import annotations

import json
from typing import Any

import pytest

from runner.dev_graph import (
    COMPLETENESS,
    DEFAULT_PACKAGE_BUDGET,
    EXCLUSION_REASONS,
    POLICY_VERSION,
    SNAPSHOT_REL,
    VIEW_POLICIES,
    Snapshot,
    build_snapshot,
    declared_status,
    package_dir,
)
from runner.leakage_scan import scan_tree
from runner.paths import find_repo_root
from tools.build_demo_dev_graph import PROJECT, SEED_TASKS, SUMMARY_REL, main

REPO = find_repo_root()

#: The Tier 3 records the builder reads on this world. Milestone 1's node-type
#: set has no outcome, impact or risk type, so `outcomes.json`, `impacts.json`
#: and `risks.json` are not indexed; see finding F3 of the ticket's report.
EXPECTED_INPUTS = (
    "docs/tier3_project_instantiation/architecture_inputs/milestones_seed.json",
    "docs/tier3_project_instantiation/architecture_inputs/objectives.json",
    "docs/tier3_project_instantiation/architecture_inputs/workpackage_seed.json",
    "docs/tier3_project_instantiation/consortium/partners.json",
    "docs/tier3_project_instantiation/source_materials/sources.json",
)

WP_SEED = "docs/tier3_project_instantiation/architecture_inputs/workpackage_seed.json"


def _load(rel: str) -> Any:
    return json.loads((REPO / rel).read_text(encoding="utf-8-sig"))


@pytest.fixture(scope="module")
def snapshot() -> Snapshot:
    return build_snapshot(REPO)


@pytest.fixture(scope="module")
def summary() -> dict[str, Any]:
    return _load(SUMMARY_REL)


@pytest.fixture(scope="module")
def manifests(summary: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for row in summary["packages"]:
        path = package_dir(REPO, row["package_id"]) / "manifest.json"
        out.append(json.loads(path.read_text(encoding="utf-8-sig")))
    return out


class TestTheSnapshot:
    def test_it_builds_and_is_not_empty(self, snapshot: Snapshot):
        assert not snapshot.empty
        assert snapshot.nodes and snapshot.edges

    def test_two_builds_give_the_same_id_and_the_same_bytes(self, snapshot: Snapshot):
        again = build_snapshot(REPO)
        assert again.snapshot_id == snapshot.snapshot_id
        assert again.to_json_bytes() == snapshot.to_json_bytes()

    def test_the_committed_snapshot_is_this_build(self, snapshot: Snapshot):
        stored = Snapshot.from_dict(_load(SNAPSHOT_REL), SNAPSHOT_REL)
        assert stored.snapshot_id == snapshot.snapshot_id

    def test_the_whole_run_replays_byte_equal(self):
        assert main(["--check"]) == 0


class TestTheBuildWasClean:
    def test_the_builder_read_exactly_these_records(self, snapshot: Snapshot):
        assert snapshot.inputs == EXPECTED_INPUTS

    def test_the_three_unindexed_seeds_exist_but_are_not_read(self, snapshot: Snapshot):
        seeds = REPO / "docs/tier3_project_instantiation/architecture_inputs"
        for name in ("outcomes.json", "impacts.json", "risks.json"):
            path = seeds / name
            assert path.is_file()
            assert path.relative_to(REPO).as_posix() not in snapshot.inputs

    def test_every_work_package_carries_both_keys_the_two_readers_use(self):
        """The seam the seeds ticket recorded: the builder reads ``wp_id`` and
        the dependency normaliser reads ``id``. A work package missing one is
        silently skipped by one of the two."""
        for wp in _load(WP_SEED)["work_packages"]:
            assert wp["wp_id"] == wp["id"]


class TestThePackages:
    def test_one_package_per_view_for_each_seed_task(self, summary: dict[str, Any]):
        assert tuple(summary["seed_tasks"]) == SEED_TASKS
        pairs = {(r["task"], r["view"]) for r in summary["packages"]}
        assert pairs == {(t, v) for t in SEED_TASKS for v in VIEW_POLICIES}

    def test_each_seed_task_is_a_task_node(self, snapshot: Snapshot):
        tasks = {n["id"] for n in snapshot.nodes if n["type"] == "task"}
        assert set(SEED_TASKS) <= tasks

    def test_every_manifest_reports_completeness(self, manifests: list[dict[str, Any]]):
        assert manifests
        assert all(m["completeness"] in COMPLETENESS for m in manifests)

    def test_every_incomplete_package_names_the_item_that_did_not_fit(
        self, summary: dict[str, Any], manifests: list[dict[str, Any]]
    ):
        for row, manifest in zip(summary["packages"], manifests):
            if manifest["completeness"] != "incomplete":
                continue
            dropped = [e for e in manifest["exclusions"] if e["reason"] == "over_budget"]
            assert dropped, "an incomplete package with nothing over budget"
            assert row["first_item_that_did_not_fit"] == dropped[0]["id"]
            assert row["over_budget_ids"] == [e["id"] for e in dropped]

    def test_the_summary_and_the_manifests_agree(
        self, summary: dict[str, Any], manifests: list[dict[str, Any]]
    ):
        for row, manifest in zip(summary["packages"], manifests):
            assert manifest["task"] == row["task"]
            assert manifest["view"] == row["view"]
            assert manifest["package_id"] == row["package_id"]
            assert manifest["budget"] == DEFAULT_PACKAGE_BUDGET
            assert manifest["policy_version"] == POLICY_VERSION
            assert manifest["snapshot_id"] == summary["snapshot_id"]
            assert manifest["project"] == PROJECT
            assert len(manifest["included"]) == row["included_count"]

    def test_the_measured_minimum_budget_exceeds_the_default(self, summary: dict[str, Any]):
        """Every package on this world is incomplete under the default budget.

        The measurement, not the verdict, is the finding: the mandatory set of
        a real work plan costs several times what the fixture's did.
        """
        for row in summary["packages"]:
            assert row["completeness"] == "incomplete"
            assert row["minimum_budget_for_mandatory"] > DEFAULT_PACKAGE_BUDGET
            assert row["minimum_budget_for_completeness"] >= row["minimum_budget_for_mandatory"]


class TestWhatThePolicyKeptOut:
    """The claim a first draft of the report got wrong.

    The report said no manifest records a policy exclusion under the default
    budget. That was generalised from T3.1, which records none, and it is false
    for three of the eighteen. Every count the report now cites is derived into
    the summary and read back here, so prose cannot drift from the artifacts
    again.
    """

    def test_the_totals_are_the_manifests(
        self, summary: dict[str, Any], manifests: list[dict[str, Any]]
    ):
        totals: dict[str, int] = {}
        for m in manifests:
            for e in m["exclusions"]:
                totals[e["reason"]] = totals.get(e["reason"], 0) + 1
        assert summary["exclusions_by_reason_total"] == dict(sorted(totals.items()))

    def test_every_reason_is_in_the_closed_set(self, summary: dict[str, Any]):
        assert set(summary["exclusions_by_reason_total"]) <= EXCLUSION_REASONS

    def test_policy_exclusions_are_rare_but_not_absent(self, summary: dict[str, Any]):
        """The budget usually exhausts before expansion reaches a refused node.

        Usually, not always. The report must say which, so both halves are
        pinned: some package records a policy exclusion, and most do not.
        """
        with_policy = summary["packages_with_a_policy_exclusion"]
        assert with_policy
        assert len(with_policy) < len(summary["packages"])
        assert summary["exclusions_by_reason_total"]["policy_forbidden"] < summary[
            "exclusions_by_reason_total"
        ]["over_budget"]

    def test_the_named_packages_are_the_ones_that_record_them(
        self, summary: dict[str, Any], manifests: list[dict[str, Any]]
    ):
        named = {tuple(pair) for pair in summary["packages_with_a_policy_exclusion"]}
        actual = {
            (m["task"], m["view"])
            for m in manifests
            if any(e["reason"] == "policy_forbidden" for e in m["exclusions"])
        }
        assert named == actual

    def test_each_row_lists_what_its_view_refused(
        self, summary: dict[str, Any], manifests: list[dict[str, Any]]
    ):
        for row, manifest in zip(summary["packages"], manifests):
            refused = [e for e in manifest["exclusions"] if e["reason"] == "policy_forbidden"]
            assert row["policy_forbidden_count"] == len(refused)
            assert [e["id"] for e in row["policy_forbidden"]] == [e["id"] for e in refused]
            assert [e["detail"] for e in row["policy_forbidden"]] == [e["detail"] for e in refused]


class TestHonesty:
    def test_no_manifest_over_states_its_own_records(self, manifests: list[dict[str, Any]]):
        for m in manifests:
            statuses = {i["declared_status"] for i in m["included"] if "declared_status" in i}
            assert statuses, "a manifest carrying no declared status at all"
            if statuses - {"Confirmed"}:
                assert m["worst_declared_status"] != "Confirmed"

    def test_every_assumed_partner_in_a_package_is_listed(
        self, snapshot: Snapshot, manifests: list[dict[str, Any]]
    ):
        assumed = {
            n["id"]
            for n in snapshot.nodes
            if n["type"] == "participant" and declared_status(n) == "Assumed"
        }
        assert assumed, "the demo consortium is wholly Assumed; this test checks nothing"
        for m in manifests:
            included = {i["id"] for i in m["included"] if i["type"] == "participant"}
            listed = {u["id"] for u in m["unresolved"] if u["kind"] == "declared_status"}
            assert (included & assumed) <= listed

    def test_the_world_holds_no_claim_to_list(self, snapshot: Snapshot):
        """Tier 5 is empty, so the criterion's claim half has nothing to check.

        It is checked against the fixture in
        `tests/runner/test_dev_graph_packages.py`. Recorded here so the gap is
        visible rather than silently passing.
        """
        assert not any(n["type"] == "claim" for n in snapshot.nodes)

    def test_only_a_source_is_confirmed_on_this_world(self, snapshot: Snapshot):
        confirmed = {n["id"] for n in snapshot.nodes if declared_status(n) == "Confirmed"}
        types = {n["id"]: n["type"] for n in snapshot.nodes}
        assert confirmed
        assert all(types[i] == "source" for i in confirmed)


class TestTheCounts:
    def test_the_summary_records_the_counts(self, snapshot: Snapshot, summary: dict[str, Any]):
        assert summary["node_count"] == len(snapshot.nodes)
        assert summary["edge_count"] == len(snapshot.edges)

    def test_the_breakdown_sums_to_the_totals(self, summary: dict[str, Any]):
        assert sum(summary["nodes_by_type"].values()) == summary["node_count"]
        assert sum(summary["edges_by_predicate"].values()) == summary["edge_count"]

    def test_the_breakdown_matches_the_snapshot(self, snapshot: Snapshot, summary: dict[str, Any]):
        by_type: dict[str, int] = {}
        for n in snapshot.nodes:
            by_type[n["type"]] = by_type.get(n["type"], 0) + 1
        assert summary["nodes_by_type"] == dict(sorted(by_type.items()))


class TestAnonymity:
    def test_the_new_artifacts_are_scanned_and_carry_no_new_leak(self):
        report = scan_tree(REPO)
        scanned = set(report.scanned_files)
        assert any(f.startswith("docs/tier4_orchestration_state/dev_graph/") for f in scanned)
        assert report.ok
        assert all(v.pre_existing for v in report.violations)
