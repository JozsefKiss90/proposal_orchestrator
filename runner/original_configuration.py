"""The configuration of a document this repository does not hold (V17).

V17 of ``plans/msca_dn_historical_validation_tickets.md``. V07 made every
assumption the importer used to hard-code a field of a selectable document
configuration, and V08 built the dry import that measures a document before it
is imported. Between the two there is a gap: the five fields the official
original still needs — its page map, its page count, its body point size, its
work-package layout and its graph root — are facts about a PDF held in a
private network, and declaring them in this repository would put them here.

So they are declared in a file the operator authors privately, and this module
reads it. Nothing in it reaches this repository: the reader runs where the
document is, and the only thing it ever writes is an exit code.

What the input is
-----------------
One JSON record, :data:`RECORD_TYPE`, holding what an operator measured from
the document in front of them and nothing a tool could have derived. Every path
in it is relative to the private root it sits under, so the record names no
absolute path on the operator's machine and no directory in this repository.

What a declaration is checked against
-------------------------------------
A declaration nobody checks is a value the import then trusts. Every field here
is measurable from the PDF the dry import already measured, so :func:`check`
reads that measurement back and compares:

* the inventory's own bytes, against the hash the input records for it, so the
  configuration is bound to one measurement rather than to whichever file sits
  at the path today;
* the authenticated hash, against the PDF the revision declares, so a
  configuration cannot be used to import a file the operator never
  authenticated;
* the declared page count, against the measured one;
* the declared body point size, against the measured distribution;
* every declared marker, against the blocks the measurement reported as
  candidate headings on that page;
* every declared page, against the page count, and every page of the document
  against the map that is meant to cover it.

A page the map does not reach is a finding unless the input declares it, with a
basis. The cover page of a submission is a legitimate answer; silence is not.

A derivative's derivation (AN10)
--------------------------------
The same input completes the anonymised derivative of the original, a third
document, from the derivative's own measurement. That input carries one more
block, ``derivation``: the pipeline revision the derivative came from, and the
paths of the A0 intake record, the policy, the A6 structural-fidelity report
and every stage log. The block is optional here because the original's input
has none; which document needs one is the importer's rule, not this reader's.
Its paths are relative to the private root like every other, and :func:`check`
holds them under it.

What this module does not do
----------------------------
It builds no :class:`~tools.import_external_proposal.DocumentConfig`. A
configuration is a tools-layer object and this is the runner layer, so what
comes out of here is plain data and the importer maps it. It reads no document
record, writes no file, and declares nothing of its own: every value it returns
was in the input or in the measurement.

Constitutional standing: a reader for an authoring tool. It evaluates no gate,
invokes no Claude, writes nothing, coins no ``schema_id``, and invents no fact
(CLAUDE.md §13.3). What it cannot check it reports as unchecked rather than
passing it (§12.2, §12.4).
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Optional, Sequence

#: Schema of a configuration input. Versioned, because the fields an import
#: requires are V07's and may grow.
SCHEMA = "original_document_configuration/1"

#: The ``record_type`` a configuration input must carry.
RECORD_TYPE = "original_document_configuration"

#: The ``record_type`` of the measurement it is checked against
#: (:data:`runner.dry_import.INVENTORY_RECORD_TYPE`, which this module does not
#: import so that a reader can run against an inventory file alone; the test
#: holds the two equal).
INVENTORY_RECORD_TYPE = "dry_import_inventory"

#: Top-level fields every input declares. A missing or blank one is refused and
#: named: an absent answer is not an answer.
REQUIRED_FIELDS: tuple[str, ...] = (
    "config_id",
    "declared_by",
    "declared_on",
    "declared_status",
    "status_note",
    "authenticated_sha256",
    "measurement",
    "dry_import_dir",
    "workspace_rel",
    "declarations_dir_rel",
    "expected_pages",
    "body_point_size",
    "sub_sections",
    "revisions",
)

#: The four statuses CLAUDE.md §12.2 defines, and the only ones an input may
#: declare. A page map reconciled against the PDF may stand Confirmed on that
#: reconciliation; a status outside this set is refused rather than carried
#: into a manifest.
STATUSES: frozenset[str] = frozenset({"Confirmed", "Inferred", "Assumed", "Unresolved"})

#: Fields a declared sub-section carries. ``marker``, ``declared_title`` and
#: ``exact_marker`` may say nothing; the first two are ``None`` for a
#: sub-section the document opens with or labels in its own words.
_SUB_SECTION_FIELDS: tuple[str, ...] = (
    "sub_section_id",
    "section_id",
    "declared_pages",
    "marker",
)

#: Fields a declared revision carries.
_REVISION_FIELDS: tuple[str, ...] = (
    "revision_id",
    "pdf_rel",
    "source_id_prefix",
    "manifest_name",
    "register_rel",
    "candidate_role",
    "candidate_version",
    "summary",
)

#: An unfilled template field. The committed template is every value in angle
#: brackets, so it is refused by the reader as well as by its location.
_PLACEHOLDER = re.compile(r"<[^>]*>")

_SHA256 = re.compile(r"^[0-9a-f]{64}$")

#: A git commit id, abbreviated or full. A branch name is not a revision: it
#: names whatever the branch points at today.
_COMMIT = re.compile(r"^[0-9a-f]{7,40}$")

#: Fields a ``derivation`` block carries, every one required.
_DERIVATION_FIELDS: tuple[str, ...] = (
    "pipeline_revision",
    "intake_record",
    "policy",
    "fidelity_report",
    "stage_logs",
)

#: This repository, resolved from the module's own location rather than from an
#: argument or the working directory. A configuration for the submitted text
#: declares a private root, and what counts as *inside this repository* may not
#: be something a caller supplies (the rule V08 established for the dry import).
THIS_REPOSITORY: Path = Path(__file__).resolve().parents[1]


class ConfigurationRefused(RuntimeError):
    """Refusal: an input is missing a field, malformed, or points into this repository."""


# --------------------------------------------------------------------------- #
# The declaration
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class SubSectionDeclaration:
    """One row of the declared page map."""

    sub_section_id: str
    section_id: str
    declared_pages: tuple[int, int]
    marker: Optional[str]
    declared_title: Optional[str]
    exact_marker: bool

    @property
    def pages(self) -> range:
        return range(self.declared_pages[0], self.declared_pages[1] + 1)

    @property
    def checkable_marker(self) -> bool:
        """Whether the measurement can confirm this row's marker.

        A numbered prefix is a candidate heading the dry import reports. A
        marker that is the whole block — a beneficiary's own heading — is not
        numbered, so the measurement has nothing to match it against and the
        row is reported as unchecked rather than as confirmed.
        """
        return self.marker is not None and not self.exact_marker


@dataclass(frozen=True)
class WorkPackageDeclaration:
    """How the document lays out its work-package table."""

    sub_section_id: str
    header_labels: tuple[str, ...]
    register_declared_labels: tuple[str, ...]
    consequence: str


@dataclass(frozen=True)
class DnTypeDeclaration:
    """Which kind of Doctoral Network the document says it is, and where.

    The copy's register declares this Confirmed because the authoring tool
    finds the phrase on the page the copy declares. A document held elsewhere
    declares its own page, and the renderer checks the phrase there; declaring
    nothing leaves the type Unresolved rather than borrowed from the copy.
    """

    value: str
    marker: str
    page: int


@dataclass(frozen=True)
class RevisionDeclaration:
    """One PDF of the document, and the files its import is keyed by."""

    revision_id: str
    pdf_rel: str
    source_id_prefix: str
    manifest_name: str
    register_rel: str
    candidate_role: str
    candidate_version: str
    summary: str
    expected_pages: Optional[int]
    supersedes: Optional[str]
    change_id: Optional[str]


@dataclass(frozen=True)
class DerivationDeclaration:
    """Where an anonymised derivative came from (AN10).

    The pipeline revision is an operator declaration: no stage record carries
    the code revision it ran under. Every other field is a path the register
    renderer reads and binds by hash.
    """

    pipeline_revision: str
    intake_record: str
    policy: str
    fidelity_report: str
    stage_logs: tuple[str, ...]


@dataclass(frozen=True)
class UnmappedPage:
    """A page the operator declares no sub-section covers, and why."""

    page: int
    basis: str


@dataclass(frozen=True)
class OriginalConfiguration:
    """What an operator declares about a document held outside this repository.

    Plain data. Every path is relative to the private root the input sits
    under, and :func:`check` resolves them against it.
    """

    config_id: str
    declared_by: str
    declared_on: str
    declared_status: str
    status_note: str
    authenticated_sha256: str
    measurement_rel: str
    measurement_sha256: str
    dry_import_dir: str
    workspace_rel: str
    declarations_dir_rel: str
    scorecard_rel: Optional[str]
    """The evaluator scorecard a sub-section with no heading takes its title
    from, or ``None``. Public, and copied into the private root by the
    workspace author: the importer resolves it against the root it is given."""
    expected_pages: int
    body_point_size: str
    marker_page_tolerance: int
    sub_sections: tuple[SubSectionDeclaration, ...]
    criterion_heading_markers: tuple[tuple[str, str, int], ...]
    work_package_layout: Optional[WorkPackageDeclaration]
    dn_type: Optional[DnTypeDeclaration]
    pages_outside_the_map: tuple[UnmappedPage, ...]
    revisions: tuple[RevisionDeclaration, ...]
    path_rel: str
    """Where the input was read from: relative to the private root when
    :func:`load_configuration` was given one, and the file name alone when it
    was not."""
    sha256: str
    """The input's own bytes, so a register can bind the declaration it rendered."""
    derivation: Optional[DerivationDeclaration] = None
    """Where the document was derived from, or ``None`` for a document that was
    not derived by the anonymisation pipeline (AN10)."""

    @property
    def declared_paths(self) -> tuple[tuple[str, str], ...]:
        """Every relative path this configuration declares, with its field name."""
        paths = [
            ("measurement.path", self.measurement_rel),
            *(() if self.scorecard_rel is None else (("scorecard_rel", self.scorecard_rel),)),
            ("dry_import_dir", self.dry_import_dir),
            ("workspace_rel", self.workspace_rel),
            ("declarations_dir_rel", self.declarations_dir_rel),
        ]
        for rev in self.revisions:
            paths.append((f"revisions[{rev.revision_id}].pdf_rel", rev.pdf_rel))
            paths.append((f"revisions[{rev.revision_id}].register_rel", rev.register_rel))
        derivation = self.derivation
        if derivation is not None:
            paths.append(("derivation.intake_record", derivation.intake_record))
            paths.append(("derivation.policy", derivation.policy))
            paths.append(("derivation.fidelity_report", derivation.fidelity_report))
            for index, log in enumerate(derivation.stage_logs):
                paths.append((f"derivation.stage_logs[{index}]", log))
        return tuple(paths)

    @property
    def mapped_pages(self) -> frozenset[int]:
        return frozenset(page for spec in self.sub_sections for page in spec.pages)


