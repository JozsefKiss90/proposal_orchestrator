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
        Deterministic coverage predicate: cross-check objectives, WP IDs,
        partner names, deliverable IDs, metrics, and terminology across
        all three criterion-aligned sections against canonical Tier 3 and
        Tier 4 artifacts.

All functions accept a ``repo_root`` keyword argument.  Paths are resolved
via ``runner.paths.resolve_repo_path``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional, Union

from runner.claim_status import normalize_status
from runner.paths import find_repo_root, resolve_repo_path
from runner.predicates.types import (
    CROSS_ARTIFACT_INCONSISTENCY,
    MALFORMED_ARTIFACT,
    MISSING_MANDATORY_INPUT,
    POLICY_VIOLATION,
    PredicateResult,
)
from runner.working_assumptions import (
    WorkingAssumptionsError,
    declared_claim_summary,
    load_working_assumptions,
)

PathLike = Union[str, Path]

# Common legal entity suffixes for partner name truncation detection
_LEGAL_SUFFIXES = frozenset({
    "AG", "Oy", "GmbH", "Ltd", "Ltd.", "S.A.", "S.r.l.", "B.V.",
    "AB", "A.S.", "A/S", "SE", "NV", "N.V.", "SAS", "SARL",
    "Inc", "Inc.", "Corp", "Corp.", "LLC", "LLP", "PLC",
})

# Keywords indicating an objective title is a named component/system
_COMPONENT_KEYWORDS = frozenset({
    "engine", "architecture", "layer", "framework", "protocol",
    "system", "platform", "suite", "registry",
})


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
    # §12.2 names the vocabulary in title case; the roll-up derivation
    # (runner.claim_status) normalises case, so this comparison must too, or an
    # operator-authored ``'Unresolved'`` preseed sails through gate_10a (PRE-1).
    if normalize_status(overall) == "unresolved":
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
# assumed_claims_are_operator_declared  (W1 — the β honesty predicate)
# ---------------------------------------------------------------------------


def assumed_claims_are_operator_declared(
    path: PathLike,
    *,
    repo_root: Optional[Path] = None,
) -> PredicateResult:
    """Pass iff every ``assumed`` claim maps to an operator declaration (W1).

    The β honesty guarantee (CLAUDE.md §13.3; ticket 9).  For the section at
    *path*, every ``validation_status.claim_statuses`` entry whose ``status`` is
    ``"assumed"`` must map **by ``claim_id``** to a ``manually_placed``
    declaration in Tier 3 ``working_assumptions.json`` whose declared value
    equals the claim's ``claim_summary``.

    Because the declaration reader
    (:func:`runner.working_assumptions.load_working_assumptions`) parses **only**
    the ``manually_placed`` operator file and rejects any other provenance, a
    ``run_produced`` artifact can never appear as a backing declaration — so
    this predicate is exactly the rule that "a ``run_produced`` artifact can
    never back an ``Assumed``": any ``assumed`` claim without an operator
    declaration fails the gate.  A section with no ``assumed`` claims passes
    vacuously (the predicate is inert unless a green was bought by declaration).

    Failure categories:
        MISSING_MANDATORY_INPUT — section path does not exist
        MALFORMED_ARTIFACT — section or working_assumptions.json malformed
        POLICY_VIOLATION — an ``assumed`` claim is not operator-declared, or its
            ``claim_summary`` does not equal the declared value
    """
    resolved = resolve_repo_path(path, repo_root)
    data, err = _read_json_object(resolved)
    if err is not None:
        return err

    # Load the operator declarations, failing closed on a malformed file (a
    # silent swallow would hide a declaration the operator believes is active).
    root = repo_root if repo_root is not None else find_repo_root()
    try:
        declarations = load_working_assumptions(root)
    except WorkingAssumptionsError as exc:
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=f"working_assumptions.json is malformed: {exc}",
            details={"path": str(resolved), "working_assumptions_error": str(exc)},
        )

    validation_status = data.get("validation_status")
    if not isinstance(validation_status, dict):
        # No validation_status → no claims to check (the field-presence check
        # is a separate predicate); nothing here can be an undeclared assumed.
        return PredicateResult(passed=True)

    claim_statuses = validation_status.get("claim_statuses", [])
    if not isinstance(claim_statuses, list):
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=(
                f"validation_status.claim_statuses in {resolved} must be an "
                f"array, got {type(claim_statuses).__name__}"
            ),
            details={"path": str(resolved)},
        )

    violations: list[dict] = []
    for index, claim in enumerate(claim_statuses):
        if not isinstance(claim, dict):
            return PredicateResult(
                passed=False,
                failure_category=MALFORMED_ARTIFACT,
                reason=(
                    f"claim_statuses[{index}] in {resolved} must be an object, "
                    f"got {type(claim).__name__}"
                ),
                details={"path": str(resolved)},
            )
        if str(claim.get("status", "")).lower() != "assumed":
            continue

        claim_id = claim.get("claim_id")
        if not isinstance(claim_id, str) or not claim_id:
            violations.append(
                {"index": index, "issue": "assumed claim has no claim_id"}
            )
            continue

        decl = declarations.declaration(claim_id)
        if decl is None:
            violations.append(
                {
                    "claim_id": claim_id,
                    "issue": (
                        "no manually_placed operator declaration "
                        "(a run_produced value can never back an assumed claim)"
                    ),
                }
            )
            continue

        expected = declared_claim_summary(decl.value)
        actual = claim.get("claim_summary")
        if actual != expected:
            violations.append(
                {
                    "claim_id": claim_id,
                    "issue": "claim_summary does not equal the declared value",
                    "declared_value": expected,
                    "claim_summary": actual,
                }
            )

    if violations:
        first = violations[0]
        return PredicateResult(
            passed=False,
            failure_category=POLICY_VIOLATION,
            reason=(
                f"{len(violations)} assumed claim(s) in {resolved} are not "
                f"backed by an operator declaration (W1). First: {first}"
            ),
            details={"path": str(resolved), "violations": violations},
        )
    return PredicateResult(passed=True)


