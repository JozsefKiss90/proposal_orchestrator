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

#: TAPM timeout for a grounded per-sub-section drafting call.  Each call reads
#: the declared grounding inputs from disk and drafts a full sub-section, so it
#: is given the generous TAPM budget rather than the 300 s cli-prompt default.
#: Live-run evidence (runs a79ed11e / 511325a3, 2026-07-29): leaf sub-section
#: calls measured 6-17 min wall clock, so the prior 1200 s ceiling sat inside
#: normal latency variance and produced intermittent ClaudeCLITimeoutError
#: node failures.  30 min gives headroom above the observed worst case while
#: still bounding a genuinely hung invocation.
_DRAFTER_TIMEOUT_SECONDS: int = 1800

#: Grounding inputs the production drafter reads (TAPM).  These are the same
#: Tier 3 / phase-output / canonical-pack sources the monolithic drafting skills
#: declared; the drafter is instructed to ground strictly in their retrieved
#: content and to cite each material claim to one of them (no fabrication).  A
#: superset is offered for every criterion; TAPM lets Claude Read only what the
#: sub-section needs.
_GROUNDING_INPUTS: tuple[str, ...] = (
    "docs/tier3_project_instantiation/project_brief/",
    "docs/tier3_project_instantiation/architecture_inputs/",
    "docs/tier3_project_instantiation/call_binding/selected_call.json",
    "docs/tier3_project_instantiation/call_binding/confirmation_checklist.json",
    "docs/tier3_project_instantiation/working_assumptions.json",
    "docs/tier2b_topic_and_call_sources/extracted/expected_outcomes.json",
    "docs/tier2b_topic_and_call_sources/extracted/expected_impacts.json",
    "docs/tier2b_topic_and_call_sources/extracted/scope_requirements.json",
    "docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/",
    "docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/",
    "docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/",
    "docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/"
    "canonical_reference_pack.json",
)


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
            f"drafter for sub-section {sub_id!r} produced no 'content' prose "
            f"(returned keys: {sorted(map(str, produced.keys()))}; "
            f"content type: {type(content).__name__})"
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

#: Root of the per-run raw-response capture (runtime execution memory, §9.2 —
#: rebuildable, never constitutional source truth).  Every live drafter call
#: persists its raw transport response here BEFORE parsing, so a malformed or
#: truncated response is diagnosable after the fact; run 511325a3/c622b352
#: failures were undiagnosable because the drafter path (unlike the skill
#: runtime) kept no diagnostic bundle.
_RESPONSE_CAPTURE_ROOT_REL: str = ".claude/logs/decomposed_drafting"


def _capture_raw_response(
    repo_root: Path,
    run_id: str,
    slug: str,
    filename: str,
    text: str,
) -> Optional[Path]:
    """Persist a raw transport response/diagnostic; never raise.

    A capture failure must not mask the drafting outcome — returns the path
    on success, ``None`` on any OS error.
    """
    try:
        cap_dir = repo_root / _RESPONSE_CAPTURE_ROOT_REL / run_id / slug
        cap_dir.mkdir(parents=True, exist_ok=True)
        path = cap_dir / filename
        path.write_text(text, encoding="utf-8")
        return path
    except OSError:  # pragma: no cover — depends on host FS state
        return None


def _snippet(text: str, limit: int = 240) -> str:
    """Whitespace-collapsed head+tail excerpt of *text* for error messages."""
    collapsed = " ".join(text.split())
    if len(collapsed) <= 2 * limit:
        return collapsed
    return f"{collapsed[:limit]} …[{len(collapsed) - 2 * limit} chars]… {collapsed[-limit:]}"


