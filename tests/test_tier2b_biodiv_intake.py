"""Tier 2B intake for the instance-two topic, checked against its own sources.

The intake ticket in `plans/dev_graph_demo_tickets.md` adds the authoritative
Tier 2B sources for `HORIZON-CL6-2027-01-BIODIV-01`, so Phase 1 has real
records to analyse. These checks hold the authored artifacts to the documents
they cite (CLAUDE.md §10.5, §13.2): every quoted span must occur in the stored
work programme PDF, and every date, figure and action type must agree with both
the PDF and the stored portal record.

The checks that matter most are the ones a reader cannot do by eye:

* each source span quote is a verbatim substring of the page it names;
* the slice is byte-equal to a fresh `runner/call_slicer.py` run, timestamp
  aside, so nothing in it was hand-written;
* the resolved dates equal the PDF timetable *and* the portal record, which is
  the contradiction the ticket asks to settle against sources, not memory.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from runner.agnosticism_lint import _PROPER_NOUNS
from runner.call_slicer import GROUPED_JSON_MAP, generate_call_slice
from runner.paths import find_repo_root
from tests._tier_sources import (
    STATUSES,
    digest as _digest,
    iter_spans as _iter_spans,
    norm as _norm,
)

REPO = find_repo_root()

TOPIC = "HORIZON-CL6-2027-01-BIODIV-01"
CALL_ID = "HORIZON-CL6-2027-01"
WORK_PROGRAMME = "cluster_climate"

TIER2B = REPO / "docs/tier2b_topic_and_call_sources"
EXTRACT = TIER2B / "call_extracts" / (TOPIC + ".json")
SLICE = TIER2B / "call_extracts" / (TOPIC + ".slice.json")
WP_DIR = TIER2B / "work_programmes" / WORK_PROGRAMME
PART9_PDF = WP_DIR / (
    "wp-9-food-bioeconomy-natural-resources-agriculture-and-environment"
    "_horizon-2026-2027_en.pdf"
)
PORTAL_JSON = WP_DIR / (TOPIC + ".portal.json")

SELECTED_CALL = (
    REPO / "docs/tier3_project_instantiation/call_binding/selected_call.json"
)
DOCUMENT_REGISTRY = REPO / "docs/index/document_registry.json"
DECISION_LOG = REPO / "docs/tier4_orchestration_state/decision_log"

#: Resolved against the Part 9 timetable (page 34) and the stored portal record.
OPENING = "2027-04-20"
DEADLINE = "2027-09-22"

#: The topic's own pages in the Part 9 PDF. Printed page == PDF page index.
TOPIC_PAGES = (73, 74, 75, 76)

#: Pages outside the topic entry that the extract cites: 34 the call timetable,
#: the destination heading and the deadline model; 35 the 2027 budget table.
SUPPORTING_PAGES = (34, 35)

#: Every cross-cutting requirement the ticket names, keyed as the extract keys it.
CROSS_CUTTING_KEYS = (
    "gbif_obis_lucas_cooperation",
    "jrc_participation",
    "lucas_grassland_and_embal",
    "eunis_and_global_ecosystem_typology",
    "eosc_and_common_data_spaces",
    "esa_futureo_coordination",
    "copernicus_galileo_egnos",
    "policy_reporting_alignment",
    "research_infrastructures",
)


def _assert_all_verbatim(strings: list, pdf_pages: dict, where: str) -> None:
    """Each string must occur verbatim on one of the topic's pages."""
    assert strings, where + " is empty"
    for index, value in enumerate(strings):
        assert value.strip(), where + "[" + str(index) + "] is blank"
        needle = _norm(value)
        assert any(needle in pdf_pages[page] for page in TOPIC_PAGES), (
            where + "[" + str(index) + "] is not verbatim on pages "
            + str(list(TOPIC_PAGES))
            + ": " + needle[:90]
        )


