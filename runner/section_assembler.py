"""
Deterministic section assembler — composes per-sub-section drafts into a
Tier 5 section JSON by array-append (CLAUDE.md §17.5.3, roster component C2).

Decomposed drafting (D2/D3/D5) produces one bounded per-sub-section draft per
Claude call, written to Tier 4 ``phase8_drafting_review/section_drafts/<slug>/``.
This module is the **composition half** of the length fix: a pure-Python,
Claude-free component that reads those drafts plus a section *spine* and
array-appends them into the section artifact the Phase-8 gates consume.

The assembler makes **no decision about content or claim status**.  It only:

  * array-appends each draft's ``sub_section`` into ``sub_sections[]`` in the
    spine-declared order (carried verbatim, incl. optional ``page_estimate``),
  * concatenates each draft's ``claim_statuses`` into
    ``validation_status.claim_statuses`` **verbatim** (no re-judging),
  * carries ``overall_status`` and the ``no_unsupported_claims_declaration``
    from the spine **verbatim**,
  * **derives** exactly two things: each sub-section's ``word_count`` and the
    de-duplicated union of the drafts' ``source_refs``.

"No synthesis" is therefore true *by construction* — the assembler never
authors prose and never sets a claim's status — and is enforced by the
byte-equal replay check ``assembler(drafts) == section_json`` (D3 / the
milestone CI check, ``tests/runner/test_section_assembler.py``).  Because the
assembler is a lookup/append/count with no inference, it cannot become an
"unlogged decision-maker" (PHASE8 brief §6).

Binding (§16.5 / C3):
    The three per-criterion assemblers are registered in
    ``runner.deterministic_components.COMPONENT_REGISTRY`` and are invocable
    through the C2/C3 substrate.  The manifest **node** binding
    (``deterministic_components:`` on n08a/n08b/n08c) is wired together with the
    decomposed drafting that *produces* the ``section_drafts/<slug>/`` inputs
    (that drafting replaces the monolithic section writer), so a node's
    assembler and its draft-producing skills land in the same change rather than
    binding an assembler over a directory no skill yet populates.

Constitutional constraints (§17.5.3, §17.6):
    * Performs no domain reasoning and never invokes Claude.
    * Cannot evaluate gates (§17.6.2) and is never invoked by a skill (§17.6.4).
    * Python owns the write (atomic); closed by the byte-equal determinism
      guarantee.
    * Fails closed (raises :class:`SectionAssemblerError`) on any missing or
      malformed input — never a partial or fabricated section.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from runner.atomic_write import atomic_write_json

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Tier 4 root under which per-section draft directories live.  Retained for
#: audit (§9.5) and freshness-excluded (the section JSON is the sole gate /
#: freshness artifact) per the milestone W2 note.
SECTION_DRAFTS_ROOT_REL: str = (
    "docs/tier4_orchestration_state/phase_outputs"
    "/phase8_drafting_review/section_drafts"
)
#: Tier 5 directory the assembled section artifacts are written to.
PROPOSAL_SECTIONS_REL: str = "docs/tier5_deliverables/proposal_sections"

#: The section slugs this assembler serves — one per Phase-8 criterion node
#: (n08a Excellence, n08b Impact, n08c Implementation).  The slug drives the
#: canonical input dir and output path; the human-facing ``criterion`` string
#: is carried verbatim from the spine, not derived from the slug.
VALID_SLUGS: frozenset[str] = frozenset({"excellence", "impact", "implementation"})

#: Section-specific fields the artifact schema marks **required** for each slug
#: (``artifact_schema_specification.yaml`` → ``impact_section`` /
#: ``implementation_section``).  These reach the artifact only via the spine's
#: ``extra_fields`` passthrough, so the assembler asserts their presence to keep
#: the output structurally compliant (§16.4) — Excellence has none.  The gate
#: (10b/10c) still validates their *content*; this only guards presence.
REQUIRED_EXTRA_FIELDS: dict[str, frozenset[str]] = {
    "excellence": frozenset(),
    "impact": frozenset({"impact_pathway_refs", "dec_coverage"}),
    "implementation": frozenset(
        {"wp_table_refs", "gantt_ref", "milestone_refs", "risk_register_ref"}
    ),
}

#: Filename of the section spine inside a ``section_drafts/<slug>/`` directory.
SPINE_FILENAME: str = "section_spine.json"
#: Suffix identifying a per-sub-section draft file.
DRAFT_SUFFIX: str = ".draft.json"

#: Core top-level keys the assembler owns.  A spine ``extra_fields`` entry may
#: not shadow any of these (fail-closed) — the assembler's derived/verbatim
#: fields can never be overridden by passthrough.
_CORE_TOP_LEVEL_KEYS: frozenset[str] = frozenset({
    "schema_id",
    "run_id",
    "criterion",
    "sub_sections",
    "validation_status",
    "traceability_footer",
})


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------


class SectionAssemblerError(Exception):
    """Raised when the section artifact cannot be composed from its drafts."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _read_json_object(path: Path, label: str) -> dict[str, Any]:
    """Read *path* as a UTF-8 JSON object, failing closed on any issue."""
    if not path.is_file():
        raise SectionAssemblerError(f"{label} not found: {path}")
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise SectionAssemblerError(f"Cannot read {label}: {exc}") from exc
    if not text.strip():
        raise SectionAssemblerError(f"{label} is empty: {path}")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SectionAssemblerError(f"{label} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise SectionAssemblerError(
            f"{label} top-level value must be an object, got {type(data).__name__}"
        )
    return data


