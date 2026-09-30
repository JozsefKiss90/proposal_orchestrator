"""
Dev-graph schema — the closed node-type set and the closed relationship set.

Both sets are data, not code paths. Adding a node type or a predicate is a
schema change and needs a test; nothing in the builder infers a type or a
relationship that is not declared here.

A relationship declares its permitted endpoint type pairs, its direction, its
cardinality, and its operational effect. The effect separates a *domain link*
(``assigned_to`` says who does the work) from an *execution dependency*
(``consumes`` says what must exist first). A traversal that treats the two
alike is a bug, and the flag makes that checkable.

Constitutional authority:
    Subordinate to CLAUDE.md. This module carries no project noun, reads no
    file, and evaluates no gate. It invents no facts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

# ---------------------------------------------------------------------------
# Node types
# ---------------------------------------------------------------------------

#: The closed node-type set for milestone 1: the types the T03 scenario needs.
NODE_TYPES: frozenset[str] = frozenset(
    {
        # Project facts (Tier 3)
        "participant",
        "objective",
        "work_package",
        "task",
        "deliverable",
        "milestone",
        # Evidence and wording
        "claim",
        "commitment",
        "passage",
        "source",
        "source_span",
        # Execution records (Tier 4 / harness)
        "artifact_version",
        "execution",
        "assessment",
        "finding",
        # Controlled change
        "change_request",
        "revision_contract",
    }
)

# ---------------------------------------------------------------------------
# Relationships
# ---------------------------------------------------------------------------

DOMAIN_LINK = "domain_link"
EXECUTION_DEPENDENCY = "execution_dependency"

#: Cardinalities that allow at most one target per (source, predicate).
_SINGLE_TARGET: frozenset[str] = frozenset({"one_to_one", "many_to_one"})


@dataclass(frozen=True)
class RelationshipSpec:
    """One closed-set predicate with its declared shape."""

    predicate: str
    endpoints: tuple[tuple[str, str], ...]
    """Permitted ``(source_type, target_type)`` pairs."""
    cardinality: str
    """``one_to_one``, ``many_to_one`` or ``many_to_many`` (source to target)."""
    effect: str
    """:data:`DOMAIN_LINK` or :data:`EXECUTION_DEPENDENCY`."""
    direction: str = "source_to_target"
    """Every predicate reads source to target; declared, never inferred."""

    def permits(self, source_type: str, target_type: str) -> bool:
        return (source_type, target_type) in self.endpoints

    @property
    def single_target(self) -> bool:
        return self.cardinality in _SINGLE_TARGET


#: The closed relationship set. ``related_to`` is deliberately absent: an
#: untyped link has no defined traversal meaning. Endpoint pairs are the ones
#: this milestone's tickets name; a later ticket that needs another pair adds
#: it here with a test and its own decision log entry.
RELATIONSHIPS: Mapping[str, RelationshipSpec] = {
    s.predicate: s
    for s in (
        RelationshipSpec(
            "assigned_to",
            (("task", "participant"), ("work_package", "participant")),
            "many_to_one",
            DOMAIN_LINK,
        ),
        RelationshipSpec(
            "contributes_to",
            (
                ("task", "work_package"),
                ("work_package", "objective"),
                ("participant", "task"),
            ),
            "many_to_many",
            DOMAIN_LINK,
        ),
        RelationshipSpec(
            "produces",
            (("work_package", "deliverable"), ("task", "deliverable")),
            "many_to_many",
            DOMAIN_LINK,
        ),
        RelationshipSpec(
            "supported_by",
            (("claim", "source_span"), ("claim", "source")),
            "many_to_many",
            DOMAIN_LINK,
        ),
        RelationshipSpec(
            "expressed_in",
            (
                ("claim", "passage"),
                ("commitment", "passage"),
                ("passage", "artifact_version"),
            ),
            "many_to_many",
            DOMAIN_LINK,
        ),
        RelationshipSpec(
            "consumes",
            (("task", "task"), ("execution", "artifact_version")),
            "many_to_many",
            EXECUTION_DEPENDENCY,
        ),
        RelationshipSpec(
            "addresses",
            (
                ("passage", "objective"),
                ("passage", "work_package"),
                ("passage", "task"),
                ("finding", "passage"),
                ("change_request", "task"),
            ),
            "many_to_many",
            DOMAIN_LINK,
        ),
        RelationshipSpec(
            "supersedes",
            (("artifact_version", "artifact_version"),),
            "one_to_one",
            DOMAIN_LINK,
        ),
        RelationshipSpec(
            "constrained_by",
            (("work_package", "source"), ("change_request", "revision_contract")),
            "many_to_many",
            DOMAIN_LINK,
        ),
        RelationshipSpec(
            "validated_by",
            (
                ("deliverable", "milestone"),
                ("artifact_version", "assessment"),
                ("claim", "assessment"),
            ),
            "many_to_many",
            EXECUTION_DEPENDENCY,
        ),
    )
}


# ---------------------------------------------------------------------------
# Document snapshots and claim evidence fields
# ---------------------------------------------------------------------------

#: Lifecycle states of a document snapshot (an ``artifact_version`` node of
#: kind ``document_snapshot``). Closed; a state outside it is rejected at
#: import.
DOCUMENT_STATES: frozenset[str] = frozenset(
    {"imported", "draft", "submitted", "superseded"}
)

#: The states whose wording is a *current* commitment. A submitted or
#: superseded snapshot is history: it is indexed, and it is never returned as
#: a current commitment.
CURRENT_DOCUMENT_STATES: frozenset[str] = frozenset({"imported", "draft"})

#: The state a snapshot carries once a later version has replaced it.
SUPERSEDED_STATE: str = "superseded"

#: A claim's declared status: the CLAUDE.md §12.2 vocabulary. Fed by the
#: evidence-strength lookup (``runner.graph_schema.EVIDENCE_TO_STATUS``) and,
#: for ``Assumed``, by an explicit declaration over an ``Unresolved`` lookup.
DECLARED_STATUSES: frozenset[str] = frozenset(
    {"Confirmed", "Inferred", "Assumed", "Unresolved"}
)

#: A claim's current approval. Independent of declared status and of the
#: verified span: a label never stands in for proof, and neither stands in
#: for a decision.
APPROVALS: frozenset[str] = frozenset({"approved", "pending", "not_applicable"})

#: Where each node type declares its CLAUDE.md §12.2 status: node type -> the
#: field name in that record's own content. Declared data, never sniffed from
#: a value: a Tier 3 seed writes ``validation_status``, the consortium
#: registry writes ``participation_status``, the source index writes
#: ``status``, and a document claim writes ``declared_status``. A type absent
#: from this map declares no status of its own, and a node of that type is
#: neither confirmed nor unresolved — it is simply silent.
DECLARED_STATUS_FIELDS: Mapping[str, str] = {
    "participant": "participation_status",
    "objective": "validation_status",
    "work_package": "validation_status",
    "task": "validation_status",
    "deliverable": "validation_status",
    "milestone": "validation_status",
    "source": "status",
    "claim": "declared_status",
}


def declared_status(node: Mapping[str, Any]) -> str | None:
    """The node's own declared §12.2 status, or ``None``.

    Pure lookup through :data:`DECLARED_STATUS_FIELDS`. Returns ``None`` when
    the type declares no status field, when the field is absent, or when its
    value is outside :data:`DECLARED_STATUSES` — a Phase-8 section's
    ``validation_status`` object, for instance, is not a Tier 3 seed's status
    string, and this returns ``None`` for it rather than guessing.
    """
    field = DECLARED_STATUS_FIELDS.get(node["type"])
    if field is None:
        return None
    value = node.get("content", {}).get(field)
    return value if isinstance(value, str) and value in DECLARED_STATUSES else None


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

#: The closed set of rejection kinds a build can fail with.
ERROR_KINDS: frozenset[str] = frozenset(
    {
        "duplicate_id",
        "dangling_edge",
        "endpoint_type",
        "unknown_predicate",
        "cardinality",
        "malformed_record",
        # Package requests (runner.dev_graph.packages)
        "malformed_request",
        "unknown_view",
        "stale_snapshot",
        "stale_policy",
        "policy_forbidden",
        # Change records and the impact planner (runner.dev_graph.changes,
        # runner.dev_graph.impact)
        "immutable_record",
        "missing_snapshot",
        "malformed_snapshot",
    }
)


class DevGraphError(Exception):
    """A fail-closed rejection naming the first invalid node, edge or record.

    ``kind`` is one of :data:`ERROR_KINDS`; ``offender`` is the node id, the
    edge label ``<source> -<predicate>-> <target>``, or the repo-relative
    record path, so the operator can go straight to it.
    """

    def __init__(self, kind: str, offender: str, message: str) -> None:
        if kind not in ERROR_KINDS:
            raise ValueError(f"unknown DevGraphError kind: {kind!r}")
        super().__init__(f"{kind}: {message} [offender: {offender}]")
        self.kind = kind
        self.offender = offender


# ---------------------------------------------------------------------------
# Validation (pure)
# ---------------------------------------------------------------------------


def edge_label(source_id: str, predicate: str, target_id: str) -> str:
    return f"{source_id} -{predicate}-> {target_id}"


def validate_graph(
    nodes: list[dict[str, Any]], edges: list[dict[str, Any]]
) -> None:
    """Fail closed on the first invalid node or edge.

    Checks, in order: duplicate ids, unknown node types, unknown predicates,
    dangling endpoints, endpoint types, then single-target cardinality.
    Pure: reads its arguments and raises :class:`DevGraphError`.
    """
    seen: dict[str, str] = {}
    for n in nodes:
        nid = n["id"]
        if nid in seen:
            raise DevGraphError(
                "duplicate_id",
                nid,
                f"node id declared more than once (types {seen[nid]!r} and {n['type']!r})",
            )
        if n["type"] not in NODE_TYPES:
            raise DevGraphError(
                "malformed_record", nid, f"unknown node type {n['type']!r}"
            )
        seen[nid] = n["type"]

    targets_seen: dict[tuple[str, str], str] = {}
    for e in edges:
        src, pred, dst = e["source"]["id"], e["predicate"], e["target"]["id"]
        label = edge_label(src, pred, dst)
        spec = RELATIONSHIPS.get(pred)
        if spec is None:
            raise DevGraphError(
                "unknown_predicate",
                label,
                f"predicate {pred!r} is not in the closed relationship set",
            )
        for end, eid in (("source", src), ("target", dst)):
            if eid not in seen:
                raise DevGraphError(
                    "dangling_edge",
                    label,
                    f"{end} node {eid!r} does not exist ({pred})",
                )
        if not spec.permits(seen[src], seen[dst]):
            raise DevGraphError(
                "endpoint_type",
                label,
                f"{pred} does not permit {seen[src]} -> {seen[dst]}; "
                f"permitted: {sorted(spec.endpoints)}",
            )
        if spec.single_target:
            prior = targets_seen.setdefault((src, pred), dst)
            if prior != dst:
                raise DevGraphError(
                    "cardinality",
                    label,
                    f"{pred} is {spec.cardinality}: {src!r} already targets {prior!r}",
                )