def _assert_statuses(field_status: dict, present_in: tuple, where: str) -> None:
    """Every status is one of the four §12.2 categories and names a real field."""
    assert field_status, where + " carries no field_status"
    for field, status in field_status.items():
        assert status in STATUSES, where + "." + field + " = " + str(status)
        assert any(field in mapping for mapping in present_in), (
            where + "." + field + " names no field of the artifact"
        )


@pytest.fixture(scope="module")
def extract() -> dict:
    return json.loads(EXTRACT.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def selected_call() -> dict:
    return json.loads(SELECTED_CALL.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def portal() -> dict:
    return json.loads(PORTAL_JSON.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def pdf_pages() -> dict:
    """The Part 9 pages the artifacts cite, normalised, keyed by printed page.

    This deliberately does not skip when pymupdf is missing. Reading the PDF is
    the whole verification this file exists to do, so an absent reader must turn
    the suite red rather than let it report green on checks that never ran
    (CLAUDE.md §15). pymupdf is declared in requirements.txt.
    """
    import pymupdf

    doc = pymupdf.open(PART9_PDF)
    try:
        wanted = TOPIC_PAGES + SUPPORTING_PAGES
        return {n: _norm(doc[n - 1].get_text()) for n in wanted}
    finally:
        doc.close()


class TestStoredSources:
    def test_the_part_9_pdf_is_stored_under_tier_2b(self) -> None:
        assert PART9_PDF.is_file()
        assert PART9_PDF.read_bytes()[:5] == b"%PDF-"

    def test_the_portal_topic_record_is_stored_under_tier_2b(
        self, portal: dict
    ) -> None:
        assert portal["topic_code"] == TOPIC
        assert portal["retrieved_from"].startswith("https://api.tech.ec.europa.eu/")
        assert portal["record"]["metadata"]["identifier"] == [TOPIC]

    def test_both_sources_are_registered_with_a_matching_digest(self) -> None:
        registry = json.loads(DOCUMENT_REGISTRY.read_text(encoding="utf-8"))
        entries = {e["path"]: e for e in registry["document_registry"]}
        for source in (PART9_PDF, PORTAL_JSON):
            rel = source.relative_to(REPO).as_posix()
            assert rel in entries, rel + " is not registered"
            entry = entries[rel]
            assert entry["sha256"] == _digest(source, entry["digest_basis"]), rel
            assert entry["tier"] == "2B", rel

    def test_every_registered_path_resolves_and_matches_its_digest(self) -> None:
        registry = json.loads(DOCUMENT_REGISTRY.read_text(encoding="utf-8"))
        for entry in registry["document_registry"]:
            path = REPO / entry["path"]
            assert path.is_file(), entry["path"]
            assert entry["sha256"] == _digest(path, entry["digest_basis"]), entry["path"]

    def test_every_row_matches_the_schema_the_registry_declares(self) -> None:
        """An index whose rows disagree with its own stated schema fails §9.6."""
        registry = json.loads(DOCUMENT_REGISTRY.read_text(encoding="utf-8"))
        schema = registry["entry_schema"]
        required = {
            "document_id",
            "path",
            "tier",
            "media_type",
            "bytes",
            "sha256",
            "digest_basis",
            "title",
            "role",
            "retrieved_on",
            "registered_by",
        }
        optional = {"retrieved_from", "retrieval_note", "pages"}
        for name in required | optional:
            assert name in schema, name + " is not declared in entry_schema"
        for entry in registry["document_registry"]:
            assert required <= set(entry), entry["document_id"]
            assert set(entry) <= required | optional, entry["document_id"]

    def test_a_row_without_a_retrieval_url_explains_why(self) -> None:
        """The schema makes retrieval_note required whenever retrieved_from is absent.

        Added by the Tier 1 and Tier 2A RIA coverage-check ticket, which
        registers three documents that predate this branch and whose download
        URLs are unrecorded. Without this check the schema's word 'required'
        would bind nothing.
        """
        registry = json.loads(DOCUMENT_REGISTRY.read_text(encoding="utf-8"))
        for entry in registry["document_registry"]:
            if "retrieved_from" not in entry:
                assert entry.get("retrieval_note"), entry["document_id"]

    def test_the_recorded_byte_count_matches_the_digest_basis(self) -> None:
        registry = json.loads(DOCUMENT_REGISTRY.read_text(encoding="utf-8"))
        for entry in registry["document_registry"]:
            raw = (REPO / entry["path"]).read_bytes()
            if entry["digest_basis"] == "lf_normalised_bytes":
                raw = raw.replace(b"\r\n", b"\n")
            assert entry["bytes"] == len(raw), entry["document_id"]

    def test_text_sources_are_digested_platform_independently(self) -> None:
        """core.autocrlf is true here, so a raw digest would identify the platform.

        A text source checks out CRLF on Windows and LF elsewhere. Recording the
        raw digest would make this suite pass on Windows and fail on Linux.
        """
        registry = json.loads(DOCUMENT_REGISTRY.read_text(encoding="utf-8"))
        for entry in registry["document_registry"]:
            expected = (
                "raw_bytes"
                if entry["media_type"] == "application/pdf"
                else "lf_normalised_bytes"
            )
            assert entry["digest_basis"] == expected, entry["document_id"]

    def test_the_portal_record_carries_the_same_dates_the_pdf_does(
        self, portal: dict
    ) -> None:
        """OPENING and DEADLINE are the values the PDF checks assert, so a match
        here is agreement between the two sources rather than a restatement."""
        action = json.loads(portal["record"]["metadata"]["actions"][0])[0]
        assert action["plannedOpeningDate"] == OPENING
        assert action["deadlineDates"] == [DEADLINE]

    def test_the_portal_record_carries_a_lump_sum_mga(
        self, portal: dict
    ) -> None:
        action = json.loads(portal["record"]["metadata"]["actions"][0])[0]
        mga = action["types"][0]["typeOfMGA"][0]
        assert mga["abbreviation"] == "HORIZON-AG-LS"
        assert "Lump Sum" in mga["description"]


class TestCallExtract:
    def test_it_names_the_topic_and_the_call(self, extract: dict) -> None:
        assert extract["topic_code"] == TOPIC
        assert extract["call_id"] == CALL_ID

    def test_the_action_type_is_ria(self, extract: dict) -> None:
        assert extract["instrument_type"] == "RIA"
        assert extract["type_of_action"] == "HORIZON-RIA"

    def test_the_budget_figures_match_the_work_programme(
        self, extract: dict, pdf_pages: dict
    ) -> None:
        assert extract["expected_eu_contribution_per_project_eur"] == 5_000_000
        assert extract["indicative_budget_eur"] == 10_000_000
        assert extract["indicative_number_of_projects"] == 2
        page = pdf_pages[73]
        assert "EU contribution of around EUR 5.00 million" in page
        assert "total indicative budget for the topic is EUR 10.00 million" in page

    def test_the_dates_match_the_work_programme_timetable(
        self, extract: dict, pdf_pages: dict
    ) -> None:
        assert extract["opening_date"] == OPENING
        assert extract["submission_deadline"] == DEADLINE
        assert "Opening: 20 Apr 2027" in pdf_pages[34]
        assert "Deadline(s): 22 Sep 2027" in pdf_pages[34]

    def test_the_budget_regime_is_lump_sum(self, extract: dict) -> None:
        assert extract["budget_regime"] == "lump_sum"

    def test_it_cites_the_part_9_pdf_by_page(self, extract: dict) -> None:
        assert extract["source_document"] == PART9_PDF.name
        assert extract["source_pages"] == "73-76"

    def test_all_three_expected_outcomes_are_verbatim_in_the_pdf(
        self, extract: dict, pdf_pages: dict
    ) -> None:
        """A length check alone would pass on three fabricated strings.

        The outcomes and the scope requirements are plain strings, not span
        objects, so `_iter_spans` never reaches them. They are the substance of
        the call, so each is matched against the topic's pages here.
        """
        outcomes = extract["expected_outcomes"]
        assert len(outcomes) == 3
        _assert_all_verbatim(outcomes, pdf_pages, "expected_outcomes")

    def test_the_five_scope_requirements_are_verbatim_in_the_pdf(
        self, extract: dict, pdf_pages: dict
    ) -> None:
        requirements = extract["scope_requirements"]
        assert len(requirements) == 5
        _assert_all_verbatim(requirements, pdf_pages, "scope_requirements")

    def test_the_scope_summary_is_verbatim_in_the_pdf(
        self, extract: dict, pdf_pages: dict
    ) -> None:
        _assert_all_verbatim([extract["scope_summary"]], pdf_pages, "scope_summary")

    def test_every_source_span_quotes_the_page_it_names(
        self, extract: dict, pdf_pages: dict
    ) -> None:
        spans = list(_iter_spans(extract))
        assert spans, "the extract carries no source span"
        for where, span in spans:
            page = span["source_page"]
            assert span["source_document"] == PART9_PDF.name, where
            assert page in pdf_pages, where + " cites unread page " + str(page)
            assert _norm(span["quote"]) in pdf_pages[page], (
                where + ": quote not found on page " + str(page)
            )

    @pytest.mark.parametrize("key", CROSS_CUTTING_KEYS)
    def test_each_cross_cutting_requirement_carries_a_span(
        self, extract: dict, key: str
    ) -> None:
        requirement = extract["cross_cutting_requirements"][key]
        assert requirement["requirement"].strip()
        span = requirement["source_span"]
        # A quote that straddles a page break is recorded as a list of spans.
        spans = span if isinstance(span, list) else [span]
        assert spans, key
        for one in spans:
            assert one["quote"].strip(), key

    def test_every_field_status_is_one_of_the_four_categories(
        self, extract: dict
    ) -> None:
        _assert_statuses(
            extract["field_status"],
            (extract, extract["cross_cutting_requirements"]),
            "extract.field_status",
        )


class TestCallSlice:
    def test_the_slice_is_a_fresh_slicer_run_bar_the_timestamp(
        self, tmp_path: Path
    ) -> None:
        """A hand-edited slice is the failure this catches.

        The slicer writes into the repo root it is given, so it runs against a
        throwaway root holding only its two inputs. Running it against REPO would
        make a test rewrite a tracked Tier 2B artifact (CLAUDE.md §9.1).
        """
        grouped_rel = GROUPED_JSON_MAP[WORK_PROGRAMME]
        for rel in (
            "docs/tier3_project_instantiation/call_binding/selected_call.json",
            grouped_rel,
        ):
            target = tmp_path / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((REPO / rel).read_bytes())

        written = generate_call_slice(tmp_path)

        committed = json.loads(SLICE.read_text(encoding="utf-8"))
        regenerated = json.loads(written.read_text(encoding="utf-8"))
        assert committed.pop("slice_timestamp")
        assert regenerated.pop("slice_timestamp")
        assert committed == regenerated
        # The tracked artifact is untouched by this test.
        assert SLICE.read_text(encoding="utf-8").count("slice_timestamp") == 1

    def test_it_slices_the_topic_out_of_the_cl6_grouped_json(self) -> None:
        sliced = json.loads(SLICE.read_text(encoding="utf-8"))
        assert sliced["topic_code"] == TOPIC
        assert sliced["source_grouped_json"] == GROUPED_JSON_MAP[WORK_PROGRAMME]
        assert sliced["call_entry"]["call_id"] == TOPIC


class TestSelectedCall:
    def test_the_slicer_can_read_it(self, selected_call: dict) -> None:
        assert selected_call["topic_code"] == TOPIC
        assert selected_call["work_programme"] in GROUPED_JSON_MAP

    def test_it_names_the_action_type_and_the_contribution(
        self, selected_call: dict
    ) -> None:
        assert selected_call["instrument_type"] == "RIA"
        assert selected_call["expected_eu_contribution_per_project_eur"] == 5_000_000

    def test_it_carries_the_resolved_dates(self, selected_call: dict) -> None:
        assert selected_call["call_opening"] == OPENING
        assert selected_call["submission_deadline"] == DEADLINE

    def test_its_budget_regime_agrees_with_the_instrument_registry(
        self, selected_call: dict
    ) -> None:
        path = REPO / "docs/tier2a_instrument_schemas/extracted/instrument_registry.json"
        registry = json.loads(path.read_text(encoding="utf-8"))
        ria = next(i for i in registry["instruments"] if i["instrument_type"] == "RIA")
        assert selected_call["budget_regime"] == ria["budget_regime"] == "lump_sum"

    def test_every_status_names_a_field_that_is_present(
        self, selected_call: dict
    ) -> None:
        _assert_statuses(
            selected_call["field_status"], (selected_call,), "selected_call.field_status"
        )

    def test_project_duration_is_never_confirmed(self, selected_call: dict) -> None:
        """Tier 2B sets no duration, so nothing can evidence one.

        The intake ticket left `project_duration_months` absent and handed the
        write to the concept ticket, where the operator takes the decision. Once
        written the field is Assumed and declared in `working_assumptions.json`.
        Confirmed would assert a call constraint the work programme does not
        carry, which is the §13.2 fabrication this check exists to catch. The
        absence itself is not the invariant — the status is.
        """
        assert selected_call["field_status"]["project_duration"] == (
            "Unresolved" if "project_duration_months" not in selected_call
            else "Assumed"
        )
        if "project_duration_months" in selected_call:
            assert selected_call["field_status"]["project_duration_months"] == "Assumed"
            assert "None." in selected_call["project_duration"]["tier2b_basis"]

    def test_the_call_extract_still_records_no_duration(
        self, extract: dict
    ) -> None:
        """Tier 2B is where a duration would have to come from, and it has none.
        A later ticket writing one into the extract would be inventing a call
        constraint (§13.2), whichever tier reads it afterwards."""
        assert extract["project_duration"]["status"] == "Unresolved"
        assert "project_duration_months" not in extract


class TestDecisionLog:
    @pytest.fixture(scope="class")
    def records(self) -> dict:
        found = {}
        for path in DECISION_LOG.glob("tier2b-biodiv-intake-*.json"):
            record = json.loads(path.read_text(encoding="utf-8"))
            found[record["id"]] = record
        return found

    def test_the_date_contradiction_names_the_prevailing_source(
        self, records: dict
    ) -> None:
        record = records["tier2b-biodiv-intake-dates"]
        assert record["record_type"] == "decision"
        assert record["prevailing_source"]["document"] == PART9_PDF.name
        assert record["resolution"]["opening_date"] == OPENING
        assert record["resolution"]["submission_deadline"] == DEADLINE

    def test_the_grant_type_finding_names_the_prevailing_source(
        self, records: dict
    ) -> None:
        record = records["tier2b-biodiv-intake-grant-type"]
        assert record["record_type"] == "decision"
        assert record["prevailing_source"]["document"] == PART9_PDF.name
        assert record["resolution"]["budget_regime"] == "lump_sum"
        assert record["resolution"]["phase_7_route"].strip()

    def test_both_records_cite_the_constitution(self, records: dict) -> None:
        assert set(records) == {
            "tier2b-biodiv-intake-dates",
            "tier2b-biodiv-intake-grant-type",
        }
        for record_id, record in records.items():
            assert record["branch"] == "dev_graph_demo", record_id
            assert "§" in record["authority"], record_id


class TestStaleExtractedFinding:
    """Finding I1 of the intake validation report, pinned so it cannot be lost.

    `phase_01_gate` checks the six Tier 2B extracted files only for non-emptiness
    and for the presence of source refs. Neither predicate compares their content
    to the selected topic. The files left by an earlier MSCA-PF run satisfy all
    twelve, so the gate would release Phase 1 for this topic on another call's
    outcomes — a fail-open gate against CLAUDE.md §15.

    The intake does not fix this: the branch holds the gate library unmodified,
    and Phase 1 owns `extracted/`. These checks hold the finding true while it is
    open, and turn red the moment someone closes it, which is the signal to strike
    the finding from the report rather than a regression.
    """

    EXTRACTED = TIER2B / "extracted"
    SIX = (
        "call_constraints",
        "expected_outcomes",
        "expected_impacts",
        "scope_requirements",
        "eligibility_conditions",
        "evaluation_priority_weights",
    )

    def test_the_extracted_files_still_belong_to_another_call(self) -> None:
        stale = [
            path.name
            for path in self.EXTRACTED.glob("*.json")
            if "HORIZON-MSCA" in path.read_text(encoding="utf-8")
        ]
        assert stale, (
            "Tier 2B extracted/ no longer carries the MSCA-era files. "
            "Finding I1 of tier2b-biodiv-intake_2026-09-29.json is closed and "
            "should be struck from the report."
        )

    def test_all_twelve_tier_2b_predicates_pass_before_phase_1_runs(self) -> None:
        from runner.predicates.file_predicates import non_empty_json
        from runner.predicates.source_ref_predicates import source_refs_present

        for stem in self.SIX:
            rel = "docs/tier2b_topic_and_call_sources/extracted/" + stem + ".json"
            assert non_empty_json(rel, repo_root=REPO).passed, stem
            assert source_refs_present(rel, repo_root=REPO).passed, stem

    def test_no_predicate_of_the_phase_1_gate_reads_the_selected_topic(self) -> None:
        """The missing check is what makes the gate fail open."""
        import yaml

        library = REPO / ".claude/workflows/system_orchestration/gate_rules_library.yaml"
        rules = yaml.safe_load(library.read_text(encoding="utf-8"))["gate_rules"]
        gate = next(g for g in rules if g.get("gate_id") == "phase_01_gate")
        tier2b = [
            p
            for p in gate["predicates"]
            if "tier2b_topic_and_call_sources/extracted" in str(p.get("args", {}))
        ]
        assert len(tier2b) == 12
        assert {p["function"] for p in tier2b} == {
            "non_empty_json",
            "source_refs_present",
        }
        # None of the twelve reads the call binding, so none can know which
        # topic the extracted content belongs to.
        for predicate in tier2b:
            args = str(predicate["args"])
            assert "selected_call" not in args, predicate["predicate_id"]
            assert TOPIC not in args, predicate["predicate_id"]

    def test_the_finding_is_recorded_in_tier_4(self) -> None:
        report = json.loads(
            (
                REPO
                / "docs/tier4_orchestration_state/validation_reports"
                / "tier2b-biodiv-intake_2026-09-29.json"
            ).read_text(encoding="utf-8")
        )
        i1 = next(f for f in report["findings"] if f["id"] == "I1")
        assert i1["status"] == "Unresolved"
        assert i1["recommended_owner"].strip()


class TestTierBoundaries:
    def test_phase_1_still_owns_tier_2b_extracted(self) -> None:
        """The intake writes no extracted/ file for this topic (§7 Phase 1)."""
        for path in (TIER2B / "extracted").glob("*.json"):
            assert TOPIC not in path.read_text(encoding="utf-8"), path.name

    def test_no_instance_one_proper_noun_reaches_the_authored_artifacts(self) -> None:
        pattern = re.compile(
            r"\b(?:" + "|".join(re.escape(n) for n in sorted(_PROPER_NOUNS)) + r")\b",
            re.IGNORECASE,
        )
        authored = [EXTRACT, SLICE, SELECTED_CALL, DOCUMENT_REGISTRY]
        authored += sorted(DECISION_LOG.glob("tier2b-biodiv-intake-*.json"))
        for path in authored:
            hits = pattern.findall(path.read_text(encoding="utf-8"))
            assert not hits, path.name + " leaks " + str(sorted(set(hits)))