def _default_claude_drafter(
    repo_root: Path,
    run_id: str = "",
    slug: str = "",
) -> SubSectionDrafter:
    """Build the production per-sub-section drafter (wraps the transport).

    Each call drafts a single sub-section in **TAPM mode**: the drafter is told
    which grounding inputs to Read from disk (Tier 3 project data, the Phase 1-3
    outputs, and the canonical reference pack) and drafts strictly from their
    retrieved content, carrying the prior sub-sections' drafts as sequential
    context (D5).  This is the live capture path (ticket 13); the driver's
    control flow is validated with an injected fake drafter in the tests, so the
    live path is never exercised in CI.

    Claim discipline (feeds the assumption-applier + W1, tickets 9/13):
      * every material claim is Confirmed/Inferred with a Tier 1-4 ``source_ref``,
        or **Unresolved**;
      * a spine-identity fact that is not confirmed in Tier 3 (researcher, host,
        supervisor, …) is emitted **Unresolved** with ``claim_id`` set to its
        ``confirmation_checklist.json`` token (e.g. ``HOST``), so a matching
        operator declaration in ``working_assumptions.json`` can flip it to
        Assumed pre-assembly and W1 can verify the mapping.  The drafter never
        self-declares an Assumed value.
    """
    from runner.claude_transport import invoke_claude_text

    grounding_list = "\n".join(f"- {p}" for p in _GROUNDING_INPUTS)

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
            "You are drafting ONE sub-section of a Horizon Europe MSCA "
            f"Postdoctoral Fellowship proposal (evaluation criterion: "
            f"{criterion}). Read the declared grounding inputs from disk with "
            "the Read/Glob tools and draft strictly from their retrieved "
            "content — do NOT fabricate partners, capabilities, objectives, "
            "figures, or identities not present in those files. When you name "
            "a partner, objective, work package, deliverable, or milestone, "
            "reproduce its canonical legal name or title EXACTLY as it appears "
            "in the canonical reference pack (docs/tier4_orchestration_state/"
            "phase_outputs/phase8_drafting_review/canonical_reference_pack.json)"
            " — never paraphrase, shorten, or append parenthetical annotations "
            "or provenance tags to it. Do not state a deliverable's due month, "
            "or a work-package or milestone month, unless it matches the "
            "canonical reference pack exactly — omit the month rather than "
            "guess. Draft this "
            "sub-section IN FULL at evaluator depth (do not summarise; the "
            "monolithic length ceiling has been lifted). Return a SINGLE JSON "
            "object (begin with '{', end with '}', no markdown fence) with "
            "keys: content (the full evaluator-oriented prose, a string), "
            "claim_statuses (array of {claim_id, claim_summary, status, "
            "source_ref}), source_refs (array of {tier, source_path}, where "
            "tier is the INTEGER 1, 2, 3, or 4 — never a string such as "
            "'Tier 2B'). Each "
            "material claim's status is 'confirmed' or 'inferred' with a "
            "source_ref into Tier 1-4, or 'unresolved'. For a spine-identity "
            "fact not confirmed in Tier 3 (researcher, host, supervisor, "
            "fellowship type, duration), set status 'unresolved' and set "
            "claim_id to its confirmation_checklist.json token (HOST, FELLOW, "
            "SUPERVISOR, FELLOWSHIP_TYPE, DURATION). Never invent an identity "
            "and never emit status 'assumed' yourself."
        )
        user_prompt = (
            f"Grounding inputs to Read (relative to the repository root):\n"
            f"{grounding_list}\n\n"
            f"Draft sub-section {sub_id}: {sub.get('section_name', '')}\n"
            f"Field requirements:\n- " + "\n- ".join(map(str, field_reqs))
            + (f"\n\nPrior sub-sections already drafted (for coherence — do "
               f"not repeat them):\n{context_blocks}"
               if context_blocks else "")
            # Restated last: after a long Read/Glob session the output
            # contract is the instruction most at risk of being dropped, and
            # a non-JSON final reply fails the whole node (observed live:
            # run c622b352, sub-section '2.3').
            + "\n\nFINAL OUTPUT CONTRACT REMINDER: after your reading is "
              "done, your final reply must be ONLY the single JSON object "
              "described in the system instructions — beginning with '{' and "
              "ending with '}', with no preamble, commentary, or markdown "
              "fence around it."
        )
        try:
            raw = invoke_claude_text(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=_DRAFTER_MODEL,
                max_tokens=_DRAFTER_MAX_TOKENS,
                timeout_seconds=_DRAFTER_TIMEOUT_SECONDS,
                tools=["Read", "Glob"],
            )
        except Exception as exc:
            # Persist whatever the transport buffered (a timeout / non-zero
            # exit still often carries partial stdout+stderr) so the failure
            # is diagnosable, then re-raise unchanged (§17.5.4 — no retry).
            _stdout = getattr(exc, "stdout", None)
            _stderr = getattr(exc, "stderr", None)
            _capture_raw_response(
                repo_root, run_id, slug, f"{sub_id}.transport_failure.txt",
                f"exception: {type(exc).__name__}: {exc}\n"
                f"--- stdout ---\n{_stdout or ''}\n"
                f"--- stderr ---\n{_stderr or ''}\n",
            )
            raise
        capture_path = _capture_raw_response(
            repo_root, run_id, slug, f"{sub_id}.response.txt", raw
        )
        parsed = _parse_drafter_response(raw, sub_id, capture_path=capture_path)
        return parsed

    return _drafter


