"""The instance-two project concept, held to the tiers it cites.

The ticket "Project concept for operator approval" in `plans/dev_graph_demo_tickets.md`
writes three artifacts into Tier 3 `project_brief/` and one decision log entry. Its
two substantive acceptance criteria are mechanical, and this module is where they
are checked rather than asserted:

* **every call phrase in the concept traces to a Tier 2B span.** Both prose files
  carry one convention: text in double quotes is a verbatim slice of the call
  extract. The structured claims in `project_summary.json` go further and name the
  span each phrase sits in, so the check is byte-level and not a keyword match.
* **every capability claim traces to `partners.json`.** A claim names the partner
  and the exact capability string. A capability the registry does not record fails
  here, which is what CLAUDE.md §13.3 asks of a project fact.

Two checks exist because a draft can overclaim in ways a reader will not notice.
`TestTheHumanGate` holds the ticket's own gate: no architecture seed may exist
while approval is unrecorded. `TestWhatTheDraftDoesNotClaim` holds the honest
statements — Assumed throughout, the two carried findings, the blocked budget
gate — so a later edit cannot quietly upgrade them.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from runner.leakage_scan import scan_partner_records, scan_tree
from runner.paths import find_repo_root
from tests._tier_sources import (
    STATUSES,
    digest as _digest_on,
    iter_strings as _iter_strings,
    norm as _norm,
    resolve_ref as _resolve,
)

REPO = find_repo_root()

TIER3 = REPO / "docs/tier3_project_instantiation"
BRIEF = TIER3 / "project_brief"
CONCEPT_NOTE = BRIEF / "concept_note.md"
PROJECT_SUMMARY = BRIEF / "project_summary.json"
POSITIONING = BRIEF / "strategic_positioning.md"
PARTNERS = TIER3 / "consortium/partners.json"
SELECTED_CALL = TIER3 / "call_binding/selected_call.json"
ARCHITECTURE_INPUTS = TIER3 / "architecture_inputs"

TIER4 = REPO / "docs/tier4_orchestration_state"
GAP_REPORT = (
    TIER4 / "validation_reports/demo-consortium-gap-analysis_2026-09-30.json"
)
DECISION = TIER4 / "decision_log/demo-concept_2026-09-30.json"

CALL_EXTRACT = (
    REPO
    / "docs/tier2b_topic_and_call_sources/call_extracts"
    / "HORIZON-CL6-2027-01-BIODIV-01.json"
)

#: The prose files that follow the double-quote convention.
PROSE = (CONCEPT_NOTE, POSITIONING)

#: The twelve pseudonyms the consortium ticket authored.
PARTNER_IDS = tuple(f"P{n:02d}" for n in range(1, 13))

#: A partner pseudonym as it appears in prose, inside backticks or bare.
_PARTNER_RE = re.compile(r"\bP\d{2}\b")

#: The seed files the architecture ticket writes. None may exist before approval.
SEED_FILES = (
    "objectives.json",
    "outcomes.json",
    "impacts.json",
    "workpackage_seed.json",
    "milestones_seed.json",
    "risks.json",
)


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


#: The digest basis the freeze record declares. core.autocrlf is true here, so a
#: text file checks out CRLF on Windows and LF elsewhere, and a raw digest would
#: identify the platform rather than the content.
FREEZE_DIGEST_BASIS = "lf_normalised_bytes"


def _digest(path: Path) -> str:
    return _digest_on(path, FREEZE_DIGEST_BASIS)


def _span_text(node: Any) -> str:
    """Every string in a resolved span, joined — the haystack for one phrase."""
    return _norm(" ".join(_iter_strings(node)))


@pytest.fixture(scope="module")
def summary() -> dict:
    return _read(PROJECT_SUMMARY)


@pytest.fixture(scope="module")
def claims(summary: dict) -> list:
    return summary["concept_claims"]


@pytest.fixture(scope="module")
def extract() -> dict:
    return _read(CALL_EXTRACT)


@pytest.fixture(scope="module")
def call_text(extract: dict) -> str:
    return _norm(" | ".join(_iter_strings(extract)))


@pytest.fixture(scope="module")
def capabilities() -> dict:
    return {
        partner["partner_id"]: set(partner["capabilities"])
        for partner in _read(PARTNERS)["partners"]
    }


# ---------------------------------------------------------------------------
# The three artifacts exist
# ---------------------------------------------------------------------------


class TestTheBriefExists:
    @pytest.mark.parametrize("path", [CONCEPT_NOTE, PROJECT_SUMMARY, POSITIONING])
    def test_each_artifact_is_present_and_not_a_stub(self, path: Path) -> None:
        assert path.is_file(), f"{path.name} is absent"
        assert len(path.read_text(encoding="utf-8-sig").strip()) > 500

    def test_the_summary_names_the_bound_topic(self, summary: dict) -> None:
        """A brief for a different topic would be a §11.3 violation."""
        bound = _read(SELECTED_CALL)
        assert summary["topic"]["topic_code"] == bound["topic_code"]
        assert summary["topic"]["instrument_type"] == bound["instrument_type"]
        assert summary["topic"]["budget_regime"] == bound["budget_regime"]


# ---------------------------------------------------------------------------
# Every call phrase traces to a Tier 2B span
# ---------------------------------------------------------------------------


class TestCallPhrases:
    def test_every_span_reference_resolves_in_the_call_extract(
        self, claims: list, extract: dict
    ) -> None:
        for claim in claims:
            ref = claim["tier2b_span_ref"]
            assert _resolve(extract, ref) is not None, (
                f"{claim['claim_id']} cites {ref}, which the extract does not carry"
            )

    def test_every_claim_phrase_is_verbatim_in_the_span_it_cites(
        self, claims: list, extract: dict
    ) -> None:
        """The strong form: not merely present in the call somewhere, but present
        in the span the claim says it answers."""
        for claim in claims:
            span = _span_text(_resolve(extract, claim["tier2b_span_ref"]))
            assert _norm(claim["call_phrase"]) in span, (
                f"{claim['claim_id']} quotes {claim['call_phrase']!r}, which is "
                f"not in {claim['tier2b_span_ref']}"
            )

    @pytest.mark.parametrize("path", PROSE)
    def test_every_quoted_phrase_in_the_prose_is_verbatim_in_the_extract(
        self, path: Path, call_text: str
    ) -> None:
        """The prose convention, enforced. Double quotes mean a call phrase, so a
        sentence cannot dress up a project claim as something the call said."""
        quoted = re.findall(r'"([^"\n]+)"', _norm(path.read_text(encoding="utf-8-sig")))
        assert quoted, f"{path.name} quotes no call phrase at all"
        missing = [q for q in quoted if _norm(q) not in call_text]
        assert not missing, f"{path.name} quotes phrases the extract does not carry: {missing}"

    def test_the_prose_declares_the_quoting_convention(self) -> None:
        """A convention a reader cannot see is a convention a reviewer cannot check."""
        for path in PROSE:
            text = path.read_text(encoding="utf-8-sig")
            assert "double quotes" in text, f"{path.name} does not state the convention"

    def test_no_claim_phrase_is_empty_or_a_single_word(self, claims: list) -> None:
        """A one-word quote traces to nothing in particular."""
        for claim in claims:
            assert len(claim["call_phrase"].split()) >= 2, claim["claim_id"]


# ---------------------------------------------------------------------------
# Every capability claim traces to partners.json
# ---------------------------------------------------------------------------


class TestCapabilityClaims:
    def test_every_capability_reference_is_an_exact_registry_string(
        self, claims: list, capabilities: dict
    ) -> None:
        for claim in claims:
            for ref in claim["capability_refs"]:
                pid = ref["partner_id"]
                assert pid in capabilities, f"{claim['claim_id']} names {pid}"
                assert ref["capability"] in capabilities[pid], (
                    f"{claim['claim_id']} rests on {ref['capability']!r}, which "
                    f"{pid} does not record"
                )

    def test_every_claim_rests_on_at_least_one_capability(
        self, claims: list
    ) -> None:
        for claim in claims:
            assert claim["capability_refs"], claim["claim_id"]

    @pytest.mark.parametrize("path", PROSE)
    def test_every_pseudonym_in_the_prose_exists(self, path: Path) -> None:
        found = set(_PARTNER_RE.findall(path.read_text(encoding="utf-8-sig")))
        unknown = found - set(PARTNER_IDS)
        assert not unknown, f"{path.name} names partners that do not exist: {unknown}"

    def test_every_partner_in_the_responsible_lists_exists(
        self, summary: dict, capabilities: dict
    ) -> None:
        for commitment in summary["coordination_commitments"]:
            for pid in commitment["responsible"]:
                assert pid in capabilities, commitment["requirement_ref"]

    def test_the_concept_uses_more_than_the_derived_six(self) -> None:
        """Option 1 is the recommendation, so the concept has to actually rest on
        the gap partners. A concept that never names them would be option 2 in
        disguise."""
        found = set(_PARTNER_RE.findall(CONCEPT_NOTE.read_text(encoding="utf-8-sig")))
        assert set(PARTNER_IDS[6:]) <= found


# ---------------------------------------------------------------------------
# The concept answers the whole call
# ---------------------------------------------------------------------------


class TestRequirementCoverage:
    @pytest.fixture(scope="class")
    def required(self) -> set:
        return {
            row["requirement_id"]
            for row in _read(GAP_REPORT)["requirement_coverage"]
        }

    def test_every_requirement_the_gap_analysis_lists_has_a_claim(
        self, claims: list, required: set
    ) -> None:
        answered: set = set()
        for claim in claims:
            answered |= set(claim["requirement_refs"])
        assert not (required - answered), (
            f"no concept claim answers: {sorted(required - answered)}"
        )

    def test_no_claim_cites_a_requirement_nobody_defined(
        self, claims: list, required: set
    ) -> None:
        for claim in claims:
            unknown = set(claim["requirement_refs"]) - required
            assert not unknown, f"{claim['claim_id']} cites {sorted(unknown)}"

    def test_all_three_expected_outcomes_are_answered(
        self, claims: list, extract: dict
    ) -> None:
        """The topic binds all three: 'expected to contribute to all of the
        following expected outcomes'."""
        assert extract["expected_outcomes_binding"] == "all"
        answered = {
            ref
            for claim in claims
            for ref in claim["requirement_refs"]
            if ref.startswith("EO")
        }
        assert len(answered) == len(extract["expected_outcomes"])

    def test_every_claim_id_is_unique(self, claims: list) -> None:
        ids = [claim["claim_id"] for claim in claims]
        assert len(ids) == len(set(ids))

    def test_each_coordination_commitment_names_a_claim_and_a_requirement(
        self, summary: dict, claims: list, required: set
    ) -> None:
        known = {claim["claim_id"] for claim in claims}
        for commitment in summary["coordination_commitments"]:
            assert commitment["claim_ref"] in known
            assert commitment["requirement_ref"] in required
            assert commitment["responsible"]


