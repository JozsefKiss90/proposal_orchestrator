"""R04 — the fidelity register's declared half, drafted for operator review.

R01 gave the declared half a durable home: one declaration input per revision
under ``docs/tier3_project_instantiation/source_materials/msca_dn/declarations/``
(:mod:`tools.fidelity_declarations`). Both inputs are absent, so both declared
halves are empty, and every ESR disposition that leans on preservation leans on
the document-wide provenance declaration instead of a per-sub-section one. R04
drafts what those inputs could say.

What this module is
-------------------
A deterministic, Claude-free renderer. It reads committed artifacts only — the
two fidelity registers, the two import manifests, the ESR dispositions and the
active review notes — and writes, per revision, one draft record under
:data:`DRAFTS_DIR_REL`, plus one Markdown review checklist across both. Nothing
is measured here that the registers and manifests do not already record, so a
draft is reproducible from its documented inputs (CLAUDE.md §9.5) and ``--check``
is a byte-equal replay.

Where the drafts live, and why not in the register
--------------------------------------------------
A draft is a proposal for operator review, so it is written to Tier 4 and never
to the Tier 3 declaration input (ticket R04 step 9). The adoptable payload sits
inside the draft under :data:`PAYLOAD_KEY`, byte-for-byte what the operator's
input would hold, and ``--emit-input <revision>`` prints it to stdout so the
operator can redirect it into place themselves. This module never writes into
Tier 3.

The three claims this draft keeps apart
---------------------------------------
Ticket R04 step 3 requires three claims to stay separate, because they are
checkable in three different places:

``extraction_fidelity_against_the_sanitised_pdf``
    Is the sub-section present in the extraction of this revision's PDF, and
    did the extraction lose anything? Measured here, in the register's derived
    half and the import manifest. Confirmed.

``difference_between_the_sanitised_revisions``
    Does this sub-section differ from the predecessor revision's? Measured
    here, by the manifest's page-by-page comparison and the two derived halves.
    Confirmed.

``fidelity_against_the_submitted_original``
    Does this sub-section say what the submitted original said? Nothing in this
    repository measures it: the original is stored only in the private network.
    Unresolved, for every sub-section of both revisions, until PE-09.

The register's ``transformation`` field sits on the third claim, one step above
the per-sub-section judgment: the operator declared at PE-01 what sanitisation
did to the document as a whole, and parts of that declaration are Confirmed by
measurement (no figure and no citation marker survives) while the amount of
prose changed is not measured anywhere. So the field carries the weaker status
of the two, Assumed, and its basis names which parts are Confirmed. The
per-sub-section judgment on the same claim is the row's own
``fidelity_to_submitted_original``, and it stays Unresolved. A present passage
and a zero extraction loss are facts about the step from this PDF to its
extraction, and this module never lets them read as fidelity to the original
(ticket R04 step 4).

Statuses are CLAUDE.md §12.2's four and nothing else: Confirmed, Inferred,
Assumed, Unresolved. No enum is coined here, and the declaration format is
unchanged — every field beyond ``presence`` and ``transformation`` travels with
the row as an extra field the reader already carries through untouched.

What this module will not do
----------------------------
It does not record an operator decision, and it does not author a declaration
as the operator. Every row it drafts says so in its own ``declared_by``, and
the draft's ``review_state`` has the single value
:data:`REVIEW_STATE`. A row the operator's declaration input already holds is
carried through **unchanged**, never redrafted and never restated at a stronger
status (ticket R04 step 6). The input is the source of that row, not the
register: the register's declared half is a rendering of the input, so a
register rendered before the input's last edit is stale rather than
authoritative. Where the two disagree the draft reports it and carries the
input.

What makes a draft go stale
---------------------------
``--check`` is a byte-equal replay, and the adoption block is measured by
scanning ``docs/``, ``workspaces/`` and ``plans/`` for the register's hash and
path. So a new committed artifact that names a register makes the drafts stale,
and the fix is to re-render. That is the intended coupling: the point of the
block is to tell the operator what adoption would cost, and an enumeration that
went out of date silently would be worse than one that fails a check.

Constitutional standing: a renderer for a Tier 4 review artifact. It evaluates
no gate, invokes no Claude, reads no higher tier it writes to, and coins no
``schema_id``.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from runner.atomic_write import atomic_write_text, canonical_json_bytes
from runner.paths import find_repo_root
from tools import fidelity_declarations as fd
from tools.import_external_proposal import REVISIONS, ImportRefused, Revision, revision_by_id

#: Where the drafts and the checklist are written. Tier 4: a draft is a review
#: artifact, not a declaration.
DRAFTS_DIR_REL = Path("docs/tier4_orchestration_state/msca_dn/declarations")

#: The record type of a draft. Distinct from ``fidelity_declarations`` so a
#: draft can never be mistaken for the input it proposes.
DRAFT_RECORD_TYPE = "fidelity_declaration_draft"

#: Where the adoptable declaration input sits inside a draft.
PAYLOAD_KEY = "declaration_input"

#: The checklist across both revisions.
CHECKLIST_REL = DRAFTS_DIR_REL / "review_checklist.md"

#: The ESR artifacts of PE-08 / R02 / R03.
ESR_DIR_REL = Path("docs/tier4_orchestration_state/msca_dn/esr")
DISPOSITIONS_REL = ESR_DIR_REL / "dispositions_f60ae6e0a2a1.json"
REVIEW_NOTES_RECORD_TYPE = "esr_review_notes"

SPEC_REL = "plans/msca_dn_pre_evaluation_spec.md"
TICKET = "R04 of plans/pe08_review_and_pe09_handoff_tickets.md"

#: The one review state a draft may carry. There is no "approved" value: an
#: operator decision is recorded by the operator, not by this renderer.
REVIEW_STATE = "agent_drafted_pending_operator_review"

DECLARED_ON = "2026-10-07"
DECLARED_BY = (
    "drafted in a Claude Code session, 2026-10-07, from the committed registers, import "
    "manifests, dispositions and review notes. Every row is a proposal for operator review "
    "and none records an operator declaration"
)

#: What a row's ``declared_by`` says, so an adopted row cannot read as approval.
ROW_DECLARED_BY = (
    "R04 draft, pending operator confirmation; replace with the operator's own attribution "
    "on adoption"
)

#: The three claims of ticket R04 step 3, and where each is checkable.
CLAIM_SCOPES: dict[str, str] = {
    "extraction_fidelity_against_the_sanitised_pdf": (
        "Whether this sub-section is present in the extraction of this revision's sanitised "
        "PDF, and whether the extraction lost anything. Measured here."
    ),
    "difference_between_the_sanitised_revisions": (
        "Whether this sub-section differs from the predecessor revision's. Measured here, by "
        "the import manifest's page-by-page comparison and the two derived halves."
    ),
    "fidelity_against_the_submitted_original": (
        "Whether this sub-section says what the submitted original said. Not measurable here: "
        "the original is stored only in the private network. Checkable at PE-09 alone."
    ),
}

_EXTRACTION = "extraction_fidelity_against_the_sanitised_pdf"
_REVISIONS_CLAIM = "difference_between_the_sanitised_revisions"
_ORIGINAL = "fidelity_against_the_submitted_original"

STATUS_VOCABULARY = (
    "CLAUDE.md §12.2: Confirmed (directly evidenced by a named source), Inferred (derived from "
    "confirmed evidence, chain stated), Assumed (adopted in the absence of direct evidence), "
    "Unresolved (conflicting or missing information). No other value is used, and no status is "
    "raised by a measurement in a different claim scope."
)


class DraftError(Exception):
    """Refusal: an input is absent, malformed, or ambiguous."""


# --------------------------------------------------------------------------- #
# Reading the committed inputs
# --------------------------------------------------------------------------- #


def _read_json(repo_root: Path, rel: Path, label: str) -> dict[str, Any]:
    path = repo_root / rel
    if not path.is_file():
        raise DraftError(f"{label} is absent at {rel.as_posix()}")
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise DraftError(f"{label} at {rel.as_posix()} is not valid JSON ({exc})") from exc
    if not isinstance(data, dict):
        raise DraftError(f"{label} at {rel.as_posix()} must hold a JSON object")
    return data


def _sha256(repo_root: Path, rel: Path) -> str:
    return fd.file_sha256(repo_root / rel)


def load_register(repo_root: Path, revision: Revision) -> dict[str, Any]:
    data = _read_json(repo_root, revision.register_rel, f"the {revision.revision_id} register")
    if data.get("record_type") != "fidelity_register":
        raise DraftError(f"{revision.register_rel.as_posix()} is not a fidelity_register record")
    for half in ("provenance", "derived"):
        if not isinstance(data.get(half), dict):
            raise DraftError(f"{revision.register_rel.as_posix()} has no {half!r} half")
    if not isinstance(data["derived"].get("sub_sections"), list):
        raise DraftError(f"{revision.register_rel.as_posix()}: derived half has no inventory")
    return data


def manifest_rel(register: Mapping[str, Any], revision: Revision) -> Path:
    """The import manifest the revision's derived half names."""
    named = register["derived"].get("import_manifest")
    if not isinstance(named, str) or not named.strip():
        raise DraftError(
            f"{revision.register_rel.as_posix()}: the derived half names no import manifest"
        )
    return Path(named)


