"""Author the submitted original's private graph root and its register (V17, V18).

Two gaps the PE-09 runbook listed as blocking stage A step 1, and this module
closes both:

**The private graph root.** ``tools/author_msca_dn_workspace.py`` authors the
sanitised copy's graph root under ``workspaces/msca_dn/``. The submitted
original cannot have one there: its page records, its registers and its spans
are the submitted text, and V08 criterion 6 keeps them out of this repository.
So this tool authors the same skeleton — README, intake record, the dev-graph
directories the importer writes into — under a private root the operator names,
and refuses any root that resolves inside this repository.

**The register of a submitted document.** The copy's register header declares a
sanitisation, a transformation and a reflow. Those are the copy's facts, so
``render_register`` refuses the submitted text rather than labelling the
original with them. :func:`render_submitted_register` is the original's own
renderer, and the one difference that matters is what the two registers are
evidence *of*:

* the copy's declared half answers how a sub-section was transformed, and its
  fidelity to the submitted original is Unresolved in this repository (R04);
* this one answers what the **extraction** of the submitted file carries, which
  is a question the operator settles page by page against the PDF (V08).

Which is why this register refuses to render until the V08 fidelity acceptance
record is admissible and complete. The alternative is a register that asserts
a document's fidelity on a measurement that is equally true of a document whose
figures are gone, which is the one thing V08 exists to prevent.

What is declared, and where it comes from
-----------------------------------------
Nothing here is typed that a file could supply. The operator's declarations
arrive in the private configuration input (:mod:`runner.original_configuration`,
V17): the page map, the page count, the body point size, the work-package
layout, the graph root, and the paths of the V08 records. The hashes, page
counts and the network-type phrase are derived from the bytes under the private
root. The intake record is not re-declared at all: the dry import already
authored one against the schema, and this tool records *that* record into the
graph root rather than restating a submission id.

Constitutional standing: an authoring tool. It evaluates no gate, invokes no
Claude, coins no ``schema_id``, writes only under the root it is given, and
declares nothing it did not read (CLAUDE.md §13.3). Its ``--check`` is a
byte-equal replay, so every value it writes is reproducible from its inputs
(§9.5).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from runner.atomic_write import atomic_write_text, canonical_json_bytes
from runner.dev_graph.builder import SOURCES_REL
from runner.dev_graph.intake import (
    INTAKE_REL,
    INTAKE_SCHEMA_ID,
    normalise_intake,
    record_esr_intake,
)
from runner.dev_graph.schema import DevGraphError
from runner.dry_import import (
    ACCEPTANCE_RECORD_TYPE,
    GRAPHICAL_PROOF_STATEMENT,
    LIMITATIONS_RECORD_TYPE,
    SPAN_LOCATES_STATEMENT,
    check_acceptance,
)
from runner.original_configuration import (
    INVENTORY_RECORD_TYPE,
    ConfigurationRefused,
    OriginalConfiguration,
    load_configuration,
    require_private_root,
)
from runner.original_configuration import check as check_configuration
from runner.source_index import read_page_text
from tools import fidelity_declarations

#: The record type both registers carry. One type, because the two are read by
#: the same readers: the integrity audit reads the provenance header's
#: ``is_submitted_document`` and its citation and identifier declarations, and
#: an original whose register declared a type of its own would be read by none
#: of them (harness/candidate_provenance.py).
REGISTER_RECORD_TYPE = "fidelity_register"

#: File names the V08 dry import writes, mirrored so this tool can bind each by
#: hash. ``tools/dry_import_original.py`` owns them and the test holds the two
#: lists equal; importing that module here would pull its argument parser into
#: a renderer.
INVENTORY_FILE = "dry_import_inventory.json"
PROVENANCE_FILE = "original_document_provenance.json"
ACCEPTANCE_FILE = "extraction_fidelity_acceptance.json"
LIMITATIONS_FILE = "unresolved_extraction_limitations.json"
PROVENANCE_RECORD_TYPE = "original_document_provenance"

#: Dev-graph directories the graph root carries empty until the importer and
#: the freeze write into them.
_EMPTY_DEV_GRAPH_DIRS = ("documents", "snapshots", "packages")
_DEV_GRAPH_REL = Path(INTAKE_REL).parent

_SCHEMA_REF = (
    "No declared schema. .claude/workflows/system_orchestration/artifact_schema_specification.yaml "
    "carries no tier3 schema for a fidelity register, and no schema_id is coined for it "
    "(CLAUDE.md §16.3). The shape is fixed by tools/author_original_workspace.py and checked by "
    "tests/test_msca_dn_original_import_route.py. The intake record is the one record under this "
    f"root that has a schema: {INTAKE_SCHEMA_ID}."
)

PROCEDURE_REL = "plans/msca_dn_v08_original_dry_import_procedure.md"
SPEC_REL = "plans/msca_dn_pre_evaluation_spec.md"
RUNBOOK_REL = "plans/msca_dn_pe09_runbook.md"


class AuthoringRefused(RuntimeError):
    """Refusal: an input is absent, inadmissible, or not the document's own."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# --------------------------------------------------------------------------- #