def _parse_drafter_response(
    raw: str,
    sub_id: str,
    capture_path: Optional[Path] = None,
) -> dict[str, Any]:
    """Parse a live drafter response into a draft dict (fail-closed).

    Delegates JSON extraction to the shared, hardened
    :func:`runner.skill_runtime._extract_json_response`, so the decomposed
    drafting path and the skill-runtime path treat malformed responses
    identically:

      * markdown fences and leading/trailing explanatory prose are tolerated;
      * a **front-truncated** response (text that begins mid-object because the
        transport returned only the tail of an over-long generation) is
        **rejected**, not salvaged into a misleading leading fragment;
      * structurally invalid JSON fails closed (§17.5.4 — no silent repair).

    A SkillResult-shaped success envelope
    (``{"status": "success", "payload": {...}}``) is unwrapped to its payload,
    mirroring the skill runtime's Phase-D.6 normalisation — the model sometimes
    wraps the draft object instead of returning it directly.  Raises
    :class:`DecomposedDraftingError` on any unparseable response.
    """
    # Local import: avoids any module-load import cycle and keeps a single
    # source of truth for JSON extraction across the runtime.
    from runner.skill_runtime import _extract_json_response

    parsed = _extract_json_response(raw)
    if parsed is None:
        raise DecomposedDraftingError(
            f"drafter response for {sub_id!r} contained no parseable JSON "
            "object (empty, truncated, or structurally malformed); "
            f"response length {len(raw)} chars"
            + (f", raw response captured at {capture_path}" if capture_path
               else "")
            + f"; excerpt: {_snippet(raw)!r}"
        )
    # Unwrap a SkillResult-shaped success envelope if the model wrapped the
    # draft payload instead of returning the draft object directly.  The draft
    # schema has no top-level ``status`` key, so this signature is unambiguous.
    if (
        parsed.get("status") == "success"
        and isinstance(parsed.get("payload"), dict)
        and parsed["payload"]
    ):
        parsed = parsed["payload"]
    return parsed


# ---------------------------------------------------------------------------
# Section-specific extra_fields sourcing (deterministic; ticket 9)
# ---------------------------------------------------------------------------

#: Canonical phase-output artifacts the per-section ``extra_fields`` derive from.
_IMPACT_ARCH_REL: str = (
    "docs/tier4_orchestration_state/phase_outputs/"
    "phase5_impact_architecture/impact_architecture.json"
)
_WP_STRUCTURE_REL: str = (
    "docs/tier4_orchestration_state/phase_outputs/"
    "phase3_wp_design/wp_structure.json"
)
_GANTT_ARTIFACT_REL: str = (
    "docs/tier4_orchestration_state/phase_outputs/"
    "phase4_gantt_milestones/gantt.json"
)
_IMPL_ARCH_REL: str = (
    "docs/tier4_orchestration_state/phase_outputs/"
    "phase6_implementation_architecture/implementation_architecture.json"
)


def _read_upstream_json(repo_root: Path, rel: str, what: str) -> dict[str, Any]:
    """Read a required upstream phase-output artifact, failing closed."""
    path = repo_root / rel
    if not path.is_file():
        raise DecomposedDraftingError(
            f"cannot source extra_fields: {what} missing at {rel}"
        )
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DecomposedDraftingError(
            f"cannot source extra_fields: {what} unreadable ({rel}): {exc}"
        ) from exc
    if not isinstance(data, dict):
        raise DecomposedDraftingError(
            f"cannot source extra_fields: {what} is not a JSON object ({rel})"
        )
    return data


