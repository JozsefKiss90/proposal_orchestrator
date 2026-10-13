"""The committed authority source index and equivalence matrix (V09, 2026-10-12).

Five groups:

* **The renderer.** ``--check`` is a byte-equal replay, the matrix check is
  green, every binding is the hash of the file on disk, and the matrix is bound
  to the index it was written beside.
* **The index.** Twelve documents obtained and four 2025 documents recorded
  absent, each with the rows it would settle, derived from the rows themselves.
  No entry is authenticated by an issuing body, which is why no row is
  Confirmed.
* **The rows.** Every quote is re-derived from the page it cites, through the
  same extraction route the evaluation bundle used. The ten aspect headings and
  the eleven appendix cross-references are reconciled against the records they
  come from. Every sourced row has 2025 evidence, every defaulted row names the
  rule its defaulting affects, and every unsourced row names the document that
  would settle it.
* **The derivations refuse.** Each of the six refusals is exercised against the
  real documents with one record mutated: a quote that is not on its page, the
  page rules breaking, an applicability tag turning up in an application form,
  the total formula stopping reproducing the recorded total, the call identifier
  stopping being Assumed, and a 2025 document arriving at its destination.
* **Scope.** The form-equivalence record is cited from the one area it measured
  and nowhere else, and both artifacts sit outside the dev-graph root.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

import harness.commands.authority_matrix as cmd
from harness import authority_matrix as am
from runner.paths import find_repo_root
from runner.source_index import normalise_whitespace, read_page_text
from tools import author_msca_dn_authority_matrix as amx

REPO = find_repo_root()

pytestmark = pytest.mark.skipif(
    not (REPO / amx.MATRIX_REL).is_file(), reason="the equivalence matrix is absent"
)

#: The eight areas ticket V09's second acceptance criterion names.
TICKET_AREAS = (
    "criteria",
    "weights",
    "thresholds",
    "evaluator_instructions",
    "variant",
    "section_mapping",
    "appendix_mapping",
    "scoring_assumption",
)


def _read(rel: Path) -> dict:
    return json.loads((REPO / rel).read_text(encoding="utf-8-sig"))


@pytest.fixture(scope="module")
def index() -> am.SourceIndex:
    return am.load_source_index(REPO / amx.INDEX_REL, repo_root=REPO)


@pytest.fixture(scope="module")
def matrix() -> am.Matrix:
    return am.load_matrix(REPO / amx.MATRIX_REL, repo_root=REPO)


@pytest.fixture(scope="module")
def scorecard() -> dict:
    return _read(amx.SCORECARD_REL)


@pytest.fixture(scope="module")
def appendix() -> dict:
    return _read(amx.APPENDIX_REL)


@pytest.fixture(scope="module")
def esr() -> dict:
    return _read(amx.ESR_REL)


# --------------------------------------------------------------------------- #
# 1. The renderer
# --------------------------------------------------------------------------- #


class TestTheRenderer:
    def test_the_authoring_tool_and_the_reader_declare_one_schema_each(self):
        # Deliberate double entry: tools/ may not import harness/, so each side
        # carries its own copy of the two schema strings.
        assert amx.SCHEMA_INDEX == am.SCHEMA_INDEX
        assert amx.SCHEMA_MATRIX == am.SCHEMA_MATRIX

    def test_check_is_a_byte_equal_replay(self):
        assert amx.check(REPO) == []

    def test_the_matrix_check_is_green(self, matrix, index):
        result = am.check(matrix, index, REPO)
        assert result.green, "\n".join(result.lines())

    def test_the_command_exits_zero_and_the_readings_are_up_to_date(self, capsys):
        code = cmd.main(["--matrix", amx.MATRIX_REL.as_posix(), "--check"])
        out = capsys.readouterr().out
        assert "matrix check: green" in out
        assert code == 0, out

    def test_the_matrix_binds_the_index_on_disk(self, matrix):
        path = REPO / matrix.index_path
        assert matrix.index_path == amx.INDEX_REL.as_posix()
        assert matrix.index_sha256 == hashlib.sha256(path.read_bytes()).hexdigest()

    def test_both_readings_are_committed_beside_their_declarations(self):
        for rel in (amx.INDEX_REL, amx.MATRIX_REL):
            assert (REPO / rel).with_suffix(".md").is_file()

    def test_both_declarations_are_pending_operator_review(self, matrix, index):
        assert matrix.review_state == "agent_drafted_pending_operator_review"
        assert index.review_state == "agent_drafted_pending_operator_review"

    def test_neither_declaration_claims_confirmed_status(self, matrix, index):
        assert matrix.declared_status == "Inferred"
        assert index.declared_status == "Inferred"


# --------------------------------------------------------------------------- #
# 2. The index
# --------------------------------------------------------------------------- #


class TestTheIndex:
    def test_fifteen_documents_are_obtained_and_one_is_not(self, index):
        assert len(index.sources) == 16
        assert len(index.obtained()) == 15
        assert len(index.missing_required()) == 1

    def test_every_obtained_entry_pins_the_file_on_disk(self, index):
        for source in index.obtained():
            path = REPO / source.path
            assert path.is_file(), source.path
            assert source.sha256 == hashlib.sha256(path.read_bytes()).hexdigest(), source.path

    def test_no_file_sits_at_an_unobtained_destination(self, index):
        for source in index.missing_required():
            assert not (REPO / source.path).exists(), source.path

    def test_the_one_absence_is_the_submission_binding(self, index):
        """What is missing is no longer an authority document.

        The three 2025 authorities the earlier index declared absent are held.
        The fourth, a separate call document, is not needed: the work
        programme part carries the call's own conditions. What remains absent
        is the record that would bind this submission to a call.
        """
        (absent,) = index.missing_required()
        assert absent.path == amx.SUBMISSION_ACK_REL.as_posix()
        assert absent.cls == "submission_record"
        assert absent.source_authenticity == "not_applicable"
        assert absent.sha256 == ""
        assert "call_document" not in {s.cls for s in index.sources}

    def test_no_entry_is_authenticated_by_an_issuing_body(self, index):
        # The reason no row may declare Confirmed. If this ever stops holding,
        # the Confirmed rule below has to be revisited rather than quietly
        # satisfied.
        assert not [s.path for s in index.sources if s.authentication == "issuer_hash_confirmed"]

    def test_the_2025_authorities_are_held_as_well_as_the_submission_records(self, index):
        historical = [s for s in index.by_era("historical") if s.obtained]
        held = {s.path for s in historical}
        for rel in (
            amx.AF_V5_REL,
            amx.HIST_WP_REL,
            amx.HIST_ANNEXES_REL,
            amx.HIST_EF_REL,
        ):
            assert rel.as_posix() in held, rel
        assert {s.cls for s in historical} == {
            "instrument_application_form",
            "work_programme",
            "programme_guidance",
            "instrument_evaluation_form",
            "evaluation_output",
            "submission_record",
        }

    def test_would_settle_is_derived_from_the_rows(self, index, matrix):
        by_path = index.by_path()
        for row in matrix.rows:
            for path in row.would_be_settled_by:
                assert path in by_path, f"{row.id} names an undeclared document"
                assert not by_path[path].obtained, f"{row.id} names an obtained document"
                assert row.id in by_path[path].would_settle, f"{row.id} missing from {path}"
        for source in index.missing_required():
            for row_id in source.would_settle:
                row = next(r for r in matrix.rows if r.id == row_id)
                assert source.path in row.would_be_settled_by

    def test_the_one_gap_settles_the_one_assumed_row(self, index):
        (absent,) = index.missing_required()
        assert absent.would_settle == ("CI-01",)

    def test_the_three_questions_are_answered_separately(self, index):
        """Every obtained entry answers all three, and none stands in for another.

        The retrieved documents are the point: their bytes are hashed in this
        tree like every other file, so byte integrity alone would read them as
        no better evidenced than a file of unknown origin.
        """
        retrieved = {
            amx.HIST_WP_REL.as_posix(),
            amx.HIST_ANNEXES_REL.as_posix(),
            amx.HIST_EF_REL.as_posix(),
        }
        for source in index.obtained():
            assert source.authentication in am.AUTHENTICATIONS
            assert source.source_authenticity in am.SOURCE_AUTHENTICITIES
            assert source.historical_applicability in am.HISTORICAL_APPLICABILITIES
            if source.path in retrieved:
                # Origin recorded, byte integrity still only computed here.
                assert source.authentication == "computed_only"
                assert source.origin_recorded
                assert source.provenance is not None
                assert source.provenance.official_url
                assert source.provenance.retrieved_on

    def test_the_corroborated_documents_name_bytes_that_are_this_file(self, index):
        """A second copy is evidence only if it is the same bytes."""
        corroborated = [
            s for s in index.obtained() if s.source_authenticity == "independently_corroborated"
        ]
        assert len(corroborated) == 3
        for source in corroborated:
            assert source.provenance is not None
            copies = source.provenance.corroborating_copies
            captures = source.provenance.archive_captures
            assert copies or captures, source.path
            for copy in copies:
                assert copy.sha256 == source.sha256, source.path

    def test_the_archived_form_does_not_claim_its_place_in_the_call(self, index):
        """The one retrieval that cannot settle the third question.

        Its address no longer serves these bytes, so one archive is the only
        witness, and captures bracket the call window without closing it.
        """
        form = index.by_path()[amx.HIST_EF_REL.as_posix()]
        assert form.source_authenticity == "retrieved_from_web_archive"
        assert form.historical_applicability == "bracketed_not_conclusive"
        assert not form.applicability_conclusive
        assert form.provenance is not None
        assert len(form.provenance.archive_captures) == 3
        # One digest across all three: one witness, observed three times.
        assert len({c.digest for c in form.provenance.archive_captures}) == 1

    def test_no_row_citing_the_archived_form_declares_confirmed(self, matrix, index):
        """The teeth of the third axis, read over the committed matrix."""
        bracketed = {
            s.path for s in index.obtained() if not s.applicability_conclusive
        }
        for row in matrix.rows:
            if {c.source for c in row.citations} & bracketed:
                assert row.declared_status != "Confirmed", row.id

    def test_every_vouched_entry_says_where_that_is_recorded(self, index):
        """A rank above computed_only names a field, and the field still says it."""
        vouched = [
            s for s in index.obtained() if s.authentication in am.AUTHENTICATIONS_NEEDING_A_BASIS
        ]
        assert [s.path for s in vouched] == [
            amx.ESR_REL.as_posix(),
            amx.FIDELITY_REL.as_posix(),
        ]
        declared = {source.rel.as_posix(): source.basis for source in amx.OBTAINED}
        for source in vouched:
            basis = declared[source.path]
            assert basis is not None
            assert basis.pointer in source.authentication_basis
            node = _read(Path(source.path))
            for segment in basis.pointer.split("/"):
                node = node[segment]
            assert basis.must_contain.lower() in str(node).lower()

    def test_every_pdf_entry_declares_its_page_count(self, index):
        for source in index.obtained():
            if source.path.endswith(".pdf"):
                assert source.pages and source.pages > 0, source.path
            else:
                assert source.pages is None, source.path


# --------------------------------------------------------------------------- #
# 3. The rows
# --------------------------------------------------------------------------- #


class TestTheRows:
    def test_the_required_areas_are_the_eight_the_ticket_names(self, matrix):
        assert matrix.required_areas == TICKET_AREAS
        assert amx.REQUIRED_AREAS == TICKET_AREAS

    def test_every_required_area_is_covered(self, matrix):
        for area in TICKET_AREAS:
            assert matrix.rows_in(area), area

    def test_the_only_area_beyond_the_required_set_is_the_call_identity(self, matrix):
        extra = [a for a in matrix.areas() if a not in matrix.required_areas]
        assert extra == ["call_identity"]

    def test_the_verdicts_are_the_committed_distribution(self, matrix):
        counts = {v: len(rows) for v, rows in matrix.rows_by_verdict().items()}
        assert counts == {
            "equivalent": 18,
            "differs": 2,
            "unresolved": 2,
            "era_neutral": 5,
        }
        assert len(matrix.rows) == 27

    def test_no_row_is_defaulted_any_more(self, matrix):
        """The six defaultings are re-derived, not relabelled.

        Each one is now equivalent because a 2025 document states the rule,
        and the next test requires every such row to cite one.
        """
        assert "defaulted" not in matrix.rows_by_verdict()

    def test_no_row_declares_confirmed(self, matrix):
        # Criterion-adjacent, and enforced by the check: every source is
        # computed_only or operator_supplied, so Confirmed is unavailable.
        assert not [r.id for r in matrix.rows if r.declared_status == "Confirmed"]

    def test_every_sourced_row_cites_an_obtained_2025_document(self, matrix, index):
        by_path = index.by_path()
        for row in matrix.rows:
            if not row.asserts_a_relation:
                continue
            historical = [
                c
                for c in row.citations
                if by_path[c.source].era == "historical" and by_path[c.source].obtained
            ]
            assert historical, f"{row.id} asserts {row.verdict} with no 2025 citation"

    def test_every_call_wide_relation_rests_on_a_2025_call_document(self, matrix, index):
        by_path = index.by_path()
        for row in matrix.rows:
            if not row.asserts_a_relation or row.settles != "call_wide":
                continue
            carriers = [
                c.source
                for c in row.citations
                if by_path[c.source].era == "historical"
                and by_path[c.source].obtained
                and not by_path[c.source].submission_scoped
            ]
            assert carriers, f"{row.id} claims a call-wide rule on submission evidence"

    def test_a_defaulted_row_would_still_have_to_name_its_rule_and_its_risk(self, matrix):
        """The invariant stays, over an empty set for now.

        It is the rule a future defaulting is held to, not a statement that
        one exists.
        """
        for row in matrix.rows_by_verdict().get("defaulted", ()):
            assert row.defaulting is not None
            assert row.defaulting.affected_rule.strip()
            assert row.defaulting.risk.strip()
            assert row.defaulting.carried_from.strip()

    def test_every_unresolved_row_names_its_gap(self, matrix):
        """A row that settles nothing says what is missing.

        One of the two names a document that would settle it. The other
        cannot: what would settle EI-02 is a statement from the issuing body
        about a version it no longer publishes, which is not a file this
        repository has a destination for. That row carries a limitation
        instead, and leaving it unnamed is what this forbids.
        """
        for row in matrix.rows:
            if row.verdict in ("defaulted", "unresolved"):
                assert row.would_be_settled_by or row.limitation.strip(), row.id

    def test_the_two_differences_are_the_part_b2_section_and_the_printed_total(self, matrix):
        by_id = {r.id: r for r in matrix.rows_by_verdict()["differs"]}
        assert set(by_id) == {"SM-03", "TH-06"}
        assert "section 11" in by_id["SM-03"].difference
        assert "vacuous" in by_id["SM-03"].consequence
        # The form's own total differs; the rule that governed did not.
        assert "out of 15" in by_id["TH-06"].difference
        assert "superseded" in by_id["TH-06"].difference

    def test_every_era_neutral_row_says_why_no_era_states_it(self, matrix):
        for row in matrix.rows_by_verdict()["era_neutral"]:
            assert row.why_era_neutral.strip()
            assert not row.asserts_a_relation

    def test_every_row_tells_the_historical_profile_what_to_do(self, matrix):
        for row in matrix.rows:
            assert row.consequence.strip(), row.id

    def test_every_document_quote_is_on_the_page_it_cites(self, matrix, index):
        by_path = index.by_path()
        checked = 0
        for row in matrix.rows:
            for citation in row.citations:
                if citation.page is None:
                    continue
                source = by_path[citation.source]
                assert citation.page <= (source.pages or 0)
                text = read_page_text(REPO / citation.source, citation.page)
                assert normalise_whitespace(citation.quote) in text, (
                    f"{row.id}: {citation.source} page {citation.page}"
                )
                checked += 1
        # Non-vacuous: the ten aspect headings, the eleven appendix
        # cross-references and the fourteen hand-named passages of the scoring,
        # page-cap, mode and Part B2 rows.
        assert checked == 74

    def test_both_criteria_tables_carry_exactly_the_scorecard_anchors(self, scorecard):
        """SM-01's second direction, re-measured off the two forms."""
        declared = {
            aspect["anchor"]
            for criterion in scorecard["criteria"]
            for aspect in criterion["aspects"]
        }
        for rel in (amx.AF_V5_REL, amx.AF_V6_REL):
            document = amx._Document(REPO, rel)
            pages = amx._table_pages(scorecard, document)
            assert pages, rel.as_posix()
            assert amx._anchors_on(document, pages) == declared, rel.as_posix()
            # The span is the whole table: neither bounding page carries an anchor.
            bounding = [pages[0] - 1, pages[-1] + 1]
            assert not amx._anchors_on(document, bounding), rel.as_posix()

    def test_the_resolution_is_decided_by_a_score_no_half_mark_rule_could_award(self, matrix):
        """The two 2025 authorities disagree, and the result decides.

        The maximum stays a separate claim from the resolution, which is the
        split the earlier matrix got wrong in the other direction.
        """
        (maximum,) = [r for r in matrix.rows if r.id == "TH-04"]
        (resolution,) = [r for r in matrix.rows if r.id == "TH-05"]
        assert maximum.verdict == "equivalent"
        assert "resolution" not in maximum.historical_value
        assert resolution.verdict == "equivalent"
        assert resolution.defaulting is None
        assert "half mark" in resolution.historical_value
        # Both sides of the 2025 conflict are cited, not just the one that won.
        cited = {c.source for c in resolution.citations}
        assert amx.HIST_WP_REL.as_posix() in cited
        assert amx.HIST_EF_REL.as_posix() in cited

    def test_the_ten_aspect_headings_are_cited_one_each(self, matrix, scorecard):
        (row,) = [r for r in matrix.rows if r.id == "SM-01"]
        quotes = {c.quote for c in row.citations}
        headings = {
            normalise_whitespace(a["af_v6_heading"])
            for c in scorecard["criteria"]
            for a in c["aspects"]
        }
        assert quotes == headings
        assert len(row.citations) == 10
        assert {c.source for c in row.citations} == {amx.AF_V5_REL.as_posix()}

    def test_the_appendix_cross_references_are_cited_once_each(self, matrix, appendix):
        (row,) = [r for r in matrix.rows if r.id == "AM-01"]
        document = [c for c in row.citations if c.page is not None]
        declared = {
            normalise_whitespace(s["quote"])
            for r in appendix["rows"]
            for s in r.get("sources", ())
        }
        assert {c.quote for c in document} == declared
        assert len(document) == 11
        assert {c.source for c in document} == {amx.AF_V5_REL.as_posix()}

    def test_the_weights_row_is_measured_against_both_records(self, matrix, esr, scorecard):
        (row,) = [r for r in matrix.rows if r.id == "WT-01"]
        assert row.verdict == "equivalent"
        recorded = [c["weight_pct"] for c in esr["evaluation_result"]["criteria"]]
        declared = [c["weight_pct"] for c in scorecard["criteria"]]
        assert recorded == declared == [50, 30, 20]
        assert len(row.measurements) == 6

    def test_the_call_identifier_row_is_unresolved(self, matrix):
        (row,) = [r for r in matrix.rows if r.id == "CI-01"]
        assert row.verdict == "unresolved"
        assert row.declared_status == "Assumed"
        assert row.limitation.strip()
        assert "never Confirmed" in row.consequence