def _word_count(content: str) -> int:
    """Derive a word count deterministically (whitespace-split token count)."""
    return len(content.split())


def _build_sub_section(draft: dict[str, Any], label: str) -> dict[str, Any]:
    """Compose one output ``sub_sections[]`` entry from a draft, verbatim.

    Carries ``sub_section_id``, ``title``, ``content`` (and the additive-
    optional ``page_estimate`` when present) verbatim; **derives** only
    ``word_count`` from ``content``.  The draft is not otherwise interpreted.
    """
    for key in ("sub_section_id", "title", "content"):
        value = draft.get(key)
        if not isinstance(value, str) or not value:
            raise SectionAssemblerError(
                f"{label} missing required string field {key!r}"
            )
    entry: dict[str, Any] = {
        "sub_section_id": draft["sub_section_id"],
        "title": draft["title"],
        "content": draft["content"],
        "word_count": _word_count(draft["content"]),
    }
    # Additive-optional page_estimate (D4): carried verbatim, never derived.
    if "page_estimate" in draft:
        page_estimate = draft["page_estimate"]
        if not isinstance(page_estimate, int) or isinstance(page_estimate, bool):
            raise SectionAssemblerError(
                f"{label} 'page_estimate' must be an integer, got "
                f"{type(page_estimate).__name__}"
            )
        entry["page_estimate"] = page_estimate
    return entry


def _source_ref_key(ref: dict[str, Any]) -> tuple[int, str]:
    """Deterministic sort/dedup key for a traceability source ref."""
    tier = ref.get("tier")
    source_path = ref.get("source_path")
    if not isinstance(tier, int) or isinstance(tier, bool):
        raise SectionAssemblerError(
            f"source_ref 'tier' must be an integer, got {tier!r}"
        )
    if not isinstance(source_path, str) or not source_path:
        raise SectionAssemblerError(
            f"source_ref 'source_path' must be a non-empty string, got "
            f"{source_path!r}"
        )
    return (tier, source_path)


