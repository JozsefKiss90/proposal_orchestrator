"""The 2025 authority source index and the 2025-to-2026 rule-equivalence matrix.

The runbook proposes preparing a historical profile as a copy of the 2026 one,
leaving a rule unchanged wherever no source states a difference
(``plans/msca_dn_pe09_runbook.md`` section 3). That is a defaulting policy. It
is not evidence that the rule applied in 2025, and a profile built that way
would score a 2025 submission under rules nobody has sourced to 2025.

This module writes the two artifacts that replace the policy with a record: an
index of the authority documents, each pinned and each declaring whether it is
obtained at all, and a matrix in which every scoring-relevant rule is either
sourced to a 2025 document or recorded as defaulted or unresolved. The
vocabulary has no verdict meaning *no difference was found*.

Every row is derived, not typed
-------------------------------
A deterministic, Claude-free transform, in the shape of
:mod:`tools.author_deferral_register`:

* the three criteria, the weights, the two thresholds and the score scale come
  from the ESR record's own ``evaluation_result`` — the 2025 evaluation's
  recorded wording — read against the 2026 scorecard's values;
* the ten Part B aspect headings are located in the **V5.0** application form,
  the form of the 2025 call, one citation per heading. The page is the heading's
  last occurrence, which is the evaluation-criteria table at the back of the
  form; the rule is validated against the scorecard's own declared V6.0 pages
  and this module refuses to render if it stops holding;
* the ten anchors are then compared in the other direction: the aspect anchors
  printed across each form's criteria table are read out and must be the same
  set, with the page either side of the table required to carry none, so an
  eleventh aspect row refuses rather than passing unseen;
* the eleven criterion-to-table cross-references behind the appendix mapping are
  located in the V5.0 form the same way, at their first occurrence, validated
  against the mapping's own declared V6.0 pages;
* the Part B2 section list, the page caps and the implementation-mode vocabulary
  are located in both forms by a declared needle, and every quote is verified to
  occur verbatim in the page text it cites;
* the submission's DN mode and the 2025 call identifier come from the fidelity
  register and the PE-01 decision record, with the status each of them declares;
* the weighted-total formula is checked against the ESR's recorded total, and
  this module refuses to render if it stops reproducing it;
* an index entry claiming a rank above ``computed_only`` names the field where
  that provenance is recorded, and this module reads the field and refuses if
  the record has stopped saying it.

The rows are built area by area, one function per area, over a single parsed
:class:`_Records`. The refusals about the records rather than about one row run
once, in :func:`_records`, before any row is built.

What this module does not do
----------------------------
It obtains no document. Four required 2025 documents are not in this repository
— the work programme, the General Annexes, the call conditions and the
evaluation form version in force — and each is an index entry with
``authentication: not_obtained`` whose path is where it will be filed when the
operator supplies it. No row closes by assuming what one of them would say.

It also does not check its own output, and cannot: ``harness/`` holds the reader
and this package may not import it, under the one-way boundary
``tests/harness/test_boundary.py`` enforces. A tool that both wrote a record and
certified it would be judging its own output.
``harness.commands.authority_matrix`` reads the two declarations, writes the
Markdown readings beside them, and is the command that can fail.

Usage::

    py -3.10 -m tools.author_msca_dn_authority_matrix           # write both
    py -3.10 -m tools.author_msca_dn_authority_matrix --check    # byte-equal replay

Then check them and render their readings, with the path the write prints::

    py -3.10 -m harness.commands.authority_matrix --matrix <MATRIX_REL>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

import pymupdf

from runner.atomic_write import atomic_write_text, canonical_json_bytes
from runner.paths import find_repo_root
from runner.source_index import normalise_whitespace, read_page_text
from tools.fidelity_declarations import file_sha256

# --------------------------------------------------------------------------- #
# The documents and records
# --------------------------------------------------------------------------- #

DN_DIR = Path("docs/tier4_orchestration_state/msca_dn")
AF_DIR = Path("docs/tier2a_instrument_schemas/application_forms/msca")

#: The Part B template of the 2025 call. The one 2025-era authority document
#: this repository holds.
AF_V5_REL = AF_DIR / "af_he-msca-dn_en.pdf"
#: The Part B template of the 2026 call.
AF_V6_REL = AF_DIR / "Tpl_Application Form (Part B) (HE MSCA DN).pdf"
EF_REL = Path("docs/tier2a_instrument_schemas/evaluation_forms/msca/ef_he-msca_en.pdf")
GENERAL_ANNEXES_REL = Path(
    "docs/tier1_normative_framework/programme_guidance/"
    "wp-15-general-annexes_horizon-2026-2027_en.pdf"
)
WORK_PROGRAMME_REL = Path(
    "docs/tier2b_topic_and_call_sources/work_programmes/msca/"
    "wp-2-marie-sklodowska-curie-actions_horizon-2026-2027_en.pdf"
)
ESR_REL = DN_DIR / "esr/msca-dn-2025-esr.json"
FIDELITY_REL = Path(
    "docs/tier3_project_instantiation/source_materials/msca_dn/fidelity_register.json"
)
PE01_REL = Path(
    "docs/tier4_orchestration_state/decision_log/msca-dn-pe01-workspace_2026-10-04.json"
)
SCORECARD_REL = Path("harness/evaluator_scorecard_msca_dn.json")
PROFILE_REL = Path("harness/profiles/msca_dn_2026_default.json")
APPENDIX_REL = Path("harness/criterion_appendix_mapping_msca_dn.json")
SPEC_REL = Path("plans/msca_dn_pre_evaluation_spec.md")

#: Where a 2025 document will be filed when the operator supplies it. These are
#: destinations, not documents: nothing is asserted about a file at one of them.
HIST_WP_REL = Path(
    "docs/tier2b_topic_and_call_sources/work_programmes/msca/historical_work_programme.pdf"
)
HIST_ANNEXES_REL = Path(
    "docs/tier1_normative_framework/programme_guidance/historical_general_annexes.pdf"
)
HIST_CALL_REL = Path(
    "docs/tier2b_topic_and_call_sources/call_extracts/historical_dn_call_conditions.pdf"
)
HIST_EF_REL = Path(
    "docs/tier2a_instrument_schemas/evaluation_forms/msca/historical_evaluation_form.pdf"
)

AUTHORITY_DIR = DN_DIR / "authority"
INDEX_REL = AUTHORITY_DIR / "authority_source_index_2026-10-12.json"
MATRIX_REL = AUTHORITY_DIR / "equivalence_matrix_2025_2026-10-12.json"

#: The schemas the two declarations carry. ``harness.authority_matrix`` holds the
#: reader's copies, and ``tests/test_msca_dn_authority_matrix.py`` asserts they
#: agree. Deliberate double entry: this module may not import the harness.
SCHEMA_INDEX = "authority_source_index/1"
SCHEMA_MATRIX = "authority_equivalence_matrix/1"

AUTHORED_ON = "2026-10-12"
TICKET = "V09 of plans/msca_dn_historical_validation_tickets.md"
HISTORICAL_LABEL = "2025"
CURRENT_LABEL = "2026"

#: The areas ticket V09's second acceptance criterion names. The matrix must
#: cover every one of them, and ``harness.authority_matrix.check`` reports any
#: that no row covers.
REQUIRED_AREAS: tuple[str, ...] = (
    "criteria",
    "weights",
    "thresholds",
    "evaluator_instructions",
    "variant",
    "section_mapping",
    "appendix_mapping",
    "scoring_assumption",
)


class AuthorityAuthoringError(RuntimeError):
    """A record or document this module refuses to render against."""


# --------------------------------------------------------------------------- #
# Reading
# --------------------------------------------------------------------------- #


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _page_count(path: Path) -> int:
    document = pymupdf.open(path)
    try:
        return int(document.page_count)
    finally:
        document.close()


class _Document:
    """A pinned PDF, read page by page through the source index's reader.

    The same extraction route the evaluation bundle used, so a quote located
    here is located in the text every other derivation in this repository sees.
    """

    def __init__(self, repo_root: Path, rel: Path) -> None:
        self.rel = rel.as_posix()
        self.path = repo_root / rel
        if not self.path.is_file():
            raise AuthorityAuthoringError(f"{self.rel}: not in the tree")
        self.pages = _page_count(self.path)
        self._text: dict[int, str] = {}

    def text(self, page: int) -> str:
        if page not in self._text:
            self._text[page] = read_page_text(self.path, page)
        return self._text[page]

    def occurrences(self, needle: str) -> tuple[int, ...]:
        wanted = normalise_whitespace(needle)
        return tuple(page for page in range(1, self.pages + 1) if wanted in self.text(page))


def _citation(source: str, page: int, quote: str, states: str) -> dict[str, Any]:
    return {"source": source, "page": page, "quote": quote, "states": states}


def _field_citation(source: str, field: str, states: str, quote: str = "") -> dict[str, Any]:
    cited: dict[str, Any] = {"source": source, "field": field, "states": states}
    if quote:
        cited["quote"] = quote
    return cited


def _verified(document: _Document, page: int, quote: str, states: str) -> dict[str, Any]:
    """A page citation whose quote is verified to occur in that page's text.

    A declared quote that is not in the page it cites is the one defect a
    citation cannot be allowed to carry, so it refuses here rather than being
    written and reported later.
    """
    wanted = normalise_whitespace(quote)
    if wanted not in document.text(page):
        raise AuthorityAuthoringError(
            f"{document.rel} page {page} does not carry the quote {quote[:60]!r}"
        )
    return _citation(document.rel, page, wanted, states)


def _verified_text(repo_root: Path, rel: Path, passage: str, states: str) -> dict[str, Any]:
    """A citation into a record that is neither JSON nor paginated.

    The passage itself is the locator and has to occur in the record as text, so
    a reworded decision refuses here rather than being written and reported
    later. The same rule the reader applies to a non-JSON source.
    """
    text = (repo_root / rel).read_text(encoding="utf-8-sig")
    if passage not in text:
        raise AuthorityAuthoringError(
            f"{rel.as_posix()} does not carry the passage {passage[:60]!r}"
        )
    return _field_citation(rel.as_posix(), passage, states)


# --------------------------------------------------------------------------- #
# The three derivations over the forms
# --------------------------------------------------------------------------- #


def _aspect_heading_citations(
    scorecard: Mapping[str, Any], v5: _Document, v6: _Document
) -> tuple[dict[str, Any], ...]:
    """One citation per Part B aspect heading, located in the 2025 form.

    A heading occurs twice or three times in a form: in the section instructions
    and again in the evaluation-criteria table at the back. The scorecard cites
    the table, which is the last occurrence — and this function refuses unless
    the last occurrence in the 2026 form is still the page the scorecard
    declares, which is what makes the rule a measurement rather than a habit.
    """
    citations: list[dict[str, Any]] = []
    for criterion in scorecard["criteria"]:
        for aspect in criterion["aspects"]:
            heading = aspect["af_v6_heading"]
            found_v6 = v6.occurrences(heading)
            found_v5 = v5.occurrences(heading)
            if not found_v6 or not found_v5:
                raise AuthorityAuthoringError(
                    f"aspect {aspect['id']}: heading not found in "
                    f"{'the 2026 form' if not found_v6 else 'the 2025 form'}"
                )
            if max(found_v6) != aspect["af_v6_heading_page"]:
                raise AuthorityAuthoringError(
                    f"aspect {aspect['id']}: the last occurrence in the 2026 form is page "
                    f"{max(found_v6)}, the scorecard declares {aspect['af_v6_heading_page']}; "
                    "the last-occurrence rule no longer holds"
                )
            citations.append(
                _verified(
                    v5,
                    max(found_v5),
                    heading,
                    f"aspect {aspect['id']} ({aspect['anchor']}) is a Part B heading of the "
                    "2025 form, verbatim",
                )
            )
    return tuple(citations)


#: An aspect anchor as a form prints it: one digit, a dot, one digit, with no
#: word character before it, so a version string such as V5.0 is not an anchor.
_ANCHOR = re.compile(r"(?<![\w.])(\d\.\d)(?![\d])")


def _table_pages(scorecard: Mapping[str, Any], document: _Document) -> tuple[int, ...]:
    """The pages of *document* carrying the evaluation-criteria table.

    Located, not declared: each aspect heading's last occurrence is its row in
    that table, and the table is the whole span those pages bracket. The span
    rather than the set, so a page inside the table that no declared heading
    happens to sit on is still read — otherwise the pages searched would be
    defined by the list being checked, and an extra row could hide on one.
    """
    pages: set[int] = set()
    for criterion in scorecard["criteria"]:
        for aspect in criterion["aspects"]:
            found = document.occurrences(aspect["af_v6_heading"])
            if found:
                pages.add(max(found))
    if not pages:
        return ()
    return tuple(range(min(pages), max(pages) + 1))


def _anchors_on(document: _Document, pages: Sequence[int]) -> set[str]:
    """Every aspect anchor printed on *pages*."""
    found: set[str] = set()
    for page in pages:
        found |= set(_ANCHOR.findall(document.text(page)))
    return found


def _refuse_unless_anchor_sets_agree(
    scorecard: Mapping[str, Any], v5: _Document, v6: _Document
) -> tuple[str, ...]:
    """Refuse unless both forms' criteria tables carry exactly the ten anchors.

    The heading citations settle one direction: every 2026 aspect heading is in
    the 2025 form. This settles the other: neither form's table carries an
    eleventh anchor the other lacks. Without it the row would claim a set
    equality while evidencing an inclusion, which reads a difference nobody
    looked for as agreement.

    The page either side of the table is read too, and must carry no anchor at
    all. That is what makes the span the whole table: an eleventh row would
    have to print its anchor somewhere, and a table that has grown past the
    span refuses here instead of going unseen.
    """
    declared = tuple(
        aspect["anchor"]
        for criterion in scorecard["criteria"]
        for aspect in criterion["aspects"]
    )
    for label, document in (("2025", v5), ("2026", v6)):
        pages = _table_pages(scorecard, document)
        if not pages:
            raise AuthorityAuthoringError(
                f"the {label} form: no aspect heading located, so the criteria table cannot be "
                "found; the anchor comparison has no subject"
            )
        found = _anchors_on(document, pages)
        if found != set(declared):
            raise AuthorityAuthoringError(
                f"the {label} form: its criteria table carries anchors {sorted(found)}, the "
                f"scorecard declares {sorted(set(declared))}; the two sets are no longer equal "
                "and the aspect rows would claim more than is measured"
            )
        bounding = [page for page in (pages[0] - 1, pages[-1] + 1) if 1 <= page <= document.pages]
        spilled = _anchors_on(document, bounding)
        if spilled:
            raise AuthorityAuthoringError(
                f"the {label} form: pages {bounding} bound the criteria table and carry anchors "
                f"{sorted(spilled)}; the table reaches past the span this compares, so the "
                "anchor sets are no longer measured over the whole table"
            )
    return declared


def _appendix_quote_citations(
    mapping: Mapping[str, Any], v5: _Document, v6: _Document
) -> tuple[dict[str, Any], ...]:
    """One citation per distinct cross-reference quote, located in the 2025 form.

    The appendix mapping routes table rows to criteria on these sentences. Each
    is cited at its first occurrence, the instructional one, and this function
    refuses unless the first occurrence in the 2026 form is still the page the
    mapping declares.
    """
    citations: list[dict[str, Any]] = []
    seen: list[str] = []
    for row in mapping["rows"]:
        for source in row.get("sources", ()):
            quote = normalise_whitespace(source["quote"])
            if quote in seen:
                continue
            seen.append(quote)
            found_v6 = v6.occurrences(quote)
            found_v5 = v5.occurrences(quote)
            if not found_v6 or not found_v5:
                raise AuthorityAuthoringError(
                    f"appendix quote {quote[:50]!r}: not found in "
                    f"{'the 2026 form' if not found_v6 else 'the 2025 form'}"
                )
            if min(found_v6) != source["page"]:
                raise AuthorityAuthoringError(
                    f"appendix quote {quote[:50]!r}: the first occurrence in the 2026 form is "
                    f"page {min(found_v6)}, the mapping declares {source['page']}; the "
                    "first-occurrence rule no longer holds"
                )
            citations.append(
                _verified(
                    v5,
                    min(found_v5),
                    quote,
                    "the cross-reference the appendix mapping routes on, in the 2025 form",
                )
            )
    return tuple(citations)


def _refuse_if_tagged(v5: _Document, v6: _Document) -> None:
    """Refuse if either application form carries an applicability tag.

    The matrix records that the tag grammar selecting the DN aspects belongs to
    the evaluation form alone, which is why the form-equivalence record cannot
    reach it. If a tag turned up in an application form that reasoning would be
    wrong, so it is checked rather than asserted.
    """
    for document in (v5, v6):
        if document.occurrences("[OPTION for"):
            raise AuthorityAuthoringError(
                f"{document.rel} carries an [OPTION for tag; the matrix states that the "
                "applicability grammar is the evaluation form's alone"
            )


def _total_reproduces(esr: Mapping[str, Any], scorecard: Mapping[str, Any]) -> dict[str, float]:
    """Refuse unless the weighted-total formula reproduces the recorded total.

    The formula is the scorecard's ``S = 10xE + 6xI + 4xQ``, which is each
    criterion's score times its weight in percent over five. Reproducing the
    2025 evaluation's own recorded total from its own recorded criterion scores
    is the arithmetic evidence that the weighting rule the 2026 scorecard holds
    is the one the 2025 evaluation applied.
    """
    result = esr["evaluation_result"]
    weights = {c["id"]: c["weight_pct"] for c in scorecard["criteria"]}
    total = 0.0
    parts: dict[str, float] = {}
    for criterion in result["criteria"]:
        ident = criterion["criterion_id"]
        if ident not in weights:
            raise AuthorityAuthoringError(
                f"the ESR records criterion {ident!r}, which the scorecard does not declare"
            )
        if criterion["weight_pct"] != weights[ident]:
            raise AuthorityAuthoringError(
                f"criterion {ident}: the ESR records weight {criterion['weight_pct']}, the "
                f"scorecard declares {weights[ident]}"
            )
        contribution = criterion["score"] * weights[ident] / 5
        parts[ident] = contribution
        total += contribution
    if round(total, 6) != round(float(result["total"]), 6):
        raise AuthorityAuthoringError(
            f"the weighted total formula yields {total}, the ESR records {result['total']}"
        )
    return parts


def _declared_assumed(record: Mapping[str, Any], pointer: Sequence[str], where: str) -> None:
    """Refuse unless the record still declares the value at *pointer* Assumed."""
    node: Any = record
    for segment in pointer:
        if not isinstance(node, Mapping) or segment not in node:
            raise AuthorityAuthoringError(
                f"{where}: {'/'.join(pointer)} does not resolve; the row that records the call "
                "identifier as unresolved no longer holds"
            )
        node = node[segment]
    if node != "Assumed":
        raise AuthorityAuthoringError(
            f"{where}: declared_status is {node!r}, not 'Assumed'; the row that records the "
            "call identifier as unresolved no longer holds"
        )


# --------------------------------------------------------------------------- #
# The rows
# --------------------------------------------------------------------------- #


def _measurement(
    ident: str, claim: str, record: Path | str, field: str, **expected: Any
) -> dict[str, Any]:
    rel = record.as_posix() if isinstance(record, Path) else record
    return {"id": ident, "claim": claim, "record": rel, "field": field, **expected}


@dataclass(frozen=True)
class _Records:
    """Every record and document the row builders read, parsed once.

    The nine area builders each read a few of these. Passing the set as one
    value keeps each signature to the thing it is derived from, and keeps the
    parsing and the refusals in one place: by the time a builder runs, the
    records have already been checked.
    """

    repo_root: Path
    esr: Mapping[str, Any]
    scorecard: Mapping[str, Any]
    profile: Mapping[str, Any]
    appendix: Mapping[str, Any]
    fidelity: Mapping[str, Any]
    pe01: Mapping[str, Any]
    v5: _Document
    v6: _Document
    ef: _Document
    annexes: _Document
    #: The aspect anchors, measured equal in both forms' criteria tables.
    anchors: tuple[str, ...]

    @property
    def result(self) -> Mapping[str, Any]:
        return self.esr["evaluation_result"]

    @property
    def scoring(self) -> Mapping[str, Any]:
        return self.scorecard["scoring"]


def _records(repo_root: Path) -> _Records:
    """Read every record and document, and refuse before any row is built.

    Five refusals run here because they are about the records rather than about
    one row: an applicability tag in an application form, the aspect anchors
    disagreeing between the forms, the weighting formula no longer reproducing
    the recorded total, and the call identifier stopping being declared Assumed
    in either record that declares it.
    """
    esr = _read_json(repo_root / ESR_REL)
    scorecard = _read_json(repo_root / SCORECARD_REL)
    v5 = _Document(repo_root, AF_V5_REL)
    v6 = _Document(repo_root, AF_V6_REL)
    fidelity = _read_json(repo_root / FIDELITY_REL)
    pe01 = _read_json(repo_root / PE01_REL)

    _refuse_if_tagged(v5, v6)
    anchors = _refuse_unless_anchor_sets_agree(scorecard, v5, v6)
    _total_reproduces(esr, scorecard)
    _declared_assumed(
        pe01, ("declared_values", "historical_call_id", "declared_status"), PE01_REL.as_posix()
    )
    _declared_assumed(
        fidelity,
        ("provenance", "historical_submission", "call_id", "declared_status"),
        FIDELITY_REL.as_posix(),
    )

    return _Records(
        repo_root=repo_root,
        esr=esr,
        scorecard=scorecard,
        profile=_read_json(repo_root / PROFILE_REL),
        appendix=_read_json(repo_root / APPENDIX_REL),
        fidelity=fidelity,
        pe01=pe01,
        v5=v5,
        v6=v6,
        ef=_Document(repo_root, EF_REL),
        annexes=_Document(repo_root, GENERAL_ANNEXES_REL),
        anchors=anchors,
    )


# --------------------------------------------------------------------------- #
# The rows, area by area
# --------------------------------------------------------------------------- #


def _call_identity_rows(src: _Records) -> list[dict[str, Any]]:
    """Which call the 2025 submission was evaluated under."""
    profile, fidelity = src.profile, src.fidelity
    fidelity_rel = FIDELITY_REL.as_posix()
    pe01_rel = PE01_REL.as_posix()
    rows: list[dict[str, Any]] = []
    rows.append(
        {
            "id": "CI-01",
            "area": "call_identity",
            "rule": (
                "Which call the 2025 submission was evaluated under. Every other row's 2025 "
                "side is addressed to this call, and the four unobtained documents can only be "
                "fetched once it is settled."
            ),
            "affects": "an interpretation",
            "verdict": "unresolved",
            "settles": "as_applied_to_this_submission",
            "declared_status": "Assumed",
            "status_basis": (
                "Two records declare the identifier Assumed and give the same reason. The value "
                "is the operator's declaration, and this module refuses to render if either "
                "record stops declaring it Assumed."
            ),
            "limitation": (
                "The Evaluation Summary Report names no call and no proposal number, and the "
                "2025 work programme is not in this repository. Nothing here confirms the call "
                "the 2025 evaluation was run under."
            ),
            "consequence": (
                "The historical profile carries the operator's declared call identifier with "
                "declared_status Assumed, never Confirmed, and the matrix is cited as the reason."
            ),
            "would_be_settled_by": [HIST_CALL_REL.as_posix(), HIST_WP_REL.as_posix()],
            "citations": [
                _field_citation(
                    pe01_rel,
                    "declared_values/historical_call_id/reason",
                    "the PE-01 decision records the call identifier as the operator's declaration",
                ),
                _field_citation(
                    fidelity_rel,
                    "provenance/historical_submission/call_id/basis",
                    "the fidelity register records the same basis for the same identifier",
                ),
            ],
            "measurements": [
                _measurement(
                    "CI-01-M1",
                    "the PE-01 decision declares the call identifier Assumed",
                    PE01_REL,
                    "declared_values/historical_call_id/declared_status",
                    expected="Assumed",
                ),
                _measurement(
                    "CI-01-M2",
                    "the fidelity register declares the same identifier Assumed",
                    FIDELITY_REL,
                    "provenance/historical_submission/call_id/declared_status",
                    expected="Assumed",
                ),
            ],
        }
    )
    return rows


def _criteria_rows(src: _Records) -> list[dict[str, Any]]:
    """The three criteria, their names and the aspects they decompose into."""
    scorecard, profile, result = src.scorecard, src.profile, src.result
    esr_rel = ESR_REL.as_posix()
    scorecard_rel = SCORECARD_REL.as_posix()
    profile_rel = PROFILE_REL.as_posix()
    rows: list[dict[str, Any]] = []
    criterion_measurements = [
        _measurement(
            "CR-01-M1",
            "the 2025 evaluation awarded three criterion scores",
            ESR_REL,
            "evaluation_result/criteria",
            expected_length=3,
        ),
        _measurement(
            "CR-01-M2",
            "the 2026 profile declares three criteria",
            PROFILE_REL,
            "criteria",
            expected_length=3,
        ),
    ]
    for position, criterion in enumerate(result["criteria"]):
        criterion_measurements.append(
            _measurement(
                f"CR-01-M{position + 3}",
                f"the 2025 evaluation's criterion {position + 1} is "
                f"{criterion['registry_criterion_id']}",
                ESR_REL,
                f"evaluation_result/criteria/#{position}/registry_criterion_id",
                expected=criterion["registry_criterion_id"],
            )
        )
        criterion_measurements.append(
            _measurement(
                f"CR-01-M{position + 6}",
                f"the 2026 profile's criterion {position + 1} is "
                f"{profile['criteria'][position]['registry_criterion_id']}",
                PROFILE_REL,
                f"criteria/#{position}/registry_criterion_id",
                expected=profile["criteria"][position]["registry_criterion_id"],
            )
        )
    rows.append(
        {
            "id": "CR-01",
            "area": "criteria",
            "rule": (
                "The three criteria the proposal is scored on, and their order: Excellence, "
                "Impact, Implementation."
            ),
            "affects": "both",
            "verdict": "equivalent",
            "settles": "as_applied_to_this_submission",
            "historical_value": "; ".join(c["wording"] for c in result["criteria"]),
            "current_value": ", ".join(c["registry_criterion_id"] for c in profile["criteria"]),
            "declared_status": "Inferred",
            "status_basis": (
                "The 2025 side is the evaluation's own recorded wording, which is evidence of "
                "what was applied to this submission. It is Inferred rather than Confirmed "
                "because no hash from the issuing body vouches for the report's bytes."
            ),
            "consequence": (
                "The historical profile declares the same three criteria in the same order, "
                "sourced to this row rather than copied."
            ),
            "citations": [
                _field_citation(
                    esr_rel,
                    f"evaluation_result/criteria/#{position}/wording",
                    f"the 2025 evaluation's recorded wording for criterion {position + 1}",
                    quote=criterion["wording"],
                )
                for position, criterion in enumerate(result["criteria"])
            ]
            + [
                _field_citation(
                    profile_rel, "criteria", "the 2026 profile's three criteria, in order"
                )
            ],
            "measurements": criterion_measurements,
        }
    )
    rows.append(
        {
            "id": "CR-02",
            "area": "criteria",
            "rule": (
                "Which criterion each of the ten aspects is graded under: four under Excellence, "
                "four under Impact, two under Implementation."
            ),
            "affects": "a number",
            "verdict": "defaulted",
            "settles": "call_wide",
            "current_value": "; ".join(
                f"{c['id']}: {', '.join(a['id'] for a in c['aspects'])}"
                for c in scorecard["criteria"]
            ),
            "declared_status": "Assumed",
            "status_basis": (
                "The assignment is read off the 2026 evaluation form through the scorecard. No "
                "2025 document in this repository states it: SM-01 shows the ten headings are "
                "the 2025 form's, and the assignment of a heading to a criterion is the "
                "evaluation form's, not the application form's."
            ),
            "defaulting": {
                "carried_from": (
                    "the 2026 evaluation form, through harness/evaluator_scorecard_msca_dn.json"
                ),
                "affected_rule": (
                    "which criterion each of the ten aspects is graded under, and therefore "
                    "which criterion score each piece of evidence moves"
                ),
                "risk": (
                    "A reassigned aspect moves evidence between criteria and changes two "
                    "criterion scores without changing any text. The comparison with the 2025 "
                    "result would then compare two different decompositions."
                ),
            },
            "consequence": (
                "The historical profile keeps the 2026 criterion-to-aspect assignment and "
                "records it as defaulted, not equivalent."
            ),
            "would_be_settled_by": [HIST_EF_REL.as_posix()],
            "citations": [
                _field_citation(
                    scorecard_rel,
                    "criteria",
                    "the 2026 evaluation form's aspects, grouped by criterion",
                ),
            ],
        }
    )
    return rows


def _weight_rows(src: _Records) -> list[dict[str, Any]]:
    """The per-criterion weights and the formula that forms the total."""
    scorecard = src.scorecard
    profile = src.profile
    ef = src.ef
    result = src.result
    scoring = src.scoring
    esr_rel = ESR_REL.as_posix()
    scorecard_rel = SCORECARD_REL.as_posix()
    rows: list[dict[str, Any]] = []
    weight_measurements: list[dict[str, Any]] = []
    for position, criterion in enumerate(result["criteria"]):
        weight_measurements.append(
            _measurement(
                f"WT-01-M{position * 2 + 1}",
                f"the 2025 evaluation weighted {criterion['criterion_id']} at "
                f"{criterion['weight_pct']}%",
                ESR_REL,
                f"evaluation_result/criteria/#{position}/weight_pct",
                expected=criterion["weight_pct"],
            )
        )
        weight_measurements.append(
            _measurement(
                f"WT-01-M{position * 2 + 2}",
                f"the 2026 scorecard weights {scorecard['criteria'][position]['id']} at "
                f"{scorecard['criteria'][position]['weight_pct']}%",
                SCORECARD_REL,
                f"criteria/#{position}/weight_pct",
                expected=scorecard["criteria"][position]["weight_pct"],
            )
        )
    rows.append(
        {
            "id": "WT-01",
            "area": "weights",
            "rule": "The criterion weights used to compute the weighted total.",
            "affects": "a number",
            "verdict": "equivalent",
            "settles": "as_applied_to_this_submission",
            "historical_value": ", ".join(
                f"{c['criterion_id']} {c['weight_pct']}%" for c in result["criteria"]
            ),
            "current_value": ", ".join(
                f"{c['id']} {c['weight_pct']}%" for c in scorecard["criteria"]
            ),
            "declared_status": "Inferred",
            "status_basis": (
                "Each weight is recorded twice: in the 2025 evaluation's own per-criterion "
                "wording, and in the 2026 scorecard derived from the evaluation form. Inferred "
                "for the reason CR-01 gives."
            ),
            "consequence": (
                "The historical profile keeps these weights, sourced to the 2025 evaluation's "
                "own record rather than carried over."
            ),
            "citations": [
                _field_citation(
                    esr_rel,
                    f"evaluation_result/criteria/#{position}/wording",
                    f"the weight the 2025 evaluation applied to criterion {position + 1}",
                    quote=criterion["wording"],
                )
                for position, criterion in enumerate(result["criteria"])
            ]
            + [
                _field_citation(
                    scorecard_rel,
                    "criteria",
                    "the 2026 scorecard's weights, derived from the evaluation form",
                )
            ],
            "measurements": weight_measurements,
        }
    )
    rows.append(
        {
            "id": "WT-02",
            "area": "weights",
            "rule": (
                "The evaluation form's statement that weighting serves the ranking and not the "
                "determination of whether a proposal passed the thresholds."
            ),
            "affects": "an interpretation",
            "verdict": "defaulted",
            "settles": "call_wide",
            "current_value": scoring["weighting_source_quote"],
            "declared_status": "Assumed",
            "status_basis": (
                "Only the 2026 evaluation form states the sentence. The 2025 evaluation's "
                "recorded total was compared with a threshold of 70 of 100, which TH-02 "
                "measures; this row does not adjudicate how that sits beside the sentence, "
                "because the 2025 form is what would."
            ),
            "defaulting": {
                "carried_from": "the 2026 evaluation form, page 2",
                "affected_rule": (
                    "whether a pass is decided on the three unweighted criterion scores, with "
                    "the weighted total used for ranking"
                ),
                "risk": (
                    "If the 2025 form put weighting into threshold determination, a pass or fail "
                    "reading of the 2025 criterion scores would be wrong. No score moves; its "
                    "interpretation does."
                ),
            },
            "consequence": (
                "The historical profile carries the sentence as defaulted. A pass or fail "
                "statement about the 2025 result rests on it and has to say so."
            ),
            "would_be_settled_by": [HIST_EF_REL.as_posix()],
            "citations": [
                _verified(
                    ef,
                    2,
                    scoring["weighting_source_quote"],
                    "the 2026 evaluation form on what weighting is for",
                ),
            ],
        }
    )
    return rows


def _threshold_rows(src: _Records) -> list[dict[str, Any]]:
    """The per-criterion and overall thresholds, the maximum and its resolution."""
    scorecard = src.scorecard
    profile = src.profile
    ef = src.ef
    annexes = src.annexes
    result = src.result
    scoring = src.scoring
    esr_rel = ESR_REL.as_posix()
    scorecard_rel = SCORECARD_REL.as_posix()
    rows: list[dict[str, Any]] = []
    threshold_measurements = [
        _measurement(
            f"TH-01-M{position + 1}",
            f"the 2025 evaluation applied a threshold of {criterion['threshold']} to "
            f"{criterion['criterion_id']}",
            ESR_REL,
            f"evaluation_result/criteria/#{position}/threshold",
            expected=criterion["threshold"],
        )
        for position, criterion in enumerate(result["criteria"])
    ] + [
        _measurement(
            "TH-01-M4",
            "the 2026 scorecard declares the same per-criterion threshold",
            SCORECARD_REL,
            "scoring/individual_threshold",
            expected=scoring["individual_threshold"],
        )
    ]
    rows.append(
        {
            "id": "TH-01",
            "area": "thresholds",
            "rule": "The per-criterion threshold a criterion score must reach.",
            "affects": "a number",
            "verdict": "equivalent",
            "settles": "as_applied_to_this_submission",
            "historical_value": ", ".join(
                f"{c['criterion_id']} threshold {c['threshold']}" for c in result["criteria"]
            ),
            "current_value": str(scoring["individual_threshold"]),
            "declared_status": "Inferred",
            "status_basis": (
                "The 2025 evaluation records the threshold beside each of its three criterion "
                "scores. Inferred for the reason CR-01 gives."
            ),
            "consequence": "The historical profile keeps the per-criterion threshold unchanged.",
            "citations": [
                _field_citation(
                    esr_rel,
                    f"evaluation_result/criteria/#{position}/wording",
                    f"the threshold recorded beside criterion {position + 1}",
                    quote=criterion["wording"],
                )
                for position, criterion in enumerate(result["criteria"])
            ]
            + [
                _verified(
                    annexes,
                    scoring["individual_threshold_source"]["page"],
                    scoring["individual_threshold_source"]["quote"],
                    "the 2026 General Annexes on the per-criterion threshold",
                )
            ],
            "measurements": threshold_measurements,
        }
    )
    rows.append(
        {
            "id": "TH-02",
            "area": "thresholds",
            "rule": "The overall threshold, and the total it applies to.",
            "affects": "a number",
            "verdict": "equivalent",
            "settles": "as_applied_to_this_submission",
            "historical_value": result["result_wording"],
            "current_value": f"{scoring['overall_threshold']} of {scoring['overall_max']}",
            "declared_status": "Inferred",
            "status_basis": (
                "The 2025 evaluation's recorded result wording carries the threshold and the "
                "maximum it is out of. Inferred for the reason CR-01 gives."
            ),
            "consequence": "The historical profile keeps the overall threshold and maximum.",
            "citations": [
                _field_citation(
                    esr_rel,
                    "evaluation_result/result_wording",
                    "the 2025 evaluation's recorded overall threshold and maximum",
                    quote=result["result_wording"],
                ),
                _verified(
                    ef,
                    2,
                    scoring["threshold_source_quote"],
                    "the 2026 evaluation form on the overall threshold",
                ),
            ],
            "measurements": [
                _measurement(
                    "TH-02-M1",
                    "the 2025 evaluation records an overall threshold of "
                    f"{result['overall_threshold']}",
                    ESR_REL,
                    "evaluation_result/overall_threshold",
                    expected=result["overall_threshold"],
                ),
                _measurement(
                    "TH-02-M2",
                    f"out of {result['overall_max']}",
                    ESR_REL,
                    "evaluation_result/overall_max",
                    expected=result["overall_max"],
                ),
                _measurement(
                    "TH-02-M3",
                    "the 2026 scorecard declares the same overall threshold",
                    SCORECARD_REL,
                    "scoring/overall_threshold",
                    expected=scoring["overall_threshold"],
                ),
                _measurement(
                    "TH-02-M4",
                    "and the same maximum",
                    SCORECARD_REL,
                    "scoring/overall_max",
                    expected=scoring["overall_max"],
                ),
            ],
        }
    )
    rows.append(
        {
            "id": "TH-03",
            "area": "thresholds",
            "rule": (
                "Which authority sets the overall threshold where the General Annexes and the "
                "evaluation form disagree. The annexes state a generic threshold on the "
                "unweighted sum; the form states one on the weighted total."
            ),
            "affects": "an interpretation",
            "verdict": "defaulted",
            "settles": "call_wide",
            "current_value": scoring["annex_d_override"]["resolution"],
            "declared_status": "Assumed",
            "status_basis": (
                "The resolution was taken on the 2026 annexes and the 2026 form. Neither 2025 "
                "document is in this repository, so the resolution is carried forward rather "
                "than re-derived."
            ),
            "defaulting": {
                "carried_from": (
                    "the 2026 General Annexes and the 2026 evaluation form, resolved in "
                    "docs/tier4_orchestration_state/decision_log/"
                    "msca-dn-pe02-evaluation-bundle_2026-10-04.json"
                ),
                "affected_rule": (
                    "which overall threshold the 2025 criterion scores are read against, and on "
                    "whose authority"
                ),
                "risk": (
                    "The 2025 annexes may state a different generic threshold, or not permit a "
                    "call to override it. TH-02 measures 70 of 100 as applied to this "
                    "submission, so the risk is to the general rule and not to this result."
                ),
            },
            "consequence": (
                "The historical profile keeps the override and records it as defaulted. A "
                "statement about any other 2025 proposal may not rest on it."
            ),
            "would_be_settled_by": [HIST_ANNEXES_REL.as_posix(), HIST_EF_REL.as_posix()],
            "citations": [
                _field_citation(
                    scorecard_rel,
                    "scoring/annex_d_override/resolution",
                    "the resolution taken on the 2026 documents",
                ),
            ],
        }
    )
    rows.append(
        {
            "id": "TH-04",
            "area": "thresholds",
            "rule": "The maximum a criterion score may reach.",
            "affects": "a number",
            "verdict": "equivalent",
            "settles": "as_applied_to_this_submission",
            "historical_value": "the maximum recorded beside each criterion score is 5.00",
            "current_value": "5, the upper end of the scorecard's scale",
            "declared_status": "Inferred",
            "status_basis": (
                "The 2025 evaluation prints the maximum beside every criterion score it "
                "records. Inferred for the reason CR-01 gives. The claim is the maximum and "
                "nothing else: row TH-05 carries the resolution, which this record does not "
                "state."
            ),
            "consequence": "The historical profile keeps the maximum.",
            "citations": [
                _field_citation(
                    esr_rel,
                    "evaluation_result/criteria/#0/wording",
                    "the 2025 evaluation's recorded maximum for criterion 1",
                    quote=result["criteria"][0]["wording"],
                ),
                _verified(
                    ef,
                    2,
                    scoring["scale_source_quote"],
                    "the 2026 evaluation form on the range and its resolution",
                ),
            ],
            "measurements": [
                _measurement(
                    "TH-04-M1",
                    "the 2026 scorecard declares the scale",
                    SCORECARD_REL,
                    "scoring/scale",
                    expected=scoring["scale"],
                ),
            ],
        }
    )
    rows.append(
        {
            "id": "TH-05",
            "area": "thresholds",
            "rule": "The resolution a criterion score is awarded to.",
            "affects": "a number",
            "verdict": "defaulted",
            "settles": "call_wide",
            "current_value": "one decimal place",
            "declared_status": "Assumed",
            "status_basis": (
                "Only the 2026 evaluation form states a resolution. The 2025 evaluation prints "
                "its three scores to two decimals, as 4.20, 4.50 and 4.20, and states no "
                "resolution rule. All three happen to end in zero, which is consistent with a "
                "one-decimal rule and is not evidence of one. Calling this equivalent would be "
                "recording the absence of a visible difference as agreement."
            ),
            "defaulting": {
                "carried_from": "the 2026 evaluation form, page 2",
                "affected_rule": (
                    "the resolution the harness awards a criterion score to, and therefore the "
                    "rounding applied before the weighted total is formed"
                ),
                "risk": (
                    "A coarser 2025 resolution moves a criterion score by up to half a point. "
                    "The total weights excellence by ten, so that is five points of the "
                    "weighted total on criterion 1 alone, and the comparison with the recorded "
                    "85.80 shifts without any judgement changing."
                ),
            },
            "consequence": (
                "The historical profile keeps one decimal place and records it as defaulted."
            ),
            "would_be_settled_by": [HIST_EF_REL.as_posix()],
            "citations": [
                _verified(
                    ef,
                    2,
                    scoring["scale_source_quote"],
                    "the 2026 evaluation form, the only side that states a resolution",
                ),
                _field_citation(
                    scorecard_rel,
                    "scoring/scale",
                    "the resolution as the scorecard carries it",
                ),
            ],
        }
    )
    return rows


def _evaluator_instruction_rows(src: _Records) -> list[dict[str, Any]]:
    """What an evaluator was told: the levels, the form and its tags."""
    esr = src.esr
    scorecard = src.scorecard
    profile = src.profile
    ef = src.ef
    annexes = src.annexes
    result = src.result
    scoring = src.scoring
    esr_rel = ESR_REL.as_posix()
    scorecard_rel = SCORECARD_REL.as_posix()
    profile_rel = PROFILE_REL.as_posix()
    rows: list[dict[str, Any]] = []
    rows.append(
        {
            "id": "EI-01",
            "area": "evaluator_instructions",
            "rule": "The six score-level descriptions, 0 to 5, an evaluator grades against.",
            "affects": "both",
            "verdict": "defaulted",
            "settles": "call_wide",
            "current_value": "; ".join(f"{k}: {v}" for k, v in scoring["levels"].items()),
            "declared_status": "Assumed",
            "status_basis": (
                "The six sentences are the 2026 evaluation form's, page 2. No 2025 document in "
                "this repository carries them, and the 2025 evaluation's record quotes none of "
                "them."
            ),
            "defaulting": {
                "carried_from": "the 2026 evaluation form, page 2",
                "affected_rule": "what a criterion score of 4 means",
                "risk": (
                    "A changed level sentence changes every grade the assessor awards. A "
                    "comparison with the 2025 total would then be between two scales wearing "
                    "the same numbers."
                ),
            },
            "consequence": (
                "The historical profile keeps the level descriptions and records them as "
                "defaulted. This is the largest single unsourced input to a numerical "
                "comparison with the 2025 result."
            ),
            "would_be_settled_by": [HIST_EF_REL.as_posix()],
            "citations": [
                _verified(
                    ef,
                    2,
                    scoring["levels"]["4"],
                    "the 2026 evaluation form's level 4 description, one of six",
                ),
                _field_citation(
                    scorecard_rel,
                    "scoring/levels",
                    "all six descriptions, as the scorecard holds them",
                ),
            ],
        }
    )
    rows.append(
        {
            "id": "EI-02",
            "area": "evaluator_instructions",
            "rule": "Which version of the evaluation form was in force for the 2025 call.",
            "affects": "an interpretation",
            "verdict": "unresolved",
            "settles": "call_wide",
            "current_value": (
                f"version {scorecard['provenance']['version']} dated "
                f"{scorecard['provenance']['version_date']}"
            ),
            "declared_status": "Unresolved",
            "status_basis": (
                "The stored form declares one version and one date. Nothing states which "
                "version the 2025 evaluation used."
            ),
            "limitation": (
                f"The stored evaluation form declares version {scorecard['provenance']['version']}, "
                f"dated {scorecard['provenance']['version_date']}. No record in this repository "
                "states the version in force when the 2025 submission was evaluated, and "
                "whether that date precedes or follows the evaluation is itself unrecorded. "
                "Every defaulted row in this area rests on this gap."
            ),
            "consequence": (
                "The historical profile records that the evaluation-form version behind its "
                "defaulted rules is unknown. It does not claim the stored version applied in "
                "2025."
            ),
            "would_be_settled_by": [HIST_EF_REL.as_posix(), HIST_CALL_REL.as_posix()],
            "citations": [
                _field_citation(
                    scorecard_rel,
                    "provenance/version_date",
                    "the version date the stored evaluation form declares",
                    quote=scorecard["provenance"]["version_date"],
                ),
            ],
            "measurements": [
                _measurement(
                    "EI-02-M1",
                    "the stored evaluation form's declared version",
                    SCORECARD_REL,
                    "provenance/version",
                    expected=scorecard["provenance"]["version"],
                ),
                _measurement(
                    "EI-02-M2",
                    "and its declared date",
                    SCORECARD_REL,
                    "provenance/version_date",
                    expected=scorecard["provenance"]["version_date"],
                ),
            ],
        }
    )
    rows.append(
        {
            "id": "EI-03",
            "area": "evaluator_instructions",
            "rule": (
                "Scores are awarded for the criteria and not for the individual aspects listed "
                "under them."
            ),
            "affects": "a number",
            "verdict": "equivalent",
            "settles": "as_applied_to_this_submission",
            "historical_value": (
                f"the 2025 evaluation records {len(result['criteria'])} criterion scores and "
                f"{len(esr['observations'])} observations, none of which carries a score"
            ),
            "current_value": scoring["no_aspect_scores_rule"]["quote"],
            "declared_status": "Inferred",
            "status_basis": (
                "The 2025 side is an absence that is measured rather than assumed: three "
                "criterion scores are recorded and no observation carries a score field. An "
                "absence evidences that the rule was applied; it does not confirm the rule's "
                "text, which is why this is Inferred."
            ),
            "consequence": (
                "The historical profile keeps the rule that the ten aspect cells inform a "
                "criterion score and are never averaged into one."
            ),
            "citations": [
                _field_citation(
                    esr_rel,
                    "evaluation_result/criteria",
                    "three criterion scores, and no aspect score, in the 2025 evaluation",
                ),
                _field_citation(
                    esr_rel,
                    "observations",
                    "every recorded observation, none of which carries a score",
                ),
                _verified(
                    annexes,
                    scoring["no_aspect_scores_rule"]["page"],
                    scoring["no_aspect_scores_rule"]["quote"],
                    "the 2026 General Annexes on what a score is awarded for",
                ),
            ],
            "measurements": [
                _measurement(
                    "EI-03-M1",
                    "three criterion scores",
                    ESR_REL,
                    "evaluation_result/criteria",
                    expected_length=len(result["criteria"]),
                ),
                _measurement(
                    "EI-03-M2",
                    f"{len(esr['observations'])} observations, none with a score",
                    ESR_REL,
                    "observations",
                    expected_length=len(esr["observations"]),
                ),
            ],
        }
    )
    rows.append(
        {
            "id": "EI-04",
            "area": "evaluator_instructions",
            "rule": (
                "The applicability-tag grammar that selects which of the evaluation form's "
                "aspects a Doctoral Network proposal is graded on."
            ),
            "affects": "a number",
            "verdict": "defaulted",
            "settles": "call_wide",
            "current_value": scorecard["provenance"]["dn_scope_rule"],
            "declared_status": "Assumed",
            "status_basis": (
                "The grammar is the evaluation form's alone: this module refuses to render if "
                "either application form carries an applicability tag, and neither does. So the "
                "form-equivalence record over the two application forms cannot reach it, and no "
                "2025 document in this repository states it."
            ),
            "defaulting": {
                "carried_from": "the 2026 evaluation form, through the scorecard's scope rule",
                "affected_rule": (
                    "which of the evaluation form's aspects are the ten a Doctoral Network "
                    "proposal is graded on"
                ),
                "risk": (
                    "If the 2025 form tagged aspects differently, the ten-aspect set is the "
                    "wrong set and every cell is graded against an aspect the 2025 evaluators "
                    "did not use."
                ),
            },
            "consequence": (
                "The historical profile keeps the tag grammar and the scope rule, recorded as "
                "defaulted. SM-01 shows the ten headings are the 2025 form's; it does not show "
                "that the 2025 evaluation form selected the same ten."
            ),
            "would_be_settled_by": [HIST_EF_REL.as_posix()],
            "citations": [
                _field_citation(
                    scorecard_rel,
                    "provenance/dn_scope_rule",
                    "the scope rule derived from the 2026 evaluation form's tags",
                ),
                _field_citation(
                    profile_rel,
                    "option_tag_grammar",
                    "the tag vocabulary the 2026 profile declares",
                ),
            ],
        }
    )
    return rows


def _variant_rows(src: _Records) -> list[dict[str, Any]]:
    """Which Doctoral Networks variant the submission was evaluated as."""
    profile, fidelity, v5, v6 = src.profile, src.fidelity, src.v5, src.v6
    profile_rel = PROFILE_REL.as_posix()
    fidelity_rel = FIDELITY_REL.as_posix()
    rows: list[dict[str, Any]] = []
    dn_type = fidelity["provenance"]["historical_submission"]["dn_type"]
    rows.append(
        {
            "id": "VA-01",
            "area": "variant",
            "rule": "Which Doctoral Network implementation mode the 2025 submission used.",
            "affects": "an interpretation",
            "verdict": "equivalent",
            "settles": "as_applied_to_this_submission",
            "historical_value": dn_type["value"],
            "current_value": profile["implementation_mode"],
            "declared_status": "Inferred",
            "status_basis": (
                "The fidelity register declares the mode Confirmed on a phrase its authoring "
                "tool checks on page 32 of the sanitised copy. This row is Inferred rather than "
                "Confirmed because no hash from an issuing body vouches for that copy's bytes."
            ),
            "consequence": (
                "The historical profile declares the same implementation mode, sourced to the "
                "submission's own text."
            ),
            "citations": [
                _field_citation(
                    fidelity_rel,
                    "provenance/historical_submission/dn_type/basis",
                    "the page of the submission the mode is checked on",
                    quote=dn_type["basis"],
                ),
                _field_citation(
                    profile_rel,
                    "implementation_mode",
                    "the mode the 2026 profile declares",
                    quote=profile["implementation_mode"],
                ),
            ],
            "measurements": [
                _measurement(
                    "VA-01-M1",
                    "the fidelity register declares the mode Confirmed",
                    FIDELITY_REL,
                    "provenance/historical_submission/dn_type/declared_status",
                    expected="Confirmed",
                ),
                _measurement(
                    "VA-01-M2",
                    "and the 2026 profile declares the same mode",
                    PROFILE_REL,
                    "implementation_mode",
                    expected=profile["implementation_mode"],
                ),
            ],
        }
    )
    mode_quote = "the implementation mode applied to (i.e. DN, DN-ID or DN-JD)"
    rows.append(
        {
            "id": "VA-02",
            "area": "variant",
            "rule": (
                "The implementation modes the application form recognises, and which must be "
                "declared in the Part B header."
            ),
            "affects": "an interpretation",
            "verdict": "equivalent",
            "settles": "call_wide",
            "historical_value": "DN, DN-ID or DN-JD",
            "current_value": "DN, DN-ID or DN-JD",
            "declared_status": "Inferred",
            "status_basis": (
                "The same sentence is located in both application forms, verbatim, and the "
                "2025 form is a 2025-call document rather than evidence about one submission."
            ),
            "consequence": (
                "The historical profile may declare the mode vocabulary as sourced to the 2025 "
                "form, not carried from the 2026 one."
            ),
            "citations": [
                _verified(
                    v5,
                    min(v5.occurrences(mode_quote)),
                    mode_quote,
                    "the 2025 form on the modes a Part B header must declare",
                ),
                _verified(
                    v6,
                    min(v6.occurrences(mode_quote)),
                    mode_quote,
                    "the same sentence in the 2026 form",
                ),
            ],
        }
    )
    return rows


def _section_mapping_rows(src: _Records) -> list[dict[str, Any]]:
    """The Part B structure the criteria are read against."""
    scorecard = src.scorecard
    profile = src.profile
    appendix = src.appendix
    fidelity = src.fidelity
    v5 = src.v5
    v6 = src.v6
    anchors = src.anchors
    scorecard_rel = SCORECARD_REL.as_posix()
    rows: list[dict[str, Any]] = []
    rows.append(
        {
            "id": "SM-01",
            "area": "section_mapping",
            "rule": (
                "The ten numbered Part B aspect headings the criteria decompose into, sections "
                "1.1 to 3.2."
            ),
            "affects": "an interpretation",
            "verdict": "equivalent",
            "settles": "call_wide",
            "historical_value": (
                "the same ten headings, all occurring verbatim in the 2025 form, and its "
                "criteria table carries no eleventh aspect anchor"
            ),
            "current_value": "the ten headings the scorecard derives from the 2026 form",
            "declared_status": "Inferred",
            "status_basis": (
                "Ten citations, one per heading, each located in the 2025 form and each quote "
                "verified to occur on the page it cites. That settles one direction. The other "
                "is measured: the anchors printed across each form's criteria table are read "
                "out and compared, with the page either side of the table required to carry "
                "none, and both sets are exactly "
                + " ".join(anchors)
                + ". This module refuses to render if either set stops matching the "
                "scorecard's, or if the page rule stops matching the scorecard's own declared "
                "2026 pages."
            ),
            "consequence": (
                "The historical profile reuses the criterion-to-section mapping unchanged, with "
                "this row as the source."
            ),
            "citations": list(_aspect_heading_citations(scorecard, v5, v6)),
            "measurements": [
                _measurement(
                    f"SM-01-M{position}",
                    f"criterion {criterion['id']} carries the aspects this row enumerates",
                    SCORECARD_REL,
                    f"criteria/#{position - 1}/aspects",
                    expected_length=len(criterion["aspects"]),
                )
                for position, criterion in enumerate(scorecard["criteria"], start=1)
            ],
        }
    )
    cap_quote = "The maximum total length for this document is 34 pages."
    inner_cap_quote = (
        "Of the maximum 30 pages applied to sections 1, 2 and 3, applicants are free to decide "
        "on the allocation of pages between the sections."
    )
    rows.append(
        {
            "id": "SM-02",
            "area": "section_mapping",
            "rule": (
                "The Part B1 length limits: 34 pages in total, of which 30 are available to "
                "sections 1 to 3."
            ),
            "affects": "an interpretation",
            "verdict": "equivalent",
            "settles": "call_wide",
            "historical_value": "34 pages in total, 30 for sections 1 to 3",
            "current_value": "34 pages in total, 30 for sections 1 to 3",
            "declared_status": "Inferred",
            "status_basis": (
                "Both sentences are located in the 2025 form and in the 2026 form, verbatim. "
                "The form-equivalence record is cited as corroboration and is within the scope "
                "it measured; the 2025 form itself is what settles the row."
            ),
            "consequence": (
                "No page-based judgment is admissible over the sanitised copy at all, which the "
                "fidelity register declares. The limits are recorded because the historical "
                "profile's structural authority has to name them."
            ),
            "citations": [
                _verified(v5, min(v5.occurrences(cap_quote)), cap_quote, "the 2025 form's total cap"),
                _verified(
                    v5,
                    min(v5.occurrences(inner_cap_quote)),
                    inner_cap_quote,
                    "the 2025 form's cap on sections 1 to 3",
                ),
                _verified(v6, min(v6.occurrences(cap_quote)), cap_quote, "the 2026 form's total cap"),
                _field_citation(
                    scorecard_rel,
                    "provenance/v5_equivalence/statement",
                    "the form-equivalence record, within the section structure it measured",
                    quote=scorecard["provenance"]["v5_equivalence"]["statement"],
                ),
            ],
        }
    )
    last_b2_quote = "10. Declaration on the use of AI"
    new_b2_quote = (
        "11. RAISE DN (Only for applicants of HORIZON-RAISE-2026-01-MSCA, 1 page)"
    )
    rows.append(
        {
            "id": "SM-03",
            "area": "section_mapping",
            "rule": "Which sections Part B2 contains.",
            "affects": "an interpretation",
            "verdict": "differs",
            "settles": "call_wide",
            "historical_value": "Part B2 ends at section 10, the declaration on the use of AI",
            "current_value": "Part B2 adds section 11, RAISE DN, for a different call",
            "difference": (
                "The 2026 form adds a Part B2 section 11 the 2025 form does not have. It is "
                "reserved for applicants of another call, so no 2025 submission could have had "
                "one."
            ),
            "declared_status": "Inferred",
            "status_basis": (
                "The 2025 form's section 10 is followed by its example block; the 2026 form's "
                "section 10 is followed by section 11. Both quotes are verified on the pages "
                "they cite."
            ),
            "consequence": (
                "The appendix mapping's rule excluding Part B2 section 11 has no subject under "
                "the 2025 form. The historical profile keeps the rule and records that it is "
                "vacuous rather than deleting it."
            ),
            "citations": [
                _verified(
                    v5,
                    min(v5.occurrences(last_b2_quote)),
                    "10. Declaration on the use of AI Example, not to be completed",
                    "the 2025 form's last Part B2 section, followed by its example block",
                ),
                _verified(
                    v6,
                    min(v6.occurrences(new_b2_quote)),
                    new_b2_quote,
                    "the section the 2026 form adds after section 10",
                ),
            ],
        }
    )
    return rows


def _appendix_mapping_rows(src: _Records) -> list[dict[str, Any]]:
    """The cross-references that route table rows to criteria."""
    profile, appendix, v5, v6, anchors = src.profile, src.appendix, src.v5, src.v6, src.anchors
    appendix_rel = APPENDIX_REL.as_posix()
    rows: list[dict[str, Any]] = []
    appendix_citations = list(_appendix_quote_citations(appendix, v5, v6))
    rows.append(
        {
            "id": "AM-01",
            "area": "appendix_mapping",
            "rule": (
                "The cross-references that route table rows to criteria at the "
                "criterion-grading stage."
            ),
            "affects": "a number",
            "verdict": "equivalent",
            "settles": "call_wide",
            "historical_value": (
                f"all {len(appendix_citations)} distinct cross-reference sentences occur "
                "verbatim in the 2025 form"
            ),
            "current_value": (
                f"{len(appendix['rows'])} mapping rows, derived from the 2026 form"
            ),
            "declared_status": "Inferred",
            "status_basis": (
                "One citation per distinct sentence, each located in the 2025 form and verified "
                "on the page it cites. This is the row the form-equivalence record could not "
                "settle: that record measured headings, tables, caps and section numbering, not "
                "the instructional sentences the mapping routes on. The claim is an inclusion "
                "and not a set equality. Every sentence the 2026 mapping routes on is in the "
                "2025 form; whether the 2025 form carries a further cross-reference the mapping "
                "has no row for is unmeasured, and cannot be searched for without the 2025 "
                "mapping's own list. Row SM-01 settles the aspect anchors in both directions, "
                "which bounds what such a sentence could reroute."
            ),
            "consequence": (
                "The historical profile reuses the appendix mapping unchanged, sourced to the "
                "2025 form rather than carried over on the form-equivalence record. The "
                "unmeasured direction stays an uncertainty of this matrix and is not closed by "
                "this row."
            ),
            "citations": appendix_citations
            + [
                _field_citation(
                    appendix_rel,
                    "rows",
                    "the mapping rows these sentences are the authority for",
                )
            ],
        }
    )
    return rows


def _scoring_assumption_rows(src: _Records) -> list[dict[str, Any]]:
    """The harness's own scoring decisions, which no call states."""
    repo_root = src.repo_root
    scorecard = src.scorecard
    profile = src.profile
    appendix = src.appendix
    fidelity = src.fidelity
    result = src.result
    scoring = src.scoring
    esr_rel = ESR_REL.as_posix()
    scorecard_rel = SCORECARD_REL.as_posix()
    fidelity_rel = FIDELITY_REL.as_posix()
    rows: list[dict[str, Any]] = []
    rows.append(
        {
            "id": "SA-01",
            "area": "scoring_assumption",
            "rule": (
                "The weighted total is each criterion score times its weight in percent over "
                "five, summed."
            ),
            "affects": "a number",
            "verdict": "equivalent",
            "settles": "as_applied_to_this_submission",
            "historical_value": result["result_wording"],
            "current_value": scoring["total_formula"],
            "declared_status": "Inferred",
            "status_basis": (
                "Arithmetic evidence: the formula applied to the 2025 evaluation's own recorded "
                "criterion scores reproduces its own recorded total. This module refuses to "
                "render if it stops doing so."
            ),
            "consequence": (
                "The historical profile keeps the total formula. It is the one scoring rule "
                "whose 2025 application is evidenced by arithmetic rather than by wording."
            ),
            "citations": [
                _field_citation(
                    esr_rel,
                    "evaluation_result/total",
                    "the total the formula has to reproduce",
                ),
                _field_citation(
                    scorecard_rel,
                    "scoring/total_formula",
                    "the formula, as the 2026 scorecard holds it",
                    quote=scoring["total_formula"],
                ),
            ],
            "measurements": [
                _measurement(
                    "SA-01-M1",
                    "the recorded total the formula reproduces",
                    ESR_REL,
                    "evaluation_result/total",
                    expected=result["total"],
                ),
            ],
        }
    )
    rows.append(
        {
            "id": "SA-02",
            "area": "scoring_assumption",
            "rule": (
                "Criterion grading draws five samples per criterion and reports the median with "
                "its spread, labelled within-assessor repeatability."
            ),
            "affects": "a number",
            "verdict": "era_neutral",
            "settles": "as_applied_to_this_submission",
            "current_value": "N=5 per criterion score, median and spread reported",
            "declared_status": "Inferred",
            "status_basis": (
                "The specification's decisions 5 and 11 fix the sample count and the statistic. "
                "The citation resolves as text in the specification, so a reworded decision "
                "fails the check."
            ),
            "why_era_neutral": (
                "The sample count and the statistic belong to the assessing harness, not to "
                "either call. No call document states them, and neither can differ between the "
                "two calls."
            ),
            "consequence": (
                "The historical profile inherits the method. The matrix records that it is not "
                "a 2025 rule and cannot be sourced to one, so a difference between the "
                "assessor's median and the 2025 total is not attributable to a rule change."
            ),
            "citations": [
                _verified_text(
                    repo_root,
                    SPEC_REL,
                    "five samples per criterion",
                    "the specification's decision on the criterion-grading stage",
                ),
                _verified_text(
                    repo_root,
                    SPEC_REL,
                    "N=5 for the three criterion scores",
                    "the specification's decision on the sample count and the statistic",
                ),
            ],
        }
    )
    rows.append(
        {
            "id": "SA-03",
            "area": "scoring_assumption",
            "rule": (
                "Where the evidence pack carries no claim ledger, a cell reports grounding "
                "unassessable — never failed and never passed."
            ),
            "affects": "an interpretation",
            "verdict": "era_neutral",
            "settles": "as_applied_to_this_submission",
            "current_value": "grounding unassessable where no ledger reaches the pack",
            "declared_status": "Inferred",
            "status_basis": (
                "The specification's decision 14 states the rule. The citation resolves as text "
                "in the specification."
            ),
            "why_era_neutral": (
                "The rule governs how this harness reports an axis it cannot assess over a "
                "damaged copy. No call document states it, in either year."
            ),
            "consequence": (
                "The historical profile inherits the rule. A grounding result is reported as "
                "unassessable and is never read as a score the 2025 evaluators would recognise."
            ),
            "citations": [
                _verified_text(
                    repo_root,
                    SPEC_REL,
                    "the cell reports grounding **unassessable**",
                    "the specification's decision on an unassessable axis",
                ),
            ],
        }
    )
    assessed = fidelity["provenance"]["current_assessment_artifact"]
    rows.append(
        {
            "id": "SA-04",
            "area": "scoring_assumption",
            "rule": (
                "The assessed text is a sanitised derivative produced after the evaluation, not "
                "the text the 2025 evaluation read."
            ),
            "affects": "both",
            "verdict": "era_neutral",
            "settles": "as_applied_to_this_submission",
            "historical_value": assessed["statement"],
            "declared_status": "Inferred",
            "status_basis": (
                "The fidelity register states it over the file it pins by hash. This is a "
                "property of one derivative, measured on it."
            ),
            "why_era_neutral": (
                "The candidate's fidelity is not a rule either call states. It is the condition "
                "of the document being assessed, and it bounds every row above regardless of "
                "which year's rules apply."
            ),
            "consequence": (
                "No result over this copy is a result over the submission. The historical "
                "profile changes nothing about that, and a comparison with the 2025 total "
                "carries the statement."
            ),
            "citations": [
                _field_citation(
                    fidelity_rel,
                    "provenance/current_assessment_artifact/statement",
                    "the register's statement over the file it pins",
                    quote=assessed["statement"],
                ),
            ],
            "measurements": [
                _measurement(
                    "SA-04-M1",
                    "the assessed file is declared not to be the submitted document",
                    FIDELITY_REL,
                    "provenance/current_assessment_artifact/is_submitted_document",
                    expected=False,
                ),
            ],
        }
    )
    rows.append(
        {
            "id": "SA-05",
            "area": "scoring_assumption",
            "rule": (
                "A blind cell reports addressal and grounding as two values, and never blends "
                "them into one."
            ),
            "affects": "an interpretation",
            "verdict": "era_neutral",
            "settles": "as_applied_to_this_submission",
            "current_value": "two values per cell, grounding never folded into addressal",
            "declared_status": "Inferred",
            "status_basis": (
                "The specification's decision 4 states the rule and its reason. The citation "
                "resolves as text in the specification, so a reworded decision fails the check."
            ),
            "why_era_neutral": (
                "What a cell reports is this harness's own output shape. Neither call states it, "
                "and neither could: no 2025 or 2026 document knows of a cell."
            ),
            "consequence": (
                "The historical profile inherits the two-value cell. A reader comparing a cell "
                "with a 2025 criterion score is comparing an assessor's two axes with an "
                "evaluator's single grade, which this row records as a method difference rather "
                "than a rule difference."
            ),
            "citations": [
                _verified_text(
                    repo_root,
                    SPEC_REL,
                    "reports addressal and grounding as two values",
                    "the specification's decision on what a blind cell reports",
                ),
            ],
        }
    )
    rows.append(
        {
            "id": "SA-06",
            "area": "scoring_assumption",
            "rule": (
                "The criterion scorer reads the complete criterion section plus the declared "
                "appendix rows, with no selection and no budget filler."
            ),
            "affects": "a number",
            "verdict": "era_neutral",
            "settles": "as_applied_to_this_submission",
            "current_value": (
                "the whole section verbatim, within the 32,768-token pack budget, with every "
                "declared appendix row resolved"
            ),
            "declared_status": "Inferred",
            "status_basis": (
                "The specification states the input and its bound, and both citations resolve "
                "as text in it. What the scorer reads is a harness decision, not a call rule, "
                "which is why it is recorded here rather than compared across the two years."
            ),
            "why_era_neutral": (
                "An evaluator reads the proposal. A pack budget and a selection rule are "
                "properties of the assessing harness, so no call document of either year states "
                "them."
            ),
            "consequence": (
                "The historical profile inherits the input rule. A truncated or selected input "
                "would change a criterion score without any 2025 rule changing, which is why "
                "the bound is recorded as a scoring assumption and not left implicit."
            ),
            "citations": [
                _verified_text(
                    repo_root,
                    SPEC_REL,
                    "the criterion lane carries no selection at all",
                    "the specification on selection in the criterion lane",
                ),
                _verified_text(
                    repo_root,
                    SPEC_REL,
                    "the assembled input fit the budget without truncation",
                    "the specification's acceptance condition on the criterion input",
                ),
            ],
        }
    )
    return rows