# ---------------------------------------------------------------------------
# declared_facts_are_not_inferred
# ---------------------------------------------------------------------------

#: Tier 3 artifact that, cited as a claim's source, means the claim rests on an
#: operator declaration.  Matched on the path tail so a repo-relative ref, an
#: absolute path and a POSIX/Windows separator all resolve alike.
_WORKING_ASSUMPTIONS_BASENAME = "working_assumptions.json"


def _cites_working_assumptions(claim: dict) -> bool:
    """True iff this claim names ``working_assumptions.json`` as a source.

    ``source_ref`` is either a string (free-form, often several refs joined by
    ``;``) or an object carrying ``source_path``.  Both shapes appear in real
    drafts, so both are inspected; anything else is not a citation.
    """
    ref = claim.get("source_ref")
    if isinstance(ref, str):
        return _WORKING_ASSUMPTIONS_BASENAME in ref
    if isinstance(ref, dict):
        return _WORKING_ASSUMPTIONS_BASENAME in str(ref.get("source_path", ""))
    return False


def declared_facts_are_not_inferred(
    path: PathLike,
    *,
    repo_root: Optional[Path] = None,
) -> PredicateResult:
    """Pass iff no claim sourced to ``working_assumptions.json`` is ``inferred``.

    Closes the escape hatch beside W1 (:func:`assumed_claims_are_operator_declared`).
    W1 audits claims already marked ``assumed``; it is silent about a claim that
    *should* be ``assumed`` but is not.  A drafter that labels an operator
    declaration ``inferred`` therefore passes both W1 (no ``assumed`` claims to
    audit — it passes **vacuously**) and ``no_unresolved_material_claims`` (not
    ``unresolved`` either), and the declared-assumption honesty apparatus goes
    inert on that section.

    Under §12.2 the two statuses are not interchangeable.  ``Inferred`` is
    *derived by logical reasoning from confirmed evidence*; ``Assumed`` is
    *adopted in the absence of direct evidence*.  An operator declaration is
    adopted precisely because there is no evidence — so citing
    ``working_assumptions.json`` while claiming ``inferred`` tells an evaluator
    the fact was reasoned from established evidence when the repository's own
    record says it was not.  That is a §12.2 misstatement of provenance and,
    because the quarantine exists to stop a declared value masquerading as
    something stronger, a §13.3 concern too.

    Deliberately narrow.  It judges only claims that name
    ``working_assumptions.json`` themselves — it never infers from a claim's
    wording that it *ought* to have cited a declaration, since that would be the
    kind of judgment a gate predicate must not make.  A claim that is genuinely
    inferred from confirmed Tier 1–4 evidence is untouched, and a section with no
    declaration-sourced ``inferred`` claims passes.

    Failure categories:
        MISSING_MANDATORY_INPUT — section path does not exist
        MALFORMED_ARTIFACT — section malformed
        POLICY_VIOLATION — a declaration-sourced claim is marked ``inferred``
    """
    resolved = resolve_repo_path(path, repo_root)
    data, err = _read_json_object(resolved)
    if err is not None:
        return err

    validation_status = data.get("validation_status")
    if not isinstance(validation_status, dict):
        return PredicateResult(passed=True)

    claim_statuses = validation_status.get("claim_statuses", [])
    if not isinstance(claim_statuses, list):
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=(
                f"validation_status.claim_statuses in {resolved} must be an "
                f"array, got {type(claim_statuses).__name__}"
            ),
            details={"path": str(resolved)},
        )

    violations: list[dict] = []
    for index, claim in enumerate(claim_statuses):
        if not isinstance(claim, dict):
            return PredicateResult(
                passed=False,
                failure_category=MALFORMED_ARTIFACT,
                reason=(
                    f"claim_statuses[{index}] in {resolved} must be an object, "
                    f"got {type(claim).__name__}"
                ),
                details={"path": str(resolved)},
            )
        if str(claim.get("status", "")).lower() != "inferred":
            continue
        if not _cites_working_assumptions(claim):
            continue
        violations.append(
            {
                "claim_id": claim.get("claim_id"),
                "index": index,
                "issue": (
                    "claim cites working_assumptions.json but is marked "
                    "'inferred'; an operator declaration is adopted without "
                    "evidence and is therefore 'assumed' (§12.2)"
                ),
                "claim_summary": claim.get("claim_summary"),
            }
        )

    if violations:
        first = violations[0]
        return PredicateResult(
            passed=False,
            failure_category=POLICY_VIOLATION,
            reason=(
                f"{len(violations)} claim(s) in {resolved} are sourced to "
                f"working_assumptions.json but marked 'inferred' rather than "
                f"'assumed' (§12.2). First: {first}"
            ),
            details={"path": str(resolved), "violations": violations},
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
# cross_section_consistency — internal helpers
# ---------------------------------------------------------------------------


def _extract_all_content(section_data: dict) -> str:
    """Concatenate all sub_section content strings from a section artifact."""
    parts: list[str] = []
    for sub in section_data.get("sub_sections", []):
        if isinstance(sub, dict):
            content = sub.get("content", "")
            if content:
                parts.append(str(content))
    return "\n".join(parts)


def _check_objective_coverage(
    sections_data: dict[str, dict],
    objectives: list[dict],
) -> list[dict]:
    """Verify all Tier 3 objectives are referenced in Excellence section
    and that cross-section objective references resolve to canonical IDs."""
    issues: list[dict] = []
    canonical_ids: set[str] = set()
    id_prefixes: set[str] = set()

    for obj in objectives:
        if isinstance(obj, dict) and obj.get("id"):
            oid = str(obj["id"])
            canonical_ids.add(oid)
            match = re.match(r'^([A-Za-z]+-)', oid)
            if match:
                id_prefixes.add(match.group(1))

    if not canonical_ids:
        return issues

    # Excellence must enumerate all objectives
    if "excellence" in sections_data:
        content = _extract_all_content(sections_data["excellence"])
        missing = {oid for oid in canonical_ids if oid not in content}
        if missing:
            issues.append({
                "check": "objective_coverage",
                "section": "excellence",
                "details": (
                    f"Excellence section missing {len(missing)} of "
                    f"{len(canonical_ids)} Tier 3 objectives: {sorted(missing)}"
                ),
            })

    # Cross-section: objective IDs mentioned in any section must exist in Tier 3
    for prefix in id_prefixes:
        pattern = re.escape(prefix) + r'\d+'
        for section_name, section_data in sections_data.items():
            content = _extract_all_content(section_data)
            mentioned = set(re.findall(pattern, content))
            unknown = mentioned - canonical_ids
            if unknown:
                issues.append({
                    "check": "objective_identity",
                    "section": section_name,
                    "details": (
                        f"{section_name.capitalize()} section references "
                        f"objective IDs not in Tier 3: {sorted(unknown)}"
                    ),
                })

    return issues


def _check_partner_naming(
    sections_data: dict[str, dict],
    partners: list[dict],
) -> list[dict]:
    """Verify partner legal names are not truncated (missing legal suffix)."""
    issues: list[dict] = []

    for partner in partners:
        if not isinstance(partner, dict):
            continue
        legal_name = partner.get("legal_name", "")
        if not legal_name:
            continue

        words = legal_name.split()
        if len(words) < 2:
            continue
        suffix = words[-1]
        if suffix not in _LEGAL_SUFFIXES:
            continue

        prefix = " ".join(words[:-1])
        if not prefix or len(prefix) < 3:
            continue

        for section_name, section_data in sections_data.items():
            content = _extract_all_content(section_data)
            # Check: prefix appears without the full legal name
            if prefix in content and legal_name not in content:
                issues.append({
                    "check": "partner_naming",
                    "section": section_name,
                    "details": (
                        f"'{prefix}' appears in {section_name} section "
                        f"without legal suffix '{suffix}'. "
                        f"Canonical legal name: '{legal_name}'"
                    ),
                })

    return issues


def _check_metric_completeness(
    sections_data: dict[str, dict],
    objectives: list[dict],
) -> list[dict]:
    """Verify all quantified percentage targets from Tier 3 objectives
    appear in sections that reference those objectives."""
    issues: list[dict] = []
    if "impact" not in sections_data:
        return issues

    impact_content = _extract_all_content(sections_data["impact"])

    for obj in objectives:
        if not isinstance(obj, dict):
            continue
        target = obj.get("measurable_target", "")
        obj_id = obj.get("id", "<unknown>")
        if not target:
            continue

        # Only check objectives whose ID appears in impact section
        if obj_id not in impact_content:
            continue

        # Extract percentage targets (e.g., ≥40%, ≥30%, ≤5%)
        percentages = re.findall(r'[≥≤]\d+%', target)
        for pct in percentages:
            bare_pct = pct[1:]  # Remove ≥/≤ prefix
            if pct not in impact_content and bare_pct not in impact_content:
                issues.append({
                    "check": "metric_completeness",
                    "objective": obj_id,
                    "details": (
                        f"Metric '{pct}' from {obj_id} measurable_target "
                        f"not found in Impact section"
                    ),
                })

    return issues


def _check_terminology_consistency(
    sections_data: dict[str, dict],
    objectives: list[dict],
) -> list[dict]:
    """Verify canonical component/system names from Tier 3 objectives
    are used consistently across sections (no semantic drift)."""
    issues: list[dict] = []

    # Extract canonical component names (titles containing component keywords)
    canonical_components: dict[str, str] = {}
    for obj in objectives:
        if not isinstance(obj, dict):
            continue
        title = obj.get("title", "")
        obj_id = obj.get("id", "")
        if not title or not obj_id:
            continue
        if any(kw in title.lower() for kw in _COMPONENT_KEYWORDS):
            canonical_components[obj_id] = title

    if not canonical_components:
        return issues

    section_names = list(sections_data.keys())
    for obj_id, canonical_name in canonical_components.items():
        # Find the stem (canonical name minus the trailing component keyword)
        cn_lower = canonical_name.lower()
        stem = canonical_name
        for kw in sorted(_COMPONENT_KEYWORDS, key=len, reverse=True):
            if cn_lower.endswith(kw):
                stem = canonical_name[:-(len(kw))].rstrip()
                break

        # Require multi-word stems (>=2 words) to avoid false positives
        # from generic single words like "Memory", "Planning", etc.
        stem_words = stem.split()
        if len(stem_words) < 2 or len(stem) < 10:
            continue

        # Check: if the stem appears in a section (case-insensitive)
        # but the full canonical name does NOT, flag terminology drift
        for sname in section_names:
            content = _extract_all_content(sections_data[sname])
            if stem.lower() in content.lower() and canonical_name not in content:
                issues.append({
                    "check": "terminology_consistency",
                    "section": sname,
                    "objective": obj_id,
                    "details": (
                        f"Stem '{stem}' appears in {sname} section but "
                        f"canonical name '{canonical_name}' is absent; "
                        f"possible terminology drift"
                    ),
                })

    return issues


def _check_deliverable_kpi_alignment(
    sections_data: dict[str, dict],
    kpis: list[dict],
    deliverables: dict[str, dict],
) -> list[dict]:
    """Verify KPIs are not incorrectly described as deliverables in sections.

    A KPI that references a deliverable via traceable_to_deliverable should
    not be described AS that deliverable in section content.
    """
    issues: list[dict] = []
    if not kpis or not deliverables:
        return issues

    if "impact" not in sections_data:
        return issues

    impact_content = _extract_all_content(sections_data["impact"])

    for kpi in kpis:
        if not isinstance(kpi, dict):
            continue
        kpi_id = kpi.get("kpi_id", "")
        linked_deliv = kpi.get("traceable_to_deliverable", "")
        if not kpi_id or not linked_deliv:
            continue
        if linked_deliv not in deliverables:
            continue

        deliv_info = deliverables[linked_deliv]
        deliv_title = deliv_info.get("title", "")

        # Check if the KPI's description is incorrectly attributed to the
        # deliverable ID. The KPI target should not be described as the
        # deliverable's title or purpose.
        kpi_desc = kpi.get("description", "")
        kpi_target = kpi.get("target", "")

        # If the impact section describes the deliverable as doing what the
        # KPI measures (and the deliverable has a DIFFERENT canonical title),
        # that's a conflation.
        if not deliv_title:
            continue

        # Check: if deliverable ID appears near KPI language that contradicts
        # the deliverable's canonical title
        # This is detected when the KPI's description appears attributed to
        # the deliverable rather than as a KPI tracked by it.
        # Simplified check: if deliverable ID appears but its canonical title
        # from wp_structure does NOT appear anywhere in the section,
        # while KPI description IS attributed to that deliverable ID
        if linked_deliv in impact_content:
            if deliv_title.lower() not in impact_content.lower():
                issues.append({
                    "check": "deliverable_kpi_alignment",
                    "kpi": kpi_id,
                    "deliverable": linked_deliv,
                    "details": (
                        f"Deliverable {linked_deliv} referenced in Impact "
                        f"but its canonical title '{deliv_title}' is absent; "
                        f"may be described using KPI-{kpi_id} language instead"
                    ),
                })

    return issues


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
    """Pass iff objectives, WP IDs, partner names, deliverable IDs, metrics,
    and terminology are cross-consistent across all three sections.

    Performs two layers of validation:

    1. **Consistency log check**: Reads the assembled Part B draft at
       *assembled_path* and fails if any ``consistency_log`` entry has
       status ``"inconsistency_flagged"``.

    2. **Artifact-driven cross-checks**: Reads the three section files in
       *sections_dir* and the canonical Tier 3 artifacts in *tier3_path*
       to perform deterministic verification of:
       - Objective coverage completeness (all Tier 3 objectives in Excellence)
       - Objective identity consistency (no unknown IDs across sections)
       - Partner naming consistency (no truncated legal names)
       - Metric completeness (quantified targets preserved in Impact)
       - Terminology consistency (canonical component names not drifted)
       - Deliverable/KPI alignment (KPIs not masquerading as deliverables)

    Failure categories:
        MISSING_MANDATORY_INPUT — path does not exist
        MALFORMED_ARTIFACT — invalid JSON or wrong section count
        CROSS_ARTIFACT_INCONSISTENCY — inconsistencies detected
    """
    resolved_assembled = resolve_repo_path(assembled_path, repo_root)

    assembled_data, err = _read_json_object(resolved_assembled)
    if err is not None:
        return err

    # --- Layer 1: Check consistency_log for flagged inconsistencies ---
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

    # --- Layer 2: Artifact-driven deterministic cross-checks ---
    resolved_sections = resolve_repo_path(sections_dir, repo_root)
    resolved_tier3 = resolve_repo_path(tier3_path, repo_root)

    # Load section artifacts
    section_files = {
        "excellence": resolved_sections / "excellence_section.json",
        "impact": resolved_sections / "impact_section.json",
        "implementation": resolved_sections / "implementation_section.json",
    }

    sections_data: dict[str, dict] = {}
    for name, path in section_files.items():
        if path.exists():
            data, _ = _read_json_object(path)
            if data is not None:
                sections_data[name] = data

    # If no section files found, skip artifact checks (per-section gates
    # handle missing files; this predicate operates post-assembly)
    if not sections_data:
        return PredicateResult(passed=True)

    # Load Tier 3 objectives
    objectives: list[dict] = []
    objectives_path = resolved_tier3 / "architecture_inputs" / "objectives.json"
    if objectives_path.exists():
        obj_data, _ = _read_json_object(objectives_path)
        if obj_data is not None:
            raw = obj_data.get("objectives", [])
            if isinstance(raw, list):
                objectives = raw

    # Load Tier 3 partners
    partners: list[dict] = []
    partners_path = resolved_tier3 / "consortium" / "partners.json"
    if partners_path.exists():
        partner_data, _ = _read_json_object(partners_path)
        if partner_data is not None:
            raw = partner_data.get("partners", [])
            if isinstance(raw, list):
                partners = raw

    # Load Tier 4 impact architecture KPIs (if available)
    kpis: list[dict] = []
    deliverables: dict[str, dict] = {}
    if repo_root is not None:
        # Load KPIs from impact_architecture.json
        impact_arch_path = (
            repo_root
            / "docs"
            / "tier4_orchestration_state"
            / "phase_outputs"
            / "phase5_impact_architecture"
            / "impact_architecture.json"
        )
        if impact_arch_path.exists():
            arch_data, _ = _read_json_object(impact_arch_path)
            if arch_data is not None:
                raw_kpis = arch_data.get("kpis", [])
                if isinstance(raw_kpis, list):
                    kpis = raw_kpis

        # Load deliverables from wp_structure.json
        wp_path = (
            repo_root
            / "docs"
            / "tier4_orchestration_state"
            / "phase_outputs"
            / "phase3_wp_design"
            / "wp_structure.json"
        )
        if wp_path.exists():
            wp_data, _ = _read_json_object(wp_path)
            if wp_data is not None:
                for wp in wp_data.get("work_packages", []):
                    if isinstance(wp, dict):
                        for deliv in wp.get("deliverables", []):
                            if isinstance(deliv, dict):
                                did = deliv.get("deliverable_id", "")
                                if did:
                                    deliverables[did] = deliv

    # Run deterministic cross-checks
    all_issues: list[dict] = []

    if objectives:
        all_issues.extend(_check_objective_coverage(sections_data, objectives))
        all_issues.extend(
            _check_metric_completeness(sections_data, objectives)
        )
        all_issues.extend(
            _check_terminology_consistency(sections_data, objectives)
        )

    if partners:
        all_issues.extend(_check_partner_naming(sections_data, partners))

    if kpis and deliverables:
        all_issues.extend(
            _check_deliverable_kpi_alignment(sections_data, kpis, deliverables)
        )

    if all_issues:
        return PredicateResult(
            passed=False,
            failure_category=CROSS_ARTIFACT_INCONSISTENCY,
            reason=(
                f"Artifact-driven cross-section checks found "
                f"{len(all_issues)} inconsistency(ies)"
            ),
            details={
                "assembled_path": str(resolved_assembled),
                "issue_count": len(all_issues),
                "issues": all_issues,
            },
        )

    return PredicateResult(passed=True)
