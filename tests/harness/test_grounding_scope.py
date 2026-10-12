"""
Tests for the grounding-scope declaration (ticket V06).

Three things are under test:

* **The measurement** — how many graded units carried a claim ledger decides
  whether grounding reads unassessable, partly assessed or assessed, and the
  reason sentence is derived from those numbers rather than stored.
* **The declaration** — ``content_focused`` and ``source_grounded`` are the
  audit's two scope choices; anything else is refused, and a
  ``source_grounded`` declaration is refused outright while the imported-claim
  route is unimplemented.
* **The rule that survives X01** — with the capability flag patched on, a
  ``source_grounded`` declaration still needs every unit assessed.
"""

from __future__ import annotations

import pytest

import harness.grounding_scope as gs
from runner.paths import find_repo_root

#: The acceptance-record template V06 authors and V15 fills in.
TEMPLATE = (
    find_repo_root()
    / "docs" / "tier4_orchestration_state" / "msca_dn" / "reviews"
    / "acceptance_record_template.md"
)


# --------------------------------------------------------------------------- #
# The vocabulary
# --------------------------------------------------------------------------- #


class TestTheVocabulary:
    def test_the_two_scope_choices_are_the_audits_two(self):
        assert gs.GROUNDING_SCOPES == (gs.SCOPE_CONTENT_FOCUSED, gs.SCOPE_SOURCE_GROUNDED)

    def test_the_measurements_are_three_and_ordered_from_least_assessed(self):
        assert gs.GROUNDING_MEASUREMENTS == (
            gs.GROUNDING_UNASSESSABLE,
            gs.GROUNDING_PARTLY_ASSESSED,
            gs.GROUNDING_ASSESSED,
        )

    def test_the_imported_claim_route_is_not_implemented(self):
        """X01 flips this.  Until then, a source-grounded declaration is refused."""
        assert gs.IMPORTED_CLAIM_ROUTE_IMPLEMENTED is False


# --------------------------------------------------------------------------- #
# The measurement
# --------------------------------------------------------------------------- #


class TestTheMeasurement:
    @pytest.mark.parametrize(
        "include_claims, with_claims, total, expected",
        [
            (False, 0, 10, gs.GROUNDING_UNASSESSABLE),
            (True, 0, 10, gs.GROUNDING_UNASSESSABLE),
            (True, 4, 10, gs.GROUNDING_PARTLY_ASSESSED),
            (True, 10, 10, gs.GROUNDING_ASSESSED),
            (True, 0, 0, gs.GROUNDING_UNASSESSABLE),
        ],
    )
    def test_the_counts_decide_the_measurement(self, include_claims, with_claims, total, expected):
        assert gs.measure(include_claims=include_claims, with_claims=with_claims, total=total) == expected

    def test_a_withheld_ledger_cannot_measure_as_assessed(self):
        with pytest.raises(gs.GroundingScopeError) as caught:
            gs.measure(include_claims=False, with_claims=3, total=10)
        assert "withheld" in str(caught.value)

    def test_more_units_with_claims_than_units_is_refused(self):
        with pytest.raises(gs.GroundingScopeError):
            gs.measure(include_claims=True, with_claims=11, total=10)

    def test_count_grounded_counts_the_cells_that_carried_a_ledger(self):
        cells = [
            {"grounding": gs.GROUNDING_IN_VERDICT},
            {"grounding": gs.GROUNDING_UNASSESSABLE},
            {"grounding": gs.GROUNDING_IN_VERDICT},
        ]
        assert gs.count_grounded(cells) == (2, 3)

    def test_count_grounded_refuses_a_cell_with_no_grounding_value(self):
        with pytest.raises(gs.GroundingScopeError) as caught:
            gs.count_grounded([{"grounding": gs.GROUNDING_IN_VERDICT}, {"criterion_id": "E"}])
        assert "carries no grounding value" in str(caught.value)

    def test_count_grounded_refuses_an_unknown_grounding_value(self):
        with pytest.raises(gs.GroundingScopeError) as caught:
            gs.count_grounded([{"grounding": "probably_fine"}])
        assert "probably_fine" in str(caught.value)


# --------------------------------------------------------------------------- #
# The reason, derived
# --------------------------------------------------------------------------- #


