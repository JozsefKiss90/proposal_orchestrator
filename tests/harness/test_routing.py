"""
Tests for harness/routing.py — deterministic-first routing.

Covers:
  - deterministic set is sourced from the runtime PREDICATE_REGISTRY
  - a real deterministic predicate is refused for judging
  - a semantic-gap property is permitted
  - semantic in-run gates do NOT count as deterministic coverage
  - extra_covered augments the set
  - assert_judgeable raises with the covering predicate named
"""

from __future__ import annotations

import pytest

from harness.routing import (
    DeterministicCoverageError,
    RoutingAuthority,
    assert_judgeable,
    deterministic_predicate_names,
    route,
    semantic_inrun_predicate_names,
)


class TestDeterministicSet:
    def test_matches_runtime_registry(self):
        from runner.gate_evaluator import PREDICATE_REGISTRY

        assert deterministic_predicate_names() == frozenset(PREDICATE_REGISTRY.keys())

    def test_known_predicates_present(self):
        names = deterministic_predicate_names()
        # spot-check the predicates the strategy §1 table names as structural.
        assert "source_refs_present" in names
        assert "canonical_terms_preserved" in names
        assert "assumed_claims_are_operator_declared" in names


class TestRoute:
    def test_deterministic_property_refused(self):
        d = route("source_refs_present")
        assert d.deterministically_covered is True
        assert d.judge_permitted is False
        assert d.authority == RoutingAuthority.DETERMINISTIC_PREDICATE
        assert d.covering_predicate == "source_refs_present"

    def test_semantic_gap_permitted(self):
        d = route("source_entails_claim")  # the semantic question source_refs_present leaves open
        assert d.deterministically_covered is False
        assert d.judge_permitted is True
        assert d.authority == RoutingAuthority.SEMANTIC_GAP
        assert d.covering_predicate is None

    def test_semantic_inrun_gate_is_not_deterministic_coverage(self):
        # no_unsupported_tier5_claims is an in-run LLM gate, NOT a deterministic
        # predicate — the out-of-band judge is allowed to re-check it.
        for name in semantic_inrun_predicate_names():
            d = route(name)
            assert d.judge_permitted is True, name

    def test_extra_covered_augments(self):
        d = route("assembler_byte_equal", extra_covered=["assembler_byte_equal"])
        assert d.judge_permitted is False
        assert d.covering_predicate == "assembler_byte_equal"

    def test_to_dict(self):
        d = route("some_semantic_prop").to_dict()
        assert d["judge_permitted"] is True
        assert d["authority"] == "semantic_gap"


class TestAssertJudgeable:
    def test_permitted_returns_decision(self):
        d = assert_judgeable("status_aware_faithfulness")
        assert d.judge_permitted is True

    def test_covered_raises(self):
        with pytest.raises(DeterministicCoverageError) as exc:
            assert_judgeable("canonical_terms_preserved")
        assert exc.value.property_key == "canonical_terms_preserved"
        assert exc.value.covering_predicate == "canonical_terms_preserved"

    def test_raise_message_names_predicate(self):
        with pytest.raises(DeterministicCoverageError, match="canonical_terms_preserved"):
            assert_judgeable("canonical_terms_preserved")

    def test_extra_covered_raises(self):
        with pytest.raises(DeterministicCoverageError):
            assert_judgeable("my_ci_check", extra_covered=["my_ci_check"])