# --------------------------------------------------------------------------- #
# 4. The derivations refuse
# --------------------------------------------------------------------------- #


class _StubDocument:
    """Just enough of a document for the tag refusal."""

    def __init__(self, rel: str, tagged: bool) -> None:
        self.rel = rel
        self._tagged = tagged

    def occurrences(self, needle: str) -> tuple[int, ...]:
        return (7,) if self._tagged else ()


class TestTheDerivationsRefuse:
    @pytest.fixture(scope="class")
    def v5(self) -> amx._Document:
        return amx._Document(REPO, amx.AF_V5_REL)

    @pytest.fixture(scope="class")
    def v6(self) -> amx._Document:
        return amx._Document(REPO, amx.AF_V6_REL)

    def test_a_quote_not_on_its_page_refuses(self, v5):
        with pytest.raises(amx.AuthorityAuthoringError, match="does not carry the quote"):
            amx._verified(v5, 24, "a sentence this form does not contain", "nowhere")

    def test_a_passage_not_in_a_prose_record_refuses(self):
        with pytest.raises(amx.AuthorityAuthoringError, match="does not carry the passage"):
            amx._verified_text(REPO, amx.SPEC_REL, "seven samples per criterion", "nowhere")

    def test_the_last_occurrence_rule_breaking_refuses(self, scorecard, v5, v6):
        mutated = copy.deepcopy(scorecard)
        mutated["criteria"][0]["aspects"][0]["af_v6_heading_page"] = 3
        with pytest.raises(amx.AuthorityAuthoringError, match="last-occurrence rule"):
            amx._aspect_heading_citations(mutated, v5, v6)

    def test_a_heading_that_leaves_the_2025_form_refuses(self, scorecard, v5, v6):
        mutated = copy.deepcopy(scorecard)
        mutated["criteria"][0]["aspects"][0]["af_v6_heading"] = "A heading in neither form"
        with pytest.raises(amx.AuthorityAuthoringError, match="heading not found"):
            amx._aspect_heading_citations(mutated, v5, v6)

    def test_the_first_occurrence_rule_breaking_refuses(self, appendix, v5, v6):
        mutated = copy.deepcopy(appendix)
        mutated["rows"][0]["sources"][0]["page"] = 2
        with pytest.raises(amx.AuthorityAuthoringError, match="first-occurrence rule"):
            amx._appendix_quote_citations(mutated, v5, v6)

    def test_an_applicability_tag_in_an_application_form_refuses(self):
        clean = _StubDocument("clean.pdf", tagged=False)
        tagged = _StubDocument("tagged.pdf", tagged=True)
        amx._refuse_if_tagged(clean, clean)
        with pytest.raises(amx.AuthorityAuthoringError, match="carries an .OPTION for tag"):
            amx._refuse_if_tagged(clean, tagged)

    def test_the_real_forms_carry_no_applicability_tag(self, v5, v6):
        # The measurement row EI-04's reasoning rests on: the tag grammar is the
        # evaluation form's alone, so the form-equivalence record cannot reach it.
        amx._refuse_if_tagged(v5, v6)

    def test_the_total_formula_reproduces_the_recorded_total(self, esr, scorecard):
        parts = amx._total_reproduces(esr, scorecard)
        assert round(sum(parts.values()), 6) == esr["evaluation_result"]["total"]

    def test_a_total_the_formula_misses_refuses(self, esr, scorecard):
        mutated = copy.deepcopy(esr)
        mutated["evaluation_result"]["total"] = 90.0
        with pytest.raises(amx.AuthorityAuthoringError, match="weighted total formula yields"):
            amx._total_reproduces(mutated, scorecard)

    def test_a_weight_the_two_records_disagree_on_refuses(self, esr, scorecard):
        mutated = copy.deepcopy(esr)
        mutated["evaluation_result"]["criteria"][0]["weight_pct"] = 40
        with pytest.raises(amx.AuthorityAuthoringError, match="the ESR records weight"):
            amx._total_reproduces(mutated, scorecard)

    def test_a_criterion_the_scorecard_does_not_declare_refuses(self, esr, scorecard):
        mutated = copy.deepcopy(esr)
        mutated["evaluation_result"]["criteria"][0]["criterion_id"] = "novelty"
        with pytest.raises(amx.AuthorityAuthoringError, match="which the scorecard does not"):
            amx._total_reproduces(mutated, scorecard)

    def test_a_call_identifier_that_stops_being_assumed_refuses(self):
        record = {"declared_values": {"historical_call_id": {"declared_status": "Confirmed"}}}
        with pytest.raises(amx.AuthorityAuthoringError, match="no longer holds"):
            amx._declared_assumed(
                record, ("declared_values", "historical_call_id", "declared_status"), "a record"
            )

    def test_an_anchor_no_form_prints_refuses(self, scorecard, v5, v6):
        """The set equality SM-01 claims is measured, so losing it refuses."""
        mutated = copy.deepcopy(scorecard)
        mutated["criteria"][2]["aspects"][1]["anchor"] = "4.1"
        with pytest.raises(amx.AuthorityAuthoringError, match="no longer equal"):
            amx._refuse_unless_anchor_sets_agree(mutated, v5, v6)

    def test_an_aspect_row_dropped_from_the_table_refuses(self, scorecard, v5, v6):
        """A shorter aspect list shortens the span, and the rest spills past it.

        Which is the guard that matters: the pages searched are located from
        the aspect list, so without a bound an eleventh row could sit on a page
        the list never points at.
        """
        mutated = copy.deepcopy(scorecard)
        mutated["criteria"][2]["aspects"] = mutated["criteria"][2]["aspects"][:1]
        with pytest.raises(amx.AuthorityAuthoringError, match="reaches past the span"):
            amx._refuse_unless_anchor_sets_agree(mutated, v5, v6)

    def test_the_real_forms_agree_on_the_anchors(self, scorecard, v5, v6):
        assert len(amx._refuse_unless_anchor_sets_agree(scorecard, v5, v6)) == 10

    def test_a_vouched_authentication_with_no_basis_refuses(self, tmp_path):
        """The author refuses the rank the reader would report."""
        bare = amx._Obtained(
            rel=amx.ESR_REL,
            cls="evaluation_output",
            era="historical",
            authentication="operator_supplied",
            role="immutable_evidence",
            version="",
            states="an entry claiming a voucher and recording none",
        )
        with pytest.raises(amx.AuthorityAuthoringError, match="declares no basis"):
            amx._resolved_basis(REPO, bare)

    def test_a_basis_whose_pointer_stops_resolving_refuses(self, tmp_path):
        moved = amx._Obtained(
            rel=amx.ESR_REL,
            cls="evaluation_output",
            era="historical",
            authentication="operator_supplied",
            role="immutable_evidence",
            version="",
            states="an entry whose record has moved underneath it",
            basis=amx._Basis(
                pointer="authored_by/who",
                must_contain="operator",
                wording="the field that is no longer there",
            ),
        )
        with pytest.raises(amx.AuthorityAuthoringError, match="does not resolve"):
            amx._resolved_basis(REPO, moved)

    def test_a_record_that_stops_saying_it_refuses(self):
        reworded = amx._Obtained(
            rel=amx.ESR_REL,
            cls="evaluation_output",
            era="historical",
            authentication="operator_supplied",
            role="immutable_evidence",
            version="",
            states="an entry whose record no longer names the operator",
            basis=amx._Basis(
                pointer="authored_by",
                must_contain="an issuing body's own hash",
                wording="a provenance the record does not state",
            ),
        )
        with pytest.raises(amx.AuthorityAuthoringError, match="no longer says"):
            amx._resolved_basis(REPO, reworded)

    def test_a_basis_on_a_rank_that_claims_nothing_refuses(self):
        overclaimed = amx._Obtained(
            rel=amx.SCORECARD_REL,
            cls="derived_configuration",
            era="current",
            authentication="computed_only",
            role="tracked_input",
            version="",
            states="an entry recording a basis for a rank that vouches for nothing",
            basis=amx._Basis(pointer="scoring", must_contain="", wording="unnecessary"),
        )
        with pytest.raises(amx.AuthorityAuthoringError, match="claims no voucher"):
            amx._resolved_basis(REPO, overclaimed)

    def test_a_copy_whose_hash_is_not_this_file_refuses(self):
        source = amx._Obtained(
            rel=amx.HIST_WP_REL,
            cls="work_programme",
            era="historical",
            authentication="computed_only",
            role="immutable_evidence",
            version="",
            states="a work programme",
            authenticity="independently_corroborated",
            authenticity_basis="a second host served the same bytes",
            provenance=amx._Provenance(
                official_url="https://example.invalid/a.pdf",
                retrieved_on="2026-10-13",
                copies=(amx._Copy(url="https://example.invalid/b.pdf", sha256="0" * 64),),
            ),
        )
        with pytest.raises(amx.AuthorityAuthoringError, match="corroborates nothing"):
            amx._refuse_a_copy_that_is_not_this_file(source, "1" * 64)

    def test_an_authenticity_claiming_evidence_with_no_basis_refuses(self):
        source = amx._Obtained(
            rel=amx.HIST_WP_REL,
            cls="work_programme",
            era="historical",
            authentication="computed_only",
            role="immutable_evidence",
            version="",
            states="a work programme",
            authenticity="retrieved_from_official_url",
        )
        with pytest.raises(amx.AuthorityAuthoringError, match="declares no basis"):
            amx._refuse_an_unevidenced_rank(source)

    def test_a_rank_its_provenance_does_not_carry_refuses(self):
        source = amx._Obtained(
            rel=amx.HIST_EF_REL,
            cls="instrument_evaluation_form",
            era="historical",
            authentication="computed_only",
            role="immutable_evidence",
            version="2.0",
            states="an evaluation form",
            applicability="bracketed_not_conclusive",
            applicability_basis="captures surround the window",
        )
        with pytest.raises(amx.AuthorityAuthoringError, match="needs the archive captures"):
            amx._refuse_an_unevidenced_rank(source)

    def test_a_result_of_only_half_marks_cannot_say_which_resolution_applied(self):
        """The refusal row TH-05 rests on.

        If every recorded score were also a half mark, both 2025 rules would
        fit the result and the row would be reading an absence of difference
        as agreement.
        """
        esr = {
            "evaluation_result": {
                "criteria": [
                    {"criterion_id": "excellence", "score": 4.5},
                    {"criterion_id": "impact", "score": 4.0},
                ]
            }
        }
        with pytest.raises(amx.AuthorityAuthoringError, match="whole or half mark"):
            amx._refuse_unless_a_score_rules_out_half_marks(esr)

    def test_an_aspect_the_2025_form_groups_elsewhere_refuses(self, scorecard):
        """Presence is not grouping.

        All ten texts could be in the document and sit under the wrong
        criterion, which is the claim the row actually makes.
        """
        src = amx._records(REPO)
        moved = json.loads(json.dumps(scorecard))
        # Give criterion 1 an aspect whose text lives in criterion 3's section.
        third = scorecard["criteria"][2]["aspects"][0]
        moved["criteria"][0]["aspects"] = list(moved["criteria"][0]["aspects"]) + [third]
        with pytest.raises(amx.AuthorityAuthoringError, match="does not sit under"):
            amx._refuse_unless_aspects_group_the_same_way(moved, src.hist_ef)

    def test_an_aspect_absent_from_the_2025_form_refuses(self, scorecard):
        src = amx._records(REPO)
        absent = json.loads(json.dumps(scorecard))
        absent["criteria"][0]["aspects"][0]["text"] = "a sentence no form carries"
        with pytest.raises(amx.AuthorityAuthoringError, match="is not in the document"):
            amx._refuse_unless_aspects_group_the_same_way(absent, src.hist_ef)

    def test_a_document_arriving_at_its_destination_refuses(self, tmp_path):
        amx._refuse_present_destinations(tmp_path)
        target = tmp_path / amx.SUBMISSION_ACK_REL
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"%PDF-1.7\n")
        with pytest.raises(amx.AuthorityAuthoringError, match="yet a file is there"):
            amx._refuse_present_destinations(tmp_path)