#: The nine area builders, in the order the matrix lists their rows.
AREA_BUILDERS = (
    _call_identity_rows,
    _criteria_rows,
    _weight_rows,
    _threshold_rows,
    _evaluator_instruction_rows,
    _variant_rows,
    _section_mapping_rows,
    _appendix_mapping_rows,
    _scoring_assumption_rows,
)


def _rows(repo_root: Path) -> list[dict[str, Any]]:
    """Every row of the matrix, one area at a time."""
    src = _records(repo_root)
    rows: list[dict[str, Any]] = []
    for build in AREA_BUILDERS:
        rows.extend(build(src))
    return rows


# --------------------------------------------------------------------------- #
# The source index
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class _Basis:
    """Where an authentication above ``computed_only`` is recorded.

    A rank saying somebody vouched for the bytes has to say where that is
    written down, or the rank rests on this module's own word — which is the
    thing the rank is supposed to improve on. The pointer is resolved against
    the record itself and the resolved value must carry *must_contain*, so the
    index cannot keep claiming a provenance a record has stopped stating.
    """

    #: ``/``-separated key path into the record.
    pointer: str
    #: The wording the resolved value must carry, lower-cased.
    must_contain: str
    #: What the index states once the pointer resolves.
    wording: str


@dataclass(frozen=True)
class _Obtained:
    """A document or record this repository holds, as the index declares it."""

    rel: Path
    cls: str
    era: str
    authentication: str
    role: str
    version: str
    states: str
    basis: Optional[_Basis] = None


