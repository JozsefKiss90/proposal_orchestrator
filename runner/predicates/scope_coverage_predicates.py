"""
Scope coverage predicate for Phase 2 gate.

Implements a deterministic predicate that verifies all mandatory Tier 2B
scope requirements are explicitly covered in the concept_refinement_summary's
scope_coverage field.

This replaces the fragile pattern where the semantic predicate
no_unresolved_scope_conflicts had to infer missing coverage from the
absence of entries in scope_conflict_log — which could not distinguish
"covered but not logged" from "not covered".

The predicate reads:
  - concept_refinement_summary.json (scope_coverage + scope_conflict_log)
  - scope_requirements.json (mandatory requirements)
  - call_constraints.json (call constraints)

And checks:
  1. scope_coverage field is present and is a non-empty object
  2. Every mandatory SR-xx requirement has an entry in scope_coverage
  3. No entry has coverage_status == "unresolved" without a corresponding
     scope_conflict_log entry
  4. No mandatory element is missing from scope_coverage entirely
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Union

from runner.paths import resolve_repo_path
from runner.predicates.types import (
    CROSS_ARTIFACT_INCONSISTENCY,
    MALFORMED_ARTIFACT,
    MISSING_MANDATORY_INPUT,
    PredicateResult,
)

PathLike = Union[str, Path]

_VALID_COVERAGE_STATUSES = frozenset({
    "covered",
    "partially_covered",
    "unresolved",
    "not_applicable",
})

_PASSING_STATUSES = frozenset({
    "covered",
    "partially_covered",
    "not_applicable",
})


def _read_json(resolved: Path) -> tuple[Optional[dict], Optional[PredicateResult]]:
    """Read a JSON file and return (parsed_dict, None) or (None, error)."""
    if not resolved.exists():
        return None, PredicateResult(
            passed=False,
            failure_category=MISSING_MANDATORY_INPUT,
            reason=f"Path does not exist: {resolved}",
            details={"path": str(resolved)},
        )
    if resolved.is_dir():
        return None, PredicateResult(
            passed=False,
            failure_category=MISSING_MANDATORY_INPUT,
            reason=f"Expected a JSON file but found a directory: {resolved}",
            details={"path": str(resolved), "is_dir": True},
        )
    try:
        text = resolved.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        return None, PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=f"Cannot read {resolved}: {exc}",
            details={"path": str(resolved)},
        )
    if not text.strip():
        return None, PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=f"File is empty: {resolved}",
            details={"path": str(resolved)},
        )
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        return None, PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=f"Invalid JSON in {resolved}: {exc}",
            details={"path": str(resolved)},
        )
    if not isinstance(parsed, dict):
        return None, PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=f"Expected a JSON object in {resolved}, got {type(parsed).__name__}.",
            details={"path": str(resolved)},
        )
    return parsed, None


def all_mandatory_scope_covered(
    summary_path: PathLike,
    scope_path: PathLike,
    constraints_path: PathLike,
    *,
    repo_root: Optional[Path] = None,
) -> PredicateResult:
    """
    Pass iff every mandatory Tier 2B scope requirement has an entry in
    scope_coverage with a non-unresolved coverage_status.

    Contract
    --------
    Pass condition:
        * scope_coverage is present in concept_refinement_summary.json
          and is a non-empty object
        * Every mandatory requirement from scope_requirements.json
          (requirement.mandatory == true) has a corresponding entry in
          scope_coverage keyed by its requirement_id
        * No entry has coverage_status == "unresolved"
        * Every "unresolved" entry also appears in scope_conflict_log

    Gate usage: g03_p08 (phase_02_gate) — deterministic replacement for
    the scope-coverage aspect of the semantic no_unresolved_scope_conflicts
    predicate.

    Failure categories
    ------------------
    ``MISSING_MANDATORY_INPUT``      — a required file is absent
    ``MALFORMED_ARTIFACT``           — invalid JSON or missing required field
    ``CROSS_ARTIFACT_INCONSISTENCY`` — mandatory scope element missing or
                                       unresolved in scope_coverage
    """
    summary_resolved = resolve_repo_path(summary_path, repo_root)
    scope_resolved = resolve_repo_path(scope_path, repo_root)
    constraints_resolved = resolve_repo_path(constraints_path, repo_root)

    # Read summary
    summary, err = _read_json(summary_resolved)
    if err is not None:
        return err

    # Read scope requirements
    scope_data, err = _read_json(scope_resolved)
    if err is not None:
        return err

    # Read call constraints (optional — continue without if absent)
    constraints_data: Optional[dict] = None
    if constraints_resolved.exists():
        constraints_data, err = _read_json(constraints_resolved)
        if err is not None:
            # Constraints file exists but is malformed — report it
            return err

    # Extract scope_coverage from summary
    scope_coverage = summary.get("scope_coverage")
    if scope_coverage is None:
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=(
                f"concept_refinement_summary.json is missing the required "
                f"'scope_coverage' field. The concept-alignment-check skill "
                f"must populate scope_coverage for all mandatory Tier 2B "
                f"scope requirements."
            ),
            details={"path": str(summary_resolved), "field": "scope_coverage"},
        )

    if not isinstance(scope_coverage, dict):
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=(
                f"scope_coverage must be an object; "
                f"got {type(scope_coverage).__name__}."
            ),
            details={"path": str(summary_resolved)},
        )

    # Extract mandatory requirement IDs from scope_requirements.json
    mandatory_ids: set[str] = set()
    requirements = scope_data.get("requirements", [])
    if isinstance(requirements, list):
        for req in requirements:
            if isinstance(req, dict) and req.get("mandatory", False):
                req_id = req.get("requirement_id")
                if isinstance(req_id, str) and req_id.strip():
                    mandatory_ids.add(req_id)

    # Also extract constraint IDs from call_constraints.json
    constraint_ids: set[str] = set()
    if constraints_data is not None:
        constraints = constraints_data.get("constraints", [])
        if isinstance(constraints, list):
            for cc in constraints:
                if isinstance(cc, dict):
                    cc_id = cc.get("constraint_id")
                    if isinstance(cc_id, str) and cc_id.strip():
                        constraint_ids.add(cc_id)

    all_required = mandatory_ids | constraint_ids

    if not all_required:
        return PredicateResult(
            passed=True,
            details={
                "summary_path": str(summary_resolved),
                "scope_path": str(scope_resolved),
                "mandatory_elements_checked": 0,
                "note": "No mandatory scope elements found; vacuous pass.",
            },
        )

    # Extract scope_conflict_log for consistency checking
    scope_conflict_log = summary.get("scope_conflict_log", [])
    conflict_ids_in_log: set[str] = set()
    if isinstance(scope_conflict_log, list):
        for conflict in scope_conflict_log:
            if isinstance(conflict, dict):
                cid = conflict.get("conflict_id", "")
                if isinstance(cid, str):
                    conflict_ids_in_log.add(cid)

    # Check coverage
    missing_elements: list[str] = []
    unresolved_elements: list[str] = []
    invalid_status_elements: list[dict] = []
    consistency_violations: list[str] = []

    for element_id in sorted(all_required):
        entry = scope_coverage.get(element_id)
        if entry is None:
            missing_elements.append(element_id)
            continue

        if not isinstance(entry, dict):
            invalid_status_elements.append({
                "element_id": element_id,
                "issue": "entry_not_a_dict",
            })
            continue

        status = entry.get("coverage_status")
        if status not in _VALID_COVERAGE_STATUSES:
            invalid_status_elements.append({
                "element_id": element_id,
                "issue": f"invalid_coverage_status: {status!r}",
            })
            continue

        if status == "unresolved":
            unresolved_elements.append(element_id)
            # Consistency: unresolved must also be in scope_conflict_log
            if element_id not in conflict_ids_in_log:
                consistency_violations.append(element_id)

    # Build failure details
    violations: list[str] = []
    violation_details: list[dict] = []

    if missing_elements:
        violations.extend(missing_elements)
        for eid in missing_elements:
            violation_details.append({
                "element_id": eid,
                "issue": "missing_from_scope_coverage",
            })

    if unresolved_elements:
        violations.extend(unresolved_elements)
        for eid in unresolved_elements:
            violation_details.append({
                "element_id": eid,
                "issue": "coverage_status_unresolved",
            })

    if invalid_status_elements:
        for entry in invalid_status_elements:
            violations.append(entry["element_id"])
            violation_details.append(entry)

    if consistency_violations:
        for eid in consistency_violations:
            violation_details.append({
                "element_id": eid,
                "issue": "unresolved_but_not_in_scope_conflict_log",
            })

    if violations:
        return PredicateResult(
            passed=False,
            failure_category=CROSS_ARTIFACT_INCONSISTENCY,
            reason=(
                f"{len(violations)} mandatory scope element(s) are missing "
                f"from scope_coverage or have unresolved coverage: "
                f"{sorted(set(violations))}. "
                "All mandatory Tier 2B scope requirements must be explicitly "
                "covered in scope_coverage with a passing coverage_status."
            ),
            details={
                "summary_path": str(summary_resolved),
                "scope_path": str(scope_resolved),
                "mandatory_elements_checked": len(all_required),
                "mandatory_sr_ids": sorted(mandatory_ids),
                "constraint_cc_ids": sorted(constraint_ids),
                "missing_elements": missing_elements,
                "unresolved_elements": unresolved_elements,
                "invalid_status_elements": invalid_status_elements,
                "consistency_violations": consistency_violations,
                "violations": violation_details,
            },
        )

    return PredicateResult(
        passed=True,
        details={
            "summary_path": str(summary_resolved),
            "scope_path": str(scope_resolved),
            "mandatory_elements_checked": len(all_required),
            "all_covered": True,
        },
    )
