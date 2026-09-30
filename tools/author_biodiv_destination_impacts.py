"""Add the destination's expected impacts to the BIODIV-01 curated call extract.

Recorded as F3 and F4 of
``docs/tier4_orchestration_state/decision_log/demo-runner-phases-1-6_2026-09-30.json``:
this topic's expected impacts never entered Tier 2B. A destination record in the
grouped work programme JSON holds only a title and its calls, so the Step 0 slice
carries no impact text and structurally cannot. The curated extract had no
``expected_impacts`` field either. Phase 1 reads three inputs — the slice, this
extract and ``selected_call.json`` — and is forbidden from reading
``work_programmes/``, so it had nothing to extract from and paraphrased the
topic's own Expected Outcome and Scope text instead, marking four of five entries
Confirmed.

This tool closes that gap at the tier the gap is in. The extract is the only one
of Phase 1's three inputs that can carry the destination's impacts, so the six go
here, each with the page and character range it was sliced from.

**Nothing is typed.** Every quote is sliced out of the Part 9 PDF, read through
``runner.source_index.read_page_text`` — the same reader whose output the Tier 3
transcription replays against. The bullet structure is located by searching the
page text: the ``Expected impact:`` preamble, the bullet characters, the footnote
block that ends page 47's list, the page-48 header, and the topic heading that
ends the list. No offset is written by hand. The fourth impact straddles the page
break and is recorded as two spans, because that is what the document does.

Each derived quote is then cross-checked against the Tier 3 source-materials
record, which transcribed both pages byte for byte and declares them Confirmed.
A mismatch aborts: two independent derivations of the same sentence must agree,
and the tool has no licence to pick one.

Run it from the repository root::

    py -3.10 -m tools.author_biodiv_destination_impacts            # write
    py -3.10 -m tools.author_biodiv_destination_impacts --check    # exit 1 if it differs

Constitutional standing: an authoring tool, not a runtime component. It writes one
Tier 2B curated artifact from the Tier 2B source document it already cites,
evaluates no gate and invokes no Claude. It does not touch Tier 2B ``extracted/``:
§7 gives that to Phase 1, and Phase 1 must be rerun for this to reach it.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from runner.atomic_write import atomic_write_json, canonical_json_bytes  # noqa: E402
from runner.source_index import read_page_text  # noqa: E402

TOPIC = "HORIZON-CL6-2027-01-BIODIV-01"

EXTRACT_REL = f"docs/tier2b_topic_and_call_sources/call_extracts/{TOPIC}.json"
SOURCES_REL = "docs/tier3_project_instantiation/source_materials/sources.json"
PDF_REL = (
    "docs/tier2b_topic_and_call_sources/work_programmes/cluster_climate/"
    "wp-9-food-bioeconomy-natural-resources-agriculture-and-environment_"
    "horizon-2026-2027_en.pdf"
)
PDF_NAME = PDF_REL.rsplit("/", 1)[-1]

#: The destination narrative, and where its expected-impact list begins and ends.
FIRST_PAGE = 47
SECOND_PAGE = 48

BULLET = "•"
PREAMBLE_OPENS = "Expected impact:"
PREAMBLE_CLOSES = "following expected impacts:"
#: The footnote block that ends page 47's running text.
FOOTNOTES_OPEN = re.compile(r"\s7 ?9 Kunming|\s79 Kunming")
#: The page-48 running header, and the topic heading that ends the impact list.
PAGE_48_HEADER = re.compile(
    r"^Horizon Europe - Work Programme 2026-2027 .*? Part 9 - Page 48 of 360\s"
)
TOPIC_HEADING = re.compile(r"\s2026 Consolidating biodiversity knowledge")

#: Where the new fields go, so the extract keeps its logical order.
INSERT_AFTER = "expected_outcomes_binding_source_span"

#: Sentences this tool adds to the extract's own prose fields. Each is appended
#: only when absent, so a second run over an unchanged document rewrites the same
#: bytes instead of stacking another copy.
PAGES_NOTE = (
    "Pages 47 and 48 carry the destination narrative: its expected-impact "
    "statement, the pathway phrase every proposal under the destination must "
    "contribute to, and the six expected impacts. The fourth straddles the page "
    "break."
)
AUTHORED_BY = (
    "expected_impacts added by tools/author_biodiv_destination_impacts.py for F3 "
    "of the ticket 'Runner Phases 1 to 6 on the demo'"
)
EXTRACT_NOTE = (
    "The destination's expected impacts are sliced from pages 47 and 48 by "
    "tools/author_biodiv_destination_impacts.py and cross-checked against the "
    "Tier 3 transcription of those pages. Phase 1 must be rerun for them to reach "
    "Tier 2B extracted/."
)


class AuthoringError(RuntimeError):
    """A structure this derivation depends on is not in the document."""


# ── derivation from the PDF ───────────────────────────────────────────────────


def _append_once(existing: str, sentence: str, joiner: str = " ") -> str:
    """*sentence* appended to *existing*, or *existing* if it is already there."""
    if sentence in existing:
        return existing
    return existing.rstrip() + joiner + sentence


def _find(pattern: re.Pattern[str], text: str, what: str) -> re.Match[str]:
    match = pattern.search(text)
    if match is None:
        raise AuthoringError(f"{what} not found in the page text.")
    return match


def _span(page: int, text: str, start: int, end: int) -> dict[str, Any]:
    """One source span: the slice, and where it came from.

    ``quote`` is the slice itself, so the span cannot disagree with the page it
    names. The offsets travel with it so a reader can re-cut it.
    """
    quote = text[start:end]
    if quote != quote.strip():
        raise AuthoringError(
            f"span {page}#{start}-{end} is not tightly bounded: {quote[:60]!r}"
        )
    return {
        "quote": quote,
        "source_document": PDF_NAME,
        "source_page": page,
        "source_page_characters": f"{start}-{end}",
    }


def _bullets(text: str, start: int, end: int) -> list[int]:
    """Bullet positions strictly inside ``[start, end)``."""
    return [
        index
        for index, char in enumerate(text)
        if char == BULLET and start <= index < end
    ]


def _cut_bullets(page: int, text: str, start: int, end: int) -> list[dict[str, Any]]:
    """The bulleted items between *start* and *end*, as source spans.

    An item's text begins one space past its bullet and excludes the punctuation
    that separates it from what follows: the ``"; "`` before the next bullet, or
    the full stop that ends the list. The last item runs to *end*.
    """
    bullets = _bullets(text, start, end)
    items: list[dict[str, Any]] = []
    for position, bullet in enumerate(bullets):
        opens = bullet + len(BULLET) + 1
        closes = bullets[position + 1] - 2 if position + 1 < len(bullets) else end
        items.append(_span(page, text, opens, _drop_terminator(text, opens, closes)))
    return items


def _drop_terminator(text: str, opens: int, closes: int) -> int:
    """*closes*, moved back over one trailing ``;`` or ``.`` and any whitespace.

    Applied so the item that ends the list is cut on the same convention as the
    items before it, which lose their ``"; "`` to the gap before the next bullet.
    """
    while closes > opens and text[closes - 1].isspace():
        closes -= 1
    if closes > opens and text[closes - 1] in ";.":
        closes -= 1
    while closes > opens and text[closes - 1].isspace():
        closes -= 1
    return closes


def derive_destination_impacts(repo_root: Path) -> dict[str, Any]:
    """The destination's expected impacts, cut out of the Part 9 PDF."""
    pdf = repo_root / PDF_REL
    first = read_page_text(pdf, FIRST_PAGE)
    second = read_page_text(pdf, SECOND_PAGE)

    opens = _find(re.compile(re.escape(PREAMBLE_OPENS)), first, PREAMBLE_OPENS)
    closes = _find(re.compile(re.escape(PREAMBLE_CLOSES)), first, PREAMBLE_CLOSES)
    preamble_end = closes.end()

    # The list on page 47 runs from the preamble to the footnote block.
    footnotes = _find(FOOTNOTES_OPEN, first[preamble_end:], "the page-47 footnote block")
    first_list_end = preamble_end + footnotes.start()
    items_first = _cut_bullets(FIRST_PAGE, first, preamble_end, first_list_end)
    if len(items_first) < 2:
        raise AuthoringError(
            f"page {FIRST_PAGE} carries {len(items_first)} bullet(s) between the "
            "expected-impact preamble and the footnotes; the list cannot be read."
        )

    # Page 48 opens mid-sentence: the last impact of page 47 straddles the break.
    # The list ends at the topic heading — bullets after it belong to the topic,
    # not to the destination, and must not be read as impacts.
    header = _find(PAGE_48_HEADER, second, "the page-48 running header")
    heading = _find(TOPIC_HEADING, second, "the topic heading that ends the list")
    second_list_end = len(second[: heading.start()].rstrip())
    items_second = _cut_bullets(SECOND_PAGE, second, header.end(), second_list_end)
    if not items_second:
        raise AuthoringError(
            f"page {SECOND_PAGE} carries no bullet between its header and the "
            "topic heading; the tail of the list cannot be read."
        )

    first_bullet_on_second = _bullets(second, header.end(), second_list_end)[0]
    continuation = _span(SECOND_PAGE, second, header.end(), first_bullet_on_second - 2)

    # The last impact on page 47 continues onto page 48.
    straddling = items_first[-1]
    impacts: list[dict[str, Any]] = []
    for index, item in enumerate(items_first[:-1], start=1):
        impacts.append({"impact_id": f"DEST-IMPACT-{index}", "spans": [item]})
    impacts.append(
        {
            "impact_id": f"DEST-IMPACT-{len(items_first)}",
            "spans": [straddling, continuation],
        }
    )
    for offset, item in enumerate(items_second, start=len(items_first) + 1):
        impacts.append({"impact_id": f"DEST-IMPACT-{offset}", "spans": [item]})

    for impact in impacts:
        impact["statement"] = " ".join(span["quote"] for span in impact["spans"])
        impact["straddles_page_break"] = len(impact["spans"]) > 1

    pathway = re.search(r"“(.+?)”", first[opens.start() : preamble_end])
    if pathway is None:
        raise AuthoringError("the destination's pathway phrase is not quoted on page 47.")
    pathway_start = opens.start() + pathway.start(1)

    return {
        "impacts": impacts,
        "binding_span": _span(FIRST_PAGE, first, opens.start(), preamble_end),
        "pathway_span": _span(
            FIRST_PAGE, first, pathway_start, pathway_start + len(pathway.group(1))
        ),
    }


