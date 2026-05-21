"""
Step 6 — Source reference predicates.

Implements the two source-reference traceability predicates defined in
gate_rules_library_plan.md §4.3:

    source_refs_present(path)
    all_mappings_have_source_refs(path)

These predicates enforce traceability-rule compliance: they verify that
every relevant item in a JSON artifact carries a non-empty source reference,
confirming that extracted facts and mappings can be traced back to their
authoritative source documents.

Failure category used: ``POLICY_VIOLATION`` for absent/empty source
reference fields (structurally valid artifact, traceability rule violated),
``MALFORMED_ARTIFACT`` for structural problems (bad JSON, unexpected types),
and ``MISSING_MANDATORY_INPUT`` for absent files.

---------------------------------------------------------------------------
Traversal strategies
---------------------------------------------------------------------------

source_refs_present — bounded traversal (§4.3)
-----------------------------------------------
Operates on Tier 2B extracted files (call_constraints.json,
expected_outcomes.json, expected_impacts.json, scope_requirements.json,
eligibility_conditions.json, evaluation_priority_weights.json), all of
which are currently empty placeholders ({}).  Based on the plan §4.3 and
the call_analysis_summary evaluation_matrix item schema (source_section +
source_document), these files will contain JSON objects or arrays whose
items carry a ``source_section`` field identifying the work programme
section from which the item was extracted.

Supported structures and traversal rules:

* **Array at top level**: each element is treated as a relevant item.
  Each element must be a dict with a non-empty ``source_ref`` OR
  ``source_section`` field.  An empty array passes (vacuous truth; the
  preceding ``non_empty_json`` predicate in the gate sequence would have
  already failed on a truly empty file).

* **Object/dict at top level** — two sub-cases:
  1. **Single-item object**: the object itself carries ``source_ref`` or
     ``source_section`` at the top level.  Treated as one item; checked
     directly.
  2. **Dict-of-entries object**: the object has no ``source_ref`` or
     ``source_section`` at the top level but contains dict values.  Each
     top-level value that is a dict is treated as an entry and must carry
     either field.  Top-level values that are not dicts are skipped (they
     are presumed to be metadata, not item entries).

This bounded strategy is the narrowest correct interpretation: no
recursive descent, no cross-file lookups, no schema inference.  When the
Tier 2B extracted files are populated, the actual structure must be
validated against this interpretation and the predicate updated if the
structure differs.

all_mappings_have_source_refs — bounded traversal (§4.3)
---------------------------------------------------------
Operates on ``docs/tier3_project_instantiation/call_binding/
topic_mapping.json`` (gate g03_p03).  This file records how the project
concept maps to the call topic, with each mapping entry requiring both:

* ``tier2b_source_ref`` — points back to the work programme / call
  extract section (Tier 2B) that defines the topic element being mapped
* ``tier3_evidence_ref`` — points to the project-specific data (Tier 3)
  that evidences the mapping

This two-channel traceability requirement is derived from the
``concept_refinement_summary.topic_mapping_rationale`` item schema in
``artifact_schema_specification.yaml`` §1.2, which lists both fields as
required.  topic_mapping.json is the Tier 3 source that feeds this
rationale.

Supported structures:

* **Array at top level**: each element is a mapping entry and must be a
  dict with non-empty ``tier2b_source_ref`` AND non-empty
  ``tier3_evidence_ref``.  An empty array passes (vacuous truth).

* **Object/dict at top level** — two sub-cases:
  1. **Single-entry object**: the dict itself carries both required fields
     at the top level → treated as a single mapping entry.
  2. **Dict-of-entries object**: no required fields at top level; each
     top-level value that is a dict is treated as an entry and must carry
     both fields.  Non-dict values are skipped as metadata.

---------------------------------------------------------------------------
Non-empty check for source reference values
---------------------------------------------------------------------------
A source reference field is considered **present and valid** only when:

* the field exists in the entry
* the value is not null
* if the value is a string: it is not blank/whitespace-only

Any other type (int, list, dict) is treated as an acceptable non-empty
reference value (the predicate enforces presence and non-blankness, not
type conformance — type conformance is for schema predicates).

This rule is documented and tested.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Union

from runner.paths import resolve_repo_path
from runner.predicates.types import (
    MALFORMED_ARTIFACT,
    MISSING_MANDATORY_INPUT,
    POLICY_VIOLATION,
    PredicateResult,
)

PathLike = Union[str, Path]

# ---------------------------------------------------------------------------
# Source-reference field names used across predicates
# ---------------------------------------------------------------------------

_SOURCE_REF_FIELDS: tuple[str, ...] = ("source_ref", "source_section")
"""
Accepted source-reference field names for source_refs_present.
An entry passes if it has at least one of these with a non-empty value.
Source: gate_rules_library_plan.md §4.3 function contract.
"""

_TIER2B_REF_FIELD: str = "tier2b_source_ref"
_TIER3_REF_FIELD: str = "tier3_evidence_ref"
"""
Required fields for all_mappings_have_source_refs.
Source: artifact_schema_specification.yaml §1.2
(concept_refinement_summary.topic_mapping_rationale item schema),
which requires both tier2b_source_ref and tier3_evidence_ref.
"""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _read_json(
    resolved: Path,
) -> tuple[Optional[object], Optional[PredicateResult]]:
    """
    Read *resolved* as UTF-8 JSON and return ``(parsed, None)`` on success.
    On any failure return ``(None, PredicateResult(...))``.

    Unlike the Step 5 ``_read_json_object`` helper this function accepts
    any JSON value (array or object) because ``source_refs_present`` must
    handle both.

    Failure categories:
    * ``MISSING_MANDATORY_INPUT`` — path absent or is a directory
    * ``MALFORMED_ARTIFACT``      — encoding error or invalid JSON
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

    return parsed, None


