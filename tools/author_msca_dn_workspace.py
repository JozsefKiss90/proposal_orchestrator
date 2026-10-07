"""Author the MSCA-DN pre-evaluation workspace, deterministically (PE-01).

Ticket PE-01 of ``plans/msca_dn_pre_evaluation_spec.md``: workspace, intake and
provenance freeze. This tool writes every authored artifact of that ticket from
the constants below and from the stored files, so that the ticket replays
byte-equal and nothing in it is typed where it could be derived.

What it writes
--------------
``docs/tier3_project_instantiation/source_materials/msca_dn/fidelity_register.json``
    The fidelity register's ``provenance`` header (spec decision 18): the five
    operator declarations of PE-01 and the input table. Each input carries a
    role, a declared version, the version markers a reader can find in the
    file, and a sha256 and page count derived here from the stored bytes.
    The ``derived`` half is rendered through
    ``tools.import_external_proposal.derive_register_half`` (PE-03), so the
    register has one renderer; the ``declared`` half comes from the operator's
    declaration input for that revision, and is empty while no input exists.

``workspaces/msca_dn/``
    The real project's graph root (spec §6). ``build_snapshot`` resolves its
    nine relative paths against it, so the demo's Tier 3 and Tier 4 records
    are unreachable by construction. It holds the dev-graph directories and the
    ESR intake record; the source index, the document record and the import
    manifest are PE-03's and are written by ``tools/import_external_proposal.py``.

``workspaces/msca_dn/docs/tier4_orchestration_state/dev_graph/intake/<id>.json``
    The intake, written through :func:`runner.dev_graph.record_esr_intake` so
    its immutability rule holds: the same content again is a no-op and a change
    is refused. A changed intake is a new intake id.

Two call bindings, one owner each (spec PE-01)
----------------------------------------------
The intake's ``call_id`` names the call the ESR evaluated, the 2025 DN call.
The baseline's target, ``HORIZON-MSCA-2026-DN-01``, belongs to the profile
(``harness/profiles/msca_dn_2026_default.json``, PE-02), the run label and the
report and never to the intake. This tool carries no copy of it; the test reads
the profile and asserts the two differ, since no engine path reads ``call_id``.

Status of the declared values
-----------------------------
The 2025 call identifier and the submission identifier are operator
declarations with ``Assumed`` status: the sanitised ESR carries neither a call
id nor a proposal number, and the 2025 work programme is not stored (spec §8).
The hashes, page counts and the page-32 DN-type phrase are checked against the
stored files and are ``Confirmed`` by re-derivation in ``tests/test_msca_dn_workspace.py``.
The ESR's content is not copied into Tier 3; it belongs to PE-08's Tier 4 record.

How an operator declares, and how regeneration keeps it (R01)
-------------------------------------------------------------
The register's ``declared`` half is the operator's. It is authored in a durable
input of its own, one file per revision::

    docs/tier3_project_instantiation/source_materials/msca_dn/declarations/<revision_id>.json

Both tools read it, carry its rows into the register unchanged, and never write
it. So a declaration survives every later authoring run, and both ``--check``
commands pass immediately after one. Delete a register and it is rebuilt from
the PDF and that input. No input means no declarations, and the register keeps
the empty declared half it has today. A malformed input is refused and nothing
is written, and so is a declaration the register holds and the input does not —
unless the operator withdrew it by editing the input. The format, the
validation, the withdrawal rule and the missing-input rule are
:mod:`tools.fidelity_declarations`.

Run it from the repository root::

    py -3.10 -m tools.author_msca_dn_workspace            # write
    py -3.10 -m tools.author_msca_dn_workspace --check    # exit 1 if any file would change

Constitutional standing: an authoring tool, not a runtime component. It writes
Tier 3 and workspace artifacts, evaluates no gate and invokes no Claude. It
coins no ``schema_id`` (CLAUDE.md §16.3).
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Sequence

from runner.atomic_write import atomic_write_text, canonical_json_bytes
from runner.dev_graph.builder import SOURCES_REL
from runner.dev_graph.intake import INTAKE_REL, normalise_intake, record_esr_intake
from runner.paths import find_repo_root
from runner.source_index import read_page_text
from tools import fidelity_declarations

# --------------------------------------------------------------------------- #
# Constants: the spec's names
# --------------------------------------------------------------------------- #

SPEC_REL = "plans/msca_dn_pre_evaluation_spec.md"

WORKSPACE_REL = Path("workspaces/msca_dn")
SOURCE_DIR_REL = Path("docs/tier3_project_instantiation/source_materials/msca_dn")
REGISTER_REL = SOURCE_DIR_REL / "fidelity_register.json"
REGISTER_RECORD_TYPE = "fidelity_register"

CANDIDATE_PDF_REL = SOURCE_DIR_REL / "sanitized_proposal_final.pdf"
ESR_PDF_REL = SOURCE_DIR_REL / "MSCA DN ESR.pdf"

INTAKE_ID = "msca-dn-2025-sanitised-v1"
DOCUMENT_ID = "MSCA-DN-2025_sanitised_part_b"
#: The proposal number stays with the original inside the private network; the
#: sanitised ESR does not carry it. A plain identifier is required by the
#: intake schema, so the withholding is stated in the identifier itself.
SUBMISSION_ID = "MSCA-DN-2025-PROPOSAL-NUMBER-WITHHELD"
#: The call the ESR evaluated. Owned by the intake.
HISTORICAL_CALL_ID = "HORIZON-MSCA-2025-DN-01"
#: Where the sanitised copy declares its DN type; checked on that page, not typed.
DN_TYPE_PAGE = 32
DN_TYPE_MARKER = "standard Doctoral Network"

DECLARED_ON = "2026-10-04"
DECLARED_BY = "operator"

#: Dev-graph directories the workspace carries empty until later tickets.
_EMPTY_DEV_GRAPH_DIRS = ("documents", "snapshots", "packages")
_DEV_GRAPH_REL = Path(INTAKE_REL).parent


@dataclass(frozen=True)
class InputSpec:
    """One input of the assessment, as the spec's §1 table names it."""

    role_key: str
    role: str
    path: str
    version: str
    version_markers: tuple[str, ...]


