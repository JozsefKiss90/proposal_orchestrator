"""
Dev graph — a rebuildable operational index over authoritative records.

Public API (the one entry point plus its vocabulary and writers):

* :func:`build_snapshot` — repository root -> immutable :class:`Snapshot`, or
  :class:`DevGraphError` naming the first invalid node, edge or record.
* :data:`NODE_TYPES`, :data:`RELATIONSHIPS` — the closed vocabularies, and
  :func:`validate_graph`, the pure fail-closed check the builder applies.
* :func:`write_snapshot`, :data:`SNAPSHOT_REL` — the deterministic writer.
* :func:`import_document`, :data:`DOCUMENTS_REL` — import a candidate as an
  immutable document snapshot record; :func:`current_commitments` — the
  commitments of current (not submitted, not superseded) snapshots.
* :func:`build_package`, :data:`VIEW_POLICIES`, :data:`POLICY_VERSION` — a
  bounded evidence package for a task under a view policy and a budget;
  :func:`write_package` — the deterministic manifest writer.
* :func:`record_change`, :func:`load_snapshot`, :func:`read_record_version`
  — record an approved new version of a Tier 3 record with the old version
  kept, both snapshots stored content-addressed.
* :func:`plan_impact`, :data:`ACTIONS` — the shadow impact planner over two
  snapshots and the durable run records; :func:`write_impact_plan` — the
  deterministic advisory-plan writer.

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
from runner.dev_graph.changes import (
    CHANGE_KINDS,
    CHANGE_SCHEMA_ID,
    CHANGES_REL,
    RECORD_PATHS,
    RECORD_VERSIONS_REL,
    SNAPSHOTS_REL,
    ChangeRecord,
    change_set,
    load_snapshot,
    read_change_record,
    read_record_version,
    record_change,
    store_snapshot,
)
from runner.dev_graph.documents import (
    DOCUMENT_SCHEMA_ID,
    DOCUMENTS_REL,
    DocumentRef,
    import_document,
)
from runner.dev_graph.identity import canonical_json, content_hash
from runner.dev_graph.impact import (
    ACTIONS,
    ENTRY_KINDS,
    HITS,
    IMPACT_PLANS_REL,
    IMPACT_REQUEST_REL,
    PLAN_SCHEMA_ID,
    RECORD_KINDS,
    RUN_RECORDS_REL,
    RUN_RECORDS_SCHEMA_ID,
    ImpactPlan,
    normalise_run_records,
    plan_impact,
    read_run_records,
    write_impact_plan,
)
from runner.dev_graph.packages import (
    COMPLETENESS,
    EXCLUSION_REASONS,
    MANDATORY_PREDICATES,
    MANIFEST_SCHEMA_ID,
    PACKAGE_REQUEST_REL,
    PACKAGE_SCHEMA_ID,
    PACKAGES_REL,
    SELECTION_REASONS,
    Package,
    build_package,
    write_package,
)
from runner.dev_graph.policies import (
    HISTORICAL_FEEDBACK_TAGS,
    POLICY_VERSION,
    VIEW_POLICIES,
    VIEWS,
    ViewPolicy,
)
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
    "ACTIONS",
    "APPROVALS",
    "CHANGES_REL",
    "CHANGE_KINDS",
    "CHANGE_SCHEMA_ID",
    "COMPLETENESS",
    "CURRENT_DOCUMENT_STATES",
    "DECLARED_STATUSES",
    "DOCUMENTS_REL",
    "DOCUMENT_SCHEMA_ID",
    "DOCUMENT_STATES",
    "DOMAIN_LINK",
    "EXCLUSION_REASONS",
    "ENTRY_KINDS",
    "EXECUTION_DEPENDENCY",
    "HITS",
    "IMPACT_PLANS_REL",
    "IMPACT_REQUEST_REL",
    "HISTORICAL_FEEDBACK_TAGS",
    "MANDATORY_PREDICATES",
    "MANIFEST_SCHEMA_ID",
    "NODE_TYPES",
    "PACKAGES_REL",
    "PACKAGE_REQUEST_REL",
    "PACKAGE_SCHEMA_ID",
    "PLAN_SCHEMA_ID",
    "POLICY_VERSION",
    "RECORD_KINDS",
    "RECORD_PATHS",
    "RECORD_VERSIONS_REL",
    "RELATIONSHIPS",
    "RUN_RECORDS_REL",
    "RUN_RECORDS_SCHEMA_ID",
    "SCHEMA_ID",
    "SELECTION_REASONS",
    "SNAPSHOTS_REL",
    "SNAPSHOT_REL",
    "VIEWS",
    "VIEW_POLICIES",
    "ChangeRecord",
    "DevGraphError",
    "DocumentRef",
    "ImpactPlan",
    "Package",
    "RelationshipSpec",
    "Snapshot",
    "ViewPolicy",
    "build_package",
    "build_snapshot",
    "canonical_json",
    "change_set",
    "content_hash",
    "current_commitments",
    "edge_label",
    "import_document",
    "load_snapshot",
    "normalise_run_records",
    "plan_impact",
    "read_change_record",
    "read_record_version",
    "read_run_records",
    "record_change",
    "store_snapshot",
    "validate_graph",
    "write_impact_plan",
    "write_package",
    "write_snapshot",
]