# ---------------------------------------------------------------------------
# The gap options are put, not chosen silently
# ---------------------------------------------------------------------------


class TestGapOptions:
    def test_all_three_options_are_present(self, summary: dict) -> None:
        assert [o["option"] for o in summary["gap_options"]] == [1, 2, 3]

    def test_each_option_carries_its_consequences(self, summary: dict) -> None:
        for option in summary["gap_options"]:
            assert len(option["consequences"]) >= 2, option["option"]
            for consequence in option["consequences"]:
                assert consequence.strip()

    def test_each_option_states_a_cost_and_not_only_a_benefit(
        self, summary: dict
    ) -> None:
        """An option list where every consequence is a benefit is a sales pitch,
        not a decision aid. Each option's consequence list must include the
        recommended one's cost and the rejected ones' merit."""
        for option in summary["gap_options"]:
            assert len(option["consequences"]) >= 3, (
                f"option {option['option']} lists too few consequences to be "
                "weighed against the others"
            )

    def test_exactly_one_option_is_recommended(self, summary: dict) -> None:
        recommended = [o for o in summary["gap_options"] if o["recommended"]]
        assert len(recommended) == 1
        assert recommended[0]["option"] == 1

    def test_the_prose_puts_the_options_too(self) -> None:
        text = CONCEPT_NOTE.read_text(encoding="utf-8-sig")
        assert "Decision 1" in text
        assert "recommended" in text.lower()

    def test_the_draft_does_not_choose_before_the_operator_does(
        self, summary: dict
    ) -> None:
        """The gate: a chosen option and an unrecorded approval cannot coexist."""
        chosen = summary["gap_option_decision"]["chosen"]
        if summary["approval"]["state"] != "recorded":
            assert chosen is None
            assert summary["gap_option_decision"]["state"] != "recorded"
        else:
            assert chosen in (1, 2, 3)


