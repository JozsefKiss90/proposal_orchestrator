"""Author the MSCA-DN evaluation bundle (spec PE-02), byte-equal on replay.

What it writes
--------------
``harness/evaluator_scorecard_msca_dn.json``
    The ten DN aspects, derived from ``ef_he-msca_en.pdf`` V2.2 pp. 4-6 by
    walking the form's ``[OPTION for ...]`` brackets, never typed. Each aspect
    carries its AF V6.0 section heading, derived from the Part B template with
    the ``#@...@#`` tags stripped (spec §2.12), and the rule under which the
    heading and the aspect correspond. The scoring block is derived from the
    form's p. 2 and the ``Weighting:`` lines, the per-criterion threshold and
    the no-aspect-scores rule from General Annexes Part 15 p. 27. Every
    non-DN variant of the form is listed under ``excluded_aspects`` with its
    tag, and Part B2 section 11 (RAISE DN) under ``excluded_sections``.

``harness/rubrics_msca_dn.json``
    Ten specificity-based rubrics (spec decision 14). Each keeps a
    substantiation step that reports grounding *unassessable* when the pack
    carries no claim ledger. Rubric prose, steps, terms and thresholds are
    authored and carry ``Assumed`` status: no source prescribes a rubric.

``harness/criterion_appendix_mapping_msca_dn.json``
    The fifth artifact: which table rows each criterion receives beyond its
    own section. Versioned with the rubric set, which pins its sha256, because
    a silent change to it changes scores.

``harness/profiles/msca_dn_2026_default.json``
    The 2026 profile (spec decision 3): the DN variant, the three criteria,
    the component pins, the structural authority (AF V6.0) and the baseline's
    target call, which this profile owns (spec PE-01).

``docs/tier2a_instrument_schemas/extracted/evaluator_expectation_registry.json``
    Gains an additive ``MSCA-DN`` instrument. The RIA and MSCA-PF entries are
    re-serialised byte-identically; ``tests/harness/test_msca_dn_profile.py``
    pins all three.

The §3.2 defect
---------------
The Impact bullet "Credibility of the measures to enhance the career
perspectives and employability of researchers ..." closes a bracket no
``[OPTION`` opened. The walk records it as untagged and the scorecard resolves
it to Doctoral networks on three grounds (spec §3.2), each of which the test
checks against the form: the plural matches the DN variants and the PF bullet
below is singular; no other bracket is open there; and the ESR, read once in
session and never copied here, lists it among the DN Impact aspects.

Run it from the repository root::

    py -3.10 -m tools.author_msca_dn_bundle            # write
    py -3.10 -m tools.author_msca_dn_bundle --check    # exit 1 if any file would change

Constitutional standing: an authoring tool, not a runtime component. It
evaluates no gate and invokes no Claude. It coins no ``schema_id``
(CLAUDE.md §16.3). The harness it feeds is an execution aid under §10.2.
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
from runner.paths import find_repo_root
from runner.source_index import read_page_text

# --------------------------------------------------------------------------- #
# Constants: the spec's names
# --------------------------------------------------------------------------- #

SPEC_REL = "plans/msca_dn_pre_evaluation_spec.md"

EVALUATION_FORM_REL = "docs/tier2a_instrument_schemas/evaluation_forms/msca/ef_he-msca_en.pdf"
EVALUATION_FORM_VERSION = "2.2"
EVALUATION_FORM_DATE = "2025-12-17"
#: The running header every criteria page repeats; stripped before parsing.
EVALUATION_FORM_HEADER = "EU Grants: Evaluation form (HE MSCA): V.2.2 – 17.12.2025"
#: The pages the walk reads: criteria on 4-6, Score 3's weighting on 7.
CRITERIA_PAGES = (4, 5, 6, 7)
SCORING_PAGE = 2

APPLICATION_FORM_V6_REL = (
    "docs/tier2a_instrument_schemas/application_forms/msca/"
    "Tpl_Application Form (Part B) (HE MSCA DN).pdf"
)
APPLICATION_FORM_V6_VERSION = "6.0"
APPLICATION_FORM_V6_DATE = "2026-04-04"
APPLICATION_FORM_V6_HEADER = "EU Grants: Application form (HE MSCA DN): V6.0 – 04.04.2026"
#: The Part B template pages carrying headings §1.1 to §3.2.
TEMPLATE_PAGES = (28, 29, 30, 31)
APPLICATION_FORM_V5_REL = "docs/tier2a_instrument_schemas/application_forms/msca/af_he-msca-dn_en.pdf"
APPLICATION_FORM_V5_VERSION = "5.0"

GENERAL_ANNEXES_REL = (
    "docs/tier1_normative_framework/programme_guidance/"
    "wp-15-general-annexes_horizon-2026-2027_en.pdf"
)
GENERAL_ANNEXES_PAGE = 27

SCORECARD_REL = "harness/evaluator_scorecard_msca_dn.json"
RUBRICS_REL = "harness/rubrics_msca_dn.json"
MAPPING_REL = "harness/criterion_appendix_mapping_msca_dn.json"
PROFILE_REL = "harness/profiles/msca_dn_2026_default.json"
REGISTRY_REL = "docs/tier2a_instrument_schemas/extracted/evaluator_expectation_registry.json"

SCORECARD_ID = "msca_dn_evaluation_scorecard"
RUBRIC_SET_ID = "msca_dn_rubrics"
RUBRIC_SET_VERSION = "1.0.0"
PROFILE_ID = "msca_dn_2026_default"
REGISTRY_INSTRUMENT_TYPE = "MSCA-DN"
APPLICABLE_VARIANT = "Doctoral networks"
TARGET_CALL_ID = "HORIZON-MSCA-2026-DN-01"

DECLARED_ON = "2026-10-04"

#: The form's bullet glyph on the criteria pages.
BULLET = "•"

#: The closed variant vocabulary, longest first so "COFUND Choose Europe" is
#: never read as "COFUND" plus a dangling "Choose Europe".
KNOWN_VARIANTS: tuple[str, ...] = (
    "Doctoral networks",
    "Postdoctoral fellowships",
    "Staff exchanges",
    "COFUND Choose Europe",
    "COFUND",
    "Special needs allowances",
)
_VARIANT_ALT = "|".join(re.escape(v) for v in KNOWN_VARIANTS)
#: ``[OPTION for <tag>`` followed by ``:``, ``;`` or nothing at all — the two
#: DN brackets on pp. 4-5 carry no delimiter between the tag and the text.
_OPEN_TAG_RE = re.compile(
    rf"^\[OPTION for ((?:all MSCA except |MSCA )(?:{_VARIANT_ALT})"
    rf"(?:(?:, | and )(?:{_VARIANT_ALT}))*)\s*[:;]?\s*"
)
_TEMPLATE_TAG_RE = re.compile(r"\s*#[@§][A-Z0-9-]+[@§]#")

#: The ten DN aspects in form order: (anchor, aspect id, criterion id).
DN_ASPECTS: tuple[tuple[str, str, str], ...] = (
    ("1.1", "exc-obj", "excellence"),
    ("1.2", "exc-method", "excellence"),
    ("1.3", "exc-training", "excellence"),
    ("1.4", "exc-supervision", "excellence"),
    ("2.1", "imp-structuring", "impact"),
    ("2.2", "imp-career", "impact"),
    ("2.3", "imp-dissemination", "impact"),
    ("2.4", "imp-magnitude", "impact"),
    ("3.1", "impl-workplan", "implementation"),
    ("3.2", "impl-participants", "implementation"),
)

CRITERIA: tuple[tuple[str, str, int, str], ...] = (
    # (criterion id, form heading number, score field number, registry id)
    ("excellence", "1", 1, "Excellence"),
    ("impact", "2", 2, "Impact"),
    ("implementation", "3", 3, "Implementation"),
)
#: Aspect id -> criterion id, the one lookup every renderer needs.
CRITERION_OF: dict[str, str] = {aspect_id: criterion_id for _a, aspect_id, criterion_id in DN_ASPECTS}

#: Tier 2B work-programme extract carrying the 2026 DN call and its deadline.
WORK_PROGRAMME_REL = "docs/tier2b_topic_and_call_sources/work_programmes/msca/HORIZON-MSCA.json"

#: The form's criterion headings, as printed after the number.
CRITERION_NAMES: dict[str, str] = {
    "excellence": "Excellence",
    "impact": "Impact",
    "implementation": "Quality and efficiency of the implementation",
}

#: Glosses the AF V6.0 heading adds to the form aspect; removed before the
#: correspondence check, lower-cased (spec PE-02 acceptance).
AF_HEADING_GLOSSES: dict[str, tuple[str, ...]] = {
    "2.1": ("(=lasting) ", " after the end of the dn funding"),
    "2.4": (" (project’s pathways towards impact)",),
}


class AuthoringError(RuntimeError):
    """The stored form does not carry what the bundle claims it carries."""


# --------------------------------------------------------------------------- #
# Derivation from the stored PDFs
# --------------------------------------------------------------------------- #


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def strip_template_tags(text: str) -> str:
    """Remove ``#@...@#`` and ``#§...§#`` processing tags (spec §2.12)."""
    return " ".join(_TEMPLATE_TAG_RE.sub("", text).split())