# --------------------------------------------------------------------------- #
# 5. Scope
# --------------------------------------------------------------------------- #


class TestTheSuccession:
    """What the 2026-10-12 pair is now, and what must stay true of it.

    A correction to an index is a successor index, which the superseded index
    says of itself. So the earlier pair is evidence, and evidence its own
    reader can no longer open is evidence nobody can check.
    """

    def test_the_superseded_declarations_are_still_in_the_tree(self):
        for rel in (amx.PRIOR_INDEX_REL, amx.PRIOR_MATRIX_REL):
            assert (REPO / rel).is_file(), rel

    def test_the_superseded_pair_still_loads_and_still_checks_green(self):
        index = am.load_source_index(REPO / amx.PRIOR_INDEX_REL, REPO)
        matrix = am.load_matrix(REPO / amx.PRIOR_MATRIX_REL, REPO)
        assert index.schema == "authority_source_index/1"
        report = am.check(matrix, index, REPO)
        assert report.green, report.lines()

    def test_the_earlier_index_reads_as_declaring_no_origins(self):
        """What a version-1 entry means under the three axes.

        It declared none of them, so every entry must read as a held file with
        no recorded origin. Reading one as corroborated would be the successor
        lending its evidence backwards.
        """
        index = am.load_source_index(REPO / amx.PRIOR_INDEX_REL, REPO)
        for source in index.obtained():
            assert source.source_authenticity == "unrecorded"
            assert source.provenance is None

    def test_both_successors_name_their_predecessor_by_hash(self, index, matrix):
        for record, rel in ((index, amx.PRIOR_INDEX_REL), (matrix, amx.PRIOR_MATRIX_REL)):
            assert rel.as_posix() in record.supersedes
            assert hashlib.sha256((REPO / rel).read_bytes()).hexdigest() in record.supersedes

    def test_the_successor_is_a_second_record_and_not_an_edit(self, index, matrix):
        assert index.source != amx.PRIOR_INDEX_REL.as_posix()
        assert matrix.source != amx.PRIOR_MATRIX_REL.as_posix()
        assert index.authored_on == amx.AUTHORED_ON
        assert matrix.authored_on == amx.AUTHORED_ON


