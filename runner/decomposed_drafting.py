"""
Decomposed section drafting — bounded per-sub-section Claude calls (D2/D3/D5).

The length shortfall in Phase-8 drafting was diagnosed as a **decomposition**
problem: one monolithic Claude call per section hits a response ceiling
(~20 KB) that caps the whole section at ~1/10th of the instrument's page
budget.  The fix is to draft **one bounded call per sub-section** at the
instrument profile's granularity, then compose the drafts with the
deterministic :mod:`runner.section_assembler` (array-append, byte-equal).

This module is the **drafting half**.  It:

  * resolves the section's drafting sub-sections from the instrument profile
    (so granularity is the profile's sub-section set — no RIA/MSCA literal),
  * drafts each sub-section with a **bounded** call, passing the prior
    sub-sections' drafts as **sequential context** for coherence (D5),
  * writes one ``<sub_section_id>.draft.json`` per sub-section plus a
    ``section_spine.json`` into ``section_drafts/<slug>/`` — exactly the
    inputs the assembler consumes.

The per-sub-section call is abstracted behind a *drafter* callable so the
control flow (loop, sequential context, spine derivation, atomic writes) is
fully unit-testable with a fake drafter, while the production drafter wraps
the Claude runtime transport.  Unlike a deterministic component this module
**does** invoke Claude (indirectly, via the drafter) — it is drafting, not
composition — so it is not a §17.5.3 component; the composition it feeds
(the assembler) is.

Live-run wiring note:
    This driver is the tested, transport-injectable realisation of
    per-sub-section drafting.  Its **governed** wiring — the ``n08a`` drafting
    skill producing the ``section_drafts/`` inputs, the ``excellence-section-
    drafting`` spec rewritten from monolithic to decomposed, and the post-skill
    ``excellence_section_assembler`` binding that composes them — lands together
    in the governed E2E run (ticket 13), which is gated on ``gate_09`` (ticket 8)
    and Tier 3 project data (ticket 14).  Until then the production skill spec is
    still monolithic and n08a binds no assembler; this driver is exercised only
    via its tests and the byte-equal composition proof, never writing a governed
    Tier 5 artifact before the budget gate (§8.4 / §13.4).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Callable, Optional

from runner.atomic_write import atomic_write_json
from runner.claim_status import worst_status
from runner.instrument_profile import resolve_instrument_profile
from runner.section_assembler import (
    SECTION_DRAFTS_ROOT_REL,
    VALID_SLUGS,
    DRAFT_SUFFIX,
    SPINE_FILENAME,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Slug → the criterion label whose sub-sections the slug drafts.  Kept as an
#: explicit map (not derived from the slug) so the human-facing criterion
#: string is authoritative; the actual sub-section set is still read from the
#: instrument profile, so no page count or sub-section id is hardcoded.
_SLUG_CRITERION: dict[str, str] = {
    "excellence": "Excellence",
    "impact": "Impact",
    "implementation": "Implementation",
}

#: Production drafter model / token budget.  The token budget is deliberately
#: generous (soft caps lifted, D5): each call drafts a single sub-section, so
#: the monolithic ~20 KB whole-section ceiling no longer binds.
_DRAFTER_MODEL: str = "claude-sonnet-4-6"
_DRAFTER_MAX_TOKENS: int = 8000


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

#: A *drafter* drafts one sub-section.  Given the sub-section spec (from the
#: profile), its criterion, and the drafts already produced (sequential
#: context), it returns a dict with at least ``content`` (the prose) and,
#: optionally, ``claim_statuses`` and ``source_refs`` (carried verbatim by the
#: assembler).  The production drafter wraps the Claude transport; tests inject
#: a deterministic fake.
SubSectionDrafter = Callable[[dict[str, Any], str, list[dict[str, Any]]], dict[str, Any]]


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------


class DecomposedDraftingError(Exception):
    """Raised when the decomposed drafts cannot be produced."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _section_id(sub: dict[str, Any]) -> str:
    return str(sub.get("section_id", ""))


