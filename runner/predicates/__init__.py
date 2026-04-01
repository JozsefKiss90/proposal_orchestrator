"""
Gate predicate implementations for the DAG runner.

Public API (Step 3 — file predicates):
    exists, non_empty, non_empty_json, dir_non_empty

Public API (Step 4 — gate-pass predicate):
    gate_pass_recorded

Public API (Step 5 — schema predicates, §4.2 and §4.8):
    json_field_present, json_fields_present,
    instrument_type_matches_schema, interface_contract_conforms,
    risk_register_populated, ethics_assessment_explicit,
    governance_matrix_present, no_blocking_inconsistencies,
    budget_gate_confirmation_present, findings_categorised_by_severity,
    revision_action_list_present, all_critical_revisions_resolved,
    checkpoint_published

Public API (Step 6 — source reference predicates, §4.3):
    source_refs_present, all_mappings_have_source_refs

All predicates return a ``PredicateResult``.  The ``failure_category``
field on a failing result is the primary triage signal consumed by the
GateResult writer (Step 10).
"""

from runner.predicates.file_predicates import (
    dir_non_empty,
    exists,
    non_empty,
    non_empty_json,
)
from runner.predicates.gate_pass_predicates import gate_pass_recorded
from runner.predicates.schema_predicates import (
    all_critical_revisions_resolved,
    budget_gate_confirmation_present,
    checkpoint_published,
    ethics_assessment_explicit,
    findings_categorised_by_severity,
    governance_matrix_present,
    instrument_type_matches_schema,
    interface_contract_conforms,
    json_field_present,
    json_fields_present,
    no_blocking_inconsistencies,
    revision_action_list_present,
    risk_register_populated,
)
from runner.predicates.source_ref_predicates import (
    all_mappings_have_source_refs,
    source_refs_present,
)
from runner.predicates.types import (
    CROSS_ARTIFACT_INCONSISTENCY,
    FAILURE_CATEGORIES,
    MALFORMED_ARTIFACT,
    MISSING_MANDATORY_INPUT,
    POLICY_VIOLATION,
    STALE_UPSTREAM_MISMATCH,
    PredicateResult,
)

__all__ = [
    # types
    "PredicateResult",
    "FAILURE_CATEGORIES",
    "MISSING_MANDATORY_INPUT",
    "MALFORMED_ARTIFACT",
    "CROSS_ARTIFACT_INCONSISTENCY",
    "POLICY_VIOLATION",
    "STALE_UPSTREAM_MISMATCH",
    # file predicates (Step 3)
    "exists",
    "non_empty",
    "non_empty_json",
    "dir_non_empty",
    # gate-pass predicate (Step 4)
    "gate_pass_recorded",
    # schema predicates (Step 5 — §4.2)
    "json_field_present",
    "json_fields_present",
    "instrument_type_matches_schema",
    "interface_contract_conforms",
    # canonical field predicates (Step 5 — §4.8)
    "risk_register_populated",
    "ethics_assessment_explicit",
    "governance_matrix_present",
    "no_blocking_inconsistencies",
    "budget_gate_confirmation_present",
    "findings_categorised_by_severity",
    "revision_action_list_present",
    "all_critical_revisions_resolved",
    "checkpoint_published",
    # source reference predicates (Step 6 — §4.3)
    "source_refs_present",
    "all_mappings_have_source_refs",
]