def load_manifest(repo_root: Path, register: Mapping[str, Any], revision: Revision) -> dict[str, Any]:
    rel = manifest_rel(register, revision)
    data = _read_json(repo_root, rel, f"the {revision.revision_id} import manifest")
    if data.get("record_type") != "external_proposal_import_manifest":
        raise DraftError(
            f"{rel.as_posix()} is not an external_proposal_import_manifest record"
        )
    return data


def active_review_notes_rel(repo_root: Path) -> Path:
    """The review-notes record no other review-notes record supersedes.

    R03's notes supersede R02's in place by naming them, so the current reading
    is the one nothing names. Two unsuperseded records are a refusal: the draft
    would otherwise pick one silently.
    """
    found: dict[str, dict[str, Any]] = {}
    for path in sorted((repo_root / ESR_DIR_REL).glob("review_notes_*.json")):
        rel = path.relative_to(repo_root).as_posix()
        data = _read_json(repo_root, Path(rel), "a review-notes record")
        if data.get("record_type") == REVIEW_NOTES_RECORD_TYPE:
            found[rel] = data
    if not found:
        raise DraftError(f"no {REVIEW_NOTES_RECORD_TYPE!r} record under {ESR_DIR_REL.as_posix()}")
    superseded = {
        str(data["supersedes"]).replace("\\", "/")
        for data in found.values()
        if isinstance(data.get("supersedes"), str)
    }
    active = sorted(rel for rel in found if rel not in superseded)
    if len(active) != 1:
        raise DraftError(
            "the active review notes are ambiguous: "
            f"{', '.join(active) or 'none'} is/are superseded by nothing"
        )
    return Path(active[0])


# --------------------------------------------------------------------------- #
# One revision's inputs, bundled
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class RevisionInputs:
    """One revision's register and import manifest, with their paths.

    These four travel together through every per-sub-section renderer, because
    a measured fact is useless without the pointer that cites it. Bundling them
    keeps each renderer's signature about the sub-section rather than about
    where the numbers came from.
    """

    revision: Revision
    register: Mapping[str, Any]
    register_path: str
    manifest: Mapping[str, Any]
    manifest_path: str

    @property
    def derived(self) -> Mapping[str, Any]:
        return self.register["derived"]

    @property
    def inventory_rows(self) -> Sequence[Mapping[str, Any]]:
        return self.derived["sub_sections"]

    @property
    def inventory(self) -> tuple[str, ...]:
        return tuple(str(row["sub_section_id"]) for row in self.inventory_rows)

    def pointer(self, *segments: str) -> str:
        """A citation into this revision's register."""
        return f"{self.register_path}#{'/'.join(segments)}"

    def manifest_pointer(self, *segments: str) -> str:
        return f"{self.manifest_path}#{'/'.join(segments)}"


def load_inputs(repo_root: Path, revision: Revision) -> RevisionInputs:
    """*revision*'s register and the import manifest its derived half names."""
    register = load_register(repo_root, revision)
    return RevisionInputs(
        revision=revision,
        register=register,
        register_path=revision.register_rel.as_posix(),
        manifest=load_manifest(repo_root, register, revision),
        manifest_path=manifest_rel(register, revision).as_posix(),
    )


# --------------------------------------------------------------------------- #
# The measured facts, per sub-section
# --------------------------------------------------------------------------- #


def _pages(row: Mapping[str, Any], key: str) -> tuple[int, int]:
    value = row.get(key)
    if not (isinstance(value, list) and len(value) == 2):
        raise DraftError(f"sub-section {row.get('sub_section_id')!r}: {key!r} is not a page pair")
    return int(value[0]), int(value[1])


def _in_range(page: Any, bounds: tuple[int, int]) -> bool:
    try:
        number = int(page)
    except (TypeError, ValueError):
        return False
    return bounds[0] <= number <= bounds[1]


def _caveats(row: Mapping[str, Any], inputs: RevisionInputs) -> list[dict[str, Any]]:
    """The extraction caveats the manifest records inside this sub-section.

    Each one qualifies the presence claim and nothing else: a cell whose
    characters are all present but out of reading order is not a lost cell.
    """
    sub_section_id = str(row["sub_section_id"])
    bounds = _pages(row, "derived_pages")
    out: list[dict[str, Any]] = []
    for item in inputs.derived.get("page_map_discrepancies") or []:
        if str(item.get("sub_section_id")) == sub_section_id:
            out.append(
                {
                    "kind": "page_map_discrepancy",
                    "detail": (
                        f"the declared start page is {item.get('declared_start_page')} and the "
                        f"derived one is {item.get('derived_start_page')}"
                    ),
                    "source": inputs.pointer("derived", "page_map_discrepancies"),
                }
            )
    tables = inputs.manifest.get("tables") or {}
    cells = [
        cell
        for cell in tables.get("cells_not_contiguous_in_page_text") or []
        if _in_range(cell.get("page"), bounds)
    ]
    if cells:
        out.append(
            {
                "kind": "table_cells_not_in_reading_order",
                "detail": (
                    f"{len(cells)} table cell(s) on page(s) "
                    f"{', '.join(str(c.get('page')) for c in cells)} carry every character but "
                    "not as a contiguous substring of the page, so no span into the page can be "
                    "derived from them"
                ),
                "source": inputs.manifest_pointer(
                    "tables", "cells_not_contiguous_in_page_text"
                ),
            }
        )
    # A claim id is "<sub_section_id>-cNNN", and the importer recovers the
    # sub-section from it the same way. Page ranges overlap at a boundary - a
    # claim that straddles one would otherwise land on both sub-sections - so
    # the id, not the page, says whose claim it is.
    claims = inputs.manifest.get("claims") or {}
    spanless = [
        claim
        for claim in claims.get("claims_without_span") or []
        if str(claim.get("claim_id", "")).rsplit("-c", 1)[0] == sub_section_id
    ]
    if spanless:
        out.append(
            {
                "kind": "claims_without_a_span",
                "detail": (
                    f"{len(spanless)} claim(s) — "
                    f"{', '.join(str(c.get('claim_id')) for c in spanless)} — straddle a page "
                    "break and live in no single page source, so they are present but not locatable"
                ),
                "source": inputs.manifest_pointer("claims", "claims_without_span"),
            }
        )
    return out