INPUTS: tuple[InputSpec, ...] = (
    InputSpec(
        "candidate",
        "Current assessment artifact: a sanitised derivative of the historical submission, "
        "reflowed from 34 to 84 pages. Not the submitted text.",
        CANDIDATE_PDF_REL.as_posix(),
        "sanitised derivative, 84 pages (reflow of a 34-page original)",
        (DN_TYPE_MARKER,),
    ),
    InputSpec(
        "esr",
        "Historical evaluation: the Evaluation Summary Report of the 2025 submission, "
        "project identifiers generalised.",
        ESR_PDF_REL.as_posix(),
        "ESR, 4 pages",
        (),
    ),
    InputSpec(
        "evaluation_form",
        "Instrument schema, evaluation: scoring authority for the baseline.",
        "docs/tier2a_instrument_schemas/evaluation_forms/msca/ef_he-msca_en.pdf",
        "V2.2, 17.12.2025",
        ("Version 2.2", "17.12.2025"),
    ),
    InputSpec(
        "application_form_submission",
        "Instrument schema, application: the form the 2025 submission was written against. "
        "Recorded for the V5.0/V6.0 equivalence of spec §2.12; not the structural authority.",
        "docs/tier2a_instrument_schemas/application_forms/msca/af_he-msca-dn_en.pdf",
        "V5.0, 29.04.2025 (2025 call)",
        ("V5.0", "29.04.2025", "For the 2025 call"),
    ),
    InputSpec(
        "application_form_baseline",
        "Instrument schema, application: structural authority for the 2026 baseline.",
        "docs/tier2a_instrument_schemas/application_forms/msca/Tpl_Application Form (Part B) (HE MSCA DN).pdf",
        "V6.0, 04.04.2026 (2026 call; footer date, see spec §2.12)",
        ("V6.0", "04.04.2026", "For the 2026 call"),
    ),
    InputSpec(
        "application_form_baseline_rtf",
        "Same V6.0 template as RTF; recorded so a text-level reading has a pinned source.",
        "docs/tier2a_instrument_schemas/application_forms/msca/Tpl_Application Form (Part B) (HE MSCA DN).rtf",
        "V6.0, 04.04.2026 (RTF rendition)",
        (),
    ),
)

