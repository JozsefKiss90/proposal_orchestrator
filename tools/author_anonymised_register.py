"""The fidelity register of the anonymised derivative (AN10).

AN10 of ``.scratch/msca-dn-anonymisation/tickets.md``, §7 of
``plans/msca_dn_anonymisation_handoff_2026-10-14.md``. The anonymised derivative
is a third document. It is not the submitted text, whose register
``tools/author_original_workspace.render_submitted_register`` renders, and it is
not the sanitised copy, whose register ``tools/author_msca_dn_workspace.render_register``
renders. Each of those headers states its own document's facts, so neither may
render this one, and this renderer refuses every document but the derivative.
``tools.import_external_proposal.register_of`` chooses between the three.

What the register states
------------------------
The derivative's own facts, each read from a stage record and bound by hash:

* **where it came from**: the authenticated original's hash, pinned by the A0
  intake record, and the stage chain the A6 report bound from it to this file;
* **how**: the pipeline revision (an operator declaration, because no stage
  record carries it) and the policy version and hash every stage ran under;
* **layout**: preserved or reflowed, from the A6 page-count comparison;
* **figures**: how many were looked at and found preserved, masked or redrawn,
  from the A6 figure review;
* **citations**: the count of kept citation markers before and after, and how
  many neutral markers took a self-citation's place;
* **Table 1.4.1**: synthetic, from the A4 log in the stage chain.

The register is not authored over a failing A6 report. Layout, figures and
citations are stated from that report, and a report with an unexplained
difference supports none of them. Nor is it authored over a chain with no A4
log: the derivative replaces Table 1.4.1, and a file that does not is not it.

What it carries for the audit
-----------------------------
``record_type`` is ``fidelity_register``, the type the integrity audit reads
whichever document it was pointed at. ``current_assessment_artifact.derived_from.route``
is :data:`DERIVATION_ROUTE`, and ``transformation.identifiers`` and
``transformation.citations`` lead with words in
``harness/candidate_provenance.py``'s vocabulary. So the audit scopes the
derivative's identities as a derivative of the original, and words its
not-comparable findings that way.

What is private
---------------
The register is authored under the private root, beside the derivative. It is
exported with the derivative once A7 accepts it (handoff §6). It quotes no
heading, no table cell and no entity: it carries counts, pages, hashes and the
paths of private records relative to the private root.

Constitutional standing: an authoring tool. It evaluates no gate, invokes no
model, coins no ``schema_id``, writes nothing itself (the importer writes what
it returns), and declares nothing it did not read (CLAUDE.md §13.3).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, NamedTuple, Optional

from runner import anonymisation_fidelity as af
from runner import anonymisation_intake as ai
from runner import anonymisation_policy as ap
from runner import anonymisation_table as at
from runner.original_configuration import RECORD_TYPE as CONFIGURATION_RECORD_TYPE
from runner.original_configuration import require_private_root
from tools import fidelity_declarations
from tools.author_msca_dn_workspace import REGISTER_RECORD_TYPE
from tools.author_original_workspace import AuthoringRefused, require_configuration

__all__ = [
    "AuthoringRefused",
    "DERIVATION_ROUTE",
    "REGISTER_RECORD_TYPE",
    "render_anonymised_register",
]

#: The ``derived_from.route`` this register declares. Mirrored by
#: ``harness.candidate_provenance.DERIVATION_ROUTE_ANONYMISATION``, which a
#: test holds equal: ``tools`` may not be imported by the harness.
DERIVATION_ROUTE = "anonymisation_of_the_original"

HANDOFF_REL = "plans/msca_dn_anonymisation_handoff_2026-10-14.md"
TICKETS_REL = ".scratch/msca-dn-anonymisation/tickets.md"

_SCHEMA_REF = (
    "No declared schema. .claude/workflows/system_orchestration/artifact_schema_specification.yaml "
    "carries no tier3 schema for a fidelity register, and no schema_id is coined for it "
    "(CLAUDE.md §16.3). The shape is fixed by tools/author_anonymised_register.py and checked by "
    "tests/test_msca_dn_anonymised_derivative.py."
)

#: The figure verdicts a register counts. ``lost`` is absent: a lost figure
#: is an A6 finding, and the register is not authored over one.
_FIGURE_VERDICTS: tuple[str, ...] = ("preserved", "masked", "redrawn")

#: Citation classes whose count the policy keeps. A marker of one of these
#: classes may only leave the derivative with a neutral marker in its place
#: (A6); a neutral marker may also stand where a self-citation entry stood.
_KEPT_CLASSES: tuple[str, ...] = tuple(sorted(af.MARKER_CLASSES))


class _Bound(NamedTuple):
    """A record read under the private root, with the hash of its bytes."""

    rel: str
    record: dict[str, Any]
    sha256: str


def _read(root: Path, rel: str, what: str) -> _Bound:
    path = (root / Path(rel)).resolve()
    if path != root and root not in path.parents:
        raise AuthoringRefused(
            f"{what} {Path(rel).name} does not resolve under the private root. Every record "
            f"this register binds sits beside the derivative."
        )
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise AuthoringRefused(
            f"{what} {Path(rel).name} cannot be read under the private root "
            f"({type(exc).__name__}). The register of the derivative is rendered from the "
            f"stage records, so they have to be there."
        ) from exc
    try:
        record = json.loads(data)
    except ValueError as exc:
        raise AuthoringRefused(f"{what} {Path(rel).name} is not valid JSON") from exc
    if not isinstance(record, dict):
        raise AuthoringRefused(f"{what} {Path(rel).name} must hold a JSON object")
    return _Bound(Path(rel).as_posix(), record, hashlib.sha256(data).hexdigest())


def _binding(bound: _Bound, record_type: str) -> dict[str, Any]:
    return {
        "record_file": bound.rel,
        "record_type": record_type,
        "sha256": bound.sha256,
        "sha256_basis": "the record's bytes under the private root",
    }


def _field(record: Mapping[str, Any], what: str, *keys: str) -> Any:
    value: Any = record
    for key in keys:
        if not isinstance(value, Mapping) or key not in value:
            raise AuthoringRefused(f"{what} carries no {'.'.join(keys)}")
        value = value[key]
    return value


# --------------------------------------------------------------------------- #
# The stage records, each bound to the A6 report
# --------------------------------------------------------------------------- #


def _fidelity_report(root: Path, rel: str, candidate_sha256: str) -> _Bound:
    report = _read(root, rel, "the structural fidelity report")
    record = report.record
    if record.get("schema") != af.SCHEMA or record.get("record_type") != af.RECORD_TYPE:
        raise AuthoringRefused(f"the structural fidelity report is not {af.SCHEMA}")
    if _field(record, "the structural fidelity report", "input", "derivative_sha256") != (
        candidate_sha256
    ):
        raise AuthoringRefused(
            "the structural fidelity report compared another derivative, not the file this "
            "register describes. A register states the facts of the file it was derived from."
        )
    if record.get("verdict") != "pass":
        raise AuthoringRefused(
            f"the structural fidelity report's verdict is {record.get('verdict')!r}, not 'pass'. "
            f"Layout, figures and citations are stated from that report, and a report with an "
            f"unexplained difference supports none of them; fix the stage and re-run A6."
        )
    return report


def _intake(root: Path, rel: str, report: _Bound) -> _Bound:
    intake = _read(root, rel, "the A0 intake record")
    if intake.record.get("schema") != ai.SCHEMA:
        raise AuthoringRefused(f"the A0 intake record is not {ai.SCHEMA}")
    if intake.sha256 != _field(report.record, "the A6 report", "input", "intake_record_sha256"):
        raise AuthoringRefused(
            "the A0 intake record is not the one the structural fidelity report compared "
            "against: its bytes hash to another value"
        )
    return intake


def _policy(root: Path, rel: str, report: _Bound) -> tuple[ap.LoadedPolicy, str]:
    try:
        policy = ap.load(root / Path(rel))
    except ap.PolicyRefused as exc:
        raise AuthoringRefused(f"the policy cannot be read: {exc}") from exc
    if policy.sha256 != report.record.get("policy_sha256"):
        raise AuthoringRefused(
            f"the policy hashes to {policy.sha256}, and the structural fidelity report ran under "
            f"{report.record.get('policy_sha256')}. A change of policy re-opens acceptance."
        )
    return policy, Path(rel).as_posix()


def _stage_logs(
    root: Path, rels: tuple[str, ...], report: _Bound
) -> list[tuple[dict[str, Any], _Bound]]:
    links = _field(report.record, "the A6 report", "input", "stage_logs")
    if not isinstance(links, list) or len(links) != len(rels):
        raise AuthoringRefused(
            f"the configuration names {len(rels)} stage log(s) and the structural fidelity "
            f"report bound {len(links) if isinstance(links, list) else 'none'}. The register "
            f"binds the chain the report checked, every link of it."
        )
    out: list[tuple[dict[str, Any], _Bound]] = []
    for rel, link in zip(rels, links):
        log = _read(root, rel, "a stage log")
        if not isinstance(link, Mapping) or log.sha256 != link.get("log_sha256"):
            raise AuthoringRefused(
                f"the stage log {Path(rel).name} is not the one the structural fidelity report "
                f"bound at that link: its bytes hash to another value"
            )
        out.append((dict(link), log))
    return out


def _inventory(root: Path, rel: str, expected: str, what: str) -> dict[str, Any]:
    bound = _read(root, rel, what)
    if bound.sha256 != expected:
        raise AuthoringRefused(
            f"{what} {Path(rel).name} hashes to {bound.sha256}, not the {expected} its record "
            f"bound"
        )
    return bound.record


# --------------------------------------------------------------------------- #
# The derivative's facts
# --------------------------------------------------------------------------- #


def _reflow(report: Mapping[str, Any], pages: int) -> dict[str, Any]:
    differences = int(
        _field(report, "the A6 report", "counts", "page_count", "differences")
    )
    applied = differences > 0
    return {
        "applied": applied,
        "layout": "reflowed" if applied else "preserved",
        "current_pages": pages,
        "declared_status": "Confirmed",
        "basis": (
            "derived: the structural fidelity report compares the derivative's page count, "
            "headings and their pages, and tables with the original's, and it passed"
        ),
        "consequence": (
            "the page count and the page of every heading are the original's, so a page-based "
            "reading here reads the original's pages"
            if not applied
            else "the page count is not the original's, so a page-based reading here is not one "
            "of the original"
        ),
    }


def _figures(report: Mapping[str, Any]) -> dict[str, Any]:
    figures = [f for f in report.get("figures") or [] if isinstance(f, Mapping)]
    reviewed = [f for f in figures if isinstance(f.get("review"), Mapping)]
    by_verdict = {
        verdict: sum(1 for f in reviewed if f["review"].get("verdict") == verdict)
        for verdict in _FIGURE_VERDICTS
    }
    return {
        "by_verdict": by_verdict,
        "pages_looked_at": len(reviewed),
        "graphical_pages": len(figures),
        "declared_status": "Confirmed",
        "basis": (
            "an operator's figure review of this derivative, one entry per graphical page, "
            "checked by the structural fidelity report. A verdict resting on a measurement alone "
            "is refused there."
        ),
    }


def _citation_markers(
    report: Mapping[str, Any], reference: Mapping[str, Any], derivative: Mapping[str, Any]
) -> dict[str, Any]:
    ref = _field(reference, "the reference inventory", "citation_markers", "counts")
    der = _field(derivative, "the derivative inventory", "citation_markers", "counts")
    reference_kept = sum(int(ref.get(c, 0)) for c in _KEPT_CLASSES)
    derivative_kept = sum(int(der.get(c, 0)) for c in _KEPT_CLASSES)
    neutral = int(der.get(af.NEUTRAL_CLASS, 0)) - int(ref.get(af.NEUTRAL_CLASS, 0))
    replaced = max(0, reference_kept - derivative_kept)
    lost = max(0, replaced - neutral)
    if derivative_kept > reference_kept:
        raise AuthoringRefused(
            f"the derivative carries {derivative_kept} citation marker(s) of the kept classes "
            f"and the original {reference_kept}, yet the structural fidelity report passed. "
            f"No policy rule adds a marker of a kept class, and the register states neither."
        )
    if lost:
        raise AuthoringRefused(
            f"the original carries {reference_kept} citation marker(s) of the kept classes, the "
            f"derivative {derivative_kept}, and only {neutral} neutral marker(s) stand in for the "
            f"difference; yet the structural fidelity report passed. The two records contradict "
            f"each other, and the register states neither."
        )
    counts = _field(report, "the A6 report", "counts", "citation_markers")
    return {
        "count_kept": True,
        "kept_classes": list(_KEPT_CLASSES),
        "reference_kept": reference_kept,
        "derivative_kept": derivative_kept,
        "replaced_by_neutral_markers": replaced,
        "markers_lost": lost,
        "neutral_markers": neutral,
        "identifiers_removed": {
            cls: int(ref.get(cls, 0)) - int(der.get(cls, 0))
            for cls in sorted(af.IDENTIFIER_CLASSES)
        },
        "differences": int(counts["differences"]),
        "differences_explained": int(counts["explained"]),
        "declared_status": "Confirmed",
        "basis": (
            "derived from the reference and derivative inventories, each bound by hash, and the "
            "structural fidelity report, which explains every per-page difference by a logged "
            "edit"
        ),
    }


def _table(logs: list[tuple[dict[str, Any], _Bound]]) -> dict[str, Any]:
    tables = [log for _link, log in logs if log.record.get("schema") == at.SCHEMA]
    if not tables:
        raise AuthoringRefused(
            "no A4 table synthesis log is in the stage chain. The derivative replaces Table "
            "1.4.1 with a synthetic table (handoff §2), and its reader caveat says so; a file "
            "without one is not the anonymised derivative, so its register is not authored."
        )
    log = tables[-1].record
    table = _field(log, "the A4 log", "table")
    return {
        "synthetic": True,
        "page": table.get("page"),
        "data_rows": table.get("data_rows"),
        "columns": table.get("columns"),
        "strategy": table.get("strategy"),
        "cells_by_rule": log.get("cells_by_rule"),
        "declared_status": "Confirmed",
        "basis": (
            "derived from the A4 log in the stage chain, bound by hash. The row map that holds "
            "the values stays private and is not bound here."
        ),
    }


def _declared_half(root: Path, revision: Any, config: Any, derived: Mapping[str, Any]) -> dict[str, Any]:
    """The operator's per-sub-section declarations, under this document's contract."""
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
            "Two fields per sub-section. 'presence' is whether the sub-section is there, read "
            "against the derivative's page; 'transformation' is what the anonymisation did to it. "
            "Neither restates the stage logs, which record every edit by page."
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


# --------------------------------------------------------------------------- #
# The register
# --------------------------------------------------------------------------- #


def render_anonymised_register(repo_root: Path, revision: Any) -> dict[str, Any]:
    """The fidelity register of an anonymised derivative (AN10).

    *repo_root* is the private root. Called by the importer's ``register_of``,
    which chooses this renderer by the document's ``is_anonymised_derivative``
    flag. Refuses every other document, and refuses a root inside this
    repository.
    """
    from tools.import_external_proposal import config_for, derive_register_half

    config = config_for(revision)
    if not config.is_anonymised_derivative:
        raise AuthoringRefused(
            f"document {config.config_id!r} is not an anonymised derivative; its register is "
            f"{'the submitted text' if config.is_submitted_document else 'the sanitised copy'}'s "
            f"own renderer's, whose header states that document's facts"
        )
    root = require_private_root(Path(repo_root))
    configuration = require_configuration(root, config)
    derivation = configuration.derivation
    if derivation is None:
        raise AuthoringRefused(
            f"the configuration input {Path(configuration.path_rel).name} declares no derivation, "
            f"so nothing says which pipeline revision, policy and stage chain made this file"
        )
    derived = derive_register_half(root, revision)
    pages = int(derived["pages"])
    expected = config.expected_pages_of(revision)
    if pages != expected:
        raise AuthoringRefused(
            f"candidate: the configuration declares {expected} page(s) and the extraction read "
            f"{pages}"
        )
    candidate_sha256 = derived["candidate_sha256"]
    if candidate_sha256 != configuration.authenticated_sha256:
        raise AuthoringRefused(
            "candidate: the file this register was derived from is not the one the configuration "
            "authenticated"
        )

    report = _fidelity_report(root, derivation.fidelity_report, candidate_sha256)
    intake = _intake(root, derivation.intake_record, report)
    policy, policy_rel = _policy(root, derivation.policy, report)
    logs = _stage_logs(root, derivation.stage_logs, report)
    reference = _inventory(
        root,
        (
            Path(derivation.intake_record).parent
            / str(_field(intake.record, "the A0 intake record", "reference_inventory", "file"))
        ).as_posix(),
        str(_field(intake.record, "the A0 intake record", "reference_inventory", "sha256")),
        "the reference inventory",
    )
    derivative_inventory = _inventory(
        root,
        (Path(derivation.fidelity_report).parent / af.DERIVATIVE_INVENTORY_FILE).as_posix(),
        str(_field(report.record, "the A6 report", "input", "derivative_inventory_sha256")),
        "the derivative inventory",
    )
    original_sha256 = str(_field(intake.record, "the A0 intake record", "input", "sha256"))
    table = _table(logs)

    stage_rows = [
        {
            "stage": link.get("stage"),
            "record_file": log.rel,
            "schema": log.record.get("schema"),
            "sha256": log.sha256,
            "output_sha256": link.get("output_sha256"),
        }
        for link, log in logs
    ]
    inputs = [
        {
            "role_key": "candidate",
            "role": revision.candidate_role,
            "path": revision.pdf_rel.as_posix(),
            "version": revision.candidate_version,
            "sha256": candidate_sha256,
            "sha256_status": "Confirmed",
            "sha256_basis": "derived from the bytes under the private root",
        },
        {
            "role_key": "a0_intake",
            "role": "the A0 intake record that pinned the original",
            "path": intake.rel,
            "version": ai.SCHEMA,
            "sha256": intake.sha256,
            "sha256_status": "Confirmed",
            "sha256_basis": "derived from the record's bytes",
        },
        {
            "role_key": "policy",
            "role": "the anonymisation policy every stage ran under",
            "path": policy_rel,
            "version": f"{ap.SCHEMA}, version {policy.version}",
            "sha256": policy.sha256,
            "sha256_status": "Confirmed",
            "sha256_basis": "the policy's own hash (runner.anonymisation_policy.policy_sha256)",
        },
        {
            "role_key": "a6_structural_fidelity",
            "role": "the A6 structural fidelity report",
            "path": report.rel,
            "version": af.SCHEMA,
            "sha256": report.sha256,
            "sha256_status": "Confirmed",
            "sha256_basis": "derived from the record's bytes",
        },
    ]
    identifiers = (
        "pseudonymised: every entity the policy names was replaced by a code from the private "
        "entity dictionary, and the synthetic supervisor table carries the same codes"
    )
    return {
        "record_type": REGISTER_RECORD_TYPE,
        "schema_ref": _SCHEMA_REF,
        "artifact_purpose": (
            "The fidelity register of the anonymised derivative: which file was assessed, which "
            "original and which pipeline it came from, and what the anonymisation changed. The "
            "submitted document's register answers what reading the original through an "
            "extraction costs; this one answers how the derivative differs from the original."
        ),
        "spec": HANDOFF_REL,
        "tickets": TICKETS_REL,
        "ticket": "AN10, authored inside the private network",
        "provenance": {
            "kind": "declared",
            "declared_by": configuration.declared_by,
            "declared_on": configuration.declared_on,
            "declared_status": configuration.declared_status,
            "status_note": (
                "The page map, the page count and the body point size are the operator's "
                "declarations, checked against the derivative's own dry-import inventory before "
                "this register was authored. Every hash, count and verdict below is derived from "
                "a stage record bound by hash, except the pipeline revision, which is declared."
            ),
            "configuration_input": {
                "file": configuration.path_rel,
                "sha256": configuration.sha256,
                "record_type": CONFIGURATION_RECORD_TYPE,
                "checked_against": configuration.measurement_rel,
                "checked_by": "runner/original_configuration.py",
            },
            "current_assessment_artifact": {
                "path": revision.pdf_rel.as_posix(),
                "sha256": candidate_sha256,
                "pages": pages,
                "kind": "an anonymised derivative of the Part B as submitted",
                "is_submitted_document": False,
                "derived_from": {
                    "route": DERIVATION_ROUTE,
                    "original_sha256": original_sha256,
                    "edit_route": intake.record.get("route"),
                    "intake": _binding(intake, ai.RECORD_TYPE),
                    "declared_status": "Confirmed",
                    "basis": (
                        "the A0 intake record pinned the original by the hash the operator "
                        "declared from the authoritative source, and the stage chain the "
                        "structural fidelity report checked leads from it to this file"
                    ),
                },
                "statement": (
                    "This file is not the text the ESR evaluated. A result over it is a result "
                    "over the derivative; what it says about the original is the score-fidelity "
                    "measurement's (A8), not this register's."
                ),
            },
            "derivation": {
                "pipeline_revision": {
                    "value": derivation.pipeline_revision,
                    "declared_status": "Assumed",
                    "basis": (
                        "operator declaration in the configuration input. No stage record "
                        "carries the code revision it ran under, so nothing here checks it."
                    ),
                },
                "policy": {
                    "file": policy_rel,
                    "schema": ap.SCHEMA,
                    "version": policy.version,
                    "sha256": policy.sha256,
                    "declared_status": "Confirmed",
                    "basis": (
                        "the policy read under the private root hashes to the policy the "
                        "structural fidelity report and every stage log ran under"
                    ),
                },
                "stage_logs": stage_rows,
                "structural_fidelity": {
                    **_binding(report, af.RECORD_TYPE),
                    "verdict": report.record.get("verdict"),
                    "counts": _field(report.record, "the A6 report", "counts"),
                },
            },
            "transformation": {
                "applied": True,
                "declared_status": "Confirmed",
                "basis": (
                    "derived: the stage chain leads from the authenticated original to this file "
                    "and records every edit"
                ),
                "identifiers": identifiers,
                "citations": (
                    "kept: the count and position of every citation marker the policy keeps; a "
                    "self-citation became a neutral marker, which resolves to no source"
                ),
                "citation_markers": _citation_markers(
                    report.record, reference, derivative_inventory
                ),
                "prose": "unchanged except at the spans the stage logs record",
                "figures": _figures(report.record),
                "table_1_4_1": table,
                "reflow": _reflow(report.record, pages),
                "statement": (
                    "This block says what the anonymisation did to the original on its way to "
                    "the assessed file. It is not a declaration that nothing identifying "
                    "remains: that is the re-identification check's (A5) and the operator's "
                    "acceptance's (A7)."
                ),
            },
            "relationship_to_esr": {
                "statement": (
                    "The ESR evaluated the original, not this file. A difference between a "
                    "result over the derivative and the ESR's own may come from the "
                    "anonymisation, from what the extraction lost, from assessor variance or "
                    "from the profile; the score-fidelity measurement (A8) separates the first."
                ),
            },
            "storage": {
                "stored_in_the_public_repository": False,
                "basis": (
                    "measured: the private root this register is authored under resolves outside "
                    "the repository the tool belongs to, and no argument moves where that is"
                ),
                "consequence": (
                    "the register stays beside the derivative until A7 accepts it, and leaves "
                    "the private network only with it"
                ),
            },
            "inputs": inputs,
        },
        "derived": derived,
        "declared": _declared_half(root, revision, config, derived),
    }
