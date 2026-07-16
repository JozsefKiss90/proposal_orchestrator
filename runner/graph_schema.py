"""
Generic graph schema — the additive superset of the methodology-graph contract.

This module is the project-agnostic *schema* half of the milestone-2 graph
substrate (tickets_milestone2.md ticket 1).  It carries **no** project-specific
knowledge: no folder names, no call, no partner nouns.  It defines only

  * the controlled ``node_type`` vocabulary (the 15 methodology types that the
    existing 87-node reference methodology vault already uses, **plus** the 8 new
    Tier-3/4/5 binding types milestone 2 introduces),
  * the ``evidence_strength`` vocabulary and the **Appendix-B pure lookup** from
    ``evidence_strength`` to a constitutional validation status
    (CLAUDE.md §12.2), carrying provenance end-to-end,
  * the required-core / additive-optional front-matter field split, and
  * fail-closed front-matter validation that names the offending node.

Design constraints (ticket 1):

* **Additive superset.**  Every one of the existing 87 methodology nodes must
  still validate unchanged, and **no new required field** is introduced.  The
  new ``node_type`` values and the four new front-matter keys
  (``tier``/``phase``/``artifact_path``/``sub_section_id``) are all
  *additive-optional* — a node that omits them is still valid.
* **Generic required core.**  Only the load-bearing identity/provenance fields
  ``id``/``title``/``node_type``/``evidence_strength`` are required.  The
  remaining methodology fields (``confidence``, ``maturity``, ``domain`` …) are
  optional here so the generic layer does not bake instance-#1 assumptions in;
  an instance's own governance may require more, but the substrate does not.
* **Pure, no inference.**  The evidence→status mapping is a dict lookup, never a
  judgement.  ``unconfirmed`` maps to ``Unresolved`` (the un-declared default);
  the β assumption-applier may later flip an *operator-declared* ``Unresolved``
  to ``Assumed`` (D11) — that is a separate, declared, deterministic step and is
  **not** this module's inference.

Constitutional authority:
    Subordinate to CLAUDE.md.  Appendix-B mapping is
    ``PHASE8_FULLSCALE_AND_OBSIDIAN_GRILL_BRIEF.md`` Appendix B; the status
    vocabulary is CLAUDE.md §12.2.  This module invents no facts.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# node_type controlled vocabulary (the additive superset)
# ---------------------------------------------------------------------------

#: The 15 methodology-graph node types the reference instance (instance #1)
#: already uses.  These are generic methodology-graph categories — abstract type
#: names, not project nouns — so they belong in the generic layer.
METHODOLOGY_NODE_TYPES: frozenset[str] = frozenset(
    {
        "meta",
        "governance",
        "dashboard",
        "source",
        "architecture",
        "state_of_the_art",
        "methodology_route",
        "methodology_problem",
        "decision_method",
        "infrastructure_layer",
        "risk",
        "swot",
        "partner",
        "concept",
        "research_questions",
    }
)

#: The 8 new Tier-3/4/5-binding node types milestone 2 introduces.  These bind a
#: node to a canonical ``docs/**`` artifact via ``graph.config.yaml`` (see
#: :mod:`runner.graph_config`).  ``risk`` is deliberately **not** here — the
#: existing methodology ``risk`` type already binds the Tier 3 risk register.
BINDING_NODE_TYPES: frozenset[str] = frozenset(
    {
        "proposal_section",  # one per Part B sub-section (the headline authoring move)
        "objective",  # Tier 3 architecture_inputs/objectives.json
        "outcome",  # Tier 3 architecture_inputs/outcomes.json
        "impact",  # Tier 3 architecture_inputs/impacts.json
        "work_package",  # Tier 3 architecture_inputs/workpackage_seed.json
        "timeline",  # Tier 3/4 Gantt + milestones (Phase 4)
        "budget",  # Tier 3/7 budget lines
        "phase_gate_state",  # Tier 4 phase/gate mirror (docs_to_graph projection)
    }
)

#: The full controlled vocabulary the reader validates ``node_type`` against.
#: A node whose ``node_type`` is outside this set fails closed (naming the node).
NODE_TYPES: frozenset[str] = METHODOLOGY_NODE_TYPES | BINDING_NODE_TYPES


# ---------------------------------------------------------------------------
# evidence_strength vocabulary + Appendix-B status mapping (pure lookup)
# ---------------------------------------------------------------------------

#: The four ``evidence_strength`` values every node front-matter must use
#: (Methodology Graph Schema §3).
EVIDENCE_STRENGTHS: frozenset[str] = frozenset(
    {"source_grounded", "synthesis", "inference", "unconfirmed"}
)

#: The constitutional validation-status vocabulary (CLAUDE.md §12.2).
VALIDATION_STATUSES: frozenset[str] = frozenset(
    {"Confirmed", "Inferred", "Assumed", "Unresolved"}
)

#: **Appendix-B pure lookup.**  ``evidence_strength`` → validation status, as a
#: dict — no inference, no judgement.  ``source_grounded`` is the only value that
#: yields ``Confirmed``; ``synthesis`` and ``inference`` both yield ``Inferred``;
#: ``unconfirmed`` yields ``Unresolved`` (the un-declared default — "not
#: finalizable").  A ``synthesis``/``inference``/``unconfirmed`` node therefore
#: can **never** land as a Confirmed fact, which is exactly what the drafting
#: gates rely on.
EVIDENCE_TO_STATUS: dict[str, str] = {
    "source_grounded": "Confirmed",
    "synthesis": "Inferred",
    "inference": "Inferred",
    "unconfirmed": "Unresolved",
}


# ---------------------------------------------------------------------------
# Front-matter field contract
# ---------------------------------------------------------------------------

#: The required *core* every node must carry — the load-bearing identity and
#: provenance fields.  This is the whole required set: the superset adds **no**
#: new required field (ticket 1).
REQUIRED_CORE_FIELDS: tuple[str, ...] = (
    "id",
    "title",
    "node_type",
    "evidence_strength",
)

#: The four additive-optional front-matter keys milestone 2 introduces.  A node
#: that omits any of them is still valid; when present they bind the node to a
#: tier/phase/artifact/sub-section for the compiler (ticket 3/6) and projector
#: (ticket 4).
OPTIONAL_BINDING_FIELDS: tuple[str, ...] = (
    "tier",
    "phase",
    "artifact_path",
    "sub_section_id",
)

#: Valid ``tier`` values (for the front-matter ``tier`` field and for
#: ``graph.config.yaml`` bindings).  Mirrors the CLAUDE.md §5 tier model.
TIERS: frozenset[str] = frozenset(
    {"tier1", "tier2a", "tier2b", "tier3", "tier4", "tier5"}
)


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------


class GraphSchemaError(Exception):
    """Raised when a node's front-matter violates the generic graph schema.

    Every message names the offending node (and the specific field/value) so a
    schema failure is actionable, never a silent skip or a bare crash.
    """


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def map_evidence_to_status(evidence_strength: str) -> str:
    """Map an ``evidence_strength`` to a validation status via the Appendix-B lookup.

    Pure and total over :data:`EVIDENCE_STRENGTHS`.  Performs no inference: it is
    a dict lookup.  Raises :class:`GraphSchemaError` on an unknown value rather
    than guessing a status.

    Parameters
    ----------
    evidence_strength:
        One of :data:`EVIDENCE_STRENGTHS`.

    Returns
    -------
    str
        One of :data:`VALIDATION_STATUSES`.
    """
    try:
        return EVIDENCE_TO_STATUS[evidence_strength]
    except (KeyError, TypeError):
        raise GraphSchemaError(
            f"Unknown evidence_strength {evidence_strength!r}; "
            f"expected one of {sorted(EVIDENCE_STRENGTHS)}"
        ) from None


def _is_blank(value: Any) -> bool:
    """True if *value* is ``None`` or a blank/whitespace-only string."""
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    return False


def validate_front_matter(front_matter: Any, node_ref: str) -> None:
    """Validate a node's parsed front-matter against the generic superset schema.

    Fails closed (:class:`GraphSchemaError`, naming *node_ref* and the specific
    problem) when:

    * the front-matter is not a mapping,
    * a :data:`REQUIRED_CORE_FIELDS` field is absent or blank,
    * ``node_type`` is outside :data:`NODE_TYPES`,
    * ``evidence_strength`` is outside :data:`EVIDENCE_STRENGTHS`,
    * an optional binding field is present but malformed (wrong type, or ``tier``
      outside :data:`TIERS`).

    A node that simply omits the additive-optional fields is valid.

    Parameters
    ----------
    front_matter:
        The parsed YAML front-matter (expected to be a ``dict``).
    node_ref:
        A human-readable node reference (path or basename) used in messages.
    """
    if not isinstance(front_matter, dict):
        raise GraphSchemaError(
            f"{node_ref}: front-matter is not a mapping "
            f"(got {type(front_matter).__name__})"
        )

    # ── required core ──────────────────────────────────────────────────
    for field_name in REQUIRED_CORE_FIELDS:
        if field_name not in front_matter or _is_blank(front_matter[field_name]):
            raise GraphSchemaError(
                f"{node_ref}: missing or blank required field {field_name!r}"
            )

    # ── controlled vocabularies ────────────────────────────────────────
    node_type = front_matter["node_type"]
    if node_type not in NODE_TYPES:
        raise GraphSchemaError(
            f"{node_ref}: unknown node_type {node_type!r}; "
            f"expected one of {sorted(NODE_TYPES)}"
        )

    evidence_strength = front_matter["evidence_strength"]
    if evidence_strength not in EVIDENCE_STRENGTHS:
        raise GraphSchemaError(
            f"{node_ref}: invalid evidence_strength {evidence_strength!r}; "
            f"expected one of {sorted(EVIDENCE_STRENGTHS)}"
        )

    # ── additive-optional binding fields (validated only when present) ──
    if "tier" in front_matter and front_matter["tier"] is not None:
        tier = front_matter["tier"]
        if tier not in TIERS:
            raise GraphSchemaError(
                f"{node_ref}: invalid tier {tier!r}; "
                f"expected one of {sorted(TIERS)}"
            )

    if "phase" in front_matter and front_matter["phase"] is not None:
        phase = front_matter["phase"]
        # ``phase`` may be an int (1-8) or a string label ("phase4"); reject
        # only clearly-malformed types (bool included — a YAML ``yes``/``no``).
        if isinstance(phase, bool) or not isinstance(phase, (int, str)):
            raise GraphSchemaError(
                f"{node_ref}: invalid phase {phase!r}; expected an int or string"
            )

    for str_field in ("artifact_path", "sub_section_id"):
        if str_field in front_matter and front_matter[str_field] is not None:
            value = front_matter[str_field]
            if not isinstance(value, str) or not value.strip():
                raise GraphSchemaError(
                    f"{node_ref}: {str_field!r} must be a non-empty string "
                    f"when present (got {value!r})"
                )