def _resolve_drafting_sub_sections(
    repo_root: Path, slug: str, criterion: str
) -> list[dict[str, Any]]:
    """Resolve the profile's drafting sub-sections for *criterion*, ordered.

    Reads the instrument profile (fail-closed) and returns the drafting
    sub-sections (``section_type`` in the proposal/implementation set) whose
    ``criterion`` matches, ordered by ``section_id``.  Fails closed when the
    profile yields no drafting sub-sections for the criterion.
    """
    profile = resolve_instrument_profile(repo_root)
    subs = [
        s
        for s in profile.drafting_sub_sections
        if isinstance(s, dict) and s.get("criterion") == criterion and _section_id(s)
    ]
    if not subs:
        raise DecomposedDraftingError(
            f"instrument profile {profile.instrument_type!r} has no drafting "
            f"sub-sections for criterion {criterion!r} (slug {slug!r})"
        )
    return sorted(subs, key=_section_id)


def _build_draft(
    sub: dict[str, Any],
    criterion: str,
    prior_drafts: list[dict[str, Any]],
    drafter: SubSectionDrafter,
) -> dict[str, Any]:
    """Draft one sub-section and shape it into a ``*.draft.json`` object."""
    sub_id = _section_id(sub)
    title = str(sub.get("section_name", "")) or sub_id

    produced = drafter(sub, criterion, prior_drafts)
    if not isinstance(produced, dict):
        raise DecomposedDraftingError(
            f"drafter for sub-section {sub_id!r} returned "
            f"{type(produced).__name__}, expected a dict"
        )
    content = produced.get("content")
    if not isinstance(content, str) or not content.strip():
        raise DecomposedDraftingError(
            f"drafter for sub-section {sub_id!r} produced no 'content' prose"
        )

    claim_statuses = produced.get("claim_statuses", [])
    if not isinstance(claim_statuses, list):
        raise DecomposedDraftingError(
            f"drafter for sub-section {sub_id!r} 'claim_statuses' must be a list"
        )
    source_refs = produced.get("source_refs", [])
    if not isinstance(source_refs, list):
        raise DecomposedDraftingError(
            f"drafter for sub-section {sub_id!r} 'source_refs' must be a list"
        )

    return {
        "sub_section_id": sub_id,
        "title": title,
        "content": content,
        "claim_statuses": claim_statuses,
        "source_refs": source_refs,
    }


def _derive_overall_status(drafts: list[dict[str, Any]]) -> str:
    """Derive the section ``overall_status`` as the worst claim status.

    The section is only as resolved as its least-resolved claim: any
    ``unresolved`` claim makes the section ``unresolved`` (the honest block),
    any ``assumed`` makes it ``assumed``, and so on.  No claims ⇒ ``confirmed``.
    Delegates to :func:`runner.claim_status.worst_status` so the drafter and the
    assumption-applier (ticket 9) derive this identically (§12.2).
    """
    return worst_status(
        claim.get("status", "")
        for draft in drafts
        for claim in draft.get("claim_statuses", [])
        if isinstance(claim, dict)
    )


# ---------------------------------------------------------------------------
# Production drafter (wraps the Claude runtime transport)
# ---------------------------------------------------------------------------