# The V08 records, read back and bound
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class DryImportRecords:
    """The four V08 records and the intake, each bound by the hash of its bytes."""

    dir_rel: str
    inventory: Mapping[str, Any]
    acceptance: Mapping[str, Any]
    limitations: Mapping[str, Any]
    provenance: Mapping[str, Any]
    intake: Mapping[str, Any]
    hashes: Mapping[str, str]

    def binding(self, key: str, file_name: str, record: Mapping[str, Any]) -> dict[str, Any]:
        """One pointer: the file, its record type and its bytes.

        The intake record carries a ``schema_id`` where the others carry a
        ``record_type``, so its type is the schema it was validated against.
        The hash is of the record's canonical bytes, the way V08's own
        provenance record binds these four, so a re-indented file keeps its
        binding and a changed value does not.
        """
        return {
            "record_file": f"{self.dir_rel}/{file_name}",
            "record_type": record.get("record_type", INTAKE_SCHEMA_ID),
            "sha256": self.hashes[key],
            "sha256_basis": "the record's canonical bytes",
        }


def _read_record(path: Path, expected: Optional[str], what: str) -> Mapping[str, Any]:
    if not path.is_file():
        raise AuthoringRefused(
            f"{what} {path.name} is not under the private root. The register of a submitted "
            f"document is rendered from the dry import's own records, so they have to be there."
        )
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise AuthoringRefused(f"{what} {path.name} is not valid JSON ({exc})") from exc
    if not isinstance(data, dict):
        raise AuthoringRefused(f"{what} {path.name} must hold a JSON object")
    if expected is not None and data.get("record_type") != expected:
        raise AuthoringRefused(
            f"{what} {path.name} carries record_type {data.get('record_type')!r}, not "
            f"{expected!r}"
        )
    return data