def _ref_value_is_present(value: object) -> bool:
    """
    Return True iff *value* counts as a present, non-blank source reference.

    Rules (see module docstring "Non-empty check" section):
    * None  → absent
    * str   → must be non-blank (strip() != "")
    * any other type → present (int, list, dict are acceptable non-empty values;
      type conformance is enforced by schema predicates, not source-ref predicates)
    """
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    return True


def _has_any_source_ref(entry: dict) -> bool:
    """
    Return True iff *entry* has at least one of ``_SOURCE_REF_FIELDS``
    with a present (non-null, non-blank) value.
    """
    for field in _SOURCE_REF_FIELDS:
        if field in entry and _ref_value_is_present(entry[field]):
            return True
    return False


def _extract_entries_for_source_ref(
    parsed: object,
    resolved: Path,
) -> tuple[Optional[list[tuple[str, dict]]], Optional[PredicateResult]]:
    """
    Apply the bounded traversal strategy for ``source_refs_present`` and
    return a list of ``(label, entry_dict)`` pairs, or a failing
    ``PredicateResult`` if the structure is not supported.

    See module docstring for the full traversal strategy.

    Returns:
        (entries, None)   — list may be empty (vacuous pass)
        (None, result)    — structural failure; result carries the error
    """
    if isinstance(parsed, list):
        # Array form: each element is an item
        entries = []
        for idx, element in enumerate(parsed):
            if not isinstance(element, dict):
                return None, PredicateResult(
                    passed=False,
                    failure_category=MALFORMED_ARTIFACT,
                    reason=(
                        f"Array entry at index {idx} is not an object "
                        f"(got {type(element).__name__}) in {resolved}.  "
                        "Each array element must be a JSON object containing "
                        "source reference fields."
                    ),
                    details={
                        "path": str(resolved),
                        "entry_index": idx,
                        "entry_type": type(element).__name__,
                    },
                )
            entries.append((f"[{idx}]", element))
        return entries, None

    if isinstance(parsed, dict):
        # Single-item object: the dict itself has source_ref or source_section
        if any(f in parsed for f in _SOURCE_REF_FIELDS):
            return [("<root>", parsed)], None
        # Dict-of-entries: each top-level value that is a dict is an entry
        entries = [
            (key, val)
            for key, val in parsed.items()
            if isinstance(val, dict)
        ]
        return entries, None

    # Unsupported top-level type (scalar, etc.)
    return None, PredicateResult(
        passed=False,
        failure_category=MALFORMED_ARTIFACT,
        reason=(
            f"Unsupported top-level JSON type {type(parsed).__name__!r} in "
            f"{resolved}.  source_refs_present requires an array or object."
        ),
        details={
            "path": str(resolved),
            "parsed_type": type(parsed).__name__,
        },
    )