def _presence(row: Mapping[str, Any], inputs: RevisionInputs) -> dict[str, Any]:
    """Whether this sub-section is present in the extraction, and at what cost."""
    sub_section_id = str(row["sub_section_id"])
    derived = _pages(row, "derived_pages")
    declared = _pages(row, "declared_pages")
    losses = inputs.derived.get("per_page_extraction_losses") or {}
    pages_with_loss = losses.get("pages_with_loss")
    if not isinstance(pages_with_loss, list):
        raise DraftError(
            f"{inputs.register_path}: per_page_extraction_losses has no pages_with_loss list"
        )
    return {
        "value": "present in this revision's extraction",
        "claim_scope": _EXTRACTION,
        "declared_status": "Confirmed",
        "basis": (
            f"{inputs.pointer('derived', 'sub_sections', sub_section_id)}: "
            f"{row['paragraphs']} prose block(s), {row['table_rows']} table row(s), "
            f"{row['characters']} characters and {row['claims']} extracted claim(s), over "
            f"derived pages {derived[0]}-{derived[1]} (declared {declared[0]}-{declared[1]}). "
            f"File-level accounting: {losses.get('total_accounted')} of "
            f"{losses.get('total_page_chars')} non-whitespace characters accounted for, "
            f"{len(pages_with_loss)} page(s) with loss."
        ),
        "scope_limit": (
            "This states what the extraction of this PDF holds. It is not a statement about the "
            "submitted original: see fidelity_to_submitted_original on this row."
        ),
        "caveats": _caveats(row, inputs),
    }


def _transformation(row: Mapping[str, Any], inputs: RevisionInputs) -> dict[str, Any]:
    """What sanitisation did: the operator's declaration, and what bounds it."""
    sub_section_id = str(row["sub_section_id"])
    figures = (inputs.derived.get("figures") or {}).get("images_on_any_page")
    citations = inputs.derived.get("citation_marker_counts") or {}
    body = (inputs.derived.get("body_point_size") or {}).get("body_point_size")
    measured = [
        {
            "fact": f"no image appears on any page of the copy ({figures} images)",
            "source": inputs.pointer("derived", "figures", "images_on_any_page"),
            "declared_status": "Confirmed",
        },
        {
            "fact": (
                "no citation marker survives anywhere in the copy: "
                + ", ".join(f"{k} = {v}" for k, v in sorted(citations.items()))
            ),
            "source": inputs.pointer("derived", "citation_marker_counts"),
            "declared_status": "Confirmed",
        },
        {
            "fact": f"the body text of the copy is set at {body} pt",
            "source": inputs.pointer("derived", "body_point_size"),
            "declared_status": "Confirmed",
        },
        {
            "fact": (
                f"this sub-section carries {row['table_rows']} rendered table row(s) in the copy"
            ),
            "source": inputs.pointer(
                "derived", "sub_sections", sub_section_id, "table_rows"
            ),
            "declared_status": "Confirmed",
        },
    ]
    return {
        "value": (
            "sanitised: identifiers generalised, some prose omitted or rephrased, every figure "
            "lost and every citation removed. How much prose was changed in this sub-section is "
            "not measured."
        ),
        "claim_scope": _ORIGINAL,
        "scope_note": (
            "The operator's document-wide declaration about the step from the submission to this "
            "copy. The per-sub-section judgment on the same claim is this row's "
            "fidelity_to_submitted_original, and it stays Unresolved."
        ),
        "declared_status": "Assumed",
        "basis": (
            "the operator's PE-01 declaration at "
            f"{inputs.pointer('provenance', 'transformation')}, Assumed where it stands. The "
            "parts of it listed under measured_parts are Confirmed document-wide by the derived "
            "half. The status of this field is the weaker of the two, because the part that "
            "matters per sub-section — how much prose moved — has no measurement."
        ),
        "measured_parts": measured,
        "not_measured": (
            "The amount of prose omitted or rephrased in this sub-section, and whether any "
            "passage was removed rather than rewritten. No artifact in this repository measures "
            "either; both need the submitted original (PE-09)."
        ),
    }


def _first_revision_difference(
    row: Mapping[str, Any], inputs: RevisionInputs, successor: Optional[Mapping[str, Any]]
) -> dict[str, Any]:
    """The revision claim of a revision with no predecessor.

    There is nothing to compare backwards, so the measurable statement is the
    forward one: what the revision superseding this one changed, and whether
    any of it falls inside this sub-section.
    """
    bounds = _pages(row, "derived_pages")
    basis = (
        f"{inputs.pointer('provenance')} carries no 'revision' block, and "
        f"{inputs.manifest_pointer('revision')} records this revision as the first sanitised "
        "derivative."
    )
    if successor is not None:
        changed = [page for page in successor["changed_pages"] if _in_range(page, bounds)]
        every = ", ".join(str(p) for p in successor["changed_pages"]) or "none"
        here = (
            "page " + ", ".join(str(p) for p in changed) + " falls"
            if changed
            else "none falls"
        )
        basis += (
            f" The successor revision {successor['revision_id']!r} differs from this one on "
            f"page(s) {every}; {here} inside this sub-section, per "
            f"{successor['manifest_path']}#revision/comparison_with_predecessor."
        )
    return {
        "value": "no predecessor revision: this is the first sanitised derivative",
        "claim_scope": _REVISIONS_CLAIM,
        "declared_status": "Confirmed",
        "basis": basis,
    }


def _successor_revision_difference(
    row: Mapping[str, Any],
    inputs: RevisionInputs,
    predecessor_row: Optional[Mapping[str, Any]],
    predecessor_register_path: Optional[str],
) -> dict[str, Any]:
    """The revision claim of a revision that supersedes another."""
    sub_section_id = str(row["sub_section_id"])
    bounds = _pages(row, "derived_pages")
    revision_block = inputs.manifest.get("revision") or {}
    comparison = revision_block.get("comparison_with_predecessor") or {}
    changed_pages = [int(p) for p in comparison.get("pages_changed") or []]
    here = [page for page in changed_pages if _in_range(page, bounds)]
    if predecessor_row is None:
        raise DraftError(
            f"sub-section {sub_section_id!r} is absent from the predecessor revision's "
            "inventory; the two inventories must agree before a difference can be stated"
        )
    deltas = [
        f"{field} {predecessor_row[field]} → {row[field]}"
        for field in ("paragraphs", "table_rows", "characters", "claims")
        if predecessor_row[field] != row[field]
    ]
    predecessor_id = comparison.get("compared_with_revision")
    if here or deltas:
        parts = [
            part
            for part in (
                f"re-typeset page(s) {', '.join(str(p) for p in here)}" if here else "",
                ", ".join(deltas) if deltas else "",
            )
            if part
        ]
        value = f"changed from {predecessor_id}: " + "; ".join(parts)
    else:
        value = f"unchanged from {predecessor_id}"
    return {
        "value": value,
        "claim_scope": _REVISIONS_CLAIM,
        "declared_status": "Confirmed",
        "basis": (
            f"{inputs.manifest_pointer('revision', 'comparison_with_predecessor')}: "
            f"{comparison.get('pages_identical')} of {comparison.get('pages_before')} page "
            f"texts identical, page(s) "
            f"{', '.join(str(p) for p in changed_pages) or 'none'} changed, compared against "
            f"sha256 {comparison.get('compared_with_sha256')}. The per-sub-section counts are "
            "the two derived halves, "
            f"{inputs.pointer('derived', 'sub_sections', sub_section_id)} against "
            f"{predecessor_register_path}#derived/sub_sections/{sub_section_id}."
        ),
    }


