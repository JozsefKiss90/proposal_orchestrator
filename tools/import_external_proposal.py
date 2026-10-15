"""Import an MSCA-DN Part B into a pre-evaluation graph root (PE-03, V07).

Ticket PE-03 of ``plans/msca_dn_pre_evaluation_spec.md``: external proposal
import. Seven things, all derived from the stored PDF and the selected document
configuration, so that the import replays byte-equal and nothing is typed where
it could be derived:

1. Extract text per page (:mod:`runner.external_proposal`).
2. Write the 84 page sources, ``SRC-DN-P01`` to ``SRC-DN-P84``, each holding
   that page's text under the source index's replay contract, so a
   ``verified_span`` resolves to a page and an offset (spec §6).
3. Map sections and sub-sections per spec §4.1 and §4.2: three section
   artifacts, fifteen sub-sections anchored ``1.1`` to ``3.2`` and ``4`` to
   ``8``. The heading of each numbered sub-section is the text block that
   starts with its marker on its declared page; ``1.1`` and ``8`` are
   unlabelled in the copy and carry declared titles.
4. Render the tables per decision 8: one pipe-delimited row per table row,
   one paragraph per row, so every row is independently selectable and the
   budget filler never splits one.
5. Extract the audit claim ledger: every sentence of the prose the closed
   claim rule selects, frozen here as ``unconfirmed`` (Unresolved by the
   lookup), with a span locating it in its page source. These are the
   proposal's own assertions with no external source, so none may declare
   ``source_grounded``, which is why the v2 tightening does not bite.
6. Emit a v2 document record through :func:`runner.dev_graph.import_candidate`.
7. Write the fidelity register's derived half: extraction losses per page,
   the figure count, the dependency keyword counts, the table render results
   and the body point-size distribution (spec decision 9).

Plus an import manifest under the workspace's ``dev_graph/imports/`` carrying
the extractor, normalisation, table-rendering and claim-extraction versions
(spec PE-05: a hash of an output cannot name the process that produced it).

Which document, and what it may assume (V07)
--------------------------------------------
Every assumption about the document — its graph root, intake, title, role,
submitted-document flag, page count, section and sub-section maps, criterion
heading anchors, beneficiary marker, work-package table layout, body point
size and source-id spelling — is a field of :class:`DocumentConfig`. Two are
declared: ``SANITISED_DERIVATIVE``, the copy PE-03 imported, and
``OFFICIAL_ORIGINAL``, the submitted text. Select one with ``--document``.

A configuration is selected, never merged. The original inherits no page map,
no 84-page count and no derivative description, and it is not a revision of
the derivative: a revision may only supersede a revision of the same document.
A configuration missing a required field refuses the import and names the
field, so an undeclared assumption can never be silently filled with the
copy's.

A **dry import** (V08) asks for less: the identity fields alone, because the
page map, the page count and the body point size are what it exists to
establish. ``tools/dry_import_original.py`` measures a document under that
weaker set and writes nothing here.

What is declared and what is derived
------------------------------------
Declared: the configuration's page map, heading markers, declared titles,
section grouping, title and role. Derived: every text, every count, every
offset, every hash, the heading texts, the start page of each sub-section, and
the one place the derived start page differs from the declared one (``8``
begins on the last line of p. 75 of the sanitised copy).

Ownership
---------
``tools/author_msca_dn_workspace.py`` (PE-01) owns the workspace skeleton,
the intake and the register's provenance header. This tool owns the source
index, the document record, the manifest and the register's derived half;
the workspace tool renders the register through :func:`derive_register_half`
so the two never disagree on its bytes.

The register's ``declared`` half is the operator's, and neither tool authors
it. Both read it from the revision's declaration input and carry its rows
through unchanged, so a declaration survives this tool's rewrite of the
register (:mod:`tools.fidelity_declarations`, R01).

Run it from the repository root::

    py -3.10 -m tools.import_external_proposal                  # write
    py -3.10 -m tools.import_external_proposal --check          # exit 1 if any file would change
    py -3.10 -m tools.import_external_proposal --environment    # the pinned extraction environment
    py -3.10 -m tools.import_external_proposal --document official_original --describe

The extraction library is pinned by :mod:`runner.extraction_environment`. A
``--check`` run that finds staleness also reports whether the environment is on
that pin, because an off-pin MuPDF build is the one cause of a stale rendering
that no amount of reading the diff explains (V01).

Constitutional standing: an authoring tool, not a runtime component. It
writes Tier 3 and Tier 4 artifacts of one workspace, evaluates no gate,
invokes no Claude, and coins no ``schema_id`` beyond the document snapshot's
own (CLAUDE.md §16.3).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional, Sequence

from runner.atomic_write import atomic_write_text, canonical_json_bytes
from runner.dev_graph.builder import SOURCES_REL
from runner.dev_graph.documents import (
    DOCUMENT_SCHEMA_ID_V2,
    document_node_id,
    import_candidate,
    render_record,
)
from runner.dev_graph.intake import INTAKE_REL, read_esr_intake
from runner.dev_graph.schema import DevGraphError
from runner.extraction_environment import (
    DECISION_REL as EXTRACTION_DECISION_REL,
)
from runner.extraction_environment import (
    MEASURED_PYTHON,
    PINNED_MUPDF,
    PINNED_PYMUPDF,
    add_environment_flag,
    environment_exit_code,
    staleness_notice,
)
from runner.external_proposal import (
    PageExtract,
    Paragraph,
    claim_rule_matches,
    extract_document,
    is_row,
    join_segments,
    locate,
    nonws_len,
    page_accounting,
    parse_row,
    split_sentences,
    versions,
)
from runner.original_configuration import (
    ConfigurationRefused,
    OriginalConfiguration,
    load_configuration,
)
from runner.original_configuration import check as check_configuration
from runner.paths import find_repo_root
from runner.source_index import PAGE_TEXT_METHOD, SOURCE_INDEX_RECORD_TYPE
from tools import author_msca_dn_workspace as ws
from tools.fidelity_declarations import (
    DEFAULT_CONTRACT,
    Contract,
    FidelityDeclarationsError,
    validate_inputs,
)

# --------------------------------------------------------------------------- #
# Constants: the spec's names
# --------------------------------------------------------------------------- #

SPEC_REL = ws.SPEC_REL
SOURCE_DIR_REL = ws.SOURCE_DIR_REL
CANDIDATE_PDF_REL = ws.CANDIDATE_PDF_REL

#: Workspace-relative directory of import manifests, beside ``documents/``.
IMPORTS_REL = Path("docs/tier4_orchestration_state/dev_graph/imports")
MANIFEST_RECORD_TYPE = "external_proposal_import_manifest"

#: How a page source id is spelled from a revision's prefix. A document
#: configuration may declare its own; both sanitised revisions use this one.
SOURCE_ID_TEMPLATE = "{prefix}-P{page:02d}"

#: Keyword counts the register's derived half records (spec §2.7), measured
#: case-insensitively over the collapsed text of every page. A measurement rule
#: over any Part B, not an assumption about one document.
DEPENDENCY_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("dependenc", r"dependenc"),
    ("interdepend", r"interdepend"),
    ("Gantt", r"gantt"),
    ("critical path", r"critical path"),
    ("in WP<n>", r"\bin WP ?\d"),
    ("build(s/ing) (up)on", r"\bbuild(?:s|ing)? (?:up)?on\b"),
)
#: Citation markers the derived half counts (spec §2.8). Zero in the sanitised
#: copy; a count, not an expectation.
CITATION_MARKERS: tuple[tuple[str, str], ...] = (
    ("bracketed_numbers", r"\[\d+(?:\s*[,–-]\s*\d+)*\]"),
    ("doi", r"\b10\.\d{4,}/"),
    ("url", r"https?://|\bwww\."),
    ("author_year", r"\([A-Z][A-Za-z-]+(?: et al\.)?,? (?:19|20)\d{2}[a-z]?\)"),
)

_NUMBERING = re.compile(r"^\d+(?:\.\d+)*\.\s+")

_SCHEMA_REF = (
    "No declared schema. .claude/workflows/system_orchestration/artifact_schema_specification.yaml "
    "carries no schema for an import manifest, and no schema_id is coined for it (CLAUDE.md §16.3). "
    "The shape is fixed by tools/import_external_proposal.py and checked by tests/test_msca_dn_import.py."
)


class ImportRefused(RuntimeError):
    """Refusal: an input is missing, or a document does not have its declared shape."""


# --------------------------------------------------------------------------- #
# The document and its revisions: every assumption, declared (V07)
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class SubSectionSpec:
    """One sub-section of a document's section map (spec §4.1 and §4.2)."""

    sub_section_id: str
    section_id: str
    declared_pages: tuple[int, int]
    """Pages per the document's own page map, declared."""
    marker: Optional[str]
    """The block prefix (``1.2.``) or exact block (``Beneficiary A``) that opens it;
    ``None`` when it opens the document."""
    declared_title: Optional[str] = None
    """A title for an unlabelled sub-section; ``None`` means the heading supplies it."""
    exact_marker: bool = False
    """The marker is the whole block, not a prefix."""


@dataclass(frozen=True)
class WorkPackageLayout:
    """How a document lays out its work-package table.

    The three values are useless apart: the measurement reads the labels inside
    the sub-section and reports the consequence of a collapsed header, so a
    document declares all three or none.
    """

    sub_section_id: str
    """The sub-section whose prose carries the work-package table."""
    header_labels: tuple[str, ...]
    """The label-value lines a header was flattened to, the one a header block
    opens with first. A reader that splits a work package into fields expects
    each label to open its own block."""
    consequence: str
    """What a collapsed header costs a reader of this document."""
    register_declared_labels: tuple[str, ...] = ()
    """The subset of the labels the fidelity register's provenance header names
    as the ones the table was flattened to (PE-01, spec decision 9). The
    register's derived half counts these and reports whether the declaration
    holds, so the subset is fixed by that header and not by this tool."""


@dataclass(frozen=True)
class Revision:
    """One revision of one document, and everything that is keyed by it.

    A revision is a new PDF of the same submission, so every revision of a
    document shares the ``document_id`` and the intake, and differs in its
    bytes, its page texts and therefore its content version. Nothing is shared
    that a span could resolve through: each revision owns its
    ``source_id_prefix``, so a ``verified_span`` of one revision can never
    resolve into another revision's page text.

    What is document-wide rather than per-revision — the title, the page map,
    the page count, the source-id spelling, the intake and the graph root —
    belongs to :class:`DocumentConfig`, not here.
    """

    revision_id: str
    pdf_rel: Path
    source_id_prefix: str
    """``SRC-DN`` for the first import; a revision takes its own prefix so the
    earlier spans keep pointing at the earlier page texts."""
    manifest_name: str
    """File name of the import manifest. The first revision keeps the name it
    was committed under; a later one is suffixed."""
    register_rel: Path
    candidate_role: str
    """The fidelity register's input-table ``role`` for this PDF."""
    candidate_version: str
    """The fidelity register's input-table ``version`` for this PDF."""
    expected_pages: Optional[int] = None
    """Page count of this PDF when it differs from the document's; ``None``
    means the document's declared count. A revision that reflowed to a
    different length must declare it, not have it discovered downstream."""
    supersedes: Optional[str] = None
    """``revision_id`` of the revision this one supersedes, or ``None``. It must
    name a revision of the same document."""
    change_id: Optional[str] = None
    """Plain identifier naming the revision in the document provenance."""
    summary: str = ""
    """What this revision is, in one sentence, for the manifest and register."""


def needs_form_title(spec: SubSectionSpec) -> bool:
    """Whether *spec*'s title has to come from the application form.

    True when the document carries no heading block for it and declares no
    title: either it opens the document, or its marker is the whole block. One
    predicate, because :meth:`DocumentConfig.missing_fields` and
    :func:`build_import` must agree on which sub-sections need a scorecard.
    """
    return (spec.marker is None or spec.exact_marker) and spec.declared_title is None


#: Required fields of a document configuration: a configuration missing any of
#: them cannot be imported, and the refusal names the ones that are missing.
#: ``scorecard_rel`` is required conditionally — only when a declared
#: sub-section has neither a marker nor a declared title, and so takes its
#: title from the application form. ``source_id_template`` is absent because
#: the spelling of a page id is generic rather than a fact about one document;
#: it carries :data:`SOURCE_ID_TEMPLATE` as its default and is still
#: overridable per document.
REQUIRED_DOCUMENT_FIELDS: tuple[str, ...] = (
    "workspace_rel",
    "intake_id",
    "title",
    "role",
    "sections",
    "sub_sections",
    "expected_pages",
    "body_point_size",
    "short_name",
    "page_statement",
    "page_map_declared_from",
    "reader_caveat_key",
    "reader_caveat",
    "first_revision_key",
    "claim_ledger_note",
    "revisions",
)