@dataclass(frozen=True)
class _Absent:
    """A 2025 document this repository does not hold, and where it will be filed."""

    rel: Path
    cls: str
    states: str


#: The obtained documents and records, in the order the index lists them.
OBTAINED: tuple[_Obtained, ...] = (
    _Obtained(
        rel=AF_V5_REL,
        cls="instrument_application_form",
        era="historical",
        authentication="computed_only",
        role="immutable_evidence",
        version="5.0",
        states=(
            "the MSCA Doctoral Networks application form of the 2025 call, Part B template "
            "included"
        ),
    ),
    _Obtained(
        rel=AF_V6_REL,
        cls="instrument_application_form",
        era="current",
        authentication="computed_only",
        role="immutable_evidence",
        version="6.0",
        states="the Part B template of the 2026 call",
    ),
    _Obtained(
        rel=EF_REL,
        cls="instrument_evaluation_form",
        era="current",
        authentication="computed_only",
        role="immutable_evidence",
        version="2.2",
        states="the evaluation form the 2026 scorecard is derived from",
    ),
    _Obtained(
        rel=GENERAL_ANNEXES_REL,
        cls="programme_guidance",
        era="current",
        authentication="computed_only",
        role="immutable_evidence",
        version="",
        states="the General Annexes of the 2026-2027 work programme",
    ),
    _Obtained(
        rel=WORK_PROGRAMME_REL,
        cls="work_programme",
        era="current",
        authentication="computed_only",
        role="immutable_evidence",
        version="",
        states="the MSCA part of the 2026-2027 work programme",
    ),
    _Obtained(
        rel=ESR_REL,
        cls="evaluation_output",
        era="historical",
        authentication="operator_supplied",
        role="immutable_evidence",
        version="",
        states="the 2025 evaluation's own recorded result, criterion by criterion",
        basis=_Basis(
            pointer="authored_by",
            must_contain="operator transcription",
            wording=(
                "an operator transcription of the 2025 report, dated 2026-10-07, stated in the "
                "record's own `authored_by` field; no hash from an issuing body"
            ),
        ),
    ),
    _Obtained(
        rel=FIDELITY_REL,
        cls="submission_record",
        era="historical",
        authentication="operator_supplied",
        role="immutable_evidence",
        version="",
        states=(
            "the fidelity register over the sanitised copy, with the submission's declared facts"
        ),
        basis=_Basis(
            pointer="provenance/declared_by",
            must_contain="operator",
            wording=(
                "the operator, named in the register's own `provenance/declared_by` field; no "
                "hash from an issuing body"
            ),
        ),
    ),
    _Obtained(
        rel=PE01_REL,
        cls="repository_decision",
        era="cross_era",
        authentication="computed_only",
        role="immutable_evidence",
        version="",
        states="the PE-01 decision, which declares the 2025 call identifier Assumed",
    ),
    _Obtained(
        rel=SCORECARD_REL,
        cls="derived_configuration",
        era="current",
        authentication="computed_only",
        role="tracked_input",
        version="2.2",
        states="the scoring contract derived from the 2026 evaluation form",
    ),
    _Obtained(
        rel=PROFILE_REL,
        cls="derived_configuration",
        era="current",
        authentication="computed_only",
        role="tracked_input",
        version="",
        states="the 2026 pre-evaluation profile the matrix compares against",
    ),
    _Obtained(
        rel=APPENDIX_REL,
        cls="derived_configuration",
        era="current",
        authentication="computed_only",
        role="tracked_input",
        version="",
        states="the criterion-to-table routing derived from the 2026 form",
    ),
    _Obtained(
        rel=SPEC_REL,
        cls="repository_decision",
        era="cross_era",
        authentication="computed_only",
        role="tracked_input",
        version="",
        states="the pre-evaluation specification, which fixes the harness's own scoring method",
    ),
)