def _original_fidelity(row: Mapping[str, Any], inputs: RevisionInputs) -> dict[str, Any]:
    """The per-sub-section claim nothing available here can resolve."""
    sub_section_id = str(row["sub_section_id"])
    return {
        "value": "not established for this sub-section",
        "claim_scope": _ORIGINAL,
        "declared_status": "Unresolved",
        "basis": (
            f"{inputs.pointer('provenance', 'authoritative_original')} records the original as "
            "stored in the private network only, and nothing in this repository compares this "
            "sub-section against it. The presence claim and the extraction accounting on this "
            "row bound the step from this PDF to its extraction, not the step from the "
            "submission to this PDF."
        ),
        "resolution_requires": (
            f"an operator reading of sub-section {sub_section_id} against the submitted "
            f"original, inside the private network ({SPEC_REL}, PE-09). Until that reading is "
            "recorded the status stays Unresolved: no measurement available here can raise it."
        ),
    }


# --------------------------------------------------------------------------- #
# ESR dependencies (ticket R04 step 8)
# --------------------------------------------------------------------------- #

#: What a confirmed declaration would change, per disposition. These are
#: statements about how the disposition vocabulary works, not new findings.
_CONSEQUENCE: dict[str, str] = {
    "not_detected_despite_sufficient_preserved_evidence": (
        "This disposition asserts the evidence was sufficient and preserved. A declaration that "
        "the sub-section is no thinner than the submission's would carry it; a declaration that "
        "material was removed would move the row to 'partially_observable' or "
        "'not_assessable_from_this_copy'."
    ),
    "partially_observable": (
        "A declaration narrowing what sanitisation removed from this sub-section would either "
        "hold the partial reading or move the row to 'independently_detected' or "
        "'not_detected_despite_sufficient_preserved_evidence'."
    ),
    "independently_detected": (
        "The detection stands on the copy's own text, so a declaration cannot unmake it. A "
        "declaration that this sub-section was rewritten would make the detection a result over "
        "the derivative alone."
    ),
    "not_assessable_from_this_copy": (
        "A declaration that the removed material is recoverable, or that it was never present, "
        "would make the row assessable or close it."
    ),
}


