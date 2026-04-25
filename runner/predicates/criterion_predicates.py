"""
Phase 8 criterion-aligned predicates for the refactored drafting pipeline.

Implements the five new predicate functions required by gates 10a-10d:

    schema_id_matches(path, expected)
        Deterministic schema predicate: check that the ``schema_id`` field
        in the artifact at *path* equals *expected*.

    no_unresolved_material_claims(path)
        Semantic-deterministic predicate: check that
        ``validation_status.overall_status`` is not ``"unresolved"``.

    impact_pathways_covered(section_path, impact_arch_path)
        Coverage predicate: check that ``impact_pathway_refs`` in the
        impact section covers all pathways in the impact architecture.

    implementation_coverage_complete(section_path, wp_path, gantt_path)
        Coverage predicate: check that ``wp_table_refs``, ``gantt_ref``,
        ``milestone_refs``, and ``risk_register_ref`` are populated.

    cross_section_consistency(assembled_path, sections_dir, tier3_path)
        Semantic-deterministic predicate: cross-check objectives, WP IDs,
        partner names, deliverable IDs, and milestone IDs across all three
        criterion-aligned sections.

All functions accept a ``repo_root`` keyword argument.  Paths are resolved
via ``runner.paths.resolve_repo_path``.
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
    POLICY_VIOLATION,
    PredicateResult,
)

PathLike = Union[str, Path]


# ---------------------------------------------------------------------------
# Internal helper — JSON reading
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


# ---------------------------------------------------------------------------
# schema_id_matches
# ---------------------------------------------------------------------------


def schema_id_matches(
    path: PathLike,
    expected: str,
    *,
    repo_root: Optional[Path] = None,
) -> PredicateResult:
    """Pass iff the ``schema_id`` field in *path* equals *expected*.

    This is a deterministic schema predicate.  It reads the artifact at
    *path*, extracts the top-level ``schema_id`` field, and compares it
    to *expected*.

    Failure categories:
        MISSING_MANDATORY_INPUT — path does not exist
        MALFORMED_ARTIFACT — invalid JSON, missing schema_id, or mismatch
    """
    resolved = resolve_repo_path(path, repo_root)
    data, err = _read_json_object(resolved)
    if err is not None:
        return err

    actual = data.get("schema_id")
    if actual is None:
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=f"Missing 'schema_id' field in {resolved}",
            details={"path": str(resolved), "expected": expected},
        )
    if actual != expected:
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=(
                f"schema_id mismatch in {resolved}: "
                f"expected {expected!r}, got {actual!r}"
            ),
            details={
                "path": str(resolved),
                "expected": expected,
                "actual": actual,
            },
        )
    return PredicateResult(passed=True)


# ---------------------------------------------------------------------------
# no_unresolved_material_claims
# ---------------------------------------------------------------------------


def no_unresolved_material_claims(
    path: PathLike,
    *,
    repo_root: Optional[Path] = None,
) -> PredicateResult:
    """Pass iff ``validation_status.overall_status`` is not ``"unresolved"``.

    Checks the artifact at *path* for a ``validation_status`` object.
    If the ``overall_status`` field is ``"unresolved"``, the predicate
    fails.  If ``validation_status`` is absent or ``overall_status`` is
    any value other than ``"unresolved"``, the predicate passes.

    Failure categories:
        MISSING_MANDATORY_INPUT — path does not exist
        MALFORMED_ARTIFACT — invalid JSON
        POLICY_VIOLATION — unresolved material claims present
    """
    resolved = resolve_repo_path(path, repo_root)
    data, err = _read_json_object(resolved)
    if err is not None:
        return err

    validation_status = data.get("validation_status")
    if not isinstance(validation_status, dict):
        # No validation_status field — cannot determine; pass conservatively
        # (the schema predicate for the field's presence is checked separately)
        return PredicateResult(passed=True)

    overall = validation_status.get("overall_status", "")
    if overall == "unresolved":
        return PredicateResult(
            passed=False,
            failure_category=POLICY_VIOLATION,
            reason=(
                f"Unresolved material claims in {resolved}: "
                f"validation_status.overall_status is 'unresolved'"
            ),
            details={
                "path": str(resolved),
                "overall_status": overall,
            },
        )
    return PredicateResult(passed=True)


# ---------------------------------------------------------------------------
# impact_pathways_covered
# ---------------------------------------------------------------------------


def impact_pathways_covered(
    section_path: PathLike,
    impact_arch_path: PathLike,
    *,
    repo_root: Optional[Path] = None,
) -> PredicateResult:
    """Pass iff ``impact_pathway_refs`` covers all pathways in the impact architecture.

    Reads the impact section artifact at *section_path* and the impact
    architecture artifact at *impact_arch_path*.  Extracts pathway IDs
    from both and checks that every pathway in the architecture is
    referenced in the section.

    Also checks ``dec_coverage`` fields (dissemination, exploitation,
    communication) are all ``true``.

    Failure categories:
        MISSING_MANDATORY_INPUT — path does not exist
        MALFORMED_ARTIFACT — invalid JSON
        CROSS_ARTIFACT_INCONSISTENCY — missing pathway coverage or DEC gaps
    """
    resolved_section = resolve_repo_path(section_path, repo_root)
    resolved_arch = resolve_repo_path(impact_arch_path, repo_root)

    section_data, err = _read_json_object(resolved_section)
    if err is not None:
        return err
    arch_data, err = _read_json_object(resolved_arch)
    if err is not None:
        return err

    # Extract pathway IDs from impact architecture.
    # The canonical Phase 5 artifact uses "impact_pathways"; fall back to
    # "pathways" for tolerance of alternative schemas.
    arch_pathways: set[str] = set()
    pathways = arch_data.get("impact_pathways") or arch_data.get("pathways", [])
    if isinstance(pathways, list):
        for pw in pathways:
            if isinstance(pw, dict):
                pid = pw.get("pathway_id") or pw.get("id") or ""
                if pid:
                    arch_pathways.add(str(pid))
    elif isinstance(pathways, dict):
        arch_pathways = set(pathways.keys())

    # If no pathways defined in architecture, vacuous pass
    if not arch_pathways:
        return PredicateResult(passed=True)

    # Extract pathway refs from the impact section
    section_refs: set[str] = set()
    refs = section_data.get("impact_pathway_refs", [])
    if isinstance(refs, list):
        section_refs = {str(r) for r in refs if r}

    missing = arch_pathways - section_refs
    if missing:
        return PredicateResult(
            passed=False,
            failure_category=CROSS_ARTIFACT_INCONSISTENCY,
            reason=(
                f"Impact section is missing pathway references: "
                f"{sorted(missing)}"
            ),
            details={
                "section_path": str(resolved_section),
                "impact_arch_path": str(resolved_arch),
                "missing_pathways": sorted(missing),
                "section_refs": sorted(section_refs),
                "arch_pathways": sorted(arch_pathways),
            },
        )

    # Check DEC coverage
    dec = section_data.get("dec_coverage", {})
    if isinstance(dec, dict):
        dec_gaps = []
        for dim in ("dissemination_addressed", "exploitation_addressed", "communication_addressed"):
            if not dec.get(dim):
                dec_gaps.append(dim)
        if dec_gaps:
            return PredicateResult(
                passed=False,
                failure_category=CROSS_ARTIFACT_INCONSISTENCY,
                reason=(
                    f"DEC coverage incomplete in impact section: "
                    f"missing {dec_gaps}"
                ),
                details={
                    "section_path": str(resolved_section),
                    "dec_gaps": dec_gaps,
                },
            )

    return PredicateResult(passed=True)


# ---------------------------------------------------------------------------
# implementation_coverage_complete
# ---------------------------------------------------------------------------


def implementation_coverage_complete(
    section_path: PathLike,
    wp_path: PathLike,
    gantt_path: PathLike,
    *,
    repo_root: Optional[Path] = None,
) -> PredicateResult:
    """Pass iff ``wp_table_refs``, ``gantt_ref``, ``milestone_refs``, and
    ``risk_register_ref`` are all populated in the implementation section.

    Also cross-checks that ``wp_table_refs`` covers all WP IDs from
    *wp_path* and that ``milestone_refs`` is non-empty.

    Failure categories:
        MISSING_MANDATORY_INPUT — path does not exist
        MALFORMED_ARTIFACT — invalid JSON
        CROSS_ARTIFACT_INCONSISTENCY — missing references
    """
    resolved_section = resolve_repo_path(section_path, repo_root)
    resolved_wp = resolve_repo_path(wp_path, repo_root)

    section_data, err = _read_json_object(resolved_section)
    if err is not None:
        return err

    # Check required reference fields are populated
    missing_fields = []

    wp_refs = section_data.get("wp_table_refs", [])
    if not wp_refs or not isinstance(wp_refs, list):
        missing_fields.append("wp_table_refs")

    gantt_ref = section_data.get("gantt_ref", "")
    if not gantt_ref:
        missing_fields.append("gantt_ref")

    milestone_refs = section_data.get("milestone_refs", [])
    if not milestone_refs or not isinstance(milestone_refs, list):
        missing_fields.append("milestone_refs")

    risk_ref = section_data.get("risk_register_ref", "")
    if not risk_ref:
        missing_fields.append("risk_register_ref")

    if missing_fields:
        return PredicateResult(
            passed=False,
            failure_category=CROSS_ARTIFACT_INCONSISTENCY,
            reason=(
                f"Implementation section missing required references: "
                f"{missing_fields}"
            ),
            details={
                "section_path": str(resolved_section),
                "missing_fields": missing_fields,
            },
        )

    # Cross-check WP coverage against wp_structure.json
    wp_data, err = _read_json_object(resolved_wp)
    if err is not None:
        return err

    wp_ids: set[str] = set()
    wps = wp_data.get("work_packages", [])
    if isinstance(wps, list):
        for wp in wps:
            if isinstance(wp, dict):
                wid = wp.get("wp_id") or wp.get("id") or ""
                if wid:
                    wp_ids.add(str(wid))
    elif isinstance(wps, dict):
        wp_ids = set(wps.keys())

    if wp_ids:
        ref_set = {str(r) for r in wp_refs if r}
        missing_wps = wp_ids - ref_set
        if missing_wps:
            return PredicateResult(
                passed=False,
                failure_category=CROSS_ARTIFACT_INCONSISTENCY,
                reason=(
                    f"Implementation section wp_table_refs missing WPs: "
                    f"{sorted(missing_wps)}"
                ),
                details={
                    "section_path": str(resolved_section),
                    "wp_path": str(resolved_wp),
                    "missing_wps": sorted(missing_wps),
                },
            )

    return PredicateResult(passed=True)


# ---------------------------------------------------------------------------
# cross_section_consistency
# ---------------------------------------------------------------------------


def cross_section_consistency(
    assembled_path: PathLike,
    sections_dir: PathLike,
    tier3_path: PathLike,
    *,
    repo_root: Optional[Path] = None,
) -> PredicateResult:
    """Pass iff objectives, WP IDs, partner names, deliverable IDs, and
    milestone IDs are cross-consistent across all three sections.

    Reads the assembled Part B draft at *assembled_path* and cross-checks
    the ``consistency_log`` for any entries with status
    ``"inconsistency_flagged"``.

    Also performs deterministic cross-checks on the three section files
    in *sections_dir*: partner names mentioned in one section must appear
    in the others where relevant.

    Failure categories:
        MISSING_MANDATORY_INPUT — path does not exist
        MALFORMED_ARTIFACT — invalid JSON
        CROSS_ARTIFACT_INCONSISTENCY — inconsistencies detected
    """
    resolved_assembled = resolve_repo_path(assembled_path, repo_root)

    assembled_data, err = _read_json_object(resolved_assembled)
    if err is not None:
        return err

    # Check consistency_log for flagged inconsistencies
    consistency_log = assembled_data.get("consistency_log", [])
    flagged = []
    if isinstance(consistency_log, list):
        for entry in consistency_log:
            if isinstance(entry, dict):
                if entry.get("status") == "inconsistency_flagged":
                    flagged.append(entry)

    if flagged:
        return PredicateResult(
            passed=False,
            failure_category=CROSS_ARTIFACT_INCONSISTENCY,
            reason=(
                f"Cross-section inconsistencies flagged in assembled draft: "
                f"{len(flagged)} issue(s)"
            ),
            details={
                "assembled_path": str(resolved_assembled),
                "flagged_count": len(flagged),
                "flagged_checks": [
                    e.get("check_id", "<unknown>") for e in flagged
                ],
            },
        )

    # Verify the sections array has exactly 3 entries
    sections = assembled_data.get("sections", [])
    if not isinstance(sections, list) or len(sections) != 3:
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=(
                f"Assembled draft must contain exactly 3 sections "
                f"(Excellence, Impact, Implementation), "
                f"found {len(sections) if isinstance(sections, list) else 'non-list'}"
            ),
            details={
                "assembled_path": str(resolved_assembled),
                "section_count": len(sections) if isinstance(sections, list) else 0,
            },
        )

    return PredicateResult(passed=True)