_SCHEMA_REF = (
    "No declared schema. .claude/workflows/system_orchestration/artifact_schema_specification.yaml "
    "carries no tier3 schema for a fidelity register, and no schema_id is coined for it "
    "(CLAUDE.md §16.3), as sources.json says of its own shape. The shape is fixed by "
    "tools/author_msca_dn_workspace.py and checked by tests/test_msca_dn_workspace.py."
)


class AuthoringError(RuntimeError):
    """A stored file does not carry what the register must derive from it."""


# --------------------------------------------------------------------------- #
# Derivations from the stored files
# --------------------------------------------------------------------------- #


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pdf_page_count(path: Path) -> int:
    import pymupdf

    doc = pymupdf.open(path)
    try:
        return int(doc.page_count)
    finally:
        doc.close()


def pdf_text(path: Path) -> str:
    """All pages of *path*, each read through :func:`runner.source_index.read_page_text`.

    The single sanctioned page reader, so a marker found here is found by the
    same normalisation the source index verifies against.
    """
    return "\n".join(read_page_text(path, page) for page in range(1, pdf_page_count(path) + 1))


def _input_rows(repo_root: Path, revision: Any = None) -> list[dict[str, Any]]:
    """The register's input table, hashes and page counts derived from disk.

    *revision* (a ``tools.import_external_proposal.Revision``) replaces the
    ``candidate`` row with that revision's PDF, so a revision's register
    describes the file it was derived from and the first register keeps its
    own. ``None`` means the first sanitised derivative, unchanged.
    """
    specs = INPUTS
    if revision is not None:
        specs = tuple(
            InputSpec(
                "candidate", revision.candidate_role, revision.pdf_rel.as_posix(),
                revision.candidate_version, (DN_TYPE_MARKER,),
            )
            if spec.role_key == "candidate" else spec
            for spec in INPUTS
        )
    rows: list[dict[str, Any]] = []
    for spec in specs:
        path = repo_root / spec.path
        if not path.is_file():
            raise AuthoringError(f"input missing: {spec.path}")
        row: dict[str, Any] = {
            "role_key": spec.role_key,
            "role": spec.role,
            "path": spec.path,
            "version": spec.version,
            "version_markers": list(spec.version_markers),
            "sha256": _sha256(path),
            "sha256_status": "Confirmed",
            "sha256_basis": "derived from the stored bytes; re-derived by the test",
        }
        if path.suffix.lower() == ".pdf":
            text = pdf_text(path)
            missing = [m for m in spec.version_markers if m not in text]
            if missing:
                raise AuthoringError(f"{spec.path}: version markers not found in text: {missing}")
            row["pages"] = pdf_page_count(path)
        rows.append(row)
    return rows


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #


def _render_declared_half(
    repo_root: Path, revision: Any, derived: dict[str, Any]
) -> dict[str, Any]:
    """The register's ``declared`` half: the operator's input, or the empty half.

    The rows come from the revision's durable declaration input and are carried
    through unchanged (:mod:`tools.fidelity_declarations`). With no input the
    half is the empty one this tool rendered before R01, byte for byte.
    """
    rows, block = fidelity_declarations.declared_half(
        repo_root,
        revision.revision_id,
        revision.register_rel,
        (row["sub_section_id"] for row in derived["sub_sections"]),
    )
    half: dict[str, Any] = {
        "kind": "declared",
        "fields_per_sub_section": list(fidelity_declarations.REQUIRED_FIELDS),
        "note": (
            "Two independent fields per sub-section: a present but heavily sanitised section is "
            "not an absent one (spec decision 9). Filled by the operator beside PE-03's derived half."
        ),
    }
    # With no input the half keeps the keys it had before R01, in their order,
    # so the committed registers stay byte-identical and the comparison
    # artifacts that recorded their hashes stay replayable.
    if block is not None:
        half[fidelity_declarations.INPUT_BLOCK_KEY] = block
    half[fidelity_declarations.SUB_SECTIONS_KEY] = list(rows)
    return half