def _dependencies(
    dispositions: Mapping[str, Any],
    notes: Mapping[str, Any],
    inventory: Sequence[str],
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    """Per sub-section, the dispositions that lean on a declaration about it.

    A row is attached to a sub-section only where the dispositions record names
    one: in a ``current_evidence`` reference, or in an ``evidence_basis``
    pointer into ``derived/sub_sections/<id>/``. Nothing is inferred from
    wording, so a declaration-dependent row that names no sub-section is
    returned separately rather than assigned to a guess.
    """
    recommendation = {
        str(row.get("observation_id")): row for row in notes.get("rows") or []
    }
    by_sub: dict[str, list[dict[str, Any]]] = {sub: [] for sub in inventory}
    unattached: list[dict[str, Any]] = []
    prefix = "derived/sub_sections/"
    for row in dispositions.get("rows") or []:
        observation_id = str(row.get("observation_id"))
        note = recommendation.get(observation_id) or {}
        subs: dict[str, str] = {}
        for ref in row.get("current_evidence") or []:
            sub = str(ref.get("sub_section_id"))
            if sub in by_sub:
                subs[sub] = "cited as current evidence in the dispositions record"
        for pointer in row.get("evidence_basis") or []:
            text = str(pointer)
            if text.startswith(prefix):
                sub = text[len(prefix):].split("/")[0]
                if sub in by_sub:
                    subs.setdefault(sub, f"named by the evidence_basis pointer {text!r}")
        disposition = str(row.get("disposition"))
        entry = {
            "observation_id": observation_id,
            "disposition": disposition,
            "review_recommendation": note.get("recommendation"),
            "declared_status_of_the_disposition": row.get("declared_status"),
            "evidence_preserved_status": row.get("evidence_preserved_status"),
            "what_confirmation_would_change": _CONSEQUENCE.get(
                disposition, "No consequence is recorded for this disposition value."
            ),
        }
        if note.get("operator_decision"):
            entry["operator_decision_already_asked"] = note["operator_decision"]
        entry = {key: value for key, value in entry.items() if value is not None}
        if subs:
            for sub, why in sorted(subs.items()):
                by_sub[sub].append({**entry, "dependency": why})
        elif note.get("recommendation") == "revisit_after_declaration":
            unattached.append(
                {
                    **entry,
                    "dependency": (
                        "the review notes recommend revisiting this row after a declaration, and "
                        "the dispositions record names no sub-section for it"
                    ),
                    "operator_question": (
                        "Name the sub-section whose declaration this row depends on. Nothing here "
                        "infers it from the wording."
                    ),
                }
            )
    return by_sub, unattached


# --------------------------------------------------------------------------- #
# Checking the operator's existing declarations against measurement (step 7)
# --------------------------------------------------------------------------- #


#: The three verdicts a checked declaration can carry. ``qualified_in_place``
#: is for a declaration the derived half already records a difference against,
#: rather than one measurement contradicts outright.
VERDICTS: tuple[str, ...] = ("holds", "contradicted", "qualified_in_place")


def _check(
    inputs: RevisionInputs, pointer: Sequence[str], measurement: str, verdict: str
) -> dict[str, Any]:
    """One checked provenance declaration, with what it says and what was measured."""
    declared: Any = inputs.register
    for segment in pointer:
        declared = (declared or {}).get(segment) if isinstance(declared, Mapping) else None
    return {
        "declaration": inputs.pointer(*pointer),
        "declared": declared,
        "measurement": measurement,
        "verdict": verdict,
    }


def _body_size_check(inputs: RevisionInputs) -> dict[str, Any]:
    """The body-size declaration, and the correction it needs where it fails.

    Ticket R04 step 7 names uniform 12-point body text as a declaration
    measurement may contradict. It holds in the first revision, whose only
    other size is bullets, and fails in the revised one, which carries prose
    below the body size.
    """
    body = inputs.derived.get("body_point_size") or {}
    distribution = body.get("distribution") or {}
    uniform = body.get("other_sizes_are_bullets_and_spaces_only")
    other = {
        size: count
        for size, count in distribution.items()
        if size != body.get("body_point_size")
    }
    sizes = (
        ", ".join(
            f"{size} pt over {count} character(s)" for size, count in sorted(other.items())
        )
        or "none"
    )
    check = _check(
        inputs,
        ("provenance", "transformation", "reformatting", "body_point_size"),
        (
            f"derived/body_point_size: the body is {body.get('body_point_size')} pt; other "
            f"sizes {sizes}; other_sizes_are_bullets_and_spaces_only = {json.dumps(uniform)}"
        ),
        "holds" if uniform else "contradicted",
    )
    if uniform:
        return check
    # A size whose character set is bullets and spaces alone is decoration, not
    # prose, so it does not contradict the declaration.
    carrying = {
        size: detail
        for size, detail in (body.get("other_sizes_character_sets") or {}).items()
        if detail.strip(" • ")
    }
    limitations = inputs.register["provenance"].get("known_extraction_limitations") or {}
    check["evidence"] = {
        "sizes_carrying_more_than_bullets": carrying,
        "characters": {size: distribution.get(size) for size in carrying},
    }
    if limitations.get("prose_below_the_body_point_size"):
        check["evidence"]["register_note"] = inputs.pointer(
            "provenance", "known_extraction_limitations", "prose_below_the_body_point_size"
        )
    check["proposed_correction"] = (
        "Replace the bare declaration 12 with a statement that the body of this revision is "
        f"set at {body.get('body_point_size')} pt except for "
        + ", ".join(
            f"{distribution.get(size)} character(s) at {size} pt" for size in sorted(carrying)
        )
        + " that carry prose rather than bullets, and name derived/body_point_size as the "
        "measurement. The declaration is the operator's, so this correction is a proposal: "
        "applying it edits the provenance literal in tools/author_msca_dn_workspace.py and "
        "changes the register's bytes."
    )
    check["correction_status"] = "Confirmed"
    check["correction_status_basis"] = (
        "the contradiction is measured, in the derived half of this register. Which page "
        "carries the smaller prose is Inferred and not asserted here: the only changed page "
        "of this revision is the one the import manifest names, and the derived half records "
        "no page for the size."
    )
    check["reviewer_status"] = REVIEW_STATE
    return check


def _declaration_checks(inputs: RevisionInputs) -> list[dict[str, Any]]:
    """Every provenance declaration this draft can check, and its verdict.

    Each check runs whether or not it finds something, so a declaration that
    holds is visibly checked rather than silently absent. A contradicted
    declaration carries a proposed correction; nothing here applies one.
    """
    figures = (inputs.derived.get("figures") or {}).get("images_on_any_page")
    citations = inputs.derived.get("citation_marker_counts") or {}
    labels = (inputs.derived.get("table_3_1a") or {}).get("label_block_counts") or {}
    uniform_labels = len(set(labels.values())) <= 1

    table_check = _check(
        inputs,
        ("provenance", "transformation", "reformatting", "table_3_1a"),
        "derived/table_3_1a/label_block_counts = "
        + ", ".join(f"{k}: {v}" for k, v in sorted(labels.items())),
        "holds" if uniform_labels else "qualified_in_place",
    )
    if not uniform_labels:
        table_check["note"] = (
            "The label counts differ, and the derived half's own basis already says they are "
            "recorded as measured and may differ. No correction is proposed: the register "
            "records the difference rather than resolving it."
        )
    return [
        _check(
            inputs,
            ("provenance", "transformation", "figures"),
            f"derived/figures/images_on_any_page = {figures}",
            "holds" if figures == 0 else "contradicted",
        ),
        _check(
            inputs,
            ("provenance", "transformation", "citations"),
            "derived/citation_marker_counts = "
            + ", ".join(f"{k}: {v}" for k, v in sorted(citations.items())),
            "holds" if all(v == 0 for v in citations.values()) else "contradicted",
        ),
        _body_size_check(inputs),
        table_check,
    ]


# --------------------------------------------------------------------------- #
# Prior declarations (ticket R04 step 6)
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class PayloadRows:
    """The rows of an adoptable payload, and where each came from."""

    rows: tuple[dict[str, Any], ...]
    carried: tuple[str, ...]
    """Sub-sections whose row is the operator's, carried through unchanged."""
    drafted: tuple[str, ...]
    """Sub-sections whose row this module drafted."""


def merge_prior(
    prior_rows: Sequence[Mapping[str, Any]],
    drafted: Sequence[Mapping[str, Any]],
    inventory: Sequence[str],
) -> PayloadRows:
    """*drafted* rows, with any operator row of the same sub-section winning.

    An operator declaration is carried through byte-for-byte and is never
    redrafted, restated, or raised to a stronger status. The draft only fills
    the sub-sections the operator has not declared.
    """
    by_prior = {str(row["sub_section_id"]): dict(row) for row in prior_rows}
    by_draft = {str(row["sub_section_id"]): dict(row) for row in drafted}
    rows: list[dict[str, Any]] = []
    carried: list[str] = []
    for sub in inventory:
        if sub in by_prior:
            rows.append(by_prior[sub])
            carried.append(sub)
        elif sub in by_draft:
            rows.append(by_draft[sub])
    unknown = sorted(set(by_prior) - set(inventory))
    if unknown:
        raise DraftError(
            "the register declares sub-section(s) "
            f"{', '.join(unknown)}, which the derived inventory does not list"
        )
    return PayloadRows(
        rows=tuple(rows),
        carried=tuple(carried),
        drafted=tuple(sub for sub in inventory if sub not in by_prior),
    )


# --------------------------------------------------------------------------- #
# Hash dependencies (ticket R04 acceptance 6)
# --------------------------------------------------------------------------- #

#: Where to look for artifacts that pin a register's bytes.
_SCANNED_DIRS: tuple[str, ...] = ("docs", "workspaces", "plans")
_SCANNED_SUFFIXES: tuple[str, ...] = (".json", ".md")

#: How short a recorded prefix may be and still count. The review reports print
#: a 16-character prefix followed by an ellipsis.
_PREFIX_LENGTH = 16


@dataclass(frozen=True)
class Dependents:
    """What the committed tree records about one artifact's bytes and path."""

    pinned_by_hash: tuple[dict[str, str], ...]
    referenced_by_path: tuple[str, ...]


def _scanned_files(repo_root: Path) -> list[Path]:
    """The committed JSON and Markdown files the scan reads.

    The drafts' own directory is excluded: a draft records the hashes itself,
    so including it would make the scan a fixed point of its own output.
    """
    skip = (repo_root / DRAFTS_DIR_REL).resolve()
    out: list[Path] = []
    for name in _SCANNED_DIRS:
        base = repo_root / name
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if path.suffix not in _SCANNED_SUFFIXES or not path.is_file():
                continue
            resolved = path.resolve()
            if resolved == skip or skip in resolved.parents:
                continue
            out.append(path)
    return out


def dependents_of(repo_root: Path, rel: Path, sha256: str) -> Dependents:
    """Every committed artifact that records *rel*'s bytes, or names its path.

    Measured, not listed by hand: adopting a declaration changes the register's
    bytes, and this is what has to be re-recorded or explained afterwards. One
    pass over the tree answers both questions, since both read the same text.

    A 16-character prefix counts as a pin, because that is what the review
    reports print before their ellipsis.
    """
    needle = rel.as_posix()
    prefix = sha256[:_PREFIX_LENGTH]
    pinned: list[dict[str, str]] = []
    named: list[str] = []
    for path in _scanned_files(repo_root):
        here = path.relative_to(repo_root).as_posix()
        if here == needle:
            continue
        try:
            text = path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError):
            continue
        if sha256 in text:
            pinned.append({"path": here, "records": "the full sha256"})
        elif prefix in text:
            pinned.append({"path": here, "records": f"the first {_PREFIX_LENGTH} characters"})
        if needle in text:
            named.append(here)
    return Dependents(pinned_by_hash=tuple(pinned), referenced_by_path=tuple(named))


# --------------------------------------------------------------------------- #
# Rendering a draft
# --------------------------------------------------------------------------- #