def _page_body(repo_root: Path, rel: str, page: int, header: str) -> str:
    """One page's normalised text with its running header removed.

    The header must carry the version the bundle's provenance claims; a form
    reissued under a new version stops matching here rather than being graded
    silently (the RIA profile's rule, kept).
    """
    text = read_page_text(repo_root / rel, page)
    prefix = f"{header} {page} " if rel == EVALUATION_FORM_REL else None
    if prefix is not None:
        if not text.startswith(prefix):
            raise AuthoringError(f"{rel} page {page} does not open with {prefix!r}")
        return text[len(prefix):]
    # The application form prints "Call: ... EU Grants: ... Part B - Page N of ..."
    marker = header
    idx = text.find(marker)
    if idx < 0:
        raise AuthoringError(f"{rel} page {page} does not carry {marker!r}")
    rest = text[idx + len(marker):]
    m = re.match(r"\s*Part B - Page \d+ of (?:\[Page limit\]|\d+)\s*", rest)
    if not m:
        raise AuthoringError(f"{rel} page {page}: no 'Part B - Page' marker after the header")
    return rest[m.end():]


@dataclass(frozen=True)
class FormAspect:
    """One bullet of the evaluation form's criteria pages."""

    criterion_id: str
    text: str
    option_tag: Optional[str]  # the tag's text after "[OPTION for ", or None
    opens: bool
    closes: bool
    page: int | str  # "a-b" when the bullet breaks across the page boundary
    applicable_dn: bool

    @property
    def untagged(self) -> bool:
        return self.option_tag is None


def _applies_to_dn(tag: str) -> bool:
    if tag.startswith("all MSCA except "):
        return APPLICABLE_VARIANT not in tag
    return APPLICABLE_VARIANT in tag


def derive_form_aspects(repo_root: Path) -> tuple[FormAspect, ...]:
    """Walk the form's criteria bullets, carrying the open bracket across them."""
    pages = {p: _page_body(repo_root, EVALUATION_FORM_REL, p, EVALUATION_FORM_HEADER) for p in CRITERIA_PAGES}
    joined = " ".join(pages[p] for p in CRITERIA_PAGES)
    aspects: list[FormAspect] = []
    cursor = 0
    for criterion_id, number, _score, _reg in CRITERIA:
        start = joined.find(f"{number}. {CRITERION_NAMES[criterion_id]}", cursor)
        if start < 0:
            raise AuthoringError(f"criterion {number} heading not found")
        lead = joined.find("description in the work programme:", start)
        end = joined.find("Comments:", lead)
        cursor = end
        if lead < 0 or end < 0:
            raise AuthoringError(f"criterion {number}: aspect block not delimited")
        block = joined[lead + len("description in the work programme:"):end]
        open_tag: Optional[str] = None
        for raw in block.split(BULLET)[1:]:
            bullet = " ".join(raw.split())
            if not bullet:
                continue
            m = _OPEN_TAG_RE.match(bullet)
            opens = m is not None
            if m:
                if open_tag is not None:
                    raise AuthoringError(f"bracket opened inside an open bracket: {bullet[:60]!r}")
                open_tag = m.group(1)
                bullet = bullet[m.end():]
            closes = bullet.endswith("]")
            if closes:
                bullet = bullet[:-1].rstrip()
            tag = open_tag
            page: int | str | None = next((p for p in CRITERIA_PAGES if bullet in pages[p]), None)
            if page is None:
                # A bullet broken across the page boundary (the COFUND Excellence
                # bullet does this): labelled "a-b", as the RIA scorecard labels its one.
                words = bullet.split(" ")
                for p in CRITERIA_PAGES[:-1]:
                    for k in range(1, len(words)):
                        head, tail = " ".join(words[:-k]), " ".join(words[-k:])
                        if pages[p].endswith(head) and pages[p + 1].startswith(tail):
                            page = f"{p}-{p + 1}"
                            break
                    if page is not None:
                        break
                if page is None:
                    raise AuthoringError(f"bullet found on no page: {bullet[:60]!r}")
            aspects.append(
                FormAspect(
                    criterion_id=criterion_id,
                    text=bullet,
                    option_tag=tag,
                    opens=opens,
                    closes=closes,
                    page=page,
                    applicable_dn=_applies_to_dn(tag) if tag is not None else False,
                )
            )
            if closes:
                open_tag = None
        if open_tag is not None:
            raise AuthoringError(f"criterion {number}: bracket {open_tag!r} never closed")
    return tuple(aspects)


def _is_the_untagged_career_bullet(aspect: FormAspect) -> bool:
    return (
        aspect.untagged
        and aspect.closes
        and aspect.criterion_id == "impact"
        and aspect.text.startswith("Credibility of the measures to enhance the career perspectives")
        and "researchers" in aspect.text
        and "their" in aspect.text
    )