def render_register(repo_root: Path, revision: Any = None) -> dict[str, Any]:
    """The fidelity register of *revision*, or of the first sanitised derivative.

    A revision gets its own register file. The first one is never re-rendered
    with a later revision's measurements, because its derived half is the
    evidence for the document record that was imported from it.
    """
    # PE-03 owns the derived half; imported here so the register has one renderer.
    from tools.import_external_proposal import REVISION_ORIGINAL, derive_register_half

    revision = revision if revision is not None else REVISION_ORIGINAL
    is_first = revision.supersedes is None
    derived = derive_register_half(repo_root, revision)
    rows = _input_rows(repo_root, None if is_first else revision)
    by_key = {r["role_key"]: r for r in rows}
    candidate = by_key["candidate"]
    esr = by_key["esr"]
    if candidate["pages"] != revision.expected_pages:
        raise AuthoringError(
            f"candidate: expected the {revision.expected_pages}-page sanitised copy, "
            f"found {candidate['pages']} pages"
        )
    if DN_TYPE_MARKER not in read_page_text(repo_root / revision.pdf_rel, DN_TYPE_PAGE):
        raise AuthoringError(f"candidate: {DN_TYPE_MARKER!r} not found on p. {DN_TYPE_PAGE}")
    declared_half = _render_declared_half(repo_root, revision, derived)
    register: dict[str, Any] = {
        "record_type": REGISTER_RECORD_TYPE,
        "schema_ref": _SCHEMA_REF,
        "artifact_purpose": (
            "The fidelity register of the MSCA-DN pre-evaluation case: what the current assessment "
            "artifact is, how it differs from the historical submission, and how much of that "
            "difference is measured versus declared. Spec decisions 9 and 18. Its provenance "
            "header is referenced by the ESR intake under workspaces/msca_dn/."
        ),
        "spec": SPEC_REL,
        "ticket": "PE-01",
        "provenance": {
            "kind": "declared",
            "declared_by": DECLARED_BY,
            "declared_on": DECLARED_ON,
            "declared_status": "Assumed",
            "status_note": (
                "Operator statements about an original that is not stored here carry Assumed status "
                "(CLAUDE.md §12.2). An item that the authoring tool checks against the stored files "
                "carries its own Confirmed status where it stands. The ESR's content, scores included, "
                "is not recorded here: it belongs to the Tier 4 ESR record of PE-08, which no snapshot "
                "reads (spec decision 12)."
            ),
            "historical_submission": {
                "instrument": "MSCA Doctoral Networks",
                "dn_type": {
                    "value": "standard Doctoral Network, not an Industrial Doctorate and not a Joint Doctorate",
                    "basis": f"the sanitised copy states it on p. {DN_TYPE_PAGE}; the tool checks the phrase on that page",
                    "declared_status": "Confirmed",
                },
                "call_id": {
                    "value": HISTORICAL_CALL_ID,
                    "declared_status": "Assumed",
                    "basis": (
                        "operator declaration. The sanitised ESR names no call and no proposal "
                        "number, and the 2025 work programme is not stored (spec §8)."
                    ),
                    "owner": "the intake record; never the profile, run label or report",
                },
                "submission_id": {
                    "value": SUBMISSION_ID,
                    "declared_status": "Assumed",
                    "basis": "the proposal number stays with the original inside the private network",
                },
            },
            "current_assessment_artifact": {
                "path": candidate["path"],
                "sha256": candidate["sha256"],
                "pages": candidate["pages"],
                "kind": "sanitised derivative of the historical submission",
                "is_submitted_document": False,
                "statement": (
                    "This file is not the text the ESR evaluated. It is a derivative produced by "
                    "sanitisation after evaluation, and no result over it is a result over the submission."
                ),
            },
            "transformation": {
                "declared_status": "Assumed",
                "basis": (
                    "operator declaration at PE-01; the body size, table flattening, figure and "
                    "citation counts are re-checked in the derived half at PE-03"
                ),
                "identifiers": "generalised (project acronym, partner names, people, places)",
                "prose": "some passages omitted or rephrased",
                "figures": "all lost; the copy carries zero images on any page",
                "citations": "all removed; no bracketed numbers, author-year, DOIs, URLs or reference list",
                "reformatting": {
                    "body_point_size": 12,
                    "table_3_1a": "flattened to label-value lines (WP Number:, WP title:, Lead participant)",
                    "tables_3_1b_to_e": "survived as tables",
                    "bullets": "one bullet per line",
                },
                "reflow": {
                    "original_pages": 34,
                    "current_pages": candidate["pages"],
                    "consequence": (
                        "no page-based judgment of length, density or page-limit compliance is "
                        "admissible from this file (spec §2.11)"
                    ),
                },
            },
            "relationship_to_esr": {
                "statement": (
                    "Same underlying project, different assessment text. The ESR scored the original; "
                    "the baseline scores the derivative. A difference from the ESR total is not "
                    "interpretable as model error: it may be changed wording, removed evidence or "
                    "assessor variance (spec §1)."
                ),
                "esr_path": esr["path"],
                "esr_sha256": esr["sha256"],
                "esr_pages": esr["pages"],
            },
            "authoritative_original": {
                "location": "the private network only",
                "stored_here": False,
                "proposal_number": "withheld with the original",
                "consequence": "fidelity against the original is checkable only at PE-09, inside that network",
            },
            "inputs": rows,
        },
        "derived": derived,
        "declared": declared_half,
    }
    if is_first:
        return register
    return _revise_register(repo_root, register, revision, derived)