# --------------------------------------------------------------------------- #
# Reading: every refusal names the field
# --------------------------------------------------------------------------- #


def _refuse(where: str, message: str) -> ConfigurationRefused:
    return ConfigurationRefused(f"{where}: {message}")


def _text(raw: Mapping[str, Any], field: str, where: str) -> str:
    value = raw.get(field)
    if not isinstance(value, str) or not value.strip():
        raise _refuse(where, f"{field} must be a non-empty string, found {value!r}")
    if _PLACEHOLDER.search(value):
        raise _refuse(
            where,
            f"{field} still carries the template placeholder {value!r}. A placeholder is not a "
            f"declaration: it says a question was printed, not that anybody answered it.",
        )
    return value


def _optional_text(raw: Mapping[str, Any], field: str, where: str) -> Optional[str]:
    if raw.get(field) is None:
        return None
    return _text(raw, field, where)


def _integer(raw: Mapping[str, Any], field: str, where: str) -> int:
    value = raw.get(field)
    if isinstance(value, bool) or not isinstance(value, int):
        raise _refuse(where, f"{field} must be an integer, found {value!r}")
    return value


def _mapping(raw: Mapping[str, Any], field: str, where: str) -> Mapping[str, Any]:
    value = raw.get(field)
    if not isinstance(value, dict):
        raise _refuse(where, f"{field} must be a JSON object, found {type(value).__name__}")
    return value


