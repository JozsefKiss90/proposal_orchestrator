"""
Single authoritative source for the Phase-8 drafting-skill skip binding.

When a Phase-8 section node (n08a/n08b/n08c) reuses a prior-run artifact or
imports a manual preseed, the scheduler suppresses the node's *drafting* skill
so the monolithic drafter does not overwrite the authoritative section that is
already on disk.  Which skill that is had been named independently in four
places — ``PRESEED_NODE_CONFIG[node]["skipped_skill"]``,
``REUSE_SKIP_SKILLS[node]``, the eligibility table ``REUSE_ELIGIBLE_NODES``, and
``_ASSEMBLER_SUPERSEDES_DRAFTING_SKILL`` in the agent runtime — and *none* was
checked against the manifest's resolved ``skill_ids``.  That produced two
defects (PRE-2 / PRE-3, ``plans/tickets_phase8_review.md`` ticket 3):

  * a skip id that matches nothing was a **silent no-op** — a skill rename let
    the drafter overwrite a preseeded/reused section while the audit record
    falsely claimed the drafting skill was skipped; and
  * eligibility and the skip binding were consulted at different times, so a
    node eligible-but-unbound recorded "drafting skipped" and still recomposed
    over stale drafts.

This module is the one place that answers "which drafting skill does this
Phase-8 node run?".  Every other table derives from it or is asserted equal to
it at import (:func:`assert_agrees_with_source`), so the tables can never drift
apart; and :func:`validate_skip_binding` resolves the chosen skip id against the
node's *manifest* ``skill_ids`` at dispatch, failing closed on any drift between
this map and the manifest rather than silently no-op'ing.

Constitutional authority:
    Subordinate to CLAUDE.md.  A pure data + validation leaf module: it names no
    project facts, evaluates no gates, invokes no agents, and imports nothing
    from ``runner``.  The manifest node binding (§16.5) remains the authority
    for what skills a node runs; this map only records which of them is the
    drafting skill that reuse/preseed suppress.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

# ---------------------------------------------------------------------------
# The single authoritative binding
# ---------------------------------------------------------------------------

#: The one authoritative ``node_id -> drafting-skill-id`` map for Phase-8
#: section nodes.  Changing which skill a node drafts with is a one-line edit
#: here; every derived table is rebuilt or re-asserted from it at import.
PHASE8_DRAFTING_SKILL_BY_NODE: dict[str, str] = {
    "n08a_excellence_drafting": "excellence-section-drafting",
    "n08b_impact_drafting": "impact-section-drafting",
    "n08c_implementation_drafting": "implementation-section-drafting",
}


class SkipBindingError(RuntimeError):
    """Raised at import when a skip-binding table drifts from the single source.

    A load-time failure by design: an inconsistent table is a programming
    error that must surface before any run, not a per-node runtime block.
    """


# ---------------------------------------------------------------------------
# Lookups
# ---------------------------------------------------------------------------


def drafting_skill_for(node_id: str) -> str | None:
    """Return the authoritative drafting skill id for *node_id*, or ``None``.

    ``None`` means the node is not a Phase-8 section-drafting node with a
    suppressible drafting skill (n08d/n08e/n08f and every non-Phase-8 node).
    """
    return PHASE8_DRAFTING_SKILL_BY_NODE.get(node_id)


# ---------------------------------------------------------------------------
# Runtime fail-closed validation (PRE-2 / PRE-3)
# ---------------------------------------------------------------------------


def validate_skip_binding(
    node_id: str,
    skip_skill_ids: Iterable[str],
    resolved_skill_ids: Iterable[str],
) -> str | None:
    """Return a failure reason iff the skip binding is not in force, else ``None``.

    Fail-closed contract used by the scheduler before it suppresses a Phase-8
    drafting skill:

      * an **empty** *skip_skill_ids* for a node about to record a skip is a
        failure (PRE-3): the suppression the audit would describe is not in
        force, so the decision must not be written; and
      * a skip id that is **not** among the node's manifest-resolved
        *resolved_skill_ids* is a failure (PRE-2): a rename must hard-block the
        node, never silently no-op and let the drafter overwrite the
        authoritative section.

    Both are returned as human-readable reason strings so the caller can block
    the node with a precise message.
    """
    resolved = set(resolved_skill_ids)
    skips = list(skip_skill_ids)
    if not skips:
        return (
            f"skip binding empty for {node_id!r}: a Phase-8 supersession was "
            "decided but no drafting skill is bound to suppress — the "
            "eligibility table and the skip binding disagree"
        )
    unmatched = sorted(s for s in skips if s not in resolved)
    if unmatched:
        return (
            f"skip id(s) {unmatched} for {node_id!r} match no manifest-resolved "
            f"skill in {sorted(resolved)}: refusing to record a skip that is "
            "not in force — a drafting-skill rename would otherwise let the "
            "drafter overwrite the authoritative section"
        )
    return None


# ---------------------------------------------------------------------------
# Load-time consistency (single source of truth)
# ---------------------------------------------------------------------------


def assert_agrees_with_source(
    table_name: str,
    node_to_skill: Mapping[str, str],
) -> None:
    """Assert *node_to_skill* equals :data:`PHASE8_DRAFTING_SKILL_BY_NODE`.

    Both the node-key set and the per-node skill value must match exactly.
    Called at import by every module that keeps a derived drafting-skill table,
    so an accidental hand-edit that diverges from the single source fails the
    import (:class:`SkipBindingError`) rather than silently drifting.
    """
    src = PHASE8_DRAFTING_SKILL_BY_NODE
    got_nodes = set(node_to_skill)
    want_nodes = set(src)
    if got_nodes != want_nodes:
        raise SkipBindingError(
            f"{table_name} node keys {sorted(got_nodes)} do not match the "
            f"authoritative Phase-8 skip binding {sorted(want_nodes)}"
        )
    drifted = {
        node: (node_to_skill[node], src[node])
        for node in src
        if node_to_skill[node] != src[node]
    }
    if drifted:
        raise SkipBindingError(
            f"{table_name} disagrees with the authoritative Phase-8 skip "
            f"binding on {drifted!r} (got, expected)"
        )


def assert_nodes_match_source(table_name: str, nodes: Iterable[str]) -> None:
    """Assert *nodes* is exactly the authoritative node-key set.

    Used for tables that carry eligibility (not a skill value) — e.g.
    ``REUSE_ELIGIBLE_NODES`` — so eligibility and the skip binding are proven to
    cover the same nodes and cannot silently diverge (PRE-3).
    """
    got = set(nodes)
    want = set(PHASE8_DRAFTING_SKILL_BY_NODE)
    if got != want:
        raise SkipBindingError(
            f"{table_name} node keys {sorted(got)} do not match the "
            f"authoritative Phase-8 skip binding {sorted(want)}"
        )