def dn_aspect_rows(repo_root: Path) -> tuple[dict[str, Any], ...]:
    """The ten DN aspects with ids, anchors, tags and the §3.2 resolution applied."""
    walk = derive_form_aspects(repo_root)
    untagged = [a for a in walk if a.untagged]
    if len(untagged) != 1 or not _is_the_untagged_career_bullet(untagged[0]):
        raise AuthoringError(
            "the form no longer carries exactly one untagged bullet, the §3.2 career "
            f"aspect — re-examine the resolution (found {len(untagged)})"
        )
    applicable = [a for a in walk if a.applicable_dn or a is untagged[0]]
    if len(applicable) != len(DN_ASPECTS):
        raise AuthoringError(f"expected {len(DN_ASPECTS)} DN aspects, the walk yields {len(applicable)}")
    rows: list[dict[str, Any]] = []
    for (anchor, aspect_id, criterion_id), aspect in zip(DN_ASPECTS, applicable):
        if aspect.criterion_id != criterion_id:
            raise AuthoringError(f"{aspect_id}: walk order puts it under {aspect.criterion_id}")
        if not isinstance(aspect.page, int):
            raise AuthoringError(f"{aspect_id}: a graded aspect must sit on one page, found {aspect.page!r}")
        row: dict[str, Any] = {
            "id": aspect_id,
            "anchor": anchor,
            "source_page": aspect.page,
            "option_tag": aspect.option_tag if aspect.option_tag is not None else f"MSCA {APPLICABLE_VARIANT}",
            "option_tag_status": "Confirmed" if aspect.option_tag is not None else "Inferred",
            "text": aspect.text,
        }
        if aspect.untagged:
            row["option_tag_resolution"] = "provenance.untagged_bullet_resolution"
        rows.append(row)
    return tuple(rows)


def excluded_aspect_rows(repo_root: Path) -> tuple[tuple[dict[str, Any], ...], tuple[dict[str, Any], ...]]:
    """Every criteria bullet the DN filter drops, verbatim with its tag.

    Returns ``(excluded, sharing_included_text)``. The second group holds the
    non-DN bullets whose text equals a DN aspect's text under the same
    criterion (the Staff exchanges bracket repeats exc-obj verbatim). The
    substrate loader matches registry rows to scorecard entries by text, so
    such a bullet cannot sit in ``excluded_aspects`` without making the row
    ambiguous; it is recorded beside them instead, under its own tag.
    """
    included = {(CRITERION_OF[r["id"]], r["text"]) for r in dn_aspect_rows(repo_root)}
    rows: list[dict[str, Any]] = []
    shared: list[dict[str, Any]] = []
    for aspect in derive_form_aspects(repo_root):
        if aspect.applicable_dn or aspect.untagged:
            continue
        row: dict[str, Any] = {
            "criterion": aspect.criterion_id,
            "source_page": aspect.page,
            "option_tag": aspect.option_tag,
            "text": aspect.text,
            "reason": f"Tagged for {aspect.option_tag!s}, which does not include {APPLICABLE_VARIANT}; must not be graded for a DN proposal.",
        }
        if aspect.text.count(". ") >= 1 and "Quality and ambition of the research" in aspect.text:
            row["form_note"] = (
                "Two aspects printed as one bullet in the form: the second starts at "
                "'Quality and ambition of the research'. Kept as the form prints it."
            )
        if (aspect.criterion_id, aspect.text) in included:
            row["reason"] = (
                f"Tagged for {aspect.option_tag!s}, but its text equals a DN aspect's under the same "
                "criterion. The text is graded once, under its DN tag; this bullet cannot be listed as "
                "excluded because the registry row would then match two scorecard entries."
            )
            shared.append(row)
        else:
            rows.append(row)
    return tuple(rows), tuple(shared)


def derive_scoring(repo_root: Path) -> dict[str, Any]:
    """Scale, levels, thresholds and weights from the form's own pages."""
    page2 = _page_body(repo_root, EVALUATION_FORM_REL, SCORING_PAGE, EVALUATION_FORM_HEADER)
    levels: dict[str, str] = {}
    for m in re.finditer(r"(\d) — (.*?)(?= \d — |Thresholds & weighting)", page2):
        levels[m.group(1)] = m.group(2).strip()
    if sorted(levels) != ["0", "1", "2", "3", "4", "5"]:
        raise AuthoringError(f"page 2 levels not derivable: {sorted(levels)}")
    scale_quote = "Scoring must be in the range from 0-5. Scores will be awarded with a resolution of one decimal place."
    threshold_quote = "The overall threshold, applying to the sum of the 3 individual scores, is 70 points."
    weighting_quote = "Weighting is only for the ranking (not to determine if the proposal passed the thresholds)."
    for quote in (scale_quote, threshold_quote, weighting_quote):
        if quote not in page2:
            raise AuthoringError(f"page 2 no longer prints {quote!r}")
    joined = " ".join(_page_body(repo_root, EVALUATION_FORM_REL, p, EVALUATION_FORM_HEADER) for p in CRITERIA_PAGES)
    weights: dict[str, int] = {}
    pages: dict[str, int] = {}
    for criterion_id, _n, score, _reg in CRITERIA:
        found = re.search(rf"Score {score} \(0-5\): Weighting: (\d+)%", joined)
        if not found:
            raise AuthoringError(f"Score {score} weighting not found")
        weights[criterion_id] = int(found.group(1))
        pages[criterion_id] = next(
            p for p in CRITERIA_PAGES if f"Score {score} (0-5): Weighting:" in _page_body(repo_root, EVALUATION_FORM_REL, p, EVALUATION_FORM_HEADER)
        )
    if "Total score Overall threshold /100" not in joined:
        raise AuthoringError("the form no longer prints 'Total score Overall threshold /100'")
    ga = read_page_text(repo_root / GENERAL_ANNEXES_REL, GENERAL_ANNEXES_PAGE)
    ga_aspects = "Evaluation scores will be awarded for the criteria, and not for the different aspects listed in the table."
    ga_threshold = "The threshold for individual criteria will be 3."
    ga_overall = "The overall threshold, applying to the sum of the three individual scores, will be 10."
    for quote in (ga_aspects, ga_threshold, ga_overall):
        if quote not in ga:
            raise AuthoringError(f"General Annexes p. {GENERAL_ANNEXES_PAGE} no longer prints {quote!r}")
    return {
        "levels": levels,
        "scale_quote": scale_quote,
        "threshold_quote": threshold_quote,
        "weighting_quote": weighting_quote,
        "weights": weights,
        "weighting_pages": pages,
        "general_annexes": {
            "no_aspect_scores_quote": ga_aspects,
            "individual_threshold_quote": ga_threshold,
            "annex_d_overall_threshold_quote": ga_overall,
        },
    }


def derive_af_headings(repo_root: Path) -> dict[str, dict[str, Any]]:
    """The AF V6.0 template headings §1.1 to §3.2, tag-stripped, by anchor."""
    pages = {
        p: strip_template_tags(_page_body(repo_root, APPLICATION_FORM_V6_REL, p, APPLICATION_FORM_V6_HEADER))
        for p in TEMPLATE_PAGES
    }
    joined = " ".join(pages[p] for p in TEMPLATE_PAGES)
    terminators = {
        "2.1": " 2.2 ",
        "2.2": " • ",
    }
    headings: dict[str, dict[str, Any]] = {}
    cursor = 0
    for anchor, _id, _c in DN_ASPECTS:
        start = joined.find(f" {anchor} ", cursor)
        if start < 0:
            raise AuthoringError(f"AF V6.0 template: heading {anchor} not found")
        start += len(anchor) + 2
        end = joined.find(terminators.get(anchor, " Required sub-headings:"), start)
        if end < 0:
            raise AuthoringError(f"AF V6.0 template: heading {anchor} not terminated")
        heading = joined[start:end].strip()
        page = next((p for p in TEMPLATE_PAGES if heading in pages[p]), None)
        if page is None:
            raise AuthoringError(f"AF V6.0 template: heading {anchor} spans pages")
        headings[anchor] = {"text": heading, "page": page}
        cursor = end
    return headings


