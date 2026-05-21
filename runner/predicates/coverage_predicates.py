"""
Step 7 — Coverage predicates.

Implements the 11 cross-artifact join predicates defined in
gate_rules_library_plan.md §4.4:

    wp_budget_coverage_match(wp_path, budget_path)
    partner_budget_coverage_match(partners_path, budget_path)
    all_impacts_mapped(impact_path, expected_impacts_path)
    kpis_traceable_to_wps(impact_path, wp_path)
    all_sections_drafted(sections_path, schema_path)
    all_partners_in_tier3(wp_path, partners_path)
    all_management_roles_in_tier3(impl_path, partners_path)
    all_tasks_have_months(gantt_path, wp_path)
    instrument_sections_addressed(impl_path, schema_path)
    all_sections_have_traceability_footer(sections_path)
    all_wps_have_deliverable_and_lead(wp_path)

All functions accept a ``repo_root`` keyword argument.  Paths are resolved
via ``runner.paths.resolve_repo_path``.

Primary failure category for cross-file mismatches: ``CROSS_ARTIFACT_INCONSISTENCY``
(gate_rules_library_plan.md §3 coverage taxonomy).

``MISSING_MANDATORY_INPUT`` applies when a required file or directory is absent.
``MALFORMED_ARTIFACT`` applies when a present file cannot be parsed or is
missing required structural fields.

---------------------------------------------------------------------------
Bounded extraction strategies
---------------------------------------------------------------------------

partners.json (Tier 3 consortium/partners.json)
-------------------------------------------------
partners.json is a manually-placed Tier 3 artifact with no mandated
schema_id or run_id.  Four structural forms are supported:

* **Array form**: top-level list of partner dicts.
* **Wrapped array form**: ``{"partners": [...]}`` — a dict with a
  ``partners`` key whose value is a list of partner dicts.
* **Object — dict-of-entries**: keys are partner identifiers (top-level
  dict values that are dicts); the key is the partner_id.
* **Object — single entry**: dict has a top-level ``partner_id``, ``id``,
  or ``short_name`` field; treated as a single partner entry.

Within each partner dict, the identifier is resolved by field priority:
``partner_id`` → ``id`` → ``short_name``.

expected_impacts.json (Tier 2B extracted) — unknown format
----------------------------------------------------------
* **Array form**: each item has ``impact_id``, ``expected_impact_id``, or
  ``id`` field (tried in that order).
* **Object**: keys are expected impact identifiers.
* Empty array or empty dict → vacuous pass.

section_schema_registry.json (Tier 2A extracted) — unknown format
----------------------------------------------------------------
* **Array**: items are dicts with ``section_id`` and optional ``mandatory``
  (bool) field.  When no ``mandatory`` field: all sections are required
  (conservative default).
* **Object**: keys are section IDs; values are dicts with optional
  ``mandatory`` field.
* Empty: vacuous pass.

For ``instrument_sections_addressed``, sections are additionally filtered
by ``section_type: "implementation"`` when that field is present in the
registry.  If no entries carry a ``section_type`` field, all mandatory
sections are used as the requirement set.

Budget response files (docs/integrations/.../received/) — unknown format
------------------------------------------------------------------------
The external budget response format is not yet defined (interface_contract.json
is empty {}).  The predicate uses a deep-scan strategy: all values of
``wp_id`` (for ``wp_budget_coverage_match``) or ``partner_id`` (for
``partner_budget_coverage_match``) fields at any nesting level in the
budget response JSON files are collected into a set.  When the interface
contract is populated, this strategy should be replaced with targeted
field-path extraction.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Set, Union

from runner.paths import resolve_repo_path
from runner.predicates.types import (
    CROSS_ARTIFACT_INCONSISTENCY,
    MALFORMED_ARTIFACT,
    MISSING_MANDATORY_INPUT,
    PredicateResult,
)

PathLike = Union[str, Path]


# ---------------------------------------------------------------------------
# Internal helpers — JSON reading
# ---------------------------------------------------------------------------


def _read_json_object(
    resolved: Path,
) -> tuple[Optional[dict], Optional[PredicateResult]]:
    """Read *resolved* as a UTF-8 JSON object (dict). Return (dict, None) or (None, err)."""
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
            details={"path": str(resolved), "json_error": str(exc)},
        )
    if not isinstance(parsed, dict):
        return None, PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=(
                f"Expected a JSON object in {resolved}, "
                f"got {type(parsed).__name__}."
            ),
            details={"path": str(resolved), "parsed_type": type(parsed).__name__},
        )
    return parsed, None


def _read_json_any(
    resolved: Path,
) -> tuple[Optional[object], Optional[PredicateResult]]:
    """Read *resolved* as UTF-8 JSON accepting any value type."""
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
            details={"path": str(resolved), "json_error": str(exc)},
        )
    return parsed, None


# ---------------------------------------------------------------------------
# Internal helpers — partner ID extraction
# ---------------------------------------------------------------------------


def _extract_partner_ids_from_array(
    items: list,
    resolved: Path,
) -> tuple[Optional[Set[str]], Optional[PredicateResult]]:
    """
    Extract partner identifier strings from a list of partner entry dicts.

    Field resolution priority: ``partner_id`` → ``id`` → ``short_name``.
    Returns (set[str], None) or (None, error PredicateResult).
    """
    ids: Set[str] = set()
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            return None, PredicateResult(
                passed=False,
                failure_category=MALFORMED_ARTIFACT,
                reason=(
                    f"partners.json array element at index {idx} is not an object "
                    f"(got {type(item).__name__}) in {resolved}."
                ),
                details={"path": str(resolved), "entry_index": idx},
            )
        pid = (
            item.get("partner_id")
            or item.get("id")
            or item.get("short_name")
        )
        if isinstance(pid, str) and pid.strip():
            ids.add(pid)
    return ids, None


def _extract_partner_ids(
    parsed: object,
    resolved: Path,
) -> tuple[Optional[Set[str]], Optional[PredicateResult]]:
    """
    Extract partner identifier strings from parsed partners.json.

    See module docstring for the full bounded traversal rules.

    Supported formats:
    * **Array form**: top-level list of partner dicts.
    * **Wrapped array form**: ``{"partners": [...]}`` — dict with a
      ``partners`` key whose value is a list of partner dicts.
    * **Dict-of-entries**: top-level keys are partner identifiers (values
      are dicts).
    * **Single-entry form**: dict with a top-level ``partner_id``, ``id``,
      or ``short_name`` field.

    Within each partner dict, the identifier is resolved by priority:
    ``partner_id`` → ``id`` → ``short_name``.

    Returns (set[str], None) or (None, error PredicateResult).
    """
    if isinstance(parsed, list):
        return _extract_partner_ids_from_array(parsed, resolved)

    if isinstance(parsed, dict):
        # Wrapped array form: {"partners": [...]}
        partners_list = parsed.get("partners")
        if isinstance(partners_list, list):
            return _extract_partner_ids_from_array(partners_list, resolved)

        # Single-entry form: dict has partner_id / id / short_name at top level
        for field in ("partner_id", "id", "short_name"):
            if field in parsed:
                pid = parsed[field]
                if isinstance(pid, str) and pid.strip():
                    return {pid}, None
                return set(), None

        # Dict-of-entries: keys are partner identifiers
        return {k for k, v in parsed.items() if isinstance(v, dict)}, None

    return None, PredicateResult(
        passed=False,
        failure_category=MALFORMED_ARTIFACT,
        reason=(
            f"Unsupported top-level JSON type {type(parsed).__name__!r} in "
            f"{resolved}.  partners.json must be an array or object."
        ),
        details={"path": str(resolved), "parsed_type": type(parsed).__name__},
    )


# ---------------------------------------------------------------------------
# Internal helpers — expected impact ID extraction
# ---------------------------------------------------------------------------

_IMPACT_ID_FIELDS: tuple[str, ...] = ("impact_id", "expected_impact_id", "id")


def _extract_expected_impact_ids(
    parsed: object,
    resolved: Path,
) -> tuple[Optional[Set[str]], Optional[PredicateResult]]:
    """
    Extract expected impact identifier strings from parsed expected_impacts.json.

    See module docstring for the full bounded traversal rules.
    Returns (set[str], None) or (None, error PredicateResult).
    """
    if isinstance(parsed, list):
        ids: Set[str] = set()
        for idx, item in enumerate(parsed):
            if not isinstance(item, dict):
                return None, PredicateResult(
                    passed=False,
                    failure_category=MALFORMED_ARTIFACT,
                    reason=(
                        f"expected_impacts.json array element at index {idx} is not an "
                        f"object (got {type(item).__name__}) in {resolved}."
                    ),
                    details={"path": str(resolved), "entry_index": idx},
                )
            for field in _IMPACT_ID_FIELDS:
                val = item.get(field)
                if isinstance(val, str) and val.strip():
                    ids.add(val)
                    break
        return ids, None

    if isinstance(parsed, dict):
        # Single-entry form: dict itself has an id field
        for field in _IMPACT_ID_FIELDS:
            if field in parsed:
                val = parsed[field]
                if isinstance(val, str) and val.strip():
                    return {val}, None
        # Dict-of-entries: keys are expected impact IDs
        return {k for k, v in parsed.items() if isinstance(v, dict)}, None

    return None, PredicateResult(
        passed=False,
        failure_category=MALFORMED_ARTIFACT,
        reason=(
            f"Unsupported top-level JSON type {type(parsed).__name__!r} in "
            f"{resolved}.  expected_impacts.json must be an array or object."
        ),
        details={"path": str(resolved), "parsed_type": type(parsed).__name__},
    )


# ---------------------------------------------------------------------------
# Internal helpers — section registry extraction
# ---------------------------------------------------------------------------


def _extract_required_section_ids(
    parsed: object,
    resolved: Path,
) -> tuple[Optional[Set[str]], Optional[PredicateResult]]:
    """
    Extract required section IDs from section_schema_registry.json.

    See module docstring.  Returns (set[str], None) or (None, error).
    Missing ``mandatory`` field → treated as mandatory (conservative default).
    """
    if isinstance(parsed, list):
        ids: Set[str] = set()
        for item in parsed:
            if not isinstance(item, dict):
                continue
            section_id = item.get("section_id")
            if not isinstance(section_id, str) or not section_id.strip():
                continue
            if item.get("mandatory", True):
                ids.add(section_id)
        return ids, None

    if isinstance(parsed, dict):
        ids = set()
        for key, val in parsed.items():
            if not isinstance(val, dict):
                continue
            if val.get("mandatory", True):
                ids.add(key)
        return ids, None

    return None, PredicateResult(
        passed=False,
        failure_category=MALFORMED_ARTIFACT,
        reason=(
            f"Unsupported top-level JSON type {type(parsed).__name__!r} in "
            f"{resolved}.  section_schema_registry.json must be an array or object."
        ),
        details={"path": str(resolved), "parsed_type": type(parsed).__name__},
    )


def _extract_required_impl_section_ids(
    parsed: object,
    resolved: Path,
) -> tuple[Optional[Set[str]], Optional[PredicateResult]]:
    """
    Extract mandatory implementation section IDs from section_schema_registry.json.

    Sections with ``section_type`` / ``type`` equal to ``"implementation"`` and
    ``mandatory: true`` are returned.  When no entries carry a type field, all
    mandatory sections are returned as the fallback requirement set.

    Returns (set[str], None) or (None, error PredicateResult).
    """
    if isinstance(parsed, list):
        impl_ids: Set[str] = set()
        all_mandatory: Set[str] = set()
        has_type = False
        for item in parsed:
            if not isinstance(item, dict):
                continue
            section_id = item.get("section_id")
            if not isinstance(section_id, str) or not section_id.strip():
                continue
            mandatory = item.get("mandatory", True)
            stype = item.get("section_type") or item.get("type")
            if stype:
                has_type = True
            if mandatory:
                all_mandatory.add(section_id)
                if stype and str(stype).lower() == "implementation":
                    impl_ids.add(section_id)
        return (impl_ids if has_type else all_mandatory), None

    if isinstance(parsed, dict):
        impl_ids = set()
        all_mandatory = set()
        has_type = False
        for key, val in parsed.items():
            if not isinstance(val, dict):
                continue
            mandatory = val.get("mandatory", True)
            stype = val.get("section_type") or val.get("type")
            if stype:
                has_type = True
            if mandatory:
                all_mandatory.add(key)
                if stype and str(stype).lower() == "implementation":
                    impl_ids.add(key)
        return (impl_ids if has_type else all_mandatory), None

    return None, PredicateResult(
        passed=False,
        failure_category=MALFORMED_ARTIFACT,
        reason=(
            f"Unsupported top-level JSON type {type(parsed).__name__!r} in "
            f"{resolved}.  section_schema_registry.json must be an array or object."
        ),
        details={"path": str(resolved), "parsed_type": type(parsed).__name__},
    )


# ---------------------------------------------------------------------------
# Internal helpers — budget response deep scan
# ---------------------------------------------------------------------------


def _collect_field_values_deep(obj: object, field_name: str) -> Set[str]:
    """
    Recursively collect all non-blank string values of *field_name* at any
    nesting depth in *obj*.

    Used to scan budget response files for wp_id / partner_id values when
    the budget response schema is not yet defined.  See module docstring.
    """
    results: Set[str] = set()
    if isinstance(obj, dict):
        for key, val in obj.items():
            if key == field_name and isinstance(val, str) and val.strip():
                results.add(val)
            results |= _collect_field_values_deep(val, field_name)
    elif isinstance(obj, list):
        for item in obj:
            results |= _collect_field_values_deep(item, field_name)
    return results


def _scan_budget_dir(
    budget_dir: Path,
    field_name: str,
) -> tuple[Optional[Set[str]], Optional[PredicateResult]]:
    """
    Scan all direct-child .json files in *budget_dir* and collect all string
    values of *field_name* at any nesting level.

    Files that cannot be parsed as JSON are skipped; structural validation is
    the responsibility of ``interface_contract_conforms`` in the gate sequence.

    Returns (set[str], None) or (None, error PredicateResult).
    """
    if not budget_dir.exists():
        return None, PredicateResult(
            passed=False,
            failure_category=MISSING_MANDATORY_INPUT,
            reason=f"Budget directory does not exist: {budget_dir}",
            details={"path": str(budget_dir)},
        )
    if not budget_dir.is_dir():
        return None, PredicateResult(
            passed=False,
            failure_category=MISSING_MANDATORY_INPUT,
            reason=f"Expected a directory but found a file: {budget_dir}",
            details={"path": str(budget_dir), "is_file": True},
        )
    found: Set[str] = set()
    for json_file in budget_dir.glob("*.json"):
        if not json_file.is_file():
            continue
        try:
            text = json_file.read_text(encoding="utf-8-sig")
            parsed = json.loads(text)
            found |= _collect_field_values_deep(parsed, field_name)
        except (json.JSONDecodeError, UnicodeDecodeError, OSError):
            pass  # Structural validation is interface_contract_conforms' job
    return found, None


# ---------------------------------------------------------------------------
# Internal helpers — WP structure extraction
# ---------------------------------------------------------------------------


def _extract_wp_ids(
    wp_data: dict,
    wp_resolved: Path,
) -> tuple[Optional[Set[str]], Optional[PredicateResult]]:
    """Extract the set of wp_id strings from a parsed wp_structure dict."""
    work_packages = wp_data.get("work_packages")
    if not isinstance(work_packages, list):
        return None, PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=(
                f"'work_packages' field is absent or not a list in {wp_resolved}."
            ),
            details={"path": str(wp_resolved), "field": "work_packages"},
        )
    ids: Set[str] = set()
    for wp in work_packages:
        if isinstance(wp, dict):
            wp_id = wp.get("wp_id")
            if isinstance(wp_id, str) and wp_id.strip():
                ids.add(wp_id)
    return ids, None


def _extract_all_deliverable_ids(
    wp_data: dict,
    wp_resolved: Path,
) -> tuple[Optional[Set[str]], Optional[PredicateResult]]:
    """Extract all deliverable_id strings across all WPs from a parsed wp_structure dict."""
    work_packages = wp_data.get("work_packages")
    if not isinstance(work_packages, list):
        return None, PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=f"'work_packages' is absent or not a list in {wp_resolved}.",
            details={"path": str(wp_resolved), "field": "work_packages"},
        )
    ids: Set[str] = set()
    for wp in work_packages:
        if not isinstance(wp, dict):
            continue
        deliverables = wp.get("deliverables", [])
        if isinstance(deliverables, list):
            for d in deliverables:
                if isinstance(d, dict):
                    did = d.get("deliverable_id")
                    if isinstance(did, str) and did.strip():
                        ids.add(did)
    return ids, None


def _extract_all_task_ids(
    wp_data: dict,
    wp_resolved: Path,
) -> tuple[Optional[Set[str]], Optional[PredicateResult]]:
    """Extract all task_id strings across all WPs from a parsed wp_structure dict."""
    work_packages = wp_data.get("work_packages")
    if not isinstance(work_packages, list):
        return None, PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=f"'work_packages' is absent or not a list in {wp_resolved}.",
            details={"path": str(wp_resolved), "field": "work_packages"},
        )
    ids: Set[str] = set()
    for wp in work_packages:
        if not isinstance(wp, dict):
            continue
        tasks = wp.get("tasks", [])
        if isinstance(tasks, list):
            for t in tasks:
                if isinstance(t, dict):
                    tid = t.get("task_id")
                    if isinstance(tid, str) and tid.strip():
                        ids.add(tid)
    return ids, None


def _extract_all_wp_partners(
    wp_data: dict,
) -> Set[str]:
    """Collect lead_partner and contributing_partners strings from all WPs."""
    partners: Set[str] = set()
    for wp in wp_data.get("work_packages", []):
        if not isinstance(wp, dict):
            continue
        lead = wp.get("lead_partner")
        if isinstance(lead, str) and lead.strip():
            partners.add(lead)
        for pid in wp.get("contributing_partners", []):
            if isinstance(pid, str) and pid.strip():
                partners.add(pid)
    return partners


# ---------------------------------------------------------------------------
# §4.4 — Coverage predicates
# ---------------------------------------------------------------------------


def all_wps_have_deliverable_and_lead(
    wp_path: PathLike,
    *,
    repo_root: Optional[Path] = None,
) -> PredicateResult:
    """
    Pass iff every WP in the Phase 3 output has at least one deliverable and
    a non-empty lead partner field.

    Contract (gate_rules_library_plan.md §4.4)
    -------------------------------------------
    Pass condition:
        * ``work_packages`` is a non-empty list in wp_structure.json
        * every WP entry has a non-empty ``lead_partner`` string
        * every WP entry has a non-empty ``deliverables`` list

    Gate usage: g04_p04 (phase_03_gate)

    Failure categories
    ------------------
    ``MISSING_MANDATORY_INPUT``  — wp_path absent
    ``MALFORMED_ARTIFACT``       — invalid JSON, ``work_packages`` absent/wrong type
    ``CROSS_ARTIFACT_INCONSISTENCY``
        A WP is missing ``lead_partner`` or has no ``deliverables``.
    """
    resolved = resolve_repo_path(wp_path, repo_root)
    wp_data, err = _read_json_object(resolved)
    if err is not None:
        return err

    work_packages = wp_data.get("work_packages")
    if not isinstance(work_packages, list):
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=f"'work_packages' is absent or not a list in {resolved}.",
            details={"path": str(resolved), "field": "work_packages"},
        )

    violations: list[dict] = []
    for wp in work_packages:
        if not isinstance(wp, dict):
            violations.append({"wp": repr(wp)[:60], "issue": "entry_not_a_dict"})
            continue
        wp_id = wp.get("wp_id", "<unknown>")
        missing: list[str] = []
        lead = wp.get("lead_partner")
        if not isinstance(lead, str) or not lead.strip():
            missing.append("lead_partner")
        deliverables = wp.get("deliverables")
        if not isinstance(deliverables, list) or not deliverables:
            missing.append("deliverables")
        if missing:
            violations.append({"wp_id": wp_id, "missing_or_empty": missing})

    if violations:
        return PredicateResult(
            passed=False,
            failure_category=CROSS_ARTIFACT_INCONSISTENCY,
            reason=(
                f"{len(violations)} WP(s) in {resolved} are missing a lead partner "
                f"or have no deliverables: "
                f"{[v.get('wp_id', v) for v in violations]}.  "
                "All WPs must have a non-empty lead_partner and at least one "
                "deliverable (gate_rules_library_plan.md §4.4)."
            ),
            details={
                "path": str(resolved),
                "wps_checked": len(work_packages),
                "violations": violations,
            },
        )

    return PredicateResult(
        passed=True,
        details={
            "path": str(resolved),
            "wps_checked": len(work_packages),
        },
    )


def all_partners_in_tier3(
    wp_path: PathLike,
    partners_path: PathLike,
    *,
    repo_root: Optional[Path] = None,
) -> PredicateResult:
    """
    Pass iff every partner assigned as lead or contributor in the WP structure
    exists in Tier 3 partners.json.

    Contract (gate_rules_library_plan.md §4.4)
    -------------------------------------------
    Pass condition:
        * both artifacts are readable
        * the set of lead_partner + contributing_partners across all WPs is a
          subset of the partner_id set in partners.json

    Gate usage: g04_p07 (phase_03_gate)

    Failure categories
    ------------------
    ``MISSING_MANDATORY_INPUT``      — either file absent
    ``MALFORMED_ARTIFACT``           — invalid JSON / structural issue
    ``CROSS_ARTIFACT_INCONSISTENCY`` — a WP references a partner not in Tier 3
    """
    wp_resolved = resolve_repo_path(wp_path, repo_root)
    partners_resolved = resolve_repo_path(partners_path, repo_root)

    wp_data, err = _read_json_object(wp_resolved)
    if err is not None:
        return err
    partners_parsed, err = _read_json_any(partners_resolved)
    if err is not None:
        return err

    wp_partners = _extract_all_wp_partners(wp_data)

    tier3_ids, err = _extract_partner_ids(partners_parsed, partners_resolved)
    if err is not None:
        return err

    missing = sorted(wp_partners - tier3_ids)
    if missing:
        return PredicateResult(
            passed=False,
            failure_category=CROSS_ARTIFACT_INCONSISTENCY,
            reason=(
                f"{len(missing)} partner(s) referenced in {wp_resolved} are not "
                f"present in {partners_resolved}: {missing}.  "
                "All WP lead and contributing partners must exist in Tier 3 "
                "consortium data (gate_rules_library_plan.md §4.4)."
            ),
            details={
                "wp_path": str(wp_resolved),
                "partners_path": str(partners_resolved),
                "partners_in_wps": sorted(wp_partners),
                "partners_in_tier3": sorted(tier3_ids),
                "missing_from_tier3": missing,
            },
        )

    return PredicateResult(
        passed=True,
        details={
            "wp_path": str(wp_resolved),
            "partners_path": str(partners_resolved),
            "partners_checked": len(wp_partners),
            "all_found_in_tier3": True,
        },
    )


def all_management_roles_in_tier3(
    impl_path: PathLike,
    partners_path: PathLike,
    *,
    repo_root: Optional[Path] = None,
) -> PredicateResult:
    """
    Pass iff every management role named in the implementation architecture
    references a partner present in Tier 3 partners.json.

    Contract (gate_rules_library_plan.md §4.4)
    -------------------------------------------
    Pass condition:
        * ``management_roles`` is a list in implementation_architecture.json
        * every entry's ``assigned_to`` value is a string present in partners.json

    Gate usage: g07_p08 (phase_06_gate)

    Failure categories
    ------------------
    ``MISSING_MANDATORY_INPUT``      — either file absent
    ``MALFORMED_ARTIFACT``           — invalid JSON / ``management_roles`` wrong type
    ``CROSS_ARTIFACT_INCONSISTENCY`` — assigned_to partner not in Tier 3
    """
    impl_resolved = resolve_repo_path(impl_path, repo_root)
    partners_resolved = resolve_repo_path(partners_path, repo_root)

    impl_data, err = _read_json_object(impl_resolved)
    if err is not None:
        return err
    partners_parsed, err = _read_json_any(partners_resolved)
    if err is not None:
        return err

    management_roles = impl_data.get("management_roles")
    if not isinstance(management_roles, list):
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=f"'management_roles' is absent or not a list in {impl_resolved}.",
            details={"path": str(impl_resolved), "field": "management_roles"},
        )

    tier3_ids, err = _extract_partner_ids(partners_parsed, partners_resolved)
    if err is not None:
        return err

    assigned_ids: Set[str] = set()
    for role in management_roles:
        if isinstance(role, dict):
            pid = role.get("assigned_to")
            if isinstance(pid, str) and pid.strip():
                assigned_ids.add(pid)

    missing = sorted(assigned_ids - tier3_ids)
    if missing:
        return PredicateResult(
            passed=False,
            failure_category=CROSS_ARTIFACT_INCONSISTENCY,
            reason=(
                f"{len(missing)} management role assignee(s) in {impl_resolved} are "
                f"not present in {partners_resolved}: {missing}.  "
                "All management roles must be assigned to Tier 3 consortium members "
                "(gate_rules_library_plan.md §4.4)."
            ),
            details={
                "impl_path": str(impl_resolved),
                "partners_path": str(partners_resolved),
                "assigned_partners": sorted(assigned_ids),
                "partners_in_tier3": sorted(tier3_ids),
                "missing_from_tier3": missing,
            },
        )

    return PredicateResult(
        passed=True,
        details={
            "impl_path": str(impl_resolved),
            "partners_path": str(partners_resolved),
            "roles_checked": len(management_roles),
            "all_found_in_tier3": True,
        },
    )


def all_tasks_have_months(
    gantt_path: PathLike,
    wp_path: PathLike,
    *,
    repo_root: Optional[Path] = None,
) -> PredicateResult:
    """
    Pass iff every task_id present in the Phase 3 WP output also appears in
    the Gantt output with non-null start_month and end_month.

    Contract (gate_rules_library_plan.md §4.4)
    -------------------------------------------
    Pass condition:
        * every task_id from wp_structure.json appears in gantt.json tasks[]
        * each matching gantt entry has non-null (integer) start_month and end_month

    Gate usage: g05_p03 (phase_04_gate)

    Failure categories
    ------------------
    ``MISSING_MANDATORY_INPUT``      — either file absent
    ``MALFORMED_ARTIFACT``           — invalid JSON / required list absent
    ``CROSS_ARTIFACT_INCONSISTENCY`` — task missing from Gantt or months null
    """
    gantt_resolved = resolve_repo_path(gantt_path, repo_root)
    wp_resolved = resolve_repo_path(wp_path, repo_root)

    gantt_data, err = _read_json_object(gantt_resolved)
    if err is not None:
        return err
    wp_data, err = _read_json_object(wp_resolved)
    if err is not None:
        return err

    # Extract WP task IDs
    wp_task_ids, err = _extract_all_task_ids(wp_data, wp_resolved)
    if err is not None:
        return err

    # Build gantt task_id → entry map
    gantt_tasks = gantt_data.get("tasks")
    if not isinstance(gantt_tasks, list):
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=f"'tasks' is absent or not a list in {gantt_resolved}.",
            details={"path": str(gantt_resolved), "field": "tasks"},
        )

    gantt_task_map: dict[str, dict] = {}
    for entry in gantt_tasks:
        if isinstance(entry, dict):
            tid = entry.get("task_id")
            if isinstance(tid, str) and tid.strip():
                gantt_task_map[tid] = entry

    violations: list[dict] = []
    for tid in sorted(wp_task_ids):
        if tid not in gantt_task_map:
            violations.append({"task_id": tid, "issue": "missing_from_gantt"})
            continue
        entry = gantt_task_map[tid]
        start = entry.get("start_month")
        end = entry.get("end_month")
        issues: list[str] = []
        if not isinstance(start, int):
            issues.append("start_month_null_or_non_integer")
        if not isinstance(end, int):
            issues.append("end_month_null_or_non_integer")
        if issues:
            violations.append({"task_id": tid, "issue": issues})

    if violations:
        return PredicateResult(
            passed=False,
            failure_category=CROSS_ARTIFACT_INCONSISTENCY,
            reason=(
                f"{len(violations)} task(s) from {wp_resolved} are missing from "
                f"or have null months in {gantt_resolved}: "
                f"{[v['task_id'] for v in violations]}.  "
                "All WP tasks must appear in the Gantt with non-null start and "
                "end months (gate_rules_library_plan.md §4.4)."
            ),
            details={
                "gantt_path": str(gantt_resolved),
                "wp_path": str(wp_resolved),
                "tasks_checked": len(wp_task_ids),
                "violations": violations,
            },
        )

    return PredicateResult(
        passed=True,
        details={
            "gantt_path": str(gantt_resolved),
            "wp_path": str(wp_resolved),
            "tasks_checked": len(wp_task_ids),
        },
    )


def all_impacts_mapped(
    impact_path: PathLike,
    expected_impacts_path: PathLike,
    *,
    repo_root: Optional[Path] = None,
) -> PredicateResult:
    """
    Pass iff every expected impact identifier in Tier 2B expected_impacts.json
    appears in the impact architecture with at least one mapped project output.

    Contract (gate_rules_library_plan.md §4.4)
    -------------------------------------------
    Pass condition:
        * every expected_impact_id from expected_impacts.json appears as the
          ``expected_impact_id`` of at least one pathway in impact_pathways[]
        * that pathway has a non-empty ``project_outputs`` list

    Gate usage: g06_p04 (phase_05_gate)

    Failure categories
    ------------------
    ``MISSING_MANDATORY_INPUT``      — either file absent
    ``MALFORMED_ARTIFACT``           — invalid JSON / ``impact_pathways`` wrong type
    ``CROSS_ARTIFACT_INCONSISTENCY`` — expected impact unmapped or has no outputs
    """
    impact_resolved = resolve_repo_path(impact_path, repo_root)
    expected_resolved = resolve_repo_path(expected_impacts_path, repo_root)

    impact_data, err = _read_json_object(impact_resolved)
    if err is not None:
        return err
    expected_parsed, err = _read_json_any(expected_resolved)
    if err is not None:
        return err

    impact_pathways = impact_data.get("impact_pathways")
    if not isinstance(impact_pathways, list):
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=f"'impact_pathways' is absent or not a list in {impact_resolved}.",
            details={"path": str(impact_resolved), "field": "impact_pathways"},
        )

    expected_ids, err = _extract_expected_impact_ids(expected_parsed, expected_resolved)
    if err is not None:
        return err

    if not expected_ids:
        return PredicateResult(
            passed=True,
            details={
                "impact_path": str(impact_resolved),
                "expected_impacts_path": str(expected_resolved),
                "expected_impacts_checked": 0,
                "note": "No expected impact IDs found; vacuous pass.",
            },
        )

    # Build map: expected_impact_id → pathways with non-empty project_outputs
    covered: Set[str] = set()
    for pathway in impact_pathways:
        if not isinstance(pathway, dict):
            continue
        eid = pathway.get("expected_impact_id")
        outputs = pathway.get("project_outputs", [])
        if isinstance(eid, str) and eid.strip() and isinstance(outputs, list) and outputs:
            covered.add(eid)

    missing = sorted(expected_ids - covered)
    if missing:
        return PredicateResult(
            passed=False,
            failure_category=CROSS_ARTIFACT_INCONSISTENCY,
            reason=(
                f"{len(missing)} expected impact(s) from {expected_resolved} are not "
                f"mapped in {impact_resolved} with at least one project output: "
                f"{missing}.  "
                "Every Tier 2B expected impact must appear in at least one pathway "
                "with non-empty project_outputs (gate_rules_library_plan.md §4.4)."
            ),
            details={
                "impact_path": str(impact_resolved),
                "expected_impacts_path": str(expected_resolved),
                "expected_impacts_checked": len(expected_ids),
                "covered": sorted(covered),
                "missing": missing,
            },
        )

    return PredicateResult(
        passed=True,
        details={
            "impact_path": str(impact_resolved),
            "expected_impacts_path": str(expected_resolved),
            "expected_impacts_checked": len(expected_ids),
        },
    )


def kpis_traceable_to_wps(
    impact_path: PathLike,
    wp_path: PathLike,
    *,
    repo_root: Optional[Path] = None,
) -> PredicateResult:
    """
    Pass iff every KPI defined in the impact architecture references a named
    deliverable from the Phase 3 WP output.

    Contract (gate_rules_library_plan.md §4.4)
    -------------------------------------------
    Pass condition:
        * ``kpis`` is a list in impact_architecture.json
        * every entry's ``traceable_to_deliverable`` is a string that matches
          a ``deliverable_id`` in wp_structure.json

    Gate usage: g06_p05 (phase_05_gate)

    Failure categories
    ------------------
    ``MISSING_MANDATORY_INPUT``      — either file absent
    ``MALFORMED_ARTIFACT``           — invalid JSON / ``kpis`` or ``work_packages`` wrong type
    ``CROSS_ARTIFACT_INCONSISTENCY`` — KPI deliverable reference not found in WP structure
    """
    impact_resolved = resolve_repo_path(impact_path, repo_root)
    wp_resolved = resolve_repo_path(wp_path, repo_root)

    impact_data, err = _read_json_object(impact_resolved)
    if err is not None:
        return err
    wp_data, err = _read_json_object(wp_resolved)
    if err is not None:
        return err

    kpis = impact_data.get("kpis")
    if not isinstance(kpis, list):
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=f"'kpis' is absent or not a list in {impact_resolved}.",
            details={"path": str(impact_resolved), "field": "kpis"},
        )

    deliverable_ids, err = _extract_all_deliverable_ids(wp_data, wp_resolved)
    if err is not None:
        return err

    if not kpis:
        return PredicateResult(
            passed=True,
            details={
                "impact_path": str(impact_resolved),
                "wp_path": str(wp_resolved),
                "kpis_checked": 0,
                "note": "No KPIs defined; vacuous pass.",
            },
        )

    violations: list[dict] = []
    for idx, kpi in enumerate(kpis):
        if not isinstance(kpi, dict):
            violations.append({"kpi_index": idx, "issue": "entry_not_a_dict"})
            continue
        kpi_id = kpi.get("kpi_id", f"[{idx}]")
        ref = kpi.get("traceable_to_deliverable")
        if not isinstance(ref, str) or not ref.strip():
            violations.append({
                "kpi_id": kpi_id,
                "issue": "missing_or_blank_traceable_to_deliverable",
            })
        elif ref not in deliverable_ids:
            violations.append({
                "kpi_id": kpi_id,
                "traceable_to_deliverable": ref,
                "issue": "deliverable_not_found_in_wp_structure",
            })

    if violations:
        return PredicateResult(
            passed=False,
            failure_category=CROSS_ARTIFACT_INCONSISTENCY,
            reason=(
                f"{len(violations)} KPI(s) in {impact_resolved} reference deliverables "
                f"not present in {wp_resolved}: "
                f"{[v.get('kpi_id', v) for v in violations]}.  "
                "Every KPI must reference a named deliverable_id from the WP structure "
                "(gate_rules_library_plan.md §4.4)."
            ),
            details={
                "impact_path": str(impact_resolved),
                "wp_path": str(wp_resolved),
                "kpis_checked": len(kpis),
                "known_deliverable_ids": sorted(deliverable_ids),
                "violations": violations,
            },
        )

    return PredicateResult(
        passed=True,
        details={
            "impact_path": str(impact_resolved),
            "wp_path": str(wp_resolved),
            "kpis_checked": len(kpis),
        },
    )


def instrument_sections_addressed(
    impl_path: PathLike,
    schema_path: PathLike,
    *,
    repo_root: Optional[Path] = None,
) -> PredicateResult:
    """
    Pass iff every mandatory implementation section listed in the section
    schema registry appears in the Phase 6 output with status ``addressed``
    or ``not_applicable``.

    Contract (gate_rules_library_plan.md §4.4)
    -------------------------------------------
    Pass condition:
        * for each required implementation section_id in section_schema_registry.json,
          implementation_architecture.json has an entry in
          ``instrument_sections_addressed[]`` with status ``addressed`` or
          ``not_applicable``

    Status semantics
    ----------------
    ``addressed``      — section is handled; satisfies the predicate.
    ``not_applicable`` — section does not apply to this project; satisfies.
    ``deferred``       — section not yet handled; fails the predicate.

    Gate usage: g07_p09 (phase_06_gate)

    Failure categories
    ------------------
    ``MISSING_MANDATORY_INPUT``      — either file absent
    ``MALFORMED_ARTIFACT``           — invalid JSON / ``instrument_sections_addressed`` wrong type
    ``CROSS_ARTIFACT_INCONSISTENCY`` — required section absent or deferred
    """
    impl_resolved = resolve_repo_path(impl_path, repo_root)
    schema_resolved = resolve_repo_path(schema_path, repo_root)

    impl_data, err = _read_json_object(impl_resolved)
    if err is not None:
        return err
    schema_parsed, err = _read_json_any(schema_resolved)
    if err is not None:
        return err

    addressed_list = impl_data.get("instrument_sections_addressed")
    if not isinstance(addressed_list, list):
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=(
                f"'instrument_sections_addressed' is absent or not a list "
                f"in {impl_resolved}."
            ),
            details={"path": str(impl_resolved), "field": "instrument_sections_addressed"},
        )

    required_ids, err = _extract_required_impl_section_ids(schema_parsed, schema_resolved)
    if err is not None:
        return err

    if not required_ids:
        return PredicateResult(
            passed=True,
            details={
                "impl_path": str(impl_resolved),
                "schema_path": str(schema_resolved),
                "required_sections_checked": 0,
                "note": "No required implementation sections found; vacuous pass.",
            },
        )

    _SATISFYING_STATUSES = {"addressed", "not_applicable"}
    satisfied: Set[str] = set()
    for entry in addressed_list:
        if not isinstance(entry, dict):
            continue
        sec_id = entry.get("section_id")
        status = entry.get("status")
        if isinstance(sec_id, str) and sec_id in required_ids:
            if isinstance(status, str) and status in _SATISFYING_STATUSES:
                satisfied.add(sec_id)

    missing = sorted(required_ids - satisfied)
    if missing:
        return PredicateResult(
            passed=False,
            failure_category=CROSS_ARTIFACT_INCONSISTENCY,
            reason=(
                f"{len(missing)} required implementation section(s) from "
                f"{schema_resolved} are absent or not addressed in "
                f"{impl_resolved}: {missing}.  "
                "All mandatory instrument sections must have status 'addressed' "
                "or 'not_applicable' (gate_rules_library_plan.md §4.4)."
            ),
            details={
                "impl_path": str(impl_resolved),
                "schema_path": str(schema_resolved),
                "required_sections": sorted(required_ids),
                "satisfied_sections": sorted(satisfied),
                "missing_or_deferred": missing,
            },
        )

    return PredicateResult(
        passed=True,
        details={
            "impl_path": str(impl_resolved),
            "schema_path": str(schema_resolved),
            "required_sections_checked": len(required_ids),
        },
    )


def all_sections_drafted(
    sections_path: PathLike,
    schema_path: PathLike,
    *,
    repo_root: Optional[Path] = None,
) -> PredicateResult:
    """
    Pass iff every section identifier required by the active instrument schema
    has a corresponding artifact file in ``proposal_sections/``.

    Contract (gate_rules_library_plan.md §4.4)
    -------------------------------------------
    Pass condition:
        * for each mandatory section_id in section_schema_registry.json, a
          file named ``<section_id>.json`` exists in sections_path

    sections_path is a collection-scope directory (exception class 3,
    artifact_schema_specification.yaml §0).

    Gate usage: g09_p02 (gate_10_part_b_completeness), g11_p02 (gate_12)

    Failure categories
    ------------------
    ``MISSING_MANDATORY_INPUT``      — sections_path or schema_path absent
    ``MALFORMED_ARTIFACT``           — schema file invalid JSON / wrong type
    ``CROSS_ARTIFACT_INCONSISTENCY`` — required section file missing
    """
    sections_resolved = resolve_repo_path(sections_path, repo_root)
    schema_resolved = resolve_repo_path(schema_path, repo_root)

    if not sections_resolved.exists():
        return PredicateResult(
            passed=False,
            failure_category=MISSING_MANDATORY_INPUT,
            reason=f"Proposal sections directory does not exist: {sections_resolved}",
            details={"path": str(sections_resolved)},
        )
    if not sections_resolved.is_dir():
        return PredicateResult(
            passed=False,
            failure_category=MISSING_MANDATORY_INPUT,
            reason=f"Expected a directory at sections_path but found a file: {sections_resolved}",
            details={"path": str(sections_resolved), "is_file": True},
        )

    schema_parsed, err = _read_json_any(schema_resolved)
    if err is not None:
        return err

    required_ids, err = _extract_required_section_ids(schema_parsed, schema_resolved)
    if err is not None:
        return err

    if not required_ids:
        return PredicateResult(
            passed=True,
            details={
                "sections_path": str(sections_resolved),
                "schema_path": str(schema_resolved),
                "required_sections_checked": 0,
                "note": "No required sections found in registry; vacuous pass.",
            },
        )

    missing: list[str] = []
    for sec_id in sorted(required_ids):
        expected_file = sections_resolved / f"{sec_id}.json"
        if not expected_file.is_file():
            missing.append(sec_id)

    if missing:
        return PredicateResult(
            passed=False,
            failure_category=CROSS_ARTIFACT_INCONSISTENCY,
            reason=(
                f"{len(missing)} required section file(s) are absent from "
                f"{sections_resolved}: {missing}.  "
                "Every required section must have a corresponding <section_id>.json "
                "file in proposal_sections/ (gate_rules_library_plan.md §4.4)."
            ),
            details={
                "sections_path": str(sections_resolved),
                "schema_path": str(schema_resolved),
                "required_sections": sorted(required_ids),
                "missing_files": missing,
            },
        )

    return PredicateResult(
        passed=True,
        details={
            "sections_path": str(sections_resolved),
            "schema_path": str(schema_resolved),
            "required_sections_checked": len(required_ids),
        },
    )


def all_sections_have_traceability_footer(
    sections_path: PathLike,
    *,
    repo_root: Optional[Path] = None,
) -> PredicateResult:
    """
    Pass iff every section artifact in ``proposal_sections/`` contains a
    non-empty traceability footer with at least one primary source.

    Contract (gate_rules_library_plan.md §4.4)
    -------------------------------------------
    Pass condition:
        * for every .json file in sections_path:
          - ``traceability_footer`` key is present and is a dict
          - ``traceability_footer.primary_sources`` is a non-empty list

    sections_path is a collection-scope directory (exception class 3).
    Empty directory → vacuous pass (all_sections_drafted guards presence).

    Gate usage: g09_p04 (gate_10_part_b_completeness)

    Failure categories
    ------------------
    ``MISSING_MANDATORY_INPUT``      — sections_path absent
    ``CROSS_ARTIFACT_INCONSISTENCY`` — a section file lacks a non-empty traceability footer
    """
    sections_resolved = resolve_repo_path(sections_path, repo_root)

    if not sections_resolved.exists():
        return PredicateResult(
            passed=False,
            failure_category=MISSING_MANDATORY_INPUT,
            reason=f"Proposal sections directory does not exist: {sections_resolved}",
            details={"path": str(sections_resolved)},
        )
    if not sections_resolved.is_dir():
        return PredicateResult(
            passed=False,
            failure_category=MISSING_MANDATORY_INPUT,
            reason=f"Expected a directory at sections_path but found a file: {sections_resolved}",
            details={"path": str(sections_resolved), "is_file": True},
        )

    json_files = sorted(p for p in sections_resolved.glob("*.json") if p.is_file())
    if not json_files:
        return PredicateResult(
            passed=True,
            details={
                "sections_path": str(sections_resolved),
                "files_checked": 0,
                "note": "No .json files found; vacuous pass.",
            },
        )

    violations: list[dict] = []
    for json_file in json_files:
        parsed, err = _read_json_any(json_file)
        if err is not None:
            violations.append({"file": json_file.name, "issue": "unreadable_or_invalid_json"})
            continue
        if not isinstance(parsed, dict):
            violations.append({"file": json_file.name, "issue": "top_level_not_a_dict"})
            continue
        footer = parsed.get("traceability_footer")
        if footer is None:
            violations.append({"file": json_file.name, "issue": "missing_traceability_footer"})
            continue
        if not isinstance(footer, dict):
            violations.append({
                "file": json_file.name,
                "issue": "traceability_footer_not_a_dict",
                "actual_type": type(footer).__name__,
            })
            continue
        primary = footer.get("primary_sources")
        if not isinstance(primary, list) or not primary:
            violations.append({
                "file": json_file.name,
                "issue": "primary_sources_missing_or_empty",
            })

    if violations:
        return PredicateResult(
            passed=False,
            failure_category=CROSS_ARTIFACT_INCONSISTENCY,
            reason=(
                f"{len(violations)} section file(s) in {sections_resolved} are missing "
                f"a non-empty traceability footer: "
                f"{[v['file'] for v in violations]}.  "
                "Every section must have traceability_footer.primary_sources non-empty "
                "(gate_rules_library_plan.md §4.4, artifact_schema_specification §3)."
            ),
            details={
                "sections_path": str(sections_resolved),
                "files_checked": len(json_files),
                "violations": violations,
            },
        )

    return PredicateResult(
        passed=True,
        details={
            "sections_path": str(sections_resolved),
            "files_checked": len(json_files),
        },
    )


def wp_budget_coverage_match(
    wp_path: PathLike,
    budget_path: PathLike,
    *,
    repo_root: Optional[Path] = None,
) -> PredicateResult:
    """
    Pass iff every WP identifier in the Phase 3 output exists as a budget
    entry in the received budget response.

    Contract (gate_rules_library_plan.md §4.4)
    -------------------------------------------
    Pass condition:
        * every wp_id from wp_structure.json appears as a ``wp_id`` value
          at any nesting level in the JSON files under budget_path

    budget_path is an external integration directory (exception class 2,
    artifact_schema_specification.yaml §0).

    Budget scanning strategy
    ------------------------
    The budget response format is not yet defined (interface_contract.json
    is empty {}).  All string values of the ``wp_id`` field at any nesting
    depth in the budget response files are collected and checked.  See module
    docstring for the rationale.

    Gate usage: g08_p05 (gate_09_budget_consistency)

    Failure categories
    ------------------
    ``MISSING_MANDATORY_INPUT``      — wp_path or budget_path absent
    ``MALFORMED_ARTIFACT``           — invalid JSON in wp_structure / work_packages wrong type
    ``CROSS_ARTIFACT_INCONSISTENCY`` — a WP has no corresponding budget entry
    """
    wp_resolved = resolve_repo_path(wp_path, repo_root)
    budget_resolved = resolve_repo_path(budget_path, repo_root)

    wp_data, err = _read_json_object(wp_resolved)
    if err is not None:
        return err

    wp_ids, err = _extract_wp_ids(wp_data, wp_resolved)
    if err is not None:
        return err

    budget_wp_ids, err = _scan_budget_dir(budget_resolved, "wp_id")
    if err is not None:
        return err

    if not wp_ids:
        return PredicateResult(
            passed=True,
            details={
                "wp_path": str(wp_resolved),
                "budget_path": str(budget_resolved),
                "wps_checked": 0,
                "note": "No WP IDs found in wp_structure.json; vacuous pass.",
            },
        )

    missing = sorted(wp_ids - budget_wp_ids)
    if missing:
        return PredicateResult(
            passed=False,
            failure_category=CROSS_ARTIFACT_INCONSISTENCY,
            reason=(
                f"{len(missing)} WP(s) from {wp_resolved} have no corresponding "
                f"budget entry in {budget_resolved}: {missing}.  "
                "Every WP must have a budget entry in the received budget response "
                "(gate_rules_library_plan.md §4.4)."
            ),
            details={
                "wp_path": str(wp_resolved),
                "budget_path": str(budget_resolved),
                "wps_in_structure": sorted(wp_ids),
                "wps_in_budget": sorted(budget_wp_ids),
                "missing_from_budget": missing,
            },
        )

    return PredicateResult(
        passed=True,
        details={
            "wp_path": str(wp_resolved),
            "budget_path": str(budget_resolved),
            "wps_checked": len(wp_ids),
        },
    )


def partner_budget_coverage_match(
    partners_path: PathLike,
    budget_path: PathLike,
    *,
    repo_root: Optional[Path] = None,
) -> PredicateResult:
    """
    Pass iff every partner identifier in Tier 3 partners.json has a
    corresponding effort or cost allocation in the received budget response.

    Contract (gate_rules_library_plan.md §4.4)
    -------------------------------------------
    Pass condition:
        * every partner_id from partners.json appears as a ``partner_id`` value
          at any nesting level in the JSON files under budget_path

    budget_path is an external integration directory (exception class 2).
    Budget scanning strategy: same deep-scan as wp_budget_coverage_match.

    Gate usage: g08_p06 (gate_09_budget_consistency)

    Failure categories
    ------------------
    ``MISSING_MANDATORY_INPUT``      — partners_path or budget_path absent
    ``MALFORMED_ARTIFACT``           — invalid JSON / unsupported partners.json structure
    ``CROSS_ARTIFACT_INCONSISTENCY`` — a partner has no corresponding budget allocation
    """
    partners_resolved = resolve_repo_path(partners_path, repo_root)
    budget_resolved = resolve_repo_path(budget_path, repo_root)

    partners_parsed, err = _read_json_any(partners_resolved)
    if err is not None:
        return err

    tier3_ids, err = _extract_partner_ids(partners_parsed, partners_resolved)
    if err is not None:
        return err

    budget_partner_ids, err = _scan_budget_dir(budget_resolved, "partner_id")
    if err is not None:
        return err

    if not tier3_ids:
        return PredicateResult(
            passed=True,
            details={
                "partners_path": str(partners_resolved),
                "budget_path": str(budget_resolved),
                "partners_checked": 0,
                "note": "No partner IDs found in partners.json; vacuous pass.",
            },
        )

    missing = sorted(tier3_ids - budget_partner_ids)
    if missing:
        return PredicateResult(
            passed=False,
            failure_category=CROSS_ARTIFACT_INCONSISTENCY,
            reason=(
                f"{len(missing)} partner(s) from {partners_resolved} have no "
                f"corresponding budget allocation in {budget_resolved}: {missing}.  "
                "Every Tier 3 partner must have a budget allocation in the received "
                "budget response (gate_rules_library_plan.md §4.4)."
            ),
            details={
                "partners_path": str(partners_resolved),
                "budget_path": str(budget_resolved),
                "partners_in_tier3": sorted(tier3_ids),
                "partners_in_budget": sorted(budget_partner_ids),
                "missing_from_budget": missing,
            },
        )

    return PredicateResult(
        passed=True,
        details={
            "partners_path": str(partners_resolved),
            "budget_path": str(budget_resolved),
            "partners_checked": len(tier3_ids),
        },
    )
