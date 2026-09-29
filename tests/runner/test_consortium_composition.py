"""The consortium-composition condition, evaluated as a pure function.

`runner/consortium_composition.py` answers one question: does a set of
pseudonymous partner records satisfy the Tier 1 consortium-composition
condition? The condition is read from
`docs/tier1_normative_framework/extracted/participation_rules.json`, never from
programme knowledge (CLAUDE.md §10.6), and every result carries the span it was
read from (§10.5).

These checks drive the evaluator on synthetic slots, so the logic is pinned
independently of the demo's own twelve partners. The checks that hold the real
`partners.json` to the condition live in `tests/test_demo_consortium.py`.

The limbs the evaluator has to get right:

* three *independent* beneficiaries, so an affiliated entity adds nothing;
* three *distinct* countries, so two partners in one slot count once;
* at least one slot that is a Member State;
* at least two *other* slots that are Member States or Associated Countries.
"""
from __future__ import annotations

import pytest

from runner.consortium_composition import (
    AC,
    MS,
    Beneficiary,
    CompositionRule,
    evaluate_composition,
    load_composition_rule,
    load_partners,
)
from runner.paths import find_repo_root

REPO = find_repo_root()


def b(
    partner_id: str,
    slot: str,
    slot_class: str = MS,
    *,
    independent: bool = True,
    beneficiary: bool = True,
) -> Beneficiary:
    """A synthetic partner record, defaulting to an independent MS beneficiary."""
    return Beneficiary(
        partner_id=partner_id,
        country_slot=slot,
        slot_class=slot_class,
        independent=independent,
        is_beneficiary=beneficiary,
    )


@pytest.fixture(scope="module")
def rule() -> CompositionRule:
    """The condition as Tier 1 records it."""
    return load_composition_rule(REPO)


class TestTheRuleIsRead:
    def test_the_thresholds_come_from_tier_1(self, rule: CompositionRule) -> None:
        assert rule.minimum_independent_beneficiaries == 3
        assert rule.minimum_distinct_countries == 3
        assert rule.minimum_in_a_member_state == 1
        assert rule.minimum_others_in_member_or_associated_countries == 2

    def test_it_carries_the_spans_it_was_read_from(
        self, rule: CompositionRule
    ) -> None:
        assert rule.citations, "a rule with no span is a rule from memory"
        for citation in rule.citations:
            assert citation.quote.strip()
            assert citation.source_document.endswith(".pdf")
            assert citation.source_page > 0

    def test_it_records_that_affiliated_entities_do_not_count(
        self, rule: CompositionRule
    ) -> None:
        assert rule.affiliated_entities_count is False


class TestTheLimbs:
    def test_three_independent_slots_with_one_member_state_meet_it(
        self, rule: CompositionRule
    ) -> None:
        result = evaluate_composition(
            [b("P1", "C1", MS), b("P2", "C2", AC), b("P3", "C3", AC)], rule
        )
        assert result.met
        assert result.failed_limbs == ()
        assert result.satisfying_selection is not None
        assert len(result.satisfying_selection) == 3

    def test_two_slots_fail_the_distinct_country_limb(
        self, rule: CompositionRule
    ) -> None:
        result = evaluate_composition(
            [b("P1", "C1", MS), b("P2", "C2", MS), b("P3", "C1", MS)], rule
        )
        assert not result.met
        assert "distinct_countries" in result.failed_limbs
        assert result.distinct_country_slots == ("C1", "C2")
        assert result.satisfying_selection is None

    def test_three_associated_countries_fail_the_member_state_limb(
        self, rule: CompositionRule
    ) -> None:
        result = evaluate_composition(
            [b("P1", "C1", AC), b("P2", "C2", AC), b("P3", "C3", AC)], rule
        )
        assert not result.met
        assert "member_state" in result.failed_limbs

    def test_two_beneficiaries_fail_the_count_limb(
        self, rule: CompositionRule
    ) -> None:
        result = evaluate_composition([b("P1", "C1", MS), b("P2", "C2", AC)], rule)
        assert not result.met
        assert "independent_beneficiaries" in result.failed_limbs

    def test_an_affiliated_entity_adds_no_country(
        self, rule: CompositionRule
    ) -> None:
        partners = [
            b("P1", "C1", MS),
            b("P2", "C2", AC),
            b("P3", "C3", AC, independent=False),
        ]
        result = evaluate_composition(partners, rule)
        assert not result.met
        assert "C3" not in result.distinct_country_slots
        assert result.excluded == ("P3",)

    def test_a_non_beneficiary_adds_no_country(self, rule: CompositionRule) -> None:
        partners = [
            b("P1", "C1", MS),
            b("P2", "C2", AC),
            b("P3", "C3", AC, beneficiary=False),
        ]
        result = evaluate_composition(partners, rule)
        assert not result.met
        assert result.excluded == ("P3",)

    def test_a_slot_in_neither_list_cannot_fill_a_limb(
        self, rule: CompositionRule
    ) -> None:
        """A third-country slot is eligible to participate, not to count."""
        partners = [b("P1", "C1", MS), b("P2", "C2", AC), b("P3", "C9", "TC")]
        result = evaluate_composition(partners, rule)
        assert not result.met
        assert "other_countries" in result.failed_limbs

    def test_six_slots_meet_it_and_the_selection_is_deterministic(
        self, rule: CompositionRule
    ) -> None:
        partners = [
            b("P1", "C1", MS),
            b("P2", "C2", MS),
            b("P3", "C3", MS),
            b("P4", "C4", AC),
            b("P5", "C5", MS),
            b("P6", "C6", AC),
        ]
        first = evaluate_composition(partners, rule)
        second = evaluate_composition(list(reversed(partners)), rule)
        assert first.met and second.met
        assert first.satisfying_selection == second.satisfying_selection

    def test_the_result_carries_the_tier_1_citation(
        self, rule: CompositionRule
    ) -> None:
        result = evaluate_composition(
            [b("P1", "C1", MS), b("P2", "C2", AC), b("P3", "C3", AC)], rule
        )
        assert result.citations == rule.citations
        assert result.reason.strip()


class TestPartnerLoading:
    def test_it_reads_the_demo_partners(self) -> None:
        partners = load_partners(REPO)
        assert len(partners) == 12
        assert [p.partner_id for p in partners] == [
            f"P{n:02d}" for n in range(1, 13)
        ]
        assert all(p.independent and p.is_beneficiary for p in partners)

    def test_every_slot_class_is_ms_or_ac(self) -> None:
        assert {p.slot_class for p in load_partners(REPO)} == {MS, AC}