def _successor(repo_root: Path, revision: Revision) -> Optional[dict[str, Any]]:
    """What the revision superseding *revision* changed, or ``None``."""
    for other in REVISIONS:
        if other.supersedes != revision.revision_id:
            continue
        other_inputs = load_inputs(repo_root, other)
        revision_block = other_inputs.manifest.get("revision") or {}
        comparison = revision_block.get("comparison_with_predecessor") or {}
        return {
            "revision_id": other.revision_id,
            "manifest_path": other_inputs.manifest_path,
            "changed_pages": [int(p) for p in comparison.get("pages_changed") or []],
        }
    return None


def _predecessor(revision: Revision) -> Optional[Revision]:
    """The revision *revision* supersedes, or ``None`` for the first one."""
    for other in REVISIONS:
        if other.revision_id == revision.supersedes:
            return other
    if revision.supersedes is not None:
        raise DraftError(
            f"revision {revision.revision_id!r} supersedes {revision.supersedes!r}, which is not "
            "a known revision"
        )
    return None


def draft_rel(revision: Revision) -> Path:
    return DRAFTS_DIR_REL / f"draft_{revision.revision_id}.json"


def _draft_rows(
    repo_root: Path, inputs: RevisionInputs, predecessor: Optional[Revision]
) -> list[dict[str, Any]]:
    """One drafted row per sub-section of the revision's derived inventory."""
    predecessor_rows: dict[str, Mapping[str, Any]] = {}
    predecessor_path: Optional[str] = None
    if predecessor is not None:
        predecessor_inputs = load_inputs(repo_root, predecessor)
        predecessor_path = predecessor_inputs.register_path
        predecessor_rows = {
            str(row["sub_section_id"]): row for row in predecessor_inputs.inventory_rows
        }
    successor = (
        _successor(repo_root, inputs.revision) if inputs.revision.supersedes is None else None
    )
    rows: list[dict[str, Any]] = []
    for row in inputs.inventory_rows:
        sub_section_id = str(row["sub_section_id"])
        if inputs.revision.supersedes is None:
            difference = _first_revision_difference(row, inputs, successor)
        else:
            difference = _successor_revision_difference(
                row, inputs, predecessor_rows.get(sub_section_id), predecessor_path
            )
        rows.append(
            {
                "sub_section_id": sub_section_id,
                "title": row.get("title"),
                "presence": _presence(row, inputs),
                "transformation": _transformation(row, inputs),
                "revision_difference": difference,
                "fidelity_to_submitted_original": _original_fidelity(row, inputs),
                "declared_by": ROW_DECLARED_BY,
                "declared_on": DECLARED_ON,
                "review_state": REVIEW_STATE,
            }
        )
    return rows


def _input_rows(
    repo_root: Path,
    inputs: RevisionInputs,
    predecessor: Optional[Revision],
    notes_rel: Path,
) -> list[dict[str, Any]]:
    """What this draft read, each with the bytes it read."""
    rows = [
        {
            "role": "the register this declaration belongs to",
            "path": inputs.register_path,
            "sha256": _sha256(repo_root, inputs.revision.register_rel),
        },
        {
            "role": "the import manifest behind its derived half",
            "path": inputs.manifest_path,
            "sha256": _sha256(repo_root, Path(inputs.manifest_path)),
        },
    ]
    if predecessor is not None:
        rows.append(
            {
                "role": "the predecessor revision's register, for the revision difference",
                "path": predecessor.register_rel.as_posix(),
                "sha256": _sha256(repo_root, predecessor.register_rel),
            }
        )
    rows.append(
        {
            "role": "the ESR dispositions, for the dependencies below",
            "path": DISPOSITIONS_REL.as_posix(),
            "sha256": _sha256(repo_root, DISPOSITIONS_REL),
        }
    )
    rows.append(
        {
            "role": "the active review notes, for each row's recommendation",
            "path": notes_rel.as_posix(),
            "sha256": _sha256(repo_root, notes_rel),
        }
    )
    declarations_rel = fd.declarations_rel(inputs.revision.revision_id)
    if (repo_root / declarations_rel).is_file():
        rows.append(
            {
                "role": "the operator's declaration input, whose rows are carried unchanged",
                "path": declarations_rel.as_posix(),
                "sha256": _sha256(repo_root, declarations_rel),
            }
        )
    return rows


def _esr_block(repo_root: Path, inputs: RevisionInputs, notes_rel: Path) -> dict[str, Any]:
    """The ESR dispositions that lean on this revision's declarations.

    A disposition record binds one register. Where it binds another revision's,
    this revision's draft says so and borrows nothing.
    """
    dispositions = _read_json(repo_root, DISPOSITIONS_REL, "the ESR dispositions")
    binds = str(dispositions.get("fidelity_register", "")).replace("\\", "/")
    if binds != inputs.register_path:
        return {
            "dispositions": DISPOSITIONS_REL.as_posix(),
            "binds_register": binds,
            "note": (
                "No ESR disposition binds this revision: the comparison is bound to the register "
                f"at {binds}. A declaration here changes no disposition until a successor "
                "comparison binds this revision."
            ),
            "by_sub_section": [],
            "declaration_dependent_without_a_sub_section": [],
        }
    notes = _read_json(repo_root, notes_rel, "the active review notes")
    by_sub, unattached = _dependencies(dispositions, notes, inputs.inventory)
    return {
        "dispositions": DISPOSITIONS_REL.as_posix(),
        "dispositions_sha256": _sha256(repo_root, DISPOSITIONS_REL),
        "review_notes": notes_rel.as_posix(),
        "review_notes_sha256": _sha256(repo_root, notes_rel),
        "attribution_rule": (
            "A disposition is attached to a sub-section only where the dispositions record "
            "names one, in a current_evidence reference or in an evidence_basis pointer into "
            "derived/sub_sections/. Nothing is inferred from wording."
        ),
        "by_sub_section": [
            {"sub_section_id": sub, "observations": by_sub[sub]}
            for sub in inputs.inventory
            if by_sub[sub]
        ],
        "declaration_dependent_without_a_sub_section": unattached,
    }


def _adoption_block(repo_root: Path, inputs: RevisionInputs) -> dict[str, Any]:
    """What adopting this draft would change, and what it would cost."""
    revision_id = inputs.revision.revision_id
    target = fd.declarations_rel(revision_id).as_posix()
    register_sha256 = _sha256(repo_root, inputs.revision.register_rel)
    manifest_path = Path(inputs.manifest_path)
    manifest_sha256 = _sha256(repo_root, manifest_path)
    register_dependents = dependents_of(
        repo_root, inputs.revision.register_rel, register_sha256
    )
    manifest_dependents = dependents_of(repo_root, manifest_path, manifest_sha256)
    return {
        "target": target,
        "steps": [
            "Record the operator review of this draft, row by row.",
            "Correct each row the review changes, and replace every row's 'declared_by' with "
            "the operator's own attribution.",
            f"Write the reviewed payload to {target} (py -3.10 -m "
            f"tools.draft_fidelity_declarations --emit-input {revision_id} prints this draft's "
            "payload unchanged).",
            "py -3.10 -m tools.author_msca_dn_workspace  (the first revision's register)",
            "py -3.10 -m tools.import_external_proposal  (every revision's register)",
            "py -3.10 -m tools.author_msca_dn_workspace --check  and  "
            "py -3.10 -m tools.import_external_proposal --check  (both exit 0)",
            "Re-record the register hash in every artifact this draft lists under "
            "adoption/pinned_by_hash, or state why each stays as written.",
        ],
        "provenance_record_must_carry": [
            "the reviewer, the date, and the draft sha256 the review was taken over",
            "a per-row decision: adopted as drafted, adopted as corrected, or withheld",
            "the register sha256 before and after, and what each pinned artifact now records",
            "every row whose status the review changed, and the evidence that moved it",
            "which proposed corrections to the provenance header were applied, and which stand",
        ],
        "register_sha256_before_adoption": register_sha256,
        "pinned_by_hash": list(register_dependents.pinned_by_hash),
        "referenced_by_path": list(register_dependents.referenced_by_path),
        "import_manifest": {
            "path": inputs.manifest_path,
            "sha256": manifest_sha256,
            "changed_by_adoption": False,
            "why": (
                "The manifest renders the derived half and the page comparison. Neither "
                "reads a declaration, so adoption leaves its bytes as they are."
            ),
            "pinned_by_hash": list(manifest_dependents.pinned_by_hash),
            "referenced_by_path": list(manifest_dependents.referenced_by_path),
        },
        "preservation_rule": (
            "The historical artifacts stay as written. A comparison that pinned the old hash "
            "stays replayable from the register version it names, so a re-recording is a "
            "successor artifact and never an edit in place."
        ),
    }


