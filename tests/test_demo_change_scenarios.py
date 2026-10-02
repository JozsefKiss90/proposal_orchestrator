"""The demo's change scenarios, read back off the records they wrote.

``tools/run_demo_change_scenarios.py`` scripts the six changes the ticket
'Change scenarios and shadow comparison' names, plus the probe criterion 4
asks for. Each runs in a sandbox copy of the frozen Tier 3, so the demo's
founding documents are never edited in place and the demo snapshot id never
moves.

Three groups of test:

* the catalogue is well formed and covers what the ticket asks;
* the records on disk are current and say what the catalogue intends;
* the advisory is not consumed at runtime — the reuse decision the scheduler
  would reach is identical with and without an advisory on disk, which is the
  second half of the ticket's third criterion.

No test here dispatches a phase. The reruns the ticket pairs with each
advisory are operator work, and what blocks them is recorded in the decision
log rather than simulated.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from runner.atomic_write import canonical_json_bytes
from runner.dev_graph.builder import build_snapshot
from runner.dev_graph.impact import RUN_RECORDS_REL
from runner.dev_graph.scenarios import (
    SCENARIO_INDEX_SCHEMA_ID,
    SCENARIOS_REL,
    advisory_rel,
    run_scenario,
    scenario_rel,
    write_scenario_records,
)
from runner.phase8_reuse import (
    REUSE_ELIGIBLE_NODES,
    compute_input_fingerprint,
    validate_reuse_candidate,
)
from runner.run_context import PRESERVED_RUN_RECORDS_REL, is_plain_run_id, run_id_slug
from tools.run_demo_change_scenarios import (
    COMPARED_RUN_IDS,
    SCENARIOS,
    run_all,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
INDEX = REPO_ROOT / SCENARIOS_REL / "index.json"


def _index() -> dict:
    if not INDEX.is_file():
        pytest.skip("the demo scenarios have not been run yet")
    return json.loads(INDEX.read_text(encoding="utf-8-sig"))


class TestCatalogue:
    """What the ticket asks for, checked against the catalogue."""

    def test_every_scenario_the_ticket_names_is_present(self) -> None:
        assert [s.scenario_id for s in SCENARIOS] == [
            "task_lead_moves",
            "gap_partner_withdraws",
            "gap_partner_confirmed",
            "claim_loses_its_span",
            "tier2b_fact_changes",
            "deliverable_month_moves",
            "protected_objective_probe",
        ]

    def test_every_scenario_has_at_least_one_arm_and_a_purpose(self) -> None:
        assert all(s.arms and s.purpose for s in SCENARIOS)

    def test_every_arm_names_a_purpose_and_an_expectation(self) -> None:
        arms = [a for s in SCENARIOS for a in s.arms]
        assert all(a.purpose and a.expects for a in arms)

    def test_no_two_scenarios_share_an_id(self) -> None:
        ids = [s.scenario_id for s in SCENARIOS]
        assert len(set(ids)) == len(ids)

    def test_no_two_arms_of_one_scenario_share_an_id(self) -> None:
        for scenario in SCENARIOS:
            ids = [a.arm_id for a in scenario.arms]
            assert len(set(ids)) == len(ids)


class TestRecordsOnDisk:
    """The written records, compared with a fresh run of the same catalogue."""

    def test_the_index_is_current(self, tmp_path: Path) -> None:
        index = _index()
        fresh = write_scenario_records(
            tmp_path / "world", run_all(REPO_ROOT, tmp_path / "sandboxes")
        )
        written = next(p for p in fresh if p.name == "index.json")

        assert canonical_json_bytes(index) == written.read_bytes()

    def test_the_index_carries_its_schema_and_its_shadow_standing(self) -> None:
        index = _index()

        assert index["schema_id"] == SCENARIO_INDEX_SCHEMA_ID
        assert index["advisory"] is True
        assert index["consumed_at_runtime"] is False

    def test_every_scenario_has_a_record_and_every_recorded_arm_an_advisory(self) -> None:
        for scenario in _index()["scenarios"]:
            assert (REPO_ROOT / scenario["path"]).is_file()
            for arm in scenario["arms"]:
                if arm["advisory"] is None:
                    continue
                assert (REPO_ROOT / arm["advisory"]).is_file()

    def test_every_advisory_gives_every_entry_a_reason_path(self) -> None:
        # The ticket's first criterion. An entry with no reason path would be
        # an assertion that something is affected, with nothing behind it.
        seen = 0
        for scenario in _index()["scenarios"]:
            record = json.loads((REPO_ROOT / scenario["path"]).read_text(encoding="utf-8-sig"))
            for arm in record["arms"]:
                if arm["advisory"] is None:
                    continue
                seen += 1
                assert arm["advisory"]["every_entry_has_a_reason_path"] is True
        assert seen

    def test_every_arm_met_the_expectation_it_declared(self) -> None:
        index = _index()
        unmet = [
            (s["scenario_id"], a["arm_id"])
            for s in index["scenarios"]
            for a in s["arms"]
            if not a["expectation_met"]
        ]

        assert unmet == []
        assert index["arms_matched_expectations"] is True

    def test_the_protected_objective_probe_is_rejected_and_names_the_node(self) -> None:
        record = json.loads(
            (REPO_ROOT / scenario_rel("protected_objective_probe")).read_text(
                encoding="utf-8-sig"
            )
        )
        check = record["arms"][0]["contract_check"]

        assert check["verdict"] == "rejected"
        assert [h["node_id"] for h in check["protected_hits"]] == ["O1"]

    def test_the_withdrawal_cannot_be_recorded_as_one_change(self) -> None:
        record = json.loads(
            (REPO_ROOT / scenario_rel("gap_partner_withdraws")).read_text(encoding="utf-8-sig")
        )
        direct = record["arms"][0]

        assert direct["outcome"] == "refused"
        assert direct["refusal"]["kind"] == "dangling_edge"

    def test_a_dropped_span_is_a_contained_change_the_planner_does_not_see(self) -> None:
        # The finding criterion 2 asks after: the planner is narrower than the
        # change, and it is structural rather than per-run.
        record = json.loads(
            (REPO_ROOT / scenario_rel("claim_loses_its_span")).read_text(encoding="utf-8-sig")
        )
        arm = record["arms"][0]

        assert [c["kind"] for c in arm["change"]["nodes_changed"]] == ["contained"]
        assert arm["advisory"]["nothing_changed"] is True
        assert arm["advisory"]["origins"] == []

    def test_a_tier2b_change_cannot_be_named_to_the_change_recorder(self) -> None:
        record = json.loads(
            (REPO_ROOT / scenario_rel("tier2b_fact_changes")).read_text(encoding="utf-8-sig")
        )
        probe = record["arms"][0]

        assert probe["outcome"] == "refused"
        assert probe["refusal"]["kind"] == "malformed_request"
        assert "selected_call.json" in probe["refusal"]["offender"]

    def test_every_shadow_comparison_in_this_world_is_a_recorded_refusal(self) -> None:
        # No run manifest in the demo world records a reuse decision, so the
        # comparison refuses rather than reporting agreement over nothing.
        # This is the ticket's open half, recorded as what it is. Since
        # subticket A the refusal is the run's, not the request's: both runs
        # are reached and found to hold no decision (subticket D is why).
        diagnostics = {
            d
            for s in _index()["scenarios"]
            for a in s["arms"]
            for d in a["shadow_diagnostics"]
        }

        assert diagnostics == {"refused:no_reuse_decision"}

    def test_the_phase_8_run_is_named_to_every_comparison_through_its_preserved_record(self) -> None:
        # Subticket A, third box. The run that carried Phase 8 is stored under
        # a mis-pasted shell command as its id. Every advisory is now compared
        # against it by its true id, read through the record the preserve tool
        # keeps under the id's slug, and what comes back is not a refusal of
        # the request.
        mispasted = COMPARED_RUN_IDS[1]
        assert not is_plain_run_id(mispasted)
        preserved = f"{PRESERVED_RUN_RECORDS_REL}/{run_id_slug(mispasted)}.json"
        assert (REPO_ROOT / preserved).is_file()

        seen = 0
        for scenario in _index()["scenarios"]:
            record = json.loads((REPO_ROOT / scenario["path"]).read_text(encoding="utf-8-sig"))
            for arm in record["arms"]:
                for comparison in arm["shadow_comparisons"]:
                    if comparison["run_id"] != mispasted:
                        continue
                    seen += 1
                    assert "diagnostic" in comparison or comparison["refused"]["kind"] != "malformed_request"
                    if "refused" in comparison:
                        assert comparison["refused"]["offender"] == preserved
        assert seen == 8, "one comparison against the Phase 8 run per recorded arm"

    def test_no_planner_narrower_result_is_left_uninvestigated(self) -> None:
        # Criterion 2. A planner_narrower row needs a scheduler decision whose
        # status is not_reused, and no manifest in this world holds one, so no
        # comparison produced a row at all. The absence is asserted, not assumed.
        for scenario in _index()["scenarios"]:
            record = json.loads(
                (REPO_ROOT / scenario["path"]).read_text(encoding="utf-8-sig")
            )
            for arm in record["arms"]:
                for comparison in arm["shadow_comparisons"]:
                    assert comparison.get("rows", []) == []


class TestTheArtifactsMatchTheirDeclaredSchemas:
    """§16.3: an artifact's fields are the ones the specification declares.

    The specification is the authority on artifact schemas (§16.2), so a
    field a writer adds without declaring it there is a divergence, not an
    extension. These tests compare the written artifacts with the spec
    rather than with the writer that produced them.
    """

    @staticmethod
    def _declared(key: str) -> dict:
        spec = yaml.safe_load(
            (
                REPO_ROOT
                / ".claude/workflows/system_orchestration/artifact_schema_specification.yaml"
            ).read_text(encoding="utf-8")
        )
        return spec["operational_artifact_schemas"][key]

    def _compare(self, key: str, rel: str) -> None:
        declared = self._declared(key)
        path = REPO_ROOT / rel
        if not path.is_file():
            pytest.skip(f"{rel} not written yet")
        doc = json.loads(path.read_text(encoding="utf-8-sig"))

        assert doc["schema_id"] == declared["schema_id_value"]
        assert set(doc) == set(declared["fields"])

    def test_the_scenario_record(self) -> None:
        self._compare("dev_graph_change_scenario", scenario_rel("task_lead_moves"))

    def test_the_scenario_index(self) -> None:
        self._compare(
            "dev_graph_change_scenario_index", f"{SCENARIOS_REL}/index.json"
        )

    def test_the_run_records(self) -> None:
        self._compare("dev_graph_run_records", RUN_RECORDS_REL)

    def test_every_arm_of_every_scenario(self) -> None:
        declared = set(
            self._declared("dev_graph_change_scenario")["fields"]["arms"]["item_schema"]
        )
        seen = 0
        for scenario in _index()["scenarios"]:
            record = json.loads(
                (REPO_ROOT / scenario["path"]).read_text(encoding="utf-8-sig")
            )
            for arm in record["arms"]:
                seen += 1
                assert set(arm) == declared, (scenario["scenario_id"], arm["arm_id"])
        assert seen

    def test_the_run_records_artifact_is_no_longer_declared_hand_placed(self) -> None:
        # It was manually_placed until a tool started deriving it. A spec that
        # still said so would send a reader to the wrong author.
        assert self._declared("dev_graph_run_records")["provenance_class"] == "derived"


class TestTheFrozenWorldIsUntouched:
    """The freeze rule: the scenarios copy, they never edit in place."""

    def test_the_demo_snapshot_id_has_not_moved(self) -> None:
        stored = json.loads(
            (REPO_ROOT / "docs/tier4_orchestration_state/dev_graph/snapshot.json").read_text(
                encoding="utf-8-sig"
            )
        )

        assert build_snapshot(REPO_ROOT).snapshot_id == stored["snapshot_id"]

    def test_every_scenario_started_from_the_demo_snapshot(self) -> None:
        live = build_snapshot(REPO_ROOT).snapshot_id

        for scenario in _index()["scenarios"]:
            assert scenario["before_snapshot_id"] == live

    @staticmethod
    def _frozen_world() -> dict[str, bytes]:
        """Every Tier 3 file, plus every file the snapshot declares as an input.

        The second set reaches outside Tier 3: the imported candidate document
        is a Tier 4 input of the snapshot, and a scenario copies it too.
        """
        files = {
            p.relative_to(REPO_ROOT).as_posix(): p.read_bytes()
            for p in sorted((REPO_ROOT / "docs/tier3_project_instantiation").rglob("*"))
            if p.is_file()
        }
        for rel in build_snapshot(REPO_ROOT).inputs:
            files[rel] = (REPO_ROOT / rel).read_bytes()
        return files

    def test_the_snapshot_declares_an_input_outside_tier_3(self) -> None:
        inputs = build_snapshot(REPO_ROOT).inputs

        assert any(not rel.startswith("docs/tier3_project_instantiation/") for rel in inputs)

    def test_a_run_writes_nothing_outside_the_sandbox(self, tmp_path: Path) -> None:
        before = self._frozen_world()

        run_all(REPO_ROOT, tmp_path / "sandboxes")

        assert self._frozen_world() == before


class TestTheAdvisoryIsNotConsumed:
    """Criterion 3: the scheduler's reuse decision does not see the advisory.

    The two dynamic tests rewrite the committed scenario records in place.
    That is deliberate and safe: the writer carries no clock, so the same
    catalogue over the same world writes the same bytes. Each test proves
    that by comparing the record tree before and after.
    """

    @staticmethod
    def _records_tree() -> dict[str, bytes]:
        base = REPO_ROOT / SCENARIOS_REL
        if not base.is_dir():
            pytest.skip("the demo scenarios have not been run yet")
        return {
            p.relative_to(base).as_posix(): p.read_bytes()
            for p in sorted(base.rglob("*"))
            if p.is_file()
        }

    def test_rewriting_the_records_changes_no_byte(self, tmp_path: Path) -> None:
        before = self._records_tree()

        write_scenario_records(REPO_ROOT, run_all(REPO_ROOT, tmp_path / "sandboxes"))

        assert self._records_tree() == before

    @pytest.mark.parametrize("node_id", sorted(REUSE_ELIGIBLE_NODES))
    def test_the_input_fingerprint_is_the_same_with_an_advisory_present(
        self, node_id: str, tmp_path: Path
    ) -> None:
        # The advisory and the scenario records live under Tier 4 dev_graph,
        # which no node's fingerprint inputs cover. If one ever did, adding an
        # advisory would invalidate a cached section and the planner would be
        # steering the scheduler.
        before = compute_input_fingerprint(node_id, REPO_ROOT)

        write_scenario_records(REPO_ROOT, run_all(REPO_ROOT, tmp_path / "sandboxes"))

        assert compute_input_fingerprint(node_id, REPO_ROOT) == before

    @pytest.mark.parametrize("node_id", sorted(REUSE_ELIGIBLE_NODES))
    def test_the_reuse_decision_is_the_same_with_an_advisory_present(
        self, node_id: str, tmp_path: Path
    ) -> None:
        def decision() -> tuple:
            d = validate_reuse_candidate(
                node_id, REPO_ROOT, compute_input_fingerprint(node_id, REPO_ROOT)
            )
            return (d.reusable, d.reason, d.artifact_path, d.input_fingerprint, d.gate_id)

        before = decision()

        write_scenario_records(REPO_ROOT, run_all(REPO_ROOT, tmp_path / "sandboxes"))

        assert decision() == before

    def test_no_fingerprint_input_covers_the_advisory_directory(self) -> None:
        from runner.phase8_reuse import FINGERPRINT_INPUTS

        for node_id, paths in FINGERPRINT_INPUTS.items():
            for path in paths:
                assert not SCENARIOS_REL.startswith(path.rstrip("/")), (node_id, path)
                assert not RUN_RECORDS_REL.startswith(path.rstrip("/")), (node_id, path)

    def test_a_scenario_run_writes_no_reuse_metadata(self, tmp_path: Path) -> None:
        reuse_dir = REPO_ROOT / "docs/tier4_orchestration_state/reuse"
        before = sorted(p.as_posix() for p in reuse_dir.rglob("*")) if reuse_dir.is_dir() else []

        run_all(REPO_ROOT, tmp_path / "sandboxes")

        after = sorted(p.as_posix() for p in reuse_dir.rglob("*")) if reuse_dir.is_dir() else []
        assert after == before


class TestComparedRuns:
    """The comparison names runs this world holds, not invented ones."""

    def test_every_compared_run_has_a_manifest(self) -> None:
        runs = REPO_ROOT / ".claude" / "runs"
        if not runs.is_dir():
            pytest.skip("runtime run state is gitignored under §9.2")

        assert COMPARED_RUN_IDS
        for run_id in COMPARED_RUN_IDS:
            assert (runs / run_id / "run_manifest.json").is_file(), run_id

    def test_no_compared_run_manifest_records_a_reuse_decision(self) -> None:
        # The premise of every recorded refusal, checked rather than assumed.
        # The Phase 8 run's manifest holds no reuse_decisions key at all: its
        # drafting nodes ran fresh, and a not_reused decision is never
        # persisted to the manifest (subticket D).
        runs = REPO_ROOT / ".claude" / "runs"
        if not runs.is_dir():
            pytest.skip("runtime run state is gitignored under §9.2")

        for run_id in COMPARED_RUN_IDS:
            manifest = json.loads(
                (runs / run_id / "run_manifest.json").read_text(encoding="utf-8-sig")
            )
            assert not manifest.get("reuse_decisions"), run_id