#: Required fields of a **dry import** (V08): the measurement that precedes the
#: import and produces the page map the import needs. It asks for the
#: document's identity and nothing about its shape, because a page map, a page
#: count and a body point size are what the dry import exists to establish. A
#: document that satisfies this set and not
#: :data:`REQUIRED_DOCUMENT_FIELDS` can be measured and not imported, which is
#: exactly the state the official original is in.
DRY_IMPORT_REQUIRED_FIELDS: tuple[str, ...] = (
    "intake_id",
    "document_id",
    "title",
    "role",
    "short_name",
    "page_statement",
    "page_map_declared_from",
    "reader_caveat_key",
    "reader_caveat",
    "status_note",
)


@dataclass(frozen=True)
class DocumentConfig:
    """One document this tool can import, and every assumption it may make
    about it.

    Before V07 the assumptions below were module constants of the importer, so
    the tool could import exactly one document: a sanitised derivative of 84
    pages, with that copy's page map, that copy's source-id prefix, that copy's
    intake and that copy's description. The official original is a different
    document. It has its own identity, its own role, its own page count, its
    own section boundaries, its own table layout and its own source
    identifiers, and it must establish all of them itself.

    A configuration is selected, never merged. Nothing is inherited from
    another configuration, so an undeclared field is missing rather than
    defaulted to the sanitised copy's value, and :meth:`require_complete`
    refuses the import naming it.

    Two kinds of field live here:

    * **Identity and provenance** — ``workspace_rel`` (the graph root),
      ``intake_id``, ``title``, ``role`` and ``is_submitted_document``. The
      flag is the one that decides whether a result over this document is a
      result over the submission, so no renderer types it.
    * **Shape** — ``sections``, ``sub_sections`` (the page map, markers and
      declared titles included), ``criterion_heading_markers``,
      ``marker_page_tolerance``, ``expected_pages``, ``body_point_size``, the
      work-package table fields, ``scorecard_rel`` and ``source_id_template``.

    ``revisions`` holds the document's own PDFs, oldest first. A revision may
    only supersede a revision of the same document, which is what stops a new
    document from being hung off another document's version chain to reuse it.
    """

    config_id: str
    is_submitted_document: bool
    """``True`` only for the text that was actually submitted."""
    is_anonymised_derivative: bool = False
    """``True`` only for a derivative the anonymisation pipeline made from the
    submitted text (AN10). It chooses that document's register renderer, and a
    document may not be both this and the submitted text."""
    intake_id: Optional[str] = None
    document_id: Optional[str] = None
    """The dev-graph document id every revision of this document shares.

    The intake record owns it for an imported document, and :func:`_document_id`
    still reads it from there. It is declared here as well so that a dry import
    (V08) can author the intake record of a document that has none yet; a test
    holds the two equal, so a drift fails rather than importing one document
    under another's id."""
    title: Optional[str] = None
    role: Optional[str] = None
    workspace_rel: Optional[Path] = None
    """The document's graph root. ``None`` when it is not a location in this
    repository; the configuration then refuses until an operator declares one."""
    sections: tuple[tuple[str, str], ...] = ()
    """``(section_id, title)`` per criterion section, in document order."""
    sub_sections: tuple[SubSectionSpec, ...] = ()
    """The page map: one entry per sub-section, in document order."""
    criterion_heading_markers: tuple[tuple[str, str, int], ...] = ()
    """``(section_id, marker, page)`` per criterion-level heading the document
    carries as its section's own content. Not required: a document that carries
    none declares the empty tuple, and none is a valid answer."""
    marker_page_tolerance: int = 0
    """How many pages before its declared start page a marker may be found on.
    Zero is the default because zero assumes nothing: a marker must be on the
    page the document's own page map declares."""
    expected_pages: Optional[int] = None
    body_point_size: Optional[str] = None
    """The declared body point size; every other size is reported with its text."""
    work_package_layout: Optional[WorkPackageLayout] = None
    """How the document lays out its work-package table, or ``None`` when it
    carries no such table."""
    scorecard_rel: Optional[Path] = None
    """The evaluator scorecard supplying the title of a sub-section the document
    leaves unlabelled."""
    short_name: str = ""
    """How a source record names this document in a phrase: *sub-section 3.1 of
    the sanitised copy*."""
    page_statement: str = ""
    """What one page of this document holds, with a ``{page}`` placeholder. It
    is the sentence a reader of a source record sees, so a derivative says it
    is a derivative here and the submitted text says it is the submitted text."""
    page_map_declared_from: str = ""
    """Where this document's page map was declared from."""
    source_id_template: str = SOURCE_ID_TEMPLATE
    reader_caveat_key: str = ""
    reader_caveat: str = ""
    """What a reader of this document's extracted text must not assume, under
    its own key. Both are required and neither defaults: the derivative's
    caveat is not the original's, and the key that carries it is the
    document's own."""
    first_revision_key: str = ""
    """The manifest key stating that a revision is the document's first. The
    key itself is the document's, because the committed manifests are bound by
    hash into the frozen baseline and cannot be renamed, and because no other
    document may be described in the derivative's vocabulary."""
    claim_ledger_note: str = ""
    """Why this document's claim ledger stands where it does, for the manifest.

    Required and never defaulted (V17). The sentence the copy carries states
    that the sanitisation removed every citation, which is a fact about the
    copy. Rendered into the original's manifest it would assert a sanitisation
    of the submitted text, so each document says this in its own words."""
    import_ticket: str = "PE-03"
    """The ticket under which this document is imported, for the manifest.

    The copy was imported at PE-03 and its manifests are bound by hash, so that
    is the default. The original is imported inside the private network, under
    another ticket, and its manifest says which."""
    configuration_input_rel: Optional[Path] = None
    """The private configuration input this document was completed from, or
    ``None`` for a document declared here in full (V17).

    A handle, not a sentence: ``page_map_declared_from`` names the input in
    prose for a reader, and a renderer needs the file. The register of a
    submitted document reads it back and re-checks it."""
    declarations_dir_rel: Optional[Path] = None
    """Where this document's fidelity declaration inputs live, or ``None`` for
    the public case's directory. The original's are private, so its location is
    declared from outside this repository (V17)."""
    declaration_fields: tuple[str, ...] = ()
    """What each declaration row must state, or ``()`` for the public case's two.

    The copy's operator declares a presence and a transformation. A
    transformation declared about the submitted text would read as a
    sanitisation statement about the document nothing sanitised, so the
    submitted text declares its own fields."""
    declaration_record_type: str = ""
    """The ``record_type`` this document's declaration inputs carry, or ``""``
    for the public case's. A distinct type refuses a file filed under the wrong
    document by its type rather than by its fields."""
    declared_status: str = "Assumed"
    """CLAUDE.md §12.2 status of the values declared here. Assumed by default:
    a title, a role and a page map are operator statements. What the importer
    checks against the stored bytes carries its own Confirmed status where it
    stands, which is why ``status_note`` says which values those are."""
    status_note: str = ""
    revisions: tuple[Revision, ...] = ()
    manifest_records_runtime_environment: bool = False
    """Whether the import manifest carries the pinned extraction environment.
    ``False`` for every manifest already bound by a hash into a frozen
    baseline, which is why V01 could not add the block to them; ``True`` for a
    manifest authored for the first time."""
    summary: str = ""

    # -- declared consistency, checked at construction -- #

    def __post_init__(self) -> None:
        if self.is_submitted_document and self.is_anonymised_derivative:
            raise ImportRefused(
                f"document {self.config_id!r} declares itself both the submitted text and an "
                f"anonymised derivative of it; a document is one or the other"
            )
        if "{prefix}" not in self.source_id_template or "{page" not in self.source_id_template:
            raise ImportRefused(
                f"document {self.config_id!r}: source_id_template must carry a prefix and a page "
                f"placeholder, found {self.source_id_template!r}"
            )
        ids = self.section_ids
        if len(set(ids)) != len(ids):
            raise ImportRefused(f"document {self.config_id!r}: duplicate section id")
        for spec in self.sub_sections:
            if spec.section_id not in ids:
                raise ImportRefused(
                    f"document {self.config_id!r}: sub-section {spec.sub_section_id} names "
                    f"section {spec.section_id!r}, which the configuration does not declare"
                )
        subs = [spec.sub_section_id for spec in self.sub_sections]
        if len(set(subs)) != len(subs):
            raise ImportRefused(f"document {self.config_id!r}: duplicate sub-section id")
        for section_id, _marker, _page in self.criterion_heading_markers:
            if section_id not in ids:
                raise ImportRefused(
                    f"document {self.config_id!r}: a criterion heading names section "
                    f"{section_id!r}, which the configuration does not declare"
                )
        layout = self.work_package_layout
        if layout is not None:
            if self.sub_sections and layout.sub_section_id not in subs:
                raise ImportRefused(
                    f"document {self.config_id!r}: the work-package sub-section "
                    f"{layout.sub_section_id!r} is not in the page map"
                )
            if not layout.header_labels:
                raise ImportRefused(
                    f"document {self.config_id!r}: the work-package layout declares no "
                    f"header labels"
                )
            unknown = [
                label for label in layout.register_declared_labels
                if label not in layout.header_labels
            ]
            if unknown:
                raise ImportRefused(
                    f"document {self.config_id!r}: the register declares the work-package "
                    f"label(s) {unknown}, which the layout does not carry"
                )
        if self.expected_pages is not None and self.expected_pages <= 0:
            raise ImportRefused(f"document {self.config_id!r}: expected_pages must be positive")
        known = {rev.revision_id for rev in self.revisions}
        if len(known) != len(self.revisions):
            raise ImportRefused(f"document {self.config_id!r}: duplicate revision id")
        for field, values in (
            ("source_id_prefix", [r.source_id_prefix for r in self.revisions]),
            ("manifest_name", [r.manifest_name for r in self.revisions]),
            ("pdf_rel", [r.pdf_rel.as_posix() for r in self.revisions]),
            ("register_rel", [r.register_rel.as_posix() for r in self.revisions]),
        ):
            if len(set(values)) != len(values):
                raise ImportRefused(f"document {self.config_id!r}: two revisions share a {field}")
        for rev in self.revisions:
            if rev.supersedes is not None and rev.supersedes not in known:
                raise ImportRefused(
                    f"document {self.config_id!r}: revision {rev.revision_id!r} supersedes "
                    f"{rev.supersedes!r}, which is not a revision of this document. A document is "
                    f"not hung off another document's version chain."
                )

    # -- the shape, resolved -- #

    @property
    def section_ids(self) -> tuple[str, ...]:
        return tuple(section_id for section_id, _title in self.sections)

    def criterion_heading(self, section_id: str) -> Optional[tuple[str, int]]:
        """``(marker, page)`` of *section_id*'s criterion-level heading, or ``None``."""
        for sid, marker, page in self.criterion_heading_markers:
            if sid == section_id:
                return marker, page
        return None

    def source_id_format(self, revision: Revision) -> str:
        return self.source_id_template.replace("{prefix}", revision.source_id_prefix)

    def source_id(self, revision: Revision, page: int) -> str:
        return self.source_id_format(revision).format(page=page)

    def expected_pages_of(self, revision: Revision) -> int:
        """*revision*'s declared page count, or the document's."""
        pages = revision.expected_pages
        pages = pages if pages is not None else self.expected_pages
        if pages is None:
            raise ImportRefused(
                f"document {self.config_id!r}: neither the document nor revision "
                f"{revision.revision_id!r} declares expected_pages"
            )
        return pages

    # -- the revisions -- #

    def revision_by_id(self, revision_id: str) -> Revision:
        for rev in self.revisions:
            if rev.revision_id == revision_id:
                return rev
        raise ImportRefused(
            f"unknown revision {revision_id!r} for document {self.config_id!r}; "
            f"known: {[r.revision_id for r in self.revisions]}"
        )

    @property
    def active_revision(self) -> Revision:
        """The revision a new assessment reads: the one no other supersedes."""
        superseded = {r.supersedes for r in self.revisions if r.supersedes is not None}
        current = [r for r in self.revisions if r.revision_id not in superseded]
        if len(current) != 1:
            raise ImportRefused(
                f"document {self.config_id!r}: expected exactly one current revision, found "
                f"{[r.revision_id for r in current]}"
            )
        return current[0]

    # -- paths -- #

    def manifest_rel(self, revision: Revision) -> Path:
        """Repo-relative path of *revision*'s import manifest."""
        return self.require_workspace() / IMPORTS_REL / revision.manifest_name

    def require_intake_id(self) -> str:
        """This document's intake id, or refuse."""
        if self.intake_id is None:
            raise ImportRefused(
                f"document {self.config_id!r} cannot be imported: intake_id not declared, so it "
                f"has no document id of its own."
            )
        return self.intake_id

    def intake_rel(self) -> Path:
        """Repo-relative path of the intake record this document's id comes from."""
        return self.require_workspace() / INTAKE_REL / f"{self.require_intake_id()}.json"

    def declaration_contract(self) -> Contract:
        """Which fidelity declarations this document's registers read (V17).

        Equal to :data:`tools.fidelity_declarations.DEFAULT_CONTRACT` when the
        document declares no part of its own, so the two committed registers
        read exactly what they read before. Each part is declared
        independently, because a document may share a location and not a
        vocabulary.
        """
        return Contract(
            declared_dir_rel=self.declarations_dir_rel,
            declared_fields=self.declaration_fields or None,
            declared_record_type=self.declaration_record_type or None,
        )

    # -- refusals -- #

    def _undeclared(self, required: tuple[str, ...]) -> tuple[str, ...]:
        """Which of *required* this configuration does not declare, in order.

        A falsy value counts as undeclared. Every required field of either set
        is a path, a non-empty name, a non-empty tuple or a positive page
        count, so there is no legitimate falsy declaration among them;
        ``__post_init__`` refuses a zero or negative ``expected_pages``
        separately.
        """
        return tuple(name for name in required if not getattr(self, name))

    def missing_fields(self) -> tuple[str, ...]:
        """Required fields of an import this configuration does not declare."""
        missing = list(self._undeclared(REQUIRED_DOCUMENT_FIELDS))
        if any(needs_form_title(spec) for spec in self.sub_sections) and self.scorecard_rel is None:
            missing.append("scorecard_rel")
        return tuple(missing)

    def require_complete(self) -> None:
        """Refuse unless every required field is declared, naming the missing ones."""
        missing = self.missing_fields()
        if missing:
            raise ImportRefused(
                f"document {self.config_id!r} cannot be imported: "
                f"{', '.join(missing)} not declared. Nothing is inherited from another "
                f"document's configuration, so each is declared from this document itself."
            )

    def dry_import_missing_fields(self) -> tuple[str, ...]:
        """Required fields of a dry import this configuration does not declare.

        A weaker set than :meth:`missing_fields` (V08): a dry import measures
        the document and declares nothing about its shape, so it asks for the
        identity and provenance fields alone. ``()`` means the document can be
        measured, which says nothing about whether it can be imported.
        """
        return self._undeclared(DRY_IMPORT_REQUIRED_FIELDS)

    def require_dry_importable(self) -> None:
        """Refuse unless this document can be measured, naming what is missing."""
        missing = self.dry_import_missing_fields()
        if missing:
            raise ImportRefused(
                f"document {self.config_id!r} cannot be measured: "
                f"{', '.join(missing)} not declared. A dry import needs the document's own "
                f"identity; nothing is inherited from another document's configuration."
            )

    def require_workspace(self) -> Path:
        """This document's graph root, or refuse."""
        if self.workspace_rel is None:
            raise ImportRefused(
                f"document {self.config_id!r} cannot be imported: workspace_rel not declared, "
                f"so it has no graph root to write to."
            )
        return self.workspace_rel

    def require_provenance(self, repo_root: Path) -> None:
        """Refuse unless the intake record this document's id comes from exists.

        The refusal names that record in both cases, including when there is no
        graph root to read it from: what is missing is the document's
        provenance, and saying only that a path field is undeclared would not
        say so.
        """
        intake_id = self.require_intake_id()
        if self.workspace_rel is None:
            raise ImportRefused(
                f"document {self.config_id!r} has no provenance of its own: its intake record "
                f"{intake_id}.json has no graph root to be read from, because workspace_rel is "
                f"not declared."
            )
        intake = self.intake_rel()
        if not (repo_root / intake).is_file():
            raise ImportRefused(
                f"document {self.config_id!r} has no provenance of its own: its intake record "
                f"{intake.as_posix()} does not exist, so it has no document id either."
            )

    def identity(self) -> dict[str, Any]:
        """What this document is, for an operator selecting it."""
        missing = self.missing_fields()
        return {
            "config_id": self.config_id,
            "title": self.title,
            "role": self.role,
            "is_submitted_document": self.is_submitted_document,
            "intake_id": self.intake_id,
            "document_id": self.document_id,
            "workspace_rel": None if self.workspace_rel is None else self.workspace_rel.as_posix(),
            "expected_pages": self.expected_pages,
            "sub_sections_declared": len(self.sub_sections),
            "revisions": [r.revision_id for r in self.revisions],
            "missing_required_fields": list(missing),
            "importable": not missing,
            "missing_dry_import_fields": list(self.dry_import_missing_fields()),
            "measurable": not self.dry_import_missing_fields(),
            "declared_status": self.declared_status,
            "status_note": self.status_note,
            "summary": self.summary,
        }