def _sequence(raw: Mapping[str, Any], field: str, where: str) -> Sequence[Any]:
    value = raw.get(field)
    if not isinstance(value, list):
        raise _refuse(where, f"{field} must be a JSON list, found {type(value).__name__}")
    return value


def _labels(raw: Mapping[str, Any], field: str, where: str) -> tuple[str, ...]:
    items = _sequence(raw, field, where)
    out: list[str] = []
    for index, item in enumerate(items):
        if not isinstance(item, str) or not item.strip():
            raise _refuse(where, f"{field}[{index}] must be a non-empty string, found {item!r}")
        if _PLACEHOLDER.search(item):
            raise _refuse(where, f"{field}[{index}] still carries a template placeholder")
        out.append(item)
    return tuple(out)


def _sha256_field(raw: Mapping[str, Any], field: str, where: str) -> str:
    value = _text(raw, field, where)
    if not _SHA256.match(value):
        raise _refuse(
            where, f"{field} must be 64 lower-case hex digits, found {value!r}"
        )
    return value


def _page_pair(raw: Mapping[str, Any], where: str) -> tuple[int, int]:
    pages = _sequence(raw, "declared_pages", where)
    if len(pages) != 2 or any(isinstance(p, bool) or not isinstance(p, int) for p in pages):
        raise _refuse(where, f"declared_pages must be two integers, found {list(pages)!r}")
    first, last = int(pages[0]), int(pages[1])
    if first < 1 or last < first:
        raise _refuse(
            where,
            f"declared_pages {[first, last]} is not a page range: the first page is 1 or more "
            f"and the last is not before the first",
        )
    return first, last


def _sub_section(raw: Any, index: int, seen: set[str]) -> SubSectionDeclaration:
    where = f"sub_sections[{index}]"
    if not isinstance(raw, dict):
        raise _refuse(where, f"must be a JSON object, found {type(raw).__name__}")
    for field in _SUB_SECTION_FIELDS:
        if field not in raw:
            raise _refuse(where, f"needs a {field!r} field; null is how a marker says none")
    sub_section_id = _text(raw, "sub_section_id", where)
    if sub_section_id in seen:
        raise _refuse(where, f"sub-section {sub_section_id!r} is declared twice")
    seen.add(sub_section_id)
    exact = raw.get("exact_marker", False)
    if not isinstance(exact, bool):
        raise _refuse(where, f"exact_marker must be true or false, found {exact!r}")
    marker = _optional_text(raw, "marker", where)
    if marker is None and exact:
        raise _refuse(
            where,
            "exact_marker is true and no marker is declared; the flag says the marker is the "
            "whole block, so there has to be one",
        )
    return SubSectionDeclaration(
        sub_section_id=sub_section_id,
        section_id=_text(raw, "section_id", where),
        declared_pages=_page_pair(raw, where),
        marker=marker,
        declared_title=_optional_text(raw, "declared_title", where),
        exact_marker=exact,
    )