#: The 2025 documents this repository does not hold. The path is where each will
#: be filed when the operator supplies it, not a claim about a file.
NOT_OBTAINED: tuple[_Absent, ...] = (
    _Absent(
        rel=HIST_WP_REL,
        cls="work_programme",
        states="the MSCA part of the work programme in force for the 2025 call",
    ),
    _Absent(
        rel=HIST_ANNEXES_REL,
        cls="programme_guidance",
        states="the General Annexes in force for the 2025 call",
    ),
    _Absent(
        rel=HIST_CALL_REL,
        cls="call_document",
        states="the conditions and topic text of the 2025 Doctoral Networks call",
    ),
    _Absent(
        rel=HIST_EF_REL,
        cls="instrument_evaluation_form",
        states="the version of the evaluation form in force for the 2025 call",
    ),
)

#: What the form-equivalence record inside the scorecard settles, and no more.
#: It measured section structure. A row about weights, thresholds or evaluator
#: instructions that cited it would be reading more out of it than it measured,
#: which is the defect ticket V09's fifth criterion names.
V5_EQUIVALENCE_RESTRICTION: dict[str, Any] = {
    "field_prefix": "provenance/v5_equivalence",
    "settles_areas": ["section_mapping"],
    "measured": (
        "the ten numbered aspect headings, Tables 3.1 a to 3.1 e, the 34-page Part B1 cap with "
        "sections 1 to 3 at 30, and Part B2 sections 4 to 10 — structure, and nothing about a "
        "scoring rule, a weight, a threshold or an evaluator instruction"
    ),
}


