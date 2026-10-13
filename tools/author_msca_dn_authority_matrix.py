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

#: The MSCA part of the work programme the 2025 call was opened under. Its
#: published filename says 2023-2024; its own cover says the 2023-2025 edition
#: and carries Commission Decision C(2025) 2779 of 14 May 2025, the same
#: decision as the General Annexes below. It carries the call's own conditions
#: and topic text, so no separate call document is held or needed.
HIST_WP_REL = Path(
    "docs/tier2b_topic_and_call_sources/work_programmes/msca/"
    "wp-2-msca-actions_horizon-2023-2025_en.pdf"
)
#: The General Annexes of the same work programme, under the same decision.
HIST_ANNEXES_REL = Path(
    "docs/tier1_normative_framework/programme_guidance/wp-14-general-annexes_horizon-2025_en.pdf"
)
#: The evaluation form served at the issuing body's template address through the
#: 2025 call window. The address now serves a later version, so this copy comes
#: from an independent archive of it, and its place in the call is bracketed and
#: not closed.
HIST_EF_REL = Path(
    "docs/tier2a_instrument_schemas/evaluation_forms/msca/ef_he-msca_v2.0_2025-02-28.pdf"
)

#: What would bind this submission to a call identifier, and is not held. A
#: destination, not a document: nothing is asserted about a file there.
SUBMISSION_ACK_REL = Path(
    "docs/tier3_project_instantiation/source_materials/msca_dn/submission_acknowledgement.pdf"
)

AUTHORITY_DIR = DN_DIR / "authority"
INDEX_REL = AUTHORITY_DIR / "authority_source_index_2026-10-13.json"
MATRIX_REL = AUTHORITY_DIR / "equivalence_matrix_2025_2026-10-13.json"

#: The pair this one supersedes. They are historical evidence and are not
#: edited: the 2026-10-12 index declared four 2025 documents absent, and a
#: correction to an index is a successor index. Their hashes are read from the
#: tree, so a superseded record that moved is reported rather than restated.
PRIOR_INDEX_REL = AUTHORITY_DIR / "authority_source_index_2026-10-12.json"
PRIOR_MATRIX_REL = AUTHORITY_DIR / "equivalence_matrix_2025_2026-10-12.json"

#: The schemas the two declarations carry. ``harness.authority_matrix`` holds the
#: reader's copies, and ``tests/test_msca_dn_authority_matrix.py`` asserts they
#: agree. Deliberate double entry: this module may not import the harness.
SCHEMA_INDEX = "authority_source_index/2"
SCHEMA_MATRIX = "authority_equivalence_matrix/1"

AUTHORED_ON = "2026-10-13"
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
# What the 2025 authorities say, quoted
#
# Each quote is checked against the page it is cited from when the matrix is
# rendered, so a quote that stops occurring refuses rather than being written.
# They are named here because several rows cite the same sentence, and a
# sentence transcribed twice is a sentence that can differ from itself.
# --------------------------------------------------------------------------- #

#: The work programme part, on the call itself.
Q25_CALL_HEADING = (
    "Call - MSCA Doctoral Networks 2025 HORIZON-MSCA-2025-DN-01 Conditions for the Call"
)
Q25_CALL_DATES = "Opening: 28 May 2025 Deadline(s): 25 Nov 2025"
Q25_AWARD_DEFER = (
    "For application of the general award criteria, including weighting and thresholds, see the "
    "specific conditions at the end of this Work Programme part."
)

#: The work programme part's specific conditions, on scoring.
Q25_CRITERIA_NAMES = (
    "the award criteria 'excellence', 'impact' and 'quality and efficiency of the implementation'"
)
Q25_NO_ASPECT_SCORES = (
    "Evaluation scores will be awarded for each of these criteria, and not for the different "
    "aspects listed in the table below."
)
Q25_MAXIMUM = "Each criterion will be scored out of 5."
Q25_RESOLUTION = "Scores will be awarded with a resolution of one decimal place"
Q25_FUNDING_THRESHOLD = "Proposals scoring equal to or above 70% will be considered for funding"
Q25_WEIGHTING = "50% 30% 20% Weighting"

#: The General Annexes of the same programme, on who sets the award criteria.
Q25_TMA_DEFER = "Training and mobility actions (TMA)"
Q25_ANNEX_INDIVIDUAL = "The threshold for individual criteria will be 3."

#: The evaluation form served through the call window, on scoring.
Q25_EF_SCALE = "Scoring must be in the range from 0-5. Half-marks may be given."
Q25_EF_INDIVIDUAL = "The threshold for the individual criteria is 3."
Q25_EF_OVERALL = (
    "The overall threshold, applying to the sum of the 3 individual scores, is 10 points."
)
Q25_EF_WEIGHTING_RANKING = (
    "Weighting is only for the ranking (not to determine if the proposal passed the thresholds)."
)
Q25_EF_CALL_MAY_DIFFER = "Specific calls or topics may have different rules"
Q25_EF_TOTAL_15 = "Total score Overall threshold /15"
#: The applicability tags, where the two eras scope one of them differently.
Q25_EF_DN_TAG = (
    "[OPTION for MSCA Doctoral networks Quality and credibility of the training programme"
)
Q25_EF_WIDE_TAG = (
    "[OPTION for MSCA Doctoral networks, Postdoctoral fellowships and Staff exchanges:"
)
Q26_EF_WIDE_TAG = "[OPTION for MSCA Doctoral networks, Postdoctoral fellowships:"


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


#: The three criterion section headings of an evaluation form, in order. Each
#: must occur exactly once, or the walk below has no boundaries to measure
#: against.
CRITERION_SECTION_HEADINGS: tuple[str, ...] = (
    "1. Excellence",
    "2. Impact",
    "3. Quality and efficiency of the implementation",
)


