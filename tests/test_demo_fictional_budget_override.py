"""
The demo's fictional budget response, and the operator override that permits it.

Ticket A in ``plans/tickets_budget_and_blind_lane.md``.  BIODIV-01 is a lump-sum RIA,
so CLAUDE.md §8.1 and §17.6.7 reserve the budget to the external Lump Sum Budget
Planner and §8.3 forbids substituting an internally generated figure for an absent
response.  No planner exists for this repository and instance two is a demonstration
that is never submitted, so the operator instructed in session that those rules are
overridden for this task.  §1 permits that: an explicit in-session instruction scoped
to the instruction that invokes it, which is not an amendment.

The override reaches six clauses, not the three the ticket first named.  A response
authored inside the repository also breaches §5's integration constraint, §8.4's
lump-sum *source* clause and §13.3's budget-figure item.  :data:`SUSPENDED_CLAUSES`
is the list, and ``TestTheOverrideIsRecorded`` reads it back out of the record so an
unnamed breach fails here rather than passing quietly.  §8.4's *categorical Phase 8
block* is a different sentence of the same section and is **not** suspended, which is
why that section appears in both of the record's lists.

What these tests pin is therefore narrow and deliberate:

* the response in ``received/`` is the only hand-authored artifact, it conforms to the
  interface contract, and it declares its own figures fictional in its own content;
* the four ``gate_09`` predicates that read ``received/`` pass on it, each proved
  separately, so a later reader can see which part of the gate this file satisfies;
* the override is recorded in Tier 4 with the rules it suspends and its expiry, because
  a suspended constitutional rule held only in a session transcript is not a record
  (§9.4);
* the rest of Phase 7 is still absent.  ``validation/`` and
  ``budget_gate_assessment.json`` are the Phase 7 node's to write, and dispatching that
  node is the operator's step.  Gate evaluation belongs to the scheduler and gate
  results to the gate evaluator (§17.1.4, §17.6.3), so nothing here writes one.

The predicate functions run here are pure.  Running them is reading the gate's
arithmetic, not declaring its verdict.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from runner.predicates.coverage_predicates import (
    partner_budget_coverage_match,
    wp_budget_coverage_match,
)
from runner.predicates.file_predicates import dir_non_empty
from runner.predicates.schema_predicates import interface_contract_conforms

REPO = Path(__file__).resolve().parents[1]

RECEIVED_REL = "docs/integrations/lump_sum_budget_planner/received/"
VALIDATION_REL = "docs/integrations/lump_sum_budget_planner/validation/"
CONTRACT_REL = "docs/integrations/lump_sum_budget_planner/interface_contract.json"
RESPONSE_REL = (
    "docs/integrations/lump_sum_budget_planner/received/"
    "budget_response_FICTIONAL_demo_2026-10-01.json"
)
WP_STRUCTURE_REL = (
    "docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json"
)
PARTNERS_REL = "docs/tier3_project_instantiation/consortium/partners.json"
CALL_REL = "docs/tier3_project_instantiation/call_binding/selected_call.json"
PHASE_7_REL = "docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate"
TIER_5_REL = "docs/tier5_deliverables"
ASSESSMENT_REL = (
    "docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/"
    "budget_gate_assessment.json"
)
OVERRIDE_REL = (
    "docs/tier4_orchestration_state/decision_log/"
    "demo-fictional-budget-override_2026-10-01.json"
)

#: Every clause the operator suspended.  A test reads these from the record, so
#: dropping one fails rather than passing quietly.  Six, not the three the ticket
#: first named: a hand-authored response also breaches §5's integration constraint,
#: §8.4's lump-sum source clause and §13.3's budget-figure item.  §8.4 and §13.3 are
#: suspended in part only, so each is matched on its clause rather than its whole
#: section number.
SUSPENDED_CLAUSES = ("§5", "§8.1", "§8.3", "§8.4", "§13.3", "§17.6.7")


def _json(rel: str) -> dict:
    return json.loads((REPO / rel).read_text(encoding="utf-8-sig"))


@pytest.fixture(scope="module")
def response() -> dict:
    return _json(RESPONSE_REL)


@pytest.fixture(scope="module")
def override() -> dict:
    return _json(OVERRIDE_REL)


# ---------------------------------------------------------------------------
# 1. The response is one file, and it says what it is
# ---------------------------------------------------------------------------


class TestTheResponseDeclaresItsOwnFiction:
    def test_it_is_the_only_response_in_received(self):
        files = sorted(
            p.name
            for p in (REPO / RECEIVED_REL).iterdir()
            if p.is_file() and p.name != ".gitkeep"
        )
        assert files == ["budget_response_FICTIONAL_demo_2026-10-01.json"]

    def test_its_filename_carries_the_word_fictional(self):
        assert "FICTIONAL" in Path(RESPONSE_REL).name

    def test_it_declares_the_figures_fictional_in_its_own_content(self, response):
        assert response["figures_are_fictional"] is True
        assert "fictional" in response["provenance_note"].lower()
        bases = {
            entry["figure_basis"]
            for group in ("work_packages", "partners")
            for entry in response[group]
        }
        assert bases == {"invented_for_this_demonstration"}

    def test_it_names_the_override_record_that_permits_it(self, response):
        assert response["authorised_by"] == OVERRIDE_REL
        assert (REPO / response["authorised_by"]).is_file()

    def test_it_declares_that_no_planner_produced_it(self, response):
        assert response["produced_by_external_planner"] is False

    def test_it_answers_the_request_the_repository_composed(self, response):
        request = _json("docs/tier3_project_instantiation/integration/budget_request.json")
        assert response["request_id"] == request["request_id"]
        assert response["call_id"] == request["call_id"]

    def test_it_names_the_contract_version_it_was_written_against(self, response):
        assert response["schema_version"] == _json(CONTRACT_REL)["contract_version"]


# ---------------------------------------------------------------------------
# 2. The four gate_09 predicates that read received/
# ---------------------------------------------------------------------------


class TestTheFourResponsePredicatesPass:
    """One test per predicate, so a failure names the part of the gate that broke."""

    def test_g08_p02_the_received_directory_is_non_empty(self):
        assert dir_non_empty(RECEIVED_REL, repo_root=REPO).passed

    def test_g08_p04_the_response_conforms_to_the_interface_contract(self):
        result = interface_contract_conforms(
            RECEIVED_REL, CONTRACT_REL, repo_root=REPO
        )
        assert result.passed, result.reason
        assert result.details["contract_mode"] == "planner_contract_document"
        assert result.details["json_files_validated"] == 1

    def test_g08_p05_every_phase_3_work_package_is_covered(self):
        result = wp_budget_coverage_match(
            WP_STRUCTURE_REL, RECEIVED_REL, repo_root=REPO
        )
        assert result.passed, result.reason
        assert result.details["wps_checked"] == 7

    def test_g08_p06_every_tier_3_partner_is_covered(self):
        result = partner_budget_coverage_match(
            PARTNERS_REL, RECEIVED_REL, repo_root=REPO
        )
        assert result.passed, result.reason
        assert result.details["partners_checked"] == 12


class TestTheCoverageIsTheArtifactsOwn:
    """The predicates deep-scan for ids.  These read the response's own entries."""

    def test_each_work_package_entry_carries_a_lump_sum(self, response):
        wp_ids = {w["wp_id"] for w in _json(WP_STRUCTURE_REL)["work_packages"]}
        priced = {w["wp_id"]: w["lump_sum"] for w in response["work_packages"]}
        assert set(priced) == wp_ids
        assert all(isinstance(v, int) and v > 0 for v in priced.values())

    def test_each_partner_entry_carries_an_effort_total(self, response):
        partner_ids = {p["partner_id"] for p in _json(PARTNERS_REL)["partners"]}
        effort = {p["partner_id"]: p["total_effort_pm"] for p in response["partners"]}
        assert set(effort) == partner_ids
        assert all(isinstance(v, int) and v > 0 for v in effort.values())

    def test_the_work_package_figures_sum_to_the_calls_expected_contribution(
        self, response
    ):
        total = sum(w["lump_sum"] for w in response["work_packages"])
        call = _json(CALL_REL)
        assert total == call["expected_eu_contribution_per_project_eur"]
        assert call["field_status"]["expected_eu_contribution_per_project_eur"] == (
            "Confirmed"
        )

    def test_the_response_states_that_total_rather_than_leaving_it_derivable(
        self, response
    ):
        assert response["total_lump_sum"] == sum(
            w["lump_sum"] for w in response["work_packages"]
        )
        assert response["total_effort_pm"] == sum(
            p["total_effort_pm"] for p in response["partners"]
        )


