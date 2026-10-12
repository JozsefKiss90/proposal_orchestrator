"""Dry-import a document and write its provenance records (V08).

V08 of ``plans/msca_dn_historical_validation_tickets.md``: the review half of
F02 of the readiness audit. Before the official original is imported or
assessed, an operator measures it against the PDF in front of them. This tool
is that run.

What it does
------------
It measures the PDF through :mod:`runner.dry_import` — the page count, the
per-page accounting, every table and its header, the graphical census, the
candidate section headings and the extraction limitations — and writes six
files into a directory the operator names:

* ``dry_import_inventory.json`` — the measurement (criterion 1).
* ``reconciliation_worksheet.md`` — the same measurement as a worksheet, so the
  reconciliation is done against a page-by-page list rather than against JSON.
* ``<intake_id>.json`` — the document's own ESR intake record (criterion 2).
* ``original_document_provenance.json`` — which file, which bytes, which
  environment, and that none of it is stored in the repository (criterion 2).
* ``extraction_fidelity_acceptance.json`` — the seven classes of evidence the
  operator reconciles, every one unreconciled (criterion 3).
* ``unresolved_extraction_limitations.json`` — what the extraction loses,
  recorded before any assessment reads the text (criterion 5).

What it refuses
---------------
* **A hash the bytes do not match.** ``--expect-sha256`` is the hash the
  operator took from the authoritative source. The tool refuses unless the file
  it was given hashes to it, which is what makes the recorded hash an
  authenticated input hash rather than a hash of whatever was lying around.
* **A path inside this repository**, for a document declared as the submitted
  text. Neither the PDF nor the output may be here (criterion 6). The original
  and every text derived from it stay in the private network.
* **A document whose identity is undeclared.** ``require_dry_importable()``
  names the missing fields. A dry import needs no page map — that is what it
  produces — but it does need to know which document it is measuring.

It writes no graph state: no document record, no source index, no snapshot and
no intake directory. Recording the intake inside the private graph root is a
separate operator step through
:func:`runner.dev_graph.intake.record_esr_intake`, and the provenance record
says so.

Run it from the repository root, with every path pointing outside it::

    py -3.10 -m tools.dry_import_original \\
        --pdf <private>/part_b_as_submitted.pdf \\
        --expect-sha256 <hash from the authoritative source> \\
        --out <private>/v08_dry_import \\
        --submission-id <the proposal number> \\
        --call-id <the 2025 call id>

Once the operator has filled in the acceptance record, its admissibility is a
command of its own, which measures nothing and writes nothing::

    py -3.10 -m tools.dry_import_original --check-acceptance <private>/.../acceptance.json

``plans/msca_dn_v08_original_dry_import_procedure.md`` is the operator
procedure. This tool has not been run against the real original in this
repository, and the ticket leaves that run to the operator.

Constitutional standing: an authoring tool, not a runtime component. It
evaluates no gate, invokes no Claude, coins no ``schema_id`` beyond the intake
record's own, and declares no project fact it was not given (CLAUDE.md §13.3,
§16.3).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Sequence

from runner.atomic_write import atomic_write_text, canonical_json_bytes
from runner.dev_graph.intake import (
    ESR_AVAILABILITY,
    INTAKE_SCHEMA_ID,
    PERMITTED_PURPOSES,
    normalise_intake,
)
from runner.dev_graph.schema import DevGraphError
from runner.dry_import import (
    ACCEPTANCE_ITEMS,
    ACCEPTANCE_RECORD_TYPE,
    GRAPHICAL_PROOF_STATEMENT,
    DryImportRefused,
    build_acceptance,
    build_unresolved_limitations,
    check_acceptance,
    measure,
)
from tools.import_external_proposal import (
    DOCUMENTS,
    OFFICIAL_ORIGINAL,
    DocumentConfig,
    ImportRefused,
    document_by_id,
)

#: File names the dry import writes. Fixed, so the provenance record can bind
#: each by hash and the procedure can name them.
INVENTORY_FILE = "dry_import_inventory.json"
PROVENANCE_FILE = "original_document_provenance.json"
ACCEPTANCE_FILE = "extraction_fidelity_acceptance.json"
LIMITATIONS_FILE = "unresolved_extraction_limitations.json"
WORKSHEET_FILE = "reconciliation_worksheet.md"

PROVENANCE_RECORD_TYPE = "original_document_provenance"

PROCEDURE_REL = "plans/msca_dn_v08_original_dry_import_procedure.md"

_SHA256 = re.compile(r"^[0-9a-f]{64}$")

_SCHEMA_REF = (
    "No declared schema. .claude/workflows/system_orchestration/artifact_schema_specification.yaml "
    "carries no schema for a dry-import inventory or a document provenance record, and no "
    "schema_id is coined for either (CLAUDE.md §16.3). The shapes are fixed by "
    "runner/dry_import.py and tools/dry_import_original.py and checked by "
    "tests/runner/test_dry_import.py and tests/test_msca_dn_dry_import.py. The intake record is "
    f"the one record here that has a schema: {INTAKE_SCHEMA_ID}."
)


@dataclass(frozen=True)
class Declarations:
    """What the operator declares about the submission, and nothing else.

    None of these is derivable from the PDF. The proposal number lives with the
    original, the call id is the operator's (and unresolved until V09), and ESR
    availability is declared and never inferred, so each arrives as an argument
    rather than a default.
    """

    submission_id: str
    call_id: str
    permitted_purpose: str = "blind_pre_evaluation"
    prior_submission: bool = False
    esr_availability: str = "unknown"
    esr_reference: Optional[str] = None


# --------------------------------------------------------------------------- #
# Refusals
# --------------------------------------------------------------------------- #


#: The repository this tool is part of, resolved from the module's own location
#: rather than from the working directory or an argument.
#:
#: Criterion 6 is about *this* repository, so what counts as inside it cannot be
#: something a caller supplies. A ``--repo-root`` flag would let an operator
#: point the check at an empty directory, write the derived text here anyway,
#: and have the provenance record state that nothing was stored here. The tool
#: also has to run from the private network, where there is no repository to
#: walk up to, so the working directory is not the answer either.
THIS_REPOSITORY: Path = Path(__file__).resolve().parents[1]


def inside_this_repository(path: Path) -> bool:
    """Whether *path* resolves inside :data:`THIS_REPOSITORY`. Measured."""
    resolved = Path(path).expanduser().resolve()
    return resolved == THIS_REPOSITORY or THIS_REPOSITORY in resolved.parents


def _require_outside_this_repository(path: Path, what: str) -> None:
    """Refuse *path* if it resolves inside this repository (criterion 6)."""
    if inside_this_repository(path):
        raise DryImportRefused(
            f"{what} {Path(path).name!r} resolves inside this repository "
            f"({THIS_REPOSITORY.name}). The submitted text and every text derived from it stay in "
            f"the private network; neither the PDF nor the dry import's output may be written "
            f"here, and no argument moves where here is."
        )


def _authenticated_sha256(pdf: Path, expected: str) -> str:
    """The hash of *pdf*, refused unless it is the one the operator declared."""
    if not _SHA256.match(expected or ""):
        raise DryImportRefused(
            f"--expect-sha256 {expected!r} is not a sha256: 64 lower-case hex digits are "
            f"required. The hash comes from the authoritative source, not from this file."
        )
    measured = hashlib.sha256(Path(pdf).read_bytes()).hexdigest()
    if measured != expected:
        raise DryImportRefused(
            f"{Path(pdf).name} hashes to {measured}, and the operator declared {expected}. This "
            f"is not the authenticated file; nothing was written."
        )
    return measured


# --------------------------------------------------------------------------- #
# The records
# --------------------------------------------------------------------------- #


def build_intake(config: DocumentConfig, declarations: Declarations) -> dict[str, Any]:
    """The document's own ESR intake record, validated against its schema.

    Separate from the provenance record below. This one holds what is known
    about the *submission*: its id, its call, whether a prior submission exists
    and whether an ESR may be read. It holds no hash and no measurement. The
    sanitised copy's intake carried its sanitisation provenance inside
    ``esr_reference``, which conflated the two; this pair does not.
    """
    config.require_dry_importable()
    raw = {
        "intake_id": config.require_intake_id(),
        "document_id": config.document_id,
        "submission_id": declarations.submission_id,
        "call_id": declarations.call_id,
        "prior_submission": declarations.prior_submission,
        "esr_availability": declarations.esr_availability,
        "permitted_purpose": declarations.permitted_purpose,
        "esr_reference": declarations.esr_reference,
    }
    return normalise_intake(raw, f"intake {raw['intake_id']}").to_dict()


def build_provenance(
    config: DocumentConfig,
    *,
    pdf: Path,
    inventory: dict[str, Any],
    declared_sha256: str,
    bound: dict[str, tuple[str, dict[str, Any]]],
    pdf_in_repository: bool,
    output_in_repository: bool,
) -> dict[str, Any]:
    """The document's own provenance record: which file, which bytes, which run.

    *bound* maps a key to ``(file name, record)``; each is bound by its hash, so
    a provenance record and the records it points at cannot drift apart
    silently.

    The two storage flags are measured from the paths this run was given, not
    declared from the document's role. For the submitted text both are false
    because the run refuses otherwise, and for any other document they say
    where its bytes actually are.
    """
    config.require_dry_importable()
    return {
        "record_type": PROVENANCE_RECORD_TYPE,
        "schema_ref": _SCHEMA_REF,
        "purpose": (
            "The provenance of one document: the file that was measured, the bytes it "
            "authenticated as, the environment that read it, and where it is kept. Written by a "
            "dry import, before any import and before any assessment."
        ),
        "separation": (
            "Two records, deliberately. The intake record holds what is known about the "
            "submission — its id, its call, ESR availability and the purpose an ESR may serve. "
            "This record holds the document's own provenance. The sanitised copy's intake "
            "carried its sanitisation provenance inside esr_reference, so one field answered two "
            "questions; here neither record answers the other's."
        ),
        "document": {
            "config_id": config.config_id,
            "document_id": config.document_id,
            "title": config.title,
            "role": config.role,
            "short_name": config.short_name,
            "is_submitted_document": config.is_submitted_document,
            "page_statement": config.page_statement,
            "declared_status": config.declared_status,
            "status_note": config.status_note,
        },
        "intake": {
            "intake_id": config.require_intake_id(),
            "record_file": f"{config.require_intake_id()}.json",
            "schema_id": INTAKE_SCHEMA_ID,
            "recorded_in_a_graph_root": False,
            "how_to_record": (
                "runner.dev_graph.intake.record_esr_intake, run inside the private graph root. "
                "The dry import writes the record as a file and records nothing in a graph, so "
                "nothing here can be read as an imported document."
            ),
        },
        "input": {
            "file_name": Path(pdf).name,
            "path_recorded": False,
            "path_basis": (
                "the file name alone. The directory is inside the private network, and a record "
                "that might later be quoted outside it carries no path into it."
            ),
            "sha256": inventory["sha256"],
            "sha256_declared_by_operator": declared_sha256,
            "authenticated": True,
            "authentication": (
                "The operator declared the hash from the authoritative source, and this tool "
                "refuses unless the file it was given hashes to it. A hash the tool computed "
                "from an unauthenticated file would say only that some file was read."
            ),
            "bytes": inventory["bytes"],
            "pages": inventory["pages"],
            "pages_basis": inventory["page_count_basis"],
        },
        "storage": {
            "pdf_stored_in_this_repository": pdf_in_repository,
            "derived_text_stored_in_this_repository": output_in_repository,
            "basis": (
                "measured: both paths this run was given were resolved against the repository "
                "root. For the submitted text the run refuses either path inside it."
            ),
            "location": (
                "outside this repository; for the submitted text, the private network only"
                if not pdf_in_repository
                else "inside this repository"
            ),
            "consequence": (
                "Fidelity against this document is checkable only where its bytes are. No page "
                "text, no span and no extracted sub-section of it reaches this repository "
                "through a dry import, so no artifact here can be replayed against it."
                if not pdf_in_repository
                else "The bytes are in this repository, so an artifact here can be replayed "
                "against them."
            ),
        },
        "page_map": {
            "declared": False,
            "declared_from": config.page_map_declared_from,
            "heading_candidates": inventory["section_map"]["candidates"],
            "consequence": (
                "The document cannot be imported until a page map is declared from this "
                "reconciliation. tools/import_external_proposal.py refuses it and names the "
                "fields that are missing."
            ),
        },
        "graphical_evidence": {
            "images_on_any_page": inventory["figures"]["images_on_any_page"],
            "vector_drawings": inventory["figures"]["vector_drawings"],
            "annotations": inventory["figures"]["annotations"],
            "embedded_files": inventory["figures"]["embedded_files"],
            "not_proof_of_preservation": GRAPHICAL_PROOF_STATEMENT,
        },
        "extraction_environment": inventory["extraction_environment"],
        "versions": inventory["versions"],
        "reader_caveat": {config.reader_caveat_key: config.reader_caveat},
        "procedure": PROCEDURE_REL,
        **{
            key: {
                "record_file": name,
                "record_type": record.get("record_type"),
                "sha256": hashlib.sha256(canonical_json_bytes(record)).hexdigest(),
                **(
                    {"complete": record["complete"]}
                    if "complete" in record
                    else {}
                ),
                **({"resolved": record["resolved"]} if "resolved" in record else {}),
            }
            for key, (name, record) in bound.items()
        },
    }


# --------------------------------------------------------------------------- #
# The worksheet
# --------------------------------------------------------------------------- #


def _cell(text: Any, limit: int) -> str:
    """*text* as one markdown table cell: whitespace collapsed, pipes escaped.

    A PDF cell's text can carry a newline, and a newline inside a markdown cell
    breaks the row it is in.
    """
    flat = re.sub(r"\s+", " ", str(text)).strip().replace("|", "\\|")
    return flat if len(flat) <= limit else flat[: limit - 1] + "…"


def _count(n: int, noun: str) -> str:
    """``1 page``, ``2 pages``. The worksheet is read, so it reads."""
    return f"{n} {noun}" if n == 1 else f"{n} {noun}s"


def render_worksheet(config: DocumentConfig, inventory: dict[str, Any]) -> str:
    """The inventory as a worksheet, for reconciling against the PDF.

    The operator reads this beside the document. Every number is the
    measurement's; every blank is theirs.
    """
    lines: list[str] = [
        f"# Dry-import reconciliation worksheet — {config.title}",
        "",
        f"Document: `{config.config_id}` ({config.short_name}).",
        f"Measured: {_count(inventory['pages'], 'page')}, "
        f"sha256 `{inventory['sha256'][:12]}…`.",
        f"Procedure: `{PROCEDURE_REL}`.",
        "",
        "Reconcile every row below against the PDF. A row nobody checked stays unchecked.",
        "",
        "## 1. Pages",
        "",
        "| Page | Characters | Blocks | Tables | Images | Vector drawings | Loss | Reconciled |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in inventory["per_page"]:
        lines.append(
            f"| {row['page']} | {row['nonws_characters']} | {row['blocks']} | "
            f"{row['tables']} | {row['images']} | {row['drawings']} | {row['loss']} |  |"
        )
    lines += [
        "",
        "## 2. Candidate section headings",
        "",
        "No page map is declared. Each row is a block that could open a sub-section; the page map",
        "is declared from what this reconciliation establishes.",
        "",
        "| Marker | Page | Heading text | Is a sub-section opening |",
        "|---|---|---|---|",
    ]
    for candidate in inventory["heading_candidates"]:
        text = _cell(candidate["text"], 90)
        lines.append(f"| `{candidate['marker']}` | {candidate['page']} | {text} |  |")
    lines += [
        "",
        "## 3. Tables",
        "",
        f"{_count(inventory['tables']['count'], 'table')}, "
        f"{_count(inventory['tables']['rows_rendered'], 'row')} rendered, "
        f"{inventory['tables']['rows_parsed']} parsed.",
        "",
        "| Page | Index | Rows | Columns | Header row | Header reconciled |",
        "|---|---|---|---|---|---|",
    ]
    for table in inventory["tables"]["per_table"]:
        header = _cell(" · ".join(str(cell) for cell in table["header"]), 70)
        lines.append(
            f"| {table['page']} | {table['index']} | {table['rows']} | {table['cols']} | "
            f"{header} |  |"
        )
    figures = inventory["figures"]
    lines += [
        "",
        "## 4. Graphical evidence",
        "",
        f"- Embedded images: **{figures['images_on_any_page']}** "
        f"(pages {figures['pages_with_images'] or 'none'})",
        f"- Vector drawings: **{figures['vector_drawings']}** "
        f"(pages {figures['pages_with_vector_drawings'] or 'none'})",
        f"- Annotations: {figures['annotations']}; embedded files: {figures['embedded_files']}",
        f"- Character accounting: "
        f"{inventory['character_accounting']['total_page_characters']} page characters, "
        f"{inventory['character_accounting']['total_accounted']} accounted, "
        f"{len(inventory['character_accounting']['pages_with_loss'])} page(s) with a loss",
        "",
        f"**Not proof.** {GRAPHICAL_PROOF_STATEMENT}",
        "",
        "## 5. Fidelity acceptance",
        "",
        "One row per class of evidence. Fill in a verdict, a basis and your name in",
        f"`{ACCEPTANCE_FILE}`; a `preserved` verdict may not rest on a measurement.",
        "",
        "| Item | What must be reconciled | Verdict |",
        "|---|---|---|",
    ]
    for spec in ACCEPTANCE_ITEMS:
        lines.append(f"| `{spec.item}` | {spec.what_must_be_reconciled} | unreconciled |")
    lines += [
        "",
        "## 6. Unresolved extraction limitations",
        "",
        f"Recorded in `{LIMITATIONS_FILE}`, before any assessment reads this text. None of them",
        "is repaired by being listed.",
        "",
    ]
    return "\n".join(lines) + "\n"


def check_filled_acceptance(path: Path) -> list[dict[str, str]]:
    """Findings against the acceptance record at *path*, or refuse.

    The operator fills the record in by hand, so the admissibility rule needs a
    command of its own. A rule reachable only by pasting a Python expression is
    a rule nobody runs.
    """
    path = Path(path)
    if not path.is_file():
        raise DryImportRefused(f"{path.name} is not a file, so there is no record to check")
    try:
        record = json.loads(path.read_text(encoding="utf-8-sig"))
    except ValueError as exc:
        raise DryImportRefused(f"{path.name}: unreadable JSON: {exc}") from exc
    if not isinstance(record, dict) or record.get("record_type") != ACCEPTANCE_RECORD_TYPE:
        raise DryImportRefused(
            f"{path.name} is not a {ACCEPTANCE_RECORD_TYPE} record; "
            f"its record_type is {record.get('record_type') if isinstance(record, dict) else None!r}"
        )
    return check_acceptance(record)


# --------------------------------------------------------------------------- #
# The run
# --------------------------------------------------------------------------- #


def dry_import(
    config: DocumentConfig,
    *,
    pdf: Path,
    out_dir: Path,
    expected_sha256: str,
    declarations: Optional[Declarations] = None,
    inventory_only: bool = False,
) -> list[str]:
    """Measure *pdf* and write the records into *out_dir*; return the names.

    Nothing is written until every refusal has passed, so a hash mismatch or a
    path inside this repository leaves the output directory as it was.
    """
    config.require_dry_importable()
    if config.is_submitted_document:
        _require_outside_this_repository(pdf, "the PDF")
        _require_outside_this_repository(out_dir, "the output directory")
    pdf = Path(pdf)
    if not pdf.is_file():
        raise DryImportRefused(f"{pdf.name} is not a file, so there is nothing to measure")
    declared = _authenticated_sha256(pdf, expected_sha256)
    if not inventory_only and declarations is None:
        raise DryImportRefused(
            "the intake record needs a submission id and a call id; neither is derivable from "
            "the PDF and neither is defaulted. Pass declarations, or ask for the inventory alone."
        )
    inventory = measure(pdf)
    files: dict[str, Any] = {INVENTORY_FILE: inventory}
    if declarations is not None and not inventory_only:
        acceptance = build_acceptance(inventory)
        limitations = build_unresolved_limitations(inventory)
        findings = check_acceptance(acceptance)
        if findings:  # pragma: no cover - guards the catalogue against itself
            raise DryImportRefused(
                f"the acceptance record this tool just built is not admissible: {findings}"
            )
        files[f"{config.require_intake_id()}.json"] = build_intake(config, declarations)
        files[ACCEPTANCE_FILE] = acceptance
        files[LIMITATIONS_FILE] = limitations
        files[PROVENANCE_FILE] = build_provenance(
            config,
            pdf=pdf,
            inventory=inventory,
            declared_sha256=declared,
            bound={
                "dry_import": (INVENTORY_FILE, inventory),
                "acceptance": (ACCEPTANCE_FILE, acceptance),
                "limitations": (LIMITATIONS_FILE, limitations),
            },
            pdf_in_repository=inside_this_repository(pdf),
            output_in_repository=inside_this_repository(out_dir),
        )
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    for name, record in files.items():
        atomic_write_text(
            canonical_json_bytes(record).decode("utf-8"), out_dir / name
        )
        written.append(name)
    atomic_write_text(render_worksheet(config, inventory), out_dir / WORKSHEET_FILE)
    written.append(WORKSHEET_FILE)
    return written


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pdf", type=Path, default=None, help="the document to measure")
    parser.add_argument(
        "--expect-sha256",
        default=None,
        help="the hash of the authoritative file; the run refuses unless the PDF matches it",
    )
    parser.add_argument(
        "--out", type=Path, default=None, help="directory the records are written to"
    )
    parser.add_argument(
        "--check-acceptance",
        type=Path,
        default=None,
        help=(
            "check a filled-in fidelity acceptance record and exit; prints every finding and "
            "exits 1 if there is one. Measures nothing and writes nothing."
        ),
    )
    parser.add_argument(
        "--document",
        default=OFFICIAL_ORIGINAL.config_id,
        choices=[doc.config_id for doc in DOCUMENTS],
        help="which document is being measured",
    )
    parser.add_argument(
        "--submission-id",
        default=None,
        help="operator declaration: the submission's own identifier, for the intake record",
    )
    parser.add_argument(
        "--call-id",
        default=None,
        help="operator declaration: the call the submission was made to",
    )
    parser.add_argument(
        "--permitted-purpose",
        default="blind_pre_evaluation",
        choices=sorted(PERMITTED_PURPOSES),
        help="operator declaration: what an ESR of this submission may be read for",
    )
    parser.add_argument(
        "--prior-submission",
        action="store_true",
        help="operator declaration: a prior submission of this proposal exists",
    )
    parser.add_argument(
        "--esr-availability",
        default="unknown",
        choices=sorted(ESR_AVAILABILITY),
        help="operator declaration, never inferred; 'available' needs --esr-reference",
    )
    parser.add_argument(
        "--esr-reference",
        default=None,
        help="what binds the ESR, required by and only by --esr-availability available",
    )
    parser.add_argument(
        "--inventory-only",
        action="store_true",
        help="write the inventory and the worksheet alone, and no provenance record",
    )
    args = parser.parse_args(argv)
    try:
        if args.check_acceptance is not None:
            findings = check_filled_acceptance(args.check_acceptance)
            for found in findings:
                print(f"{found['code']}: {found['item']}: {found['message']}")
            print(
                "admissible as it stands"
                if not findings
                else f"{len(findings)} finding(s); the record is not admissible"
            )
            return 1 if findings else 0
        missing = [
            name
            for name, value in (
                ("--pdf", args.pdf),
                ("--expect-sha256", args.expect_sha256),
                ("--out", args.out),
            )
            if value is None
        ]
        if missing:
            raise DryImportRefused(f"{', '.join(missing)} required to measure a document")
        config = document_by_id(args.document)
        declarations: Optional[Declarations] = None
        if not args.inventory_only:
            if not args.submission_id or not args.call_id:
                raise DryImportRefused(
                    "--submission-id and --call-id are required for the intake record; neither "
                    "is derivable from the PDF. Use --inventory-only to measure without one."
                )
            declarations = Declarations(
                submission_id=args.submission_id,
                call_id=args.call_id,
                permitted_purpose=args.permitted_purpose,
                prior_submission=args.prior_submission,
                esr_availability=args.esr_availability,
                esr_reference=args.esr_reference,
            )
        written = dry_import(
            config,
            pdf=args.pdf,
            out_dir=args.out,
            expected_sha256=args.expect_sha256,
            declarations=declarations,
            inventory_only=args.inventory_only,
        )
    except (DryImportRefused, ImportRefused, DevGraphError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1
    for name in written:
        print(f"wrote: {name}")
    print(f"{len(written)} file(s) written to {args.out}")
    print(
        "Reconcile the worksheet against the PDF, then fill in "
        f"{ACCEPTANCE_FILE}. Nothing here is an import: no graph state was written."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
