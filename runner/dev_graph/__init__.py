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
  :data:`DEFAULT_PACKAGE_BUDGET` — the budget a caller defaults to;
  :func:`write_package` — the deterministic manifest writer;
  :func:`package_dir` — where one package lands.
* :data:`DECLARED_STATUS_FIELDS`, :func:`declared_status` — where each node
  type declares its §12.2 status, and the pure read of it the manifest rolls
  up. Declared per type, never sniffed from a value.
* :func:`record_change`, :func:`load_snapshot`, :func:`read_record_version`
  — record an approved new version of a Tier 3 record with the old version
  kept, both snapshots stored content-addressed.
* :func:`plan_impact`, :data:`ACTIONS` — the shadow impact planner over two
  snapshots and the durable run records; :func:`write_impact_plan` — the
  deterministic advisory-plan writer.
* :func:`check_revision`, :func:`normalise_contract`, :data:`CHANGE_CLASSES`,
  :data:`CONTRACT_VERDICTS` — the pure revision contract checker;
  :func:`create_candidate_version` — a new candidate version superseding
  the old one with provenance; :func:`bind_assessment`,
  :func:`check_applicability`, :data:`APPLICABILITY_REASONS` — whether an
  assessment still applies; :func:`write_revision_record` — the
  deterministic revision record writer.
* :func:`compare_shadow`, :data:`DIAGNOSTICS` — the planner's advisory
  against the scheduler's recorded reuse decision (agreed, planner
  narrower, planner broader); :func:`write_shadow_comparison` — the
  deterministic comparison writer. Nothing consumes it at runtime.
* :class:`Scenario`, :class:`Arm`, :func:`run_scenario`, :data:`TRANSFORMS`,
  :func:`materialise_sandbox` — a scripted approved change run against a copy
  of the world's own snapshot inputs, with its contract check, its advisory
  and its comparison; :func:`write_scenario_records` — the record writer.
  The catalogue of scenarios is project data and lives outside this package.
* :func:`record_esr_intake`, :func:`read_esr_intake`, :data:`ESR_AVAILABILITY`,
  :data:`PERMITTED_PURPOSES` — the ESR intake record: availability declared
  from a closed set and never inferred, bound submission and call ids, and
  the permitted purpose.

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
    DOCUMENT_SCHEMA_ID_V2,
    DOCUMENT_SCHEMA_IDS,
    DOCUMENTS_REL,
    DocumentRef,
    import_candidate,
    import_document,
    render_record,
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
from runner.dev_graph.intake import (
    ESR_AVAILABILITY,
    INTAKE_REL,
    INTAKE_SCHEMA_ID,
    PERMITTED_PURPOSES,
    EsrIntake,
    normalise_intake,
    read_esr_intake,
    record_esr_intake,
)
from runner.dev_graph.packages import (
    COMPLETENESS,
    DEFAULT_PACKAGE_BUDGET,
    EXCLUSION_REASONS,
    MANDATORY_PREDICATES,
    MANIFEST_SCHEMA_ID,
    PACKAGE_REQUEST_REL,
    PACKAGE_SCHEMA_ID,
    PACKAGES_REL,
    SELECTION_REASONS,
    Package,
    build_package,
    package_dir,
    write_package,
)
from runner.dev_graph.policies import (
    HISTORICAL_FEEDBACK_TAGS,
    POLICY_VERSION,
    VIEW_POLICIES,
    VIEWS,
    ViewPolicy,
)
from runner.dev_graph.scenarios import (
    ARM_KINDS,
    ENACTMENT_SCHEMA_ID,
    RECORDED,
    RERUN_SCHEMA_ID,
    SCENARIO_INDEX_SCHEMA_ID,
    SCENARIO_SCHEMA_ID,
    SCENARIOS_REL,
    TRANSFORMS,
    Arm,
    ArmResult,
    Enactment,
    Sandbox,
    Scenario,
    ScenarioResult,
    advisory_rel,
    apply_transform,
    enact_scenario,
    enactment_rel,
    materialise_sandbox,
    read_enactment,
    read_rerun,
    read_reruns,
    record_rerun,
    rerun_rel,
    reruns_rel,
    run_scenario,
    scenario_rel,
    shadow_label,
    versions_before,
    write_scenario_records,
)
from runner.dev_graph.shadow import (
    DIAGNOSTICS,
    SHADOW_COMPARISONS_REL,
    SHADOW_REQUEST_REL,
    SHADOW_SCHEMA_ID,
    VERDICTS,
    ShadowComparison,
    advisory_verdicts,
    compare_shadow,
    locate_run_manifest,
    read_plan,
    read_reuse_decisions,
    write_shadow_comparison,
)
from runner.dev_graph.revisions import (
    APPLICABILITY_REASONS,
    CHANGE_CLASSES,
    CONTRACT_VERDICTS,
    REVISION_REQUEST_REL,
    REVISION_SCHEMA_ID,
    REVISIONS_REL,
    Applicability,
    ContractCheck,
    RevisionContract,
    RevisionRecord,
    bind_assessment,
    build_provenance,
    check_applicability,
    check_revision,
    classify_change_set,
    create_candidate_version,
    normalise_contract,
    read_revision_record,
    write_revision_record,
)
from runner.dev_graph.schema import (
    APPROVALS,
    CURRENT_DOCUMENT_STATES,
    DECLARED_STATUSES,
    DECLARED_STATUS_FIELDS,
    DOCUMENT_STATES,
    DOMAIN_LINK,
    EXECUTION_DEPENDENCY,
    NODE_TYPES,
    RELATIONSHIPS,
    DevGraphError,
    RelationshipSpec,
    declared_status,
    edge_label,
    validate_graph,
)
from runner.dev_graph.writer import SNAPSHOT_REL, write_snapshot