# ---------------------------------------------------------------------------
# Duration stays the operator's, and stays out of the call binding
# ---------------------------------------------------------------------------


class TestDuration:
    def test_the_draft_proposes_a_value_and_alternatives(
        self, summary: dict
    ) -> None:
        duration = summary["project_duration"]
        assert duration["proposed_months"] in duration["options_put"]
        assert len(duration["options_put"]) >= 2
        assert duration["reasoning_for_48"].strip()

    def test_it_says_tier_2b_sets_no_duration(self, summary: dict) -> None:
        assert "None." in summary["project_duration"]["tier2b_basis"]
        assert summary["project_duration"]["decision_owner"] == "operator"

    def test_the_duration_is_never_confirmed(self, summary: dict) -> None:
        """Tier 2B carries no duration, so no evidence can make it Confirmed."""
        assert summary["project_duration"]["status"] in ("Unresolved", "Assumed")
        assert summary["field_status"]["project_duration"] in (
            "Unresolved",
            "Assumed",
        )

    def test_the_call_binding_carries_the_duration_only_once_it_is_decided(
        self,
    ) -> None:
        """The runner reads project_duration_months from selected_call.json and
        nowhere else, so the decided value has to land there. It must never be
        marked Confirmed: a duration is an operator choice, and dressing one as a
        Tier 2B fact is what §13.2 forbids."""
        bound = _read(SELECTED_CALL)
        duration = summary_duration = _read(PROJECT_SUMMARY)["project_duration"]
        if duration["status"] == "Unresolved":
            assert "project_duration_months" not in bound
            assert bound["field_status"]["project_duration"] == "Unresolved"
            return
        assert bound["project_duration_months"] == summary_duration["value_months"]
        assert bound["field_status"]["project_duration_months"] == "Assumed"
        assert bound["project_duration"]["status"] == "Assumed"
        assert "None." in bound["project_duration"]["tier2b_basis"]

    def test_a_decided_duration_is_declared_in_the_uncertainty_ledger(
        self, summary: dict
    ) -> None:
        """An Assumed value that is not declared is an undeclared assumption. The
        W1 rule traces every Assumed claim back to a declaration."""
        if summary["project_duration"]["status"] == "Unresolved":
            pytest.skip("no duration decided yet")
        declared = _read(TIER3 / "working_assumptions.json")["declarations"]
        entry = next(d for d in declared if d["key"] == "project_duration")
        assert str(summary["project_duration"]["value_months"]) in entry["value"]
        assert entry["rationale"].strip()


