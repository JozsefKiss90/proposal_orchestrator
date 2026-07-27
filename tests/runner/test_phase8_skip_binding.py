"""
Unit tests for the single authoritative Phase-8 skip binding
(``runner/phase8_skip_binding.py``) and the load-time invariants that keep the
derived tables from drifting from it (PRE-2/PRE-3, ticket 3).

Two layers are covered:

  A. ``validate_skip_binding`` — the fail-closed runtime contract the scheduler
     calls before it suppresses a drafting skill: an unmatched id or an empty
     skip set is a reasoned failure, an in-agreement id passes.
  B. The single source of truth — every derived table
     (``PRESEED_NODE_CONFIG``, ``REUSE_SKIP_SKILLS``, ``REUSE_ELIGIBLE_NODES``,
     ``_ASSEMBLER_SUPERSEDES_DRAFTING_SKILL``) agrees with
     ``PHASE8_DRAFTING_SKILL_BY_NODE`` at import, and the ``assert_*`` helpers
     raise ``SkipBindingError`` on any divergence.
"""

from __future__ import annotations

import pytest

from runner.agent_runtime import _ASSEMBLER_SUPERSEDES_DRAFTING_SKILL
from runner.phase8_preseed import PRESEED_NODE_CONFIG
from runner.phase8_reuse import REUSE_ELIGIBLE_NODES, REUSE_SKIP_SKILLS
from runner.phase8_skip_binding import (
    PHASE8_DRAFTING_SKILL_BY_NODE,
    SkipBindingError,
    assert_agrees_with_source,
    assert_nodes_match_source,
    drafting_skill_for,
    validate_skip_binding,
)


# ---------------------------------------------------------------------------
# A. validate_skip_binding — fail-closed runtime contract
# ---------------------------------------------------------------------------


class TestValidateSkipBinding:
    _NODE = "n08a_excellence_drafting"
    _SKILL = "excellence-section-drafting"

    def test_matched_id_passes(self) -> None:
        assert (
            validate_skip_binding(self._NODE, [self._SKILL], [self._SKILL, "audit"])
            is None
        )

    def test_unmatched_id_is_a_failure(self) -> None:
        reason = validate_skip_binding(
            self._NODE, ["excellence-section-drafting-v2"], [self._SKILL]
        )
        assert reason is not None
        assert "excellence-section-drafting-v2" in reason
        assert self._NODE in reason

    def test_empty_skip_set_is_a_failure(self) -> None:
        """PRE-3: a supersession with nothing bound to suppress must fail."""
        reason = validate_skip_binding(self._NODE, [], [self._SKILL])
        assert reason is not None
        assert "empty" in reason

    def test_reports_only_the_unmatched_ids(self) -> None:
        reason = validate_skip_binding(
            self._NODE, [self._SKILL, "ghost-skill"], [self._SKILL]
        )
        assert reason is not None
        assert "ghost-skill" in reason
        # The matched one is not reported as unmatched.
        assert "'excellence-section-drafting'," not in reason

    def test_resolved_ids_accepts_any_iterable(self) -> None:
        assert (
            validate_skip_binding(self._NODE, [self._SKILL], {self._SKILL})
            is None
        )


# ---------------------------------------------------------------------------
# B. Single source of truth — derived tables agree at import
# ---------------------------------------------------------------------------


class TestSingleSourceAgreement:
    def test_drafting_skill_for_returns_the_source(self) -> None:
        for node, skill in PHASE8_DRAFTING_SKILL_BY_NODE.items():
            assert drafting_skill_for(node) == skill
        assert drafting_skill_for("n08d_assembly") is None
        assert drafting_skill_for("nope") is None

    def test_preseed_config_agrees_with_source(self) -> None:
        derived = {
            node: cfg["skipped_skill"]
            for node, cfg in PRESEED_NODE_CONFIG.items()
        }
        assert derived == PHASE8_DRAFTING_SKILL_BY_NODE

    def test_reuse_skip_skills_is_the_source(self) -> None:
        assert REUSE_SKIP_SKILLS == PHASE8_DRAFTING_SKILL_BY_NODE

    def test_reuse_eligible_nodes_cover_the_same_nodes(self) -> None:
        assert set(REUSE_ELIGIBLE_NODES) == set(PHASE8_DRAFTING_SKILL_BY_NODE)

    def test_assembler_supersessions_are_authoritative_skills(self) -> None:
        assert set(_ASSEMBLER_SUPERSEDES_DRAFTING_SKILL.values()) <= set(
            PHASE8_DRAFTING_SKILL_BY_NODE.values()
        )


# ---------------------------------------------------------------------------
# C. The load-time helpers reject drift
# ---------------------------------------------------------------------------


class TestLoadTimeHelpersRejectDrift:
    def test_agrees_with_source_passes_on_a_faithful_copy(self) -> None:
        assert_agrees_with_source(
            "copy", dict(PHASE8_DRAFTING_SKILL_BY_NODE)
        )

    def test_agrees_with_source_rejects_a_changed_value(self) -> None:
        drifted = dict(PHASE8_DRAFTING_SKILL_BY_NODE)
        drifted["n08a_excellence_drafting"] = "wrong-skill"
        with pytest.raises(SkipBindingError, match="disagrees"):
            assert_agrees_with_source("drifted", drifted)

    def test_agrees_with_source_rejects_a_missing_node(self) -> None:
        partial = dict(PHASE8_DRAFTING_SKILL_BY_NODE)
        partial.pop("n08c_implementation_drafting")
        with pytest.raises(SkipBindingError, match="node keys"):
            assert_agrees_with_source("partial", partial)

    def test_nodes_match_source_passes_on_the_same_keys(self) -> None:
        assert_nodes_match_source(
            "keys", list(PHASE8_DRAFTING_SKILL_BY_NODE)
        )

    def test_nodes_match_source_rejects_an_extra_node(self) -> None:
        with pytest.raises(SkipBindingError, match="node keys"):
            assert_nodes_match_source(
                "extra", list(PHASE8_DRAFTING_SKILL_BY_NODE) + ["n08z_bogus"]
            )