def _prior_declarations_block(
    repo_root: Path,
    inputs: RevisionInputs,
    declarations: fd.Declarations,
    merged: PayloadRows,
) -> dict[str, Any]:
    """What the operator has already declared, and where this draft read it.

    The operator's declarations live in the durable input, not in the register:
    the register's declared half is a rendering of that input, and a register
    rendered before the last edit is simply stale. So the input is what this
    draft carries through, and the register's own rows are reported beside it
    so a disagreement between the two is visible rather than silently resolved.
    """
    in_register = fd.read_declared_half(repo_root, inputs.revision.register_rel)
    block: dict[str, Any] = {
        "declaration_input": fd.declarations_rel(inputs.revision.revision_id).as_posix(),
        "input_present": declarations.supplied,
        "declared_in_the_input": [row["sub_section_id"] for row in declarations.rows],
        "declared_in_the_register_today": list(in_register.sub_section_ids),
        "carried_through_unchanged": list(merged.carried),
        "drafted_here": list(merged.drafted),
        "rule": (
            "An operator declaration is read from the durable input and carried into the payload "
            "byte-for-byte, never redrafted and never restated at a stronger status (ticket R04 "
            "step 6). This draft fills only the sub-sections the input does not declare."
        ),
    }
    only_in_register = [
        sub
        for sub in in_register.sub_section_ids
        if sub not in {row["sub_section_id"] for row in declarations.rows}
    ]
    if only_in_register:
        block["declared_only_in_the_register"] = only_in_register
        block["note"] = (
            "The register declares sub-section(s) "
            f"{', '.join(only_in_register)} that the input does not. This draft carries the "
            "input, so those rows are drafted here rather than preserved. Either the operator "
            "withdrew them from the input, or they were typed into the register — "
            "tools/fidelity_declarations.guard_against_silent_loss tells the two apart from the "
            "input sha256 the register records, and refuses the second. Resolve that before "
            "adopting this draft."
        )
    return block


def render_draft(repo_root: Path, revision: Revision) -> dict[str, Any]:
    """The draft record for *revision*, from its committed inputs alone."""
    inputs = load_inputs(repo_root, revision)
    predecessor = _predecessor(revision)
    notes_rel = active_review_notes_rel(repo_root)

    declarations = fd.load_declarations(repo_root, revision.revision_id)
    merged = merge_prior(
        declarations.rows, _draft_rows(repo_root, inputs, predecessor), inputs.inventory
    )
    return {
        "record_type": DRAFT_RECORD_TYPE,
        "schema_ref": (
            "No declared schema. "
            ".claude/workflows/system_orchestration/artifact_schema_specification.yaml carries "
            "no schema for a fidelity declaration draft, and no schema_id is coined here."
        ),
        "artifact_purpose": (
            "A draft of the fidelity register's declared half for one revision of the MSCA-DN "
            "sanitised derivative: what can be declared from measurement, what rests on the "
            "operator's PE-01 declaration, and what stays Unresolved until the submitted "
            "original is read inside the private network. Prepared for operator review; it "
            "declares nothing."
        ),
        "spec": SPEC_REL,
        "ticket": TICKET,
        "advisory": True,
        "blocking": False,
        "revision_id": revision.revision_id,
        "derived_inventory": list(inputs.inventory),
        "declared_by": DECLARED_BY,
        "declared_on": DECLARED_ON,
        "review_state": REVIEW_STATE,
        "claim_scopes": CLAIM_SCOPES,
        "status_vocabulary": STATUS_VOCABULARY,
        "inputs": _input_rows(repo_root, inputs, predecessor, notes_rel),
        "prior_declarations": _prior_declarations_block(
            repo_root, inputs, declarations, merged
        ),
        "declarations_checked": _declaration_checks(inputs),
        "esr_dependencies": _esr_block(repo_root, inputs, notes_rel),
        "adoption": _adoption_block(repo_root, inputs),
        PAYLOAD_KEY: {
            "record_type": fd.DECLARATIONS_RECORD_TYPE,
            "revision_id": revision.revision_id,
            fd.SUB_SECTIONS_KEY: list(merged.rows),
        },
    }


# --------------------------------------------------------------------------- #
# The review checklist
# --------------------------------------------------------------------------- #