class TestScope:
    def test_the_form_equivalence_record_settles_section_mapping_alone(self, index):
        (source,) = [s for s in index.sources if s.scope_restrictions]
        assert source.path == amx.SCORECARD_REL.as_posix()
        (restriction,) = source.scope_restrictions
        assert restriction.field_prefix == "provenance/v5_equivalence"
        assert restriction.settles_areas == ("section_mapping",)

    def test_it_is_cited_from_that_area_and_nowhere_else(self, matrix, index):
        (source,) = [s for s in index.sources if s.scope_restrictions]
        citing = [
            (row.id, row.area)
            for row in matrix.rows
            for c in row.citations
            if c.source == source.path and source.restriction_for(c.field) is not None
        ]
        assert citing == [("SM-02", "section_mapping")]

    def test_the_appendix_row_does_not_lean_on_it(self, matrix):
        # Criterion 5 made concrete: the record measured headings, tables, caps
        # and section numbering, not the instructional sentences the appendix
        # mapping routes on. AM-01 carries its own measurement instead.
        (row,) = [r for r in matrix.rows if r.id == "AM-01"]
        assert not [c for c in row.citations if "v5_equivalence" in c.field]

    def test_a_restricted_citation_from_another_area_would_be_reported(self, matrix, index):
        # The negative case over the committed index, so the restriction is not
        # merely declared.
        trespass = am.Row(
            id="X-01",
            area="thresholds",
            rule="a threshold read off the form-equivalence record",
            affects="a number",
            verdict="defaulted",
            settles="call_wide",
            declared_status="Assumed",
            status_basis="synthetic",
            consequence="synthetic",
            citations=(
                am.Citation(
                    source=amx.SCORECARD_REL.as_posix(),
                    field="provenance/v5_equivalence/statement",
                    states="read as settling a threshold",
                ),
            ),
            defaulting=am.Defaulting(
                carried_from="synthetic", affected_rule="synthetic", risk="synthetic"
            ),
        )
        probe = am.Matrix(
            name=matrix.name,
            subject=matrix.subject,
            authored_on=matrix.authored_on,
            purpose=matrix.purpose,
            review_state=matrix.review_state,
            declared_status=matrix.declared_status,
            supersedes=matrix.supersedes,
            uncertainties=matrix.uncertainties,
            required_areas=("thresholds",),
            index_path=matrix.index_path,
            index_sha256=matrix.index_sha256,
            rows=(trespass,),
            source=matrix.source,
        )
        result = am.check(probe, index, REPO)
        assert len(result.citations_outside_their_declared_scope) == 1
        assert "cited from area thresholds" in result.citations_outside_their_declared_scope[0]

    def test_both_artifacts_sit_outside_the_dev_graph_root(self):
        # The matrix quotes the 2025 evaluation's recorded figures. It holds the
        # position the ESR record already holds: outside workspaces/, so no
        # snapshot reads it and it cannot reach an evidence pack.
        for rel in (amx.INDEX_REL, amx.MATRIX_REL):
            assert not rel.as_posix().startswith("workspaces/")
            assert rel.as_posix().startswith("docs/tier4_orchestration_state/msca_dn/")

    def test_the_matrix_declares_its_isolation_and_its_authority(self):
        document = _read(amx.MATRIX_REL)
        assert "outside the dev-graph root" in document["isolation_note"]
        assert document["advisory"] is True
        assert document["blocking"] is False
        assert "closes no gate" in document["authority_note"]