def read_dry_import(
    root: Path, configuration: OriginalConfiguration, intake_id: str, document_id: Optional[str]
) -> DryImportRecords:
    """The V08 records under *root*, refused unless they are this document's.

    Four refusals, each closing a way a register could end up describing one
    document with another's measurement: an inventory that measured other
    bytes, an acceptance record over other bytes, an intake under another id,
    and an intake naming another document.
    """
    directory = root / Path(configuration.dry_import_dir)
    names = {
        "inventory": (INVENTORY_FILE, INVENTORY_RECORD_TYPE),
        "acceptance": (ACCEPTANCE_FILE, ACCEPTANCE_RECORD_TYPE),
        "limitations": (LIMITATIONS_FILE, LIMITATIONS_RECORD_TYPE),
        "provenance": (PROVENANCE_FILE, PROVENANCE_RECORD_TYPE),
        "intake": (f"{intake_id}.json", None),
    }
    records: dict[str, Mapping[str, Any]] = {}
    hashes: dict[str, str] = {}
    for key, (file_name, record_type) in names.items():
        path = directory / file_name
        records[key] = _read_record(path, record_type, "the dry import's")
        hashes[key] = hashlib.sha256(
            canonical_json_bytes(dict(records[key]))
        ).hexdigest()
    for key in ("inventory", "acceptance"):
        measured = records[key].get("sha256")
        if measured != configuration.authenticated_sha256:
            raise AuthoringRefused(
                f"the dry import's {names[key][0]} is over bytes hashing to {measured!r} and "
                f"this configuration authenticated "
                f"{configuration.authenticated_sha256}. A register must not carry one "
                f"document's reconciliation as another's."
            )
    intake = normalise_intake(dict(records["intake"]), f"intake {intake_id}").to_dict()
    if intake["intake_id"] != intake_id:
        raise AuthoringRefused(
            f"the dry import's intake record declares intake_id {intake['intake_id']!r} and "
            f"this document's is {intake_id!r}"
        )
    if document_id is not None and intake["document_id"] != document_id:
        raise AuthoringRefused(
            f"the dry import's intake record names document {intake['document_id']!r} and this "
            f"document is {document_id!r}"
        )
    records["intake"] = intake
    hashes["intake"] = hashlib.sha256(canonical_json_bytes(intake)).hexdigest()
    return DryImportRecords(
        dir_rel=Path(configuration.dry_import_dir).as_posix(),
        inventory=records["inventory"],
        acceptance=records["acceptance"],
        limitations=records["limitations"],
        provenance=records["provenance"],
        intake=records["intake"],
        hashes=hashes,
    )


def require_complete_reconciliation(records: DryImportRecords) -> dict[str, Any]:
    """The reconciliation block, or a refusal naming what is still open.

    The register of a submitted document is the artifact a later reading leans
    on when it claims a passage was preserved. V08 settled what may stand
    behind such a claim, so this is where that rule is enforced rather than
    restated: an inadmissible record refuses, and so does an incomplete one.
    """
    acceptance = dict(records.acceptance)
    findings = check_acceptance(acceptance)
    rows = [row for row in acceptance.get("items", []) if isinstance(row, dict)]
    verdicts = {str(row.get("item")): str(row.get("verdict")) for row in rows}
    unreconciled = sorted(item for item, verdict in verdicts.items() if verdict == "unreconciled")
    if findings:
        listed = "; ".join(f"{f['code']} ({f['item']})" for f in findings)
        raise AuthoringRefused(
            f"the fidelity acceptance record is not admissible: {listed}. "
            f"py -3.10 -m tools.dry_import_original --check-acceptance names each one."
        )
    if not acceptance.get("complete") or unreconciled:
        raise AuthoringRefused(
            f"the fidelity acceptance record is not complete: "
            f"{len(unreconciled) or 'an item'} class(es) of evidence still unreconciled"
            f"{' (' + ', '.join(unreconciled) + ')' if unreconciled else ''}. "
            f"The register of a submitted document is what a later claim of preservation rests "
            f"on, so it is not authored over an open reconciliation ({PROCEDURE_REL} step 4)."
        )
    return {
        **records.binding("acceptance", ACCEPTANCE_FILE, records.acceptance),
        "complete": True,
        "classes_reconciled": len(verdicts),
        "verdicts": dict(sorted(verdicts.items())),
        "reconciled_by": sorted(
            {str(row.get("reconciled_by")) for row in rows if row.get("reconciled_by")}
        ),
        "statement": (
            "What the extraction of the submitted file loses is settled here, by an operator "
            "reading the PDF, and nowhere else. The derived half below measures what the "
            "extraction carried."
        ),
        "not_proof": GRAPHICAL_PROOF_STATEMENT,
    }


# --------------------------------------------------------------------------- #
# The register of a submitted document
# --------------------------------------------------------------------------- #