def _cell(text: Any) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def render_checklist(repo_root: Path, drafts: Sequence[tuple[Revision, Mapping[str, Any]]]) -> str:
    """The operator's checklist across both revisions."""
    lines: list[str] = [
        "# Fidelity declaration drafts — operator review checklist",
        "",
        f"Ticket: {TICKET}  ",
        f"Specification: `{SPEC_REL}`  ",
        f"Review state: `{REVIEW_STATE}`  ",
        f"Drafted on: {DECLARED_ON}",
        "",
        "Both declaration inputs are absent today, so both registers carry an empty declared",
        "half. These drafts propose what each input could say. Nothing here is an operator",
        "declaration, and nothing here changes a disposition.",
        "",
        "## The three claims, kept apart",
        "",
        "| Claim | Where it is checkable | Status in these drafts |",
        "|---|---|---|",
        "| extraction fidelity against the sanitised PDF | here, in the derived half and the "
        "import manifest | Confirmed |",
        "| difference between the sanitised revisions | here, in the manifest's page-by-page "
        "comparison | Confirmed |",
        "| fidelity against the submitted original | the private network only (PE-09) | "
        "Unresolved, every sub-section of both revisions |",
        "",
        "A present passage and a zero extraction loss are facts about the step from the PDF to",
        "its extraction. Neither bounds the step from the submission to the PDF.",
        "",
        "The register's `transformation` field sits on the third claim, one step above the",
        "per-sub-section judgment. It carries the operator's PE-01 declaration about the document",
        "as a whole, so its status is Assumed. The part that matters per sub-section — how much",
        "prose moved — has no measurement anywhere in this repository.",
        "",
    ]
    for revision, draft in drafts:
        payload = draft[PAYLOAD_KEY]
        lines += [
            f"## Revision `{revision.revision_id}`",
            "",
            f"- Draft: `{draft_rel(revision).as_posix()}`",
            f"- Adoption target: `{draft['adoption']['target']}`",
            f"- Register: `{draft['inputs'][0]['path']}` `{draft['inputs'][0]['sha256'][:16]}…`",
            f"- Sub-sections declared: {len(payload[fd.SUB_SECTIONS_KEY])} of "
            f"{len(draft['derived_inventory'])} in the derived inventory",
            f"- Carried through from the operator unchanged: "
            f"{', '.join(draft['prior_declarations']['carried_through_unchanged']) or 'none'}",
            "",
            "| Sub-section | Presence | Revision difference | Original fidelity | Dependent ESR rows | Decision needed |",
            "|---|---|---|---|---|---|",
        ]
        dependent = {
            entry["sub_section_id"]: entry["observations"]
            for entry in draft["esr_dependencies"]["by_sub_section"]
        }
        for row in payload[fd.SUB_SECTIONS_KEY]:
            sub = str(row["sub_section_id"])
            observations = dependent.get(sub) or []
            ids = ", ".join(o["observation_id"] for o in observations) or "—"
            asked = [
                o["observation_id"]
                for o in observations
                if o.get("operator_decision_already_asked")
            ]
            decision = "confirm presence and transformation"
            if asked:
                decision += (
                    "; the draft carries an open question on " + ", ".join(asked)
                )
            difference = row["revision_difference"]["value"]
            if difference.startswith("no predecessor"):
                difference = "first revision, no predecessor"
            lines.append(
                "| `"
                + sub
                + "` | "
                + _cell(row["presence"]["declared_status"])
                + (
                    f", {len(row['presence']['caveats'])} caveat(s)"
                    if row["presence"]["caveats"]
                    else ""
                )
                + " | "
                + _cell(difference)
                + " | "
                + _cell(row["fidelity_to_submitted_original"]["declared_status"])
                + " | "
                + ids
                + " | "
                + decision
                + " |"
            )
        lines.append("")
        contradicted = [
            check
            for check in draft["declarations_checked"]
            if check["verdict"] == "contradicted"
        ]
        lines += ["### Declarations checked against measurement", "", "| Declaration | Verdict |", "|---|---|"]
        for check in draft["declarations_checked"]:
            lines.append(f"| `{check['declaration']}` | {check['verdict']} |")
        lines.append("")
        if contradicted:
            lines += ["### Corrections proposed", ""]
            for check in contradicted:
                lines += [
                    f"- `{check['declaration']}`",
                    f"  - declared: {_cell(check['declared'])}",
                    f"  - measured: {_cell(check['measurement'])}",
                    f"  - proposed: {_cell(check['proposed_correction'])}",
                    f"  - status of the contradiction: {check['correction_status']} — "
                    f"{_cell(check['correction_status_basis'])}",
                    f"  - reviewer status: `{check['reviewer_status']}`",
                ]
            lines.append("")
        else:
            lines += ["No declaration of this revision is contradicted by measurement.", ""]
        unattached = draft["esr_dependencies"]["declaration_dependent_without_a_sub_section"]
        if unattached:
            lines += [
                "### Declaration-dependent rows with no sub-section",
                "",
                "The dispositions record names no sub-section for these, so nothing here assigns",
                "one. Each needs the operator to name it.",
                "",
            ]
            for entry in unattached:
                lines += [
                    f"- **{entry['observation_id']}** ({entry['disposition']})",
                    f"  - {_cell(entry.get('operator_decision_already_asked', ''))}",
                    f"  - {_cell(entry['operator_question'])}",
                ]
            lines.append("")
        adoption = draft["adoption"]
        lines += [
            "### What adoption changes",
            "",
            f"Register sha256 before adoption: `{adoption['register_sha256_before_adoption']}`",
            "",
            "Adopting a declaration rewrites this register, so every artifact that pinned its",
            "bytes has to be re-recorded or explained. Measured, not listed by hand:",
            "",
            "| Artifact | Records |",
            "|---|---|",
        ]
        for entry in adoption["pinned_by_hash"]:
            lines.append(f"| `{entry['path']}` | {entry['records']} |")
        if not adoption["pinned_by_hash"]:
            lines.append("| — | no artifact pins this register's bytes |")
        lines += [
            "",
            "Artifacts that name the register by path, hash or not: "
            + (", ".join(f"`{p}`" for p in adoption["referenced_by_path"]) or "none")
            + ".",
            "",
            "The import manifest `"
            + adoption["import_manifest"]["path"]
            + "` is unaffected. "
            + adoption["import_manifest"]["why"]
            + " Artifacts pinning its bytes: "
            + (
                ", ".join(
                    f"`{entry['path']}`"
                    for entry in adoption["import_manifest"]["pinned_by_hash"]
                )
                or "none"
            )
            + ".",
            "",
            adoption["preservation_rule"],
            "",
            "Steps:",
            "",
        ]
        lines += [f"{i}. {step}" for i, step in enumerate(adoption["steps"], start=1)]
        lines.append("")
    lines += [
        "## What stays open",
        "",
        "- Every `fidelity_to_submitted_original` row is Unresolved. Only a reading against the",
        "  submitted original, inside the private network, can change that (PE-09).",
        "- A declaration drafted here is an agent's proposal. Each row's `declared_by` says so,",
        "  and the operator replaces it on adoption.",
        "- Adoption is the operator's act. This renderer never writes into",
        f"  `{fd.DECLARATIONS_DIR_REL.as_posix()}`.",
        "",
        "## The adoption record this review still owes",
        "",
        "No adoption or provenance record exists yet, because no operator review has been",
        "recorded. When one is, it must carry:",
        "",
    ]
    for requirement in drafts[0][1]["adoption"]["provenance_record_must_carry"]:
        lines.append(f"- {requirement}")
    lines.append("")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- #
# Writing and checking
# --------------------------------------------------------------------------- #


def render_all(repo_root: Path) -> dict[str, bytes]:
    drafts = [(revision, render_draft(repo_root, revision)) for revision in REVISIONS]
    out: dict[str, bytes] = {
        draft_rel(revision).as_posix(): canonical_json_bytes(draft)
        for revision, draft in drafts
    }
    out[CHECKLIST_REL.as_posix()] = render_checklist(repo_root, drafts).encode("utf-8")
    return out


def check(repo_root: Path) -> list[str]:
    """Relative paths whose bytes differ from the rendering, or are absent."""
    return [
        rel
        for rel, data in render_all(repo_root).items()
        if not (repo_root / rel).is_file() or (repo_root / rel).read_bytes() != data
    ]


def write(repo_root: Path) -> list[str]:
    """Write every draft and the checklist; return the paths that changed."""
    changed: list[str] = []
    for rel, data in render_all(repo_root).items():
        target = repo_root / rel
        if target.is_file() and target.read_bytes() == data:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(data.decode("utf-8"), target)
        changed.append(rel)
    return changed


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument(
        "--check", action="store_true", help="exit 1 if any draft or the checklist would change"
    )
    parser.add_argument(
        "--emit-input",
        metavar="REVISION",
        default=None,
        help="print that revision's adoptable declaration input to stdout and write nothing",
    )
    parser.add_argument("--repo-root", type=Path, default=None)
    args = parser.parse_args(argv)
    repo_root = args.repo_root or find_repo_root()
    try:
        if args.emit_input:
            revision = revision_by_id(args.emit_input)
            payload = render_draft(repo_root, revision)[PAYLOAD_KEY]
            sys.stdout.write(canonical_json_bytes(payload).decode("utf-8") + "\n")
            return 0
        if args.check:
            stale = check(repo_root)
            for rel in stale:
                print(f"would change: {rel}")
            print("up to date" if not stale else f"{len(stale)} file(s) would change")
            return 1 if stale else 0
        changed = write(repo_root)
        for rel in changed:
            print(f"wrote: {rel}")
        print("no change" if not changed else f"{len(changed)} file(s) written")
        return 0
    except (DraftError, ImportRefused, fd.FidelityDeclarationsError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