def heading_corresponds(aspect_text: str, heading: str, anchor: str) -> bool:
    """The PE-02 correspondence rule: equal after glosses, case and the final period."""
    h = " ".join(heading.split()).lower()
    for gloss in AF_HEADING_GLOSSES.get(anchor, ()):
        if gloss not in h:
            return False
        h = h.replace(gloss, "")
    a = " ".join(aspect_text.split()).lower().rstrip(".")
    return h.rstrip(".") == a


def derive_section_11(repo_root: Path) -> dict[str, Any]:
    """Part B2 section 11's heading from the V6.0 instructions page."""
    for page in (23, 24):
        text = strip_template_tags(read_page_text(repo_root / APPLICATION_FORM_V6_REL, page))
        m = re.search(r"11\. (RAISE DN \(Only for applicants of HORIZON-RAISE-2026-01-MSCA, 1 page\))", text)
        if m:
            return {"section": "11", "heading": m.group(1), "source_page": page}
    raise AuthoringError("AF V6.0: section 11 heading not found on pp. 23-24")


# --------------------------------------------------------------------------- #
# Rendering: the scorecard
# --------------------------------------------------------------------------- #


def render_scorecard(repo_root: Path) -> dict[str, Any]:
    rows = dn_aspect_rows(repo_root)
    scoring = derive_scoring(repo_root)
    headings = derive_af_headings(repo_root)
    for row in rows:
        heading = headings[row["anchor"]]
        if not heading_corresponds(row["text"], heading["text"], row["anchor"]):
            raise AuthoringError(f"{row['id']}: AF V6.0 heading does not correspond to the form aspect")
        row["af_v6_heading"] = heading["text"]
        row["af_v6_heading_page"] = heading["page"]
        row["af_v6_heading_glosses"] = list(AF_HEADING_GLOSSES.get(row["anchor"], ()))
    by_criterion: dict[str, list[dict[str, Any]]] = {c[0]: [] for c in CRITERIA}
    for row in rows:
        by_criterion[CRITERION_OF[row["id"]]].append(row)
    weights = scoring["weights"]
    criteria = []
    for criterion_id, number, score, _reg in CRITERIA:
        aspects = by_criterion[criterion_id]
        pages = sorted({a["source_page"] for a in aspects})
        criteria.append(
            {
                "id": criterion_id,
                "name": CRITERION_NAMES[criterion_id],
                "weight_pct": weights[criterion_id],
                "threshold_score": 3,
                "score_field": f"Score {score}",
                "weighting_page": scoring["weighting_pages"][criterion_id],
                "source_page": pages[0] if len(pages) == 1 else f"{pages[0]}-{pages[-1]}",
                "aspects": aspects,
            }
        )
    section_11 = derive_section_11(repo_root)
    excluded, shared = excluded_aspect_rows(repo_root)
    return {
        "scorecard_id": SCORECARD_ID,
        "instrument": "MSCA Doctoral Networks (standard DN)",
        "provenance": {
            "source_form": "Horizon Europe Evaluation Form (HE MSCA)",
            "version": EVALUATION_FORM_VERSION,
            "version_date": EVALUATION_FORM_DATE,
            "source_path": EVALUATION_FORM_REL,
            "criteria_pages": "4-6",
            "weighting_pages": "5-7",
            "scoring_page": SCORING_PAGE,
            "derivation": (
                "Aspect texts, levels, weights and quotes are derived from the stored PDFs by "
                "tools/author_msca_dn_bundle.py through runner.source_index.read_page_text "
                "(whitespace normalised, every other character carried through) and are never "
                "typed. tests/harness/test_msca_dn_profile.py re-derives them."
            ),
            "scoring_authority": "The evaluation form (Tier 2A), with the per-criterion threshold and the no-aspect-scores rule from General Annexes Part 15 (Tier 1).",
            "structural_authority": {
                "source_path": APPLICATION_FORM_V6_REL,
                "version": APPLICATION_FORM_V6_VERSION,
                "version_date": APPLICATION_FORM_V6_DATE,
                "template_pages": "28-31",
                "note": (
                    "The page footer dates V6.0 to 04.04.2026; the form's own history table says "
                    "26.03.2026. The footer is cited and the discrepancy recorded, not resolved (spec §2.12)."
                ),
                "template_tag_rule": "Headings derived from either application form strip #@...@# and #§...§# tags before use (spec §2.12).",
            },
            "v5_equivalence": {
                "source_path": APPLICATION_FORM_V5_REL,
                "version": APPLICATION_FORM_V5_VERSION,
                "statement": (
                    "For HORIZON-MSCA-2026-DN-01 the V5.0 (2025 call) and V6.0 (2026 call) Part B "
                    "templates are structurally identical: the same ten numbered aspect headings §1.1 "
                    "to §3.2, the same Tables 3.1 a to 3.1 e, the same 34-page Part B1 cap with "
                    "sections 1-3 at 30, the same Part B2 sections 4 to 10. V6.0 adds Part B2 "
                    "section 11 (RAISE DN) for a different call. Measured in spec §2.12."
                ),
            },
            "dn_scope_rule": (
                "Keep every aspect whose [OPTION for ...] tag names MSCA Doctoral networks, plus the "
                "'all MSCA except ...' aspects whose exception list does not name it. Exclude every "
                "Postdoctoral fellowships, Staff exchanges, COFUND, COFUND Choose Europe and Special "
                "needs allowances variant."
            ),
            "untagged_bullet_resolution": {
                "aspect_id": "imp-career",
                "defect": (
                    "The bullet closes a bracket with ']' but no '[OPTION for ...' opens it. The DN "
                    "bracket opened at imp-structuring and closed at 'developing sustainable elements "
                    "of doctoral programmes. ]'."
                ),
                "resolved_to": f"MSCA {APPLICABLE_VARIANT}",
                "status": "Inferred",
                "grounds": [
                    "The plural 'researchers ... their' matches the DN variants; the Postdoctoral fellowships bullet immediately below is singular ('the researcher ... his/her').",
                    "The ESR, assessing a DN proposal, lists it as one of the four Impact aspects considered (read once in session on 2026-10-04; the ESR's content is not copied here, spec decision 12).",
                    "No other variant's bracket is open at that point in the document: the walk in tools/author_msca_dn_bundle.py records the previous bullet as closing.",
                ],
            },
            "esr_cross_confirmation": (
                "Read once in session on 2026-10-04: nine of the ten aspect texts occur verbatim in the "
                "ESR; exc-training differs only by a hyphenation line break ('inter- sectoral'). No ESR "
                "text is stored in this bundle."
            ),
            "verified_by": "tools/author_msca_dn_bundle.py (derived) and tests/harness/test_msca_dn_profile.py (re-derived)",
            "verified_on": DECLARED_ON,
        },
        "scoring": {
            "scale": "0-5, one decimal place",
            "scale_source_quote": scoring["scale_quote"],
            "levels": scoring["levels"],
            "levels_note": "Verbatim from the form p. 2, each level's full sentence.",
            "individual_threshold": 3,
            "individual_threshold_source": {
                "source_path": GENERAL_ANNEXES_REL,
                "page": GENERAL_ANNEXES_PAGE,
                "quote": scoring["general_annexes"]["individual_threshold_quote"],
            },
            "no_aspect_scores_rule": {
                "source_path": GENERAL_ANNEXES_REL,
                "page": GENERAL_ANNEXES_PAGE,
                "quote": scoring["general_annexes"]["no_aspect_scores_quote"],
                "consequence": "Scores are awarded per criterion. The ten aspect cells inform a criterion score; they are never averaged into one (spec decisions 5 and 11).",
            },
            "overall_threshold": 70,
            "overall_max": 100,
            "threshold_source_quote": scoring["threshold_quote"],
            "weighting_source_quote": scoring["weighting_quote"],
            "total_formula": "S = 10·E + 6·I + 4·Q",
            "total_formula_note": "Each 0-5 score times weight_pct/5: 50% -> 10, 30% -> 6, 20% -> 4; maximum 100 (form p. 7 'Total score Overall threshold /100').",
            "annex_d_override": {
                "annex_d_rule": scoring["general_annexes"]["annex_d_overall_threshold_quote"],
                "form_rule": scoring["threshold_quote"],
                "resolution": (
                    "The MSCA evaluation form (Tier 2A) overrides the General Annexes' generic overall "
                    "threshold of 10 on the unweighted sum with 70 on a weighted total out of 100; the "
                    "General Annexes themselves allow it ('Specific calls or topics may have different "
                    "rules'). The per-criterion threshold of 3 is unchanged. Tier interaction logged per "
                    "CLAUDE.md §12.3 in docs/tier4_orchestration_state/decision_log/msca-dn-pe02-evaluation-bundle_2026-10-04.json."
                ),
            },
            "weighting_note": "Each of the 3 criteria is scored 0-5, then weighted into a total out of 100; overall pass threshold is 70/100. Weighting is used for ranking only (form p. 2).",
        },
        "criteria": criteria,
        "excluded_aspects": list(excluded),
        "excluded_aspects_sharing_included_text": list(shared),
        "excluded_sections": [
            {
                **section_11,
                "source_path": APPLICATION_FORM_V6_REL,
                "reason": (
                    "Part B2 section 11 belongs to HORIZON-RAISE-2026-01-MSCA, not to "
                    f"{TARGET_CALL_ID}. It is no evaluation-form aspect, anchors no rubric and "
                    "appears in no criterion appendix mapping."
                ),
            }
        ],
    }