def _work_package(raw: Any) -> Optional[WorkPackageDeclaration]:
    if raw is None:
        return None
    where = "work_package_layout"
    if not isinstance(raw, dict):
        raise _refuse(
            where,
            f"must be a JSON object or null, found {type(raw).__name__}. Null is the answer for "
            f"a document that carries no work-package table.",
        )
    labels = _labels(raw, "header_labels", where)
    if not labels:
        raise _refuse(where, "declares no header_labels; a layout with no label is no layout")
    declared = _labels(raw, "register_declared_labels", where)
    unknown = [label for label in declared if label not in labels]
    if unknown:
        raise _refuse(
            where,
            f"register_declared_labels names {unknown}, which header_labels does not carry",
        )
    return WorkPackageDeclaration(
        sub_section_id=_text(raw, "sub_section_id", where),
        header_labels=labels,
        register_declared_labels=declared,
        consequence=_text(raw, "consequence", where),
    )


def _dn_type(raw: Any) -> Optional[DnTypeDeclaration]:
    if raw is None:
        return None
    where = "dn_type"
    if not isinstance(raw, dict):
        raise _refuse(
            where,
            f"must be a JSON object or null, found {type(raw).__name__}. Null leaves the network "
            f"type Unresolved, which is an answer; the copy's type is not inherited either way.",
        )
    return DnTypeDeclaration(
        value=_text(raw, "value", where),
        marker=_text(raw, "marker", where),
        page=_integer(raw, "page", where),
    )


def _criterion_headings(raw: Any) -> tuple[tuple[str, str, int], ...]:
    where = "criterion_heading_markers"
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise _refuse(where, f"must be a JSON list, found {type(raw).__name__}")
    out: list[tuple[str, str, int]] = []
    for index, item in enumerate(raw):
        at = f"{where}[{index}]"
        if not isinstance(item, dict):
            raise _refuse(at, f"must be a JSON object, found {type(item).__name__}")
        out.append(
            (
                _text(item, "section_id", at),
                _text(item, "marker", at),
                _integer(item, "page", at),
            )
        )
    return tuple(out)


def _unmapped(raw: Any) -> tuple[UnmappedPage, ...]:
    where = "pages_outside_the_map"
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise _refuse(where, f"must be a JSON list, found {type(raw).__name__}")
    out: list[UnmappedPage] = []
    seen: set[int] = set()
    for index, item in enumerate(raw):
        at = f"{where}[{index}]"
        if not isinstance(item, dict):
            raise _refuse(at, f"must be a JSON object, found {type(item).__name__}")
        page = _integer(item, "page", at)
        if page in seen:
            raise _refuse(at, f"page {page} is declared outside the map twice")
        seen.add(page)
        out.append(UnmappedPage(page=page, basis=_text(item, "basis", at)))
    return tuple(out)


def _derivation(raw: Any) -> Optional[DerivationDeclaration]:
    if raw is None:
        return None
    where = "derivation"
    if not isinstance(raw, dict):
        raise _refuse(where, f"must be a JSON object or null, found {type(raw).__name__}")
    for field in _DERIVATION_FIELDS:
        if field not in raw:
            raise _refuse(where, f"needs a {field!r} field")
    revision = _text(raw, "pipeline_revision", where)
    if not _COMMIT.match(revision):
        raise _refuse(
            where,
            f"pipeline_revision must be a git commit id, 7 to 40 lower-case hex digits, found "
            f"{revision!r}. A branch name says what the branch points at today, not what ran.",
        )
    logs = _labels(raw, "stage_logs", where)
    if not logs:
        raise _refuse(
            where,
            "stage_logs is empty. A derivative is made by at least one logged stage, and the "
            "chain from the original to it is read from those logs.",
        )
    return DerivationDeclaration(
        pipeline_revision=revision,
        intake_record=_text(raw, "intake_record", where),
        policy=_text(raw, "policy", where),
        fidelity_report=_text(raw, "fidelity_report", where),
        stage_logs=logs,
    )