class TestTheReasonIsDerived:
    def _scope(self, **kwargs):
        params = {
            "declared": gs.SCOPE_CONTENT_FOCUSED,
            "include_claims": False,
            "with_claims": 0,
            "total": 10,
            "unit": gs.UNIT_CELL,
        }
        params.update(kwargs)
        return gs.declare_scope(**params)

    def test_a_withheld_ledger_says_it_was_withheld(self):
        assert "withheld" in self._scope().reason

    def test_an_offered_but_empty_ledger_says_so_instead(self):
        reason = self._scope(include_claims=True).reason
        assert "withheld" not in reason
        assert "no cell carried" in reason

    def test_a_partly_assessed_run_states_both_numbers(self):
        reason = self._scope(include_claims=True, with_claims=4).reason
        assert "4 of 10" in reason

    def test_an_assessed_run_states_the_total(self):
        reason = self._scope(include_claims=True, with_claims=10).reason
        assert "10" in reason
        assert "addressal and grounding together" in reason

    def test_no_graded_unit_says_that_rather_than_an_empty_ledger(self):
        reason = self._scope(include_claims=True, with_claims=0, total=0).reason
        assert "no cell was produced" in reason

    def test_the_headline_names_the_measurement_and_the_declaration(self):
        headline = self._scope().headline
        assert gs.GROUNDING_UNASSESSABLE.upper() in headline
        assert gs.SCOPE_CONTENT_FOCUSED in headline
        assert "0 of 10" in headline

    def test_the_unit_travels_into_the_wording(self):
        assert "pack" in self._scope(unit=gs.UNIT_PACK).reason


# --------------------------------------------------------------------------- #
# The declaration
# --------------------------------------------------------------------------- #


class TestTheDeclaration:
    def test_a_content_focused_declaration_on_an_unassessable_run_is_accepted(self):
        scope = gs.declare_scope(
            gs.SCOPE_CONTENT_FOCUSED,
            include_claims=False,
            with_claims=0,
            total=10,
            unit=gs.UNIT_CELL,
        )
        assert scope.declared == gs.SCOPE_CONTENT_FOCUSED
        assert scope.measured == gs.GROUNDING_UNASSESSABLE
        assert scope.declaration_source == gs.DECLARED_BY_THE_RUN

    def test_an_unknown_scope_is_refused_and_names_the_two_choices(self):
        with pytest.raises(gs.GroundingScopeError) as caught:
            gs.declare_scope("thorough", include_claims=True, with_claims=1, total=1, unit=gs.UNIT_CELL)
        message = str(caught.value)
        assert gs.SCOPE_CONTENT_FOCUSED in message
        assert gs.SCOPE_SOURCE_GROUNDED in message

    def test_no_scope_at_all_is_refused_by_the_same_rule(self):
        with pytest.raises(gs.GroundingScopeError):
            gs.declare_scope(None, include_claims=True, with_claims=1, total=1, unit=gs.UNIT_CELL)

    def test_a_source_grounded_declaration_is_refused_while_x01_is_open(self):
        with pytest.raises(gs.GroundingScopeError) as caught:
            gs.declare_scope(
                gs.SCOPE_SOURCE_GROUNDED,
                include_claims=True,
                with_claims=10,
                total=10,
                unit=gs.UNIT_CELL,
            )
        message = str(caught.value)
        assert "X01" in message
        assert gs.SCOPE_CONTENT_FOCUSED in message

    def test_the_refusal_names_the_three_missing_integrations(self):
        with pytest.raises(gs.GroundingScopeError) as caught:
            gs.declare_scope(
                gs.SCOPE_SOURCE_GROUNDED,
                include_claims=True,
                with_claims=10,
                total=10,
                unit=gs.UNIT_CELL,
            )
        message = str(caught.value)
        for fragment in ("resolvable sources", "backed by evidence", "E2 grounding"):
            assert fragment in message

    def test_with_the_route_implemented_a_fully_assessed_run_may_declare_it(self, monkeypatch):
        monkeypatch.setattr(gs, "IMPORTED_CLAIM_ROUTE_IMPLEMENTED", True)
        scope = gs.declare_scope(
            gs.SCOPE_SOURCE_GROUNDED,
            include_claims=True,
            with_claims=10,
            total=10,
            unit=gs.UNIT_CELL,
        )
        assert scope.declared == gs.SCOPE_SOURCE_GROUNDED
        assert scope.measured == gs.GROUNDING_ASSESSED

    @pytest.mark.parametrize(
        "include_claims, with_claims",
        [(False, 0), (True, 0), (True, 9)],
    )
    def test_even_with_the_route_implemented_an_unassessed_run_may_not_declare_it(
        self, monkeypatch, include_claims, with_claims
    ):
        monkeypatch.setattr(gs, "IMPORTED_CLAIM_ROUTE_IMPLEMENTED", True)
        with pytest.raises(gs.GroundingScopeError) as caught:
            gs.declare_scope(
                gs.SCOPE_SOURCE_GROUNDED,
                include_claims=include_claims,
                with_claims=with_claims,
                total=10,
                unit=gs.UNIT_CELL,
            )
        assert gs.SCOPE_SOURCE_GROUNDED in str(caught.value)