# --------------------------------------------------------------------------- #
# Rendering: the rubric set (authored, Assumed)
# --------------------------------------------------------------------------- #

_SUBSTANTIATION_STEP = (
    "Substantiation: if the pack carries claim-ledger entries, check the load-bearing statements "
    "against them and report grounding as passed or failed. If the pack carries no claim ledger, "
    "report grounding UNASSESSABLE — never failed and never passed — and say so in the rationale."
)
_CLOSING_STEP = (
    "If pack_status is insufficient_context, or the spans do not substantively cover the aspect, "
    "do not report a clean pass."
)

_RUBRICS: tuple[dict[str, Any], ...] = (
    {
        "expectation_key": "exc-obj",
        "rubric": (
            "Decide whether the evidence pack shows the section ADDRESSES this aspect with SPECIFIC content: "
            "named research and innovation objectives, individual doctoral-candidate projects with a title, "
            "objectives and expected results, and a stated advance over an identified state of the art. "
            "Generic ambition language, or objectives that cannot be told apart from any other network's, "
            "must not pass. Judge specificity and addressal; do not reward eloquence or formatting."
        ),
        "evaluation_steps": [
            "List the spans that state research or innovation objectives, or an individual DC project (title, objectives, expected results, secondments).",
            "Check each objective is concrete: an identifiable outcome, a scope, and a relation to a named state of the art or existing programme.",
            "Check the DC projects are integrated into the overall programme rather than listed beside it.",
            _SUBSTANTIATION_STEP,
            _CLOSING_STEP,
        ],
        "selection_terms": [
            "objective", "objectives", "state of the art", "state-of-the-art", "ambition", "ambitious",
            "research question", "research questions", "hypothesis", "hypotheses", "novelty", "novel",
            "advance", "beyond", "doctoral candidate", "DC", "individual research project",
            "research programme", "pertinence", "overview",
        ],
        "anchor_sub_section_ids": ["1.1"],
    },
    {
        "expectation_key": "exc-method",
        "rubric": (
            "Decide whether the evidence pack shows the section ADDRESSES this aspect with SPECIFIC content: "
            "a described overall methodology with its concepts, models and assumptions; how methods from "
            "different disciplines are integrated or why no interdisciplinary approach is needed; how the gender "
            "dimension and other diversity aspects enter the research content or why they do not; and which open "
            "science practices are adopted. Naming a practice without saying how it applies to this work must "
            "not pass. Judge specificity and addressal."
        ),
        "evaluation_steps": [
            "List the spans describing the overall methodology, including concepts, models and assumptions.",
            "Check the integration of methods and disciplines is explained, or a justification is given for not needing one.",
            "Check the gender dimension and other diversity aspects are addressed in the research content, or justified as not relevant; and that open science practices are named with how they apply.",
            _SUBSTANTIATION_STEP,
            _CLOSING_STEP,
        ],
        "selection_terms": [
            "methodology", "method", "methods", "approach", "interdisciplinary", "inter-disciplinary",
            "multidisciplinary", "gender dimension", "gender", "diversity", "open science", "open access",
            "data management", "FAIR", "preregistration", "reproducibility", "concept", "model", "assumption",
            "work package",
        ],
        "anchor_sub_section_ids": ["1.2"],
    },
    {
        "expectation_key": "exc-training",
        "rubric": (
            "Decide whether the evidence pack shows the section ADDRESSES this aspect with SPECIFIC content: "
            "an overview and content structure of the doctoral training programme, network-wide training events "
            "with a lead institution and timing, transferable-skills, inter/multidisciplinary and inter-sectoral "
            "training, and how network-wide events complement local programmes. A list of event names with no "
            "content or no link to the research must not pass. Judge specificity and addressal."
        ),
        "evaluation_steps": [
            "List the spans describing the training programme's structure and the network-wide training events, schools, courses and conferences.",
            "Check the events are concrete: a topic, a lead or host, a timing or ECTS, and a link to the research or to transferable skills.",
            "Check inter/multidisciplinary, inter-sectoral, gender and other diversity aspects of the training are addressed, and local programmes are complemented rather than duplicated.",
            _SUBSTANTIATION_STEP,
            _CLOSING_STEP,
        ],
        "selection_terms": [
            "training", "training programme", "training event", "training events", "school", "summer school",
            "winter school", "course", "courses", "workshop", "ECTS", "transferable skills", "transferable",
            "inter-sectoral", "intersectoral", "secondment", "secondments", "local training", "doctoral programme",
            "doctoral school", "table 1",
        ],
        "anchor_sub_section_ids": ["1.3"],
    },
    {
        "expectation_key": "exc-supervision",
        "rubric": (
            "Decide whether the evidence pack shows the section ADDRESSES this aspect with SPECIFIC content: "
            "the qualifications and supervision experience of the supervisors, how supervision of the doctoral "
            "candidates is organised with progress and review procedures, feedback mechanisms and support, and "
            "the joint supervision arrangements where the mode requires them. A statement that supervisors are "
            "experienced, with nothing behind it, must not pass. Judge specificity and addressal."
        ),
        "evaluation_steps": [
            "List the spans describing supervisor qualifications and experience, the supervision arrangements, and any joint supervision.",
            "Check the arrangements are concrete: who supervises whom, how often progress is reviewed, what feedback and support exist, and what the career development plan contains.",
            "Check the mandatory joint supervision is addressed for the declared implementation mode, or stated as not applicable for a standard DN.",
            _SUBSTANTIATION_STEP,
            _CLOSING_STEP,
        ],
        "selection_terms": [
            "supervision", "supervisor", "supervisors", "co-supervisor", "co-supervision", "joint supervision",
            "supervisory", "mentoring", "mentor", "career development plan", "progress review", "feedback",
            "thesis", "PhD", "doctorate", "guidelines for MSCA supervision", "Charter",
        ],
        "anchor_sub_section_ids": ["1.4"],
    },
    {
        "expectation_key": "imp-structuring",
        "rubric": (
            "Decide whether the evidence pack shows the section ADDRESSES this aspect with SPECIFIC content: "
            "how the project structures doctoral training at the European level and strengthens innovation "
            "capacity, what the non-academic sector contributes to the training (secondments, research, "
            "network-wide training) and which elements of the doctoral programme are designed to last beyond "
            "the funding. A claim of European structuring with no named mechanism must not pass. Judge "
            "specificity and addressal."
        ),
        "evaluation_steps": [
            "List the spans describing the contribution to structuring doctoral training at the European level and to innovation capacity.",
            "Check the non-academic sector's contribution is concrete: named partners, secondments with purpose and duration, roles in research or training.",
            "Check the sustainable elements are named and their continuation after the project is explained.",
            _SUBSTANTIATION_STEP,
            _CLOSING_STEP,
        ],
        "selection_terms": [
            "structuring", "European level", "innovation capacity", "non-academic", "industry", "industrial",
            "sustainable", "sustainability", "lasting", "beyond the project", "after the project", "doctoral programme",
            "doctoral school", "joint", "network", "secondment", "secondments", "collaboration",
        ],
        "anchor_sub_section_ids": ["2.1"],
    },
    {
        "expectation_key": "imp-career",
        "rubric": (
            "Decide whether the evidence pack shows the section ADDRESSES this aspect with SPECIFIC content: "
            "named measures that enhance the doctoral candidates' career perspectives and employability in "
            "academia and beyond, and the technical and transferable skills the project equips them with. "
            "A statement that careers will benefit, with no measure attached, must not pass. Judge specificity "
            "and addressal."
        ),
        "evaluation_steps": [
            "List the spans describing career measures, employability and skills development for the doctoral candidates.",
            "Check the measures are concrete: a named activity, who delivers it, and the career option or skill it serves.",
            "Check both academic and non-academic career paths are addressed, or the omission is justified.",
            _SUBSTANTIATION_STEP,
            _CLOSING_STEP,
        ],
        "selection_terms": [
            "career", "careers", "employability", "employment", "skills", "skill", "transferable skills",
            "career development", "career perspectives", "entrepreneurship", "job", "jobs", "sector",
            "academia", "academic", "non-academic", "mentoring", "alumni",
        ],
        "anchor_sub_section_ids": ["2.2"],
    },
    {
        "expectation_key": "imp-dissemination",
        "rubric": (
            "Decide whether the evidence pack shows the section ADDRESSES this aspect with SPECIFIC content: "
            "a dissemination and exploitation plan with target groups, measures, objectives and indicators; "
            "communication activities with messages, tools and channels; and an outline strategy for managing "
            "intellectual property. A list of channels with no target group or objective must not pass. Judge "
            "specificity and addressal."
        ),
        "evaluation_steps": [
            "List the spans describing dissemination, exploitation and communication measures and the intellectual property strategy.",
            "Check each measure names a target group, an objective and a way of monitoring it.",
            "Check exploitation and IP management are addressed with concrete actions during and after the project.",
            _SUBSTANTIATION_STEP,
            _CLOSING_STEP,
        ],
        "selection_terms": [
            "dissemination", "exploitation", "communication", "outreach", "public engagement", "open access",
            "publication", "publications", "intellectual property", "IP", "IPR", "patent", "target group",
            "target groups", "website", "social media", "stakeholder", "stakeholders", "indicator", "indicators",
        ],
        "anchor_sub_section_ids": ["2.3"],
    },
    {
        "expectation_key": "imp-magnitude",
        "rubric": (
            "Decide whether the evidence pack shows the section ADDRESSES this aspect with SPECIFIC content: "
            "expected scientific, economic or technological, and societal impacts stated as effects of this "
            "project, with target groups, and with an indication of magnitude and importance, quantified where "
            "possible. Impacts stated for the field in general, or links too tenuous to be the project's own "
            "contribution, must not pass. Judge specificity and addressal."
        ),
        "evaluation_steps": [
            "List the spans stating expected scientific, economic/technological and societal impacts.",
            "Check each impact is the project's own: a named result, a target group, and a pathway from result to impact.",
            "Check magnitude and importance are indicated, with quantified estimates where the text offers them.",
            _SUBSTANTIATION_STEP,
            _CLOSING_STEP,
        ],
        "selection_terms": [
            "impact", "impacts", "scientific impact", "economic impact", "technological impact", "societal impact",
            "pathway", "pathways", "outcome", "outcomes", "magnitude", "importance", "benefit", "benefits",
            "target group", "beneficiaries", "society", "policy", "market", "industry",
        ],
        "anchor_sub_section_ids": ["2.4"],
    },
    {
        "expectation_key": "impl-workplan",
        "rubric": (
            "Decide whether the evidence pack shows the section ADDRESSES this aspect with SPECIFIC content: "
            "work packages with objectives, tasks, lead and participating organisations and the doctoral "
            "candidates involved; deliverables and milestones with due months and means of verification; "
            "dependencies between work packages; and a risk assessment with likelihood, severity and mitigation. "
            "A work plan with no timing, no dependencies or no risks must not pass. Judge specificity and addressal."
        ),
        "evaluation_steps": [
            "List the spans and table rows describing work packages, tasks, deliverables, milestones and risks.",
            "Check the work plan is concrete: start and end months, leads, DCs per task, due dates and means of verification.",
            "Check inter-work-package dependencies and the effort per work package are described, and the risk table carries mitigation per risk.",
            _SUBSTANTIATION_STEP,
            _CLOSING_STEP,
        ],
        "selection_terms": [
            "work package", "work packages", "WP", "task", "tasks", "deliverable", "deliverables", "milestone",
            "milestones", "risk", "risks", "mitigation", "likelihood", "severity", "timeline", "Gantt", "month",
            "months", "dependency", "dependencies", "effort", "lead participant", "lead beneficiary",
        ],
        "anchor_sub_section_ids": ["3.1"],
    },
    {
        "expectation_key": "impl-participants",
        "rubric": (
            "Decide whether the evidence pack shows the section ADDRESSES this aspect with SPECIFIC content: "
            "each participant's quality, capacity and role in light of its tasks, its infrastructure and hosting "
            "arrangements, the consortium's complementarity, the role of associated partners, and the expertise "
            "the consortium brings together as a whole. Reputation language with no named facility, role or "
            "task must not pass. Judge specificity and addressal."
        ),
        "evaluation_steps": [
            "List the spans describing each participating organisation's capacity, infrastructure, role and hosting arrangements, including the participating-organisation tables.",
            "Check each role is tied to tasks in the work plan and each hosting arrangement is concrete.",
            "Check the consortium's complementarity and the associated partners' contributions are explained, and any non-associated third-country funding is justified.",
            _SUBSTANTIATION_STEP,
            _CLOSING_STEP,
        ],
        "selection_terms": [
            "participant", "participants", "participating organisation", "participating organisations",
            "beneficiary", "beneficiaries", "associated partner", "associated partners", "consortium",
            "complementarity", "complementary", "expertise", "capacity", "infrastructure", "facilities",
            "equipment", "hosting", "hosting arrangements", "host", "role", "roles", "laboratory", "laboratories",
            "non-academic", "third country",
        ],
        "anchor_sub_section_ids": ["3.2"],
    },
)