def _network_type(root: Path, revision: Any, configuration: OriginalConfiguration) -> dict[str, Any]:
    """The declared network type, checked on the page the operator names."""
    declared = configuration.dn_type
    if declared is None:
        return {
            "value": None,
            "declared_status": "Unresolved",
            "basis": (
                "this document's configuration declares no network type and no page to check it "
                "on. The copy's register declares one from the copy's own page map, which is not "
                "this document's, so nothing is carried across."
            ),
        }
    text = read_page_text(root / revision.pdf_rel, declared.page)
    if declared.marker not in text:
        raise AuthoringRefused(
            f"the network type is declared from the phrase {declared.marker!r} on p. "
            f"{declared.page}, and that page's text does not carry it"
        )
    return {
        "value": declared.value,
        "declared_status": "Confirmed",
        "basis": (
            f"the document states it on p. {declared.page}; this tool checks the declared phrase "
            f"on that page through the one sanctioned page reader"
        ),
    }


def _input_rows(root: Path, revision: Any, records: DryImportRecords) -> list[dict[str, Any]]:
    """The register's input table: what is under the private root, and nothing else.

    The copy's table resolves six public files from this repository. None of
    them is under a private root, and reading them from the clone this tool
    runs from would bind a private register to a public checkout. They are
    named below instead, without a hash this root cannot produce.
    """
    pdf = root / revision.pdf_rel
    rows: list[dict[str, Any]] = [
        {
            "role_key": "candidate",
            "role": revision.candidate_role,
            "path": revision.pdf_rel.as_posix(),
            "version": revision.candidate_version,
            "sha256": _sha256(pdf),
            "sha256_status": "Confirmed",
            "sha256_basis": "derived from the bytes under the private root",
        }
    ]
    for key, file_name in (
        ("inventory", INVENTORY_FILE),
        ("acceptance", ACCEPTANCE_FILE),
        ("limitations", LIMITATIONS_FILE),
        ("provenance", PROVENANCE_FILE),
    ):
        record = getattr(records, key)
        rows.append(
            {
                "role_key": f"v08_{key}",
                "role": f"the dry import's {key} record (V08)",
                "path": f"{records.dir_rel}/{file_name}",
                "version": str(record.get("record_type")),
                "sha256": records.hashes[key],
                "sha256_status": "Confirmed",
                "sha256_basis": "derived from the record's canonical bytes",
            }
        )
    return rows


def _render_declared_half(
    root: Path, revision: Any, config: Any, derived: Mapping[str, Any]
) -> dict[str, Any]:
    """The operator's per-sub-section reconciliation, carried through unchanged.

    The same mechanism as the copy's declared half (R01) under this document's
    own contract: its own directory, its own record type and its own two
    fields. A *transformation* field is not among them, because nothing
    transformed this document.
    """
    contract = config.declaration_contract()
    rows, block = fidelity_declarations.declared_half(
        root,
        revision.revision_id,
        revision.register_rel,
        (row["sub_section_id"] for row in derived["sub_sections"]),
        contract,
    )
    half: dict[str, Any] = {
        "kind": "declared",
        "fields_per_sub_section": list(contract.required_fields),
        "note": (
            "Two independent fields per sub-section. 'presence' is whether the sub-section is "
            "there, read against the PDF page; 'extraction_fidelity' is what the extraction of "
            "it carried and what it lost. Neither is a fidelity-to-the-original claim: this "
            "document is the original, so that question does not arise here (R04's third claim)."
        ),
        "input_contract": {
            "directory": contract.dir_rel.as_posix(),
            "record_type": contract.record_type,
            "basis": (
                "the operator's durable input, one file per revision, under the private root. "
                "This tool reads it, carries its rows through unchanged, and never writes it."
            ),
        },
    }
    if block is not None:
        half[fidelity_declarations.INPUT_BLOCK_KEY] = block
    half[fidelity_declarations.SUB_SECTIONS_KEY] = list(rows)
    return half