class TestTheResponseNamesPseudonymsOnly:
    """``docs/integrations/`` sits outside both legs of the leakage scan.

    The scan covers Tier 3, Tier 4, Tier 5 and the vaults, and the budget *request*
    is in its scope as a Tier 3 integration artifact.  A *response* is not, because
    a response normally arrives from a third party rather than being authored here.
    This one was authored here, so these tests stand in for the scan it escapes.
    """

    def test_every_partner_identifier_is_a_tier_3_pseudonym(self, response):
        """Two steps, because one would pass on a coincidence.

        Tier 3 is pseudonymous: each partner's ``legal_name`` *is* its ``partner_id``.
        So checking the response's ids against the set of legal names proves nothing
        on its own.  The second assertion is the one that carries the claim.
        """
        tier3 = _json(PARTNERS_REL)["partners"]
        assert {p["partner_id"] for p in response["partners"]} == {
            p["partner_id"] for p in tier3
        }
        assert all(p["legal_name"] == p["partner_id"] for p in tier3), (
            "Tier 3 now carries a real legal name. The response reproduces partner "
            "ids, so re-check what this file would disclose before trusting it."
        )

    def test_the_response_carries_no_partner_name_field_at_all(self, response):
        assert all("name" not in entry for entry in response["partners"])

    def test_no_work_package_entry_carries_a_title(self, response):
        assert all("title" not in entry for entry in response["work_packages"])


