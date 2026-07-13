"""
Assumption-applier — the β honesty layer's pre-assembly claim flip (ticket 9).

The engine defaults to *honest block* (mode α): a claim it cannot ground in
Tier 1–4 is ``unresolved``, and a section with any unresolved claim blocks at
``gate_10a`` (``no_unresolved_material_claims``).  The operator may turn an
honest block into a **conscious green** (mode β) by declaring the unconfirmed
fact in Tier 3 ``working_assumptions.json`` (§9; ticket 15).  This component is
the mechanism that *applies* those declarations to the drafted claims.

**What it does — and only this.**  For each per-sub-section draft in
``section_drafts/<slug>/``, every claim whose ``status`` is ``unresolved`` and
whose ``claim_id`` matches an operator declaration ``key`` is flipped to
``assumed``: its ``claim_summary`` is set to the declared value (via the shared
:func:`runner.working_assumptions.declared_claim_summary`) and
``assumption_declared`` is set ``true``.  It then re-derives the section spine's
``overall_status`` from the post-flip claims so the section the assembler
carries verbatim stays internally consistent.  Nothing else is touched.

**It cannot invent (§13.3).**  It flips *only* enumerated ``unresolved →
assumed`` claims, and *only* where a declaration backs them by ``claim_id``.  It
never creates a claim, never flips ``confirmed``/``inferred``, and never
upgrades ``assumed`` further.  The W1 predicate
(``assumed_claims_are_operator_declared``, ticket 9) independently re-checks on
the assembled section that every ``assumed`` claim maps to a declaration — so a
flip this applier makes is exactly what W1 will accept, and any ``assumed`` claim
*not* produced from a declaration (e.g. a drafter fabrication) is caught there.

**α is a pure no-op.**  With no declarations (absent/empty
``working_assumptions.json``) the applier writes nothing: the drafts pass through
unchanged, their ``unresolved`` claims survive, and the honest block stands.

**Deterministic component (§17.5.3 / C2).**  Pure-Python, Claude-free, no
inference (a lookup + enumerated flip + worst-status re-derivation), closed by a
determinism guarantee: given the same drafts and declarations it produces
byte-identical output, and it is idempotent — a second run finds no
``unresolved`` claim left to flip and writes nothing.  Python owns every write
(atomic).  It is registered in
:data:`runner.deterministic_components.COMPONENT_REGISTRY`; its manifest **node**
binding (before the section assembler on n08a/b/c — the flip must precede
composition) lands with the governed E2E run (ticket 13), together with the
assembler binding, per the "don't bind over drafts no skill yet writes" rule.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from runner.atomic_write import atomic_write_json
from runner.claim_status import worst_status
from runner.section_assembler import (
    DRAFT_SUFFIX,
    SECTION_DRAFTS_ROOT_REL,
    SPINE_FILENAME,
    VALID_SLUGS,
)
from runner.working_assumptions import (
    WorkingAssumptions,
    declared_claim_summary,
    load_working_assumptions,
)

logger = logging.getLogger(__name__)

#: The two §12.2 claim statuses this component moves between.  Claim-level
#: statuses are lowercase (the section schema enum); ``declared_claim_summary``
#: owns the value rendering, ``worst_status`` owns the section roll-up.
_UNRESOLVED: str = "unresolved"
_ASSUMED: str = "assumed"


class AssumptionApplierError(Exception):
    """Raised when the declared assumptions cannot be applied to the drafts."""


def _read_json_object(path: Path, label: str) -> dict[str, Any]:
    """Read *path* as a UTF-8 JSON object, failing closed on any issue."""
    if not path.is_file():
        raise AssumptionApplierError(f"{label} not found: {path}")
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise AssumptionApplierError(f"Cannot read {label}: {exc}") from exc
    if not text.strip():
        raise AssumptionApplierError(f"{label} is empty: {path}")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AssumptionApplierError(f"{label} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise AssumptionApplierError(
            f"{label} top-level value must be an object, got {type(data).__name__}"
        )
    return data


def _flip_declared_claims(
    draft: dict[str, Any],
    wa: WorkingAssumptions,
    label: str,
) -> bool:
    """Flip this draft's declared ``unresolved → assumed`` claims in place.

    Returns ``True`` iff at least one claim was flipped.  Only claims that are
    ``unresolved`` *and* whose ``claim_id`` matches a declaration are touched.
    """
    claim_statuses = draft.get("claim_statuses", [])
    if not isinstance(claim_statuses, list):
        raise AssumptionApplierError(
            f"{label} 'claim_statuses' must be an array when present"
        )

    changed = False
    for claim in claim_statuses:
        if not isinstance(claim, dict):
            raise AssumptionApplierError(
                f"{label} 'claim_statuses' entry must be an object, got "
                f"{type(claim).__name__}"
            )
        if str(claim.get("status", "")).lower() != _UNRESOLVED:
            continue
        claim_id = claim.get("claim_id")
        if not isinstance(claim_id, str) or not claim_id:
            # An unresolved claim with no id cannot be declared against; leave
            # it unresolved (it will keep the section blocked, honestly).
            continue
        decl = wa.declaration(claim_id)
        if decl is None:
            continue  # undeclared → stays unresolved (honest block persists)
        claim["status"] = _ASSUMED
        claim["claim_summary"] = declared_claim_summary(decl.value)
        claim["assumption_declared"] = True
        changed = True
    return changed


def apply_assumptions(run_id: str, repo_root: Path, slug: str) -> list[Path]:
    """Apply operator declarations to the ``<slug>`` section drafts, pre-assembly.

    Reads Tier 3 ``working_assumptions.json`` and every
    ``section_drafts/<slug>/*.draft.json``; flips each declared ``unresolved →
    assumed`` claim (by ``claim_id``); re-derives the spine's ``overall_status``;
    and atomically rewrites only the files that actually changed.

    Parameters
    ----------
    run_id:
        Current DAG-runner run UUID (unused for content but part of the
        component signature; the spine's ``run_id`` is left untouched and the
        assembler enforces its freshness downstream).
    repo_root:
        Absolute path to the repository root.
    slug:
        One of ``"excellence"``, ``"impact"``, ``"implementation"``.

    Returns
    -------
    list[Path]
        The files rewritten (changed drafts, then the spine if its
        ``overall_status`` changed), in a stable order.  Empty when nothing was
        declared or nothing matched (mode α is a pure no-op).

    Raises
    ------
    AssumptionApplierError
        On an unknown slug, a missing drafts directory or spine (once there is
        something to apply), or a malformed draft/spine.
    """
    if slug not in VALID_SLUGS:
        raise AssumptionApplierError(
            f"Unknown section slug {slug!r}; expected one of {sorted(VALID_SLUGS)}"
        )

    wa = load_working_assumptions(repo_root)
    if wa.is_empty:
        # Mode α: no declarations → nothing to apply.  Do not read or touch the
        # drafts; they flow to the assembler unchanged and the honest block
        # stands.  (The assembler validates the drafts directory itself.)
        return []

    drafts_dir = repo_root / SECTION_DRAFTS_ROOT_REL / slug
    if not drafts_dir.is_dir():
        raise AssumptionApplierError(
            f"section drafts directory not found for {slug!r}: {drafts_dir}"
        )

    # ── Flip declared claims in each draft; collect every post-flip claim ──
    changed_drafts: list[Path] = []
    all_claims: list[Any] = []
    for path in sorted(drafts_dir.glob(f"*{DRAFT_SUFFIX}")):
        draft = _read_json_object(path, f"draft {path.name}")
        if _flip_declared_claims(draft, wa, f"draft {path.name}"):
            atomic_write_json(draft, path, prefix="assumption_applier_")
            changed_drafts.append(path)
        all_claims.extend(draft.get("claim_statuses", []))

    # ── Re-derive the spine's overall_status when a flip changed a claim ───
    #
    # Only a flip can change the section's worst-status, so the spine is touched
    # iff at least one draft was rewritten.  With no flips the drafter's spine
    # already reflects the (unchanged) claims and is left untouched — the applier
    # does not "correct" a spine it had no hand in (that is the drafter's job).
    written: list[Path] = list(changed_drafts)
    if changed_drafts:
        spine_path = drafts_dir / SPINE_FILENAME
        spine = _read_json_object(spine_path, "section spine")
        new_overall = worst_status(
            claim.get("status", "")
            for claim in all_claims
            if isinstance(claim, dict)
        )
        if spine.get("overall_status") != new_overall:
            spine["overall_status"] = new_overall
            atomic_write_json(spine, spine_path, prefix="assumption_applier_")
            written.append(spine_path)

    logger.info(
        "assumption-applier: %s — %d draft(s) flipped, %d file(s) written",
        slug,
        len(changed_drafts),
        len(written),
    )
    return written