def _revision(raw: Any, index: int, seen: set[str]) -> RevisionDeclaration:
    where = f"revisions[{index}]"
    if not isinstance(raw, dict):
        raise _refuse(where, f"must be a JSON object, found {type(raw).__name__}")
    for field in _REVISION_FIELDS:
        if field not in raw:
            raise _refuse(where, f"needs a {field!r} field")
    revision_id = _text(raw, "revision_id", where)
    if revision_id in seen:
        raise _refuse(where, f"revision {revision_id!r} is declared twice")
    seen.add(revision_id)
    pages = raw.get("expected_pages")
    if pages is not None and (isinstance(pages, bool) or not isinstance(pages, int)):
        raise _refuse(where, f"expected_pages must be an integer or null, found {pages!r}")
    return RevisionDeclaration(
        revision_id=revision_id,
        pdf_rel=_text(raw, "pdf_rel", where),
        source_id_prefix=_text(raw, "source_id_prefix", where),
        manifest_name=_text(raw, "manifest_name", where),
        register_rel=_text(raw, "register_rel", where),
        candidate_role=_text(raw, "candidate_role", where),
        candidate_version=_text(raw, "candidate_version", where),
        summary=_text(raw, "summary", where),
        expected_pages=None if pages is None else int(pages),
        supersedes=_optional_text(raw, "supersedes", where),
        change_id=_optional_text(raw, "change_id", where),
    )


def load_configuration(path: Path, root: Optional[Path] = None) -> OriginalConfiguration:
    """Read and refuse. Nothing is checked against a measurement here.

    Every refusal names the field, because the operator reading it is the one
    who has to answer it.

    With a *root*, the input must sit under it and the record carries its
    path relative to it: every other path it declares is relative to that root,
    so one outside it would be read against a root it does not belong to.
    Without a root, the record carries the file name alone — the directory is
    inside the private network and a record that might be quoted outside it
    carries no path into it (the rule V08 set for the provenance records).
    """
    path = Path(path)
    where = path.name
    relative = path.name
    if root is not None:
        resolved, base = path.expanduser().resolve(), Path(root).expanduser().resolve()
        if base not in resolved.parents:
            raise _refuse(
                where,
                f"does not sit under the private root {base.name!r}. Every path a configuration "
                f"declares is relative to that root, so the configuration belongs under it too.",
            )
        relative = resolved.relative_to(base).as_posix()
    if not path.is_file():
        raise _refuse(where, "is not a file, so there is no configuration to read")
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise _refuse(where, f"is not valid JSON ({exc})") from exc
    if not isinstance(raw, dict):
        raise _refuse(where, f"must hold a JSON object, found {type(raw).__name__}")
    schema = raw.get("schema")
    if schema != SCHEMA:
        raise _refuse(where, f"schema must be {SCHEMA!r}, found {schema!r}")
    record_type = raw.get("record_type")
    if record_type != RECORD_TYPE:
        raise _refuse(where, f"record_type must be {RECORD_TYPE!r}, found {record_type!r}")
    for field in REQUIRED_FIELDS:
        if field not in raw:
            raise _refuse(where, f"needs a {field!r} field")
    measurement = _mapping(raw, "measurement", where)
    sub_sections = _sequence(raw, "sub_sections", where)
    if not sub_sections:
        raise _refuse(
            where,
            "declares no sub-section. A page map is what the import needs from this file, and an "
            "empty map is not one.",
        )
    revisions = _sequence(raw, "revisions", where)
    if not revisions:
        raise _refuse(where, "declares no revision, so it names no PDF to import")
    status = _text(raw, "declared_status", where)
    if status not in STATUSES:
        raise _refuse(
            where,
            f"declared_status {status!r} is not one of {sorted(STATUSES)} (CLAUDE.md §12.2). A "
            f"status outside the four would be carried into an import manifest.",
        )
    tolerance = raw.get("marker_page_tolerance", 0)
    if isinstance(tolerance, bool) or not isinstance(tolerance, int) or tolerance < 0:
        raise _refuse(
            where, f"marker_page_tolerance must be a whole number of pages, found {tolerance!r}"
        )
    for field, null_means in (
        ("work_package_layout", "a document with no work-package table"),
        ("dn_type", "a document whose network type nothing here checks"),
    ):
        if field not in raw:
            raise _refuse(
                where,
                f"needs a {field!r} field; null is the answer for {null_means}, and silence is "
                f"not",
            )
    seen_subs: set[str] = set()
    seen_revs: set[str] = set()
    data = path.read_bytes()
    return OriginalConfiguration(
        config_id=_text(raw, "config_id", where),
        declared_by=_text(raw, "declared_by", where),
        declared_on=_text(raw, "declared_on", where),
        declared_status=_text(raw, "declared_status", where),
        status_note=_text(raw, "status_note", where),
        authenticated_sha256=_sha256_field(raw, "authenticated_sha256", where),
        measurement_rel=_text(measurement, "path", "measurement"),
        measurement_sha256=_sha256_field(measurement, "sha256", "measurement"),
        dry_import_dir=_text(raw, "dry_import_dir", where),
        workspace_rel=_text(raw, "workspace_rel", where),
        declarations_dir_rel=_text(raw, "declarations_dir_rel", where),
        scorecard_rel=_optional_text(raw, "scorecard_rel", where),
        expected_pages=_integer(raw, "expected_pages", where),
        body_point_size=_text(raw, "body_point_size", where),
        marker_page_tolerance=tolerance,
        sub_sections=tuple(
            _sub_section(row, index, seen_subs) for index, row in enumerate(sub_sections)
        ),
        criterion_heading_markers=_criterion_headings(raw.get("criterion_heading_markers")),
        work_package_layout=_work_package(raw.get("work_package_layout")),
        dn_type=_dn_type(raw.get("dn_type")),
        pages_outside_the_map=_unmapped(raw.get("pages_outside_the_map")),
        revisions=tuple(
            _revision(row, index, seen_revs) for index, row in enumerate(revisions)
        ),
        path_rel=relative,
        sha256=hashlib.sha256(data).hexdigest(),
        derivation=_derivation(raw.get("derivation")),
    )