#: The operator's PE-01 transformation declarations that a revision re-checks
#: against its own bytes. Each names the derived measurement that settles it.
_RECHECKED_DECLARATIONS: tuple[tuple[str, str], ...] = (
    ("figures", "figures"),
    ("citations", "citation_marker_counts"),
    ("body_point_size", "body_point_size"),
    ("table_3_1a", "table_3_1a"),
    ("reflow_page_count", "pages"),
)


def _recheck(derived: dict[str, Any], prior: dict[str, Any]) -> dict[str, Any]:
    """Each carried PE-01 transformation declaration against this revision's measurement.

    ``holds`` is derived from the measurement, never declared. A declaration
    that no longer holds is reported as not holding; it is not rewritten,
    because only the operator may withdraw a declaration (spec decision 9).
    """
    tr = prior
    ps = derived["body_point_size"]
    t31a = derived["table_3_1a"]
    figures = derived["figures"]
    citations = derived["citation_marker_counts"]
    out: dict[str, Any] = {
        "basis": (
            "Every PE-01 declaration that a measurement can settle, re-run against this revision's "
            "bytes by tools/import_external_proposal.derive_register_half. 'holds' is derived. A "
            "declaration that does not hold is reported, not rewritten: withdrawing one is the "
            "operator's act."
        ),
        "figures": {
            "declaration": tr["figures"],
            "measured": figures,
            "holds": figures["images_on_any_page"] == 0,
        },
        "citations": {
            "declaration": tr["citations"],
            "measured": citations,
            "holds": set(citations.values()) == {0},
        },
        "body_point_size": {
            "declaration": tr["reformatting"]["body_point_size"],
            "measured_distribution": ps["distribution"],
            "measured_other_size_character_sets": ps["other_sizes_character_sets"],
            "holds": ps["other_sizes_are_bullets_and_spaces_only"],
            "consequence_if_not": (
                "A point size other than the declared body size carries prose, not only bullet "
                "glyphs. The declaration 'body 12 pt' is then incomplete for this revision: part of "
                "the text is set smaller. Recorded here and in the derived half; not repaired."
            ),
        },
        "table_3_1a": {
            "declaration": tr["reformatting"]["table_3_1a"],
            "measured_label_block_counts": t31a["label_block_counts"],
            "measured_wp_number_blocks": t31a["wp_number_blocks"],
            "holds": t31a["flattened_to_label_value_blocks"],
            "note": (
                "The flattening holds while each named label opens at least one prose block. The "
                "per-label counts are recorded as measured: a label that falls short of the work "
                "package count did not open its own block on every work package."
            ),
        },
        "reflow_page_count": {
            "declaration": tr["reflow"]["current_pages"],
            "measured": derived["pages"],
            "holds": tr["reflow"]["current_pages"] == derived["pages"],
        },
    }
    out["declarations_that_no_longer_hold"] = sorted(
        name for name, _ in _RECHECKED_DECLARATIONS if out[name]["holds"] is False
    )
    return out