# --------------------------------------------------------------------------- #
# The documents
# --------------------------------------------------------------------------- #

#: The three criterion sections of an MSCA-DN Part B. They come from the
#: application form (Tier 2A), not from any one document, so both
#: configurations declare the same three; nothing else is shared.
MSCA_DN_PART_B_SECTIONS: tuple[tuple[str, str], ...] = (
    ("excellence_section", "Excellence"),
    ("impact_section", "Impact"),
    ("implementation_section", "Quality and Efficiency of the Implementation"),
)

#: The sanitised copy's page map (spec §4.1 and §4.2). Its last entry carries
#: the beneficiary marker: sub-section 8 is unlabelled in the copy and opens
#: with the first participating organisation's own heading block.
_SANITISED_SUB_SECTIONS: tuple[SubSectionSpec, ...] = (
    SubSectionSpec("1.1", "excellence_section", (1, 13), None, declared_title=None),
    SubSectionSpec("1.2", "excellence_section", (14, 21), "1.2."),
    SubSectionSpec("1.3", "excellence_section", (22, 26), "1.3."),
    SubSectionSpec("1.4", "excellence_section", (27, 31), "1.4."),
    SubSectionSpec("2.1", "impact_section", (32, 33), "2.1."),
    SubSectionSpec("2.2", "impact_section", (34, 35), "2.2."),
    SubSectionSpec("2.3", "impact_section", (36, 38), "2.3."),
    SubSectionSpec("2.4", "impact_section", (39, 40), "2.4."),
    SubSectionSpec("3.1", "implementation_section", (41, 64), "3.1."),
    SubSectionSpec("3.2", "implementation_section", (65, 66), "3.2."),
    SubSectionSpec("4", "implementation_section", (67, 67), "4."),
    SubSectionSpec("5", "implementation_section", (68, 72), "5."),
    SubSectionSpec("6", "implementation_section", (73, 74), "6."),
    SubSectionSpec("7", "implementation_section", (74, 75), "7."),
    SubSectionSpec(
        "8", "implementation_section", (76, 84), "Beneficiary A",
        declared_title="Participating Organisations", exact_marker=True,
    ),
)

_SANITISED_ROLE = (
    "Current assessment artifact: a sanitised derivative of the historical submission, "
    "reflowed from 34 to 84 pages. Not the submitted text."
)

REVISION_ORIGINAL = Revision(
    revision_id="sanitised_v1",
    pdf_rel=SOURCE_DIR_REL / "sanitized_proposal_final.pdf",
    source_id_prefix="SRC-DN",
    manifest_name="MSCA-DN-2025_sanitised_part_b.json",
    register_rel=SOURCE_DIR_REL / "fidelity_register.json",
    candidate_role=_SANITISED_ROLE,
    candidate_version="sanitised derivative, 84 pages (reflow of a 34-page original)",
    summary=(
        "The first sanitised derivative imported at PE-03. Retained unchanged so its "
        "document record, its page texts and every span into them stay reproducible."
    ),
)

REVISION_RESOLVED_FIXES = Revision(
    revision_id="resolved_fixes",
    pdf_rel=SOURCE_DIR_REL / "sanitized_proposal_resolved_fixes.pdf",
    source_id_prefix="SRC-DN-RF",
    manifest_name="MSCA-DN-2025_sanitised_part_b.resolved_fixes.json",
    register_rel=SOURCE_DIR_REL / "fidelity_register_resolved_fixes.json",
    candidate_role=(
        "Current assessment artifact: a revised sanitised derivative of the same historical "
        "submission, reflowed from 34 to 84 pages. Not the submitted text, and not the first "
        "sanitised derivative either."
    ),
    candidate_version=(
        "revised sanitised derivative, 84 pages (reflow of a 34-page original); supersedes the "
        "first sanitised derivative"
    ),
    supersedes="sanitised_v1",
    change_id="msca-dn-2025-sanitised-resolved-fixes",
    summary=(
        "A revised sanitised derivative of the same submission. The page count, the section "
        "boundaries and 83 of the 84 page texts are unchanged; page 45 was re-typeset."
    ),
)

#: The sanitised derivative of the 2025 MSCA-DN submission: the document PE-03
#: imported, with both of its revisions. Every value here was a constant of
#: this module before V07.
SANITISED_DERIVATIVE = DocumentConfig(
    config_id="sanitised_derivative",
    is_submitted_document=False,
    intake_id=ws.INTAKE_ID,
    document_id=ws.DOCUMENT_ID,
    title="Sanitised derivative of the MSCA-DN 2025 Part B (PROJECT-X)",
    role=_SANITISED_ROLE,
    workspace_rel=ws.WORKSPACE_REL,
    sections=MSCA_DN_PART_B_SECTIONS,
    sub_sections=_SANITISED_SUB_SECTIONS,
    # The one criterion-level heading the copy carries; it is the section's own
    # content and must be followed immediately by the first sub-section heading.
    criterion_heading_markers=(("implementation_section", "3.", 41),),
    # A marker is searched on its declared start page and the page before it:
    # 8's opening block is the last line of p. 75 while §4.1 says 76.
    marker_page_tolerance=1,
    expected_pages=84,
    body_point_size="12.0",
    work_package_layout=WorkPackageLayout(
        sub_section_id="3.1",
        header_labels=(
            "WP Number:", "WP title:", "Start month", "Lead participant", "Participants",
            "DCs involved",
        ),
        register_declared_labels=("WP Number:", "WP title:", "Lead participant"),
        consequence=(
            "A work package whose labels ran into its 'WP Number:' block has no separate "
            "'WP title:', 'Lead participant', 'Participants' or 'DCs involved' block. The text is "
            "all there; a reader that splits a work package by its label blocks alone does not see "
            "that work package's fields and may report it as undescribed."
        ),
    ),
    scorecard_rel=Path("harness/evaluator_scorecard_msca_dn.json"),
    short_name="the sanitised copy",
    page_map_declared_from=f"{ws.SPEC_REL} §4.1",
    page_statement=(
        "Page {page} of the sanitised derivative stored in this repository. "
        "Not the submitted text (fidelity register, provenance)."
    ),
    reader_caveat_key="not_the_submitted_text",
    reader_caveat=(
        "This is a sanitised derivative. Figures are absent and citations were removed, so no "
        "judgment of evidence base, length or page-limit compliance is admissible from it."
    ),
    first_revision_key="is_the_first_sanitised_derivative",
    claim_ledger_note=(
        "These are the proposal's own assertions. The sanitisation removed every citation "
        "(spec §2.8), so no claim has an external source and none declares source_grounded; "
        "the span locates the assertion in its page source and is not evidence for it. "
        "Nobody in this repository approves a proposal's assertions, so approval is not applicable. "
        "The integrity audit (PE-07) enumerates this ledger and reports each claim Unresolved."
    ),
    declared_status="Assumed",
    status_note=(
        "The title, role, short name, page statement, reader caveat and page map are operator "
        "declarations (spec PE-01, decision 18). The page count, the body point size, the "
        "work-package layout and every start page are re-derived from the stored PDF by the "
        "importer and re-derived again by tests/test_msca_dn_import.py, so each stands Confirmed "
        "where it is measured. The register records both halves side by side."
    ),
    revisions=(REVISION_ORIGINAL, REVISION_RESOLVED_FIXES),
    manifest_records_runtime_environment=False,
    summary=(
        "The copy PROJECT-X's acronym stands in for the real one. Two revisions, both 84 pages; "
        "the second re-typeset page 45. Both manifests are bound by hash into the frozen 74.60 "
        "baseline, so neither may gain a field."
    ),
)