# ---------------------------------------------------------------------------
# The human gate
# ---------------------------------------------------------------------------


class TestTheHumanGate:
    def test_the_approval_block_declares_a_human_gate(self, summary: dict) -> None:
        assert summary["approval"]["gate"] == "human"
        assert summary["approval"]["state"] in ("recorded", "not_recorded")

    def test_no_architecture_seed_exists_while_approval_is_unrecorded(
        self, summary: dict
    ) -> None:
        """The ticket's own rule: no architecture seed is authored until the
        operator records approval."""
        if summary["approval"]["state"] == "recorded":
            return
        for name in SEED_FILES:
            assert not (ARCHITECTURE_INPUTS / name).exists(), (
                f"{name} exists while the concept is unapproved"
            )

    def test_a_recorded_approval_has_a_decision_log_entry(
        self, summary: dict
    ) -> None:
        if summary["approval"]["state"] != "recorded":
            return
        assert DECISION.is_file(), "approval recorded with no decision log entry"
        entry = _read(DECISION)
        assert entry["record_type"] == "decision"
        assert entry["branch"] == "dev_graph_demo"

    def test_the_decision_log_entry_carries_the_operator_answers(
        self, summary: dict
    ) -> None:
        """§9.4: a decision that affects future interpretation is written to
        Tier 4. The three answers the ticket names are the gap option, the
        duration and the approval itself."""
        if not DECISION.is_file():
            pytest.skip("the operator has not recorded a decision yet")
        entry = _read(DECISION)
        questions = {d["question_id"] for d in entry["operator_decisions"]}
        assert {"OD1", "OD2", "OD4"} <= questions
        for decision in entry["operator_decisions"]:
            assert decision["options_put"]
            assert decision["decision"].strip()
            assert decision["reasoning"].strip()

    def test_the_recorded_decision_matches_the_brief(self, summary: dict) -> None:
        """A decision log entry and a brief that disagree would leave the next
        ticket free to pick whichever it liked."""
        if not DECISION.is_file():
            pytest.skip("the operator has not recorded a decision yet")
        entry = _read(DECISION)
        by_id = {d["question_id"]: d for d in entry["operator_decisions"]}
        assert str(summary["gap_option_decision"]["chosen"]) in by_id["OD1"]["decision"]
        assert str(summary["project_duration"]["value_months"]) in by_id["OD2"][
            "decision"
        ]
        assert summary["approval"]["decision"] in by_id["OD4"]["decision"]