def _extract_mapping_entries(
    parsed: object,
    resolved: Path,
) -> tuple[Optional[list[tuple[str, dict]]], Optional[PredicateResult]]:
    """
    Apply the bounded traversal strategy for ``all_mappings_have_source_refs``
    and return a list of ``(label, entry_dict)`` pairs, or a failing
    ``PredicateResult``.

    See module docstring for the full traversal strategy.
    """
    if isinstance(parsed, list):
        entries = []
        for idx, element in enumerate(parsed):
            if not isinstance(element, dict):
                return None, PredicateResult(
                    passed=False,
                    failure_category=MALFORMED_ARTIFACT,
                    reason=(
                        f"Mapping array entry at index {idx} is not an object "
                        f"(got {type(element).__name__}) in {resolved}.  "
                        "Each mapping entry must be a JSON object."
                    ),
                    details={
                        "path": str(resolved),
                        "entry_index": idx,
                        "entry_type": type(element).__name__,
                    },
                )
            entries.append((f"[{idx}]", element))
        return entries, None

    if isinstance(parsed, dict):
        # Single-entry object: the dict itself carries the required fields
        if _TIER2B_REF_FIELD in parsed or _TIER3_REF_FIELD in parsed:
            return [("<root>", parsed)], None
        # Dict-of-entries: each top-level value that is a dict is an entry
        entries = [
            (key, val)
            for key, val in parsed.items()
            if isinstance(val, dict)
        ]
        return entries, None

    return None, PredicateResult(
        passed=False,
        failure_category=MALFORMED_ARTIFACT,
        reason=(
            f"Unsupported top-level JSON type {type(parsed).__name__!r} in "
            f"{resolved}.  all_mappings_have_source_refs requires an array "
            "or object."
        ),
        details={
            "path": str(resolved),
            "parsed_type": type(parsed).__name__,
        },
    )


# ---------------------------------------------------------------------------
# §4.3 — Source reference predicates
# ---------------------------------------------------------------------------


def source_refs_present(
    path: PathLike,
    *,
    repo_root: Optional[Path] = None,
) -> PredicateResult:
    """
    Pass iff every relevant item in the artifact at *path* contains a
    non-empty ``source_ref`` or ``source_section`` field.

    Contract (gate_rules_library_plan.md §4.3)
    -------------------------------------------
    Pass condition:
        * path exists and is a readable JSON file
        * the JSON value is an array or object (see traversal strategy below)
        * every relevant entry has a non-empty ``source_ref`` OR
          ``source_section`` field

    Traversal strategy
    ------------------
    See module docstring for the full bounded traversal rules.  Summary:

    * Array → each element is a relevant item (must be a dict).
    * Object with ``source_ref`` / ``source_section`` at top level → single
      item; checked directly.
    * Object without those fields → each top-level dict value is an entry.
    * Empty arrays / objects with no dict values → pass (vacuous truth;
      ``non_empty_json`` in the gate sequence catches truly empty files).

    Source-reference validity
    -------------------------
    A field counts as present iff it is non-null and, when a string, is
    not whitespace-only.  See ``_ref_value_is_present``.

    Accepted field names: ``source_ref``, ``source_section``.

    Gate usage (gate_rules_library_plan.md §5 phase_01_gate)
    ---------------------------------------------------------
    g02_p07 – g02_p12: applied to all six Tier 2B extracted JSON files
    (call_constraints, expected_outcomes, expected_impacts,
    scope_requirements, eligibility_conditions,
    evaluation_priority_weights).

    Failure categories
    ------------------
    ``MISSING_MANDATORY_INPUT``
        Path does not exist.
    ``MALFORMED_ARTIFACT``
        Invalid JSON, unsupported top-level type, or an array element that
        is not a dict.
    ``POLICY_VIOLATION``
        A relevant entry has no ``source_ref`` or ``source_section`` field,
        or the field value is null/blank.  Constitutional basis:
        CLAUDE.md §5 Tier 2B Constraints — "faithfully represent source
        work programme documents"; §9.4 — traceability to source documents
        must be written to Tier 4.

    Parameters
    ----------
    path:
        Repository-relative or absolute path to the Tier 2B extracted JSON
        file (or any JSON file whose items must carry source references).
    repo_root:
        Repository root for relative path resolution.
    """
    resolved = resolve_repo_path(path, repo_root)
    parsed, err = _read_json(resolved)
    if err is not None:
        return err

    entries, err = _extract_entries_for_source_ref(parsed, resolved)
    if err is not None:
        return err

    # Vacuous pass: no entries to check (empty array or object with no dict values)
    if not entries:
        return PredicateResult(
            passed=True,
            details={
                "path": str(resolved),
                "entries_checked": 0,
                "note": "No relevant entries found; vacuous pass.",
            },
        )

    missing_refs: list[str] = []
    for label, entry in entries:
        if not _has_any_source_ref(entry):
            missing_refs.append(label)

    if missing_refs:
        return PredicateResult(
            passed=False,
            failure_category=POLICY_VIOLATION,
            reason=(
                f"{len(missing_refs)} entry(ies) in {resolved} have no "
                f"non-empty 'source_ref' or 'source_section' field: "
                f"{missing_refs}.  "
                "All extracted items must carry a source section reference "
                "for traceability (gate_rules_library_plan.md §4.3)."
            ),
            details={
                "path": str(resolved),
                "entries_checked": len(entries),
                "missing_source_ref_entries": missing_refs,
                "accepted_fields": list(_SOURCE_REF_FIELDS),
            },
        )

    return PredicateResult(
        passed=True,
        details={
            "path": str(resolved),
            "entries_checked": len(entries),
        },
    )