# --------------------------------------------------------------------------- #
# Locations: the private root, and what may not be inside this repository
# --------------------------------------------------------------------------- #


def inside_this_repository(path: Path) -> bool:
    """Whether *path* resolves inside :data:`THIS_REPOSITORY`. Measured."""
    resolved = Path(path).expanduser().resolve()
    return resolved == THIS_REPOSITORY or THIS_REPOSITORY in resolved.parents


def require_private_root(root: Path) -> Path:
    """*root* resolved, refused if it is inside this repository.

    The submitted text's page records, its registers and its graph root stay
    where its bytes are. A root inside this repository would bring them here,
    which is what V08 criterion 6 forbids.
    """
    root = Path(root).expanduser()
    if inside_this_repository(root):
        raise ConfigurationRefused(
            f"the private root {root.name!r} resolves inside this repository "
            f"({THIS_REPOSITORY.name}). The submitted text, its extracted pages, its registers "
            f"and its graph root stay in the private network, and no argument moves where here is."
        )
    return root.resolve()


def _escapes(root: Path, rel: str) -> bool:
    """Whether *rel* leaves *root*, judged before the file has to exist."""
    pure = PurePosixPath(rel.replace("\\", "/"))
    if pure.is_absolute() or ".." in pure.parts:
        return True
    resolved = (root / Path(rel)).resolve()
    return resolved != root and root not in resolved.parents


# --------------------------------------------------------------------------- #
# Checking the declaration against the measurement
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class ConfigurationCheck:
    """What the measurement says about the declaration.

    ``findings`` is empty only when every declared value the measurement can
    reach agrees with it. ``unchecked`` lists what it cannot reach, so nothing
    passes by having had no test.
    """

    config_id: str
    measurement_rel: str
    measurement_sha256: str
    measured_pages: Optional[int]
    declared_pages: int
    mapped_pages: int
    findings: tuple[tuple[str, str], ...]
    unchecked: tuple[tuple[str, str], ...]

    @property
    def green(self) -> bool:
        return not self.findings

    def lines(self) -> list[str]:
        """The check as an operator reads it: field names and verdicts, no values."""
        out = [
            f"configuration: {self.config_id}",
            f"measurement: {self.measurement_rel} sha256:{self.measurement_sha256[:12]}…",
            f"pages: declared {self.declared_pages}, measured {self.measured_pages}, "
            f"mapped {self.mapped_pages}",
        ]
        out.append(f"findings: {len(self.findings)}")
        out.extend(f"  - {name}: {detail}" for name, detail in self.findings)
        out.append(f"unchecked: {len(self.unchecked)}")
        out.extend(f"  - {name}: {detail}" for name, detail in self.unchecked)
        return out


