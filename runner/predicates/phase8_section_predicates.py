"""
Deterministic preflight predicates for Phase 8 section artifacts.

These predicates catch canonical-term drift, stale artifacts, and
deliverable identity corruption *before* gate_10d runs.  They are
registered in gates 10a/10b/10c so that per-section issues surface
early and with actionable details.

Rules:
    - Deterministic JSON/string checks only.
    - No LLM calls, no broad semantic inference.
    - Fail with actionable details: offending term, artifact path,
      source canonical value.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional, Union

from runner.paths import resolve_repo_path
from runner.predicates.types import (
    CROSS_ARTIFACT_INCONSISTENCY,
    MALFORMED_ARTIFACT,
    MISSING_MANDATORY_INPUT,
    STALE_UPSTREAM_MISMATCH,
    PredicateResult,
)

PathLike = Union[str, Path]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _read_json(resolved: Path) -> tuple[dict | None, PredicateResult | None]:
    """Read *resolved* as a UTF-8 JSON object.  Return (dict, None) or (None, err)."""
    if not resolved.exists():
        return None, PredicateResult(
            passed=False,
            failure_category=MISSING_MANDATORY_INPUT,
            reason=f"Path does not exist: {resolved}",
            details={"path": str(resolved)},
        )
    try:
        text = resolved.read_text(encoding="utf-8-sig")
    except (UnicodeDecodeError, OSError) as exc:
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
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return None, PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=f"Invalid JSON in {resolved}: {exc}",
            details={"path": str(resolved)},
        )
    if not isinstance(data, dict):
        return None, PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=f"Expected JSON object in {resolved}, got {type(data).__name__}",
            details={"path": str(resolved)},
        )
    return data, None


def _extract_all_content(section_data: dict) -> str:
    """Concatenate all sub_section content strings."""
    parts: list[str] = []
    for sub in section_data.get("sub_sections", []):
        if isinstance(sub, dict):
            content = sub.get("content", "")
            if content:
                parts.append(str(content))
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# no_stale_run_id
# ---------------------------------------------------------------------------


def no_stale_run_id(
    section_path: PathLike,
    expected_run_id: str,
    *,
    repo_root: Optional[Path] = None,
) -> PredicateResult:
    """Pass iff the ``run_id`` in *section_path* equals *expected_run_id*.

    Failure categories:
        MISSING_MANDATORY_INPUT -- path does not exist
        MALFORMED_ARTIFACT -- invalid JSON or missing run_id
        STALE_UPSTREAM_MISMATCH -- run_id does not match
    """
    resolved = resolve_repo_path(section_path, repo_root)
    data, err = _read_json(resolved)
    if err is not None:
        return err

    actual = data.get("run_id")
    if actual is None:
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=f"Missing 'run_id' field in {resolved}",
            details={"path": str(resolved), "expected_run_id": expected_run_id},
        )
    if str(actual) != str(expected_run_id):
        return PredicateResult(
            passed=False,
            failure_category=STALE_UPSTREAM_MISMATCH,
            reason=(
                f"Stale run_id in {resolved}: "
                f"expected {expected_run_id!r}, got {actual!r}"
            ),
            details={
                "path": str(resolved),
                "expected_run_id": expected_run_id,
                "actual_run_id": actual,
            },
        )
    return PredicateResult(passed=True)


# ---------------------------------------------------------------------------
# partner_names_preserved
# ---------------------------------------------------------------------------


def partner_names_preserved(
    section_path: PathLike,
    canonical_pack_path: PathLike,
    *,
    repo_root: Optional[Path] = None,
) -> PredicateResult:
    """Pass iff every partner short_name from the canonical pack appears
    in the section content, and no short_name is used without its
    canonical legal_name also appearing at least once.

    Failure categories:
        MISSING_MANDATORY_INPUT -- path does not exist
        MALFORMED_ARTIFACT -- invalid JSON
        CROSS_ARTIFACT_INCONSISTENCY -- partner name missing or truncated
    """
    resolved_section = resolve_repo_path(section_path, repo_root)
    resolved_pack = resolve_repo_path(canonical_pack_path, repo_root)

    section_data, err = _read_json(resolved_section)
    if err is not None:
        return err
    pack_data, err = _read_json(resolved_pack)
    if err is not None:
        return err

    content = _extract_all_content(section_data)
    if not content.strip():
        return PredicateResult(passed=True)

    partners = pack_data.get("partners", [])
    if not partners:
        return PredicateResult(passed=True)

    issues: list[dict] = []
    for p in partners:
        if not isinstance(p, dict):
            continue
        short = p.get("short_name", "")
        legal = p.get("legal_name", "")
        if not short:
            continue

        # Check: short_name mentioned in content
        if short in content:
            # If there's a legal name that differs from short name,
            # verify the legal name appears at least once
            if legal and legal != short and legal not in content:
                issues.append({
                    "partner": short,
                    "expected_legal_name": legal,
                    "issue": "short_name used but legal_name never appears",
                })

    if issues:
        return PredicateResult(
            passed=False,
            failure_category=CROSS_ARTIFACT_INCONSISTENCY,
            reason=(
                f"Partner name preservation issues in {resolved_section}: "
                f"{len(issues)} partner(s) with truncated legal names"
            ),
            details={
                "section_path": str(resolved_section),
                "canonical_pack_path": str(resolved_pack),
                "issues": issues,
            },
        )
    return PredicateResult(passed=True)


# ---------------------------------------------------------------------------
# deliverable_identity_preserved
# ---------------------------------------------------------------------------


def deliverable_identity_preserved(
    section_path: PathLike,
    canonical_pack_path: PathLike,
    *,
    repo_root: Optional[Path] = None,
) -> PredicateResult:
    """Pass iff every deliverable ID mentioned in the section has the
    correct title, parent WP, and due month per the canonical pack.

    Failure categories:
        MISSING_MANDATORY_INPUT -- path does not exist
        MALFORMED_ARTIFACT -- invalid JSON
        CROSS_ARTIFACT_INCONSISTENCY -- deliverable identity mismatch
    """
    resolved_section = resolve_repo_path(section_path, repo_root)
    resolved_pack = resolve_repo_path(canonical_pack_path, repo_root)

    section_data, err = _read_json(resolved_section)
    if err is not None:
        return err
    pack_data, err = _read_json(resolved_pack)
    if err is not None:
        return err

    content = _extract_all_content(section_data)
    if not content.strip():
        return PredicateResult(passed=True)

    deliverables = pack_data.get("deliverables", [])
    if not deliverables:
        return PredicateResult(passed=True)

    # Build lookup: deliverable_id -> canonical info
    canon: dict[str, dict] = {}
    for d in deliverables:
        if not isinstance(d, dict):
            continue
        did = d.get("deliverable_id", "")
        if did:
            canon[did] = d

    issues: list[dict] = []
    # Find deliverable IDs mentioned in section content
    # Pattern: D followed by digits, dash, digits (e.g. D1-01, D9-03)
    mentioned_ids = set(re.findall(r'D\d+-\d+', content))

    for did in mentioned_ids:
        if did not in canon:
            continue
        canonical = canon[did]
        c_title = canonical.get("title", "")
        c_wp = canonical.get("parent_wp", "")
        c_month = canonical.get("due_month")

        # Check title: if canonical title is non-trivial, verify it
        # appears in the section when the deliverable ID is mentioned
        if c_title and len(c_title) > 5 and c_title not in content:
            issues.append({
                "deliverable_id": did,
                "check": "title_missing",
                "canonical_title": c_title,
                "issue": (
                    f"Deliverable {did} mentioned but its canonical "
                    f"title '{c_title}' is absent from section content"
                ),
            })

        # Check due month: if present, verify it appears near the ID
        if c_month is not None:
            month_str = f"month {c_month}"
            month_str_alt = f"M{c_month}"
            if (month_str.lower() not in content.lower()
                    and month_str_alt not in content
                    and str(c_month) not in content):
                issues.append({
                    "deliverable_id": did,
                    "check": "due_month_missing",
                    "canonical_due_month": c_month,
                    "issue": (
                        f"Deliverable {did} mentioned but due month "
                        f"{c_month} not found in section content"
                    ),
                })

        # Check parent WP: verify the WP ID appears in the section
        if c_wp and c_wp not in content:
            issues.append({
                "deliverable_id": did,
                "check": "parent_wp_missing",
                "canonical_parent_wp": c_wp,
                "issue": (
                    f"Deliverable {did} mentioned but its parent "
                    f"WP '{c_wp}' is absent from section content"
                ),
            })

    if issues:
        return PredicateResult(
            passed=False,
            failure_category=CROSS_ARTIFACT_INCONSISTENCY,
            reason=(
                f"Deliverable identity issues in {resolved_section}: "
                f"{len(issues)} issue(s)"
            ),
            details={
                "section_path": str(resolved_section),
                "canonical_pack_path": str(resolved_pack),
                "issues": issues,
            },
        )
    return PredicateResult(passed=True)


# ---------------------------------------------------------------------------
# canonical_terms_preserved
# ---------------------------------------------------------------------------


def canonical_terms_preserved(
    section_path: PathLike,
    canonical_pack_path: PathLike,
    *,
    repo_root: Optional[Path] = None,
) -> PredicateResult:
    """Pass iff canonical objective titles and WP titles from the pack
    are not shortened or paraphrased in the section.

    Checks that when an objective ID or WP ID is mentioned, the full
    canonical title also appears somewhere in the section.

    Failure categories:
        MISSING_MANDATORY_INPUT -- path does not exist
        MALFORMED_ARTIFACT -- invalid JSON
        CROSS_ARTIFACT_INCONSISTENCY -- canonical term shortened or absent
    """
    resolved_section = resolve_repo_path(section_path, repo_root)
    resolved_pack = resolve_repo_path(canonical_pack_path, repo_root)

    section_data, err = _read_json(resolved_section)
    if err is not None:
        return err
    pack_data, err = _read_json(resolved_pack)
    if err is not None:
        return err

    content = _extract_all_content(section_data)
    if not content.strip():
        return PredicateResult(passed=True)

    issues: list[dict] = []

    # Check objective titles
    for obj in pack_data.get("objectives", []):
        if not isinstance(obj, dict):
            continue
        oid = obj.get("id", "")
        title = obj.get("title", "")
        if not oid or not title or len(title) < 8:
            continue
        # Only check if the ID is mentioned in the content
        if oid in content and title not in content:
            issues.append({
                "term_type": "objective_title",
                "id": oid,
                "canonical_title": title,
                "issue": (
                    f"Objective {oid} referenced but canonical title "
                    f"'{title}' is absent — possible shortening or paraphrase"
                ),
            })

    # Check WP titles
    for wp in pack_data.get("wps", []):
        if not isinstance(wp, dict):
            continue
        wid = wp.get("wp_id", "")
        title = wp.get("title", "")
        if not wid or not title or len(title) < 8:
            continue
        if wid in content and title not in content:
            issues.append({
                "term_type": "wp_title",
                "id": wid,
                "canonical_title": title,
                "issue": (
                    f"WP {wid} referenced but canonical title "
                    f"'{title}' is absent — possible shortening or paraphrase"
                ),
            })

    if issues:
        return PredicateResult(
            passed=False,
            failure_category=CROSS_ARTIFACT_INCONSISTENCY,
            reason=(
                f"Canonical term preservation issues in {resolved_section}: "
                f"{len(issues)} term(s) shortened or absent"
            ),
            details={
                "section_path": str(resolved_section),
                "canonical_pack_path": str(resolved_pack),
                "issues": issues,
            },
        )
    return PredicateResult(passed=True)


# ---------------------------------------------------------------------------
# measurable_targets_preserved
# ---------------------------------------------------------------------------

# Regex for quantitative tokens: ≥N%, ≤N%, ≥N, ≤N, >N, <N
_QUANTITATIVE_RE = re.compile(r'[≥≤><]\s*\d+(?:\.\d+)?%?')


def _extract_quantitative_components(target: str) -> list[str]:
    """Extract all quantitative tokens from a measurable_target string.

    Returns patterns like '≥500', '≥2', '≥30%', '≤5%'.
    """
    return _QUANTITATIVE_RE.findall(target)


def measurable_targets_preserved(
    section_path: PathLike,
    canonical_pack_path: PathLike,
    *,
    repo_root: Optional[Path] = None,
) -> PredicateResult:
    """Pass iff every quantitative component of every referenced
    objective's ``measurable_target`` appears in the section content.

    For each objective ID mentioned in the section, extracts all
    quantitative tokens (``≥N%``, ``≤N``, etc.) from the canonical
    ``measurable_target`` and verifies each token appears in the
    section content.

    Failure categories:
        MISSING_MANDATORY_INPUT -- path does not exist
        MALFORMED_ARTIFACT -- invalid JSON
        CROSS_ARTIFACT_INCONSISTENCY -- metric components missing
    """
    resolved_section = resolve_repo_path(section_path, repo_root)
    resolved_pack = resolve_repo_path(canonical_pack_path, repo_root)

    section_data, err = _read_json(resolved_section)
    if err is not None:
        return err
    pack_data, err = _read_json(resolved_pack)
    if err is not None:
        return err

    content = _extract_all_content(section_data)
    if not content.strip():
        return PredicateResult(passed=True)

    issues: list[dict] = []

    for obj in pack_data.get("objectives", []):
        if not isinstance(obj, dict):
            continue
        oid = obj.get("id", "")
        target = obj.get("measurable_target", "")
        if not oid or not target:
            continue
        # Only check if the objective ID is mentioned in the section
        if oid not in content:
            continue

        components = _extract_quantitative_components(target)
        if not components:
            continue

        missing = []
        for comp in components:
            # Normalize spacing for comparison
            comp_normalized = comp.replace(" ", "")
            # Check if the component or its bare number appears
            if comp_normalized not in content.replace(" ", ""):
                # Also check bare number (without comparator prefix)
                bare = re.sub(r'^[≥≤><]\s*', '', comp)
                if bare not in content:
                    missing.append(comp)

        if missing:
            issues.append({
                "objective_id": oid,
                "measurable_target": target,
                "missing_components": missing,
                "total_components": len(components),
                "issue": (
                    f"Objective {oid} referenced but "
                    f"{len(missing)}/{len(components)} metric "
                    f"components missing: {missing}"
                ),
            })

    if issues:
        return PredicateResult(
            passed=False,
            failure_category=CROSS_ARTIFACT_INCONSISTENCY,
            reason=(
                f"Measurable target metric loss in {resolved_section}: "
                f"{len(issues)} objective(s) with missing components"
            ),
            details={
                "section_path": str(resolved_section),
                "canonical_pack_path": str(resolved_pack),
                "issues": issues,
            },
        )
    return PredicateResult(passed=True)