# --------------------------------------------------------------------------- #
# A record that declares nothing
# --------------------------------------------------------------------------- #


class TestTheMeasuredOnlyRecord:
    def test_it_carries_the_measurement_and_no_declaration(self):
        scope = gs.measured_only(include_claims=False, with_claims=0, total=10, unit=gs.UNIT_CELL)
        assert scope.declared is None
        assert scope.measured == gs.GROUNDING_UNASSESSABLE
        assert scope.declaration_source == gs.MEASURED_HERE

    def test_its_headline_says_no_scope_was_declared(self):
        scope = gs.measured_only(include_claims=False, with_claims=0, total=10, unit=gs.UNIT_CELL)
        assert "none declared" in scope.headline

    def test_a_measured_only_record_can_never_read_source_grounded(self):
        """The conservative value is the only one derivation can produce."""
        scope = gs.measured_only(include_claims=True, with_claims=10, total=10, unit=gs.UNIT_CELL)
        assert scope.declared is None
        assert gs.SCOPE_SOURCE_GROUNDED not in scope.to_dict().values()


# --------------------------------------------------------------------------- #
# The persisted shape
# --------------------------------------------------------------------------- #


class TestThePersistedShape:
    def test_to_dict_carries_the_declaration_the_measurement_and_its_numbers(self):
        scope = gs.declare_scope(
            gs.SCOPE_CONTENT_FOCUSED,
            include_claims=False,
            with_claims=0,
            total=10,
            unit=gs.UNIT_CELL,
        )
        assert scope.to_dict() == {
            "declared": gs.SCOPE_CONTENT_FOCUSED,
            "declaration_source": gs.DECLARED_BY_THE_RUN,
            "measured": gs.GROUNDING_UNASSESSABLE,
            "include_claims": False,
            "unit": gs.UNIT_CELL,
            "with_claims": 0,
            "total": 10,
            "reason": scope.reason,
        }

    def test_declared_scope_of_reads_the_declaration_back_out_of_a_record(self):
        record = {"grounding_scope": {"declared": gs.SCOPE_CONTENT_FOCUSED}}
        assert gs.declared_scope_of(record) == gs.SCOPE_CONTENT_FOCUSED

    def test_declared_scope_of_a_record_that_declares_nothing_is_none(self):
        assert gs.declared_scope_of({}) is None
        assert gs.declared_scope_of({"grounding_scope": None}) is None
        assert gs.declared_scope_of({"grounding_scope": {}}) is None

    def test_the_record_is_immutable(self):
        scope = gs.measured_only(include_claims=False, with_claims=0, total=1, unit=gs.UNIT_CELL)
        with pytest.raises(Exception):
            scope.measured = gs.GROUNDING_ASSESSED  # type: ignore[misc]


# --------------------------------------------------------------------------- #
# The acceptance-record template
# --------------------------------------------------------------------------- #


class TestTheAcceptanceRecordTemplate:
    """V06's fourth criterion.  The assertions bind the template to this
    module's vocabulary, so renaming a scope or a measurement fails here
    rather than leaving the template quietly describing something else."""

    @pytest.fixture(scope="class")
    def text(self) -> str:
        assert TEMPLATE.is_file(), TEMPLATE
        return TEMPLATE.read_text(encoding="utf-8")

    def test_it_states_both_of_the_audits_scope_choices(self, text):
        for scope in gs.GROUNDING_SCOPES:
            assert scope in text

    def test_it_reads_each_value_from_the_freeze_records_own_block(self, text):
        for key in ("declared", "declaration_source", "measured", "with_claims", "total", "reason"):
            assert f"grounding_scope.{key}" in text

    def test_it_names_the_x01_condition_on_a_source_grounded_acceptance(self, text):
        assert "X01" in text
        for fragment in ("resolvable sources", "backed by evidence", "E2 grounding"):
            assert fragment in text

    def test_it_offers_the_audits_two_halves_of_the_grounding_sentence(self, text):
        assert "validated" in text
        assert gs.GROUNDING_UNASSESSABLE in text

    def test_it_is_not_signed(self, text):
        assert "Not an approval" in text
        for blank in ("Approval identity", "Date", "Reference"):
            assert blank in text
        assert "`________`" in text