def _refuse_unless_aspects_group_the_same_way(
    scorecard: Mapping[str, Any], document: _Document
) -> tuple[dict[str, Any], ...]:
    """Refuse unless *document* groups the ten aspects as the scorecard does.

    The claim is about which criterion each aspect is graded under, so reading
    it off a list of aspect texts would not establish it: the texts could all
    be present and grouped differently. This walks the document once, finds the
    three criterion section boundaries, and requires every aspect text to fall
    inside its own criterion's section. A heading that occurs twice gives no
    boundary, and an aspect outside its section is the difference the row would
    otherwise have called equivalence.
    """
    pages = {n: document.text(n) for n in range(1, document.pages + 1)}
    whole = "\n".join(pages[n] for n in sorted(pages))
    offsets: list[int] = []
    for heading in CRITERION_SECTION_HEADINGS:
        if whole.count(heading) != 1:
            raise AuthorityAuthoringError(
                f"{document.rel}: the criterion heading {heading!r} occurs "
                f"{whole.count(heading)} times; the aspect grouping cannot be measured"
            )
        offsets.append(whole.index(heading))
    if offsets != sorted(offsets):
        raise AuthorityAuthoringError(
            f"{document.rel}: the three criterion headings are out of order"
        )
    bounds = offsets + [len(whole)]

    citations: list[dict[str, Any]] = []
    for position, criterion in enumerate(scorecard["criteria"]):
        for aspect in criterion["aspects"]:
            text = normalise_whitespace(aspect["text"])
            offset = whole.find(text)
            if offset < 0:
                raise AuthorityAuthoringError(
                    f"{document.rel}: aspect {aspect['anchor']} is not in the document; the "
                    "grouping claim would rest on an absent aspect"
                )
            if not bounds[position] < offset < bounds[position + 1]:
                raise AuthorityAuthoringError(
                    f"{document.rel}: aspect {aspect['anchor']} does not sit under "
                    f"{CRITERION_SECTION_HEADINGS[position]!r}; the grouping differs"
                )
            page = next(n for n in sorted(pages) if text in pages[n])
            citations.append(
                _verified(
                    document,
                    page,
                    text,
                    f"aspect {aspect['anchor']} under {CRITERION_SECTION_HEADINGS[position]}",
                )
            )
    return tuple(citations)


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