def source_section_extra_fields(repo_root: Path, slug: str) -> dict[str, Any]:
    """Deterministically derive the section-specific ``extra_fields`` the
    assembler requires (``section_assembler.REQUIRED_EXTRA_FIELDS``) from the
    upstream phase outputs.  Ticket 9.

    * ``excellence`` needs none → ``{}``.
    * ``impact`` → ``impact_pathway_refs`` (every pathway id in the Phase-5
      impact architecture, so ``impact_pathways_covered`` passes) and
      ``dec_coverage`` (dissemination / exploitation / communication addressed,
      derived from the Phase-5 plans).
    * ``implementation`` → ``wp_table_refs`` (every WP id from Phase 3),
      ``gantt_ref`` (the Phase-4 gantt artifact), ``milestone_refs`` (every
      milestone id from Phase 4), ``risk_register_ref`` (the Phase-6
      implementation architecture holding the populated risk register).

    Pure lookup/derivation — no inference, no Claude.  Fails closed
    (``DecomposedDraftingError``) if a required upstream artifact is missing or
    malformed, so a live run fails BEFORE spending drafting quota.
    """
    if slug == "excellence":
        return {}

    if slug == "impact":
        arch = _read_upstream_json(
            repo_root, _IMPACT_ARCH_REL, "Phase-5 impact_architecture.json"
        )
        pathways = arch.get("impact_pathways") or arch.get("pathways") or []
        refs = [
            str(p.get("pathway_id") or p.get("id"))
            for p in pathways
            if isinstance(p, dict) and (p.get("pathway_id") or p.get("id"))
        ]
        dp = arch.get("dissemination_plan") or {}
        ep = arch.get("exploitation_plan") or {}
        arch_txt = json.dumps(arch, ensure_ascii=False).lower()
        return {
            "impact_pathway_refs": refs,
            "dec_coverage": {
                "dissemination_addressed": bool(
                    dp.get("activities") if isinstance(dp, dict) else dp
                ),
                "exploitation_addressed": bool(
                    ep.get("activities") if isinstance(ep, dict) else ep
                ),
                # Communication is part of the Phase-5 DEC check (its skill is
                # dissemination-exploitation-COMMUNICATION-check); look across
                # the whole impact architecture, not just dissemination_plan.
                "communication_addressed": (
                    "communication" in arch_txt
                    or bool(arch.get("communication_plan"))
                ),
            },
        }

    if slug == "implementation":
        wp = _read_upstream_json(
            repo_root, _WP_STRUCTURE_REL, "Phase-3 wp_structure.json"
        )
        gantt = _read_upstream_json(
            repo_root, _GANTT_ARTIFACT_REL, "Phase-4 gantt.json"
        )
        # Presence-check the Phase-6 architecture that holds the risk register.
        _read_upstream_json(
            repo_root, _IMPL_ARCH_REL,
            "Phase-6 implementation_architecture.json",
        )
        wp_refs = [
            str(w.get("wp_id") or w.get("id"))
            for w in wp.get("work_packages", [])
            if isinstance(w, dict) and (w.get("wp_id") or w.get("id"))
        ]
        ms_refs = [
            str(m.get("milestone_id") or m.get("id"))
            for m in gantt.get("milestones", [])
            if isinstance(m, dict) and (m.get("milestone_id") or m.get("id"))
        ]
        return {
            "wp_table_refs": wp_refs,
            "gantt_ref": _GANTT_ARTIFACT_REL,
            "milestone_refs": ms_refs,
            "risk_register_ref": _IMPL_ARCH_REL,
        }

    raise DecomposedDraftingError(
        f"cannot source extra_fields for unknown slug {slug!r}"
    )


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

    # Source the section-specific extra_fields the assembler requires unless the
    # caller supplied them (tests inject fixtures).  Done BEFORE drafting so a
    # missing upstream artifact fails closed without spending drafting quota
    # (ticket 9).
    if extra_fields is None:
        extra_fields = source_section_extra_fields(repo_root, slug)

    subs = _resolve_drafting_sub_sections(repo_root, slug, criterion)

    if drafter is None:
        drafter = _default_claude_drafter(repo_root, run_id=run_id, slug=slug)

    drafts_dir = repo_root / SECTION_DRAFTS_ROOT_REL / slug

    # ── Rerun hygiene: drop drafts/spine left by a prior run ──────────────
    # The assembler treats the spine's sub_section_order as the sole authority
    # on membership and fails closed on any draft file it does not declare.  A
    # profile change between runs (e.g. a sub-section leaving the drafting set)
    # would otherwise strand a stale <id>.draft.json on disk and block assembly
    # (§6.4 — reruns must update state deterministically from current inputs).
    if drafts_dir.is_dir():
        for stale in drafts_dir.glob(f"*{DRAFT_SUFFIX}"):
            stale.unlink()
        stale_spine = drafts_dir / SPINE_FILENAME
        if stale_spine.is_file():
            stale_spine.unlink()

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
