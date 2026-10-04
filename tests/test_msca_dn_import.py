"""PE-03 — External proposal import.

Acceptance, from ``plans/msca_dn_pre_evaluation_spec.md`` §7 PE-03:

* Sub-section prose matches the PDF verbatim under a declared normalisation.
* Re-running the importer produces byte-identical output.
* All 17 tables render and every row parses.
* Extraction losses are recorded, including the zero figures and the zero
  dependency strings.
* The originals are untouched.

Plus the ticket's rules on the ledger: it is frozen here, every claim is a
proposal assertion with no external source (``unconfirmed``, never
``source_grounded``), and the record is schema v2.

Every figure is re-derived from the stored PDF through the same substrate the
importer uses, and the committed files are compared byte for byte against a
fresh rendering. The import takes a few seconds, so it is built once per
module.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

from runner.dev_graph import DOCUMENT_SCHEMA_ID_V2, build_snapshot, read_esr_intake
from runner.dev_graph.builder import SOURCES_REL
from runner.dev_graph.documents import DOCUMENTS_REL
from runner.external_proposal import is_row, nonws_len, parse_row
from runner.paths import find_repo_root
from runner.source_index import PAGE_TEXT_METHOD, normalise_whitespace, read_page_text
from tools import author_msca_dn_workspace as ws
from tools import import_external_proposal as ie

REPO = find_repo_root()
WORKSPACE = REPO / ie.WORKSPACE_REL
PDF = REPO / ie.CANDIDATE_PDF_REL
MANIFEST = WORKSPACE / ie.IMPORTS_REL / "MSCA-DN-2025_sanitised_part_b.json"

#: Spec §4.2, typed on purpose: the test must catch a shape the tool drifted to.
SPEC_SHAPE = {
    "excellence_section": ["1.1", "1.2", "1.3", "1.4"],
    "impact_section": ["2.1", "2.2", "2.3", "2.4"],
    "implementation_section": ["3.1", "3.2", "4", "5", "6", "7", "8"],
}
#: Spec §4.1 start pages, typed on purpose; the one derived difference is asserted below.
SPEC_START_PAGES = {
    "1.1": 1, "1.2": 14, "1.3": 22, "1.4": 27, "2.1": 32, "2.2": 34, "2.3": 36, "2.4": 39,
    "3.1": 41, "3.2": 65, "4": 67, "5": 68, "6": 73, "7": 74, "8": 76,
}
SPEC_TABLES = 17
SPEC_PAGES = 84
#: Spec §1 and PE-01, first 16 hex of the sha256.
SPEC_HASH_PREFIXES = {"candidate": "5474569f33d20174", "esr": "40a885e8aa593367"}


@pytest.fixture(scope="module")
def imp() -> ie.Import:
    return ie.build_import(REPO)


@pytest.fixture(scope="module")
def record() -> dict:
    recs = sorted((WORKSPACE / DOCUMENTS_REL).rglob("*.json"))
    assert len(recs) == 1, [p.name for p in recs]
    return json.loads(recs[0].read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def sources() -> dict:
    return json.loads((WORKSPACE / SOURCES_REL).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def register() -> dict:
    return json.loads((REPO / ie.REGISTER_REL).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def page_texts() -> dict[int, str]:
    return {p: read_page_text(PDF, p) for p in range(1, SPEC_PAGES + 1)}


def _sub_sections(record: dict) -> dict[str, dict]:
    return {ss["sub_section_id"]: ss for s in record["sections"] for ss in s["sub_sections"]}


def _paragraphs(content: str) -> list[str]:
    return [p for p in content.split("\n\n") if p]


# --------------------------------------------------------------------------- #
# Replay: byte-identical output, both tools
# --------------------------------------------------------------------------- #


class TestReplay:
    def test_import_check_mode_passes_on_the_committed_tree(self) -> None:
        assert ie.main(["--check"]) == 0

    def test_workspace_check_mode_still_passes(self) -> None:
        assert ws.main(["--check"]) == 0

    def test_rendering_twice_is_equal(self) -> None:
        assert ie.render_all(REPO) == ie.render_all(REPO)

    def test_rendered_bytes_match_the_committed_files(self) -> None:
        for rel, data in ie.render_all(REPO).items():
            assert (REPO / rel).read_bytes() == data, rel

    def test_the_two_tools_render_the_same_register(self) -> None:
        from runner.atomic_write import canonical_json_bytes

        assert ie.render_all(REPO)[ie.REGISTER_REL.as_posix()] == canonical_json_bytes(ws.render_register(REPO))

    def test_no_wall_clock_field_anywhere(self) -> None:
        for rel in ie.render_all(REPO):
            text = (REPO / rel).read_text(encoding="utf-8")
            for key in ("imported_at", "created_at", "timestamp", "generated_at"):
                assert key not in text, (rel, key)


# --------------------------------------------------------------------------- #
# The originals
# --------------------------------------------------------------------------- #


class TestOriginals:
    def test_the_two_pdfs_still_carry_the_spec_hashes(self) -> None:
        for key, path in (("candidate", PDF), ("esr", REPO / ws.ESR_PDF_REL)):
            assert hashlib.sha256(path.read_bytes()).hexdigest().startswith(SPEC_HASH_PREFIXES[key]), key

    def test_the_importer_writes_nothing_under_the_originals_directory(self) -> None:
        assert not any(rel.startswith(ws.SOURCE_DIR_REL.as_posix()) and not rel.endswith("fidelity_register.json")
                       for rel in ie.render_all(REPO))


# --------------------------------------------------------------------------- #
# Verbatim under the declared normalisation
# --------------------------------------------------------------------------- #


class TestVerbatim:
    def test_every_prose_paragraph_is_a_substring_of_the_page_text(self, record, page_texts) -> None:
        joined = " ".join(page_texts[p] for p in range(1, SPEC_PAGES + 1))
        for sid, ss in _sub_sections(record).items():
            for para in _paragraphs(ss["content"]):
                if is_row(para):
                    continue
                assert para in joined, (sid, para[:80])

    def test_every_heading_and_the_criterion_heading_are_on_the_page(self, record, imp, page_texts) -> None:
        for s in imp.sub_sections:
            if s.heading is not None:
                assert s.heading in page_texts[s.start_page], s.spec.sub_section_id
        impl = next(s for s in record["sections"] if s["section_id"] == "implementation_section")
        assert impl["content"] == "3. Quality and Efficiency of the Implementation"
        assert impl["content"] in page_texts[41]

    def test_every_table_cell_is_made_of_its_pages_characters(self, imp, page_texts, manifest) -> None:
        """A wrapped cell is not always contiguous in the page's reading order
        (three cells are not), so containment is checked as a character
        multiset; the completeness count below proves no character was dropped,
        and the manifest records which cells read in a different order."""
        from collections import Counter

        reordered = []
        for p in imp.pages:
            page_chars = Counter(page_texts[p.page].replace(" ", ""))
            for t in p.tables:
                for r, row in enumerate(t.rows):
                    for c, cell in enumerate(row):
                        assert not (Counter(cell.replace(" ", "")) - page_chars), (p.page, cell[:60])
                        if cell and cell not in page_texts[p.page]:
                            reordered.append((p.page, t.index, r, c))
        assert [(x["page"], x["index"], x["row"], x["col"]) for x in manifest["tables"]["cells_not_contiguous_in_page_text"]] == reordered
        assert len(reordered) == 3

    def test_nothing_is_lost_the_record_accounts_for_every_non_whitespace_character(self, record, imp, page_texts) -> None:
        """Completeness, the other half of verbatim: the headings, the criterion
        heading, every prose paragraph and every table cell together carry
        exactly the non-whitespace characters of the 84 pages."""
        total = sum(nonws_len(t) for t in page_texts.values())
        accounted = nonws_len(next(s for s in record["sections"] if s["section_id"] == "implementation_section")["content"])
        for s in imp.sub_sections:
            if s.heading is not None:
                accounted += nonws_len(s.heading)
        for ss in _sub_sections(record).values():
            for para in _paragraphs(ss["content"]):
                if is_row(para):
                    accounted += sum(nonws_len(c) for c in parse_row(para))
                else:
                    accounted += nonws_len(para)
        assert accounted == total

    def test_the_declared_normalisation_is_whitespace_only(self, record, page_texts) -> None:
        """Collapsing a sub-section's prose yields text whose every character
        is a character of the page text: nothing was rewritten."""
        chars = set("".join(page_texts.values()))
        for ss in _sub_sections(record).values():
            for para in _paragraphs(ss["content"]):
                if not is_row(para):
                    assert set(normalise_whitespace(para)) <= chars


# --------------------------------------------------------------------------- #
# Shape: spec §4.1 and §4.2
# --------------------------------------------------------------------------- #


class TestShape:
    def test_three_sections_with_the_spec_sub_sections_in_order(self, record) -> None:
        assert {s["section_id"]: [ss["sub_section_id"] for ss in s["sub_sections"]] for s in record["sections"]} == SPEC_SHAPE

    def test_derived_start_pages_match_the_spec_except_the_one_recorded_discrepancy(self, imp, manifest) -> None:
        derived = {s.spec.sub_section_id: s.start_page for s in imp.sub_sections}
        assert {k: v for k, v in derived.items() if k != "8"} == {k: v for k, v in SPEC_START_PAGES.items() if k != "8"}
        assert derived["8"] == 75 and SPEC_START_PAGES["8"] == 76
        assert manifest["page_map"]["discrepancies"] == [
            {
                "sub_section_id": "8",
                "declared_start_page": 76,
                "derived_start_page": 75,
                "note": "the opening block sits on the page before the declared one",
            }
        ]

    def test_the_two_unlabelled_sub_sections_carry_declared_titles(self, record, manifest) -> None:
        subs = _sub_sections(record)
        assert subs["8"]["title"] == "Participating Organisations"
        assert subs["8"]["content"].startswith("Beneficiary A")
        scorecard = json.loads((REPO / ie.SCORECARD_REL).read_text(encoding="utf-8"))
        heading_1_1 = next(a["af_v6_heading"] for c in scorecard["criteria"] for a in c["aspects"] if a["anchor"] == "1.1")
        assert subs["1.1"]["title"] == heading_1_1
        assert subs["1.1"]["content"].startswith("Introduction, objectives and overview")
        sources = {r["sub_section_id"]: r["title_source"] for r in manifest["page_map"]["sub_sections"]}
        assert sources["1.1"] == "declared" and sources["8"] == "declared"
        assert all(v == "candidate heading" for k, v in sources.items() if k not in ("1.1", "8"))

    def test_numbered_titles_are_the_heading_without_its_number(self, record) -> None:
        subs = _sub_sections(record)
        assert subs["1.2"]["title"] == "Soundness of the proposed methodology"
        assert subs["5"]["title"] == "Network organisation (Fully Sanitized)"
        assert not any(re.match(r"^\d", ss["title"]) for ss in subs.values())

    def test_document_id_is_the_intakes(self, record) -> None:
        intake = read_esr_intake(WORKSPACE, ie.INTAKE_ID)
        assert record["document_id"] == intake.document_id

    def test_the_candidate_is_nowhere_called_the_submitted_version(self, manifest, sources) -> None:
        forbidden = re.compile(r"(?i)\b(the submitted version|as submitted|submitted document|submitted proposal)\b")
        for text in (json.dumps(manifest), json.dumps({k: v for k, v in sources.items() if k != "sources"})):
            assert forbidden.search(text) is None
        assert manifest["candidate"]["is_submitted_document"] is False


# --------------------------------------------------------------------------- #
# Tables: decision 8
# --------------------------------------------------------------------------- #


class TestTables:
    def test_all_17_tables_render(self, imp, manifest, register) -> None:
        assert sum(len(p.tables) for p in imp.pages) == SPEC_TABLES
        assert manifest["tables"]["count"] == SPEC_TABLES
        assert register["derived"]["tables"]["count"] == SPEC_TABLES
        assert manifest["tables"]["every_row_parses"] is True

    def test_every_rendered_row_parses_to_its_tables_column_count(self, record, imp) -> None:
        cols_by_table = {(p.page, t.index): t.cols for p in imp.pages for t in p.tables}
        rows_in_record = [p for ss in _sub_sections(record).values() for p in _paragraphs(ss["content"]) if is_row(p)]
        assert len(rows_in_record) == sum(len(t.rows) for p in imp.pages for t in p.tables) == 88
        rendered = [(p.page, t.index, row) for p in imp.pages for t in p.tables for row in t.rows]
        for (page, index, row), line in zip(rendered, rows_in_record):
            assert parse_row(line) == row
            assert len(parse_row(line)) == cols_by_table[(page, index)]

    def test_rows_are_paragraphs_of_their_own_inside_3_1(self, record) -> None:
        subs = _sub_sections(record)
        rows = [p for p in _paragraphs(subs["3.1"]["content"]) if is_row(p)]
        assert len(rows) == 88
        assert all(not is_row(p) for sid, ss in subs.items() if sid != "3.1" for p in _paragraphs(ss["content"]))
        for caption in ("Table 3.1 b Deliverables List (Sanitized)", "Table 3.1 c Milestones List (Sanitized)",
                        "Table 3.1 d DC Table (Sanitized)", "Table 3.1 e Project Risks (Sanitized)"):
            assert caption in _paragraphs(subs["3.1"]["content"])

    def test_the_header_cells_are_whole_not_split_by_line(self, imp) -> None:
        first = next(t for p in imp.pages for t in p.tables)
        assert first.rows[0][0] == "Numbe r" and first.rows[0][1] == "Deliverable Title"


# --------------------------------------------------------------------------- #
# The ledger: frozen here, every claim a proposal assertion
# --------------------------------------------------------------------------- #


class TestLedger:
    def test_the_record_is_schema_v2(self, record) -> None:
        assert record["schema_id"] == DOCUMENT_SCHEMA_ID_V2
        assert record["state"] == "imported"

    def test_there_are_claims_and_none_is_source_grounded(self, record, manifest) -> None:
        assert record["claims"], "an empty ledger makes decision 6 and decision 15 vacuous"
        assert len(record["claims"]) == manifest["claims"]["count"]
        for c in record["claims"]:
            assert c["evidence_strength"] == "unconfirmed", c["claim_id"]
            assert c["declared_status"] == "Unresolved", c["claim_id"]
            assert c["approval"] == "not_applicable", c["claim_id"]

    def test_every_claim_is_a_sentence_of_its_sub_section(self, record) -> None:
        subs = _sub_sections(record)
        for c in record["claims"]:
            sid = c["claim_id"].rsplit("-c", 1)[0]
            assert c["text"] in subs[sid]["content"], c["claim_id"]
            assert subs[sid] in next(s for s in record["sections"] if s["section_id"] == c["section_id"])["sub_sections"]

    def test_every_span_resolves_to_the_claim_text_in_its_page_source(self, record, sources, manifest) -> None:
        text_by_id = {s["source_id"]: s["text"] for s in sources["sources"]}
        without = 0
        for c in record["claims"]:
            span = c["verified_span"]
            if span is None:
                without += 1
                continue
            assert text_by_id[span["source_id"]][span["start"]:span["end"]] == c["text"], c["claim_id"]
        assert without == manifest["claims"]["without_span"] == len(manifest["claims"]["claims_without_span"])
        assert without <= 1
        for entry in manifest["claims"]["claims_without_span"]:
            assert len(entry["pages"]) > 1, entry

    def test_the_snapshot_builds_over_the_workspace_and_resolves_every_span(self, record) -> None:
        snap = build_snapshot(WORKSPACE)
        by_type: dict[str, int] = {}
        for n in snap.nodes:
            by_type[n["type"]] = by_type.get(n["type"], 0) + 1
        assert by_type["source"] == SPEC_PAGES
        assert by_type["artifact_version"] == 1
        assert by_type["passage"] == 3
        assert by_type["claim"] == len(record["claims"])
        assert by_type["source_span"] == sum(1 for c in record["claims"] if c["verified_span"])
        assert "finding" not in by_type and "assessment" not in by_type

    def test_the_rule_is_named_and_versioned(self, manifest) -> None:
        assert set(manifest["claims"]["rules_matched"]) <= {"quantity", "evidential"}
        assert manifest["versions"]["claim_extraction"]
        assert manifest["claims"]["duplicates_removed"] == 0


# --------------------------------------------------------------------------- #
# Sources: one per page, replayable
# --------------------------------------------------------------------------- #


class TestSources:
    def test_84_page_sources_in_order(self, sources) -> None:
        ids = [s["source_id"] for s in sources["sources"]]
        assert ids == [ie.SOURCE_ID_FORMAT.format(page=p) for p in range(1, SPEC_PAGES + 1)]

    def test_every_page_text_replays_byte_equal(self, sources, page_texts) -> None:
        for s in sources["sources"]:
            assert s["transcription"]["method"] == PAGE_TEXT_METHOD
            assert s["text"] == page_texts[s["resolves_to"]["page"]]
            assert s["resolves_to"]["stored_path"] == ie.CANDIDATE_PDF_REL.as_posix()

    def test_the_manifest_pins_the_source_index_bytes(self, manifest) -> None:
        data = (WORKSPACE / SOURCES_REL).read_bytes()
        assert manifest["sources"]["sha256"] == hashlib.sha256(data).hexdigest()
        assert manifest["sources"]["count"] == SPEC_PAGES


# --------------------------------------------------------------------------- #
# The register's derived half: losses recorded
# --------------------------------------------------------------------------- #


class TestDerivedHalf:
    def test_extraction_losses_are_recorded_and_zero_on_every_page(self, register, manifest) -> None:
        losses = register["derived"]["per_page_extraction_losses"]
        assert losses["pages_with_loss"] == []
        assert losses["total_page_chars"] == losses["total_accounted"] > 100_000
        assert manifest["extraction_losses"] == losses

    def test_zero_figures_recorded(self, register) -> None:
        assert register["derived"]["figures"] == {"images_on_any_page": 0, "pages_with_images": []}

    def test_zero_dependency_strings_recorded_with_the_informal_relations(self, register) -> None:
        kw = register["derived"]["dependency_keyword_counts"]
        assert {kw[k] for k in ("dependenc", "interdepend", "Gantt", "critical path")} == {0}
        assert kw["in WP<n>"] == 4  # spec §2.7, measured again here
        assert kw["build(s/ing) (up)on"] == 1  # spec §2.7's one 'builds on'; the copy writes 'build upon'

    def test_zero_citation_markers_recorded(self, register) -> None:
        assert set(register["derived"]["citation_marker_counts"].values()) == {0}

    def test_body_point_size_distribution_and_what_the_other_size_is(self, register) -> None:
        ps = register["derived"]["body_point_size"]
        assert ps["distribution"] == {"12.0": 117953, "10.0": 1040}
        assert ps["other_sizes_are_bullets_and_spaces_only"] is True

    def test_table_3_1a_flattening_is_measured(self, register) -> None:
        t31a = register["derived"]["table_3_1a"]
        assert t31a["wp_number_blocks"] == 7
        # The copy carries six 'Lead participant' lines for seven work packages; recorded, not repaired.
        assert t31a["label_block_counts"] == {"WP Number:": 7, "WP title:": 7, "Lead participant": 6}
        assert t31a["flattened_to_label_value_blocks"] is True

    def test_character_order_losses_are_counted_as_losses(self, register, manifest) -> None:
        col = register["derived"]["per_page_extraction_losses"]["character_order_losses"]
        assert col["cells"] == 3 == len(manifest["tables"]["cells_not_contiguous_in_page_text"])

    def test_the_derived_half_is_marked_and_names_its_versions_and_manifest(self, register, manifest) -> None:
        d = register["derived"]
        assert d["kind"] == "derived" and d["status"] == "written" and d["declared_status"] == "Confirmed"
        assert d["versions"] == manifest["versions"]
        assert d["import_manifest"] == MANIFEST.relative_to(REPO).as_posix()
        assert d["candidate_sha256"] == manifest["candidate"]["sha256"]

    def test_the_provenance_header_is_untouched_by_pe03(self, register) -> None:
        assert register["ticket"] == "PE-01"
        assert register["provenance"]["kind"] == "declared"
        assert register["provenance"]["current_assessment_artifact"]["is_submitted_document"] is False


# --------------------------------------------------------------------------- #
# Isolation holds after population
# --------------------------------------------------------------------------- #


class TestIsolation:
    def test_no_demo_node_is_reachable_from_the_populated_workspace(self) -> None:
        demo = build_snapshot(REPO)
        real = build_snapshot(WORKSPACE)
        assert {n["id"] for n in real.nodes}.isdisjoint({n["id"] for n in demo.nodes})
        assert all((WORKSPACE / rel).is_file() for rel in real.inputs)

    def test_the_esr_is_not_a_source_and_no_source_carries_esr_content(self, sources) -> None:
        for s in sources["sources"]:
            assert "ESR" not in s["resolves_to"]["stored_path"]
        text = json.dumps(sources)
        for token in (r"\b85\.80\b", r"\b4\.20\b", r"\b4\.50\b"):
            assert re.search(token, text) is None, token