__all__ = [
    "ACTIONS",
    "APPLICABILITY_REASONS",
    "APPROVALS",
    "CHANGES_REL",
    "CHANGE_CLASSES",
    "CHANGE_KINDS",
    "CHANGE_SCHEMA_ID",
    "COMPLETENESS",
    "CONTRACT_VERDICTS",
    "CURRENT_DOCUMENT_STATES",
    "DECLARED_STATUSES",
    "DECLARED_STATUS_FIELDS",
    "DEFAULT_PACKAGE_BUDGET",
    "DIAGNOSTICS",
    "DOCUMENTS_REL",
    "DOCUMENT_SCHEMA_ID",
    "DOCUMENT_SCHEMA_ID_V2",
    "DOCUMENT_SCHEMA_IDS",
    "DOCUMENT_STATES",
    "DOMAIN_LINK",
    "ENTRY_KINDS",
    "ESR_AVAILABILITY",
    "EXCLUSION_REASONS",
    "EXECUTION_DEPENDENCY",
    "HISTORICAL_FEEDBACK_TAGS",
    "HITS",
    "IMPACT_PLANS_REL",
    "IMPACT_REQUEST_REL",
    "INTAKE_REL",
    "INTAKE_SCHEMA_ID",
    "MANDATORY_PREDICATES",
    "MANIFEST_SCHEMA_ID",
    "NODE_TYPES",
    "PACKAGES_REL",
    "PACKAGE_REQUEST_REL",
    "PACKAGE_SCHEMA_ID",
    "PERMITTED_PURPOSES",
    "PLAN_SCHEMA_ID",
    "POLICY_VERSION",
    "RECORD_KINDS",
    "RECORD_PATHS",
    "RECORD_VERSIONS_REL",
    "RELATIONSHIPS",
    "REVISIONS_REL",
    "REVISION_REQUEST_REL",
    "REVISION_SCHEMA_ID",
    "RUN_RECORDS_REL",
    "RUN_RECORDS_SCHEMA_ID",
    "SCHEMA_ID",
    "SELECTION_REASONS",
    "ARM_KINDS",
    "RECORDED",
    "Arm",
    "ArmResult",
    "ENACTMENT_SCHEMA_ID",
    "Enactment",
    "RERUN_SCHEMA_ID",
    "SCENARIOS_REL",
    "SCENARIO_INDEX_SCHEMA_ID",
    "SCENARIO_SCHEMA_ID",
    "Sandbox",
    "Scenario",
    "ScenarioResult",
    "TRANSFORMS",
    "advisory_rel",
    "advisory_verdicts",
    "apply_transform",
    "enact_scenario",
    "enactment_rel",
    "materialise_sandbox",
    "read_enactment",
    "read_rerun",
    "read_reruns",
    "record_rerun",
    "rerun_rel",
    "reruns_rel",
    "run_scenario",
    "scenario_rel",
    "shadow_label",
    "versions_before",
    "write_scenario_records",
    "SHADOW_COMPARISONS_REL",
    "SHADOW_REQUEST_REL",
    "SHADOW_SCHEMA_ID",
    "SNAPSHOTS_REL",
    "SNAPSHOT_REL",
    "VERDICTS",
    "VIEWS",
    "VIEW_POLICIES",
    "Applicability",
    "ChangeRecord",
    "ContractCheck",
    "DevGraphError",
    "DocumentRef",
    "EsrIntake",
    "ImpactPlan",
    "Package",
    "RelationshipSpec",
    "RevisionContract",
    "RevisionRecord",
    "ShadowComparison",
    "Snapshot",
    "ViewPolicy",
    "bind_assessment",
    "build_package",
    "build_provenance",
    "build_snapshot",
    "canonical_json",
    "change_set",
    "check_applicability",
    "check_revision",
    "classify_change_set",
    "compare_shadow",
    "content_hash",
    "create_candidate_version",
    "current_commitments",
    "declared_status",
    "edge_label",
    "import_candidate",
    "import_document",
    "load_snapshot",
    "normalise_contract",
    "normalise_intake",
    "normalise_run_records",
    "package_dir",
    "plan_impact",
    "read_change_record",
    "read_esr_intake",
    "read_plan",
    "locate_run_manifest",
    "read_record_version",
    "render_record",
    "read_reuse_decisions",
    "read_revision_record",
    "read_run_records",
    "record_change",
    "record_esr_intake",
    "store_snapshot",
    "validate_graph",
    "write_impact_plan",
    "write_package",
    "write_revision_record",
    "write_shadow_comparison",
    "write_snapshot",
]
