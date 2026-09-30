"""Author the instance-two Tier 3 source index, deterministically.

Writes ``docs/tier3_project_instantiation/source_materials/sources.json`` for the
demo ticket "Source materials and the sources index". Nothing in the output is
typed by hand except the citations, the uses and the name partition: every page
transcription and every byte offset is derived here and re-checked independently
by :mod:`runner.source_index`.

Two derivations do the work.

**Transcription.** Each cited page of the stored work programme PDF is read
through :func:`runner.source_index.read_page_text`, the single implementation of
the declared method. The verifier re-runs the same function and compares byte for
byte, so a hand edit to the stored text fails rather than passes.

**Spans.** Two span sets are merged. The first comes from the Tier 2B call
extract: every quote it recorded for a cited page is located in the transcribed
text, and its offsets are stored. The second comes from the concept's own claims:
each claim's ``call_phrase`` is located the same way. A phrase that does not
occur verbatim is a hard error here, not a warning — the whole point is that a
span the source does not contain never reaches the index.

Run it from the repository root::

    py -3.10 -m tools.author_demo_sources            # write
    py -3.10 -m tools.author_demo_sources --check    # exit 1 if the file would change

Constitutional standing: an authoring tool, not a runtime component. It writes one
Tier 3 artifact, evaluates no gate and invokes no Claude.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional, Sequence

from runner.paths import find_repo_root
from runner.source_index import (
    PAGE_TEXT_METHOD,
    PROJECT_SUMMARY_REL,
    SOURCE_INDEX_RECORD_TYPE,
    SOURCES_REL,
    normalise_whitespace,
    read_page_text,
    span_id,
)

TOPIC = "HORIZON-CL6-2027-01-BIODIV-01"

CALL_EXTRACT_REL = (
    "docs/tier2b_topic_and_call_sources/call_extracts/"
    "HORIZON-CL6-2027-01-BIODIV-01.json"
)
PART9_REL = (
    "docs/tier2b_topic_and_call_sources/work_programmes/cluster_climate/"
    "wp-9-food-bioeconomy-natural-resources-agriculture-and-environment_horizon-2026-2027_en.pdf"
)
PART9_DOCUMENT_ID = "tier2b.wp9.horizon-2026-2027"

#: The printed pages the concept relies on, and what each one carries. Only pages
#: the Tier 2B extract or a concept claim actually cites are transcribed: a page
#: nothing cites would be an unused copy of a Tier 2B document sitting in Tier 3.
PAGES: dict[int, str] = {
    34: "The call conditions table: opening date, deadline and deadline model.",
    35: "The call conditions table: indicative budget and the number of projects.",
    73: "The topic header: type of action, budget regime, and the two topic-level "
        "eligibility exceptions (the Joint Research Centre place, and the "
        "Copernicus or Galileo/EGNOS condition).",
    74: "The topic's expected outcomes, and the binding force of the outcome list.",
    75: "The topic scope: the five scope requirements, the ecosystem realms, and "
        "most of the cross-cutting requirements.",
    76: "The remainder of the scope: research-infrastructure services, the "
        "FuturEO coordination duty and the tail of the monitoring-scheme "
        "sentence that straddles the page break.",
    47: "The destination narrative for Biodiversity and ecosystem services: the "
        "international commitments the destination serves, and the first four of "
        "its six expected impacts.",
    48: "The tail of the fourth expected impact, which straddles the page break, "
        "and the destination's last two.",
}

#: What the concept takes from each page, for the page source's ``relied_on_for``.
PAGE_USES: dict[int, str] = {
    34: "The submission deadline and the deadline model the concept states in its "
        "header.",
    35: "The per-project EU contribution the duration decision weighs.",
    73: "The action type, and the two eligibility conditions the consortium design "
        "answers: the open Joint Research Centre place, and the obligation to use "
        "Copernicus or Galileo/EGNOS once the project uses satellite data.",
    74: "The three expected outcomes the concept's chain is built to answer, "
        "including the omics layer and the training-and-validation outcome.",
    75: "The scope requirements, the three ecosystem realms, and the cooperation, "
        "monitoring-data, typology-interoperability, data-infrastructure and "
        "policy-reporting duties the concept assigns to named partners.",
    76: "The FuturEO coordination duty, and the permissive research-infrastructure "
        "clause.",
    47: "The destination's expected impact statement and its first four bullets, "
        "which the impact pathways in architecture_inputs/impacts.json are mapped "
        "against.",
    48: "The fourth bullet's valuation clause, and the last two expected impacts, "
        "including the one about farmers and land managers that the agricultural "
        "uptake pathway answers.",
}

#: Spans a Tier 3 seed relies on that neither the Tier 2B extract nor a concept
#: claim cites, as ``{page: ((quote, requirement_ref), ...)}``.
#:
#: The call extract carries the topic's expected *outcomes* and no expected
#: *impacts*: those sit in the destination narrative, two pages this index did
#: not transcribe while only the concept relied on it. ``impacts.json`` maps a
#: project pathway to each of them, so each bullet needs a span, and inventing
#: the bullet text in Tier 3 would be exactly the fabrication §13.2 forbids.
#:
#: The destination sets **six** expected impacts. The fourth straddles the page
#: break, so it has two spans: ``DEST-IMPACT-4`` on page 47 and its tail on page
#: 48, which carries no bullet marker of its own. Counting that tail as a seventh
#: impact is the mistake ``TestTheDestinationExpectedImpacts`` exists to prevent.
#:
#: Offsets are located the same way every other span is, so a quote that is not
#: in the replayed page text fails the build rather than being written down.
SEED_SPANS: dict[int, tuple[tuple[str, str], ...]] = {
    47: (
        ("Expected impact: Proposals for topics under this destination should set "
         "out a credible pathway contributing to", "DEST-IMPACT"),
        ("putting biodiversity on a path to recovery, and protecting and restoring "
         "ecosystems and their services", "DEST-IMPACT"),
        ("Knowledge on biodiversity status and trends and drivers of biodiversity "
         "loss is improved", "DEST-IMPACT-1"),
        ("Innovations, methods, pathways, models and tools are available and used "
         "to protect healthy and resilient ecosystems and to restore degraded "
         "ones, ensuring the continuous provision of ecosystem services, including "
         "for adaptation and/or mitigation to climate change", "DEST-IMPACT-2"),
        ("The ongoing biodiversity crisis and its consequences, notably on "
         "ecosystem functioning and their services, and the need to monitor, "
         "protect, restore and sustainably use biodiversity are better understood "
         "to better benefit the whole society in an inclusive way", "DEST-IMPACT-3"),
        ("Policymakers and stakeholders, all relevant economic sectors and society "
         "are aware and well informed of relevant challenges and opportunities of "
         "biodiversity protection, restoration and sustainable use, leading to "
         "better implementation of the biodiversity", "DEST-IMPACT-4"),
    ),
    48: (
        ("legislation and better valuation of ecosystem services, leading to "
         "transformative change towards a nature positive economy", "DEST-IMPACT-4"),
        ("Farmers, foresters, land and sea managers, fishers and aquaculture "
         "producers have access to key information, and test and implement "
         "biodiversity-friendly management practices, while safeguarding food and "
         "water security and fostering competitiveness, demonstrating the "
         "long-term sustainability of these sectors", "DEST-IMPACT-5"),
        ("Progress towards international commitments worldwide on biodiversity is "
         "made", "DEST-IMPACT-6"),
    ),
}


# ---------------------------------------------------------------------------
# The external references — authored content, anchored mechanically
# ---------------------------------------------------------------------------

#: One entry per external framework, dataset, policy instrument or paper the
#: concept names. ``names`` are the strings the concept uses, and the anchor is
#: found by searching the transcribed spans for the first of them, so a reference
#: cannot claim a citation the call text does not make.
#:
#: Every ``identifier`` is recorded from prior knowledge and **not** resolved:
#: this workspace has no verified network egress and no copy of any of these
#: documents is stored, so each carries Assumed under CLAUDE.md §10.6 with the
#: basis stated. Confirming them is an operator step.
_KNOWLEDGE_BASIS = (
    "Recorded from the model's prior knowledge of the public identifier and not "
    "resolved: this workspace has no verified network egress and no copy is "
    "stored in the repository. Flagged Assumed under CLAUDE.md §10.6. An "
    "operator confirms it by resolving the identifier."
)

EXTERNALS: tuple[dict[str, Any], ...] = (
    {
        "source_id": "SRC-GBIF",
        "title": "Global Biodiversity Information Facility (GBIF)",
        "names": ["GBIF"],
        "cited_as": "Global Biodiversity Information Facility (GBIF), the international "
                    "open-data infrastructure publishing species occurrence records.",
        "identifier": "https://www.gbif.org",
        "holds": "The GBIF portal, from which occurrence records and the publishing "
                 "standards they follow are obtained.",
        "used_for": "The cooperation duty the scope places on the proposal, and the "
                    "publishing route P10 offers for occurrence data.",
    },
    {
        "source_id": "SRC-OBIS",
        "title": "Ocean Biodiversity Information System (OBIS)",
        "names": ["OBIS"],
        "cited_as": "Ocean Biodiversity Information System (OBIS), the marine "
                    "counterpart to GBIF, hosted under the IOC of UNESCO.",
        "identifier": "https://obis.org",
        "holds": "The OBIS portal, from which marine occurrence records are obtained.",
        "used_for": "The marine limb of the cooperation duty, which P08 answers by "
                    "contributing coastal occurrence data.",
    },
    {
        "source_id": "SRC-LUCAS",
        "title": "LUCAS — Land Use and Coverage Area frame Survey",
        "names": ["LUCAS"],
        "cited_as": "LUCAS (Land Use and Coverage Area frame Survey), the Eurostat "
                    "in-situ survey of land cover and land use, including its "
                    "grassland module.",
        "identifier": "https://ec.europa.eu/eurostat/web/lucas",
        "holds": "The Eurostat LUCAS pages, from which the survey design and the "
                 "released data are obtained.",
        "used_for": "Both duties that name it: cooperation with an existing in-situ "
                    "framework, and ingestion of Commission-steered monitoring data.",
    },
    {
        "source_id": "SRC-EMBAL",
        "title": "EMBAL — European Monitoring of Biodiversity in Agricultural "
                 "Landscapes",
        "names": ["EMBAL"],
        "cited_as": "EMBAL (European Monitoring of Biodiversity in Agricultural "
                    "Landscapes), a Commission-steered field survey of biodiversity "
                    "in farmed landscapes.",
        "identifier": None,
        "holds": "Nothing is stored and no persistent identifier is recorded. The "
                 "only verified text about EMBAL on this branch is the call "
                 "sentence that names it.",
        "used_for": "The monitoring-data ingestion duty, which the concept assigns to "
                    "P03 and P10.",
        "identifier_note": "No public persistent identifier is recorded, because none "
                           "could be verified here. The entry is Unresolved on its "
                           "identifier and resolves through its anchor instead.",
    },
    {
        "source_id": "SRC-EUNIS",
        "title": "EUNIS habitat classification",
        "names": ["EUNIS"],
        "cited_as": "The EUNIS habitat classification, maintained by the European "
                    "Environment Agency.",
        "identifier": "https://eunis.eea.europa.eu",
        "holds": "The EEA's EUNIS pages, from which the habitat classes and their "
                 "definitions are obtained.",
        "used_for": "The interoperability duty: every habitat label the project "
                    "publishes carries a crosswalk to it, which P10 owns.",
    },
    {
        "source_id": "SRC-GET",
        "title": "IUCN Global Ecosystem Typology",
        "names": ["Global Ecosystem Typology"],
        "cited_as": "The IUCN Global Ecosystem Typology, the function-based global "
                    "classification of ecosystems.",
        "identifier": "https://global-ecosystems.org",
        "holds": "The typology's own site, from which the biome and ecosystem "
                 "functional group definitions are obtained.",
        "used_for": "The second half of the interoperability duty, alongside EUNIS.",
    },
    {
        "source_id": "SRC-EOSC",
        "title": "European Open Science Cloud (EOSC)",
        "names": ["EOSC", "European Open Science Cloud"],
        "cited_as": "The European Open Science Cloud (EOSC), the European federation "
                    "of research data services.",
        "identifier": "https://eosc.eu",
        "holds": "The EOSC portal, from which the service catalogue and onboarding "
                 "requirements are obtained.",
        "used_for": "The data-infrastructure linking duty, which P10 and P04 hold.",
    },
    {
        "source_id": "SRC-CDS",
        "title": "European Common Data Spaces",
        "names": ["European Common Data Spaces"],
        "cited_as": "The European Common Data Spaces, the Commission's sectoral data "
                    "space programme, including its agriculture and Green Deal "
                    "strands.",
        "identifier": "https://digital-strategy.ec.europa.eu/en/policies/data-spaces",
        "holds": "The Commission's data spaces policy pages, from which the "
                 "governance and interoperability expectations are obtained.",
        "used_for": "The other half of the data-infrastructure duty the concept "
                    "accepts.",
    },
    {
        "source_id": "SRC-COPERNICUS",
        "title": "Copernicus, the EU Earth observation programme",
        "names": ["Copernicus"],
        "cited_as": "Copernicus, the European Union's Earth observation programme, "
                    "including its Sentinel missions and its data and information "
                    "services.",
        "identifier": "https://www.copernicus.eu",
        "holds": "The Copernicus programme pages, from which mission specifications "
                 "and data access terms are obtained.",
        "used_for": "The eligibility condition on satellite data, and the satellite "
                    "layer of the observation chain that P02 and P12 hold.",
    },
    {
        "source_id": "SRC-GALILEO",
        "title": "Galileo and EGNOS",
        "names": ["Galileo", "EGNOS"],
        "cited_as": "Galileo, the EU global navigation satellite system, and EGNOS, "
                    "its European augmentation service.",
        "identifier": "https://www.euspa.europa.eu",
        "holds": "The EU Agency for the Space Programme pages, from which the "
                 "positioning services and their accuracy are obtained.",
        "used_for": "The positioning limb of the same eligibility condition, which "
                    "bears on how in-situ plots and aerial survey are georeferenced.",
    },
    {
        "source_id": "SRC-FUTUREO",
        "title": "ESA FuturEO programme",
        "names": ["FuturEO"],
        "cited_as": "FuturEO, the European Space Agency's Earth observation research "
                    "programme, whose projects this topic asks selected consortia to "
                    "coordinate with.",
        "identifier": "https://www.esa.int/Applications/Observing_the_Earth",
        "holds": "ESA's Earth observation pages. The programme's own project list is "
                 "not recorded, so which FuturEO projects exist at the deadline is "
                 "not known here.",
        "used_for": "The coordination duty the concept assigns to P02 and P12.",
    },
    {
        "source_id": "SRC-HABITATS-DIR",
        "title": "Habitats Directive 92/43/EEC",
        "names": ["Habitats Directive"],
        "cited_as": "Council Directive 92/43/EEC of 21 May 1992 on the conservation "
                    "of natural habitats and of wild fauna and flora.",
        "identifier": "http://data.europa.eu/eli/dir/1992/43/oj",
        "holds": "The consolidated directive, from which the Article 17 reporting "
                 "obligations and the habitat annexes are obtained.",
        "used_for": "The policy-reporting alignment duty, and the reporting needs "
                    "P11 analyses.",
    },
    {
        "source_id": "SRC-BIRDS-DIR",
        "title": "Birds Directive 2009/147/EC",
        "names": ["Birds Directive"],
        "cited_as": "Directive 2009/147/EC of the European Parliament and of the "
                    "Council of 30 November 2009 on the conservation of wild birds.",
        "identifier": "http://data.europa.eu/eli/dir/2009/147/oj",
        "holds": "The directive, from which the Article 12 reporting obligations are "
                 "obtained.",
        "used_for": "The same policy-reporting duty, for the farmland and wetland "
                    "species the terrestrial and freshwater cases cover.",
    },
    {
        "source_id": "SRC-MSFD",
        "title": "Marine Strategy Framework Directive 2008/56/EC",
        "names": ["Marine Strategy Framework Directive"],
        "cited_as": "Directive 2008/56/EC of the European Parliament and of the "
                    "Council of 17 June 2008 establishing a framework for community "
                    "action in the field of marine environmental policy.",
        "identifier": "http://data.europa.eu/eli/dir/2008/56/oj",
        "holds": "The directive, from which the good-environmental-status descriptors "
                 "and their indicators are obtained.",
        "used_for": "The marine limb of the policy-reporting duty, which P08 answers "
                    "through its indicator work.",
    },
    {
        "source_id": "SRC-NRR",
        "title": "Nature Restoration Regulation (EU) 2024/1991",
        "names": ["EU Nature Restoration Regulation"],
        "cited_as": "Regulation (EU) 2024/1991 of the European Parliament and of the "
                    "Council of 24 June 2024 on nature restoration.",
        "identifier": "http://data.europa.eu/eli/reg/2024/1991/oj",
        "holds": "The regulation, from which the restoration targets, the ecosystem "
                 "condition indicators and the national planning obligations are "
                 "obtained.",
        "used_for": "The restoration-priority framing of the demonstration cases, and "
                    "the reporting alignment the scope requires.",
    },
    {
        "source_id": "SRC-FAIR",
        "title": "The FAIR data principles",
        "names": ["FAIR"],
        "cited_as": "Wilkinson, M. D. et al. (2016), 'The FAIR Guiding Principles for "
                    "scientific data management and stewardship', Scientific Data 3, "
                    "160018.",
        "identifier": "https://doi.org/10.1038/sdata.2016.18",
        "holds": "The paper that states the four principles the call's FAIR "
                 "requirement refers to.",
        "used_for": "The harmonisation and metadata workflows the fourth scope "
                    "requirement asks for, which P04 and P10 engineer.",
    },
)


# ---------------------------------------------------------------------------
# The name partition — the half of the derivation that is not a source
# ---------------------------------------------------------------------------

#: Every derived candidate name that is not source material, with the reason.
#:
#: The sweep in :func:`runner.source_index.candidate_names` is deliberately
#: indiscriminate: it takes every acronym and every multi-word capitalised name in
#: the concept brief and the consortium registry. That is what makes "each source
#: cited in the concept has an entry" checkable rather than asserted, and it means
#: each candidate it produces needs a disposition. Three kinds appear here: tier
#: vocabulary that belongs to Tier 1, 2A or 2B rather than to source material;
#: organisations the project coordinates with but cites nothing from; and
#: artifacts of the regex itself.
NOT_SOURCES: dict[str, str] = {
    # Tier vocabulary
    "RIA": "The Tier 2A instrument name. A structural authority, not source material.",
    "Research and Innovation Action": "The Tier 2A action type the topic selects. Tier "
                                      "2A governs it; nothing is cited from it.",
    "HORIZON": "The first token of the topic and call identifiers. An identifier, not "
               "a document.",
    "BIODIV-01": "The tail of the topic identifier.",
    "EUR": "The currency of the budget figure.",
    "SME": "An enterprise category from Tier 1 participation vocabulary, used as a "
           "partner type in partners.json.",
    "Member State": "Tier 1 eligibility vocabulary, carried by the composition "
                    "condition. Tier 1 governs it.",
    "Associated Country": "Tier 1 eligibility vocabulary, the other half of the "
                          "composition condition.",
    "Member States and Associated Countries": "A Tier 2B scope phrase naming where use "
                                              "cases must sit. A requirement, not a "
                                              "source.",
    "Integrating Remote Sensing": "The opening words of the topic title.",
    "Satellite Remote Sensing": "A Tier 2B scope phrase describing a measurement "
                                "class. No document is cited under it; the Copernicus "
                                "entry carries the missions.",
    "CLAUDE": "The filename of the repository constitution, cited by artifacts that "
              "name the clause they comply with.",
    "DNA": "Part of 'environmental DNA', a technique named in partner capabilities. A "
           "method, not a document.",
    "REALM": "The prefix of the three requirement references REALM-terrestrial, "
             "REALM-freshwater and REALM-marine in project_summary.json. An internal "
             "reference key.",
    # Organisations the project coordinates with, citing nothing from them
    "Joint Research Centre": "An EU body the topic allows into the consortium as a "
                             "zero-funding beneficiary. The concept holds a place for "
                             "it and cites nothing from it. Its permission is Tier 2B "
                             "text, carried by the page 73 source.",
    "The Joint Research Centre": "The same body with its article. Same disposition.",
    "European Space Agency": "The agency whose FuturEO programme the project "
                             "coordinates with. The programme has an entry "
                             "(SRC-FUTUREO); the agency as an institution is not "
                             "itself cited.",
    # Artifacts of the derivation
    "Marine Strategy Framework Directive and EU Nature Restoration Regulation": (
        "A regex artifact: the sweep glues two adjacent directive names that the call "
        "sentence joins with 'and'. Both halves are sources — SRC-MSFD and SRC-NRR — "
        "and each is claimed under its own name."
    ),
    "Confirmed for Tier": "A regex artifact spanning a status word and a tier "
                          "reference in adjacent prose.",
    "The Tier": "A regex artifact: the article plus a tier reference.",
    "Ingest Commission": "A regex artifact from the coordination table row 'Ingest "
                         "Commission-steered monitoring data'.",
    "Ingest the Commission": "The same row in project_summary.json, where the phrase "
                             "reads 'Ingest the Commission-steered monitoring data'.",
    "Use the European": "A regex artifact from a claim that begins 'Use the European "
                        "radar and optical missions'.",
}


# ---------------------------------------------------------------------------
# Derivation
# ---------------------------------------------------------------------------

SPAN_KEYS = frozenset({"quote", "source_document", "source_page"})


class AuthoringError(Exception):
    """A derivation could not be completed. Never worked around."""


def _iter_spans(node: Any, where: str = "$"):
    """Yield every recorded source-span object in the call extract, with its path."""
    if isinstance(node, dict):
        if SPAN_KEYS <= set(node):
            yield where, node
            return
        for key, value in node.items():
            yield from _iter_spans(value, f"{where}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _iter_spans(value, f"{where}[{index}]")


def _resolve_ref(node: Any, ref: str) -> Any:
    """Resolve a ``$.a.b[0]`` reference, or return ``None``."""
    if not ref.startswith("$"):
        return None
    current = node
    for part in ref[1:].split("."):
        if not part:
            continue
        name, _, rest = part.partition("[")
        if name:
            if not isinstance(current, dict) or name not in current:
                return None
            current = current[name]
        while rest:
            index_text, _, rest = rest.partition("]")
            if not isinstance(current, list):
                return None
            index = int(index_text)
            if index >= len(current):
                return None
            current = current[index]
            rest = rest.lstrip("[")
    return current


def _source_id(page: int) -> str:
    return f"SRC-WP9-P{page}"


def _locate(quote: str, texts: dict[int, str], page: Optional[int], what: str) -> tuple[int, int]:
    """Find *quote* in the transcribed pages and return ``(page, start)``.

    Raises when the quote is absent, or when no page is declared and more than
    one page contains it. Both are hard errors: a span whose page is guessed is
    a span whose provenance is guessed.
    """
    if page is not None:
        if page not in texts:
            raise AuthoringError(f"{what}: page {page} is not transcribed")
        start = texts[page].find(quote)
        if start < 0:
            raise AuthoringError(
                f"{what}: not found verbatim on page {page} — {quote[:80]!r}"
            )
        return page, start
    hits = [(p, texts[p].find(quote)) for p in sorted(texts) if texts[p].find(quote) >= 0]
    if not hits:
        raise AuthoringError(f"{what}: not found verbatim on any cited page — {quote[:80]!r}")
    if len(hits) > 1:
        raise AuthoringError(
            f"{what}: found on pages {[p for p, _ in hits]} and no page is declared, "
            f"so its provenance would be a guess — {quote[:80]!r}"
        )
    return hits[0]


def _build_spans(
    texts: dict[int, str], extract: dict[str, Any], summary: dict[str, Any]
) -> dict[int, list[dict[str, Any]]]:
    """Derive every span, merged by (page, start, end) and sorted by offset."""
    merged: dict[tuple[int, int, int], dict[str, Any]] = {}

    def add(page: int, start: int, quote: str, *, tier2b_ref: str = "",
            claim_ref: str = "", requirement_refs: Sequence[str] = ()) -> None:
        end = start + len(quote)
        key = (page, start, end)
        span = merged.setdefault(
            key,
            {
                "span_id": span_id(_source_id(page), start, end),
                "start": start,
                "end": end,
                "quote": quote,
                "tier2b_refs": [],
                "claim_refs": [],
                "requirement_refs": [],
            },
        )
        for field, value in (("tier2b_refs", tier2b_ref), ("claim_refs", claim_ref)):
            if value and value not in span[field]:
                span[field].append(value)
        for ref in requirement_refs:
            if ref not in span["requirement_refs"]:
                span["requirement_refs"].append(ref)

    for ref, recorded in _iter_spans(extract):
        if recorded["source_document"] != Path(PART9_REL).name:
            continue
        page = recorded["source_page"]
        if page not in texts:
            continue
        quote = normalise_whitespace(recorded["quote"])
        _, start = _locate(quote, texts, page, f"Tier 2B span {ref}")
        add(page, start, quote, tier2b_ref=ref)

    for claim in summary.get("concept_claims", []):
        cid = claim["claim_id"]
        quote = normalise_whitespace(claim["call_phrase"])
        target = _resolve_ref(extract, claim.get("tier2b_span_ref", ""))
        declared_page = None
        if isinstance(target, dict) and isinstance(target.get("source_page"), int):
            declared_page = target["source_page"]
        elif isinstance(target, list):
            pages = {t.get("source_page") for t in target if isinstance(t, dict)}
            candidates = sorted(p for p in pages if isinstance(p, int) and p in texts
                                and quote in texts[p])
            if len(candidates) == 1:
                declared_page = candidates[0]
        if declared_page is not None and quote not in texts.get(declared_page, ""):
            declared_page = None
        page, start = _locate(quote, texts, declared_page, f"claim {cid} call_phrase")
        add(page, start, quote, claim_ref=cid,
            requirement_refs=claim.get("requirement_refs", []))

    for page, entries in SEED_SPANS.items():
        for quote, requirement_ref in entries:
            _, start = _locate(quote, texts, page, f"seed span {requirement_ref}")
            add(page, start, quote, requirement_refs=(requirement_ref,))

    by_page: dict[int, list[dict[str, Any]]] = {page: [] for page in texts}
    for (page, start, _end), span in sorted(merged.items()):
        by_page[page].append(span)
    return by_page


def _page_source(page: int, text: str, spans: list[dict[str, Any]]) -> dict[str, Any]:
    claim_refs = sorted({ref for span in spans for ref in span["claim_refs"]})
    return {
        "source_id": _source_id(page),
        "title": f"Horizon Europe Work Programme 2026-2027, Part 9, page {page}",
        "kind": "call_document_page",
        "status": "Confirmed",
        "what_the_page_carries": PAGES[page],
        "citation": {
            "cited_as": "European Commission, Horizon Europe Work Programme 2026-2027, "
                        "Part 9: Food, Bioeconomy, Natural Resources, Agriculture and "
                        f"Environment, page {page}.",
            "document_id": PART9_DOCUMENT_ID,
            "page": page,
        },
        "resolves_to": {
            "class": "stored_document",
            "stored_path": PART9_REL,
            "document_id": PART9_DOCUMENT_ID,
            "page": page,
            "what_it_holds": f"Page {page} of the work programme PDF stored in this "
                             f"repository and registered as {PART9_DOCUMENT_ID}.",
        },
        "transcription": {
            "state": "transcribed",
            "method": PAGE_TEXT_METHOD,
            "replay": "runner.source_index.read_page_text(stored_path, page). The "
                      "verifier re-runs it and compares byte for byte, so this text "
                      "cannot drift from the stored document.",
        },
        "text": text,
        "spans": spans,
        "relied_on_for": [
            {
                "what": PAGE_USES[page],
                "claim_refs": claim_refs,
                "span_refs": [span["span_id"] for span in spans],
                "status": "Confirmed",
            }
        ],
    }


def _anchor_for(external: dict[str, Any], by_page: dict[int, list[dict[str, Any]]]
                ) -> dict[str, Any]:
    """Find the first transcribed span that names this reference.

    Searches pages in order, then offsets in order, so the anchor is stable
    across runs. Raises when no span names it: a reference the call text and the
    transcribed pages never name has no business claiming to be cited.
    """
    for page in sorted(by_page):
        for span in by_page[page]:
            for name in external["names"]:
                if name in span["quote"]:
                    return {
                        "via_source": _source_id(page),
                        "span_id": span["span_id"],
                        "verbatim": name,
                        "what_the_anchor_shows": "The call text names this source, "
                                                 "inside a span replayed byte-for-byte "
                                                 "from the stored page. It does not "
                                                 "show what the source itself contains.",
                    }
    raise AuthoringError(
        f"{external['source_id']}: none of {external['names']} appears in any "
        f"transcribed span, so the reference cannot be anchored"
    )


def _external_source(external: dict[str, Any], by_page: dict[int, list[dict[str, Any]]]
                     ) -> dict[str, Any]:
    identifier = external.get("identifier")
    resolves: dict[str, Any] = {
        "class": "external_identifier",
        "identifier": identifier,
        "identifier_status": "Assumed" if identifier else "Unresolved",
        "basis": _KNOWLEDGE_BASIS if identifier else external["identifier_note"],
        "what_it_holds": external["holds"],
    }
    record = {
        "source_id": external["source_id"],
        "title": external["title"],
        "kind": "external_reference",
        "status": "Assumed",
        "names": list(external["names"]),
        "citation": {"cited_as": external["cited_as"]},
        "anchor": _anchor_for(external, by_page),
        "resolves_to": resolves,
        "transcription": {
            "state": "cited_only",
            "reason": "No copy is stored in this repository and this workspace has no "
                      "verified network egress, so no verbatim text is transcribed. "
                      "The record therefore carries no span, and no claim can be "
                      "verified against it.",
        },
        "relied_on_for": [
            {
                "what": external["used_for"],
                "claim_refs": [],
                "span_refs": [],
                "status": "Assumed",
            }
        ],
    }
    return record


def _read_json(repo_root: Path, rel: str) -> Any:
    """Read a required input, or refuse with the same error type as the rest.

    Fail-closed and uniform: a missing concept summary and a missing PDF are the
    same kind of failure, and both must surface as a refusal to author rather
    than as a traceback from a different layer.
    """
    path = repo_root / rel
    if not path.is_file():
        raise AuthoringError(f"{rel} is absent")
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        raise AuthoringError(f"{rel} is unreadable: {exc}") from exc


def build(repo_root: Path) -> dict[str, Any]:
    """Derive the whole index. Raises :class:`AuthoringError` on any gap."""
    extract = _read_json(repo_root, CALL_EXTRACT_REL)
    summary = _read_json(repo_root, PROJECT_SUMMARY_REL)
    pdf = repo_root / PART9_REL
    if not pdf.is_file():
        raise AuthoringError(f"{PART9_REL} is absent")
    texts = {page: read_page_text(pdf, page) for page in sorted(PAGES)}
    by_page = _build_spans(texts, extract, summary)

    sources: list[dict[str, Any]] = [
        _page_source(page, texts[page], by_page[page]) for page in sorted(PAGES)
    ]
    sources.extend(_external_source(external, by_page) for external in EXTERNALS)

    return {
        "record_type": SOURCE_INDEX_RECORD_TYPE,
        "schema_ref": (
            "No declared schema. .claude/workflows/system_orchestration/"
            "artifact_schema_specification.yaml carries tier3_source_schemas for "
            "selected_call, topic_mapping, compliance_profile, partners, "
            "milestones_seed and working_assumptions, and none for sources.json. "
            "runner/dev_graph/builder.py asks only for a non-empty source_id and, "
            "if present, a string text. The rest of this shape is authored, and no "
            "schema_id is coined for it (CLAUDE.md §16.3), as partners.json and "
            "roles.json say of their own. runner/source_index.py holds what the "
            "shape must satisfy."
        ),
        "provenance_class": "derived_from_stored_sources",
        "artifact_purpose": (
            "The Tier 3 source index for instance two. The dev-graph snapshot builder "
            "reads it and turns each entry into a source node; a claim's verified span "
            "resolves byte offsets into a source's text. Written by "
            "tools/author_demo_sources.py and checked by runner/source_index.py."
        ),
        "topic_code": TOPIC,
        "intake_rule": {
            "rule": "A source carries verbatim text only when that text can be "
                    "re-derived from a file stored in this repository, byte for byte. "
                    "Everything else is a reference: a citation, an anchor showing "
                    "where the project names it, and an identifier recorded rather "
                    "than resolved.",
            "why": "A source record is the one place in Tier 3 where an unevidenced "
                   "claim can be made to look evidenced. A plausible citation, an "
                   "invented quotation and a span pointed at it would make the graph "
                   "report a grounded claim that no document supports. The builder "
                   "cannot catch that, because it has no way to know whether the text "
                   "is real. Byte-equal replay can.",
            "consequence": "Sixteen of the twenty-four entries carry no text at all, so "
                           "no claim in this project can be verified against a policy "
                           "instrument, a dataset or a paper. That is the honest state "
                           "of the evidence base, not a defect in the index.",
            "authority": "CLAUDE.md §10.5, §11.5, §12.2 and §13.3; §10.6 for the "
                         "identifiers recorded from prior knowledge.",
        },
        "sources": sources,
        "names_that_are_not_sources": dict(sorted(NOT_SOURCES.items())),
        "names_that_are_not_sources_note": (
            "The completeness half of the check. runner/source_index.candidate_names "
            "sweeps the concept brief and the consortium registry for every acronym "
            "and every multi-word capitalised name, and each candidate must be either "
            "claimed by a source's 'names' or declared here with a reason. An "
            "unclassified candidate fails the check, so a framework added to the "
            "concept later cannot pass unnoticed. Single capitalised words are the "
            "sweep's known limit and are listed in SINGLE_WORD_EXTERNALS instead."
        ),
        "field_status": {
            "transcribed_text_and_spans": "Confirmed. Re-derived from the stored PDF on "
                                          "every check and compared byte for byte.",
            "anchors": "Confirmed. Each anchor string is checked to occur inside a "
                       "replayed span.",
            "external_identifiers": "Assumed, or Unresolved where none is recorded. "
                                    "None was resolved on this branch.",
            "what_each_external_source_contains": "Assumed. Nothing is stored, so the "
                                                  "citation describes the document "
                                                  "without quoting it.",
            "relied_on_for_of_an_external_reference": "Assumed. The anchor shows the "
                                                      "call names the source. It does "
                                                      "not show the source supports the "
                                                      "use.",
        },
        "authored_by": (
            "tools/author_demo_sources.py, for the ticket 'Source materials and the "
            "sources index' in plans/dev_graph_demo_tickets.md, branch dev_graph_demo. "
            "Pages 47 and 48 and their nine spans were added by the ticket "
            "'Architecture seeds and the uncertainty ledger', which needed a Tier 2B "
            "ground for the impact pathways: see decision D3 in "
            "docs/tier4_orchestration_state/decision_log/"
            "demo-architecture-seeds_2026-09-30.json."
        ),
        "note": (
            "Anonymity: no organisation name, person name, place, web address, grant or "
            "project identifier from instance one appears here. The web addresses are "
            "public European and international framework addresses, none of which is "
            "tied to instance one. No unpublished material and no manuscript is cited."
        ),
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m tools.author_demo_sources",
        description="Author the instance-two Tier 3 source index from the stored call "
                    "document and the approved concept.",
    )
    parser.add_argument("--check", action="store_true",
                        help="Do not write; exit 1 if the file on disk differs.")
    parser.add_argument("--repo-root", default=None)
    args = parser.parse_args(argv)
    repo_root = Path(args.repo_root).resolve() if args.repo_root else find_repo_root()
    try:
        doc = build(repo_root)
    except AuthoringError as exc:
        print(f"[author-sources] FAIL — {exc}")
        return 1
    payload = json.dumps(doc, indent=2, ensure_ascii=False) + "\n"
    target = repo_root / SOURCES_REL
    if args.check:
        current = target.read_text(encoding="utf-8") if target.is_file() else ""
        if current != payload:
            print(f"[author-sources] FAIL — {SOURCES_REL} differs from the derivation")
            return 1
        print(f"[author-sources] OK — {SOURCES_REL} matches the derivation")
        return 0
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(payload, encoding="utf-8", newline="\n")
    spans = sum(len(s.get("spans", [])) for s in doc["sources"])
    print(f"[author-sources] wrote {SOURCES_REL}: {len(doc['sources'])} sources, "
          f"{spans} spans, {len(doc['names_that_are_not_sources'])} names declared "
          f"not to be sources")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