def _refuse_present_destinations(repo_root: Path) -> None:
    """Refuse if a file sits at one of the unobtained documents' destinations.

    A destination holding a file means the document has arrived, and the index
    would then record an absence over a document that is there. Obtaining one
    is an index change, not something to write around.
    """
    for absent in NOT_OBTAINED:
        if (repo_root / absent.rel).exists():
            raise AuthorityAuthoringError(
                f"{absent.rel.as_posix()}: declared not obtained, yet a file is there; the index "
                "would record an absence over a present document"
            )


def _resolved_basis(repo_root: Path, source: _Obtained) -> str:
    """The recorded basis for *source*'s authentication, read out of the record.

    Refuses in both directions. An authentication claiming somebody vouched for
    the bytes with no basis declared is this module asserting a rank, and a
    basis whose pointer no longer resolves — or no longer says what it said —
    is the index describing a record that has moved underneath it.
    """
    claims_a_voucher = source.authentication in ("issuer_hash_confirmed", "operator_supplied")
    if not claims_a_voucher:
        if source.basis is not None:
            raise AuthorityAuthoringError(
                f"{source.rel.as_posix()}: authentication {source.authentication} claims no "
                "voucher, so a basis would say more than the rank does"
            )
        return ""
    if source.basis is None:
        raise AuthorityAuthoringError(
            f"{source.rel.as_posix()}: authentication {source.authentication} claims a voucher "
            "and declares no basis; the rank would rest on this module's own word"
        )
    node: Any = _read_json(repo_root / source.rel)
    for segment in source.basis.pointer.split("/"):
        if not isinstance(node, Mapping) or segment not in node:
            raise AuthorityAuthoringError(
                f"{source.rel.as_posix()}: {source.basis.pointer} does not resolve; the "
                f"authentication {source.authentication} has lost its recorded basis"
            )
        node = node[segment]
    if source.basis.must_contain.lower() not in str(node).lower():
        raise AuthorityAuthoringError(
            f"{source.rel.as_posix()}: {source.basis.pointer} no longer says "
            f"{source.basis.must_contain!r}; the authentication {source.authentication} has "
            "lost its recorded basis"
        )
    return source.basis.wording