def _revise_register(
    repo_root: Path, register: dict[str, Any], revision: Any, derived: dict[str, Any]
) -> dict[str, Any]:
    """The register of a superseding revision: the PE-01 header, re-checked.

    Nothing is carried forward silently. Every declaration a measurement can
    settle is re-run against this revision's bytes and reported with its
    verdict, and the register says in its own header that it describes a
    revised derivative rather than the original submission.
    """
    from tools.import_external_proposal import (
        extraction_limitations,
        manifest_rel,
        revision_by_id,
    )

    predecessor = revision_by_id(revision.supersedes)
    prov = register["provenance"]
    prior = dict(prov["transformation"])
    prov["current_assessment_artifact"]["kind"] = (
        "revised sanitised derivative of the historical submission"
    )
    prov["current_assessment_artifact"]["statement"] = (
        "This file is not the text the ESR evaluated, and it is not the first sanitised derivative "
        "either. It is a later sanitised derivative of the same historical submission, and no "
        "result over it is a result over the submission."
    )
    prov["transformation"]["basis"] = (
        "the PE-01 operator declarations, carried to this revision and re-checked against its own "
        "bytes under 'rechecked_for_this_revision'; the declarations themselves are unchanged"
    )
    prov["transformation"]["rechecked_for_this_revision"] = _recheck(derived, prior)
    prov["revision"] = {
        "revision_id": revision.revision_id,
        "summary": revision.summary,
        "declared_status": "Confirmed",
        "basis": "derived: the page-by-page comparison in the import manifest",
        "supersedes": {
            "revision_id": predecessor.revision_id,
            "path": predecessor.pdf_rel.as_posix(),
            "sha256": hashlib.sha256((repo_root / predecessor.pdf_rel).read_bytes()).hexdigest(),
            "fidelity_register": predecessor.register_rel.as_posix(),
            "import_manifest": manifest_rel(predecessor).as_posix(),
            "retained": (
                "The predecessor PDF, its register, its import manifest, its page texts and its "
                "document record are retained unchanged. This register does not replace that one."
            ),
        },
        "same_historical_submission": (
            "Both revisions are sanitised derivatives of the one 2025 submission. The intake, the "
            "document id and the call binding are unchanged; only the derivative's bytes differ."
        ),
    }
    prov["known_extraction_limitations"] = extraction_limitations(repo_root, revision)
    register["ticket"] = "PE-01 header, re-checked for this revision at PE-03"
    return register


def intake_fields(repo_root: Path) -> dict[str, Any]:
    """The intake's declared fields, in the writer's keyword shape."""
    return {
        "intake_id": INTAKE_ID,
        "document_id": DOCUMENT_ID,
        "submission_id": SUBMISSION_ID,
        "call_id": HISTORICAL_CALL_ID,
        "prior_submission": True,
        "esr_availability": "available",
        "permitted_purpose": "blind_pre_evaluation",
        "esr_reference": _esr_reference(repo_root, REGISTER_REL.as_posix()),
    }


def render_intake(repo_root: Path) -> dict[str, Any]:
    return normalise_intake(intake_fields(repo_root), f"intake {INTAKE_ID}").to_dict()


def _esr_reference(repo_root: Path, register_rel: str) -> str:
    """One string binding the ESR by path and hash and naming the register.

    ``EsrIntake`` has one free-text field, so the reference to the fidelity
    register's provenance header (spec decision 18) travels in it.
    """
    esr_hash = _sha256(repo_root / ESR_PDF_REL)
    return (
        f"{ESR_PDF_REL.as_posix()} sha256:{esr_hash}; "
        f"sanitisation provenance: {register_rel}#provenance"
    )