def _union_source_refs(
    drafts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Derive the de-duplicated, deterministically-ordered ``primary_sources``.

    The union across every draft's ``source_refs``, de-duplicated by
    ``(tier, source_path)`` and sorted by that key so the output bytes are
    stable regardless of draft iteration order.
    """
    seen: dict[tuple[int, str], dict[str, Any]] = {}
    for draft in drafts:
        refs = draft.get("source_refs", [])
        if not isinstance(refs, list):
            raise SectionAssemblerError(
                "draft 'source_refs' must be an array when present"
            )
        for ref in refs:
            if not isinstance(ref, dict):
                raise SectionAssemblerError(
                    f"draft 'source_refs' entry must be an object, got "
                    f"{type(ref).__name__}"
                )
            key = _source_ref_key(ref)
            if key not in seen:
                seen[key] = {"tier": key[0], "source_path": key[1]}
    return [seen[key] for key in sorted(seen)]


def _load_drafts_in_order(
    drafts_dir: Path,
    spine: dict[str, Any],
) -> list[dict[str, Any]]:
    """Load the per-sub-section drafts in the spine-declared order.

    The spine's ``sub_section_order`` is the sole authority on order and
    membership.  Fails closed when a declared sub-section has no draft, when a
    draft on disk is not declared, or when a sub-section is declared twice.
    """
    order = spine.get("sub_section_order")
    if not isinstance(order, list) or not order:
        raise SectionAssemblerError(
            "section spine missing non-empty 'sub_section_order' array"
        )
    if len(set(order)) != len(order):
        raise SectionAssemblerError(
            f"section spine 'sub_section_order' contains duplicates: {order}"
        )

    # Index draft files on disk by their self-declared sub_section_id.
    on_disk: dict[str, Path] = {}
    for path in sorted(drafts_dir.glob(f"*{DRAFT_SUFFIX}")):
        draft = _read_json_object(path, f"draft {path.name}")
        sub_id = draft.get("sub_section_id")
        if not isinstance(sub_id, str) or not sub_id:
            raise SectionAssemblerError(
                f"draft {path.name} missing 'sub_section_id'"
            )
        if sub_id in on_disk:
            raise SectionAssemblerError(
                f"two draft files declare sub_section_id {sub_id!r}: "
                f"{on_disk[sub_id].name} and {path.name}"
            )
        on_disk[sub_id] = path

    declared = set(order)
    undeclared = sorted(set(on_disk) - declared)
    if undeclared:
        raise SectionAssemblerError(
            f"draft(s) on disk not declared in spine 'sub_section_order': "
            f"{undeclared}"
        )

    drafts: list[dict[str, Any]] = []
    for sub_id in order:
        path = on_disk.get(sub_id)
        if path is None:
            raise SectionAssemblerError(
                f"spine declares sub-section {sub_id!r} but no "
                f"'{sub_id}{DRAFT_SUFFIX}'-style draft is present in "
                f"{drafts_dir}"
            )
        drafts.append(_read_json_object(path, f"draft {path.name}"))
    return drafts


def _carry_claim_statuses(drafts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Concatenate every draft's ``claim_statuses`` verbatim, in draft order."""
    carried: list[dict[str, Any]] = []
    for draft in drafts:
        statuses = draft.get("claim_statuses", [])
        if not isinstance(statuses, list):
            raise SectionAssemblerError(
                "draft 'claim_statuses' must be an array when present"
            )
        for status in statuses:
            if not isinstance(status, dict):
                raise SectionAssemblerError(
                    f"draft 'claim_statuses' entry must be an object, got "
                    f"{type(status).__name__}"
                )
            # Verbatim: the assembler copies the claim through unchanged.
            carried.append(status)
    return carried


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def assemble_section(run_id: str, repo_root: Path, slug: str) -> Path:
    """Assemble the ``<slug>`` section artifact from its per-sub-section drafts.

    Reads ``section_drafts/<slug>/section_spine.json`` and every
    ``section_drafts/<slug>/*.draft.json``; array-appends the sub-sections in
    the spine-declared order; carries claim/validation status up verbatim;
    derives ``word_count`` and the ``source_refs`` union; and atomically writes
    ``proposal_sections/<slug>_section.json``.

    Parameters
    ----------
    run_id:
        Current DAG-runner run UUID.  The spine's ``run_id`` must match — a
        mismatch means stale drafts and is a fail-closed error.
    repo_root:
        Absolute path to the repository root.
    slug:
        One of ``"excellence"``, ``"impact"``, ``"implementation"``.

    Returns
    -------
    Path
        Absolute path to the written ``<slug>_section.json``.

    Raises
    ------
    SectionAssemblerError
        On an unknown slug, any missing/malformed input, a run_id or schema_id
        mismatch, an extra-field collision, or an order/membership mismatch
        between the spine and the drafts on disk.
    """
    if slug not in VALID_SLUGS:
        raise SectionAssemblerError(
            f"Unknown section slug {slug!r}; expected one of "
            f"{sorted(VALID_SLUGS)}"
        )

    drafts_dir = repo_root / SECTION_DRAFTS_ROOT_REL / slug
    if not drafts_dir.is_dir():
        raise SectionAssemblerError(
            f"section drafts directory not found for {slug!r}: {drafts_dir}"
        )

    spine = _read_json_object(drafts_dir / SPINE_FILENAME, "section spine")

    # ── Section identity + stale-guard (verbatim from spine) ─────────────
    expected_schema_id = f"orch.tier5.{slug}_section.v1"
    schema_id = spine.get("schema_id")
    if schema_id != expected_schema_id:
        raise SectionAssemblerError(
            f"section spine schema_id {schema_id!r} does not match the "
            f"expected {expected_schema_id!r} for slug {slug!r}"
        )

    spine_run_id = spine.get("run_id")
    if spine_run_id != run_id:
        raise SectionAssemblerError(
            f"section spine run_id {spine_run_id!r} does not match the current "
            f"run_id {run_id!r} (stale drafts)"
        )

    criterion = spine.get("criterion")
    if not isinstance(criterion, str) or not criterion:
        raise SectionAssemblerError("section spine missing 'criterion' string")

    overall_status = spine.get("overall_status")
    if not isinstance(overall_status, str) or not overall_status:
        raise SectionAssemblerError(
            "section spine missing 'overall_status' string"
        )

    no_unsupported = spine.get("no_unsupported_claims_declaration")
    if not isinstance(no_unsupported, bool):
        raise SectionAssemblerError(
            "section spine missing boolean "
            "'no_unsupported_claims_declaration'"
        )

    # ── Load drafts in spine order, then compose (append / carry / derive) ─
    drafts = _load_drafts_in_order(drafts_dir, spine)

    sub_sections = [
        _build_sub_section(draft, f"draft for {draft.get('sub_section_id')!r}")
        for draft in drafts
    ]
    claim_statuses = _carry_claim_statuses(drafts)
    primary_sources = _union_source_refs(drafts)

    artifact: dict[str, Any] = {
        "schema_id": schema_id,
        "run_id": run_id,
        "criterion": criterion,
        "sub_sections": sub_sections,
        "validation_status": {
            "overall_status": overall_status,
            "claim_statuses": claim_statuses,
        },
        "traceability_footer": {
            "primary_sources": primary_sources,
            "no_unsupported_claims_declaration": no_unsupported,
        },
    }

    # ── Section-specific passthrough (Impact/Implementation extras) ───────
    #
    # dec_coverage, impact_pathway_refs, wp_table_refs, gantt_ref, etc. are
    # carried verbatim from the spine.  They may never shadow a core field —
    # the assembler's own derived/verbatim fields always win (fail-closed).
    extra_fields = spine.get("extra_fields")
    present_extras: set[str] = set()
    if extra_fields is not None:
        if not isinstance(extra_fields, dict):
            raise SectionAssemblerError(
                "section spine 'extra_fields' must be an object when present"
            )
        collisions = sorted(set(extra_fields) & _CORE_TOP_LEVEL_KEYS)
        if collisions:
            raise SectionAssemblerError(
                f"section spine 'extra_fields' may not shadow core field(s): "
                f"{collisions}"
            )
        for key in sorted(extra_fields):
            artifact[key] = extra_fields[key]
        present_extras = set(extra_fields)

    # ── Structural compliance: section-specific required fields (§16.4) ───
    #
    # Impact/Implementation schemas mark fields like dec_coverage / gantt_ref
    # as required; they reach the artifact only through extra_fields, so a
    # spine omitting them would silently yield a schema-non-compliant section.
    # Fail closed here rather than emit a malformed artifact (the drafting gate
    # still validates their content).
    missing_required = sorted(REQUIRED_EXTRA_FIELDS[slug] - present_extras)
    if missing_required:
        raise SectionAssemblerError(
            f"section {slug!r} is missing schema-required field(s) "
            f"{missing_required}; supply them via the spine 'extra_fields'"
        )

    # ── Atomic write ─────────────────────────────────────────────────────
    output_path = repo_root / PROPOSAL_SECTIONS_REL / f"{slug}_section.json"
    atomic_write_json(artifact, output_path, prefix="section_assembler_")
    logger.info(
        "Assembled %s section: %d sub-sections, %d claim(s), %d source(s)",
        slug,
        len(sub_sections),
        len(claim_statuses),
        len(primary_sources),
    )
    return output_path
