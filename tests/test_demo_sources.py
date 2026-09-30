"""The instance-two source materials, held to what they actually contain.

The ticket "Source materials and the sources index" in
`plans/dev_graph_demo_tickets.md` writes one Tier 3 artifact,
`source_materials/sources.json`, which the dev-graph snapshot builder turns into
`source` nodes and against which a claim's verified span resolves byte offsets.

Its three acceptance criteria are all mechanical, so all three are checked here
rather than asserted:

* **the builder reads it without error.** `TestTheBuilderReadsIt` builds a real
  snapshot over the populated repository and rebuilds it, because a source index
  that produced a different graph on a second read would break the demo's first
  question.
* **each source cited in the concept has an entry, and each entry resolves.**
  `TestEverySourceTheConceptCitesHasAnEntry` leans on the derived name partition
  in `runner/source_index.py`: every acronym and multi-word name in the brief and
  the consortium registry is either claimed by a source or declared with a reason.
  `TestEveryEntryResolves` holds the other half.
* **no source is described as supporting a claim it does not contain.**
  `TestNothingIsOverclaimed` is where that lives. Sixteen of the twenty-two
  entries carry no text at all, so nothing in this project can be verified
  against a policy instrument, a dataset or a paper. That is the honest state of
  the evidence base, and `TestTheHonestState` pins it so a later edit cannot
  quietly upgrade it.

The unit tests for the verifier itself, including a red case for every check, are
in `tests/runner/test_source_index.py`. This module is about the real data.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from runner import source_index as si
from runner.dev_graph.builder import build_snapshot
from runner.leakage_scan import scan_tree
from runner.paths import find_repo_root
from tests._tier_sources import iter_spans, norm

REPO = find_repo_root()

SOURCES = REPO / si.SOURCES_REL
CALL_EXTRACT = (
    REPO
    / "docs/tier2b_topic_and_call_sources/call_extracts"
    / "HORIZON-CL6-2027-01-BIODIV-01.json"
)
PROJECT_SUMMARY = REPO / si.PROJECT_SUMMARY_REL
GAP_REPORT = (
    REPO
    / "docs/tier4_orchestration_state/validation_reports"
    / "demo-consortium-gap-analysis_2026-09-30.json"
)
VALIDATION_REPORT = (
    REPO
    / "docs/tier4_orchestration_state/validation_reports"
    / "demo-source-materials_2026-09-30.json"
)
DECISION = (
    REPO
    / "docs/tier4_orchestration_state/decision_log"
    / "demo-source-materials_2026-09-30.json"
)

#: The Part 9 pages the index transcribes. Pinned so a page silently dropped from
#: the derivation fails here rather than quietly narrowing the evidence base.
CITED_PAGES = (34, 35, 73, 74, 75, 76)


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


@pytest.fixture(scope="module")
def index() -> dict[str, Any]:
    return _json(SOURCES)


@pytest.fixture(scope="module")
def pages(index: dict[str, Any]) -> list[dict[str, Any]]:
    return [s for s in index["sources"] if s["kind"] == "call_document_page"]


@pytest.fixture(scope="module")
def references(index: dict[str, Any]) -> list[dict[str, Any]]:
    return [s for s in index["sources"] if s["kind"] == "external_reference"]


@pytest.fixture(scope="module")
def all_spans(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [span for page in pages for span in page["spans"]]


# ---------------------------------------------------------------------------
# The verifier, on the real index
# ---------------------------------------------------------------------------


class TestTheIndexVerifies:
    def test_every_check_passes_on_the_real_index(self) -> None:
        report = si.verify(REPO)
        assert report.ok, report.format()

    def test_the_transcriptions_replay_byte_for_byte(self, pages: list[dict[str, Any]]) -> None:
        """The anti-fabrication guarantee, run directly rather than through the
        verifier, so this module fails on its own if the stored text ever drifts
        from the document it claims to come from."""
        for page in pages:
            stored = REPO / page["resolves_to"]["stored_path"]
            replayed = si.read_page_text(stored, page["resolves_to"]["page"])
            assert page["text"] == replayed, page["source_id"]

    def test_the_index_matches_its_own_derivation(self) -> None:
        """Nothing in the index is hand-typed except the citations and the uses.

        `tools/author_demo_sources.py --check` re-derives every transcription and
        every offset. A hand edit to a span or a page text fails here, which is
        what makes the offsets trustworthy rather than merely plausible.
        """
        from tools.author_demo_sources import main

        assert main(["--check", "--repo-root", str(REPO)]) == 0

    def test_the_cited_pages_are_the_ones_pinned_here(self, pages: list[dict[str, Any]]) -> None:
        assert tuple(p["resolves_to"]["page"] for p in pages) == CITED_PAGES


# ---------------------------------------------------------------------------
# Criterion 1 — the builder reads it
# ---------------------------------------------------------------------------


class TestTheBuilderReadsIt:
    def test_a_snapshot_builds_over_the_populated_repository(self, index: dict[str, Any]) -> None:
        snapshot = build_snapshot(REPO)
        sources = [n for n in snapshot.nodes if n["type"] == "source"]
        assert len(sources) == len(index["sources"])
        assert si.SOURCES_REL in snapshot.inputs

    def test_two_builds_give_the_same_snapshot_id(self) -> None:
        assert build_snapshot(REPO).snapshot_id == build_snapshot(REPO).snapshot_id

    def test_the_builder_derives_no_span_node_from_this_index(self) -> None:
        """Stated so the index's 45 spans are not read as graph spans.

        They are resolved by runner/source_index.py. The builder's own span
        mechanism needs a document record, and Tier 3 has none yet.
        """
        types = {n["type"] for n in build_snapshot(REPO).nodes}
        assert "source" in types
        assert "source_span" not in types

    def test_every_source_node_carries_its_record_and_its_path(self, index: dict[str, Any]) -> None:
        nodes = {n["id"]: n for n in build_snapshot(REPO).nodes if n["type"] == "source"}
        for source in index["sources"]:
            node = nodes[source["source_id"]]
            assert node["path"] == si.SOURCES_REL
            assert node["content"] == source

    def test_a_span_offset_resolves_inside_the_node_text(self, pages: list[dict[str, Any]]) -> None:
        """The offsets work against the text the builder actually indexes.

        The builder does not read this index's `spans`: it derives source_span
        nodes from a *document* record's claim `verified_span`, under
        `dev_graph/documents`. A snapshot over Tier 3 alone therefore carries 22
        source nodes and no source_span node, which the next assertion pins.
        What these spans are is the offsets a later document claim will point
        at, resolved in advance against the same node text the builder will use.
        """
        nodes = {n["id"]: n for n in build_snapshot(REPO).nodes if n["type"] == "source"}
        for page in pages:
            text = nodes[page["source_id"]]["content"]["text"]
            for span in page["spans"]:
                assert text[span["start"]:span["end"]] == span["quote"]


# ---------------------------------------------------------------------------
# Criterion 2 — every cited source has an entry, and every entry resolves
# ---------------------------------------------------------------------------


class TestEverySourceTheConceptCitesHasAnEntry:
    def test_every_derived_name_is_claimed_or_declared(self, index: dict[str, Any]) -> None:
        """The partition, restated here so this module carries the criterion.

        The sweep is indiscriminate on purpose. A framework added to the concept
        later produces a candidate, and an unclassified candidate fails.
        """
        candidates = si.candidate_names(REPO)
        claimed = {n for s in index["sources"] for n in s.get("names", [])}
        declared = set(index["names_that_are_not_sources"])
        unclassified = set(candidates) - claimed - declared
        assert not unclassified, sorted(unclassified)

    def test_the_frameworks_the_scope_names_all_have_entries(self, index: dict[str, Any]) -> None:
        """A direct read of the cross-cutting requirements, independent of the
        sweep, so a regex change cannot silently drop a required source."""
        extract = _json(CALL_EXTRACT)
        claimed = {n for s in index["sources"] for n in s.get("names", [])}
        declared = set(index["names_that_are_not_sources"])
        named_in_scope = (
            "GBIF", "OBIS", "LUCAS", "EMBAL", "EUNIS", "Global Ecosystem Typology",
            "EOSC", "European Common Data Spaces", "Copernicus", "FuturEO",
            "Habitats Directive", "Birds Directive",
        )
        extract_text = json.dumps(extract, ensure_ascii=False)
        for name in named_in_scope:
            assert name in extract_text, f"{name} is not in the call extract"
            assert name in claimed or name in declared, name

    def test_no_entry_claims_a_name_the_concept_never_uses(
        self, references: list[dict[str, Any]]
    ) -> None:
        texts = [
            (REPO / rel).read_text(encoding="utf-8-sig")
            for rel in si.NAMED_IN_PATHS
            if (REPO / rel).is_file()
        ]
        for reference in references:
            for name in reference["names"]:
                assert any(name in text for text in texts), (
                    f"{reference['source_id']} claims {name!r}"
                )

    def test_every_declared_non_source_gives_a_reason(self, index: dict[str, Any]) -> None:
        for name, reason in index["names_that_are_not_sources"].items():
            assert len(reason.split()) >= 4, f"{name}: {reason!r}"


class TestEveryEntryResolves:
    def test_a_page_source_resolves_to_a_registered_stored_file(
        self, pages: list[dict[str, Any]]
    ) -> None:
        registry = {
            entry["document_id"]
            for entry in _json(REPO / si.DOCUMENT_REGISTRY_REL)["document_registry"]
        }
        for page in pages:
            resolves = page["resolves_to"]
            assert (REPO / resolves["stored_path"]).is_file()
            assert resolves["document_id"] in registry

    def test_a_reference_resolves_through_an_identifier_or_an_anchor(
        self, references: list[dict[str, Any]]
    ) -> None:
        """The criterion allows either a stored file or a public identifier.

        A reference with no identifier — EMBAL, for which none could be verified
        here — resolves through its anchor instead: the stored call page that
        names it. A reference with neither would resolve to nothing, and the
        verifier refuses that.
        """
        for reference in references:
            resolves = reference["resolves_to"]
            has_identifier = bool(resolves["identifier"])
            has_anchor = bool(reference["anchor"].get("via_source")
                              or reference["anchor"].get("artifact"))
            assert has_identifier or has_anchor, reference["source_id"]

    def test_every_anchor_lands_in_a_replayed_span(
        self, references: list[dict[str, Any]], pages: list[dict[str, Any]]
    ) -> None:
        spans = {
            span["span_id"]: span for page in pages for span in page["spans"]
        }
        for reference in references:
            anchor = reference["anchor"]
            assert anchor["verbatim"] in spans[anchor["span_id"]]["quote"], (
                reference["source_id"]
            )


# ---------------------------------------------------------------------------
# Criterion 3 — nothing is described as supporting what it does not contain
# ---------------------------------------------------------------------------


class TestNothingIsOverclaimed:
    def test_no_reference_carries_text_or_a_span(
        self, references: list[dict[str, Any]]
    ) -> None:
        """The rule, at its plainest.

        No copy of any external reference is stored and this workspace has no
        verified network egress, so a quotation from one would be a quotation
        nobody can check. None is present, so no claim can ever resolve against
        one.
        """
        for reference in references:
            assert "text" not in reference, reference["source_id"]
            assert "spans" not in reference, reference["source_id"]
            assert reference["transcription"]["state"] == "cited_only"

    def test_no_use_of_a_reference_is_confirmed(
        self, references: list[dict[str, Any]]
    ) -> None:
        for reference in references:
            for use in reference["relied_on_for"]:
                assert use["status"] != "Confirmed", reference["source_id"]
                assert use["span_refs"] == []

    def test_no_external_identifier_is_confirmed(
        self, references: list[dict[str, Any]]
    ) -> None:
        for reference in references:
            assert reference["resolves_to"]["identifier_status"] in {
                "Assumed", "Unresolved"
            }, reference["source_id"]

    def test_the_declared_status_and_the_verified_span_stay_separate_fields(
        self, index: dict[str, Any]
    ) -> None:
        """A use's status is declared; a span is verified. Neither is derived
        from the other, so a use with no span keeps its own lower status rather
        than losing it, and a use with a span does not gain Confirmed by
        implication."""
        for source in index["sources"]:
            for use in source["relied_on_for"]:
                assert "status" in use and "span_refs" in use
                if use["status"] == "Confirmed":
                    assert use["span_refs"]

    def test_every_anchor_says_what_it_does_not_show(
        self, references: list[dict[str, Any]]
    ) -> None:
        """An anchor proves the call names a source. It proves nothing about
        what the source contains, and the record has to say so, because that is
        the exact confusion this criterion guards against."""
        for reference in references:
            shown = reference["anchor"]["what_the_anchor_shows"]
            assert "does not show" in shown, reference["source_id"]


# ---------------------------------------------------------------------------
# What the index actually covers
# ---------------------------------------------------------------------------


class TestCoverageOfTheConcept:
    def test_every_concept_claim_has_a_span_carrying_its_call_phrase(
        self, all_spans: list[dict[str, Any]]
    ) -> None:
        claims = _json(PROJECT_SUMMARY)["concept_claims"]
        covered = {ref for span in all_spans for ref in span["claim_refs"]}
        assert covered == {claim["claim_id"] for claim in claims}

    def test_each_claim_span_is_the_claim_phrase_verbatim(
        self, all_spans: list[dict[str, Any]]
    ) -> None:
        phrases = {
            claim["claim_id"]: norm(claim["call_phrase"])
            for claim in _json(PROJECT_SUMMARY)["concept_claims"]
        }
        for span in all_spans:
            for ref in span["claim_refs"]:
                assert phrases[ref] == span["quote"], ref

    def test_every_recorded_tier2b_span_on_a_cited_page_is_located(
        self, all_spans: list[dict[str, Any]]
    ) -> None:
        extract = _json(CALL_EXTRACT)
        part9 = (
            "wp-9-food-bioeconomy-natural-resources-agriculture-and-environment"
            "_horizon-2026-2027_en.pdf"
        )
        expected = {
            where
            for where, span in iter_spans(extract)
            if span["source_document"] == part9 and span["source_page"] in CITED_PAGES
        }
        located = {ref for span in all_spans for ref in span["tier2b_refs"]}
        assert expected == located

    def test_every_requirement_the_gap_analysis_rows_is_reached(
        self, all_spans: list[dict[str, Any]]
    ) -> None:
        """The gap analysis carries one row per topic requirement. Each of those
        requirements is reached by at least one span here, so the evidence layer
        covers the same requirement set the consortium was measured against."""
        rows = _json(GAP_REPORT)["requirement_coverage"]
        reached = {ref for span in all_spans for ref in span["requirement_refs"]}
        expected = {row["requirement_id"] for row in rows}
        assert expected <= reached, sorted(expected - reached)


# ---------------------------------------------------------------------------
# The honest state, pinned
# ---------------------------------------------------------------------------


class TestTheHonestState:
    def test_the_evidence_base_is_mostly_unverifiable_and_says_so(
        self, index: dict[str, Any], pages: list[dict[str, Any]],
        references: list[dict[str, Any]]
    ) -> None:
        """Six transcribed pages of a call document, and sixteen references with
        no text. Written down because it is the ticket's real result: the concept
        now cites its sources, and almost none of those citations can be checked
        from inside this repository."""
        assert len(pages) == 6
        assert len(references) == 16
        consequence = index["intake_rule"]["consequence"]
        assert "no claim" in consequence
        assert "twenty-two" in consequence

    def test_the_intake_rule_states_the_byte_equal_condition(
        self, index: dict[str, Any]
    ) -> None:
        rule = index["intake_rule"]["rule"]
        assert "byte for byte" in rule
        assert "stored in this repository" in rule

    def test_the_field_status_marks_the_identifiers_assumed(
        self, index: dict[str, Any]
    ) -> None:
        status = index["field_status"]
        assert status["external_identifiers"].startswith("Assumed")
        assert status["transcribed_text_and_spans"].startswith("Confirmed")

    def test_no_orch_schema_id_is_coined(self, index: dict[str, Any]) -> None:
        """§16.3, and the convention partners.json and roles.json state.

        No Tier 3 source artifact carries a registered orch.* id, because the
        schema specification declares no shape for one. The index declares what
        it is through record_type and says in schema_ref that its shape is
        authored.
        """
        assert "schema_id" not in index
        assert index["record_type"] == si.SOURCE_INDEX_RECORD_TYPE
        assert "No declared schema" in index["schema_ref"]

    def test_no_source_is_unpublished_material(self, index: dict[str, Any]) -> None:
        """The ticket forbids instance-one unpublished material and manuscripts.

        Every entry is either a page of the public work programme or a public
        framework, dataset, policy instrument or paper.
        """
        assert {s["kind"] for s in index["sources"]} == {
            "call_document_page", "external_reference"
        }
        assert "no unpublished material" in index["note"].lower()

    def test_a_validation_report_and_a_decision_entry_exist(self) -> None:
        assert VALIDATION_REPORT.is_file()
        assert DECISION.is_file()
        report = _json(VALIDATION_REPORT)
        assert report["findings"], "a report with no findings hides its own limits"

    def test_the_report_rows_match_the_index(
        self, pages: list[dict[str, Any]], references: list[dict[str, Any]]
    ) -> None:
        """A report that records derived values must record the real ones.

        The first draft of this report carried hand-typed span ids, and thirteen
        of sixteen were wrong. A Tier 4 record that misstates the artifact it
        reports on is worse than no record, so the rows are checked here.
        """
        report = _json(VALIDATION_REPORT)
        assert [
            {"source_id": p["source_id"], "page": p["resolves_to"]["page"],
             "chars": len(p["text"]), "spans": len(p["spans"])}
            for p in pages
        ] == [
            {"source_id": r["source_id"], "page": r["page"],
             "chars": r["transcribed_chars"], "spans": r["spans"]}
            for r in report["transcribed_sources"]
        ]
        assert [
            {"source_id": r["source_id"], "anchor": r["anchor"]["span_id"],
             "identifier": r["resolves_to"]["identifier"],
             "names": r["names"]}
            for r in references
        ] == [
            {"source_id": r["source_id"], "anchor": r["anchored_in"],
             "identifier": r["identifier"], "names": r["names"]}
            for r in report["external_references"]
        ]

    def test_the_report_counts_match_the_index(
        self, pages: list[dict[str, Any]], references: list[dict[str, Any]],
        all_spans: list[dict[str, Any]]
    ) -> None:
        answer = _json(VALIDATION_REPORT)["answer"]
        assert f"{len(all_spans)} resolved spans" in answer
        assert len(pages) + len(references) == 22


# ---------------------------------------------------------------------------
# Anonymity
# ---------------------------------------------------------------------------


class TestAnonymity:
    def test_the_index_introduces_no_new_leak(self) -> None:
        report = scan_tree(REPO)
        offenders = [
            v for v in report.new_violations
            if v.path.endswith("source_materials/sources.json")
        ]
        assert not offenders, [v.snippet for v in offenders]

    def test_the_branch_is_no_less_ok_than_before(self) -> None:
        """`ok` is the regression guard; `clean` is the constraint. The branch
        holds one recorded pre-existing leak in a Tier 4 purge record, so it is
        not clean, and this ticket does not change that."""
        report = scan_tree(REPO)
        assert report.ok, report.format()
        assert not report.clean

    def test_the_web_addresses_are_public_framework_addresses(
        self, references: list[dict[str, Any]]
    ) -> None:
        """Tier 3 carries web addresses for the first time on this branch.

        The constraint forbids instance one's addresses, not every address. Each
        one here belongs to a European or international framework the call names,
        and none is attached to a partner record, where an address would
        re-identify a derived partner.
        """
        partners = _json(REPO / "docs/tier3_project_instantiation/consortium/partners.json")
        assert "http" not in json.dumps(partners)
        for reference in references:
            identifier = reference["resolves_to"]["identifier"]
            if identifier:
                assert identifier.startswith(("http://", "https://"))