def cross_check_against_tier3(repo_root: Path, derived: dict[str, Any]) -> list[str]:
    """Confirm each derived quote against the Tier 3 transcription of the pages.

    Returns the Tier 3 span ids that matched. The transcription is an independent
    read of the same two pages, declared Confirmed. Two derivations of one
    sentence must agree; a disagreement is for a human, not for this tool.
    """
    sources = json.loads((repo_root / SOURCES_REL).read_text(encoding="utf-8"))
    transcribed: dict[str, str] = {}
    for record in sources["sources"]:
        for span in record.get("spans") or []:
            transcribed[span["span_id"]] = span["quote"]
    if not transcribed:
        raise AuthoringError(f"{SOURCES_REL} carries no transcribed spans to check against.")

    matched: list[str] = []
    unmatched: list[str] = []
    for impact in derived["impacts"]:
        for span in impact["spans"]:
            quote = span["quote"]
            hits = [sid for sid, text in transcribed.items() if text == quote]
            if hits:
                matched.extend(hits)
            else:
                unmatched.append(f"{impact['impact_id']} {quote[:70]!r}")
    if unmatched:
        raise AuthoringError(
            "these derived quotes match no Tier 3 transcribed span, so the two "
            "reads of the page disagree:\n  " + "\n  ".join(unmatched)
        )

    # Neither side may hold an impact the other does not. A count that agrees
    # with the Confirmed Tier 3 record rules out both a stray bullet read as an
    # impact and an impact missed at a boundary.
    impacts_path = repo_root / "docs/tier3_project_instantiation/architecture_inputs/impacts.json"
    recorded = json.loads(impacts_path.read_text(encoding="utf-8"))
    expected = len(recorded["destination_expected_impacts"]["impacts"])
    if len(derived["impacts"]) != expected:
        raise AuthoringError(
            f"derived {len(derived['impacts'])} destination expected impacts, but "
            f"the Tier 3 record holds {expected}. One read has a boundary wrong."
        )
    return sorted(matched)