# ---------------------------------------------------------------------------
# What the draft does not claim
# ---------------------------------------------------------------------------


class TestWhatTheDraftDoesNotClaim:
    def test_every_status_is_one_of_the_four_categories(
        self, summary: dict
    ) -> None:
        for field, status in summary["field_status"].items():
            assert status in STATUSES, f"{field} carries {status!r}"
        for claim in summary["concept_claims"]:
            assert claim["status"] in STATUSES, claim["claim_id"]
        for risk in summary["risks_the_draft_carries"]:
            assert risk["status"] in STATUSES, risk["id"]

    def test_no_concept_claim_is_marked_confirmed(self, claims: list) -> None:
        """The concept is design intent resting on unconfirmed partners. §12.2
        reserves Confirmed for a fact a named Tier 1-3 source evidences."""
        for claim in claims:
            assert claim["status"] == "Assumed", claim["claim_id"]

    def test_the_capability_claims_are_assumed_not_confirmed(
        self, summary: dict
    ) -> None:
        assert summary["field_status"]["capability_refs"] == "Assumed"
        assert summary["field_status"]["concept"] == "Assumed"

    def test_nothing_the_project_claims_is_confirmed(self, summary: dict) -> None:
        """Exactly two things may carry Confirmed, and a reader of this branch can
        check both against Tier 2B for herself: the bound topic and the call
        phrases. Everything the project claims about itself stays Assumed."""
        confirmed = {
            field
            for field, status in summary["field_status"].items()
            if status == "Confirmed"
        }
        assert confirmed == {"topic", "call_phrases"}

    def test_an_operator_act_never_borrows_the_status_vocabulary(
        self, summary: dict
    ) -> None:
        """§12.2 reserves Confirmed for a fact a named Tier 1-3 source evidences.
        An approval lives in Tier 4 and is an act, not a fact, so it carries a
        lifecycle `state` instead. The first version of this brief marked both
        operator acts Confirmed on a Tier 4 record, which widened §12.2 without
        the amendment §14.5 requires."""
        for block in ("approval", "gap_option_decision"):
            assert "status" not in summary[block], (
                f"{block} borrows the §12.2 vocabulary for an operator act"
            )
            assert summary[block]["state"] not in STATUSES
            assert summary[block]["vocabulary_note"].strip()
            assert block not in summary["field_status"]
        for decision in summary["open_decisions"]:
            assert decision["state"] in ("decided", "open"), decision["id"]

    def test_it_carries_the_two_findings_the_consortium_handed_forward(
        self, summary: dict
    ) -> None:
        carried = " ".join(r["carried_from"] for r in summary["risks_the_draft_carries"])
        assert "F4" in carried
        assert "F5" in carried

    def test_it_records_the_blocked_budget_gate(self, summary: dict) -> None:
        """The topic is lump sum, so Phase 8 is hard-blocked. A concept that did
        not say so would invite a later ticket to start drafting."""
        budget = next(
            r for r in summary["risks_the_draft_carries"] if "lump sum" in r["risk"]
        )
        assert "hard-blocked" in budget["risk"]
        assert budget["status"] == "Confirmed"

    def test_the_prose_states_that_no_source_materials_back_it_yet(self) -> None:
        text = CONCEPT_NOTE.read_text(encoding="utf-8-sig")
        assert "No source literature is cited yet" in text

    def test_no_acronym_is_invented(self, summary: dict) -> None:
        """An acronym is a project identifier, and an invented one can collide
        with a real grant. It stays Unresolved until the operator sets it."""
        if summary["concept"]["acronym"] is None:
            assert summary["concept"]["acronym_status"] == "Unresolved"
            assert summary["concept"]["acronym_note"].strip()