def _refuse_unless_a_score_rules_out_half_marks(esr: Mapping[str, Any]) -> str:
    """Refuse unless a recorded score is finer than a half-mark.

    Two 2025 authorities state different resolutions: the work programme one
    decimal place, the evaluation form half-marks. The recorded scores decide
    which was applied, but only if at least one of them is not also a
    half-mark. If every recorded score happened to be a half-mark, both rules
    would fit and the row would be reading the absence of a visible difference
    as agreement, which is the defect the matrix exists to prevent.
    """
    finer = [
        f"{c['criterion_id']} {c['score']}"
        for c in esr["evaluation_result"]["criteria"]
        if abs(round(float(c["score"]) * 2) - float(c["score"]) * 2) > 1e-9
    ]
    if not finer:
        raise AuthorityAuthoringError(
            f"{ESR_REL.as_posix()}: every recorded score is a whole or half mark, so the "
            "recorded result cannot say which of the two 2025 resolutions was applied"
        )
    return ", ".join(finer)


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
    #: The MSCA part of the work programme the 2025 call was opened under.
    hist_wp: _Document
    #: The General Annexes of that same work programme.
    hist_annexes: _Document
    #: The evaluation form served through the 2025 call window.
    hist_ef: _Document
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
        hist_wp=_Document(repo_root, HIST_WP_REL),
        hist_annexes=_Document(repo_root, HIST_ANNEXES_REL),
        hist_ef=_Document(repo_root, HIST_EF_REL),
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
                "side is addressed to this call."
            ),
            "affects": "an interpretation",
            "verdict": "unresolved",
            "settles": "as_applied_to_this_submission",
            "declared_status": "Assumed",
            "status_basis": (
                "Two records declare the identifier Assumed and give the same reason. The value "
                "is the operator's declaration, and this module refuses to render if either "
                "record stops declaring it Assumed. The work programme now evidences that a "
                "call with that identifier existed, with the dates it cites. It does not "
                "evidence that this submission was made to it, which is what the row is about, "
                "so the status stays Assumed."
            ),
            "limitation": (
                "The call itself is now pinned. The work programme part states its identifier, "
                "its opening date and its deadline, so the call this submission is declared "
                "against exists and its conditions are held. What is still missing is the "
                "binding: the Evaluation Summary Report names no proposal number, and nothing "
                "in this repository shows this submission was entered into that call. Two "
                "records declare the binding, and a declaration is not evidence of it."
            ),
            "consequence": (
                "The historical profile carries the operator's declared call identifier with "
                "declared_status Assumed, never Confirmed, and the matrix is cited as the reason."
            ),
            "would_be_settled_by": [SUBMISSION_ACK_REL.as_posix()],
            "citations": [
                _verified(
                    src.hist_wp,
                    23,
                    Q25_CALL_HEADING,
                    "the work programme states the identifier of the 2025 call",
                ),
                _verified(
                    src.hist_wp,
                    23,
                    Q25_CALL_DATES,
                    "and that call's opening date and deadline",
                ),
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
                "The 2025 side is stated twice: by the evaluation's own recorded wording, which "
                "is evidence of what was applied to this submission, and by the work programme "
                "the call was opened under, which names the three criteria as the call's. It is "
                "Inferred rather than Confirmed because no hash from the issuing body vouches "
                "for either document's bytes."
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
                _verified(
                    src.hist_wp,
                    123,
                    Q25_CRITERIA_NAMES,
                    "the work programme names the three award criteria of the 2025 call",
                ),
                _field_citation(
                    profile_rel, "criteria", "the 2026 profile's three criteria, in order"
                ),
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
            "verdict": "equivalent",
            "settles": "call_wide",
            "historical_value": (
                "the evaluation form served through the 2025 call window carries all ten aspect "
                "texts, each inside the section of the criterion the scorecard grades it under"
            ),
            "current_value": "; ".join(
                f"{c['id']}: {', '.join(a['id'] for a in c['aspects'])}"
                for c in scorecard["criteria"]
            ),
            "declared_status": "Inferred",
            "status_basis": (
                "Measured, not read off a list. The 2025 form is walked once, its three "
                "criterion section headings locate three boundaries, and every one of the ten "
                "aspect texts is required to fall inside its own criterion's section. An aspect "
                "present but grouped elsewhere refuses here. Inferred, not Confirmed, because "
                "that form's place in the call is bracketed and not closed, which row EI-02 "
                "keeps open."
            ),
            "consequence": (
                "The historical profile keeps the criterion-to-aspect assignment, sourced to "
                "the 2025 form's own grouping rather than carried over from 2026."
            ),
            "citations": list(_refuse_unless_aspects_group_the_same_way(scorecard, src.hist_ef))
            + [
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
                "Each weight is recorded three times: in the 2025 evaluation's own "
                "per-criterion wording, in the work programme's weighting row for that call, "
                "and in the 2026 scorecard derived from the evaluation form. The call document "
                "and the result agree, so the weights are the call's rule and not only what "
                "this submission was given. Inferred for the reason CR-01 gives."
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
                _verified(
                    src.hist_wp,
                    124,
                    Q25_WEIGHTING,
                    "the work programme's weighting row for the 2025 call",
                ),
                _field_citation(
                    scorecard_rel,
                    "criteria",
                    "the 2026 scorecard's weights, derived from the evaluation form",
                ),
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
            "verdict": "equivalent",
            "settles": "call_wide",
            "historical_value": Q25_EF_WEIGHTING_RANKING,
            "current_value": scoring["weighting_source_quote"],
            "declared_status": "Inferred",
            "status_basis": (
                "The two forms carry the sentence word for word. Inferred, not Confirmed, "
                "because the 2025 form's place in the call is bracketed, which row EI-02 keeps "
                "open."
            ),
            "consequence": (
                "The historical profile carries the sentence, sourced to the 2025 form. A pass "
                "or fail statement about the 2025 result rests on it and may cite this row."
            ),
            "citations": [
                _verified(
                    src.hist_ef,
                    2,
                    Q25_EF_WEIGHTING_RANKING,
                    "the 2025 evaluation form on what weighting is for",
                ),
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
    finer_than_half_marks = _refuse_unless_a_score_rules_out_half_marks(src.esr)
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
                "scores, and the evaluation form of that call window states the same figure as "
                "a rule. Result and rule agree. Inferred for the reason CR-01 gives."
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
                    src.hist_ef,
                    2,
                    Q25_EF_INDIVIDUAL,
                    "the 2025 evaluation form on the per-criterion threshold",
                ),
                _verified(
                    annexes,
                    scoring["individual_threshold_source"]["page"],
                    scoring["individual_threshold_source"]["quote"],
                    "the 2026 General Annexes on the per-criterion threshold",
                ),
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
                "maximum it is out of, and the work programme the call was opened under sets "
                "the same threshold as a percentage of the weighted total. Seventy per cent of "
                "a hundred is seventy points, so the two are the same rule stated in two "
                "units. Inferred for the reason CR-01 gives."
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
                    src.hist_wp,
                    123,
                    Q25_FUNDING_THRESHOLD,
                    "the work programme sets the 2025 call's funding threshold",
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
            "verdict": "equivalent",
            "settles": "call_wide",
            "historical_value": (
                "the call's own work programme part governs. Its General Annexes refer training "
                "and mobility actions to that part, the part itself takes the weighting and the "
                "thresholds into its specific conditions, and the evaluation form of the call "
                "window says a call may set different rules"
            ),
            "current_value": scoring["annex_d_override"]["resolution"],
            "declared_status": "Inferred",
            "status_basis": (
                "Three 2025 documents point the same way, and none of them is this "
                "repository's. The General Annexes hand training and mobility actions to the "
                "work programme part; that part states the weighting and thresholds are in its "
                "own specific conditions; and the evaluation form of the call window says a "
                "specific call may differ. So the call document outranked the generic one in "
                "2025, which is the resolution the 2026 documents were given. Inferred, not "
                "Confirmed, because no issuing body's hash vouches for any of the three."
            ),
            "consequence": (
                "The historical profile reads the 2025 scores against the call's own threshold, "
                "citing this row. The resolution is no longer carried forward from 2026."
            ),
            "citations": [
                _verified(
                    src.hist_annexes,
                    24,
                    Q25_TMA_DEFER,
                    "the 2025 General Annexes refer this action type to the work programme part",
                ),
                _verified(
                    src.hist_wp,
                    24,
                    Q25_AWARD_DEFER,
                    "that part takes the weighting and the thresholds into its own conditions",
                ),
                _verified(
                    src.hist_ef,
                    2,
                    Q25_EF_CALL_MAY_DIFFER,
                    "the 2025 evaluation form allows a call to set different rules",
                ),
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
                "records, and the work programme of that call states it as a rule. Inferred "
                "for the reason CR-01 gives. The claim is the maximum and nothing else: row "
                "TH-05 carries the resolution, which the two 2025 authorities state "
                "differently."
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
                    src.hist_wp,
                    123,
                    Q25_MAXIMUM,
                    "the work programme states the maximum for the 2025 call",
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
            "verdict": "equivalent",
            "settles": "call_wide",
            "historical_value": (
                "one decimal place. The two 2025 authorities state different resolutions, and "
                f"the recorded scores decide between them: {finer_than_half_marks} is not a "
                "half mark"
            ),
            "current_value": "one decimal place",
            "declared_status": "Inferred",
            "status_basis": (
                "The two 2025 authorities disagree. The work programme of the call states one "
                "decimal place; the evaluation form of the call window states that half marks "
                "may be given. The recorded result settles which was applied, because a score "
                "of 4.2 is not a half mark and could not have been awarded under the form's "
                "rule. This module refuses to render if no recorded score is finer than a half "
                "mark, because then both rules would fit and the equivalence would be the "
                "absence of a visible difference again. Inferred, not Confirmed: the rule "
                "applied to this submission is evidenced, and the conflict between the two 2025 "
                "documents is recorded rather than resolved in general."
            ),
            "consequence": (
                "The historical profile keeps one decimal place and cites this row, not a "
                "defaulting. A statement about any other 2025 proposal must carry the conflict "
                "between the two authorities, which the matrix records as an uncertainty."
            ),
            "citations": [
                _verified(
                    src.hist_wp,
                    123,
                    Q25_RESOLUTION,
                    "the work programme states one decimal place for the 2025 call",
                ),
                _verified(
                    src.hist_ef,
                    2,
                    Q25_EF_SCALE,
                    "the evaluation form of the call window states half marks instead",
                ),
                _field_citation(
                    esr_rel,
                    "evaluation_result/criteria/#0/score",
                    "a recorded score that no half-mark rule could have awarded",
                    quote=str(result["criteria"][0]["score"]),
                ),
                _verified(
                    ef,
                    2,
                    scoring["scale_source_quote"],
                    "the 2026 evaluation form on the range and its resolution",
                ),
                _field_citation(
                    scorecard_rel,
                    "scoring/scale",
                    "the resolution as the scorecard carries it",
                ),
            ],
            "measurements": [
                _measurement(
                    f"TH-05-M{position + 1}",
                    f"the 2025 evaluation recorded {criterion['score']} for "
                    f"{criterion['criterion_id']}",
                    ESR_REL,
                    f"evaluation_result/criteria/#{position}/score",
                    expected=criterion["score"],
                )
                for position, criterion in enumerate(result["criteria"])
            ],
        }
    )
    rows.append(
        {
            "id": "TH-06",
            "area": "thresholds",
            "rule": (
                "The total the three criterion scores are summed into, as the evaluation form "
                "itself prints it."
            ),
            "affects": "a number",
            "verdict": "differs",
            "settles": "call_wide",
            "historical_value": (
                "the 2025 evaluation form prints an unweighted total out of 15 and states an "
                "overall threshold of 10 points on the sum of the three scores"
            ),
            "current_value": (
                f"{scoring['overall_threshold']} points on a weighted total out of "
                f"{scoring['overall_max']}"
            ),
            "difference": (
                "The 2025 evaluation form's own total is the three criterion scores added up, "
                "out of 15, read against 10 points. The 2026 form instead states the threshold "
                "on the weighted total out of 100. The difference is in the form, and it is not "
                "the difference that governed: the work programme of the 2025 call sets the "
                "threshold at 70% of the weighted total, and the recorded result is a weighted "
                "total out of 100. So the 2025 form's generic total was superseded by the "
                "call's own rule, which is what TH-03 resolves and TH-02 measures."
            ),
            "declared_status": "Inferred",
            "status_basis": (
                "Both forms are read directly, and the recorded result shows which total was "
                "actually formed. Inferred, not Confirmed, for the reason CR-01 gives, and "
                "because the 2025 form's place in the call is bracketed."
            ),
            "consequence": (
                "The historical profile forms the weighted total out of 100 and cites the call "
                "document for it. It must not cite the 2025 evaluation form's /15 total, and a "
                "reader comparing the two eras is told why the form's own total does not apply."
            ),
            "citations": [
                _verified(
                    src.hist_ef,
                    2,
                    Q25_EF_OVERALL,
                    "the 2025 evaluation form's generic overall threshold",
                ),
                _verified(
                    src.hist_ef,
                    6,
                    Q25_EF_TOTAL_15,
                    "and the total it prints that threshold against",
                ),
                _verified(
                    src.hist_wp,
                    123,
                    Q25_FUNDING_THRESHOLD,
                    "the work programme's threshold for the 2025 call instead",
                ),
                _field_citation(
                    esr_rel,
                    "evaluation_result/result_wording",
                    "the total the 2025 evaluation actually recorded",
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
                    "TH-06-M1",
                    "the 2025 evaluation recorded a maximum of "
                    f"{result['overall_max']}, not the form's fifteen",
                    ESR_REL,
                    "evaluation_result/overall_max",
                    expected=result["overall_max"],
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
            "verdict": "equivalent",
            "settles": "call_wide",
            "historical_value": (
                "all six sentences occur word for word in the evaluation form served through "
                "the 2025 call window"
            ),
            "current_value": "; ".join(f"{k}: {v}" for k, v in scoring["levels"].items()),
            "declared_status": "Inferred",
            "status_basis": (
                "Each of the six sentences is located in the 2025 form and in the 2026 form, "
                "and the citation below refuses if any one of them stops occurring on the page "
                "it cites. This was the largest unsourced input to a numerical comparison, and "
                "it is now sourced on both sides. Inferred, not Confirmed, because the 2025 "
                "form's place in the call is bracketed, which row EI-02 keeps open."
            ),
            "consequence": (
                "The historical profile keeps the level descriptions and cites this row. A "
                "grade awarded under them is no longer resting on a 2026 document alone."
            ),
            "citations": [
                _verified(
                    src.hist_ef,
                    2,
                    scoring["levels"][level],
                    f"the 2025 evaluation form's level {level} description",
                )
                for level in sorted(scoring["levels"])
            ]
            + [
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
                "A version served at the issuing body's template address through the call "
                "window is now held, and its place in the call is bracketed rather than "
                "settled. Nothing states which version the 2025 evaluation used."
            ),
            "limitation": (
                "Three captures of the issuing body's template address carry one archive "
                "digest, dated inside the call window, the last of them twenty days before the "
                "deadline, and the next distinct digest is months after it. That brackets the "
                "window and does not close it: a version served between two captures and never "
                "captured would leave no trace, and nothing states which version the "
                "evaluators were given. The captures are also of one archive, so they are one "
                "witness observed three times rather than three independent witnesses. Every "
                "row citing the 2025 form is Inferred because of this, and none is Confirmed."
            ),
            "consequence": (
                "The historical profile records that the evaluation-form version the 2025 "
                "evaluators used is not established. It does not claim the held version "
                "applied, and every rule it takes from that form is declared Inferred."
            ),
            "would_be_settled_by": [],
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
                "The 2025 side is stated and also measured. The work programme of the call "
                "carries the rule in words, and the recorded result bears it out: three "
                "criterion scores are recorded and no observation carries a score field. "
                "Inferred rather than Confirmed because no issuing body's hash vouches for "
                "either document."
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
                    src.hist_wp,
                    123,
                    Q25_NO_ASPECT_SCORES,
                    "the work programme of the 2025 call states the same rule",
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
            "verdict": "equivalent",
            "settles": "call_wide",
            "historical_value": (
                "the evaluation form of the 2025 call window carries the same tag grammar, and "
                "names this action type in the tags that select the ten aspects"
            ),
            "current_value": scorecard["provenance"]["dn_scope_rule"],
            "declared_status": "Inferred",
            "status_basis": (
                "The grammar is the evaluation form's alone: this module refuses to render if "
                "either application form carries an applicability tag, and neither does. The "
                "2025 form carries it, and row CR-02 measures that the aspects it selects for "
                "this action type are the scorecard's ten, each under the same criterion. One "
                "tag's scope did move between the eras, and it does not move the selection: "
                "the 2025 tag names a third action type that the 2026 tag does not, and this "
                "action type is named in both. Inferred for the reason EI-02 gives."
            ),
            "consequence": (
                "The historical profile keeps the tag grammar and the scope rule, cited to the "
                "2025 form. CR-02 carries the measured selection, so no row rests on the "
                "assumption that the two forms tagged alike."
            ),
            "citations": [
                _verified(
                    src.hist_ef,
                    4,
                    Q25_EF_DN_TAG,
                    "a 2025 tag naming this action type for one of the ten aspects",
                ),
                _verified(
                    src.hist_ef,
                    4,
                    Q25_EF_WIDE_TAG,
                    "the one tag whose scope moved, as the 2025 form states it",
                ),
                _verified(
                    ef,
                    4,
                    Q26_EF_WIDE_TAG,
                    "and as the 2026 form states it, with a third action type dropped",
                ),
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
                "Arithmetic evidence, and now a rule to match it. The formula applied to the "
                "2025 evaluation's own recorded criterion scores reproduces its own recorded "
                "total, and this module refuses to render if it stops doing so. The work "
                "programme of the call states the two inputs the formula is built from: a "
                "maximum of five per criterion and the weighting row. Inferred, not Confirmed, "
                "for the reason CR-01 gives."
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
                _verified(
                    src.hist_wp,
                    123,
                    Q25_MAXIMUM,
                    "the work programme on the maximum each criterion is scored out of",
                ),
                _verified(
                    src.hist_wp,
                    124,
                    Q25_WEIGHTING,
                    "and on the weights the total applies to those scores",
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
class _Capture:
    """One capture of a document's published address by an independent archive."""

    url: str
    captured_on: str
    #: The archive's own digest, in the archive's own format. Recorded so a
    #: reader can ask the archive the same question, never compared here.
    digest: str = ""


@dataclass(frozen=True)
class _Copy:
    """The same bytes obtained a second, independent way."""

    url: str
    #: sha256 of that copy. Checked against the stored file when the index is
    #: rendered, because a copy whose bytes differ corroborates nothing.
    sha256: str
    note: str = ""


@dataclass(frozen=True)
class _Provenance:
    """Where a document's bytes came from, recorded act by act.

    Facts only. Every judgement about them — whether they are the issuing
    body's, whether they governed a closed call — is a separate field that
    names this record as its basis.
    """

    official_url: str = ""
    retrieved_from: str = ""
    retrieved_on: str = ""
    title: str = ""
    declared_version: str = ""
    document_date: str = ""
    filename_note: str = ""
    captures: tuple[_Capture, ...] = ()
    copies: tuple[_Copy, ...] = ()


@dataclass(frozen=True)
class _Obtained:
    """A document or record this repository holds, as the index declares it.

    Three independent questions, three fields. ``authentication`` says how the
    bytes are vouched for once they are here. ``authenticity`` says what makes
    them the issuing body's. ``applicability`` says whether this was the
    version in force for the era the document states rules for. A retrieval
    settles the second and cannot settle the third.
    """

    rel: Path
    cls: str
    era: str
    authentication: str
    role: str
    version: str
    states: str
    basis: Optional[_Basis] = None
    authenticity: str = "unrecorded"
    authenticity_basis: str = ""
    applicability: str = "not_applicable"
    applicability_basis: str = ""
    provenance: Optional[_Provenance] = None


@dataclass(frozen=True)
class _Absent:
    """A document this repository does not hold, and where it will be filed."""

    rel: Path
    cls: str
    states: str


#: The issuing body's document root. Every published address below hangs off it.
PORTAL = "https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027"
#: The address the evaluation form's template is published at. One address
#: serves whichever version is current, which is why a version in force for a
#: closed call can only be read from an archive of it.
EF_TEMPLATE_URL = f"{PORTAL}/horizon/temp-form/ef/ef_he-msca_en.pdf"
#: The archive this repository read.
ARCHIVE = "https://web.archive.org/web"
#: The date every retrieval below was made.
RETRIEVED_ON = "2026-10-13"
#: The work programme part's published address, and the issuing body's second
#: site for the same document.
HIST_WP_URL = f"{PORTAL}/horizon/wp-call/2023-2024/wp-2-msca-actions_horizon-2023-2024_en.pdf"
HIST_WP_MIRROR_URL = (
    "https://marie-sklodowska-curie-actions.ec.europa.eu/sites/default/files/2025-05/"
    "wp-2-msca-actions_horizon-2023-2024_en.pdf"
)
HIST_ANNEXES_URL = f"{PORTAL}/horizon/wp-call/2025/wp-14-general-annexes_horizon-2025_en.pdf"

#: The sha256 of each retrieved copy, as recorded when it was retrieved. The
#: index refuses to render if a declared copy's hash is not the stored file's,
#: because a copy whose bytes differ corroborates nothing.
HIST_WP_SHA = "dd1209675abd79075768093ea277ddf0afe2985f489a5514f8f219d5902fbacf"
HIST_ANNEXES_SHA = "2f2454f28b18583af2f9684455c80d35a17bda5ded7000de0c416e3960037d81"
EF_V22_SHA = "f7478ef7f1eac4c327c62489b66f0c8531ee890917671442846027f329bfbd2c"


def _capture_url(timestamp: str, url: str) -> str:
    """An archive capture address that serves the captured bytes unmodified."""
    return f"{ARCHIVE}/{timestamp}id_/{url}"


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
        applicability="unresolved",
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
        authenticity="independently_corroborated",
        authenticity_basis=(
            "an independent archive of the issuing body's template address serves these bytes. "
            "The file was already in this tree, and the archived capture was read afterwards "
            "and agrees with it byte for byte"
        ),
        provenance=_Provenance(
            official_url=EF_TEMPLATE_URL,
            retrieved_on=RETRIEVED_ON,
            title="Horizon Europe Evaluation Form (HE MSCA)",
            declared_version="2.2",
            document_date="2025-12-17",
            captures=(
                _Capture(
                    url=_capture_url("20260312122434", EF_TEMPLATE_URL),
                    captured_on="2026-03-12",
                    digest="FQSNHZPEEYLINX6FCJHO566PIL27Y6UK",
                ),
            ),
            copies=(
                _Copy(
                    url=_capture_url("20260312122434", EF_TEMPLATE_URL),
                    sha256=EF_V22_SHA,
                    note=(
                        "the archived capture of the published address, read into a scratch "
                        "file and hashed; it is this entry's bytes"
                    ),
                ),
            ),
        ),
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
        rel=HIST_WP_REL,
        cls="work_programme",
        era="historical",
        authentication="computed_only",
        role="immutable_evidence",
        version="",
        states=(
            "the MSCA part of the work programme the 2025 call was opened under, carrying that "
            "call's own conditions and topic text, its award criteria, its weighting and its "
            "funding threshold"
        ),
        authenticity="independently_corroborated",
        authenticity_basis=(
            "retrieved from the issuing body's published address and, the same day, from that "
            "body's own second site for this work programme; the two downloads agree byte for "
            "byte, and both agree with the file pinned here"
        ),
        applicability="in_force_confirmed",
        applicability_basis=(
            "the document states the call it governs. Page 23 carries the 2025 Doctoral "
            "Networks call heading with its identifier, its opening date and its deadline, and "
            "the cover carries the Commission Decision the General Annexes pinned here carry too"
        ),
        provenance=_Provenance(
            official_url=HIST_WP_URL,
            retrieved_on=RETRIEVED_ON,
            title="Horizon Europe Work Programme 2023-2025, 2. Marie Sklodowska-Curie Actions",
            document_date="2025-05-14",
            filename_note=(
                "stored under the edition its cover declares. The published filename says "
                "2023-2024, which names neither the edition nor the decision the document "
                "itself carries, and a reader who trusted it would cite the wrong year"
            ),
            copies=(
                _Copy(
                    url=HIST_WP_MIRROR_URL,
                    sha256=HIST_WP_SHA,
                    note=(
                        "the issuing body's second site for this work programme, a different "
                        "host and a different path from the published address"
                    ),
                ),
            ),
        ),
    ),
    _Obtained(
        rel=HIST_ANNEXES_REL,
        cls="programme_guidance",
        era="historical",
        authentication="computed_only",
        role="immutable_evidence",
        version="",
        states=(
            "the General Annexes of the work programme the 2025 call was opened under, whose "
            "award-criteria table refers training and mobility actions to the work programme "
            "part pinned above"
        ),
        authenticity="independently_corroborated",
        authenticity_basis=(
            "the operator placed the file, and the issuing body's published address was read "
            "afterwards and served the same bytes; the placement and the retrieval are "
            "independent of each other and agree"
        ),
        applicability="in_force_confirmed",
        applicability_basis=(
            "the document's cover names the 2025 work programme and the Commission Decision "
            "that adopted it, which is the decision the work programme part pinned here carries "
            "as well, so the two are parts of one adopted programme"
        ),
        provenance=_Provenance(
            official_url=HIST_ANNEXES_URL,
            retrieved_from="placed by the operator, then read from the published address",
            retrieved_on=RETRIEVED_ON,
            title="Horizon Europe Work Programme 2025, 14. General Annexes",
            document_date="2025-05-14",
            copies=(
                _Copy(
                    url=HIST_ANNEXES_URL,
                    sha256=HIST_ANNEXES_SHA,
                    note="the published address, read after the operator placed the file",
                ),
            ),
        ),
    ),
    _Obtained(
        rel=HIST_EF_REL,
        cls="instrument_evaluation_form",
        era="historical",
        authentication="computed_only",
        role="immutable_evidence",
        version="2.0",
        states=(
            "the version of the evaluation form served at the issuing body's template address "
            "through the 2025 call window, carrying that form's own scoring, threshold and "
            "weighting statements"
        ),
        authenticity="retrieved_from_web_archive",
        authenticity_basis=(
            "the template address serves whichever version is current and now serves a later "
            "one, so these bytes come from an independent archive of that address. One archive "
            "is one witness: no second, independent copy of this version was found"
        ),
        applicability="bracketed_not_conclusive",
        applicability_basis=(
            "three captures of the template address carry one archive digest, dated inside the "
            "call window and the last of them twenty days before the deadline, and the next "
            "distinct digest is months after it. That brackets the window without closing it. A "
            "version served between two captures and never captured would leave no trace here"
        ),
        provenance=_Provenance(
            official_url=EF_TEMPLATE_URL,
            retrieved_from=_capture_url("20250619081843", EF_TEMPLATE_URL),
            retrieved_on=RETRIEVED_ON,
            title="Horizon Europe Evaluation Form (HE MSCA)",
            declared_version="2.0",
            document_date="2025-02-28",
            filename_note=(
                "stored under its declared version and date. The published address carries one "
                "filename for every version, and that filename is already taken in this tree by "
                "the later version pinned above"
            ),
            captures=(
                _Capture(
                    url=_capture_url("20250619081843", EF_TEMPLATE_URL),
                    captured_on="2025-06-19",
                    digest="ODDXOSHI52ABE7ZJQ4EWCIHCNHHR5YBU",
                ),
                _Capture(
                    url=_capture_url("20251003102007", EF_TEMPLATE_URL),
                    captured_on="2025-10-03",
                    digest="ODDXOSHI52ABE7ZJQ4EWCIHCNHHR5YBU",
                ),
                _Capture(
                    url=_capture_url("20251105174714", EF_TEMPLATE_URL),
                    captured_on="2025-11-05",
                    digest="ODDXOSHI52ABE7ZJQ4EWCIHCNHHR5YBU",
                ),
            ),
        ),
    ),
    _Obtained(
        rel=ESR_REL,
        authenticity="not_applicable",
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
        authenticity="not_applicable",
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
        rel=SUBMISSION_ACK_REL,
        cls="submission_record",
        states=(
            "the submission's own acknowledgement of receipt, which would bind this submission "
            "to a call identifier rather than leaving the binding declared"
        ),
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


#: What a rank has to carry in its provenance record before it is more than a
#: word. ``harness.authority_matrix`` reports the same requirement over the
#: written index; this refuses before the index is written.
RANK_REQUIREMENTS: tuple[tuple[str, str], ...] = (
    ("independently_corroborated", "a capture or a corroborating copy"),
    ("retrieved_from_official_url", "an official address and a retrieval date"),
    ("retrieved_from_web_archive", "an archive capture and a retrieval date"),
    ("edition_declared", "a declared version or a document date"),
    ("bracketed_not_conclusive", "the archive captures that form the brackets"),
)

#: Ranks that claim evidence of origin, and so must say what it is.
AUTHENTICITIES_NEEDING_A_BASIS: tuple[str, ...] = (
    "issuer_hash_matched",
    "independently_corroborated",
    "retrieved_from_official_url",
    "retrieved_from_web_archive",
    "operator_placed",
)
#: Applicabilities that must say what they rest on.
APPLICABILITIES_NEEDING_A_BASIS: tuple[str, ...] = (
    "in_force_confirmed",
    "edition_declared",
    "bracketed_not_conclusive",
)


def _rank_is_supported(source: _Obtained, rank: str) -> bool:
    """Whether *source*'s provenance carries what *rank* needs."""
    prov = source.provenance
    if rank == "independently_corroborated":
        return prov is not None and bool(prov.captures or prov.copies)
    if rank == "retrieved_from_official_url":
        return prov is not None and bool(prov.official_url and prov.retrieved_on)
    if rank == "retrieved_from_web_archive":
        return prov is not None and bool(prov.captures and prov.retrieved_on)
    if rank == "edition_declared":
        return prov is not None and bool(prov.declared_version or prov.document_date)
    if rank == "bracketed_not_conclusive":
        return prov is not None and bool(prov.captures)
    return True


def _refuse_an_unevidenced_rank(source: _Obtained) -> None:
    """Refuse a rank with no basis, or one its provenance does not carry.

    The two defects are separate. A rank with no basis is this module asserting
    a provenance; a rank whose record does not carry what the rank needs is a
    basis that says more than the record beside it does.
    """
    for rank, basis, needing in (
        (source.authenticity, source.authenticity_basis, AUTHENTICITIES_NEEDING_A_BASIS),
        (source.applicability, source.applicability_basis, APPLICABILITIES_NEEDING_A_BASIS),
    ):
        if rank in needing and not basis.strip():
            raise AuthorityAuthoringError(
                f"{source.rel.as_posix()}: {rank} claims evidence and declares no basis"
            )
    for rank, needs in RANK_REQUIREMENTS:
        if rank in (source.authenticity, source.applicability) and not _rank_is_supported(
            source, rank
        ):
            raise AuthorityAuthoringError(
                f"{source.rel.as_posix()}: {rank} needs {needs} in its provenance record"
            )


def _refuse_a_copy_that_is_not_this_file(source: _Obtained, sha256: str) -> None:
    """Refuse a declared copy whose hash is not the stored file's.

    A second copy is evidence only if it is the same bytes. One whose hash
    differs is either a different document or a mis-recorded hash, and either
    way the corroboration it is cited for does not hold.
    """
    prov = source.provenance
    if prov is None:
        return
    for copy in prov.copies:
        if copy.sha256 != sha256:
            raise AuthorityAuthoringError(
                f"{source.rel.as_posix()}: the copy at {copy.url} is recorded as "
                f"{copy.sha256}, which is not this file's {sha256}; it corroborates nothing"
            )


def _provenance_entry(prov: _Provenance) -> dict[str, Any]:
    """The provenance record, omitting every field that was not recorded."""
    entry: dict[str, Any] = {}
    for key, value in (
        ("official_url", prov.official_url),
        ("retrieved_from", prov.retrieved_from),
        ("retrieved_on", prov.retrieved_on),
        ("title", prov.title),
        ("declared_version", prov.declared_version),
        ("document_date", prov.document_date),
        ("filename_note", prov.filename_note),
    ):
        if value:
            entry[key] = value
    if prov.captures:
        entry["archive_captures"] = [
            {"url": c.url, "captured_on": c.captured_on, **({"digest": c.digest} if c.digest else {})}
            for c in prov.captures
        ]
    if prov.copies:
        entry["corroborating_copies"] = [
            {"url": c.url, "sha256": c.sha256, **({"note": c.note} if c.note else {})}
            for c in prov.copies
        ]
    return entry


def _prior_matrix(repo_root: Path) -> str:
    """What this matrix replaces, with the replaced bytes read from the tree."""
    path = repo_root / PRIOR_MATRIX_REL
    if not path.is_file():
        raise AuthorityAuthoringError(
            f"{PRIOR_MATRIX_REL.as_posix()}: the superseded matrix is not in the tree; this "
            "matrix declares a succession from a record nobody can read"
        )
    return (
        f"the equivalence matrix authored on 2026-10-12, `{PRIOR_MATRIX_REL.as_posix()}` "
        f"(sha256 {file_sha256(path)}). That matrix carried six defaulted rows and two "
        "unresolved, every one of them resting on a 2025 document this repository did not "
        "hold. Three of those documents have since been obtained, so the six defaultings are "
        "re-derived here against the sources themselves and one new row records a difference "
        "they revealed. The superseded matrix stays in the tree unedited: a correction to a "
        "matrix is a successor matrix, and what was believed on 2026-10-12 is part of the "
        "evidence. The specification's decision 3, which pinned one 2026 profile because the "
        "2025 sources were absent, stands as written."
    )


def _supersession(repo_root: Path) -> str:
    """What this index replaces, with the replaced bytes read from the tree.

    The superseded pair is historical evidence and is not edited. Its hashes
    are read here rather than written down, so a superseded record that has
    itself moved shows up as a changed sentence instead of a restated hash that
    no longer matches anything.
    """
    parts = []
    for rel, what in ((PRIOR_INDEX_REL, "index"), (PRIOR_MATRIX_REL, "matrix")):
        path = repo_root / rel
        if not path.is_file():
            raise AuthorityAuthoringError(
                f"{rel.as_posix()}: the superseded {what} is not in the tree; this index "
                "declares a succession from a record nobody can read"
            )
        parts.append(f"`{rel.as_posix()}` (sha256 {file_sha256(path)})")
    return (
        "the authority source index and equivalence matrix authored on 2026-10-12, "
        + " and ".join(parts)
        + ". Those two declared four 2025 documents absent. Three of them have since been "
        "obtained and the fourth is not a document this repository needs, so the entries and "
        "the rows resting on their absence are restated here. The superseded pair stays in the "
        "tree unedited: a correction to an index is a successor index, and the record of what "
        "was believed on 2026-10-12 is part of the evidence."
    )


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
        _refuse_an_unevidenced_rank(source)
        _refuse_a_copy_that_is_not_this_file(source, entry["sha256"])
        entry["source_authenticity"] = source.authenticity
        if source.authenticity_basis:
            entry["source_authenticity_basis"] = source.authenticity_basis
        entry["historical_applicability"] = source.applicability
        if source.applicability_basis:
            entry["historical_applicability_basis"] = source.applicability_basis
        if source.provenance is not None:
            entry["provenance"] = _provenance_entry(source.provenance)
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
                "source_authenticity": "not_applicable",
                "historical_applicability": "not_applicable",
                "role": "immutable_evidence",
                "states": absent.states,
                "required": True,
                "would_settle": sorted(settled_by.get(key, ())),
                "path_note": (
                    "A destination, not a document. This is where the file is filed when it is "
                    "obtained."
                ),
            }
        )

    return {
        "schema": SCHEMA_INDEX,
        "record_type": "authority_source_index",
        "index_name": "msca_dn_authority_sources_2026-10-13",
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
            "states, the class of authority it is, and three separate answers about it: how its "
            "bytes are vouched for here, what says they are the issuing body's, and whether this "
            "was the version in force for the era it states rules for. A document this "
            "repository does not hold is an entry too, so a row cannot rest on one by assuming "
            "what it would say."
        ),
        "review_state": "agent_drafted_pending_operator_review",
        "declared_status": "Inferred",
        "declared_status_note": (
            "Inferred, not Confirmed, and now for a narrower reason than before. Four documents "
            "record where their bytes came from, and three of those were retrieved from the "
            "issuing body's own published addresses and agree with a second, independent copy. "
            "That is evidence of origin, and it is not a hash published by the issuing body. No "
            "entry carries one, so byte integrity stays computed in this tree and no row rests "
            "a Confirmed status on it. The entries with no recorded origin at all are unchanged: "
            "for them nothing says the stored bytes are the official ones."
        ),
        "supersedes": _supersession(repo_root),
        "uncertainties": [
            "No entry is authenticated by a hash from its issuing body, so no matrix row may "
            "declare Confirmed and none does. Three documents are corroborated by a second "
            "independent copy, which is evidence of origin and not an issuer's hash.",
            "The 2025 evaluation form's place in the call is bracketed and not closed. Three "
            "captures of its published address carry one digest, the last of them twenty days "
            "before the deadline, and a version served between captures and never captured "
            "would leave no trace. Row EI-02 keeps that open.",
            "The 2025 application form has no recorded origin and no established place in the "
            "call. It was in this tree before any retrieval was made, and the five rows citing "
            "it are Inferred for that reason.",
            "No separate 2025 call document is held, and none is needed: the work programme "
            "part pinned here carries the call's own conditions and topic text, and the rows "
            "about them cite its pages.",
            "The submission's binding to a call identifier is declared, not evidenced. The one "
            "unobtained entry is the document that would settle it.",
            "Four entries are tracked inputs: the scorecard, the 2026 profile, the appendix "
            "mapping and the specification. Any edit to one makes the matrix stale until it is "
            "re-derived.",
        ],
        "authority_note": (
            "This index confers no authority. It records what is held and what is missing. "
            "Pinning a document is not authenticating it, retrieving one from its published "
            "address is not establishing what governed a closed call, and recording a "
            "destination for an absent document asserts nothing about a file there."
        ),
        "written_by": "tools/author_msca_dn_authority_matrix.py",
        "sources": sources,
    }


def render_matrix(
    rows: Sequence[Mapping[str, Any]], index_sha256: str, prior_matrix: str
) -> dict[str, Any]:
    """The matrix, bound to the index by the hash of the bytes written."""
    return {
        "schema": SCHEMA_MATRIX,
        "record_type": "authority_equivalence_matrix",
        "matrix_name": "msca_dn_2025_to_2026_equivalence_2026-10-13",
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
        "supersedes": prior_matrix,
        "uncertainties": [
            "No row is defaulted. Two are unresolved, and each names what is missing: the "
            "binding of this submission to a call, and the evaluation form version the 2025 "
            "evaluators were given.",
            "Twenty-five rows are Inferred and none is Confirmed. Every 2025 document here is "
            "hashed in this tree and none carries a hash published by its issuing body, so no "
            "row may be Confirmed on byte integrity. Three documents are corroborated by a "
            "second independent copy, which raises what is known about their origin and not "
            "about what governed the call.",
            "Two 2025 authorities state different score resolutions. The work programme says "
            "one decimal place, the evaluation form says half marks. TH-05 shows which was "
            "applied to this submission, from a recorded score no half-mark rule could award. "
            "It does not resolve the conflict in general, and a statement about any other 2025 "
            "proposal must carry it.",
            "Every row citing the 2025 evaluation form inherits EI-02's bracket. Three captures "
            "of one archive are one witness observed three times, and a version served between "
            "two captures and never captured would leave no trace.",
            "The 2025 application form has no recorded origin, and nothing establishes it was "
            "the version in force. The five rows citing it are Inferred for that reason, and "
            "retrieving a corroborating copy of it is not attempted here.",
            "A sourced row claims what its citations measure and no more. SM-01 compares the "
            "aspect anchors in both directions; AM-01 claims an inclusion only, so a 2025 "
            "cross-reference the 2026 mapping has no row for would not have been seen.",
            "Whether an area's rows are all of its scoring-relevant rules is this author's "
            "judgement. The check reads what each row cites and refuses an unsourced relation; "
            "it cannot report a rule nobody wrote a row for.",
            "The rows sourced to the 2025 evaluation's own record settle what was applied to "
            "this submission. None of them settles a rule of the 2025 call, and the check "
            "refuses a call-wide claim resting only on them.",
            "EI-01, the six score-level descriptions, was the largest unsourced input to a "
            "numerical comparison. All six sentences are now located in the 2025 form, word "
            "for word, so the comparison no longer rests on a 2026 document alone.",
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
            "finding that it is wrong, and a row marked equivalent is a statement about the "
            "documents cited rather than about every rule of the call."
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
        MATRIX_REL.as_posix(): canonical_json_bytes(
            render_matrix(rows, index_sha, _prior_matrix(repo_root))
        ),
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