def render_rubrics(repo_root: Path, mapping_sha256: str) -> dict[str, Any]:
    rows = {r["id"]: r for r in dn_aspect_rows(repo_root)}
    rubrics = []
    for authored in _RUBRICS:
        key = authored["expectation_key"]
        criterion_id = CRITERION_OF[key]
        rubrics.append(
            {
                "expectation_key": key,
                "criterion_id": criterion_id,
                "expectation_text": rows[key]["text"],
                "rubric": authored["rubric"],
                "evaluation_steps": list(authored["evaluation_steps"]),
                "pass_threshold": 0.6,
                "selection_terms": list(authored["selection_terms"]),
                "anchor_sub_section_ids": list(authored["anchor_sub_section_ids"]),
            }
        )
    return {
        "rubric_set_id": RUBRIC_SET_ID,
        "version": RUBRIC_SET_VERSION,
        "scorecard_id": SCORECARD_ID,
        "scorecard_version": EVALUATION_FORM_VERSION,
        "framing": (
            "Specificity-based (spec decision 14): each rubric asks whether the section ADDRESSES its aspect "
            "with specific, verifiable content, never whether the prose is good. Every rubric keeps a "
            "substantiation step; where the pack carries no claim ledger the cell reports grounding "
            "UNASSESSABLE, never failed and never passed, so a sanitisation artifact is not penalised and "
            "the instrument stays whole for the authoritative evaluation. Expectation texts are the verbatim "
            "scorecard aspect texts (HE MSCA Evaluation Form V2.2, pp. 4-6); expectation_key equals the "
            "scorecard aspect id; anchors are the AF V6.0 Part B1 sub-sections 1.1-1.4, 2.1-2.4, 3.1-3.2. "
            "Part B2 sub-sections 4-8 carry no anchor and compete on selection terms (spec §4.2). Rubric "
            "prose, steps, selection terms and thresholds are authored and carry Assumed status. The "
            "two-value cell contract (addressal, grounding) is PE-04's."
        ),
        "criterion_appendix_mapping": {
            "path": MAPPING_REL,
            "sha256": mapping_sha256,
            "rule": "The mapping is versioned with this rubric set: a change to it changes this pin and the rubric-set version, never the scoring-time assembly.",
        },
        "rubrics": rubrics,
    }