# ---------------------------------------------------------------------------
# 3. The override is a Tier 4 record, not a session memory
# ---------------------------------------------------------------------------


class TestTheOverrideIsRecorded:
    @pytest.mark.parametrize("clause", SUSPENDED_CLAUSES)
    def test_it_names_each_clause_it_suspends(self, override, clause):
        named = " ".join(entry["rule"] for entry in override["rules_suspended"])
        assert clause in named

    def test_it_suspends_nothing_beyond_that_list(self, override):
        """An override by accretion is as bad as one by omission."""
        assert len(override["rules_suspended"]) == len(SUSPENDED_CLAUSES)

    def test_it_records_that_its_scope_was_corrected(self, override):
        """The ticket named three clauses. The review found three more."""
        assert "§8.1, §8.3 and §17.6.7" in override["scope_correction"]

    def test_each_suspended_rule_states_what_it_says_and_why_it_is_suspended(
        self, override
    ):
        for entry in override["rules_suspended"]:
            assert entry["what_it_requires"].strip()
            assert entry["why_suspended_here"].strip()

    def test_it_names_the_human_who_authorised_it(self, override):
        assert override["authorised_by"] == "operator"
        assert override["authorisation_route"].startswith("CLAUDE.md §1")

    def test_it_declares_that_it_is_not_an_amendment(self, override):
        assert override["is_constitutional_amendment"] is False
        assert "§14" in override["why_it_is_not_an_amendment"]

    def test_it_declares_its_expiry(self, override):
        assert override["expires"].strip()
        assert "ticket" in override["expires"].lower()

    @pytest.mark.parametrize(
        "rule", ["§8.4", "§13.4", "§12.2", "§13.8", "§17.6.3"]
    )
    def test_it_names_the_rules_that_stay_in_force(self, override, rule):
        """An entry may group two clauses, so this reads the clause, not the key."""
        named = " ".join(entry["rule"] for entry in override["still_in_force"])
        assert rule in named

    def test_the_phase_8_block_is_in_force_while_the_source_clause_is_not(
        self, override
    ):
        """§8.4 is split, so neither list may claim the whole section.

        The source clause is suspended, because a hand-authored response is not an
        external one.  The categorical block is not, because it is what stops this
        ticket from unfreezing Phase 8 by itself.
        """
        suspended = next(
            e for e in override["rules_suspended"] if e["rule"].startswith("§8.4")
        )
        in_force = next(
            e for e in override["still_in_force"] if e["rule"].startswith("§8.4")
        )
        assert "source clause" in suspended["rule"]
        assert "Phase 8 block" in in_force["rule"]
        assert "§13.4" in in_force["rule"]

    def test_it_points_at_the_artifact_it_permitted(self, override):
        assert override["artifact_permitted"] == RESPONSE_REL
        assert (REPO / override["artifact_permitted"]).is_file()

    def test_it_records_what_the_fiction_costs(self, override):
        assert override["what_this_costs"].strip()

    def test_the_categorical_block_is_never_suspended(self, override):
        """§13.4 carries the block alone, so it must appear in neither list as suspended."""
        suspended = " ".join(entry["rule"] for entry in override["rules_suspended"])
        assert "§13.4" not in suspended