def render_submitted_register(repo_root: Path, revision: Any) -> dict[str, Any]:
    """The fidelity register of a submitted document (V18).

    *repo_root* is the private root. Called by the importer's renderer, which
    chooses between this and the copy's by the document's own
    ``is_submitted_document`` flag.
    """
    from tools.import_external_proposal import config_for, derive_register_half

    config = config_for(revision)
    if not config.is_submitted_document:
        raise AuthoringRefused(
            f"document {config.config_id!r} is not the submitted text; its register is "
            f"tools/author_msca_dn_workspace.render_register, whose header declares the "
            f"sanitisation, the transformation and the reflow this one does not"
        )
    configuration = require_configuration(repo_root, config)
    records = read_dry_import(
        repo_root, configuration, config.require_intake_id(), config.document_id
    )
    reconciliation = require_complete_reconciliation(records)
    derived = derive_register_half(repo_root, revision)
    pages = int(derived["pages"])
    expected = config.expected_pages_of(revision)
    if pages != expected:
        raise AuthoringRefused(
            f"candidate: the configuration declares {expected} page(s) and the extraction read "
            f"{pages}"
        )
    if derived["candidate_sha256"] != configuration.authenticated_sha256:
        raise AuthoringRefused(
            "candidate: the file this register was derived from is not the one the configuration "
            "authenticated"
        )
    rows = _input_rows(repo_root, revision, records)
    intake = records.intake
    return {
        "record_type": REGISTER_RECORD_TYPE,
        "schema_ref": _SCHEMA_REF,
        "artifact_purpose": (
            "The fidelity register of the submitted Part B: which file was assessed, what the "
            "extraction of it carries, and how much of that is measured rather than reconciled "
            "by an operator. The copy's register answers how a derivative differs from this "
            "document; this one answers what reading this document through an extraction costs."
        ),
        "spec": SPEC_REL,
        "runbook": RUNBOOK_REL,
        "ticket": "V18, authored inside the private network",
        "provenance": {
            "kind": "declared",
            "declared_by": configuration.declared_by,
            "declared_on": configuration.declared_on,
            "declared_status": configuration.declared_status,
            "status_note": (
                "The page map, the page count, the body point size and the work-package layout "
                "are the operator's declarations from the V08 reconciliation, checked against "
                "the dry-import inventory before this register was authored. The hashes, the "
                "page count and the network-type phrase below are derived from the bytes under "
                "the private root and stand Confirmed where they are measured. What the "
                "extraction loses is the reconciliation, not a measurement."
            ),
            "configuration_input": {
                "file": configuration.path_rel,
                "sha256": configuration.sha256,
                "record_type": "original_document_configuration",
                "checked_against": f"{records.dir_rel}/{INVENTORY_FILE}",
                "checked_by": "runner/original_configuration.py",
            },
            "historical_submission": {
                "instrument": "MSCA Doctoral Networks",
                "dn_type": _network_type(repo_root, revision, configuration),
                "call_id": {
                    "value": intake["call_id"],
                    "declared_status": "Assumed",
                    "basis": "operator declaration, carried from the intake record",
                    "owner": "the intake record; never the profile, run label or report",
                },
                "submission_id": {
                    "value": intake["submission_id"],
                    "declared_status": "Assumed",
                    "basis": (
                        "operator declaration, carried from the intake record. It stays with "
                        "this register inside the private network."
                    ),
                },
                "intake": {
                    **records.binding("intake", f"{intake['intake_id']}.json", intake),
                    "schema_id": INTAKE_SCHEMA_ID,
                    "intake_id": intake["intake_id"],
                    "recorded_in_the_graph_root": (
                        f"{configuration.workspace_rel}/{INTAKE_REL}/{intake['intake_id']}.json"
                    ),
                },
            },
            "current_assessment_artifact": {
                "path": revision.pdf_rel.as_posix(),
                "sha256": derived["candidate_sha256"],
                "pages": pages,
                "kind": "the Part B as submitted",
                "is_submitted_document": config.is_submitted_document,
                "authentication": {
                    "declared_sha256": configuration.authenticated_sha256,
                    "basis": (
                        "the operator's hash from the authoritative source. The dry import "
                        "refuses a file that does not match it, the configuration carries it, "
                        "and this register is refused unless the file it was derived from hashes "
                        "to it."
                    ),
                },
                "statement": (
                    "This file is the text the ESR evaluated. A result over it is a result over "
                    "the submission, as far as the extraction of it carries the submission: what "
                    "the extraction loses is the reconciliation above, and no statement here "
                    "settles it."
                ),
            },
            "transformation": {
                "applied": False,
                "declared_status": "Confirmed",
                "basis": (
                    "derived: the assessed file hashes to the authenticated original, so nothing "
                    "stands between the submission and the text assessed here"
                ),
                "identifiers": "unchanged: as submitted",
                "citations": (
                    "unchanged: as submitted. Whether a cited source exists is not resolved "
                    "here; the imported-source grounding route is ticket X01."
                ),
                "prose": "unchanged: as submitted",
                "figures": (
                    "unchanged in the file. What the extraction carries of them is the "
                    "reconciliation, where each class of graphical evidence has a verdict."
                ),
                "statement": (
                    "This block says what happened to the submission on its way to the assessed "
                    "text, and the answer is nothing. It is not a declaration that the "
                    "extraction preserved everything."
                ),
                "reflow": {
                    "applied": False,
                    "current_pages": pages,
                    "consequence": (
                        "the page count is the submitted document's own, so a page-based reading "
                        "here is a reading of the submission rather than of a reflowed copy. "
                        "What the page limit was is the call's, and this register does not state "
                        "it."
                    ),
                },
            },
            "relationship_to_esr": {
                "statement": (
                    "The ESR evaluated this text. A difference between a result over this "
                    "document and the ESR's own is therefore not explained by changed wording or "
                    "removed evidence, as it is for the copy. Assessor variance, the profile and "
                    "what the extraction lost remain."
                ),
                "esr_record": "docs/tier4_orchestration_state/msca_dn/esr/ (this repository)",
                "esr_sha256": None,
                "esr_sha256_basis": (
                    "not resolved under the private root. The ESR is a public artifact of the "
                    "repository, bound by hash in the committed register and in the V09 "
                    "authority index; a hash this root cannot produce is not restated here."
                ),
            },
            "storage": {
                "stored_in_the_public_repository": False,
                "basis": (
                    "measured: the private root this register is authored under resolves outside "
                    "the repository the tool belongs to, and no argument moves where that is"
                ),
                "consequence": (
                    "no page text, no span, no register row and no declaration about this "
                    "document reaches the public repository through this tool"
                ),
            },
            "extraction_reconciliation": reconciliation,
            "unresolved_extraction_limitations": {
                **records.binding("limitations", LIMITATIONS_FILE, records.limitations),
                "limitations_recorded": len(records.limitations.get("limitations") or []),
                "span_locates_statement": SPAN_LOCATES_STATEMENT,
            },
            "document_provenance": records.binding(
                "provenance", PROVENANCE_FILE, records.provenance
            ),
            "inputs": rows,
        },
        "derived": derived,
        "declared": _render_declared_half(repo_root, revision, config, derived),
    }


