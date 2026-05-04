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
    - Proposal prose may reference entities by ID alone without
      repeating full titles, legal names, or due months every time.
      Predicates only fail on *contradictory* explicit attachments,
      not on absent contextual information.
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
# Prose-aware matching helpers
# ---------------------------------------------------------------------------

_STOP_WORDS = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "has", "in", "is", "it", "its", "of", "on", "or", "that", "the",
    "to", "was", "were", "will", "with",
})


def _content_words(text: str) -> set[str]:
    """Extract non-stop content words from text, lowercased."""
    return {
        w for w in re.findall(r'[a-zA-Z][\w-]*', text.lower())
        if w not in _STOP_WORDS
    }


def _is_title_attempt(canonical_title: str, appositive: str) -> bool:
    """Heuristic: does *appositive* look like an attempt to state a title?

    Returns True when either direction meets the 50% threshold:
    - >=50% of the appositive's content words appear in canonical, OR
    - >=50% of the canonical title's content words appear in appositive.

    The bidirectional check ensures that long sentences containing the
    title words are still detected even when diluted by trailing prose.
    """
    appos_words = _content_words(appositive)
    if not appos_words:
        return False
    canon_words = _content_words(canonical_title)
    if not canon_words:
        return False
    shared = canon_words & appos_words
    return (len(shared) / len(appos_words) >= 0.5
            or len(shared) / len(canon_words) >= 0.5)


def _title_matches(canonical: str, found: str) -> bool:
    """Check if *found* text is compatible with *canonical* via substring containment."""
    c = canonical.lower().strip()
    f = found.lower().strip()
    return c in f or f in c


def _find_appositives(id_str: str, content: str) -> list[str]:
    """Find title-like text explicitly attached to *id_str* via :, em-dash, en-dash, or parenthetical.

    Only returns text fragments >= 15 chars (filters out short role
    phrases like "(coordinator)").
    """
    pattern = re.compile(
        re.escape(id_str)
        + r'\s*(?:[:]\s+|[—–]\s*|\(\s*)'
        + r'([^.;)\n]{15,}?)'
        + r'(?:[.;)\n]|$)',
        re.MULTILINE,
    )
    return [m.group(1).strip() for m in pattern.finditer(content)]


def _find_truncated_legal_name(legal_name: str, content: str) -> Optional[str]:
    """Return the truncated form if *legal_name* appears truncated in *content*, else None.

    A legal name is "truncated" when a multi-word prefix (>= 2 words,
    >= 10 chars) appears in the content but the full name does not.
    """
    if not legal_name or legal_name in content:
        return None
    words = legal_name.split()
    if len(words) < 2:
        return None
    for n in range(len(words) - 1, 1, -1):
        prefix = " ".join(words[:n])
        if len(prefix) >= 10 and prefix in content:
            return prefix
    return None


def _check_partner_conflation(
    short: str,
    legal: str,
    legal_to_short: dict[str, str],
    content: str,
) -> Optional[dict]:
    """Check if *short* appears with another partner's legal name in a parenthetical."""
    pattern = re.compile(re.escape(short) + r'\s*\(([^)]+)\)', re.IGNORECASE)
    for m in pattern.finditer(content):
        paren_text = m.group(1).strip()
        if len(paren_text) < 10:
            continue
        for other_legal, other_short in legal_to_short.items():
            if other_short != short and other_legal.lower() in paren_text.lower():
                return {
                    "partner": short,
                    "expected_legal_name": legal,
                    "found_conflation": paren_text,
                    "conflated_with": other_short,
                    "issue": (
                        f"Partner conflation: {short} appears with "
                        f"{other_short}'s legal name '{other_legal}' "
                        f"in parenthetical"
                    ),
                }
    return None