def render_index(repo_root: Path, rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """The source index. ``would_settle`` is derived from *rows*, never typed."""
    settled_by: dict[str, list[str]] = {}
    for row in rows:
        for path in row.get("would_be_settled_by", ()):
            settled_by.setdefault(path, []).append(row["id"])

    sources: list[dict[str, Any]] = []
    for source in OBTAINED:
        path = repo_root / source.rel
        if not path.is_file():
            raise AuthorityAuthoringError(f"{source.rel.as_posix()}: not in the tree")
        entry: dict[str, Any] = {
            "path": source.rel.as_posix(),
            "class": source.cls,
            "era": source.era,
            "authentication": source.authentication,
            "role": source.role,
            "sha256": file_sha256(path),
            "states": source.states,
        }
        basis = _resolved_basis(repo_root, source)
        if basis:
            entry["authentication_basis"] = basis
        if source.version:
            entry["version"] = source.version
        if source.rel.suffix == ".pdf":
            entry["pages"] = _page_count(path)
        if source.rel == SCORECARD_REL:
            entry["scope_restrictions"] = [V5_EQUIVALENCE_RESTRICTION]
        sources.append(entry)

    _refuse_present_destinations(repo_root)
    for absent in NOT_OBTAINED:
        key = absent.rel.as_posix()
        sources.append(
            {
                "path": key,
                "class": absent.cls,
                "era": "historical",
                "authentication": "not_obtained",
                "role": "immutable_evidence",
                "states": absent.states,
                "required": True,
                "would_settle": sorted(settled_by.get(key, ())),
                "path_note": (
                    "A destination, not a document. This is where the file is filed when the "
                    "operator supplies it."
                ),
            }
        )

    return {
        "schema": SCHEMA_INDEX,
        "record_type": "authority_source_index",
        "index_name": "msca_dn_authority_sources_2026-10-12",
        "subject": (
            "the authority documents of the 2025 MSCA Doctoral Networks call and of the 2026 "
            "call the current profile was written for"
        ),
        "authored_on": AUTHORED_ON,
        "ticket": TICKET,
        "advisory": True,
        "blocking": False,
        "historical_label": HISTORICAL_LABEL,
        "current_label": CURRENT_LABEL,
        "purpose": (
            "Every document a matrix row may cite, pinned by sha256, with the era whose rules it "
            "states, the class of authority it is and how its bytes are vouched for. The four "
            "2025 documents this repository does not hold are entries too, so a row cannot rest "
            "on one by assuming what it would say."
        ),
        "review_state": "agent_drafted_pending_operator_review",
        "declared_status": "Inferred",
        "declared_status_note": (
            "Inferred, not Confirmed. Each hash is computed from the bytes in this tree, which "
            "is evidence of what is here. That those bytes are the document the issuing body "
            "published is not established for any entry: nothing in this repository records "
            "where a stored PDF was downloaded from. Only an operator-supplied hash from the "
            "issuing body would move this."
        ),
        "supersedes": (
            "nothing. This is the first authority source index on this branch. The 2026-only "
            "pinning the specification's decision 3 recorded stands as the state it replaces, "
            "and a correction to this index is a successor index, never an edit."
        ),
        "uncertainties": [
            "No entry is authenticated by a hash from its issuing body, so no matrix row may "
            "declare Confirmed and none does.",
            "The four unobtained documents cannot be fetched until the 2025 call identifier is "
            "settled, which row CI-01 records as unresolved.",
            "The stored evaluation form declares a version date later than the 2025 call's own "
            "year, and whether it was in force for that call is row EI-02's open question.",
            "Four entries are tracked inputs: the scorecard, the 2026 profile, the appendix "
            "mapping and the specification. Any edit to one makes the matrix stale until it is "
            "re-derived.",
        ],
        "authority_note": (
            "This index confers no authority. It records what is held and what is missing. "
            "Pinning a document is not authenticating it, and recording a destination for an "
            "absent document asserts nothing about a file there."
        ),
        "written_by": "tools/author_msca_dn_authority_matrix.py",
        "sources": sources,
    }


def render_matrix(
    rows: Sequence[Mapping[str, Any]], index_sha256: str
) -> dict[str, Any]:
    """The matrix, bound to the index by the hash of the bytes written."""
    return {
        "schema": SCHEMA_MATRIX,
        "record_type": "authority_equivalence_matrix",
        "matrix_name": "msca_dn_2025_to_2026_equivalence_2026-10-12",
        "subject": (
            "every scoring-relevant rule of the 2025 MSCA Doctoral Networks evaluation, read "
            "against the 2026 profile"
        ),
        "authored_on": AUTHORED_ON,
        "ticket": TICKET,
        "advisory": True,
        "blocking": False,
        "purpose": (
            "The runbook proposes preparing a historical profile as a copy of the 2026 one, "
            "leaving a rule unchanged where no source states a difference. That is a defaulting "
            "policy, not evidence that the rule applied in 2025. This matrix replaces it: each "
            "rule is sourced to a 2025 document, or recorded as defaulted with the rule its "
            "defaulting affects, or recorded as an unresolved limitation. No verdict means that "
            "no difference was found."
        ),
        "review_state": "agent_drafted_pending_operator_review",
        "declared_status": "Inferred",
        "declared_status_note": (
            "Inferred, not Confirmed. Every sourced row rests on a pinned document whose bytes "
            "nothing from an issuing body vouches for, and harness.authority_matrix.check "
            "refuses a Confirmed row on such a source."
        ),
        "supersedes": (
            "nothing. It is the first equivalence matrix on this branch. It supersedes no "
            "record and edits none: the specification's decision 3, which pinned one 2026 "
            "profile because the 2025 sources were absent, stands as written, and this matrix "
            "is what a historical profile is authored from instead."
        ),
        "uncertainties": [
            "Six rows are defaulted and two unresolved. All eight trace to the four unobtained "
            "2025 documents, and five of them to the 2025 evaluation form alone.",
            "A sourced row claims what its citations measure and no more. SM-01 compares the "
            "aspect anchors in both directions; AM-01 claims an inclusion only, so a 2025 "
            "cross-reference the 2026 mapping has no row for would not have been seen.",
            "Whether an area's rows are all of its scoring-relevant rules is this author's "
            "judgement. The check reads what each row cites and refuses an unsourced relation; "
            "it cannot report a rule nobody wrote a row for.",
            "The rows sourced to the 2025 evaluation's own record settle what was applied to "
            "this submission. None of them settles a rule of the 2025 call, and the check "
            "refuses a call-wide claim resting only on them.",
            "EI-01, the six score-level descriptions, is the largest unsourced input to any "
            "numerical comparison with the 2025 result.",
            "This matrix quotes the 2025 evaluation's recorded figures. It lives beside the ESR "
            "record, outside the dev-graph root, and is not snapshotted; the blind lane's "
            "isolation rests on that exclusion and on the assessor running with no tools from "
            "outside the repository, exactly as it does for the ESR record itself.",
        ],
        "isolation_note": (
            "Written under docs/tier4_orchestration_state/msca_dn/, outside the dev-graph root "
            "at workspaces/msca_dn/. No snapshot reads it, so it cannot reach an evidence pack, "
            "which is the position the ESR record already holds (specification decision 12)."
        ),
        "authority_note": (
            "This matrix confers no authority and closes no gate. It records what the sources "
            "state. A row marked defaulted is a declaration that a rule is unsourced, not a "
            "finding that it is wrong."
        ),
        "required_areas": list(REQUIRED_AREAS),
        "source_index": {"path": INDEX_REL.as_posix(), "sha256": index_sha256},
        "written_by": "tools/author_msca_dn_authority_matrix.py",
        "rows": list(rows),
    }


# --------------------------------------------------------------------------- #
# Checking and writing
# --------------------------------------------------------------------------- #


def render_all(repo_root: Path) -> dict[str, bytes]:
    """The two artifacts this module writes, by relative path."""
    rows = _rows(repo_root)
    index_bytes = canonical_json_bytes(render_index(repo_root, rows))
    index_sha = hashlib.sha256(index_bytes).hexdigest()
    return {
        INDEX_REL.as_posix(): index_bytes,
        MATRIX_REL.as_posix(): canonical_json_bytes(render_matrix(rows, index_sha)),
    }


def check(repo_root: Path) -> list[str]:
    """Relative paths whose bytes differ from the rendering, or are absent."""
    return [
        rel
        for rel, data in render_all(repo_root).items()
        if not (repo_root / rel).is_file() or (repo_root / rel).read_bytes() != data
    ]


def write(repo_root: Path) -> list[str]:
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
        "--check", action="store_true", help="exit 1 if either artifact would change"
    )
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
        changed = write(repo_root)
        for rel in changed:
            print(f"wrote: {rel}")
        print("no change" if not changed else f"{len(changed)} file(s) written")
        print(
            "now check them and render their readings:\n"
            f"  py -3.10 -m harness.commands.authority_matrix --matrix {MATRIX_REL.as_posix()}"
        )
        return 0
    except AuthorityAuthoringError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