# --------------------------------------------------------------------------- #
# The private graph root
# --------------------------------------------------------------------------- #


def require_configuration(root: Path, config: Any) -> OriginalConfiguration:
    """The configuration a completed document was built from, read back.

    The importer applies a configuration input and keeps its path and hash in
    the document's ``page_map_declared_from``, which is a sentence rather than
    a handle. A renderer needs the file, so the document carries the path and
    this reads and re-checks it. A document the operator has not completed
    refuses, naming the input.
    """
    rel = config.configuration_input_rel
    if rel is None:
        raise AuthoringRefused(
            f"document {config.config_id!r} carries no configuration input, so there is nothing "
            f"to render its register from. Complete it with --config-input "
            f"(runner/original_configuration.py)."
        )
    configuration = load_configuration(root / Path(rel), root)
    report = check_configuration(configuration, root)
    if not report.green:
        listed = "; ".join(f"{name}" for name, _detail in report.findings)
        raise AuthoringRefused(
            f"the configuration input {Path(rel).name} disagrees with the measurement it names: "
            f"{listed}"
        )
    return configuration


def render_readme(configuration: OriginalConfiguration, config: Any) -> str:
    """The private graph root's README, in the document's own names."""
    revision = config.revisions[0]
    pages = config.expected_pages_of(revision)
    return (
        "# MSCA-DN private graph root: the Part B as submitted\n"
        "\n"
        f"This directory is the `--graph-root` of the submitted original ({RUNBOOK_REL} §4).\n"
        "It is not in the public repository and must not be copied into one. Every record here is\n"
        "derived from the submitted text.\n"
        "\n"
        "What lives here:\n"
        "\n"
        f"- `{SOURCES_REL.as_posix()}`: the source index, one source per page of "
        f"{config.short_name}\n"
        f"  (`{config.source_id(revision, 1)}` to `{config.source_id(revision, pages)}`), each "
        "holding that page's text.\n"
        f"- `{_DEV_GRAPH_REL.as_posix()}/intake/{config.require_intake_id()}.json`: the intake "
        "record the dry\n"
        "  import authored, recorded into this graph root.\n"
        f"- `{_DEV_GRAPH_REL.as_posix()}/documents/`: the imported document record (schema v2).\n"
        f"- `{_DEV_GRAPH_REL.as_posix()}/imports/{revision.manifest_name}`: the import manifest.\n"
        f"- `{_DEV_GRAPH_REL.as_posix()}/snapshots/`, `packages/`: written by the freeze.\n"
        "\n"
        "What does not live here:\n"
        "\n"
        f"- The PDF, its register and the V08 records, under `{configuration.dry_import_dir}/` "
        "and\n"
        f"  `{Path(revision.register_rel).parent.as_posix()}/` of the private root.\n"
        "- The ESR record and the Tier 2A authorities, which are the public repository's.\n"
        "\n"
        "The assessment artifact under the register is the submitted text itself. A result over it\n"
        "is a result over the submission, as far as the extraction carries it: what the extraction\n"
        f"loses is the reconciliation in `{configuration.dry_import_dir}/{ACCEPTANCE_FILE}`.\n"
        "\n"
        "Authored by `py -3.10 -m tools.author_original_workspace` (skeleton, intake) and\n"
        "`py -3.10 -m tools.import_external_proposal --document official_original` (sources,\n"
        "document record, manifest, the register). Each tool's `--check` exits 1 if a file it owns\n"
        f"would change. The operator procedure is `{PROCEDURE_REL}`.\n"
    )