# ---------------------------------------------------------------------------
# 4. What is still outstanding, and whose step it is
# ---------------------------------------------------------------------------


class TestThePhase7DispatchReachedTheGate:
    """The operator's second dispatch released the node, on 1 October.

    The first dispatch failed at ``agent_body``: the skill declared ``pass`` and
    named a validation artifact it could not write, so §17.6.6 read the empty
    directory off disk and §17.3.2 skipped the gate.  Commit ``67794f3`` gave the
    skill the output contract it was missing.  The re-dispatch wrote both
    artifacts and ``gate_09`` evaluated to pass on 9 of 9 predicates.

    These tests read the gate evaluator's own artifact, never the skill's
    self-declaration.  That distinction is the whole lesson of the first failure:
    a skill saying ``pass`` proved nothing, and §17.6.3 reserves the gate result
    to the evaluator.
    """

    def test_the_validation_directory_holds_the_canonical_artifact(self):
        assert dir_non_empty(VALIDATION_REL, repo_root=REPO).passed, (
            "validation/ is empty again. g08_p03 reads it, so the gate cannot "
            "pass; check whether a rerun cleared it."
        )

    def test_the_artifact_the_assessment_names_is_on_disk(self):
        """The assessment's claim and the directory's contents now agree.

        The first dispatch broke precisely here, so the pairing is worth its own
        test: a reference to a file nobody wrote is what §17.6.6 caught.
        """
        assessment = _json(ASSESSMENT_REL)
        reference = assessment["validation_artifact_reference"]
        assert reference
        assert (REPO / VALIDATION_REL / reference).exists(), (
            f"the assessment names {reference!r}, which is not in validation/"
        )

    def test_the_gate_evaluator_recorded_a_pass(self):
        """§17.6.3: only the evaluator writes this, so only it can be believed."""
        result = _json(PHASE_7_REL + "/gate_result.json")
        assert result["gate_id"] == "gate_09_budget_consistency"
        assert result["status"] == "pass"
        assert result["deterministic_predicates"]["failed"] == []

    def test_the_gate_read_both_directories_it_depends_on(self):
        """g08_p02 reads received/, g08_p03 reads validation/. Both are populated."""
        assert dir_non_empty(RECEIVED_REL, repo_root=REPO).passed
        assert dir_non_empty(VALIDATION_REL, repo_root=REPO).passed

    def test_tier_5_content_carries_the_fictional_label(self):
        """§13.8 falls due the moment Phase 8 drafts a section.

        Vacuous while Tier 5 holds only placeholders, and live from the first
        draft.  The check is deliberately broad — every Tier 5 file, not only
        those quoting a figure — because the demo's entire budget is fictional
        and a reader cannot tell which sentence rests on it.  Fail closed and
        label the section, rather than adjudicate per sentence.
        """
        real = [
            p
            for p in (REPO / TIER_5_REL).rglob("*")
            if p.is_file() and p.name != ".gitkeep"
        ]
        unlabelled = [
            str(p.relative_to(REPO))
            for p in real
            if "fictional" not in p.read_text(encoding="utf-8-sig").lower()
        ]
        assert unlabelled == [], (
            "Tier 5 content rests on fictional budget figures without saying so. "
            "§13.8 requires the deliverable to flag the gap, and the override "
            "record in the decision log carries the obligation."
        )

    def test_the_override_record_carries_the_outstanding_label_obligation(
        self, override
    ):
        assert override["outstanding"]["tier_5_label"].strip()
        assert override["outstanding"]["operator_dispatch"].strip()
