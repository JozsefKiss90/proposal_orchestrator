"""
Dev graph — a rebuildable operational index over authoritative records.

Public API (the one entry point plus its vocabulary and writer):

* :func:`build_snapshot` — repository root -> immutable :class:`Snapshot`, or
  :class:`DevGraphError` naming the first invalid node, edge or record.
* :data:`NODE_TYPES`, :data:`RELATIONSHIPS` — the closed vocabularies, and
  :func:`validate_graph`, the pure fail-closed check the builder applies.
* :func:`write_snapshot`, :data:`SNAPSHOT_REL` — the deterministic writer.
* :func:`import_document`, :data:`DOCUMENTS_REL` — import a candidate as an
  immutable document snapshot record; :func:`current_commitments` — the
  commitments of current (not submitted, not superseded) snapshots.

The graph owns nothing. Tier 3 JSON owns project facts; the graph indexes
them with stable ids, content-hash versions and typed edges. Nothing here
reads the scheduler, evaluates a gate, or invokes Claude.
"""

from __future__ import annotations

from runner.dev_graph.builder import (
    SCHEMA_ID,
    Snapshot,
    build_snapshot,
    current_commitments,
)
from runner.dev_graph.documents import (
    DOCUMENT_SCHEMA_ID,
    DOCUMENTS_REL,
    DocumentRef,
    import_document,
)
from runner.dev_graph.identity import canonical_json, content_hash
from runner.dev_graph.schema import (
    APPROVALS,
    CURRENT_DOCUMENT_STATES,
    DECLARED_STATUSES,
    DOCUMENT_STATES,
    DOMAIN_LINK,
    EXECUTION_DEPENDENCY,
    NODE_TYPES,
    RELATIONSHIPS,
    DevGraphError,
    RelationshipSpec,
    edge_label,
    validate_graph,
)
from runner.dev_graph.writer import SNAPSHOT_REL, write_snapshot

__all__ = [
    "APPROVALS",
    "CURRENT_DOCUMENT_STATES",
    "DECLARED_STATUSES",
    "DOCUMENTS_REL",
    "DOCUMENT_SCHEMA_ID",
    "DOCUMENT_STATES",
    "DOMAIN_LINK",
    "EXECUTION_DEPENDENCY",
    "NODE_TYPES",
    "RELATIONSHIPS",
    "SCHEMA_ID",
    "SNAPSHOT_REL",
    "DevGraphError",
    "DocumentRef",
    "RelationshipSpec",
    "Snapshot",
    "build_snapshot",
    "canonical_json",
    "content_hash",
    "current_commitments",
    "edge_label",
    "import_document",
    "validate_graph",
    "write_snapshot",
]