# --------------------------------------------------------------------------- #
# Rendering: the criterion appendix mapping
# --------------------------------------------------------------------------- #


def _af_quote(repo_root: Path, page: int, quote: str) -> dict[str, Any]:
    text = strip_template_tags(read_page_text(repo_root / APPLICATION_FORM_V6_REL, page))
    if quote not in text:
        raise AuthoringError(f"AF V6.0 p. {page} does not carry {quote!r}")
    return {"source_path": APPLICATION_FORM_V6_REL, "page": page, "quote": quote}


def render_mapping(repo_root: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = [
        {
            "criterion_id": "excellence",
            "aspect_id": "exc-obj",
            "table": "Table 3.1 a — Description of Work Packages",
            "candidate_sub_section": "3.1",
            "rows": "all work-package rows",
            "status": "Confirmed",
            "sources": [
                _af_quote(repo_root, 11, "The action should be divided in Work Packages and described in the Table 3.1a under the Implementation section."),
            ],
        },
        {
            "criterion_id": "excellence",
            "aspect_id": "exc-obj",
            "table": "Table 3.1 d — DC Table",
            "candidate_sub_section": "3.1",
            "rows": "every DC row: planned start, duration, secondment months, non-academic months",
            "status": "Inferred",
            "inference": "§1.1 requires each DC project's planned secondments with purpose, timing, duration, host and sector; Table 3.1 d is where the durations are tabulated.",
            "sources": [
                _af_quote(repo_root, 11, "Describe each DC’s individual research project, including for each a title, objectives, expected results, and planned secondments (purpose, timing, duration, host, sector)."),
                _af_quote(repo_root, 18, "Total duration of secondments (months)"),
            ],
        },
        {
            "criterion_id": "excellence",
            "aspect_id": "exc-supervision",
            "table": "Section 8 — Participating Organisations",
            "candidate_sub_section": "8",
            "rows": "'Role and Commitment of key persons (including supervisors)' per beneficiary",
            "status": "Confirmed",
            "sources": [
                _af_quote(repo_root, 13, "To avoid duplication, the role and scientific profile of the supervisors should only be listed in the \"Participating Organisations\" tables (see section 8 below)."),
            ],
        },
        {
            "criterion_id": "impact",
            "aspect_id": "imp-dissemination",
            "table": "Table 3.1 a — Description of Work Packages",
            "candidate_sub_section": "3.1",
            "rows": "the work-package rows whose tasks carry dissemination, exploitation or communication",
            "status": "Confirmed",
            "sources": [
                _af_quote(repo_root, 15, "Concrete plans for sections 2.3 must be included in the corresponding table 3.1 a Description of Work Packages."),
                _af_quote(repo_root, 29, "Concrete plans for sections 2.3 must be included in the corresponding implementation tables."),
            ],
        },
        {
            "criterion_id": "impact",
            "aspect_id": "imp-dissemination",
            "table": "Table 3.1 b — Deliverables List",
            "candidate_sub_section": "3.1",
            "rows": "'Management, Training, Recruitment and Dissemination Deliverables' rows, type PDE",
            "status": "Inferred",
            "inference": "The template says 'implementation tables' in the plural and Table 3.1 b types a deliverable PDE for dissemination and/or exploitation of results.",
            "sources": [
                _af_quote(repo_root, 29, "Concrete plans for sections 2.3 must be included in the corresponding implementation tables."),
                _af_quote(repo_root, 17, "PDE = dissemination and/or exploitation of results"),
            ],
        },
        {
            "criterion_id": "impact",
            "aspect_id": "imp-structuring",
            "table": "Table 3.1 d — DC Table",
            "candidate_sub_section": "3.1",
            "rows": "every DC row: secondment months and 'Total duration in non-academic sector (months)'",
            "status": "Inferred",
            "inference": "§2.1 a) names exposure of the DCs to the non-academic sector through secondments; the DC table's non-academic column measures it.",
            "sources": [
                _af_quote(repo_root, 14, "meaningful exposure of Doctoral Candidates to the non-academic sector through secondments"),
                _af_quote(repo_root, 18, "Total duration in non- academic sector (months)"),
            ],
        },
        {
            "criterion_id": "implementation",
            "aspect_id": "impl-participants",
            "table": "Section 8 — Participating Organisations",
            "candidate_sub_section": "8",
            "rows": "all beneficiary and associated-partner entries",
            "status": "Confirmed",
            "sources": [
                _af_quote(repo_root, 19, "Appropriateness of the infrastructure and capacity of each participating organisation, as outlined in Section 8 (Participating Organisations), in light of the tasks allocated to them in the action;"),
                _af_quote(repo_root, 19, "Role of associated partners to the programme (please see also section 8)."),
            ],
        },
    ]
    return {
        "mapping_id": "msca_dn_criterion_appendix_mapping",
        "rubric_set_id": RUBRIC_SET_ID,
        "rubric_set_version": RUBRIC_SET_VERSION,
        "scorecard_id": SCORECARD_ID,
        "purpose": (
            "Which table rows each criterion receives beyond its own section at the criterion-grading "
            "stage (spec PE-02, PE-04). Versioned with the rubric set and never assembled at scoring time, "
            "because a silent change to it changes scores. Candidate sub-section ids follow the page map of "
            "spec §4.1: Tables 3.1 a-e sit in sub-section 3.1, Participating Organisations in sub-section 8."
        ),
        "status_rule": "Confirmed rows rest on an explicit cross-reference in the AF V6.0 text, quoted; Inferred rows state the inference chain (CLAUDE.md §12.2).",
        "own_section_rule": "A criterion always receives its own sub-sections' tables; those are not listed here.",
        "never_received": ["Part B2 section 11 (RAISE DN): a different call's section."],
        "rows": rows,
    }


# --------------------------------------------------------------------------- #
# Rendering: the profile and the registry
# --------------------------------------------------------------------------- #


def derive_target_call(repo_root: Path) -> dict[str, Any]:
    """The 2026 DN call's identifier and deadline from the Tier 2B extract."""
    data = json.loads((repo_root / WORK_PROGRAMME_REL).read_text(encoding="utf-8-sig"))
    calls = [
        call
        for destination in data.get("destinations", [])
        for call in destination.get("calls", [])
        if call.get("call_identifier") == TARGET_CALL_ID
    ]
    if len(calls) != 1:
        raise AuthoringError(f"{WORK_PROGRAMME_REL} carries {len(calls)} calls named {TARGET_CALL_ID}, expected one")
    deadline = str(calls[0].get("deadline", ""))
    if not re.match(r"\d{4}-\d{2}-\d{2}T", deadline):
        raise AuthoringError(f"{TARGET_CALL_ID}: deadline not derivable from {WORK_PROGRAMME_REL}")
    return {
        "call_id": TARGET_CALL_ID,
        "topic_id": str(calls[0].get("topic_identifier") or calls[0].get("topic_id") or ""),
        "deadline": deadline[:10],
        "source_path": WORK_PROGRAMME_REL,
        "declared_status": "Confirmed",
    }


def render_profile(repo_root: Path) -> dict[str, Any]:
    target = derive_target_call(repo_root)
    return {
        "profile_id": PROFILE_ID,
        "label": "MSCA Doctoral Networks — 2026 resubmission-readiness pre-evaluation profile",
        "instrument": {
            "registry_instrument_type": REGISTRY_INSTRUMENT_TYPE,
            "name": "MSCA Doctoral Networks",
            "form_name": "HE MSCA Evaluation Form",
        },
        "option_tag_grammar": {
            "applicable_variant": APPLICABLE_VARIANT,
            "known_variants": list(KNOWN_VARIANTS),
            "variant_prefix": "MSCA ",
            "all_except_prefix": "all MSCA except ",
        },
        "criteria": [
            {"id": "excellence", "registry_criterion_id": "Excellence", "section_ids": ["excellence_section"]},
            {"id": "impact", "registry_criterion_id": "Impact", "section_ids": ["impact_section"]},
            {"id": "implementation", "registry_criterion_id": "Implementation", "section_ids": ["implementation_section"]},
        ],
        "registry_path": REGISTRY_REL,
        "scorecard": {"path": SCORECARD_REL, "scorecard_id": SCORECARD_ID, "version": EVALUATION_FORM_VERSION},
        "rubric_set": {"path": RUBRICS_REL, "rubric_set_id": RUBRIC_SET_ID, "version": RUBRIC_SET_VERSION},
        "criterion_appendix_mapping": {"path": MAPPING_REL},
        "structural_authority": {
            "path": APPLICATION_FORM_V6_REL,
            "version": APPLICATION_FORM_V6_VERSION,
            "version_date": APPLICATION_FORM_V6_DATE,
            "v5_equivalence_recorded_in": f"{SCORECARD_REL} provenance.v5_equivalence",
        },
        "target_call": {
            **target,
            "label": "resubmission readiness",
            "owner_note": (
                "The baseline's target call is owned by this profile, the run label and the report "
                "(spec PE-01). It never enters the ESR intake, whose call_id is the historical 2025 call."
            ),
        },
        "implementation_mode": "standard Doctoral Network (not DN-ID, not DN-JD)",
    }


def render_registry(repo_root: Path) -> bytes:
    """The Tier 2A registry with the MSCA-DN instrument added or replaced.

    Re-serialised with the file's own options (indent 2, raw UTF-8, the
    newline style found on disk, no final newline) so the other instruments'
    bytes do not move.
    """
    path = repo_root / REGISTRY_REL
    raw = path.read_bytes()
    newline = "\r\n" if b"\r\n" in raw else "\n"
    data = json.loads(raw.decode("utf-8-sig"))
    instruments = data["instruments"]
    rows = dn_aspect_rows(repo_root)
    entry = {
        "instrument_type": REGISTRY_INSTRUMENT_TYPE,
        "criteria": [
            {
                "criterion_id": reg,
                "criterion_name": CRITERION_NAMES[cid],
                "threshold_score": 3,
                "evaluator_expectations": [r["text"] for r in rows if CRITERION_OF[r["id"]] == cid],
            }
            for cid, _n, _s, reg in CRITERIA
        ],
    }
    kept = [i for i in instruments if i.get("instrument_type") != REGISTRY_INSTRUMENT_TYPE]
    data["instruments"] = kept + [entry]
    return json.dumps(data, indent=2, ensure_ascii=False).replace("\n", newline).encode("utf-8")


# --------------------------------------------------------------------------- #
# Writing and checking
# --------------------------------------------------------------------------- #


def render_all(repo_root: Path) -> dict[str, bytes]:
    """Every file PE-02 authors, as the bytes it should hold on disk."""
    mapping = canonical_json_bytes(render_mapping(repo_root))
    return {
        SCORECARD_REL: canonical_json_bytes(render_scorecard(repo_root)),
        MAPPING_REL: mapping,
        RUBRICS_REL: canonical_json_bytes(render_rubrics(repo_root, _sha256(mapping))),
        PROFILE_REL: canonical_json_bytes(render_profile(repo_root)),
        REGISTRY_REL: render_registry(repo_root),
    }


def check(repo_root: Path) -> list[str]:
    """Relative paths whose bytes differ from the rendering, or are absent."""
    return [
        rel
        for rel, data in render_all(repo_root).items()
        if not (repo_root / rel).is_file() or (repo_root / rel).read_bytes() != data
    ]


def author(repo_root: Path) -> list[str]:
    """Write every file; return the relative paths that changed."""
    changed: list[str] = []
    for rel, data in render_all(repo_root).items():
        target = repo_root / rel
        if target.is_file() and target.read_bytes() == data:
            continue
        atomic_write_text(data.decode("utf-8"), target)  # newlines written verbatim
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
    except AuthoringError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