def all_mappings_have_source_refs(
    path: PathLike,
    *,
    repo_root: Optional[Path] = None,
) -> PredicateResult:
    """
    Pass iff every mapping entry in the artifact at *path* carries both a
    Tier 2B source reference (``tier2b_source_ref``) and a Tier 3 project
    evidence source (``tier3_evidence_ref``).

    Contract (gate_rules_library_plan.md §4.3)
    -------------------------------------------
    Pass condition:
        * path exists and is a readable JSON file
        * the JSON value is an array or object (see traversal strategy)
        * every mapping entry has a non-empty ``tier2b_source_ref`` AND
          a non-empty ``tier3_evidence_ref``

    Required fields per entry
    -------------------------
    ``tier2b_source_ref``
        Points to the work programme / call extract section (Tier 2B)
        that defines the topic element being mapped.  Sourced from
        artifact_schema_specification.yaml §1.2
        (concept_refinement_summary.topic_mapping_rationale item schema).

    ``tier3_evidence_ref``
        Points to the project-specific data (Tier 3) that evidences the
        mapping.  Sourced from the same schema.

    Traversal strategy
    ------------------
    See module docstring for the full bounded traversal rules.  Summary:

    * Array → each element is a mapping entry (must be a dict).
    * Object with ``tier2b_source_ref`` or ``tier3_evidence_ref`` at top
      level → single entry; checked directly.
    * Object without those fields → each top-level dict value is an entry.
    * Empty structures → pass (vacuous truth).

    Source-reference validity
    -------------------------
    A field counts as present iff it is non-null and, when a string, is
    not whitespace-only.  See ``_ref_value_is_present``.

    Gate usage (gate_rules_library_plan.md §5 phase_02_gate)
    ---------------------------------------------------------
    g03_p03: applied to
    ``docs/tier3_project_instantiation/call_binding/topic_mapping.json``

    Failure categories
    ------------------
    ``MISSING_MANDATORY_INPUT``
        Path does not exist.
    ``MALFORMED_ARTIFACT``
        Invalid JSON, unsupported top-level type, or an array element that
        is not a dict.
    ``POLICY_VIOLATION``
        A mapping entry is missing ``tier2b_source_ref``,
        ``tier3_evidence_ref``, or either value is null/blank.
        Constitutional basis: CLAUDE.md §5 Tier 2B/3 Constraints —
        all call constraints and project facts used in deliverables must be
        traceable; §10.5 — agents must identify source for every material
        claim.

    Parameters
    ----------
    path:
        Repository-relative or absolute path to topic_mapping.json or any
        JSON file whose mapping entries must carry two-channel source refs.
    repo_root:
        Repository root for relative path resolution.
    """
    resolved = resolve_repo_path(path, repo_root)
    parsed, err = _read_json(resolved)
    if err is not None:
        return err

    entries, err = _extract_mapping_entries(parsed, resolved)
    if err is not None:
        return err

    if not entries:
        return PredicateResult(
            passed=True,
            details={
                "path": str(resolved),
                "entries_checked": 0,
                "note": "No mapping entries found; vacuous pass.",
            },
        )

    violations: list[dict] = []
    for label, entry in entries:
        missing_channels: list[str] = []

        if not _ref_value_is_present(entry.get(_TIER2B_REF_FIELD)):
            missing_channels.append(_TIER2B_REF_FIELD)
        if not _ref_value_is_present(entry.get(_TIER3_REF_FIELD)):
            missing_channels.append(_TIER3_REF_FIELD)

        if missing_channels:
            violations.append({"entry": label, "missing": missing_channels})

    if violations:
        violated_labels = [v["entry"] for v in violations]
        return PredicateResult(
            passed=False,
            failure_category=POLICY_VIOLATION,
            reason=(
                f"{len(violations)} mapping entry(ies) in {resolved} are "
                f"missing required source reference channel(s): "
                f"{violated_labels}.  "
                "Every mapping must carry both 'tier2b_source_ref' and "
                "'tier3_evidence_ref' (gate_rules_library_plan.md §4.3)."
            ),
            details={
                "path": str(resolved),
                "entries_checked": len(entries),
                "violations": violations,
                "required_fields": [_TIER2B_REF_FIELD, _TIER3_REF_FIELD],
            },
        )

    return PredicateResult(
        passed=True,
        details={
            "path": str(resolved),
            "entries_checked": len(entries),
        },
    )