def _intake_fields(records: DryImportRecords) -> dict[str, Any]:
    """The dry import's intake record, in the writer's keyword shape."""
    intake = records.intake
    return {
        "intake_id": intake["intake_id"],
        "document_id": intake["document_id"],
        "submission_id": intake["submission_id"],
        "call_id": intake["call_id"],
        "prior_submission": intake["prior_submission"],
        "esr_availability": intake["esr_availability"],
        "permitted_purpose": intake["permitted_purpose"],
        "esr_reference": intake.get("esr_reference"),
    }


def render_all(root: Path, configuration: OriginalConfiguration) -> dict[str, bytes]:
    """Every file this tool authors under the private root, as its bytes.

    The register, the source index, the document record and the manifest are
    the importer's: this tool writes the skeleton the importer needs and the
    intake record it was given.
    """
    config = _completed(configuration)
    records = read_dry_import(
        root, configuration, config.require_intake_id(), config.document_id
    )
    workspace = Path(configuration.workspace_rel)
    intake = records.intake
    files: dict[str, bytes] = {
        (workspace / "README.md").as_posix(): render_readme(configuration, config).encode(
            "utf-8"
        ),
        (workspace / INTAKE_REL / f"{intake['intake_id']}.json").as_posix(): canonical_json_bytes(
            dict(intake)
        ),
    }
    for name in _EMPTY_DEV_GRAPH_DIRS:
        files[(workspace / _DEV_GRAPH_REL / name / ".gitkeep").as_posix()] = b""
    scorecard = configuration.scorecard_rel
    if scorecard is not None:
        files[Path(scorecard).as_posix()] = _scorecard_bytes(scorecard)
    return files