def render_readme() -> str:
    return (
        "# MSCA-DN pre-evaluation graph root\n"
        "\n"
        f"This directory is the `--graph-root` of the MSCA-DN pre-evaluation case (`{SPEC_REL}`, §6).\n"
        "`build_snapshot` resolves its Tier 3 and Tier 4 relative paths against it, so nothing under the\n"
        "repository's own `docs/` is reachable from here. The demo instance keeps its records there.\n"
        "\n"
        "What lives here:\n"
        "\n"
        f"- `{SOURCES_REL.as_posix()}`: the source index, one source per page of the sanitised copy\n"
        "  (`SRC-DN-P01` to `SRC-DN-P84`), each holding that page's text, written by PE-03.\n"
        f"- `{_DEV_GRAPH_REL.as_posix()}/intake/{INTAKE_ID}.json`: the ESR intake, whose `call_id` is the\n"
        "  call the ESR evaluated.\n"
        "- The baseline's target call belongs to the profile, the run label and the report, never to the intake.\n"
        f"- `{_DEV_GRAPH_REL.as_posix()}/documents/`: the imported document record (schema v2), written by PE-03.\n"
        f"- `{_DEV_GRAPH_REL.as_posix()}/imports/`: the import manifest naming the extractor, normalisation,\n"
        "  table-rendering and claim-extraction versions, written by PE-03.\n"
        f"- `{_DEV_GRAPH_REL.as_posix()}/snapshots/`, `packages/`: empty until PE-06.\n"
        "\n"
        "What does not live here:\n"
        "\n"
        f"- The two PDFs and the fidelity register, under `{SOURCE_DIR_REL.as_posix()}/`.\n"
        "- The ESR record, under `docs/tier4_orchestration_state/msca_dn/esr/`, which no snapshot ever reads.\n"
        "\n"
        "The assessment artifact under the register is a sanitised derivative of the historical submission.\n"
        "No result over it is a result over that submission.\n"
        "\n"
        "Authored by `py -3.10 -m tools.author_msca_dn_workspace` (skeleton, intake, register) and\n"
        "`py -3.10 -m tools.import_external_proposal` (sources, document record, manifest, the register's\n"
        "derived half). Each tool's `--check` exits 1 if any file it owns would change.\n"
    )


def render_all(repo_root: Path) -> dict[str, bytes]:
    """Every file PE-01 authors, as the bytes it should hold on disk."""
    files: dict[str, bytes] = {
        REGISTER_REL.as_posix(): canonical_json_bytes(render_register(repo_root)),
        (WORKSPACE_REL / "README.md").as_posix(): render_readme().encode("utf-8"),
        (WORKSPACE_REL / INTAKE_REL / f"{INTAKE_ID}.json").as_posix(): canonical_json_bytes(render_intake(repo_root)),
    }
    for name in _EMPTY_DEV_GRAPH_DIRS:
        files[(WORKSPACE_REL / _DEV_GRAPH_REL / name / ".gitkeep").as_posix()] = b""
    return files


# --------------------------------------------------------------------------- #
# Writing and checking
# --------------------------------------------------------------------------- #


def check(repo_root: Path) -> list[str]:
    """Relative paths whose bytes differ from the rendering, or are absent.

    Read-only, and it may refuse instead of returning: a malformed declaration
    input or a declaration the register holds alone is a refusal, not a
    staleness entry (:mod:`tools.fidelity_declarations`).
    """
    return [
        rel
        for rel, data in render_all(repo_root).items()
        if not (repo_root / rel).is_file() or (repo_root / rel).read_bytes() != data
    ]


def author(repo_root: Path) -> list[str]:
    """Write every file; return the relative paths that changed.

    The declaration input of the register this tool writes is read before
    anything is written, so a malformed one is refused with no file touched.
    """
    from tools.import_external_proposal import REVISION_ORIGINAL

    # Only the first revision's register: the later revisions' registers are
    # the importer's, and that tool validates its own.
    fidelity_declarations.validate_inputs(
        repo_root, [(REVISION_ORIGINAL.revision_id, REVISION_ORIGINAL.register_rel)]
    )
    changed: list[str] = []
    intake_rel = (WORKSPACE_REL / INTAKE_REL / f"{INTAKE_ID}.json").as_posix()
    for rel, data in render_all(repo_root).items():
        target = repo_root / rel
        if target.is_file() and target.read_bytes() == data:
            continue
        if rel == intake_rel:
            # The engine's writer owns immutability: a changed intake is refused.
            record_esr_intake(repo_root / WORKSPACE_REL, **intake_fields(repo_root))
        elif data == b"":
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"")
        else:
            atomic_write_text(data.decode("utf-8"), target)
        changed.append(rel)
    return changed


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="exit 1 if any authored file would change")
    parser.add_argument("--repo-root", type=Path, default=None)
    args = parser.parse_args(argv)
    repo_root = args.repo_root or find_repo_root()
    try:
        if args.check:
            stale = check(repo_root)
            for rel in stale:
                print(f"would change: {rel}")
            print("up to date" if not stale else f"{len(stale)} file(s) would change")
            return 1 if stale else 0
        changed = author(repo_root)
        for rel in changed:
            print(f"wrote: {rel}")
        print("no change" if not changed else f"{len(changed)} file(s) written")
        return 0
    except (AuthoringError, fidelity_declarations.FidelityDeclarationsError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