#: The official 2025 submission. Declared so that it can never be imported
#: under the sanitised copy's page map, page count, body size or description:
#: it inherits none of them, and selecting it refuses until an operator
#: declares each from the original itself (V08). Its graph root is deliberately
#: undeclared — the original and the text extracted from it stay in the private
#: network and are not committed to this repository.
OFFICIAL_ORIGINAL = DocumentConfig(
    config_id="official_original",
    is_submitted_document=True,
    intake_id="msca-dn-2025-original",
    document_id="MSCA-DN-2025_part_b_as_submitted",
    title="MSCA-DN 2025 Part B, as submitted",
    role=(
        "Current assessment artifact: the Part B of the 2025 MSCA Doctoral Networks "
        "submission, as submitted. The submitted text itself."
    ),
    workspace_rel=None,
    sections=MSCA_DN_PART_B_SECTIONS,
    short_name="the Part B as submitted",
    page_map_declared_from=(
        "the V08 dry-import reconciliation against the PDF, page by page. No page map is "
        "declared here yet, which is why selecting this document refuses."
    ),
    first_revision_key="is_the_first_version_of_the_original",
    claim_ledger_note=(
        "These are the proposal's own assertions, extracted from the submitted text. No claim "
        "declares source_grounded: resolving a citation to its source is the imported-source "
        "grounding route of ticket X01, which has not landed, so a citation this document "
        "carries is not resolved here. The span locates the assertion in its page source and is "
        "not evidence for it. Nobody in this repository approves a proposal's assertions, so "
        "approval is not applicable. The integrity audit enumerates this ledger and reports each "
        "claim Unresolved."
    ),
    import_ticket="PE-09 stage A step 1, under V17; run inside the private network",
    declaration_fields=("presence", "extraction_fidelity"),
    declaration_record_type="extraction_fidelity_declarations",
    declared_status="Assumed",
    status_note=(
        "Every value here is an operator declaration about a document this repository does not "
        "hold. Nothing has been derived from the original, so no value is Confirmed and none can "
        "be until V08's dry import measures it."
    ),
    page_statement=(
        "Page {page} of the Part B submitted to the 2025 MSCA Doctoral Networks call. The "
        "submitted text itself, held in the private network and not in this repository."
    ),
    reader_caveat_key="the_submitted_text_itself",
    reader_caveat=(
        "This is the submitted text. What its extraction loses is therefore unknown until the "
        "V08 dry import has been reconciled against the PDF page by page, and nothing here "
        "declares that reconciliation done."
    ),
    manifest_records_runtime_environment=True,
    summary=(
        "Not imported. Its page map, page count, body point size, work-package layout, graph "
        "root and revisions are undeclared, and no value is taken from the sanitised copy. It is "
        "a document of its own and not a descendant of the derivative: its intake id differs, "
        "and a revision of one document may not supersede a revision of another."
    ),
)

#: The anonymised derivative of the 2025 submission (AN10): a third document,
#: made from the authenticated original by the anonymisation pipeline inside
#: the private network. It is neither the submitted text nor the sanitised
#: copy, and it inherits nothing from either: its page map, page count, body
#: point size, graph root and revisions come from its own measurement, through
#: a private configuration input (V17), and its register is its own renderer's.
ANONYMISED_DERIVATIVE = DocumentConfig(
    config_id="anonymised_derivative",
    is_submitted_document=False,
    is_anonymised_derivative=True,
    intake_id="msca-dn-2025-anonymised-derivative",
    document_id="MSCA-DN-2025_part_b_anonymised_derivative",
    title="Anonymised derivative of the MSCA-DN 2025 Part B",
    role=(
        "Current assessment artifact: an anonymised derivative of the Part B as submitted, made "
        "from the authenticated original by the anonymisation pipeline. Not the submitted text."
    ),
    workspace_rel=None,
    sections=MSCA_DN_PART_B_SECTIONS,
    short_name="the anonymised derivative",
    page_map_declared_from=(
        "the dry import of the derivative itself, through a private configuration input. No "
        "page map is declared here, which is why selecting this document refuses until one is "
        "applied."
    ),
    first_revision_key="is_the_first_anonymised_derivative",
    claim_ledger_note=(
        "These are the proposal's own assertions, extracted from an anonymised derivative of "
        "the submitted text. No claim declares source_grounded: the derivative keeps the count "
        "and position of every citation marker, and a self-citation became a neutral marker "
        "that resolves to no source. The span locates the assertion in its page source and is "
        "not evidence for it. Nobody in this repository approves a proposal's assertions, so "
        "approval is not applicable. The integrity audit enumerates this ledger and reports "
        "each claim Unresolved."
    ),
    import_ticket="AN14, under V17; the derivative is imported from its own configuration input",
    declaration_fields=("presence", "transformation"),
    declaration_record_type="anonymisation_declarations",
    declared_status="Assumed",
    status_note=(
        "Every value here is an operator declaration about a document this repository does not "
        "hold. Nothing has been derived from the derivative here, so no value is Confirmed and "
        "none can be until its own dry import measures it."
    ),
    page_statement=(
        "Page {page} of an anonymised derivative of the Part B submitted to the 2025 MSCA "
        "Doctoral Networks call. Not the submitted text: names, places and identifiers are "
        "pseudonyms, and the supervisor table is synthetic (fidelity register, derivation)."
    ),
    reader_caveat_key="an_anonymised_derivative_of_the_original",
    reader_caveat=(
        "This is an anonymised derivative of the submitted text. Identifiers are pseudonyms, "
        "Table 1.4.1 is synthetic, and a self-citation is a neutral marker, so no judgment of "
        "who the consortium is or what it cites is admissible from it. Its layout is the "
        "original's only as far as its register's structural fidelity report says."
    ),
    manifest_records_runtime_environment=True,
    summary=(
        "Not imported here. Its page map, page count, body point size, graph root and revisions "
        "are undeclared, and nothing is taken from the sanitised copy or the original. It is a "
        "document of its own: its intake id differs from both, and its register states the "
        "pipeline revision and policy it came from."
    ),
)

#: Every document this tool can be pointed at.
DOCUMENTS: tuple[DocumentConfig, ...] = (
    SANITISED_DERIVATIVE,
    OFFICIAL_ORIGINAL,
    ANONYMISED_DERIVATIVE,
)
#: The document selected when none is named: the one PE-03 imported.
DEFAULT_DOCUMENT: DocumentConfig = SANITISED_DERIVATIVE


def _index_documents() -> dict[str, DocumentConfig]:
    """``revision_id`` to document, refusing any collision between documents.

    Two documents may not share a config id, an intake id, a graph root or a
    revision: a revision resolves to exactly one document, and a shared intake
    or graph root would make one document's page texts resolvable as another's.
    """
    for field in ("config_id", "intake_id", "document_id", "workspace_rel"):
        values = [str(getattr(doc, field)) for doc in DOCUMENTS if getattr(doc, field) is not None]
        if len(set(values)) != len(values):
            raise ImportRefused(f"two documents share a {field}")
    by_revision: dict[str, DocumentConfig] = {}
    for doc in DOCUMENTS:
        for rev in doc.revisions:
            if rev.revision_id in by_revision:
                raise ImportRefused(
                    f"revision {rev.revision_id!r} belongs to two documents: "
                    f"{by_revision[rev.revision_id].config_id!r} and {doc.config_id!r}"
                )
            by_revision[rev.revision_id] = doc
    return by_revision


_DOCUMENT_BY_REVISION: dict[str, DocumentConfig] = _index_documents()


def register_document(config: DocumentConfig) -> DocumentConfig:
    """Make *config*'s revisions resolvable by :func:`config_for` (V17).

    Every renderer resolves a revision to its document through one lookup over
    :data:`DOCUMENTS`, which is how a page map, a page count or a title can
    never be borrowed across documents. A document completed from a private
    input is not in that tuple: its revisions are declared at run time, inside
    the private network, so they are registered here instead.

    Two things this does not allow. A configuration id :data:`DOCUMENTS` does
    not declare cannot be registered, so the registry is still closed over the
    documents this tool knows. And a revision another document already owns
    cannot be taken, so one document's page texts can never resolve as
    another's. The registration lasts for the process, like the completed
    configuration itself.
    """
    if config.config_id not in {doc.config_id for doc in DOCUMENTS}:
        raise ImportRefused(
            f"document {config.config_id!r} is not one this tool declares; known: "
            f"{[d.config_id for d in DOCUMENTS]}"
        )
    for rev in config.revisions:
        owner = _DOCUMENT_BY_REVISION.get(rev.revision_id)
        if owner is not None and owner.config_id != config.config_id:
            raise ImportRefused(
                f"revision {rev.revision_id!r} already belongs to document "
                f"{owner.config_id!r}; a revision resolves to exactly one document"
            )
        _DOCUMENT_BY_REVISION[rev.revision_id] = config
    return config


def complete_from_input(
    config: DocumentConfig, configuration: OriginalConfiguration
) -> DocumentConfig:
    """*config* with the operator's private declarations applied (V17).

    The five fields the official original is missing are facts about a PDF held
    in a private network, so they are declared in a file the operator authors
    there (:mod:`runner.original_configuration`) and applied here. Nothing is
    merged from another document: every value below comes from the input, and
    what the input does not declare stays as this configuration declares it.

    Two refusals keep this from becoming a way to redeclare a committed
    document. The input must name the configuration it completes, and a
    configuration that is already complete may not be completed again: both
    sanitised manifests are bound by hash into the frozen baseline, and the
    page map they were measured under is not a runtime argument.

    ``page_map_declared_from`` and ``status_note`` are rewritten, because the
    sentences this configuration carries say the page map is *not* declared
    yet. Left as they were, the import manifest would state that.
    """
    if configuration.config_id != config.config_id:
        raise ImportRefused(
            f"the configuration input declares document {configuration.config_id!r} and "
            f"{config.config_id!r} is selected. An input completes the document it names."
        )
    if not config.missing_fields():
        raise ImportRefused(
            f"document {config.config_id!r} is already complete, so a configuration input may "
            f"not redeclare it. Its page map, page count and revisions are the ones its "
            f"committed manifests were measured under, and those manifests are bound by hash."
        )
    if config.is_anonymised_derivative and configuration.derivation is None:
        raise ImportRefused(
            f"document {config.config_id!r} is an anonymised derivative and its configuration "
            f"input declares no derivation. Its register states the pipeline revision, the "
            f"policy and the structural fidelity it came from, so the input must name them."
        )
    if not config.is_anonymised_derivative and configuration.derivation is not None:
        raise ImportRefused(
            f"document {config.config_id!r} is not an anonymised derivative and its "
            f"configuration input declares a derivation. Only the derivative was derived."
        )
    layout = configuration.work_package_layout
    completed = replace(
        config,
        workspace_rel=Path(configuration.workspace_rel),
        sub_sections=tuple(
            SubSectionSpec(
                sub_section_id=spec.sub_section_id,
                section_id=spec.section_id,
                declared_pages=spec.declared_pages,
                marker=spec.marker,
                declared_title=spec.declared_title,
                exact_marker=spec.exact_marker,
            )
            for spec in configuration.sub_sections
        ),
        criterion_heading_markers=configuration.criterion_heading_markers,
        marker_page_tolerance=configuration.marker_page_tolerance,
        expected_pages=configuration.expected_pages,
        body_point_size=configuration.body_point_size,
        work_package_layout=(
            None
            if layout is None
            else WorkPackageLayout(
                sub_section_id=layout.sub_section_id,
                header_labels=layout.header_labels,
                register_declared_labels=layout.register_declared_labels,
                consequence=layout.consequence,
            )
        ),
        scorecard_rel=(
            config.scorecard_rel
            if configuration.scorecard_rel is None
            else Path(configuration.scorecard_rel)
        ),
        declarations_dir_rel=Path(configuration.declarations_dir_rel),
        configuration_input_rel=Path(configuration.path_rel),
        revisions=tuple(
            Revision(
                revision_id=rev.revision_id,
                pdf_rel=Path(rev.pdf_rel),
                source_id_prefix=rev.source_id_prefix,
                manifest_name=rev.manifest_name,
                register_rel=Path(rev.register_rel),
                candidate_role=rev.candidate_role,
                candidate_version=rev.candidate_version,
                expected_pages=rev.expected_pages,
                supersedes=rev.supersedes,
                change_id=rev.change_id,
                summary=rev.summary,
            )
            for rev in configuration.revisions
        ),
        declared_status=configuration.declared_status,
        page_map_declared_from=(
            f"{configuration.path_rel} (sha256 {configuration.sha256}), declared by "
            f"{configuration.declared_by} on {configuration.declared_on} from the V08 "
            f"dry-import reconciliation against the PDF"
        ),
        status_note=(
            f"{configuration.status_note} The page count, the body point size, every declared "
            f"marker and the coverage of the page map were checked against the dry-import "
            f"inventory {configuration.measurement_rel} (sha256 "
            f"{configuration.measurement_sha256}) before this import, by "
            f"runner/original_configuration.py. What that check cannot reach it reports as "
            f"unchecked rather than as agreeing."
        ),
    )
    # Every renderer resolves a revision to its document through config_for,
    # and these revisions were declared at run time.
    return register_document(completed)