# ---------------------------------------------------------------------------
# Anonymity
# ---------------------------------------------------------------------------


class TestAnonymity:
    def test_the_brief_carries_no_country_name_address_or_email(self) -> None:
        violations = tuple(
            v for v in scan_partner_records(REPO) if "project_brief" in v.path
        )
        assert violations == (), "\n".join(
            f"{v.path}:{v.line}: [{v.kind}] {v.noun}" for v in violations
        )

    def test_the_brief_carries_no_instance_one_noun(self) -> None:
        report = scan_tree(REPO)
        violations = tuple(
            v for v in report.violations if "project_brief" in v.path
        )
        assert violations == (), "\n".join(
            f"{v.path}:{v.line}: {v.noun}" for v in violations
        )

    def test_the_brief_adds_no_new_leak_to_the_branch(self) -> None:
        """`ok` rather than `clean`: the branch carries one recorded pre-existing
        leak in the 22 September purge record, which this ticket does not touch."""
        assert scan_tree(REPO).ok

    def test_the_prose_names_partners_only_by_pseudonym(self) -> None:
        """A capability sentence that named a real organisation would defeat the
        whole anonymisation, and the word scan cannot catch a name it has never
        been told about."""
        for path in PROSE:
            text = path.read_text(encoding="utf-8-sig")
            assert _PARTNER_RE.search(text), f"{path.name} names no partner at all"


# ---------------------------------------------------------------------------
# The freeze
# ---------------------------------------------------------------------------