# ── the extract ──────────────────────────────────────────────────────────────


def build_extract(repo_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """The extract with the destination's expected impacts added."""
    extract = json.loads((repo_root / EXTRACT_REL).read_text(encoding="utf-8"))
    derived = derive_destination_impacts(repo_root)
    cross_check_against_tier3(repo_root, derived)

    additions = {
        "expected_impacts_level": "destination",
        "expected_impacts_level_note": (
            "These are the destination's expected impacts, not the topic's. The "
            "topic entry on pages 73 to 76 states expected outcomes and scope and "
            "no expected impact of its own. Recorded here because the destination "
            "narrative is absent from the grouped work programme JSON, so the Step "
            "0 slice cannot carry it and Phase 1 has no other declared input that "
            "can."
        ),
        "expected_impacts": [
            impact["statement"] for impact in derived["impacts"]
        ],
        "expected_impacts_binding": "one_or_more",
        "expected_impacts_binding_source_span": derived["binding_span"],
        "expected_impacts_pathway_source_span": derived["pathway_span"],
        "expected_impacts_source_spans": [
            {
                "impact_id": impact["impact_id"],
                "straddles_page_break": impact["straddles_page_break"],
                "spans": impact["spans"],
            }
            for impact in derived["impacts"]
        ],
    }

    rebuilt: dict[str, Any] = {}
    for key, value in extract.items():
        rebuilt[key] = value
        if key == INSERT_AFTER:
            rebuilt.update(additions)
    if INSERT_AFTER not in extract:
        raise AuthoringError(f"{EXTRACT_REL} has no {INSERT_AFTER!r} to insert after.")

    supporting = rebuilt["source_pages_supporting"]
    if "47-48" not in supporting:
        rebuilt["source_pages_supporting"] = f"{supporting}, 47-48"
    rebuilt["source_pages_note"] = _append_once(
        rebuilt["source_pages_note"], PAGES_NOTE
    )

    status = dict(rebuilt["field_status"])
    for field in (
        "expected_impacts",
        "expected_impacts_level",
        "expected_impacts_binding",
    ):
        status[field] = "Confirmed"
    rebuilt["field_status"] = status

    rebuilt["authored_by"] = _append_once(rebuilt["authored_by"], AUTHORED_BY, "; ")
    rebuilt["note"] = _append_once(rebuilt["note"], EXTRACT_NOTE)
    return rebuilt, derived


# ── entry point ──────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Add the destination's expected impacts to the BIODIV-01 curated call "
            "extract, sliced from the Part 9 PDF."
        )
    )
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--check",
        action="store_true",
        help="Write nothing; exit 1 if the extract on disk would change.",
    )
    args = parser.parse_args(argv)

    repo_root = args.repo_root.resolve()
    try:
        rebuilt, derived = build_extract(repo_root)
    except AuthoringError as exc:
        print(f"[BLOCKED] {exc}", file=sys.stderr)
        return 2

    target = repo_root / EXTRACT_REL
    expected = canonical_json_bytes(rebuilt)

    if args.check:
        if target.read_bytes() != expected:
            print(f"[DIFFERS] {EXTRACT_REL} would change.", file=sys.stderr)
            return 1
        print(f"[OK] {EXTRACT_REL} is unchanged.")
        return 0

    atomic_write_json(rebuilt, target)
    print(f"Wrote {EXTRACT_REL}")
    print(f"  {len(derived['impacts'])} destination expected impacts, sliced from the PDF")
    for impact in derived["impacts"]:
        pages = ", ".join(
            f"p.{span['source_page']}#{span['source_page_characters']}"
            for span in impact["spans"]
        )
        print(f"    {impact['impact_id']}  {pages}")
        print(f"      {impact['statement'][:96]}")
    print(f"  binding: {rebuilt['expected_impacts_binding']}")
    print(f"  source_pages_supporting: {rebuilt['source_pages_supporting']}")
    print("  every quote matched a Tier 3 transcribed span")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