def document_by_id(config_id: str) -> DocumentConfig:
    for doc in DOCUMENTS:
        if doc.config_id == config_id:
            return doc
    raise ImportRefused(
        f"unknown document {config_id!r}; known: {[d.config_id for d in DOCUMENTS]}"
    )


def config_for(revision: Revision) -> DocumentConfig:
    """The document *revision* belongs to.

    A pure lookup over :data:`DOCUMENTS`. A revision is never interpreted
    against a document that does not declare it, so a page map, a page count or
    a title cannot be borrowed across documents.
    """
    doc = _DOCUMENT_BY_REVISION.get(revision.revision_id)
    if doc is None:
        raise ImportRefused(
            f"revision {revision.revision_id!r} belongs to no declared document; "
            f"known: {sorted(_DOCUMENT_BY_REVISION)}"
        )
    return doc


def revision_by_id(revision_id: str) -> Revision:
    """The revision *revision_id* of whichever document declares it."""
    doc = _DOCUMENT_BY_REVISION.get(revision_id)
    if doc is None:
        raise ImportRefused(
            f"unknown revision {revision_id!r}; known: {sorted(_DOCUMENT_BY_REVISION)}"
        )
    return doc.revision_by_id(revision_id)


# No module-level name holds one document's workspace, intake, title, page
# count, registers or revisions any more: each is read from the selected
# configuration, and :data:`DEFAULT_DOCUMENT` is the one a caller gets when it
# names none. ``render_all`` writes every revision of the selected document, so
# a revision never silently drops the page texts an earlier span resolves into.


# --------------------------------------------------------------------------- #
# Extraction (cached per PDF bytes)
# --------------------------------------------------------------------------- #


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@lru_cache(maxsize=8)
def _extract(pdf: str, sha256: str) -> tuple[PageExtract, ...]:
    return extract_document(Path(pdf))


def extract(repo_root: Path, revision: Revision = REVISION_ORIGINAL) -> tuple[PageExtract, ...]:
    """Every page of *revision*'s PDF, or refuse.

    The page count is checked against the count the revision or its document
    declares, rather than assumed: a revision that reflowed to a different
    length must be declared, not discovered downstream.
    """
    expected = config_for(revision).expected_pages_of(revision)
    pdf = repo_root / revision.pdf_rel
    if not pdf.is_file():
        raise ImportRefused(
            f"candidate missing for revision {revision.revision_id}: {revision.pdf_rel.as_posix()}"
        )
    pages = _extract(str(pdf), _sha256(pdf))
    if len(pages) != expected:
        raise ImportRefused(
            f"candidate {revision.pdf_rel.as_posix()}: expected {expected} pages, "
            f"found {len(pages)}"
        )
    return pages


# --------------------------------------------------------------------------- #
# Section map
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class SubSection:
    spec: SubSectionSpec
    heading: Optional[str]
    """The heading block text, verbatim and collapsed; ``None`` for an unlabelled one."""
    title: str
    paragraphs: tuple[Paragraph, ...]
    start_page: int
    end_page: int

    @property
    def content(self) -> str:
        return "\n\n".join(p.text for p in self.paragraphs)


def _is_marker(p: Paragraph, spec: SubSectionSpec) -> bool:
    if p.kind != "prose" or spec.marker is None:
        return False
    return p.text == spec.marker if spec.exact_marker else p.text.startswith(spec.marker + " ")


def _find_heading(
    paragraphs: Sequence[Paragraph], spec: SubSectionSpec, start_from: int, tolerance: int
) -> int:
    lo = spec.declared_pages[0] - tolerance
    hi = spec.declared_pages[0]
    for i in range(start_from, len(paragraphs)):
        p = paragraphs[i]
        if p.pages[0] > hi:
            break
        if lo <= p.pages[0] <= hi and _is_marker(p, spec):
            return i
    raise ImportRefused(
        f"sub-section {spec.sub_section_id}: no block starting with {spec.marker!r} on pages {lo}-{hi}"
    )


def _title_of(spec: SubSectionSpec, heading: Optional[str]) -> str:
    if spec.declared_title is not None:
        return spec.declared_title
    if heading is None:
        return ""  # unlabelled: filled from the application form by build_import
    return _NUMBERING.sub("", heading, count=1)


def map_sub_sections(
    paragraphs: Sequence[Paragraph], config: DocumentConfig = DEFAULT_DOCUMENT
) -> tuple[tuple[SubSection, ...], dict[str, str]]:
    """Cut the paragraph stream at the headings *config* declares. Returns the
    sub-sections and the criterion-heading content per section
    (``{section_id: heading}``)."""
    cuts: list[tuple[SubSectionSpec, int, Optional[str]]] = []
    cursor = 0
    for spec in config.sub_sections:
        if spec.marker is None:
            cuts.append((spec, 0, None))
            continue
        i = _find_heading(paragraphs, spec, cursor, config.marker_page_tolerance)
        heading = None if spec.exact_marker else paragraphs[i].text
        cuts.append((spec, i, heading))
        cursor = i + 1
    criterion_content: dict[str, str] = {}
    out: list[SubSection] = []
    for n, (spec, i, heading) in enumerate(cuts):
        body_start = i if heading is None else i + 1
        end = cuts[n + 1][1] if n + 1 < len(cuts) else len(paragraphs)
        body = list(paragraphs[body_start:end])
        # A criterion-level heading sits at the end of the previous
        # sub-section's range; it belongs to its section, not to that prose.
        nxt = cuts[n + 1][0] if n + 1 < len(cuts) else None
        criterion = None if nxt is None else config.criterion_heading(nxt.section_id)
        if nxt is not None and criterion is not None and nxt.section_id != spec.section_id:
            marker, page = criterion
            if not body or body[-1].kind != "prose" or not body[-1].text.startswith(marker + " ") \
                    or body[-1].pages[0] != page:
                raise ImportRefused(
                    f"section {nxt.section_id}: the criterion heading {marker!r} on p. {page} is not the "
                    f"block immediately before the {nxt.sub_section_id} heading"
                )
            criterion_content[nxt.section_id] = body.pop().text
        if not body:
            raise ImportRefused(f"sub-section {spec.sub_section_id} has no content")
        out.append(
            SubSection(
                spec=spec,
                heading=heading,
                title=_title_of(spec, heading),
                paragraphs=tuple(body),
                start_page=min(p.pages[0] for p in body) if heading is None else paragraphs[i].pages[0],
                end_page=max(p.pages[-1] for p in body),
            )
        )
    return tuple(out), criterion_content


# --------------------------------------------------------------------------- #
# Claims
# --------------------------------------------------------------------------- #


