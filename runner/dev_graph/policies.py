"""
Dev-graph view policies — configuration data, one policy per view.

A view policy says what a consumer of an evidence package may see. It names
the permitted node types, the permitted relationship traversals, the maximum
expansion depth, the forbidden node types and the forbidden tags. The package
builder applies the policy *before* graph expansion: a node the policy does
not permit is never a step in a traversal, so nothing behind it can enter
through a side path.

The six views are the ones the milestone names. The blind pre-evaluation
policy forbids assessment, finding and change request nodes and any node
tagged as historical feedback (a node's tags are the ``tags`` list in its
content). Tags for historical scores, target scores and repair plans are
forbidden with it, so the leakage guard in the harness is a second check,
not the only one. It also hides superseded document versions
(``hide_superseded_versions``): every node derived from a snapshot that a
later version ``supersedes``, or whose state is ``superseded``, is refused
before expansion. The policy only says whether a view hides them. The
package builder decides which snapshots are superseded, because that is
a fact of the whole graph and not a tag on one node (decision record
``dev-graph-blind-view-superseded-versions``).

``POLICY_VERSION`` is the content hash of every policy in canonical form. A
package built under one version is refused under another, so a policy edit
never silently reinterprets an existing package.

Constitutional authority:
    Subordinate to CLAUDE.md. Pure data and pure lookups; reads no file,
    evaluates no gate, invents no facts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from runner.dev_graph.identity import content_hash
from runner.dev_graph.schema import NODE_TYPES, RELATIONSHIPS

#: The closed set of views.
VIEWS: frozenset[str] = frozenset(
    {
        "engineering",
        "controlled_revision",
        "integrity_audit",
        "blind_pre_evaluation",
        "historical_feedback_analysis",
        "change_impact_planning",
    }
)

#: Tags that mark a node as feedback on a prior submission. A blind
#: assessment must not see any of them.
HISTORICAL_FEEDBACK_TAGS: frozenset[str] = frozenset(
    {"historical_feedback", "historical_score", "target_score", "repair_plan"}
)

_PROJECT_TYPES: frozenset[str] = frozenset(
    {"participant", "objective", "work_package", "task", "deliverable", "milestone"}
)
_EVIDENCE_TYPES: frozenset[str] = frozenset(
    {"claim", "commitment", "passage", "source", "source_span", "artifact_version"}
)
_FEEDBACK_TYPES: frozenset[str] = frozenset({"assessment", "finding"})
_CHANGE_TYPES: frozenset[str] = frozenset({"change_request", "revision_contract"})
_ALL_PREDICATES: frozenset[str] = frozenset(RELATIONSHIPS)


@dataclass(frozen=True)
class ViewPolicy:
    """What one view may see: closed-vocabulary sets, a depth and one switch."""

    view: str
    permitted_types: frozenset[str]
    permitted_traversals: frozenset[str]
    max_depth: int
    forbidden_types: frozenset[str] = frozenset()
    forbidden_tags: frozenset[str] = frozenset()
    #: Refuse every node derived from a superseded document version
    #: (:func:`runner.dev_graph.builder.superseded_versions`).
    hide_superseded_versions: bool = False

    def __post_init__(self) -> None:
        if self.view not in VIEWS:
            raise ValueError(f"unknown view {self.view!r}")
        if not self.permitted_types <= NODE_TYPES:
            raise ValueError(f"{self.view}: permitted_types outside NODE_TYPES")
        if not self.forbidden_types <= NODE_TYPES:
            raise ValueError(f"{self.view}: forbidden_types outside NODE_TYPES")
        if self.forbidden_types & self.permitted_types:
            raise ValueError(f"{self.view}: a type is both permitted and forbidden")
        if not self.permitted_traversals <= _ALL_PREDICATES:
            raise ValueError(f"{self.view}: permitted_traversals outside RELATIONSHIPS")
        if self.max_depth < 1:
            raise ValueError(f"{self.view}: max_depth must be at least 1")

    def to_dict(self) -> dict[str, Any]:
        return {
            "view": self.view,
            "permitted_types": sorted(self.permitted_types),
            "permitted_traversals": sorted(self.permitted_traversals),
            "max_depth": self.max_depth,
            "forbidden_types": sorted(self.forbidden_types),
            "forbidden_tags": sorted(self.forbidden_tags),
            "hide_superseded_versions": self.hide_superseded_versions,
        }

    def node_tags(self, node: Mapping[str, Any]) -> frozenset[str]:
        tags = node.get("content", {}).get("tags", [])
        return frozenset(t for t in tags if isinstance(t, str)) if isinstance(tags, list) else frozenset()

    def refusal(self, node: Mapping[str, Any]) -> str | None:
        """Why this node may not enter a package under this view, or ``None``.

        Pure lookup. The three reasons are reported separately so an operator
        can tell a forbidden type from a tag from a type the view leaves out.
        """
        ntype = node["type"]
        if ntype in self.forbidden_types:
            return "type_forbidden"
        tags = self.node_tags(node) & self.forbidden_tags
        if tags:
            return "tag_forbidden:" + ",".join(sorted(tags))
        if ntype not in self.permitted_types:
            return "type_not_permitted"
        return None


#: The policies, keyed by view. Data: an edit here changes POLICY_VERSION.
VIEW_POLICIES: Mapping[str, ViewPolicy] = {
    p.view: p
    for p in (
        ViewPolicy(
            "engineering",
            permitted_types=NODE_TYPES,
            permitted_traversals=_ALL_PREDICATES,
            max_depth=3,
        ),
        ViewPolicy(
            "controlled_revision",
            permitted_types=_PROJECT_TYPES | _EVIDENCE_TYPES | _CHANGE_TYPES,
            permitted_traversals=_ALL_PREDICATES - {"validated_by"},
            max_depth=2,
            forbidden_types=_FEEDBACK_TYPES,
        ),
        ViewPolicy(
            "integrity_audit",
            permitted_types=NODE_TYPES,
            permitted_traversals=_ALL_PREDICATES,
            max_depth=3,
        ),
        ViewPolicy(
            "blind_pre_evaluation",
            permitted_types=_PROJECT_TYPES | _EVIDENCE_TYPES,
            permitted_traversals=_ALL_PREDICATES - {"validated_by", "supersedes"},
            max_depth=3,
            forbidden_types=_FEEDBACK_TYPES | {"change_request"},
            forbidden_tags=HISTORICAL_FEEDBACK_TAGS,
            hide_superseded_versions=True,
        ),
        ViewPolicy(
            "historical_feedback_analysis",
            permitted_types=_PROJECT_TYPES | _EVIDENCE_TYPES | _FEEDBACK_TYPES,
            permitted_traversals=_ALL_PREDICATES,
            max_depth=2,
            forbidden_types=_CHANGE_TYPES,
        ),
        ViewPolicy(
            "change_impact_planning",
            permitted_types=NODE_TYPES,
            permitted_traversals=_ALL_PREDICATES,
            max_depth=4,
        ),
    )
}

#: Content hash of every policy in canonical form.
POLICY_VERSION: str = content_hash({v: VIEW_POLICIES[v].to_dict() for v in sorted(VIEW_POLICIES)})
