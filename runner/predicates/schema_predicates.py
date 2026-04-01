"""
Step 5 — Schema predicates.

Implements the schema-level deterministic predicates defined in
gate_rules_library_plan.md §4.2 and §4.8:

    §4.2 — Schema predicates:
        json_field_present(path, field)
        json_fields_present(path, fields)
        instrument_type_matches_schema(call_path, schema_path)
        interface_contract_conforms(response_path, contract_path)

    §4.8 — Canonical field predicates:
        risk_register_populated(path)
        ethics_assessment_explicit(path)
        governance_matrix_present(path)
        no_blocking_inconsistencies(path)
        budget_gate_confirmation_present(path)
        findings_categorised_by_severity(path)
        revision_action_list_present(path)
        all_critical_revisions_resolved(path)
        checkpoint_published(path)

All functions accept a ``repo_root`` keyword argument.  Paths are resolved
via ``runner.paths.resolve_repo_path``.

Design constraints (from gate_rules_library_plan.md §4.2, §4.8, and the
Step 5 implementation brief):

* All §4.8 predicates inspect a single canonical file path; no directory
  scanning.  Mandated by §4.8: "All predicates in this section take a
  canonical file path, not a directory path."
* JSON files are read as UTF-8 with BOM stripping (utf-8-sig), consistent
  with Step 3 file predicates.
* ``interface_contract_conforms`` uses ``jsonschema`` 4.x for JSON Schema
  validation.  jsonschema 4.23.0 is confirmed available in this
  environment.
* Failure categories follow the Step 5 mapping from gate_rules_library_plan.md §3:
    absent file/dir                  → MISSING_MANDATORY_INPUT
    invalid JSON / missing field     → MALFORMED_ARTIFACT
    structurally-valid rule violation → POLICY_VIOLATION

Registry format assumption (instrument_type_matches_schema)
-----------------------------------------------------------
``section_schema_registry.json`` (the schema_path argument) is expected
to be a JSON object whose top-level keys are instrument type identifiers
(e.g., "RIA", "IA", "CSA", "MSCA-PF").  An instrument_type matches when
it appears as a key in this object.  This is the narrowest correct
interpretation supported by the current (empty ``{}``) registry file; no
other structural signal exists to distinguish field semantics.  When the
registry is populated this interpretation must be validated against the
actual format.

Sentinel set (ethics_assessment_explicit)
-----------------------------------------
Defined in ``artifact_schema_specification.yaml`` §1.6, field
``ethics_assessment``:
    "Must not be null, empty string, or the sentinel placeholder value
    'N/A'".
``_ETHICS_SENTINELS = {"N/A"}`` — no other sentinels are defined in the
schema specification.  The predicate additionally checks the
``self_assessment_statement`` sub-field of the ethics_assessment object
because ``artifact_schema_specification.yaml`` §1.6 states: "This is the
field that ethics_assessment_explicit verifies is present, non-null, not
empty, and not a placeholder."

No-JSON-files behaviour (interface_contract_conforms)
-----------------------------------------------------
If response_path contains no .json direct-child files this predicate
passes.  The policy is that ``dir_non_empty`` is evaluated as a separate
preceding predicate (gate_rules_library_plan.md §5 gate sequences) so this
predicate is reached only when overall presence has been confirmed.  The
predicate's role is structure validation, not presence confirmation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional, Union

import jsonschema
import jsonschema.exceptions

from runner.paths import resolve_repo_path
from runner.predicates.types import (
    MALFORMED_ARTIFACT,
    MISSING_MANDATORY_INPUT,
    POLICY_VIOLATION,
    PredicateResult,
)

PathLike = Union[str, Path]

# ---------------------------------------------------------------------------
# Sentinel values for ethics_assessment_explicit
# Source: artifact_schema_specification.yaml §1.6 (implementation_architecture)
# ---------------------------------------------------------------------------
_ETHICS_SENTINELS: frozenset[str] = frozenset({"N/A"})
"""
Placeholder sentinel strings that are not acceptable as ethics
self-assessment content.  Sourced exclusively from
artifact_schema_specification.yaml §1.6, field description:
"Must not be null, empty string, or the sentinel placeholder value 'N/A'".
No other sentinels are defined in the specification.
"""

# ---------------------------------------------------------------------------
# Valid severity values for findings_categorised_by_severity
# Source: artifact_schema_specification.yaml §2.2 (review_packet.findings.severity)
# ---------------------------------------------------------------------------
_FINDING_SEVERITIES: frozenset[str] = frozenset({"critical", "major", "minor"})
"""
Allowed severity values for findings entries.  Sourced from
artifact_schema_specification.yaml §2.2 review_packet findings.severity
enum: [critical, major, minor].
"""


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------


def _read_json_object(
    resolved: Path,
) -> tuple[Optional[dict], Optional[PredicateResult]]:
    """
    Read *resolved* as a UTF-8 JSON file and return ``(parsed_dict, None)``
    when it is a valid JSON object.  On any failure return
    ``(None, PredicateResult(...))``.

    Used by all §4.2 and §4.8 predicates that require a single canonical
    JSON file containing a top-level object.

    Failure categories returned:
    * ``MISSING_MANDATORY_INPUT`` — path absent or is a directory
    * ``MALFORMED_ARTIFACT``      — encoding error, invalid JSON, or
                                    parsed type is not dict
    """
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
            reason=(
                f"Expected a JSON file but found a directory: {resolved}.  "
                "This predicate requires a canonical artifact file path."
            ),
            details={"path": str(resolved), "is_dir": True},
        )

    try:
        text = resolved.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        return None, PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=f"File is not valid UTF-8: {exc}",
            details={"path": str(resolved), "encoding_error": str(exc)},
        )

    if not text.strip():
        return None, PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=f"File is empty (no non-whitespace content): {resolved}",
            details={"path": str(resolved)},
        )

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        return None, PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=f"Invalid JSON in {resolved}: {exc}",
            details={
                "path": str(resolved),
                "json_error": str(exc),
                "error_line": exc.lineno,
                "error_col": exc.colno,
            },
        )

    if not isinstance(parsed, dict):
        return None, PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=(
                f"Expected a JSON object (dict) but got {type(parsed).__name__}: {resolved}.  "
                "All canonical artifact files must have a top-level JSON object."
            ),
            details={"path": str(resolved), "parsed_type": type(parsed).__name__},
        )

    return parsed, None


# ---------------------------------------------------------------------------
# §4.2 — Schema predicates
# ---------------------------------------------------------------------------


def json_field_present(
    path: PathLike,
    field: str,
    *,
    repo_root: Optional[Path] = None,
) -> PredicateResult:
    """
    Pass iff *path* is a valid JSON object containing top-level *field*
    with a non-null value.

    Contract (gate_rules_library_plan.md §4.2)
    -------------------------------------------
    Pass condition:
        * path exists and is a file
        * file is valid UTF-8 JSON
        * parsed value is a JSON object (dict)
        * top-level *field* is present
        * value of *field* is not null

    Failure categories
    ------------------
    ``MISSING_MANDATORY_INPUT``
        Path does not exist (or is a directory).
    ``MALFORMED_ARTIFACT``
        Invalid JSON, non-object JSON, missing field, or null field.

    Parameters
    ----------
    path:
        Repository-relative or absolute path to the canonical artifact.
    field:
        Top-level field name to check.
    repo_root:
        Repository root for relative path resolution.
    """
    resolved = resolve_repo_path(path, repo_root)
    parsed, err = _read_json_object(resolved)
    if err is not None:
        return err

    if field not in parsed:
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=f"Required top-level field {field!r} is absent in {resolved}",
            details={"path": str(resolved), "missing_field": field},
        )

    if parsed[field] is None:
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=f"Required top-level field {field!r} is null in {resolved}",
            details={"path": str(resolved), "null_field": field},
        )

    return PredicateResult(
        passed=True,
        details={"path": str(resolved), "field": field},
    )


def json_fields_present(
    path: PathLike,
    fields: List[str],
    *,
    repo_root: Optional[Path] = None,
) -> PredicateResult:
    """
    Pass iff *path* is a valid JSON object containing all *fields* with
    non-null values.

    Contract (gate_rules_library_plan.md §4.2)
    -------------------------------------------
    Pass condition:
        * path exists and is a valid JSON object
        * every field in *fields* is present at top level
        * every field value is non-null

    All missing and null fields are collected before returning; the first
    problem encountered determines the failure reason but all problems are
    included in ``details``.

    Failure categories
    ------------------
    ``MISSING_MANDATORY_INPUT``
        Path does not exist.
    ``MALFORMED_ARTIFACT``
        Invalid JSON, non-object JSON, any listed field absent, or any
        listed field null.

    Parameters
    ----------
    path:
        Repository-relative or absolute path to the canonical artifact.
    fields:
        List of top-level field names that must all be present and non-null.
    repo_root:
        Repository root for relative path resolution.
    """
    resolved = resolve_repo_path(path, repo_root)
    parsed, err = _read_json_object(resolved)
    if err is not None:
        return err

    missing = [f for f in fields if f not in parsed]
    null_fields = [f for f in fields if f in parsed and parsed[f] is None]

    if missing or null_fields:
        problems: list[str] = []
        if missing:
            problems.append(f"absent: {missing}")
        if null_fields:
            problems.append(f"null: {null_fields}")
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=(
                f"Required top-level fields not satisfied in {resolved} — "
                + "; ".join(problems)
            ),
            details={
                "path": str(resolved),
                "missing_fields": missing,
                "null_fields": null_fields,
            },
        )

    return PredicateResult(
        passed=True,
        details={"path": str(resolved), "fields_checked": list(fields)},
    )


def instrument_type_matches_schema(
    call_path: PathLike,
    schema_path: PathLike,
    *,
    repo_root: Optional[Path] = None,
) -> PredicateResult:
    """
    Pass iff the ``instrument_type`` field in *call_path* matches at least
    one entry in the schema registry at *schema_path*.

    Contract (gate_rules_library_plan.md §4.2)
    -------------------------------------------
    Pass condition:
        * call_path is a valid JSON object containing non-null
          ``instrument_type``
        * schema_path is a valid JSON object (the section schema registry)
        * the ``instrument_type`` value is a key in the registry object

    Registry format assumption
    --------------------------
    The section_schema_registry.json is expected to be a JSON object whose
    top-level keys are instrument type identifiers (e.g., "RIA", "IA",
    "CSA", "MSCA-PF").  A match is confirmed when ``instrument_type``
    appears as a key.  See module docstring for the full rationale.

    Failure categories
    ------------------
    ``MISSING_MANDATORY_INPUT``
        Either call_path or schema_path does not exist.
    ``MALFORMED_ARTIFACT``
        Invalid JSON, non-object JSON, or ``instrument_type`` field absent
        or null in call_path; or schema_path cannot be read as a JSON
        object.
    ``POLICY_VIOLATION``
        ``instrument_type`` value is present but not found in the registry.
        Constitutional violation: CLAUDE.md §7 Phase 1 gate requires the
        instrument type to resolve to a Tier 2A schema entry.

    Parameters
    ----------
    call_path:
        Path to selected_call.json (contains instrument_type).
    schema_path:
        Path to section_schema_registry.json (the registry).
    repo_root:
        Repository root for relative path resolution.
    """
    resolved_call = resolve_repo_path(call_path, repo_root)
    resolved_schema = resolve_repo_path(schema_path, repo_root)

    # Read call artifact
    call_data, err = _read_json_object(resolved_call)
    if err is not None:
        return err

    if "instrument_type" not in call_data:
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=(
                f"Required field 'instrument_type' is absent in {resolved_call}"
            ),
            details={"path": str(resolved_call), "missing_field": "instrument_type"},
        )

    instrument_type = call_data["instrument_type"]
    if instrument_type is None:
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=f"Field 'instrument_type' is null in {resolved_call}",
            details={"path": str(resolved_call), "null_field": "instrument_type"},
        )

    # Read schema registry — re-wrap error to surface schema_path context
    registry, err = _read_json_object(resolved_schema)
    if err is not None:
        return PredicateResult(
            passed=False,
            failure_category=err.failure_category,
            reason=f"Schema registry at {resolved_schema}: {err.reason}",
            details={**err.details, "schema_path": str(resolved_schema)},
        )

    # Lookup: instrument_type must be a top-level key in the registry
    if instrument_type not in registry:
        return PredicateResult(
            passed=False,
            failure_category=POLICY_VIOLATION,
            reason=(
                f"instrument_type {instrument_type!r} from {resolved_call} "
                f"is not registered in the schema registry at {resolved_schema}.  "
                f"Known instrument types: "
                f"{sorted(registry.keys()) if registry else '(registry is empty)'}"
            ),
            details={
                "path": str(resolved_call),
                "schema_path": str(resolved_schema),
                "instrument_type": instrument_type,
                "registry_keys": sorted(registry.keys()),
            },
        )

    return PredicateResult(
        passed=True,
        details={
            "path": str(resolved_call),
            "schema_path": str(resolved_schema),
            "instrument_type": instrument_type,
        },
    )


def interface_contract_conforms(
    response_path: PathLike,
    contract_path: PathLike,
    *,
    repo_root: Optional[Path] = None,
) -> PredicateResult:
    """
    Pass iff all .json files in *response_path* (direct children) conform
    to the JSON schema defined in *contract_path*.

    Contract (gate_rules_library_plan.md §4.2)
    -------------------------------------------
    Pass condition:
        * response_path exists and is a directory
        * contract_path exists and is a valid JSON schema object
        * every .json file in response_path (direct children) is valid JSON
          and conforms to the schema

    No JSON files
    -------------
    If response_path contains no .json files this predicate passes.
    Presence has been confirmed by a preceding ``dir_non_empty`` predicate
    in the gate sequence.  This predicate's responsibility is structure
    validation only.  This behaviour is explicit and tested.

    JSON Schema validation
    ----------------------
    Uses ``jsonschema`` 4.x.  An empty contract ``{}`` is a valid JSON
    Schema that accepts any JSON value, so the current placeholder contract
    will not block.  When the contract is populated, this predicate will
    enforce the schema.

    Failure categories
    ------------------
    ``MISSING_MANDATORY_INPUT``
        response_path does not exist or is not a directory; contract_path
        does not exist.
    ``MALFORMED_ARTIFACT``
        contract_path contains invalid JSON; or a response file contains
        invalid JSON.
    ``POLICY_VIOLATION``
        A response file is valid JSON but fails schema validation against
        the contract.

    Parameters
    ----------
    response_path:
        Directory containing response files to validate.
    contract_path:
        Path to the JSON Schema contract file.
    repo_root:
        Repository root for relative path resolution.
    """
    resolved_response = resolve_repo_path(response_path, repo_root)
    resolved_contract = resolve_repo_path(contract_path, repo_root)

    # Validate response directory
    if not resolved_response.exists():
        return PredicateResult(
            passed=False,
            failure_category=MISSING_MANDATORY_INPUT,
            reason=f"Response directory does not exist: {resolved_response}",
            details={"path": str(resolved_response)},
        )
    if not resolved_response.is_dir():
        return PredicateResult(
            passed=False,
            failure_category=MISSING_MANDATORY_INPUT,
            reason=(
                f"Expected a directory for response_path but found a file: "
                f"{resolved_response}"
            ),
            details={"path": str(resolved_response), "is_file": True},
        )

    # Read and parse contract
    if not resolved_contract.exists():
        return PredicateResult(
            passed=False,
            failure_category=MISSING_MANDATORY_INPUT,
            reason=f"Contract file does not exist: {resolved_contract}",
            details={"contract_path": str(resolved_contract)},
        )

    try:
        contract_text = resolved_contract.read_text(encoding="utf-8-sig")
        contract_schema = json.loads(contract_text)
    except UnicodeDecodeError as exc:
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=f"Contract file is not valid UTF-8: {exc}",
            details={
                "contract_path": str(resolved_contract),
                "encoding_error": str(exc),
            },
        )
    except json.JSONDecodeError as exc:
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=f"Contract file contains invalid JSON: {exc}",
            details={
                "contract_path": str(resolved_contract),
                "json_error": str(exc),
            },
        )

    # Scan direct-child .json files only
    json_files = sorted(
        child
        for child in resolved_response.iterdir()
        if child.is_file() and child.suffix.lower() == ".json"
    )

    # No JSON files: pass — presence confirmed by preceding dir_non_empty
    if not json_files:
        return PredicateResult(
            passed=True,
            details={
                "path": str(resolved_response),
                "contract_path": str(resolved_contract),
                "json_files_validated": 0,
                "note": (
                    "No .json files found in response directory.  "
                    "Presence is confirmed by a preceding dir_non_empty predicate."
                ),
            },
        )

    violations: list[dict] = []
    for json_file in json_files:
        try:
            content_text = json_file.read_text(encoding="utf-8-sig")
            content = json.loads(content_text)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            return PredicateResult(
                passed=False,
                failure_category=MALFORMED_ARTIFACT,
                reason=(
                    f"Response file contains invalid JSON or encoding error: "
                    f"{json_file}: {exc}"
                ),
                details={
                    "path": str(resolved_response),
                    "failed_file": str(json_file),
                    "error": str(exc),
                },
            )

        try:
            jsonschema.validate(instance=content, schema=contract_schema)
        except jsonschema.exceptions.ValidationError as exc:
            violations.append(
                {
                    "file": str(json_file),
                    "message": exc.message,
                    "schema_path": list(exc.absolute_schema_path),
                }
            )
        except jsonschema.exceptions.SchemaError as exc:
            return PredicateResult(
                passed=False,
                failure_category=MALFORMED_ARTIFACT,
                reason=(
                    f"Contract at {resolved_contract} is not a valid "
                    f"JSON Schema: {exc.message}"
                ),
                details={
                    "contract_path": str(resolved_contract),
                    "schema_error": exc.message,
                },
            )

    if violations:
        return PredicateResult(
            passed=False,
            failure_category=POLICY_VIOLATION,
            reason=(
                f"{len(violations)} response file(s) in {resolved_response} "
                f"do not conform to the interface contract at {resolved_contract}."
            ),
            details={
                "path": str(resolved_response),
                "contract_path": str(resolved_contract),
                "violations": violations,
            },
        )

    return PredicateResult(
        passed=True,
        details={
            "path": str(resolved_response),
            "contract_path": str(resolved_contract),
            "json_files_validated": len(json_files),
        },
    )


# ---------------------------------------------------------------------------
# §4.8 — Canonical field predicates
# ---------------------------------------------------------------------------


def risk_register_populated(
    path: PathLike,
    *,
    repo_root: Optional[Path] = None,
) -> PredicateResult:
    """
    Pass iff the canonical artifact at *path* contains a non-empty
    ``risk_register`` array where every entry has non-null ``likelihood``,
    ``impact``, and ``mitigation`` fields.

    Contract (gate_rules_library_plan.md §4.8)
    -------------------------------------------
    Pass condition:
        * valid JSON object
        * top-level ``risk_register`` array is non-empty
        * every entry has non-null ``likelihood``, ``impact``, ``mitigation``

    Canonical artifact
    ------------------
    This predicate targets
    ``implementation_architecture.json``
    (artifact_schema_specification.yaml §1.6).

    Failure categories
    ------------------
    ``MISSING_MANDATORY_INPUT``
        Path does not exist.
    ``MALFORMED_ARTIFACT``
        All sub-cases: field absent, not an array, empty, or an entry
        missing a required field.  These are artifact-completeness failures,
        not rule violations.

    Parameters
    ----------
    path:
        Path to the canonical implementation_architecture.json file.
    repo_root:
        Repository root for relative path resolution.
    """
    resolved = resolve_repo_path(path, repo_root)
    parsed, err = _read_json_object(resolved)
    if err is not None:
        return err

    if "risk_register" not in parsed:
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=f"Required field 'risk_register' is absent in {resolved}",
            details={"path": str(resolved), "missing_field": "risk_register"},
        )

    register = parsed["risk_register"]
    if not isinstance(register, list) or len(register) == 0:
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=(
                f"'risk_register' must be a non-empty array in {resolved}; "
                f"got {type(register).__name__} with "
                f"{len(register) if isinstance(register, list) else 'N/A'} entries"
            ),
            details={
                "path": str(resolved),
                "field": "risk_register",
                "value_type": type(register).__name__,
                "length": len(register) if isinstance(register, list) else None,
            },
        )

    required_entry_fields = ("likelihood", "impact", "mitigation")
    for idx, entry in enumerate(register):
        if not isinstance(entry, dict):
            return PredicateResult(
                passed=False,
                failure_category=MALFORMED_ARTIFACT,
                reason=(
                    f"risk_register entry at index {idx} is not an object "
                    f"(got {type(entry).__name__}) in {resolved}"
                ),
                details={"path": str(resolved), "entry_index": idx},
            )
        for field_name in required_entry_fields:
            if field_name not in entry or entry[field_name] is None:
                return PredicateResult(
                    passed=False,
                    failure_category=MALFORMED_ARTIFACT,
                    reason=(
                        f"risk_register entry at index {idx} has missing or null "
                        f"'{field_name}' in {resolved}"
                    ),
                    details={
                        "path": str(resolved),
                        "entry_index": idx,
                        "missing_or_null_field": field_name,
                    },
                )

    return PredicateResult(
        passed=True,
        details={"path": str(resolved), "risk_register_count": len(register)},
    )


def ethics_assessment_explicit(
    path: PathLike,
    *,
    repo_root: Optional[Path] = None,
) -> PredicateResult:
    """
    Pass iff the canonical artifact at *path* contains a non-null,
    non-placeholder ``ethics_assessment`` field.

    Contract (gate_rules_library_plan.md §4.8)
    -------------------------------------------
    Pass condition:
        * valid JSON object
        * top-level ``ethics_assessment`` field is present and non-null
        * if a string: not empty and not a sentinel placeholder
        * if an object: ``self_assessment_statement`` sub-field is
          present, non-null, non-empty, and not a sentinel placeholder

    Sentinel values
    ---------------
    ``_ETHICS_SENTINELS = {"N/A"}`` — sourced from
    artifact_schema_specification.yaml §1.6.  No other sentinels are
    defined.  Empty strings are checked separately.

    Sub-field requirement
    ---------------------
    artifact_schema_specification.yaml §1.6 states:
    "This is the field that ethics_assessment_explicit verifies is
    present, non-null, not empty, and not a placeholder."
    The field is ``ethics_assessment.self_assessment_statement``.

    Canonical artifact
    ------------------
    This predicate targets ``implementation_architecture.json``
    (artifact_schema_specification.yaml §1.6).

    Failure categories
    ------------------
    ``MISSING_MANDATORY_INPUT``
        Path does not exist.
    ``MALFORMED_ARTIFACT``
        Field absent, null, empty string, or object with missing/null/empty
        self_assessment_statement.
    ``POLICY_VIOLATION``
        Field value (or self_assessment_statement) equals a sentinel.

    Parameters
    ----------
    path:
        Path to the canonical implementation_architecture.json file.
    repo_root:
        Repository root for relative path resolution.
    """
    resolved = resolve_repo_path(path, repo_root)
    parsed, err = _read_json_object(resolved)
    if err is not None:
        return err

    if "ethics_assessment" not in parsed:
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=f"Required field 'ethics_assessment' is absent in {resolved}",
            details={"path": str(resolved), "missing_field": "ethics_assessment"},
        )

    value = parsed["ethics_assessment"]

    if value is None:
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=f"Field 'ethics_assessment' is null in {resolved}",
            details={"path": str(resolved), "null_field": "ethics_assessment"},
        )

    # Handle mistaken string assignment of this object field
    if isinstance(value, str):
        if value.strip() == "":
            return PredicateResult(
                passed=False,
                failure_category=MALFORMED_ARTIFACT,
                reason=(
                    f"Field 'ethics_assessment' is an empty string in {resolved}; "
                    "must be a non-empty non-placeholder value"
                ),
                details={"path": str(resolved), "field": "ethics_assessment"},
            )
        if value in _ETHICS_SENTINELS:
            return PredicateResult(
                passed=False,
                failure_category=POLICY_VIOLATION,
                reason=(
                    f"Field 'ethics_assessment' contains placeholder sentinel "
                    f"{value!r} in {resolved}.  Sentinels: {sorted(_ETHICS_SENTINELS)}"
                ),
                details={
                    "path": str(resolved),
                    "field": "ethics_assessment",
                    "sentinel_value": value,
                    "sentinel_set": sorted(_ETHICS_SENTINELS),
                },
            )
        # Non-empty, non-sentinel string: pass
        return PredicateResult(
            passed=True,
            details={"path": str(resolved), "field": "ethics_assessment"},
        )

    # Object value: check self_assessment_statement sub-field
    if isinstance(value, dict):
        if "self_assessment_statement" not in value:
            return PredicateResult(
                passed=False,
                failure_category=MALFORMED_ARTIFACT,
                reason=(
                    f"'ethics_assessment.self_assessment_statement' is absent "
                    f"in {resolved}"
                ),
                details={
                    "path": str(resolved),
                    "missing_subfield": "self_assessment_statement",
                },
            )
        sub = value["self_assessment_statement"]
        if sub is None:
            return PredicateResult(
                passed=False,
                failure_category=MALFORMED_ARTIFACT,
                reason=(
                    f"'ethics_assessment.self_assessment_statement' is null "
                    f"in {resolved}"
                ),
                details={
                    "path": str(resolved),
                    "null_subfield": "self_assessment_statement",
                },
            )
        if not isinstance(sub, str) or sub.strip() == "":
            return PredicateResult(
                passed=False,
                failure_category=MALFORMED_ARTIFACT,
                reason=(
                    f"'ethics_assessment.self_assessment_statement' is empty "
                    f"in {resolved}"
                ),
                details={
                    "path": str(resolved),
                    "empty_subfield": "self_assessment_statement",
                },
            )
        if sub in _ETHICS_SENTINELS:
            return PredicateResult(
                passed=False,
                failure_category=POLICY_VIOLATION,
                reason=(
                    f"'ethics_assessment.self_assessment_statement' contains "
                    f"placeholder sentinel {sub!r} in {resolved}.  "
                    f"Sentinels: {sorted(_ETHICS_SENTINELS)}"
                ),
                details={
                    "path": str(resolved),
                    "sentinel_subfield": "self_assessment_statement",
                    "sentinel_value": sub,
                    "sentinel_set": sorted(_ETHICS_SENTINELS),
                },
            )
        return PredicateResult(
            passed=True,
            details={"path": str(resolved), "field": "ethics_assessment"},
        )

    # Unexpected type (list, int, etc.): treat as malformed
    return PredicateResult(
        passed=False,
        failure_category=MALFORMED_ARTIFACT,
        reason=(
            f"Field 'ethics_assessment' has unexpected type "
            f"{type(value).__name__!r} in {resolved}; expected object or string"
        ),
        details={
            "path": str(resolved),
            "unexpected_type": type(value).__name__,
        },
    )


def governance_matrix_present(
    path: PathLike,
    *,
    repo_root: Optional[Path] = None,
) -> PredicateResult:
    """
    Pass iff the canonical artifact at *path* contains a non-empty
    ``governance_matrix`` field.

    Contract (gate_rules_library_plan.md §4.8)
    -------------------------------------------
    Pass condition:
        * valid JSON object
        * top-level ``governance_matrix`` exists and is non-null
        * contains at least one non-empty entry

    Canonical artifact
    ------------------
    This predicate targets ``implementation_architecture.json``
    (artifact_schema_specification.yaml §1.6).

    Failure categories
    ------------------
    ``MISSING_MANDATORY_INPUT``
        Path does not exist.
    ``MALFORMED_ARTIFACT``
        Field absent, null, or empty array/object.

    Parameters
    ----------
    path:
        Path to the canonical implementation_architecture.json file.
    repo_root:
        Repository root for relative path resolution.
    """
    resolved = resolve_repo_path(path, repo_root)
    parsed, err = _read_json_object(resolved)
    if err is not None:
        return err

    if "governance_matrix" not in parsed:
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=f"Required field 'governance_matrix' is absent in {resolved}",
            details={"path": str(resolved), "missing_field": "governance_matrix"},
        )

    matrix = parsed["governance_matrix"]

    if matrix is None:
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=f"Field 'governance_matrix' is null in {resolved}",
            details={"path": str(resolved), "null_field": "governance_matrix"},
        )

    if not isinstance(matrix, (list, dict)):
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=(
                f"Field 'governance_matrix' must be an array or object; "
                f"got {type(matrix).__name__} in {resolved}"
            ),
            details={
                "path": str(resolved),
                "unexpected_type": type(matrix).__name__,
            },
        )

    if len(matrix) == 0:
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=(
                f"Field 'governance_matrix' is empty (zero entries) in {resolved}"
            ),
            details={"path": str(resolved), "field": "governance_matrix", "length": 0},
        )

    return PredicateResult(
        passed=True,
        details={
            "path": str(resolved),
            "governance_matrix_entries": len(matrix),
        },
    )


def no_blocking_inconsistencies(
    path: PathLike,
    *,
    repo_root: Optional[Path] = None,
) -> PredicateResult:
    """
    Pass iff the canonical artifact at *path* has no blocking inconsistencies
    with ``resolution == "unresolved"``.

    Contract (gate_rules_library_plan.md §4.8)
    -------------------------------------------
    Pass condition:
        * valid JSON object
        * ``blocking_inconsistencies`` is absent, or present with no entry
          where ``resolution == "unresolved"``

    Canonical artifact
    ------------------
    This predicate targets ``budget_gate_assessment.json``
    (artifact_schema_specification.yaml §1.7).

    Failure categories
    ------------------
    ``MISSING_MANDATORY_INPUT``
        Path does not exist.
    ``MALFORMED_ARTIFACT``
        Invalid JSON, non-object JSON, or ``blocking_inconsistencies`` is
        not an array.
    ``POLICY_VIOLATION``
        The array exists and at least one entry has
        ``resolution: "unresolved"``.  Structurally valid but violates the
        workflow rule that all blocking inconsistencies must be resolved.

    Parameters
    ----------
    path:
        Path to the canonical budget_gate_assessment.json file.
    repo_root:
        Repository root for relative path resolution.
    """
    resolved = resolve_repo_path(path, repo_root)
    parsed, err = _read_json_object(resolved)
    if err is not None:
        return err

    # Absent field: no inconsistencies — pass
    if "blocking_inconsistencies" not in parsed:
        return PredicateResult(
            passed=True,
            details={"path": str(resolved), "blocking_inconsistencies": "absent"},
        )

    items = parsed["blocking_inconsistencies"]
    if not isinstance(items, list):
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=(
                f"'blocking_inconsistencies' must be an array; "
                f"got {type(items).__name__} in {resolved}"
            ),
            details={
                "path": str(resolved),
                "unexpected_type": type(items).__name__,
            },
        )

    unresolved = [
        entry
        for entry in items
        if isinstance(entry, dict) and entry.get("resolution") == "unresolved"
    ]

    if unresolved:
        return PredicateResult(
            passed=False,
            failure_category=POLICY_VIOLATION,
            reason=(
                f"{len(unresolved)} unresolved blocking inconsistency(ies) in "
                f"{resolved}.  All must be resolved before this gate can pass."
            ),
            details={
                "path": str(resolved),
                "unresolved_count": len(unresolved),
                "unresolved_ids": [
                    e.get("inconsistency_id", f"<index {i}>")
                    for i, e in enumerate(unresolved)
                ],
            },
        )

    return PredicateResult(
        passed=True,
        details={
            "path": str(resolved),
            "blocking_inconsistencies_count": len(items),
        },
    )


def budget_gate_confirmation_present(
    path: PathLike,
    *,
    repo_root: Optional[Path] = None,
) -> PredicateResult:
    """
    Pass iff the canonical budget gate artifact at *path* declares
    ``gate_pass_declaration == "pass"``.

    Contract (gate_rules_library_plan.md §4.8)
    -------------------------------------------
    Pass condition:
        * valid JSON object
        * top-level ``gate_pass_declaration`` equals ``"pass"``

    Canonical artifact
    ------------------
    This predicate targets ``budget_gate_assessment.json``
    (artifact_schema_specification.yaml §1.7).

    Failure categories
    ------------------
    ``MISSING_MANDATORY_INPUT``
        Path does not exist.
    ``MALFORMED_ARTIFACT``
        Invalid JSON, non-object JSON, or ``gate_pass_declaration`` field
        absent or null.
    ``POLICY_VIOLATION``
        Field is present but value is not ``"pass"``.  The budget gate
        has been explicitly failed or holds an unknown value; Phase 8 is
        blocked (CLAUDE.md §8.4, §13.4).

    Parameters
    ----------
    path:
        Path to the canonical budget_gate_assessment.json file.
    repo_root:
        Repository root for relative path resolution.
    """
    resolved = resolve_repo_path(path, repo_root)
    parsed, err = _read_json_object(resolved)
    if err is not None:
        return err

    if "gate_pass_declaration" not in parsed:
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=(
                f"Required field 'gate_pass_declaration' is absent in {resolved}"
            ),
            details={"path": str(resolved), "missing_field": "gate_pass_declaration"},
        )

    declaration = parsed["gate_pass_declaration"]
    if declaration is None:
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=f"Field 'gate_pass_declaration' is null in {resolved}",
            details={"path": str(resolved), "null_field": "gate_pass_declaration"},
        )

    if declaration != "pass":
        return PredicateResult(
            passed=False,
            failure_category=POLICY_VIOLATION,
            reason=(
                f"Budget gate declaration is {declaration!r} (expected 'pass') "
                f"in {resolved}.  Phase 8 is blocked until the budget gate passes."
            ),
            details={
                "path": str(resolved),
                "gate_pass_declaration": declaration,
                "expected": "pass",
            },
        )

    return PredicateResult(
        passed=True,
        details={"path": str(resolved), "gate_pass_declaration": "pass"},
    )


def findings_categorised_by_severity(
    path: PathLike,
    *,
    repo_root: Optional[Path] = None,
) -> PredicateResult:
    """
    Pass iff every entry in the ``findings`` array has a valid severity.

    Contract (gate_rules_library_plan.md §4.8)
    -------------------------------------------
    Pass condition:
        * valid JSON object
        * top-level ``findings`` array exists
        * every entry has a non-null ``severity`` field drawn from
          ``{"critical", "major", "minor"}``

    Severity enum
    -------------
    Sourced from artifact_schema_specification.yaml §2.2 review_packet
    findings.severity enum:
        ``_FINDING_SEVERITIES = {"critical", "major", "minor"}``

    Canonical artifact
    ------------------
    This predicate targets ``review_packet.json``
    (artifact_schema_specification.yaml §2.2).

    Failure categories
    ------------------
    ``MISSING_MANDATORY_INPUT``
        Path does not exist.
    ``MALFORMED_ARTIFACT``
        ``findings`` absent, not an array, or entry has absent/null severity.
    ``POLICY_VIOLATION``
        Entry ``severity`` is present but outside the allowed set.

    Parameters
    ----------
    path:
        Path to the canonical review_packet.json file.
    repo_root:
        Repository root for relative path resolution.
    """
    resolved = resolve_repo_path(path, repo_root)
    parsed, err = _read_json_object(resolved)
    if err is not None:
        return err

    if "findings" not in parsed:
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=f"Required field 'findings' is absent in {resolved}",
            details={"path": str(resolved), "missing_field": "findings"},
        )

    findings = parsed["findings"]
    if not isinstance(findings, list):
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=(
                f"Field 'findings' must be an array; "
                f"got {type(findings).__name__} in {resolved}"
            ),
            details={"path": str(resolved), "unexpected_type": type(findings).__name__},
        )

    for idx, entry in enumerate(findings):
        if not isinstance(entry, dict):
            return PredicateResult(
                passed=False,
                failure_category=MALFORMED_ARTIFACT,
                reason=(
                    f"findings entry at index {idx} is not an object "
                    f"(got {type(entry).__name__}) in {resolved}"
                ),
                details={"path": str(resolved), "entry_index": idx},
            )

        if "severity" not in entry or entry["severity"] is None:
            return PredicateResult(
                passed=False,
                failure_category=MALFORMED_ARTIFACT,
                reason=(
                    f"findings entry at index {idx} has missing or null "
                    f"'severity' in {resolved}"
                ),
                details={"path": str(resolved), "entry_index": idx},
            )

        severity = entry["severity"]
        if severity not in _FINDING_SEVERITIES:
            return PredicateResult(
                passed=False,
                failure_category=POLICY_VIOLATION,
                reason=(
                    f"findings entry at index {idx} has invalid severity "
                    f"{severity!r} in {resolved}.  "
                    f"Allowed: {sorted(_FINDING_SEVERITIES)}"
                ),
                details={
                    "path": str(resolved),
                    "entry_index": idx,
                    "invalid_severity": severity,
                    "allowed_severities": sorted(_FINDING_SEVERITIES),
                },
            )

    return PredicateResult(
        passed=True,
        details={"path": str(resolved), "findings_count": len(findings)},
    )


def revision_action_list_present(
    path: PathLike,
    *,
    repo_root: Optional[Path] = None,
) -> PredicateResult:
    """
    Pass iff the canonical artifact at *path* contains a non-empty
    ``revision_actions`` array.

    Contract (gate_rules_library_plan.md §4.8)
    -------------------------------------------
    Pass condition:
        * valid JSON object
        * top-level ``revision_actions`` array exists and is non-empty

    Canonical artifact
    ------------------
    This predicate targets ``review_packet.json``
    (artifact_schema_specification.yaml §2.2).

    Failure categories
    ------------------
    ``MISSING_MANDATORY_INPUT``
        Path does not exist.
    ``MALFORMED_ARTIFACT``
        Field absent, not an array, or empty array.

    Parameters
    ----------
    path:
        Path to the canonical review_packet.json file.
    repo_root:
        Repository root for relative path resolution.
    """
    resolved = resolve_repo_path(path, repo_root)
    parsed, err = _read_json_object(resolved)
    if err is not None:
        return err

    if "revision_actions" not in parsed:
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=f"Required field 'revision_actions' is absent in {resolved}",
            details={"path": str(resolved), "missing_field": "revision_actions"},
        )

    actions = parsed["revision_actions"]
    if not isinstance(actions, list):
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=(
                f"Field 'revision_actions' must be an array; "
                f"got {type(actions).__name__} in {resolved}"
            ),
            details={"path": str(resolved), "unexpected_type": type(actions).__name__},
        )

    if len(actions) == 0:
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=f"Field 'revision_actions' is an empty array in {resolved}",
            details={"path": str(resolved), "field": "revision_actions", "length": 0},
        )

    return PredicateResult(
        passed=True,
        details={"path": str(resolved), "revision_actions_count": len(actions)},
    )


def all_critical_revisions_resolved(
    path: PathLike,
    *,
    repo_root: Optional[Path] = None,
) -> PredicateResult:
    """
    Pass iff no ``revision_actions`` entry is critical, unresolved, and
    lacks a non-empty reason.

    Contract (gate_rules_library_plan.md §4.8)
    -------------------------------------------
    Pass condition:
        * valid JSON object
        * no ``revision_actions`` entry has ALL of:
            - ``severity == "critical"``
            - ``status == "unresolved"``
            - ``reason`` absent or empty

    Per the plan and artifact_schema_specification.yaml §1.8:
    unresolved critical items are acceptable ONLY when explicitly logged
    as unresolvable with a non-empty ``reason`` field.

    Canonical artifact
    ------------------
    This predicate targets ``drafting_review_status.json``
    (artifact_schema_specification.yaml §1.8).

    Failure categories
    ------------------
    ``MISSING_MANDATORY_INPUT``
        Path does not exist.
    ``MALFORMED_ARTIFACT``
        Invalid JSON or non-object JSON.
    ``POLICY_VIOLATION``
        One or more critical revision actions remain unresolved without a
        stated reason.

    Parameters
    ----------
    path:
        Path to the canonical drafting_review_status.json file.
    repo_root:
        Repository root for relative path resolution.
    """
    resolved = resolve_repo_path(path, repo_root)
    parsed, err = _read_json_object(resolved)
    if err is not None:
        return err

    # Absent field: nothing to resolve — pass
    actions = parsed.get("revision_actions", [])
    if not isinstance(actions, list):
        return PredicateResult(
            passed=True,
            details={
                "path": str(resolved),
                "note": "revision_actions is not a list; no critical resolution check performed",
            },
        )

    violations: list[str] = []
    for idx, entry in enumerate(actions):
        if not isinstance(entry, dict):
            continue
        if (
            entry.get("severity") == "critical"
            and entry.get("status") == "unresolved"
        ):
            reason = entry.get("reason")
            if not reason or (isinstance(reason, str) and not reason.strip()):
                violations.append(
                    str(entry.get("action_id", f"<index {idx}>"))
                )

    if violations:
        return PredicateResult(
            passed=False,
            failure_category=POLICY_VIOLATION,
            reason=(
                f"{len(violations)} critical revision action(s) are unresolved "
                f"without a non-empty reason in {resolved}: {violations}"
            ),
            details={
                "path": str(resolved),
                "unresolved_critical_ids": violations,
            },
        )

    return PredicateResult(
        passed=True,
        details={"path": str(resolved)},
    )


def checkpoint_published(
    path: PathLike,
    *,
    repo_root: Optional[Path] = None,
) -> PredicateResult:
    """
    Pass iff the checkpoint artifact at *path* exists, is valid JSON, and
    contains ``status == "published"``.

    Contract (gate_rules_library_plan.md §4.8)
    -------------------------------------------
    Pass condition:
        * file exists
        * valid JSON object
        * ``status == "published"``

    Canonical artifact
    ------------------
    This predicate targets ``phase8_checkpoint.json``
    (artifact_schema_specification.yaml §1.9).

    Failure categories
    ------------------
    ``MISSING_MANDATORY_INPUT``
        Path does not exist.
    ``MALFORMED_ARTIFACT``
        Invalid JSON, non-object JSON, or ``status`` field absent or null.
    ``POLICY_VIOLATION``
        Field ``status`` is present but not ``"published"``.

    Parameters
    ----------
    path:
        Path to the canonical phase8_checkpoint.json file.
    repo_root:
        Repository root for relative path resolution.
    """
    resolved = resolve_repo_path(path, repo_root)
    parsed, err = _read_json_object(resolved)
    if err is not None:
        return err

    if "status" not in parsed:
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=f"Required field 'status' is absent in {resolved}",
            details={"path": str(resolved), "missing_field": "status"},
        )

    status = parsed["status"]
    if status is None:
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=f"Field 'status' is null in {resolved}",
            details={"path": str(resolved), "null_field": "status"},
        )

    if status != "published":
        return PredicateResult(
            passed=False,
            failure_category=POLICY_VIOLATION,
            reason=(
                f"Checkpoint status is {status!r} (expected 'published') "
                f"in {resolved}"
            ),
            details={
                "path": str(resolved),
                "status": status,
                "expected": "published",
            },
        )

    return PredicateResult(
        passed=True,
        details={"path": str(resolved), "status": "published"},
    )