def extract_claims(
    subs: Sequence[SubSection], pages: Sequence[PageExtract], revision: Revision = REVISION_ORIGINAL
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """The audit claim ledger: one claim per rule-selected sentence, first
    occurrence of a sentence text wins, each with a span into its page."""
    config = config_for(revision)
    by_page = {p.page: p.text for p in pages}
    claims: list[dict[str, Any]] = []
    seen: set[str] = set()
    stats: dict[str, Any] = {
        "sentences": 0, "duplicates_removed": 0, "without_span": 0, "claims_without_span": [], "rules_matched": {},
    }
    rules: dict[str, int] = {}
    for sub in subs:
        n = 0
        for para in sub.paragraphs:
            if para.kind != "prose":
                continue
            for sentence in split_sentences(para.text):
                stats["sentences"] += 1
                matched = claim_rule_matches(sentence)
                if not matched:
                    continue
                if sentence in seen:
                    stats["duplicates_removed"] += 1
                    continue
                seen.add(sentence)
                n += 1
                for r in matched:
                    rules[r] = rules.get(r, 0) + 1
                span: Optional[dict[str, Any]] = None
                for page in para.pages:
                    hit = locate(by_page[page], sentence)
                    if hit is not None:
                        span = {
                            "source_id": config.source_id(revision, page),
                            "start": hit[0],
                            "end": hit[1],
                        }
                        break
                claim_id = f"{sub.spec.sub_section_id}-c{n:03d}"
                if span is None:
                    stats["without_span"] += 1
                    stats["claims_without_span"].append(
                        {"claim_id": claim_id, "pages": list(para.pages), "reason": "the sentence straddles a page break and is in no single page source"}
                    )
                claim: dict[str, Any] = {
                    "claim_id": claim_id,
                    "section_id": sub.spec.section_id,
                    "text": sentence,
                    "evidence_strength": "unconfirmed",
                    "approval": "not_applicable",
                }
                if span is not None:
                    claim["verified_span"] = span
                claims.append(claim)
    stats["rules_matched"] = dict(sorted(rules.items()))
    return claims, stats


# --------------------------------------------------------------------------- #
# The import
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Import:
    revision: Revision
    pages: tuple[PageExtract, ...]
    sub_sections: tuple[SubSection, ...]
    criterion_content: dict[str, str]
    candidate: dict[str, Any]
    claims_stats: dict[str, Any]
    record: dict[str, Any]
    record_rel: str
    """Workspace-relative path of the document record."""

    @property
    def config(self) -> DocumentConfig:
        """The document this import is of."""
        return config_for(self.revision)


def _form_heading(repo_root: Path, config: DocumentConfig, anchor: str) -> str:
    """The application-form heading of *anchor*, from *config*'s scorecard.

    The title of a sub-section the document leaves unlabelled comes from the
    form rather than from the copy, so it is never invented here.
    """
    scorecard = config.scorecard_rel
    if scorecard is None:
        raise ImportRefused(
            f"document {config.config_id!r}: sub-section {anchor} is unlabelled and carries no "
            f"declared title, and the configuration declares no scorecard_rel to take one from"
        )
    sc = json.loads((repo_root / scorecard).read_text(encoding="utf-8-sig"))
    for crit in sc["criteria"]:
        for aspect in crit["aspects"]:
            if aspect.get("anchor") == anchor:
                return str(aspect["af_v6_heading"])
    raise ImportRefused(f"{scorecard.as_posix()}: no aspect anchored {anchor}")


def _document_id(repo_root: Path, config: DocumentConfig) -> str:
    """The document id of *config*, read from its intake record.

    The intake record is authoritative. The configuration declares the id too
    (V08, so a dry import can author an intake record for a document that has
    none), and a drift between the two would import one document under
    another's id, so it is refused here rather than discovered later.
    """
    config.require_provenance(repo_root)
    world = repo_root / config.require_workspace()
    recorded = read_esr_intake(world, config.require_intake_id()).document_id
    if config.document_id is not None and config.document_id != recorded:
        raise ImportRefused(
            f"document {config.config_id!r}: the configuration declares document id "
            f"{config.document_id!r} and its intake record {config.intake_rel().as_posix()} "
            f"holds {recorded!r}. The intake record is authoritative; the declaration exists "
            f"only so a dry import can author one, and it must agree."
        )
    return recorded


def node_id_of(repo_root: Path, revision: Revision) -> str:
    """The dev-graph node id *revision*'s document record has or would have.

    Derived from the revision's own PDF, never typed, so a predecessor
    reference cannot drift from the record it names.
    """
    imp = build_import(repo_root, revision)
    return document_node_id(imp.candidate["document_id"], imp.record["content_version"])


def build_document_provenance(repo_root: Path, revision: Revision) -> Optional[dict[str, Any]]:
    """The provenance *revision*'s record carries, or ``None`` for a first import.

    Uses the engine's own supersession mechanism
    (:func:`runner.dev_graph.revisions.build_provenance`): the predecessor is
    resolved against the built snapshot, so the declared predecessor version
    is the one this build actually holds, and
    :func:`runner.dev_graph.builder.build_snapshot` turns the result into the
    ``supersedes`` edge. A superseded snapshot stops being a current
    candidate, which is what lets the document id keep resolving to exactly
    one version (``harness.blind_assessment.resolve_document``).

    ``change_id`` names the revision. No change record is written for it:
    ``runner.dev_graph.changes.record_change`` accepts only the five Tier 3
    record paths and rebuilds a before/after snapshot pair, so it is neither
    applicable to a replacement source PDF nor replayable inside a byte-equal
    importer. The manifest states this where the id appears.
    """
    if revision.supersedes is None:
        return None
    from runner.dev_graph.builder import build_snapshot
    from runner.dev_graph.revisions import build_provenance

    config = config_for(revision)
    predecessor = config.revision_by_id(revision.supersedes)
    previous_node = node_id_of(repo_root, predecessor)
    snapshot = build_snapshot(repo_root / config.require_workspace())
    return build_provenance(
        snapshot,
        supersedes=previous_node,
        change_id=revision.change_id or revision.revision_id,
        evidence=(),
    )


def build_import(
    repo_root: Path, revision: Revision = REVISION_ORIGINAL, *, with_provenance: bool = True
) -> Import:
    """The whole import of *revision*, derived from its PDF.

    *with_provenance* resolves the superseded snapshot against the built graph,
    which needs the source index on disk. The source index is itself rendered
    from an import, so rendering it uses ``with_provenance=False``: provenance
    is not part of the content version and no source record depends on it, so
    the two renderings agree on everything the index carries.
    """
    config = config_for(revision)
    config.require_complete()
    pages = extract(repo_root, revision)
    paragraphs = join_segments(pages)
    subs, criterion_content = map_sub_sections(paragraphs, config)
    # A sub-section the document carries no heading block for, and declares no
    # title for, takes the application form's heading for its anchor.
    subs = tuple(
        SubSection(
            s.spec, s.heading, _form_heading(repo_root, config, s.spec.sub_section_id),
            s.paragraphs, s.start_page, s.end_page,
        )
        if needs_form_title(s.spec) else s
        for s in subs
    )
    claims, stats = extract_claims(subs, pages, revision)
    sections = []
    for section_id, section_title in config.sections:
        sections.append(
            {
                "section_id": section_id,
                "title": section_title,
                "content": criterion_content.get(section_id, ""),
                "addresses": [],
                "sub_sections": [
                    {"sub_section_id": s.spec.sub_section_id, "title": s.title, "content": s.content}
                    for s in subs
                    if s.spec.section_id == section_id
                ],
            }
        )
    candidate = {
        "document_id": _document_id(repo_root, config),
        "title": config.title,
        "sections": sections,
        "claims": claims,
        "commitments": [],
    }
    record, record_rel = render_record(
        candidate,
        "tools/import_external_proposal.py candidate",
        provenance=build_document_provenance(repo_root, revision) if with_provenance else None,
        schema_id=DOCUMENT_SCHEMA_ID_V2,
    )
    return Import(revision, pages, subs, criterion_content, candidate, stats, record, record_rel)


# --------------------------------------------------------------------------- #
# Rendering: sources, manifest, derived half
# --------------------------------------------------------------------------- #


def _pages_of(sub: SubSection) -> set[int]:
    return {pg for p in sub.paragraphs for pg in p.pages}


def render_source_records(repo_root: Path, imp: Import) -> list[dict[str, Any]]:
    """One ``source`` record per page of *imp*'s revision, in page order."""
    revision = imp.revision
    config = imp.config
    title = config.title
    sha = _sha256(repo_root / revision.pdf_rel)
    claims_by_page: dict[int, list[str]] = {}
    for c in imp.candidate["claims"]:
        span = c.get("verified_span")
        if span:
            page = int(span["source_id"][-2:])
            claims_by_page.setdefault(page, []).append(c["claim_id"])
    subs_by_page: dict[int, list[str]] = {}
    for s in imp.sub_sections:
        for pg in sorted(_pages_of(s)):
            subs_by_page.setdefault(pg, []).append(s.spec.sub_section_id)
    sources = []
    for p in imp.pages:
        carries = subs_by_page.get(p.page, [])
        sources.append(
            {
                "source_id": config.source_id(revision, p.page),
                "title": f"{title}, page {p.page} of {len(imp.pages)}",
                "kind": "call_document_page",
                "kind_note": (
                    "runner.source_index's closed transcription vocabulary has two kinds; this is the "
                    "transcribed one. The page belongs to the candidate proposal (Tier 3 source material), "
                    "not to a call document."
                ),
                "status": "Confirmed",
                "what_the_page_carries": (
                    f"sub-section(s) {', '.join(carries)} of {config.short_name}"
                    if carries else "no mapped sub-section"
                ),
                "citation": {
                    "cited_as": f"{title}, page {p.page}.",
                    "document_id": imp.candidate["document_id"],
                    "page": p.page,
                },
                "resolves_to": {
                    "class": "stored_document",
                    "stored_path": revision.pdf_rel.as_posix(),
                    "stored_path_relative_to": "the repository root, not this graph root (spec decision 2)",
                    "sha256": sha,
                    "document_id": imp.candidate["document_id"],
                    "page": p.page,
                    "what_it_holds": config.page_statement.format(page=p.page),
                },
                "transcription": {
                    "state": "transcribed",
                    "method": PAGE_TEXT_METHOD,
                    "replay": (
                        "runner.source_index.read_page_text(stored_path, page); the import test re-runs "
                        "it and compares byte for byte, so this text cannot drift from the stored file."
                    ),
                },
                "text": p.text,
                "relied_on_for": [
                    {
                        "what": (
                            "The prose of the sub-sections this page carries, and the location of each "
                            "claim the ledger extracted from it."
                        ),
                        "claim_refs": claims_by_page.get(p.page, []),
                        "status": "Confirmed",
                    }
                ],
            }
        )
    return sources


def render_sources(
    repo_root: Path,
    imps: Optional[Sequence[Import]] = None,
    config: DocumentConfig = DEFAULT_DOCUMENT,
) -> dict[str, Any]:
    """The graph root's whole source index: every revision's pages, oldest first.

    One file holds every revision because the dev-graph builder reads exactly
    one ``sources.json`` per graph root. Keeping the earlier revision's records
    in it is what lets the earlier document record keep resolving its spans,
    so a superseded candidate stays reproducible rather than becoming a
    dangling reference.

    One graph root holds one document, so *config* is taken from the imports
    when any are given and every import must be of that document.
    """
    imps = list(
        imps if imps is not None
        else build_imports(repo_root, with_provenance=False, config=config)
    )
    documents = {imp.config.config_id for imp in imps}
    if len(documents) > 1:
        raise ImportRefused(
            f"one source index holds one document; given revisions of {sorted(documents)}"
        )
    if documents and documents != {config.config_id}:
        raise ImportRefused(
            f"the imports are of document {documents.pop()!r} and the index was asked for "
            f"{config.config_id!r}; the two must be the same document"
        )
    sources: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    for imp in imps:
        sources.extend(render_source_records(repo_root, imp))
        candidates.append(
            {
                "revision_id": imp.revision.revision_id,
                "path": imp.revision.pdf_rel.as_posix(),
                "sha256": _sha256(repo_root / imp.revision.pdf_rel),
                "pages": len(imp.pages),
                "source_id_format": imp.config.source_id_format(imp.revision),
                "supersedes_revision": imp.revision.supersedes,
            }
        )
    seen: dict[str, str] = {}
    for src in sources:
        if src["source_id"] in seen:
            raise ImportRefused(
                f"two revisions claim the source id {src['source_id']!r}; a revision needs its own prefix"
            )
        seen[src["source_id"]] = src["resolves_to"]["stored_path"]
    return {
        "record_type": SOURCE_INDEX_RECORD_TYPE,
        "schema_ref": (
            "No declared schema; see docs/tier3_project_instantiation/source_materials/sources.json "
            "for the shape rationale. runner/dev_graph/builder.py asks only for a non-empty source_id "
            "and, if present, a string text."
        ),
        "provenance_class": "derived",
        "artifact_purpose": (
            "The Tier 3 source index of the MSCA-DN pre-evaluation graph root: one source per page of "
            f"each revision of {config.short_name}, each holding that page's extracted text, so a "
            "verified_span resolves to a page and an offset (spec §6). Written by PE-03."
        ),
        "spec": SPEC_REL,
        "written_by": "tools/import_external_proposal.py",
        "revision_note": (
            "Every revision keeps its own source-id prefix and its own records. A span written "
            "against an earlier revision therefore resolves into that revision's page text and never "
            "into a later one, which is what keeps a superseded document record reproducible."
        ),
        "candidates": candidates,
        "versions": versions(),
        "sources": sources,
    }


def _table_rows(imp: Import) -> dict[str, Any]:
    per_table = []
    rendered = parsed = cells = 0
    reordered: list[dict[str, Any]] = []
    for p in imp.pages:
        for t in p.tables:
            rows = [p_.text for p_ in join_segments((p,)) if p_.kind == "row" and p_.table == (p.page, t.index)]
            ok = sum(1 for r in rows if is_row(r) and len(parse_row(r)) == t.cols)
            rendered += len(rows)
            parsed += ok
            for r, row in enumerate(t.rows):
                for c, cell in enumerate(row):
                    cells += 1
                    if cell and cell not in p.text:
                        reordered.append({"page": p.page, "index": t.index, "row": r, "col": c, "cell": cell})
            per_table.append(
                {
                    "page": p.page,
                    "index": t.index,
                    "rows": len(rows),
                    "cols": t.cols,
                    "rows_parsed": ok,
                    "header": list(t.rows[0]) if t.rows else [],
                }
            )
    return {
        "strategy": versions()["table_strategy"],
        "count": len(per_table),
        "rows_rendered": rendered,
        "rows_parsed": parsed,
        "every_row_parses": rendered == parsed,
        "cells": cells,
        "cells_not_contiguous_in_page_text": reordered,
        "cells_not_contiguous_note": (
            "A wrapped cell whose lines the page's reading order interleaves with other cells, or whose "
            "glyphs pymupdf orders differently in the cell than on the page. The characters are the same; "
            "the per-page accounting balances. Recorded, not repaired."
        ),
        "per_table": per_table,
    }


def _sub_section_rows(imp: Import) -> list[dict[str, Any]]:
    claims_by_sub: dict[str, int] = {}
    for c in imp.candidate["claims"]:
        sid = c["claim_id"].rsplit("-c", 1)[0]
        claims_by_sub[sid] = claims_by_sub.get(sid, 0) + 1
    rows = []
    for s in imp.sub_sections:
        rows.append(
            {
                "sub_section_id": s.spec.sub_section_id,
                "section_id": s.spec.section_id,
                "declared_pages": list(s.spec.declared_pages),
                "derived_pages": [s.start_page, s.end_page],
                "heading": s.heading,
                "title": s.title,
                "title_source": "declared" if s.spec.declared_title is not None or s.heading is None else "candidate heading",
                "paragraphs": sum(1 for p in s.paragraphs if p.kind == "prose"),
                "table_rows": sum(1 for p in s.paragraphs if p.kind == "row"),
                "characters": len(s.content),
                "claims": claims_by_sub.get(s.spec.sub_section_id, 0),
            }
        )
    return rows


def _discrepancies(imp: Import) -> list[dict[str, Any]]:
    out = []
    for s in imp.sub_sections:
        if s.start_page != s.spec.declared_pages[0]:
            out.append(
                {
                    "sub_section_id": s.spec.sub_section_id,
                    "declared_start_page": s.spec.declared_pages[0],
                    "derived_start_page": s.start_page,
                    "note": "the opening block sits on the page before the declared one",
                }
            )
    return out


def _losses(imp: Import) -> dict[str, Any]:
    acc = [page_accounting(p) for p in imp.pages]
    reordered = _table_rows(imp)["cells_not_contiguous_in_page_text"]
    return {
        "unit": "non-whitespace characters: the only thing the normalisation moves is whitespace",
        "total_page_chars": sum(a["chars"] for a in acc),
        "total_accounted": sum(a["accounted"] for a in acc),
        "pages_with_loss": [a for a in acc if a["loss"] != 0],
        "character_order_losses": {
            "cells": len(reordered),
            "where": [{k: v for k, v in c.items() if k != "cell"} for c in reordered],
            "note": (
                "Cells whose characters are all present but not in the page's reading order; the integrity "
                "audit reads these rows and must treat their text as unordered. Listed in full under tables."
            ),
        },
    }


def _keyword_counts(imp: Import) -> dict[str, int]:
    joined = " ".join(p.text for p in imp.pages)
    return {name: len(re.findall(pattern, joined, flags=re.IGNORECASE)) for name, pattern in DEPENDENCY_KEYWORDS}


def _citation_counts(imp: Import) -> dict[str, int]:
    joined = " ".join(p.text for p in imp.pages)
    return {name: len(re.findall(pattern, joined)) for name, pattern in CITATION_MARKERS}


def _point_sizes(imp: Import) -> dict[str, Any]:
    body = imp.config.body_point_size
    dist: dict[str, int] = {}
    other_text: dict[str, set[str]] = {}
    for p in imp.pages:
        for size, n in p.chars_by_point_size.items():
            dist[size] = dist.get(size, 0) + n
        for size, text in p.text_by_point_size.items():
            if size != body:
                other_text.setdefault(size, set()).update(text)
    return {
        "body_point_size": body,
        "distribution": dict(sorted(dist.items(), key=lambda kv: -kv[1])),
        "other_sizes_character_sets": {k: "".join(sorted(v)) for k, v in sorted(other_text.items())},
        "other_sizes_are_bullets_and_spaces_only": all(v <= {"•", " "} for v in other_text.values()),
    }


def derive_register_half(repo_root: Path, revision: Revision = REVISION_ORIGINAL) -> dict[str, Any]:
    """The fidelity register's ``derived`` half (spec decision 9), from the PDF alone."""
    imp = build_import(repo_root, revision)
    layout = imp.config.work_package_layout
    labels = () if layout is None else layout.register_declared_labels
    label_counts = {
        label: sum(1 for s in imp.sub_sections for p in s.paragraphs if p.kind == "prose" and p.text.startswith(label))
        for label in labels
    }
    wp_blocks = 0 if not labels else label_counts[labels[0]]
    return {
        "kind": "derived",
        "status": "written",
        "written_by": "PE-03, tools/import_external_proposal.py",
        "declared_status": "Confirmed",
        "basis": (
            "Derived from the stored PDF bytes by the importer under the versions below and re-derived "
            "by tests/test_msca_dn_import.py. A declaration in the provenance header is not changed by "
            "a measurement here; where the two differ the difference is recorded, not resolved."
        ),
        "candidate_sha256": _sha256(repo_root / revision.pdf_rel),
        "pages": len(imp.pages),
        "versions": versions(),
        "figures": {
            "images_on_any_page": sum(p.images for p in imp.pages),
            "pages_with_images": [p.page for p in imp.pages if p.images],
        },
        "dependency_keyword_counts": _keyword_counts(imp),
        "citation_marker_counts": _citation_counts(imp),
        "tables": _table_rows(imp),
        "table_3_1a": {
            "flattened_to_label_value_blocks": all(n > 0 for n in label_counts.values()),
            "wp_number_blocks": wp_blocks,
            "label_block_counts": label_counts,
            "basis": (
                "derived: the flattening holds when each of the three label-value lines the provenance header "
                "names opens at least one prose block inside sub-section 3.1; the counts are recorded as "
                "measured and may differ (one work package carries no 'Lead participant' line in the copy)"
            ),
        },
        "body_point_size": _point_sizes(imp),
        "per_page_extraction_losses": _losses(imp),
        "sub_sections": _sub_section_rows(imp),
        "page_map_discrepancies": _discrepancies(imp),
        "import_manifest": manifest_rel(revision).as_posix(),
    }


def _page_comparison(repo_root: Path, imp: Import, predecessor: Revision) -> dict[str, Any]:
    """Per-page comparison of *imp*'s page texts against *predecessor*'s.

    Derived, never declared: what a revision changed is measured by comparing
    the two extractions page by page under the same normalisation.
    """
    before = extract(repo_root, predecessor)
    after = imp.pages
    rows: list[dict[str, Any]] = []
    for b, a in zip(before, after):
        if b.text == a.text:
            continue
        rows.append(
            {
                "page": a.page,
                "chars_before": len(b.text),
                "chars_after": len(a.text),
                "nonws_before": nonws_len(b.text),
                "nonws_after": nonws_len(a.text),
                "blocks_before": len(b.blocks),
                "blocks_after": len(a.blocks),
                "tables_before": len(b.tables),
                "tables_after": len(a.tables),
            }
        )
    charset_before = {c for pg in before for c in pg.text if ord(c) > 127}
    charset_after = {c for pg in after for c in pg.text if ord(c) > 127}
    return {
        "compared_with_revision": predecessor.revision_id,
        "compared_with_path": predecessor.pdf_rel.as_posix(),
        "compared_with_sha256": _sha256(repo_root / predecessor.pdf_rel),
        "pages_before": len(before),
        "pages_after": len(after),
        "pages_identical": sum(1 for b, a in zip(before, after) if b.text == a.text),
        "pages_changed": [r["page"] for r in rows],
        "changed_pages": rows,
        "characters_gained": "".join(sorted(charset_after - charset_before)),
        "characters_lost": "".join(sorted(charset_before - charset_after)),
        "basis": (
            "derived: both PDFs are extracted through runner.external_proposal under the versions "
            "this manifest records, and the page texts are compared as strings. A page counted "
            "identical is byte-equal after whitespace normalisation."
        ),
    }


#: Typographic ligatures a PDF may carry as one code point. A plain-text search
#: for the unligatured spelling misses them, so their presence is recorded.
LIGATURES: str = "ﬀﬁﬂﬃﬄﬅﬆ"


def _work_package_header_blocks(imp: Import) -> dict[str, Any]:
    """Which work-package headers survived the flattening as separate blocks.

    A header whose labels all ran into the first label's block is still present
    as text, but a reader that splits a work package by its labels cannot see
    its fields. Measured, because a revision can break this without changing a
    single word. The sub-section, the labels and the consequence are the
    document's own (V07); nothing here assumes a layout.
    """
    layout = imp.config.work_package_layout
    if layout is None:
        return {
            "wp_number_blocks": [],
            "headers_collapsed_into_one_block": [],
            "label_blocks": {},
            "consequence": (
                "The document configuration declares no work-package layout, so no header "
                "layout was measured."
            ),
            "read_by": "nothing; there is no measurement to read",
        }
    labels = layout.header_labels
    anchor = layout.sub_section_id
    first = labels[0]
    number = re.compile("^" + re.escape(first) + r"\s*(\d+)(?!\d)")
    sub = next((s for s in imp.sub_sections if s.spec.sub_section_id == anchor), None)
    blocks = [] if sub is None else [p.text for p in sub.paragraphs if p.kind == "prose"]
    collapsed: list[dict[str, Any]] = []
    numbers: list[int] = []
    for text in blocks:
        m = number.match(text)
        if m is None:
            continue
        numbers.append(int(m.group(1)))
        inline = [lab for lab in labels if lab != first and lab in text]
        if inline:
            collapsed.append(
                {"work_package": int(m.group(1)), "labels_run_into_the_block": inline}
            )
    return {
        "wp_number_blocks": sorted(numbers),
        "headers_collapsed_into_one_block": collapsed,
        "label_blocks": {
            lab: sum(1 for t in blocks if t.startswith(lab)) for lab in labels
        },
        "consequence": layout.consequence,
        "read_by": (
            "The integrity audit (PE-07) reads both layouts: harness/integrity_audit."
            "split_header_fields treats a header field as '<label> <value>' and looks for each "
            "label only after the label before it, in the order the application form fixes, so a "
            "collapsed header yields the same fields as one paragraph per label and keeps the "
            "paragraph it was read from as its location. Any other reader that splits on label "
            "blocks alone is still subject to the consequence above."
        ),
    }


def extraction_limitations(repo_root: Path, revision: Revision) -> dict[str, Any]:
    """What a reader of this revision's text must not assume. All measured.

    Every entry is derived from the extraction, so a limitation cannot be
    declared away and cannot be forgotten when a revision changes the copy.
    """
    imp = build_import(repo_root, revision)
    pages = imp.pages
    ligature_pages: dict[str, list[int]] = {}
    ligature_counts: dict[str, int] = {}
    for page in pages:
        for ch in LIGATURES:
            n = page.text.count(ch)
            if n:
                ligature_counts[ch] = ligature_counts.get(ch, 0) + n
                ligature_pages.setdefault(ch, []).append(page.page)
    sizes = _point_sizes(imp)
    off_body_prose = {
        size: {"characters": sizes["distribution"][size], "character_set": chars}
        for size, chars in sizes["other_sizes_character_sets"].items()
        if set(chars) - {"•", " "}
    }
    losses = _losses(imp)
    return {
        "basis": (
            "derived: measured from this revision's extraction by "
            "tools/import_external_proposal.extraction_limitations, and re-derived by "
            "tests/test_msca_dn_import.py. Recorded, never repaired."
        ),
        "ligatures": {
            "present": sorted(ligature_counts),
            "counts": {ch: ligature_counts[ch] for ch in sorted(ligature_counts)},
            "pages": {ch: sorted(set(ligature_pages[ch])) for ch in sorted(ligature_pages)},
            "consequence": (
                "A ligature is one code point. A search for the unligatured spelling "
                "('Beneficiary') does not match the ligatured one ('Benefi' + U+FB01), so a reader "
                "matching names or labels over this text must fold ligatures first."
            ),
            "read_by": (
                "The integrity audit (PE-07) folds them: harness/integrity_audit.fold_ligatures "
                "supplies the comparison form and harness.integrity_audit.Folded maps a match on "
                "it back to the candidate's own text, so a ligature changes what matches and never "
                "what a finding quotes. Any other reader of this text must fold them itself."
            ),
        },
        "prose_below_the_body_point_size": {
            "body_point_size": sizes["body_point_size"],
            "sizes_carrying_more_than_bullets": off_body_prose,
            "consequence": (
                "Text set smaller than the declared body size is prose, not decoration. No "
                "page-based judgment of length or density was admissible from this file already "
                "(spec §2.11); this is a second reason."
            ),
        },
        "table_cells_not_in_page_reading_order": {
            "cells": losses["character_order_losses"]["cells"],
            "where": losses["character_order_losses"]["where"],
            "consequence": (
                "Every character is present and the per-page accounting balances, but the cell's "
                "text is not a contiguous substring of the page. A span into the page cannot be "
                "derived from such a cell."
            ),
        },
        "claims_without_a_span": {
            "count": imp.claims_stats["without_span"],
            "claims": imp.claims_stats["claims_without_span"],
            "consequence": (
                "A sentence that straddles a page break lives in no single page source, so the "
                "ledger carries it with no verified_span. It is still a claim; it is not locatable."
            ),
        },
        "work_package_header_blocks": _work_package_header_blocks(imp),
        "page_map_discrepancies": _discrepancies(imp),
        imp.config.reader_caveat_key: imp.config.reader_caveat,
    }


def _revision_block(repo_root: Path, imp: Import) -> dict[str, Any]:
    """What this revision is and what it supersedes. Declared and derived, marked."""
    revision = imp.revision
    config = imp.config
    out: dict[str, Any] = {
        "revision_id": revision.revision_id,
        "summary": revision.summary,
        "source_id_prefix": revision.source_id_prefix,
        "is_submitted_document": config.is_submitted_document,
        config.first_revision_key: revision.supersedes is None,
        "all_revisions": [r.revision_id for r in config.revisions],
    }
    if revision.supersedes is None:
        out["supersedes"] = None
        return out
    predecessor = config.revision_by_id(revision.supersedes)
    provenance = imp.record.get("provenance") or {}
    out["supersedes"] = {
        "revision_id": predecessor.revision_id,
        "path": predecessor.pdf_rel.as_posix(),
        "sha256": _sha256(repo_root / predecessor.pdf_rel),
        "node_id": (provenance.get("supersedes") or {}).get("id"),
        "node_version": (provenance.get("supersedes") or {}).get("version"),
        "import_manifest": manifest_rel(predecessor).as_posix(),
        "fidelity_register": predecessor.register_rel.as_posix(),
        "mechanism": (
            "runner.dev_graph.revisions.build_provenance wrote the record's provenance and "
            "runner.dev_graph.builder.build_snapshot turns it into the 'supersedes' edge. The "
            "predecessor record, its page texts and its spans are untouched; it stops being a "
            "current candidate and stays readable as history."
        ),
    }
    out["change_id"] = provenance.get("change_id")
    out["change_record"] = {
        "written": False,
        "why": (
            "runner.dev_graph.changes.record_change accepts only the five Tier 3 record paths and "
            "rebuilds a before/after snapshot pair, so it neither covers a replaced source PDF nor "
            "replays byte-equal inside this importer. The change_id names the revision; no change "
            "record stands behind it, and nothing in the build resolves it."
        ),
    }
    out["comparison_with_predecessor"] = _page_comparison(repo_root, imp, predecessor)
    return out


def manifest_rel(revision: Revision) -> Path:
    """Repo-relative path of *revision*'s import manifest."""
    return config_for(revision).manifest_rel(revision)


def _criterion_heading_note(config: DocumentConfig) -> str:
    """How the manifest's normalisation block describes the criterion headings."""
    markers = [marker for _section, marker, _page in config.criterion_heading_markers]
    if not markers:
        return "the document carries no criterion-level heading of its own"
    if len(markers) == 1:
        return f"the one criterion-level heading ({markers[0]!r}) is its section's own content"
    listed = ", ".join(repr(m) for m in markers)
    return f"the criterion-level headings ({listed}) are their sections' own content"


def _runtime_environment_block(config: DocumentConfig) -> dict[str, Any]:
    """The pinned extraction environment, for a manifest that may carry it.

    Empty for a manifest already bound by hash into a frozen baseline: V01
    found that adding the block there would rewrite four artifacts the
    historical-validation milestone holds immutable. A manifest authored for
    the first time carries it, so the pin travels with the artifact rather
    than only in ``requirements.txt`` and the decision record. The values are
    the declared pin, never a measurement, so the manifest stays replayable on
    any machine that is on the pin.
    """
    if not config.manifest_records_runtime_environment:
        return {}
    return {
        "runtime_environment": {
            "pymupdf": PINNED_PYMUPDF,
            "mupdf": PINNED_MUPDF,
            "measured_python": list(MEASURED_PYTHON),
            "basis": (
                "declared: the pin of runner.extraction_environment, not a measurement of the "
                "machine that wrote this manifest. An off-pin build does not reproduce these "
                "bytes; --environment reports whether the running one is on the pin."
            ),
            "decision_record": EXTRACTION_DECISION_REL,
        }
    }


def render_manifest(
    repo_root: Path, imp: Optional[Import] = None, imps: Optional[Sequence[Import]] = None
) -> dict[str, Any]:
    imp = imp or build_import(repo_root)
    revision = imp.revision
    config = imp.config
    records = render_source_records(repo_root, imp)
    sources_bytes = canonical_json_bytes(render_sources(repo_root, imps, config))
    doc_id = imp.candidate["document_id"]
    return {
        "record_type": MANIFEST_RECORD_TYPE,
        "schema_ref": _SCHEMA_REF,
        "spec": SPEC_REL,
        "ticket": config.import_ticket,
        "tool": "tools/import_external_proposal.py",
        "candidate": {
            "path": revision.pdf_rel.as_posix(),
            "sha256": _sha256(repo_root / revision.pdf_rel),
            "pages": len(imp.pages),
            "is_submitted_document": config.is_submitted_document,
            "fidelity_register": revision.register_rel.as_posix(),
        },
        "revision": _revision_block(repo_root, imp),
        "versions": versions(),
        "document": {
            "document_id": doc_id,
            "title": imp.candidate["title"],
            "schema_id": imp.record["schema_id"],
            "state": imp.record["state"],
            "record_path": imp.record_rel,
            "content_version": imp.record["content_version"],
            "node_id": document_node_id(doc_id, imp.record["content_version"]),
            "sections": [
                {"section_id": s["section_id"], "sub_sections": [ss["sub_section_id"] for ss in s["sub_sections"]]}
                for s in imp.candidate["sections"]
            ],
        },
        "sources": {
            "path": SOURCES_REL.as_posix(),
            "count": len(imp.pages),
            "source_id_format": config.source_id_format(revision),
            "sha256": hashlib.sha256(sources_bytes).hexdigest(),
            "sha256_covers": (
                "the whole source index of the graph root, every revision's records included; one "
                "file is what runner/dev_graph/builder.py reads per graph root"
            ),
            "records_sha256": hashlib.sha256(canonical_json_bytes(records)).hexdigest(),
            "records_sha256_covers": "only this revision's own source records, in page order",
            "revisions_in_the_file": [r.revision_id for r in config.revisions],
        },
        "page_map": {
            "declared_from": config.page_map_declared_from,
            "sub_sections": _sub_section_rows(imp),
            "discrepancies": _discrepancies(imp),
        },
        "normalisation": {
            "whitespace": "runs of whitespace collapse to one space; nothing else is rewritten",
            "paragraphs": "one paragraph per pymupdf text block; blank-line blocks dropped",
            "page_crossing": (
                "the last prose block of a page joins the first of the next when it ends without "
                "terminal punctuation and the next starts in lower case, or when it ends with a hyphen"
            ),
            "headings": "the heading block of a numbered sub-section is its title (numbering stripped), not its content",
            "criterion_heading": _criterion_heading_note(config),
            "tables": "one pipe-delimited paragraph per table row, cells collapsed; a pipe inside a cell is refused",
            "hyphenation": "line-end hyphens are kept as the source carries them",
        },
        "tables": _table_rows(imp),
        "claims": {
            "count": len(imp.candidate["claims"]),
            "rule": (
                "every sentence of the prose that matches a named pattern of "
                "runner.external_proposal.CLAIM_RULES; table rows and headings are not sentences"
            ),
            **imp.claims_stats,
            "evidence_strength": "unconfirmed",
            "declared_status": "Unresolved",
            "approval": "not_applicable",
            # The document's own sentence, never a generic one: the copy's says
            # the sanitisation removed every citation, which is not true of the
            # submitted text and would be asserted of it by a shared default.
            "why": config.claim_ledger_note,
        },
        "extraction_losses": _losses(imp),
        **_runtime_environment_block(config),
        # This revision's own register, never the first revision's: each revision
        # owns the register whose derived half was measured from its extraction.
        "fidelity_register_derived_half": f"{revision.register_rel.as_posix()}#derived",
    }


# --------------------------------------------------------------------------- #
# Writing and checking
# --------------------------------------------------------------------------- #


def build_imports(
    repo_root: Path, *, with_provenance: bool = True, config: DocumentConfig = DEFAULT_DOCUMENT
) -> list[Import]:
    """Every revision of *config*, oldest first."""
    config.require_complete()
    return [
        build_import(repo_root, revision, with_provenance=with_provenance)
        for revision in config.revisions
    ]


def render_sources_bytes(repo_root: Path, config: DocumentConfig = DEFAULT_DOCUMENT) -> bytes:
    """The source index alone, without resolving any provenance.

    The one artifact an empty graph root can be bootstrapped from: a document
    record's provenance is resolved against the built graph, and the graph
    cannot be built until every span has a source to resolve into.
    """
    imps = build_imports(repo_root, with_provenance=False, config=config)
    return canonical_json_bytes(render_sources(repo_root, imps, config))


def render_all(repo_root: Path, config: DocumentConfig = DEFAULT_DOCUMENT) -> dict[str, bytes]:
    """Every file PE-03 authors for *config*, as the bytes it should hold on disk.

    Every revision is rendered, not only the active one: the source index is
    one file per graph root, and a revision that stopped writing the earlier
    revision's page records would break the earlier record's spans.
    """
    config.require_complete()
    workspace = config.require_workspace()
    imps = build_imports(repo_root, config=config)
    out: dict[str, bytes] = {
        (workspace / SOURCES_REL).as_posix(): canonical_json_bytes(
            render_sources(repo_root, imps, config)
        ),
    }
    for imp in imps:
        out[(workspace / imp.record_rel).as_posix()] = canonical_json_bytes(imp.record)
        out[config.manifest_rel(imp.revision).as_posix()] = canonical_json_bytes(
            render_manifest(repo_root, imp, imps)
        )
        out[imp.revision.register_rel.as_posix()] = canonical_json_bytes(
            register_of(repo_root, imp.revision)
        )
    return out


def register_of(repo_root: Path, revision: Revision) -> dict[str, Any]:
    """*revision*'s fidelity register, from the renderer its document has (V17, AN10).

    Three documents, three renderers, and this is the one place that chooses
    between them. The sanitised case's header declares a sanitisation, a
    transformation and a reflow, so
    :func:`tools.author_msca_dn_workspace.render_register` refuses both other
    documents rather than labelling them with the copy's facts. The submitted
    text and the anonymised derivative each have a renderer of their own, and
    each refuses every document but its own. Imported late, because both
    modules read this one.
    """
    config = config_for(revision)
    if config.is_submitted_document:
        from tools import author_original_workspace as ows

        return ows.render_submitted_register(repo_root, revision)
    if config.is_anonymised_derivative:
        from tools import author_anonymised_register as aar

        return aar.render_anonymised_register(repo_root, revision)
    return ws.render_register(repo_root, revision)


def check(repo_root: Path, config: DocumentConfig = DEFAULT_DOCUMENT) -> list[str]:
    """Relative paths whose bytes differ from the rendering, or are absent.

    Read-only, and it may refuse instead of returning: a malformed declaration
    input or a declaration a register holds alone is a refusal, not a staleness
    entry (:mod:`tools.fidelity_declarations`).
    """
    return [
        rel
        for rel, data in render_all(repo_root, config).items()
        if not (repo_root / rel).is_file() or (repo_root / rel).read_bytes() != data
    ]


def author(repo_root: Path, config: DocumentConfig = DEFAULT_DOCUMENT) -> list[str]:
    """Write every file of *config*; return the relative paths that changed.

    The source index is written before any document record, because a record
    whose spans name records the file does not yet carry would not build. The
    declaration inputs of every register are read first, so a malformed one is
    refused before the source index is written.
    """
    config.require_complete()
    workspace = config.require_workspace()
    validate_inputs(
        repo_root,
        [(r.revision_id, r.register_rel) for r in config.revisions],
        config.declaration_contract(),
    )
    changed: list[str] = []
    sources_rel = (workspace / SOURCES_REL).as_posix()
    # Bootstrap: the source index is written first and without building the
    # graph, because the provenance of every later record is resolved against a
    # graph that cannot be built until the spans have sources to resolve into.
    sources_bytes = render_sources_bytes(repo_root, config)
    sources_target = repo_root / sources_rel
    if not sources_target.is_file() or sources_target.read_bytes() != sources_bytes:
        atomic_write_text(sources_bytes.decode("utf-8"), sources_target)
        changed.append(sources_rel)
    imps = build_imports(repo_root, config=config)
    rendered = render_all(repo_root, config)
    if rendered[sources_rel] != sources_bytes:  # pragma: no cover - guards the bootstrap
        raise ImportRefused(
            "the source index rendered with and without provenance differ; provenance must not "
            "reach the source index"
        )
    by_record = {(workspace / imp.record_rel).as_posix(): imp for imp in imps}
    order = [rel for rel in rendered if rel != sources_rel]
    for rel in order:
        data = rendered[rel]
        target = repo_root / rel
        if target.is_file() and target.read_bytes() == data:
            continue
        imp = by_record.get(rel)
        if imp is not None:
            # The engine's writer owns immutability: a changed record is a new version.
            import_candidate(
                repo_root / workspace,
                imp.candidate,
                where="tools/import_external_proposal.py candidate",
                provenance=imp.record.get("provenance"),
                schema_id=DOCUMENT_SCHEMA_ID_V2,
            )
        else:
            atomic_write_text(data.decode("utf-8"), target)
        changed.append(rel)
    return changed


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="exit 1 if any file would change")
    parser.add_argument(
        "--document",
        default=DEFAULT_DOCUMENT.config_id,
        choices=[doc.config_id for doc in DOCUMENTS],
        help="which document to import; the default is the one PE-03 imported",
    )
    parser.add_argument(
        "--describe",
        action="store_true",
        help="print the selected document's identity and what it still needs, and write nothing",
    )
    parser.add_argument(
        "--config-input",
        type=Path,
        default=None,
        help=(
            "a private configuration input (runner/original_configuration.py) completing the "
            "selected document. Checked against the dry-import inventory it names before it is "
            "applied; a disagreement is reported and nothing is written."
        ),
    )
    add_environment_flag(parser)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help=(
            "the root every path is resolved against. For the submitted original this is the "
            "private root, never a directory in this repository."
        ),
    )
    args = parser.parse_args(argv)
    requested = environment_exit_code(args)
    if requested is not None:
        return requested
    repo_root = args.repo_root or find_repo_root()
    try:
        config = document_by_id(args.document)
        if args.config_input is not None:
            configuration = load_configuration(args.config_input, repo_root)
            report = check_configuration(configuration, repo_root)
            for line in report.lines():
                print(line)
            if not report.green:
                print(
                    f"refused: the configuration disagrees with the measurement it names in "
                    f"{len(report.findings)} place(s); nothing was written",
                    file=sys.stderr,
                )
                return 1
            config = complete_from_input(config, configuration)
        if args.describe:
            print(json.dumps(config.identity(), indent=2, ensure_ascii=False))
            return 0
        if args.check:
            stale = check(repo_root, config)
            for rel in stale:
                print(f"would change: {rel}")
            print("up to date" if not stale else f"{len(stale)} file(s) would change")
            if stale:
                print(staleness_notice())
            return 1 if stale else 0
        changed = author(repo_root, config)
        for rel in changed:
            print(f"wrote: {rel}")
        print("no change" if not changed else f"{len(changed)} file(s) written")
        return 0
    except (
        ImportRefused,
        ConfigurationRefused,
        DevGraphError,
        FidelityDeclarationsError,
    ) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