def _default_claude_drafter() -> SubSectionDrafter:
    """Build the production per-sub-section drafter (wraps the transport).

    Each call drafts a single sub-section with a bounded prompt that carries
    the prior sub-sections' drafts as sequential context.  This is the live
    path; the driver's control flow is validated with an injected fake drafter
    in the tests, so this wrapper stays thin.
    """
    from runner.claude_transport import invoke_claude_text

    def _drafter(
        sub: dict[str, Any],
        criterion: str,
        prior_drafts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        sub_id = _section_id(sub)
        field_reqs = sub.get("field_requirements", [])
        context_blocks = "\n\n".join(
            f"[{d['sub_section_id']} {d['title']}]\n{d['content']}"
            for d in prior_drafts
        )
        system_prompt = (
            "You are drafting one sub-section of a Horizon Europe proposal "
            f"(criterion: {criterion}). Draft ONLY this sub-section, in full, "
            "grounded strictly in the provided project data. Return a single "
            "JSON object with keys: content (the full prose), claim_statuses "
            "(array), source_refs (array of {tier, source_path}). Every "
            "material claim must be Confirmed/Inferred/Assumed with a source "
            "ref, or flagged Unresolved. Do not fabricate."
        )
        user_prompt = (
            f"Sub-section {sub_id}: {sub.get('section_name', '')}\n"
            f"Field requirements:\n- " + "\n- ".join(map(str, field_reqs))
            + (f"\n\nPrior sub-sections (for coherence):\n{context_blocks}"
               if context_blocks else "")
        )
        raw = invoke_claude_text(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=_DRAFTER_MODEL,
            max_tokens=_DRAFTER_MAX_TOKENS,
        )
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise DecomposedDraftingError(
                f"drafter response for {sub_id!r} was not valid JSON: {exc}"
            ) from exc
        if not isinstance(parsed, dict):
            raise DecomposedDraftingError(
                f"drafter response for {sub_id!r} was not a JSON object"
            )
        return parsed

    return _drafter


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def draft_section_decomposed(
    run_id: str,
    repo_root: Path,
    slug: str,
    *,
    drafter: Optional[SubSectionDrafter] = None,
    extra_fields: Optional[dict[str, Any]] = None,
) -> list[Path]:
    """Draft a section as bounded per-sub-section calls → ``section_drafts/``.

    Resolves the section's drafting sub-sections from the instrument profile,
    drafts each with a bounded call (sequential context passed between calls),
    and writes one ``<sub_section_id>.draft.json`` per sub-section plus a
    ``section_spine.json`` into ``section_drafts/<slug>/`` — the exact inputs
    :func:`runner.section_assembler.assemble_section` consumes.

    Parameters
    ----------
    run_id:
        Current run UUID (stamped into the spine; the assembler enforces it).
    repo_root:
        Absolute path to the repository root.
    slug:
        One of ``"excellence"``, ``"impact"``, ``"implementation"``.
    drafter:
        Per-sub-section drafter callable.  Defaults to the production Claude
        drafter; tests inject a deterministic fake.
    extra_fields:
        Section-specific spine ``extra_fields`` (e.g. Impact's ``dec_coverage``
        / ``impact_pathway_refs``).  Excellence needs none; carried verbatim
        into the spine for the assembler's structural-compliance check.

    Returns
    -------
    list[Path]
        Absolute paths written (the spine and each draft), spine first.

    Raises
    ------
    DecomposedDraftingError
        On an unknown slug, an unresolvable profile, or a malformed draft.
    """
    if slug not in VALID_SLUGS:
        raise DecomposedDraftingError(
            f"Unknown section slug {slug!r}; expected one of {sorted(VALID_SLUGS)}"
        )
    criterion = _SLUG_CRITERION[slug]
    subs = _resolve_drafting_sub_sections(repo_root, slug, criterion)

    if drafter is None:
        drafter = _default_claude_drafter()

    drafts_dir = repo_root / SECTION_DRAFTS_ROOT_REL / slug

    # ── Draft each sub-section, passing prior drafts as sequential context ─
    drafts: list[dict[str, Any]] = []
    written: list[Path] = []
    for sub in subs:
        draft = _build_draft(sub, criterion, list(drafts), drafter)
        draft_path = drafts_dir / f"{draft['sub_section_id']}{DRAFT_SUFFIX}"
        atomic_write_json(draft, draft_path, prefix="decomposed_draft_")
        drafts.append(draft)
        written.append(draft_path)

    # ── Spine (order + verbatim status the assembler carries up) ──────────
    spine: dict[str, Any] = {
        "schema_id": f"orch.tier5.{slug}_section.v1",
        "run_id": run_id,
        "criterion": criterion,
        "sub_section_order": [d["sub_section_id"] for d in drafts],
        "overall_status": _derive_overall_status(drafts),
        "no_unsupported_claims_declaration": True,
    }
    if extra_fields:
        spine["extra_fields"] = extra_fields

    spine_path = drafts_dir / SPINE_FILENAME
    atomic_write_json(spine, spine_path, prefix="decomposed_draft_")

    logger.info(
        "decomposed drafting wrote %d sub-section draft(s) + spine for %s "
        "(overall_status=%s)",
        len(drafts),
        slug,
        spine["overall_status"],
    )
    return [spine_path] + written