def _extract_attached_wps(did: str, content: str) -> list[str]:
    """Find WP IDs explicitly attached to deliverable *did*.

    Detects parenthetical, slash, and comma-attached patterns in both
    directions (did before WP, WP before did).
    """
    wps: list[str] = []
    # Parenthetical after deliverable ID: D2-01 (WP3)
    for m in re.finditer(re.escape(did) + r'\s*\(([^)]*)\)', content):
        wps.extend(re.findall(r'WP\d+', m.group(1)))
    # Slash or comma directly after: D2-01/WP3, D2-01, WP3
    for m in re.finditer(re.escape(did) + r'\s*[/,]\s*(WP\d+)', content):
        wps.append(m.group(1))
    # WP before deliverable (tight proximity): WP3/D2-01
    for m in re.finditer(r'(WP\d+)\s*[/,]\s*' + re.escape(did), content):
        wps.append(m.group(1))
    return wps


def _extract_attached_months(did: str, content: str) -> list[int]:
    """Find month values explicitly attached to deliverable *did*."""
    months: list[int] = []
    # Parenthetical with month: D2-01 (M18), D2-01 (month 18)
    for m in re.finditer(
        re.escape(did) + r'\s*\([^)]*?(?:month\s+|M)(\d+)[^)]*?\)',
        content, re.IGNORECASE,
    ):
        months.append(int(m.group(1)))
    # "due in/by month N" within ~60 chars: D2-01, due in month 24
    for m in re.finditer(
        re.escape(did) + r'[^.;\n]{0,60}?\bdue\s+(?:in\s+|by\s+)?(?:month\s+|M)(\d+)',
        content, re.IGNORECASE,
    ):
        months.append(int(m.group(1)))
    return months


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
    """Pass iff partner names from the canonical pack are used consistently
    in the section without corruption, truncation, or conflation.

    Does NOT require legal_name to appear alongside every short_name
    mention.  Short names from the canonical pack are valid standalone
    references in proposal prose.

    Fails only when:
        - A short_name is mapped to the wrong legal name (conflation)
        - A legal name appears in truncated / corrupted form
        - Two partners are conflated (short_name + wrong legal_name)

    Failure categories:
        MISSING_MANDATORY_INPUT -- path does not exist
        MALFORMED_ARTIFACT -- invalid JSON
        CROSS_ARTIFACT_INCONSISTENCY -- corrupted, truncated, or conflated partner name
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

    short_to_legal: dict[str, str] = {}
    legal_to_short: dict[str, str] = {}
    for p in partners:
        if not isinstance(p, dict):
            continue
        short = p.get("short_name", "")
        legal = p.get("legal_name", "")
        if short and legal:
            short_to_legal[short] = legal
            legal_to_short[legal] = short

    issues: list[dict] = []

    for p in partners:
        if not isinstance(p, dict):
            continue
        short = p.get("short_name", "")
        legal = p.get("legal_name", "")
        if not short or short not in content:
            continue

        if not legal:
            continue

        # Check 1: Truncated / corrupted legal name
        truncated = _find_truncated_legal_name(legal, content)
        if truncated:
            issues.append({
                "partner": short,
                "expected_legal_name": legal,
                "found_truncated": truncated,
                "issue": (
                    f"Legal name for {short} appears truncated: "
                    f"found '{truncated}' instead of '{legal}'"
                ),
            })

        # Check 2: Conflation — short_name appears with another partner's
        # legal name in a parenthetical
        conflation = _check_partner_conflation(
            short, legal, legal_to_short, content,
        )
        if conflation:
            issues.append(conflation)

    if issues:
        return PredicateResult(
            passed=False,
            failure_category=CROSS_ARTIFACT_INCONSISTENCY,
            reason=(
                f"Partner name issues in {resolved_section}: "
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
# deliverable_identity_preserved
# ---------------------------------------------------------------------------


# Patterns indicating exclusive/narrow deliverable purpose assignment
_EXCLUSIVE_PURPOSE_RE = re.compile(
    r'\b(?:sole(?:ly)?\s+(?:for\s+)?(?:the\s+)?(?:purpose|aim|focus|objective)'
    r'|(?:exclusively|primarily|only)\s+(?:for|to|serves?|addresses?|supports?)'
    r'|dedicated\s+(?:to|exclusively)'
    r'|the\s+single\s+purpose'
    r'|(?:is|are)\s+solely\b)\b',
    re.IGNORECASE,
)


def deliverable_identity_preserved(
    section_path: PathLike,
    canonical_pack_path: PathLike,
    *,
    repo_root: Optional[Path] = None,
) -> PredicateResult:
    """Pass iff every deliverable ID mentioned in the section is known in
    the canonical pack and no contradictory identity (wrong title, parent
    WP, or due month) is explicitly asserted.

    Does NOT require canonical title, parent WP, or due month to appear
    alongside every deliverable ID mention.  Bare ID references are valid
    in proposal prose.

    Fails only when:
        - An unknown deliverable ID appears
        - A wrong title is explicitly attached (via : — – or parenthetical)
        - A wrong parent WP is explicitly attached
        - A wrong due month is explicitly attached
        - Exclusive-purpose language narrows a multi-outcome deliverable

    Failure categories:
        MISSING_MANDATORY_INPUT -- path does not exist
        MALFORMED_ARTIFACT -- invalid JSON
        CROSS_ARTIFACT_INCONSISTENCY -- unknown ID, wrong identity, or narrowing
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

    # Build multi-outcome index
    multi_outcome_map: dict[str, list[str]] = {}
    for outcome in pack_data.get("outcomes", []):
        if not isinstance(outcome, dict):
            continue
        out_id = outcome.get("id", "")
        for linked_did in outcome.get("linked_deliverable_ids", []):
            if linked_did not in multi_outcome_map:
                multi_outcome_map[linked_did] = []
            multi_outcome_map[linked_did].append(out_id)

    issues: list[dict] = []
    mentioned_ids = set(re.findall(r'D\d+-\d+', content))

    for did in sorted(mentioned_ids):
        # Check 1: Unknown deliverable ID
        if did not in canon:
            issues.append({
                "deliverable_id": did,
                "check": "unknown_deliverable",
                "issue": (
                    f"Deliverable {did} referenced in section but "
                    f"not found in canonical reference pack"
                ),
            })
            continue

        canonical = canon[did]
        c_title = canonical.get("title", "")
        c_wp = canonical.get("parent_wp", "")
        c_month = canonical.get("due_month")

        # Check 2: Wrong title explicitly attached
        if c_title:
            for appos in _find_appositives(did, content):
                if _is_title_attempt(c_title, appos) and not _title_matches(c_title, appos):
                    issues.append({
                        "deliverable_id": did,
                        "check": "wrong_title",
                        "canonical_title": c_title,
                        "found_title": appos,
                        "issue": (
                            f"Deliverable {did} has wrong title attached: "
                            f"found '{appos}', expected '{c_title}'"
                        ),
                    })
                    break

        # Check 3: Wrong parent WP explicitly attached
        if c_wp:
            for wp in _extract_attached_wps(did, content):
                if wp != c_wp:
                    issues.append({
                        "deliverable_id": did,
                        "check": "wrong_parent_wp",
                        "canonical_parent_wp": c_wp,
                        "found_parent_wp": wp,
                        "issue": (
                            f"Deliverable {did} explicitly attached to {wp}, "
                            f"but canonical parent is {c_wp}"
                        ),
                    })
                    break

        # Check 4: Wrong due month explicitly attached
        if c_month is not None:
            for month in _extract_attached_months(did, content):
                if month != c_month:
                    issues.append({
                        "deliverable_id": did,
                        "check": "wrong_due_month",
                        "canonical_due_month": c_month,
                        "found_due_month": month,
                        "issue": (
                            f"Deliverable {did} states due month {month}, "
                            f"but canonical due month is {c_month}"
                        ),
                    })
                    break

        # Check 5: Multi-outcome narrowing
        linked_outcomes = multi_outcome_map.get(did, [])
        if len(linked_outcomes) >= 2:
            for match in re.finditer(re.escape(did), content):
                start = max(0, match.start() - 150)
                end = min(len(content), match.end() + 150)
                window = content[start:end]
                if _EXCLUSIVE_PURPOSE_RE.search(window):
                    issues.append({
                        "deliverable_id": did,
                        "check": "multi_outcome_narrowing",
                        "linked_outcome_ids": linked_outcomes,
                        "issue": (
                            f"Deliverable {did} is linked to "
                            f"{len(linked_outcomes)} outcomes "
                            f"({linked_outcomes}) but section text uses "
                            f"exclusive-purpose language near the reference"
                        ),
                    })
                    break

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
    """Pass iff canonical objective, outcome, and WP titles are not
    contradicted when explicitly attached to their IDs.

    IDs that appear alone or with short role phrases are acceptable.
    Only fails when an ID is followed by a title-like appositive (via
    :, em-dash, en-dash, or parenthetical) that contradicts the
    canonical title.

    Failure categories:
        MISSING_MANDATORY_INPUT -- path does not exist
        MALFORMED_ARTIFACT -- invalid JSON
        CROSS_ARTIFACT_INCONSISTENCY -- canonical term contradicted
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
        if not oid or not title or len(title) < 8 or oid not in content:
            continue
        for appos in _find_appositives(oid, content):
            if _is_title_attempt(title, appos) and not _title_matches(title, appos):
                issues.append({
                    "term_type": "objective_title",
                    "id": oid,
                    "canonical_title": title,
                    "found_title": appos,
                    "issue": (
                        f"Objective {oid} has wrong title attached: "
                        f"found '{appos}', expected '{title}'"
                    ),
                })
                break

    # Check outcome titles
    for outcome in pack_data.get("outcomes", []):
        if not isinstance(outcome, dict):
            continue
        out_id = outcome.get("id", "")
        title = outcome.get("title", "")
        if not out_id or not title or len(title) < 8 or out_id not in content:
            continue
        for appos in _find_appositives(out_id, content):
            if _is_title_attempt(title, appos) and not _title_matches(title, appos):
                issues.append({
                    "term_type": "outcome_title",
                    "id": out_id,
                    "canonical_title": title,
                    "found_title": appos,
                    "issue": (
                        f"Outcome {out_id} has wrong title attached: "
                        f"found '{appos}', expected '{title}'"
                    ),
                })
                break

    # Check WP titles
    for wp in pack_data.get("wps", []):
        if not isinstance(wp, dict):
            continue
        wid = wp.get("wp_id", "")
        title = wp.get("title", "")
        if not wid or not title or len(title) < 8 or wid not in content:
            continue
        for appos in _find_appositives(wid, content):
            if _is_title_attempt(title, appos) and not _title_matches(title, appos):
                issues.append({
                    "term_type": "wp_title",
                    "id": wid,
                    "canonical_title": title,
                    "found_title": appos,
                    "issue": (
                        f"WP {wid} has wrong title attached: "
                        f"found '{appos}', expected '{title}'"
                    ),
                })
                break

    if issues:
        return PredicateResult(
            passed=False,
            failure_category=CROSS_ARTIFACT_INCONSISTENCY,
            reason=(
                f"Canonical term issues in {resolved_section}: "
                f"{len(issues)} term(s) with wrong titles"
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

# Patterns that claim comprehensive objective coverage
_ALL_OBJECTIVES_RE = re.compile(
    r'\b(?:all\s+(?:project\s+)?objectives'
    r'|all\s+measurable\s+objectives'
    r'|project\s+objectives\s+(?:are|include|comprise)'
    r'|each\s+(?:of\s+the\s+)?(?:project\s+)?objectives)\b',
    re.IGNORECASE,
)


def _extract_quantitative_components(target: str) -> list[str]:
    """Extract all quantitative tokens from a measurable_target string.

    Returns patterns like '≥500', '≥2', '≥30%', '≤5%'.
    """
    return _QUANTITATIVE_RE.findall(target)


def _detect_section_type(resolved_path: Path) -> str:
    """Detect section type from the file name.

    Returns 'excellence', 'impact', 'implementation', or 'unknown'.
    """
    name = resolved_path.name.lower()
    if "excellence" in name:
        return "excellence"
    if "impact" in name:
        return "impact"
    if "implementation" in name:
        return "implementation"
    return "unknown"


def _check_quantitative_components(
    content: str, target: str, oid: str,
) -> Optional[dict]:
    """Check all quantitative components of a measurable_target are in content.

    Returns an issue dict if components are missing, None otherwise.
    """
    components = _extract_quantitative_components(target)
    if not components:
        return None

    missing = []
    content_nospace = content.replace(" ", "")
    for comp in components:
        comp_normalized = comp.replace(" ", "")
        if comp_normalized not in content_nospace:
            bare = re.sub(r'^[≥≤><]\s*', '', comp)
            if bare not in content:
                missing.append(comp)

    if missing:
        return {
            "objective_id": oid,
            "measurable_target": target,
            "missing_components": missing,
            "total_components": len(components),
            "issue": (
                f"Objective {oid} referenced but "
                f"{len(missing)}/{len(components)} metric "
                f"components missing: {missing}"
            ),
        }
    return None


def measurable_targets_preserved(
    section_path: PathLike,
    canonical_pack_path: PathLike,
    *,
    repo_root: Optional[Path] = None,
) -> PredicateResult:
    """Pass iff measurable targets are faithfully preserved in the section.

    Three enforcement modes based on section type:

    **Excellence**: If the section claims coverage of all objectives
    (via phrases like "all objectives", "all project objectives",
    "each of the objectives"), every canonical objective ID must appear
    and every objective's quantitative metric components must be present.
    For individually-mentioned objectives, all metric components are required.

    **Impact**: For individually-mentioned objective IDs, all quantitative
    metric components must be present.  Additionally, for any outcome ID
    mentioned in the section, objectives linked to that outcome (via the
    canonical pack's ``outcomes[].linked_objectives``) are also required
    to have their metrics present.

    **Implementation**: Only enforces metric preservation for objectives
    that are individually mentioned by ID.  Does not require full
    measurable target reproduction for "all objectives" claims since the
    implementation section may focus on WP/timeline/resources.

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

    section_type = _detect_section_type(resolved_section)
    objectives = [o for o in pack_data.get("objectives", []) if isinstance(o, dict)]
    outcomes = [o for o in pack_data.get("outcomes", []) if isinstance(o, dict)]

    issues: list[dict] = []

    # Build objective lookup
    obj_by_id: dict[str, dict] = {}
    for obj in objectives:
        oid = obj.get("id", "")
        if oid:
            obj_by_id[oid] = obj

    # Determine which objectives must be checked
    must_check_ids: set[str] = set()

    # 1. Always check objectives explicitly mentioned by ID
    for oid in obj_by_id:
        if oid in content:
            must_check_ids.add(oid)

    # 2. Excellence: if "all objectives" claim, require ALL objective IDs
    claims_all = bool(_ALL_OBJECTIVES_RE.search(content))
    if section_type == "excellence" and claims_all:
        missing_ids = [
            oid for oid in obj_by_id if oid not in content
        ]
        if missing_ids:
            issues.append({
                "check": "all_objectives_claim",
                "missing_objective_ids": missing_ids,
                "issue": (
                    f"Section claims 'all objectives' but omits "
                    f"{len(missing_ids)} objective ID(s): {missing_ids}"
                ),
            })
        # All objectives are now candidates for metric checking
        must_check_ids = set(obj_by_id.keys())

    # 3. Impact: objectives linked to mentioned outcomes are also required
    if section_type == "impact":
        for outcome in outcomes:
            out_id = outcome.get("id", "")
            if out_id and out_id in content:
                for linked_oid in outcome.get("linked_objectives", []):
                    if linked_oid in obj_by_id:
                        must_check_ids.add(linked_oid)

    # 4. Check quantitative components for all must-check objectives
    for oid in sorted(must_check_ids):
        obj = obj_by_id.get(oid)
        if not obj:
            continue
        target = obj.get("measurable_target", "")
        if not target:
            continue
        issue = _check_quantitative_components(content, target, oid)
        if issue:
            issues.append(issue)

    if issues:
        return PredicateResult(
            passed=False,
            failure_category=CROSS_ARTIFACT_INCONSISTENCY,
            reason=(
                f"Measurable target metric loss in {resolved_section}: "
                f"{len(issues)} issue(s)"
            ),
            details={
                "section_path": str(resolved_section),
                "canonical_pack_path": str(resolved_pack),
                "section_type": section_type,
                "issues": issues,
            },
        )
    return PredicateResult(passed=True)