def _scorecard_bytes(scorecard_rel: str) -> bytes:
    """The evaluator scorecard, copied from this repository into the private root.

    A sub-section the document leaves unlabelled takes its title from the
    application form's scorecard, and the importer resolves that path against
    the root it is given. The scorecard is a public Tier 2A derivative, so
    copying it into the private root moves nothing private and lets the import
    run with no path back into this repository.
    """
    from runner.original_configuration import THIS_REPOSITORY

    source = THIS_REPOSITORY / Path(scorecard_rel)
    if not source.is_file():
        raise AuthoringRefused(
            f"the configuration declares scorecard_rel {scorecard_rel!r} and no such file is in "
            f"this repository to copy from. A sub-section with no heading and no declared title "
            f"takes its title from the application form's scorecard."
        )
    return source.read_bytes()


def _completed(configuration: OriginalConfiguration) -> Any:
    """The document configuration this input completes, completed."""
    from tools.import_external_proposal import complete_from_input, document_by_id

    return complete_from_input(document_by_id(configuration.config_id), configuration)


def check(root: Path, configuration: OriginalConfiguration) -> list[str]:
    """Relative paths whose bytes differ from the rendering, or are absent."""
    return [
        rel
        for rel, data in render_all(root, configuration).items()
        if not (root / rel).is_file() or (root / rel).read_bytes() != data
    ]


def author(root: Path, configuration: OriginalConfiguration) -> list[str]:
    """Write the skeleton under *root*; return the relative paths that changed."""
    config = _completed(configuration)
    records = read_dry_import(
        root, configuration, config.require_intake_id(), config.document_id
    )
    workspace = Path(configuration.workspace_rel)
    intake_rel = (
        workspace / INTAKE_REL / f"{records.intake['intake_id']}.json"
    ).as_posix()
    changed: list[str] = []
    for rel, data in render_all(root, configuration).items():
        target = root / rel
        if target.is_file() and target.read_bytes() == data:
            continue
        if rel == intake_rel:
            # The engine's writer owns immutability: a changed intake is refused.
            record_esr_intake(root / workspace, **_intake_fields(records))
        elif data == b"":
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"")
        else:
            atomic_write_text(data.decode("utf-8"), target)
        changed.append(rel)
    return changed


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--root",
        type=Path,
        required=True,
        help="the private root; refused if it resolves inside this repository",
    )
    parser.add_argument(
        "--config-input",
        type=Path,
        required=True,
        help="the configuration input, relative to the private root or absolute",
    )
    parser.add_argument(
        "--check", action="store_true", help="exit 1 if any authored file would change"
    )
    args = parser.parse_args(argv)
    try:
        root = require_private_root(args.root)
        path = args.config_input
        path = path if path.is_absolute() else root / path
        configuration = load_configuration(path, root)
        report = check_configuration(configuration, root)
        for line in report.lines():
            print(line)
        if not report.green:
            print(
                f"refused: the configuration disagrees with the measurement it names in "
                f"{len(report.findings)} place(s); nothing was written",
                file=sys.stderr,
            )
            return 1
        if args.check:
            stale = check(root, configuration)
            for rel in stale:
                print(f"would change: {rel}")
            print("up to date" if not stale else f"{len(stale)} file(s) would change")
            return 1 if stale else 0
        changed = author(root, configuration)
        for rel in changed:
            print(f"wrote: {rel}")
        print("no change" if not changed else f"{len(changed)} file(s) written")
        return 0
    except (
        AuthoringRefused,
        ConfigurationRefused,
        DevGraphError,
        fidelity_declarations.FidelityDeclarationsError,
    ) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