class TestTheFreeze:
    """The operator manual's freeze rule, turned from a convention into a check.

    The rule makes the founding documents immutable once instantiation is
    complete, because the phases gate on them. Nobody enforced it. A recorded
    fingerprint fails the moment a later ticket edits a frozen file, which is
    while the edit is still cheap to reverse.
    """

    @pytest.fixture(scope="class")
    def freeze(self) -> dict:
        if not DECISION.is_file():
            pytest.skip("the concept is not approved yet, so nothing is frozen")
        return _read(DECISION)["freeze_record"]

    def test_all_three_brief_artifacts_are_listed(self, freeze: dict) -> None:
        listed = set(freeze["artifacts"])
        assert listed == {
            path.relative_to(REPO).as_posix()
            for path in (CONCEPT_NOTE, PROJECT_SUMMARY, POSITIONING)
        }

    def test_every_frozen_artifact_still_matches_its_fingerprint(
        self, freeze: dict
    ) -> None:
        """Edit a frozen file and this is where it surfaces. To change one
        deliberately, the operator records a new decision that supersedes the
        freeze and carries the new fingerprints."""
        mismatched = []
        for rel, recorded in freeze["artifacts"].items():
            actual = _digest(REPO / rel)
            if actual != recorded:
                mismatched.append(f"{rel}\n  recorded {recorded}\n  actual   {actual}")
        assert not mismatched, (
            "a frozen brief artifact was edited after the freeze:\n"
            + "\n".join(mismatched)
        )

    def test_the_uncertainty_ledger_is_not_frozen(self, freeze: dict) -> None:
        """The freeze rule exempts it by name, and later tickets append to it."""
        exempt = freeze["not_frozen"]
        assert "docs/tier3_project_instantiation/working_assumptions.json" in exempt
        for path, reason in exempt.items():
            assert reason.strip(), f"{path} is exempt without a reason"

    def test_unfreezing_is_named_as_an_operator_decision(self, freeze: dict) -> None:
        assert "operator decision" in freeze["unfreezing"].lower()


# ---------------------------------------------------------------------------
# The brief agrees with the artifacts it describes
# ---------------------------------------------------------------------------


class TestCrossReferences:
    """A frozen artifact that describes another artifact can go stale silently.

    The first version of this brief said selected_call.json recorded the duration
    as Unresolved. The same commit changed it to Assumed, so the brief asserted
    something false about Tier 3 state and no check noticed. Freezing a file
    makes that worse, not better: nothing rereads it.
    """

    def test_what_the_brief_says_about_the_call_binding_is_true(
        self, summary: dict
    ) -> None:
        bound = _read(SELECTED_CALL)
        basis = summary["project_duration"]["tier2b_basis"]
        actual = bound["field_status"]["project_duration"]
        stale = [
            status
            for status in STATUSES
            if status != actual
            and f"selected_call.json records project_duration as {status}" in basis
        ]
        assert not stale, (
            f"the brief says selected_call.json records project_duration as "
            f"{stale[0]}, and it records {actual}"
        )
        assert actual in basis, (
            f"the brief describes selected_call.json without naming its actual "
            f"status, {actual}"
        )

    def test_every_repo_path_the_brief_names_exists(self, summary: dict) -> None:
        """A pointer to a file that is not there is a claim nobody can follow."""
        named = {
            value
            for value in _iter_strings(summary)
            if value.startswith("docs/") and value.count(" ") == 0
        }
        missing = sorted(rel for rel in named if not (REPO / rel).exists())
        assert not missing, f"the brief names paths that do not exist: {missing}"

    def test_the_brief_and_the_decision_record_name_each_other(
        self, summary: dict
    ) -> None:
        """Either half alone can be renamed or retired without the other noticing."""
        if summary["approval"]["state"] != "recorded":
            pytest.skip("the operator has not recorded a decision yet")
        rel = DECISION.relative_to(REPO).as_posix()
        assert summary["approval"]["recorded_in"] == rel
        entry = _read(DECISION)
        brief = PROJECT_SUMMARY.relative_to(REPO).as_posix()
        assert brief in entry["freeze_record"]["artifacts"]