def _read_inventory(path: Path) -> Mapping[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(raw, dict):
        raise _refuse(path.name, "must hold a JSON object")
    return raw


def check(configuration: OriginalConfiguration, root: Path) -> ConfigurationCheck:
    """Compare *configuration* with the measurement it names, under *root*.

    *root* is the private root every declared path is relative to. It is
    refused if it is inside this repository, before anything is read.
    """
    root = require_private_root(root)
    findings: list[tuple[str, str]] = []
    unchecked: list[tuple[str, str]] = []

    def finding(name: str, detail: str) -> None:
        findings.append((name, detail))

    # One rule covers both locations: the root is outside this repository, so a
    # path that stays under the root is outside it too, symlinks included —
    # ``_escapes`` resolves before it compares.
    for field, rel in configuration.declared_paths:
        if _escapes(root, rel):
            finding(
                "path_outside_the_private_root",
                f"{field} is {rel!r}, which does not resolve under the private root. Every path "
                f"a configuration declares is relative to that root, which is itself outside "
                f"this repository.",
            )

    inventory: Optional[Mapping[str, Any]] = None
    measurement = root / Path(configuration.measurement_rel)
    if not measurement.is_file():
        finding(
            "measurement_absent",
            f"{configuration.measurement_rel} is not a file. The declaration is checked against "
            f"the dry import's inventory, so the inventory has to be there.",
        )
    else:
        measured_hash = hashlib.sha256(measurement.read_bytes()).hexdigest()
        if measured_hash != configuration.measurement_sha256:
            finding(
                "measurement_is_not_the_one_declared",
                f"{configuration.measurement_rel} hashes to {measured_hash[:12]}… and the "
                f"configuration records {configuration.measurement_sha256[:12]}…",
            )
        else:
            try:
                inventory = _read_inventory(measurement)
            except (json.JSONDecodeError, ConfigurationRefused) as exc:
                finding("measurement_unreadable", str(exc))
            if inventory is not None and inventory.get("record_type") != INVENTORY_RECORD_TYPE:
                finding(
                    "measurement_is_not_a_dry_import",
                    f"{configuration.measurement_rel} carries record_type "
                    f"{inventory.get('record_type')!r}, not {INVENTORY_RECORD_TYPE!r}",
                )
                inventory = None

    measured_pages: Optional[int] = None
    if inventory is not None:
        if inventory.get("sha256") != configuration.authenticated_sha256:
            finding(
                "measurement_measured_another_file",
                "the inventory's sha256 is not the authenticated hash this configuration "
                "declares, so the page map was declared from a measurement of another file",
            )
        pages = inventory.get("pages")
        if isinstance(pages, int) and not isinstance(pages, bool):
            measured_pages = pages
            if pages != configuration.expected_pages:
                finding(
                    "page_count_disagrees_with_the_measurement",
                    f"expected_pages is {configuration.expected_pages} and the measurement read "
                    f"{pages}",
                )
        _check_body_size(configuration, inventory, finding)
        _check_markers(configuration, inventory, finding, unchecked)

    _check_map(configuration, measured_pages, finding)
    _check_revisions(configuration, root, finding, unchecked)

    layout = configuration.work_package_layout
    if layout is not None:
        declared = {spec.sub_section_id for spec in configuration.sub_sections}
        if layout.sub_section_id not in declared:
            finding(
                "work_package_sub_section_not_in_the_map",
                f"the work-package table is declared on sub-section "
                f"{layout.sub_section_id!r}, which the page map does not carry",
            )
    else:
        unchecked.append(
            (
                "work_package_layout_declared_as_none",
                "no work-package table is declared, so no header flattening is measured for this "
                "document and the audit parser reads none",
            )
        )

    return ConfigurationCheck(
        config_id=configuration.config_id,
        measurement_rel=configuration.measurement_rel,
        measurement_sha256=configuration.measurement_sha256,
        measured_pages=measured_pages,
        declared_pages=configuration.expected_pages,
        mapped_pages=len(configuration.mapped_pages),
        findings=tuple(findings),
        unchecked=tuple(unchecked),
    )


def _check_body_size(
    configuration: OriginalConfiguration,
    inventory: Mapping[str, Any],
    finding: Any,
) -> None:
    """The declared body size, against the sizes the measurement counted."""
    sizes = inventory.get("point_sizes")
    distribution = sizes.get("distribution") if isinstance(sizes, dict) else None
    if not isinstance(distribution, dict) or not distribution:
        finding(
            "point_sizes_not_measured",
            "the inventory carries no point-size distribution, so the declared body size stands "
            "against nothing",
        )
        return
    if configuration.body_point_size not in distribution:
        finding(
            "body_point_size_not_measured",
            f"body_point_size is {configuration.body_point_size!r} and the measurement counted "
            f"no character at that size; it counted {sorted(distribution)}",
        )
        return
    largest = max(distribution.items(), key=lambda kv: (kv[1], kv[0]))[0]
    if largest != configuration.body_point_size:
        finding(
            "body_point_size_is_not_the_largest_share",
            f"body_point_size is {configuration.body_point_size!r} and the largest share of "
            f"characters is at {largest!r}. The importer reports every other size as a "
            f"deviation, so declaring the smaller share reports the body as deviant.",
        )


def _check_markers(
    configuration: OriginalConfiguration,
    inventory: Mapping[str, Any],
    finding: Any,
    unchecked: list[tuple[str, str]],
) -> None:
    """Every declared marker, against the candidate headings on its page."""
    candidates = inventory.get("heading_candidates")
    if not isinstance(candidates, list):
        finding(
            "heading_candidates_not_measured",
            "the inventory reports no candidate heading, so no declared marker stands against a "
            "measurement",
        )
        return
    by_marker: dict[str, set[int]] = {}
    for item in candidates:
        if not isinstance(item, dict):
            continue
        marker = item.get("marker")
        if not isinstance(marker, str):
            continue
        spans = item.get("pages")
        on_pages: list[Any] = spans if isinstance(spans, list) else [item.get("page")]
        by_marker.setdefault(marker, set()).update(
            page for page in on_pages if isinstance(page, int) and not isinstance(page, bool)
        )
    tolerance = configuration.marker_page_tolerance
    for spec in configuration.sub_sections:
        if spec.marker is None:
            unchecked.append(
                (
                    "sub_section_opens_the_document",
                    f"{spec.sub_section_id} declares no marker, so its start page is the "
                    f"operator's reading and not a measured block",
                )
            )
            continue
        if not spec.checkable_marker:
            unchecked.append(
                (
                    "marker_is_a_whole_block",
                    f"{spec.sub_section_id} declares the exact block {spec.marker!r}, which the "
                    f"measurement does not report as a numbered candidate heading",
                )
            )
            continue
        start = spec.declared_pages[0]
        pages = by_marker.get(spec.marker)
        if pages is None:
            finding(
                "marker_not_measured_anywhere",
                f"{spec.sub_section_id} declares the marker {spec.marker!r}, which opens no "
                f"candidate heading in the measurement",
            )
            continue
        allowed = set(range(start - tolerance, start + 1))
        if not pages & allowed:
            finding(
                "marker_not_on_its_declared_page",
                f"{spec.sub_section_id} declares {spec.marker!r} on p. {start} and the "
                f"measurement found it on {sorted(pages)}, outside the declared tolerance of "
                f"{tolerance} page(s)",
            )
    for section_id, marker, page in configuration.criterion_heading_markers:
        pages = by_marker.get(marker)
        if pages is None:
            finding(
                "criterion_heading_not_measured",
                f"section {section_id} declares the criterion heading {marker!r}, which opens no "
                f"candidate heading in the measurement",
            )
        elif page not in pages:
            finding(
                "criterion_heading_not_on_its_declared_page",
                f"section {section_id} declares {marker!r} on p. {page} and the measurement "
                f"found it on {sorted(pages)}",
            )


def _check_map(
    configuration: OriginalConfiguration,
    measured_pages: Optional[int],
    finding: Any,
) -> None:
    """The page map, against the page count and against itself."""
    limit = measured_pages if measured_pages is not None else configuration.expected_pages
    previous: Optional[tuple[int, str]] = None
    for spec in configuration.sub_sections:
        first, last = spec.declared_pages
        if last > limit:
            finding(
                "sub_section_page_beyond_the_document",
                f"{spec.sub_section_id} is declared on pp. {first}-{last} and the document has "
                f"{limit} page(s)",
            )
        if previous is not None and first < previous[0]:
            finding(
                "page_map_is_not_in_document_order",
                f"{spec.sub_section_id} starts on p. {first}, before {previous[1]} which starts "
                f"on p. {previous[0]}. The map is the document's own order.",
            )
        previous = (first, spec.sub_section_id)
    mapped = configuration.mapped_pages
    declared_outside = {row.page for row in configuration.pages_outside_the_map}
    both = sorted(mapped & declared_outside)
    if both:
        finding(
            "page_declared_outside_a_map_that_covers_it",
            f"page(s) {both} are declared outside the map and a sub-section covers them",
        )
    missing = sorted(set(range(1, limit + 1)) - mapped - declared_outside)
    if missing:
        finding(
            "page_in_no_sub_section_and_not_declared",
            f"page(s) {missing} belong to no sub-section. A page nothing covers is read by no "
            f"assessment; declare it under 'pages_outside_the_map' with a basis, or extend the "
            f"map.",
        )
    dn = configuration.dn_type
    if dn is not None and not 1 <= dn.page <= limit:
        finding(
            "dn_type_page_beyond_the_document",
            f"the network type is declared on p. {dn.page} and the document has {limit} page(s)",
        )
    beyond = sorted(page for page in declared_outside if page > limit)
    if beyond:
        finding(
            "page_declared_outside_the_document",
            f"page(s) {beyond} are declared outside the map and beyond the document's {limit} "
            f"page(s)",
        )


def _check_revisions(
    configuration: OriginalConfiguration,
    root: Path,
    finding: Any,
    unchecked: list[tuple[str, str]],
) -> None:
    """Each declared PDF, against the hash the operator authenticated."""
    known = {rev.revision_id for rev in configuration.revisions}
    for rev in configuration.revisions:
        if rev.supersedes is not None and rev.supersedes not in known:
            finding(
                "revision_supersedes_an_unknown_revision",
                f"{rev.revision_id} supersedes {rev.supersedes!r}, which this configuration does "
                f"not declare. A document is not hung off another document's version chain.",
            )
        pdf = root / Path(rev.pdf_rel)
        if not pdf.is_file():
            finding(
                "declared_pdf_absent",
                f"revisions[{rev.revision_id}].pdf_rel names {rev.pdf_rel}, which is not a file "
                f"under the private root",
            )
            continue
        measured = hashlib.sha256(pdf.read_bytes()).hexdigest()
        if rev.supersedes is None and measured != configuration.authenticated_sha256:
            finding(
                "declared_pdf_is_not_the_authenticated_file",
                f"revisions[{rev.revision_id}] names a file hashing to {measured[:12]}… and the "
                f"configuration authenticated {configuration.authenticated_sha256[:12]}…. The "
                f"import would read a file the operator did not authenticate.",
            )
        elif rev.supersedes is not None:
            unchecked.append(
                (
                    "later_revision_hash_not_authenticated_here",
                    f"{rev.revision_id} supersedes {rev.supersedes}, and this configuration "
                    f"authenticates the first revision's bytes only",
                )
            )
