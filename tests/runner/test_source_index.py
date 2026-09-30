"""The Tier 3 source-index verifier.

`runner/source_index.py` enforces one rule: a source carries verbatim text only
when that text can be re-derived from a file stored in this repository, byte for
byte. Everything else is a reference with no text and therefore no span.

The rule matters because a source record is the one place in Tier 3 where an
unevidenced claim can be dressed as an evidenced one. Write a plausible citation,
invent a quotation, point a span at it, and the dev-graph snapshot builder reports
a grounded claim that no document supports. The builder cannot catch that — it has
no way to know whether the text is real — so these tests hold the checks that can.

Every test here feeds the verifier a *broken* index and asserts which problem it
reports. That is the only way to know a green run on the real index means
something: a check that cannot fail has not verified anything.

The fixture is a two-page synthetic document, written by the test, so no
assertion here depends on the real work programme PDF. The real index is held to
these same checks in `tests/test_demo_sources.py`.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from runner import source_index as si

# ---------------------------------------------------------------------------
# A synthetic repository
# ---------------------------------------------------------------------------

PAGE_ONE = "The proposal earmarks resources for cooperation with SYNTH and OTHER."
PAGE_TWO = "Demonstration cases ensure interoperability with the Synthetic Typology."

#: The one candidate the fixture's concept note names that no fixture source
#: claims. Tests that want a green index declare it; the partition tests below
#: leave it out on purpose, to show the check firing.
DECLARED = {"Synthetic Typology": "A fixture phrase, not a source."}


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A minimal repository: a two-page PDF, a registry and a concept summary."""
    pymupdf = pytest.importorskip("pymupdf")
    pdf_rel = "docs/stored/synthetic.pdf"
    pdf_path = tmp_path / pdf_rel
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open()
    for body in (PAGE_ONE, PAGE_TWO):
        page = doc.new_page()
        page.insert_text((72, 72), body, fontsize=11)
    doc.save(pdf_path)
    doc.close()

    _write(tmp_path / si.DOCUMENT_REGISTRY_REL, {
        "document_registry": [{"document_id": "synth.doc", "path": pdf_rel}]
    })
    _write(tmp_path / si.PROJECT_SUMMARY_REL, {
        "concept_claims": [{"claim_id": "C01"}, {"claim_id": "C02"}]
    })
    # The swept artifacts the name checks read. Only the two the fixture needs.
    (tmp_path / "docs/tier3_project_instantiation/project_brief").mkdir(
        parents=True, exist_ok=True
    )
    (tmp_path / "docs/tier3_project_instantiation/project_brief/concept_note.md").write_text(
        "The project cooperates with SYNTH and uses the Synthetic Typology.\n",
        encoding="utf-8",
    )
    return tmp_path


def _write(path: Path, doc: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")


def _page_text(repo: Path, page: int) -> str:
    return si.read_page_text(repo / "docs/stored/synthetic.pdf", page)


def _page_source(repo: Path, page: int, **overrides: Any) -> dict[str, Any]:
    text = _page_text(repo, page)
    quote = "SYNTH" if page == 1 else "Synthetic Typology"
    start = text.index(quote)
    record: dict[str, Any] = {
        "source_id": f"SRC-P{page}",
        "title": f"Synthetic document page {page}",
        "kind": "call_document_page",
        "status": "Confirmed",
        "citation": {"cited_as": f"Synthetic document, page {page}.", "page": page},
        "resolves_to": {
            "class": "stored_document",
            "stored_path": "docs/stored/synthetic.pdf",
            "document_id": "synth.doc",
            "page": page,
            "what_it_holds": f"Page {page} of the stored synthetic document.",
        },
        "transcription": {"state": "transcribed", "method": si.PAGE_TEXT_METHOD,
                          "replay": "read_page_text"},
        "text": text,
        "spans": [{
            "span_id": f"SRC-P{page}#{start}-{start + len(quote)}",
            "start": start,
            "end": start + len(quote),
            "quote": quote,
            "claim_refs": ["C01"],
        }],
        "relied_on_for": [{
            "what": "The naming of the framework.",
            "claim_refs": ["C01"],
            "span_refs": [f"SRC-P{page}#{start}-{start + len(quote)}"],
            "status": "Confirmed",
        }],
    }
    record.update(overrides)
    return record


def _reference(repo: Path, **overrides: Any) -> dict[str, Any]:
    span = _page_source(repo, 1)["spans"][0]
    record: dict[str, Any] = {
        "source_id": "SRC-SYNTH",
        "title": "The SYNTH framework",
        "kind": "external_reference",
        "status": "Assumed",
        "names": ["SYNTH"],
        "citation": {"cited_as": "SYNTH, a synthetic data framework."},
        "anchor": {"via_source": "SRC-P1", "span_id": span["span_id"],
                   "verbatim": "SYNTH",
                   "what_the_anchor_shows": "The document names it."},
        "resolves_to": {
            "class": "external_identifier",
            "identifier": "https://example.invalid/synth",
            "identifier_status": "Assumed",
            "basis": "Recorded, not resolved.",
            "what_it_holds": "The framework's own pages.",
        },
        "transcription": {"state": "cited_only", "reason": "No copy is stored."},
        "relied_on_for": [{"what": "The cooperation duty.", "claim_refs": [],
                           "span_refs": [], "status": "Assumed"}],
    }
    record.update(overrides)
    return record


def _index(repo: Path, sources: list[dict[str, Any]], **overrides: Any) -> Path:
    doc: dict[str, Any] = {
        "record_type": si.SOURCE_INDEX_RECORD_TYPE,
        "sources": sources,
        "names_that_are_not_sources": {},
    }
    doc.update(overrides)
    path = repo / si.SOURCES_REL
    _write(path, doc)
    return path


def _messages(report: si.SourceIndexReport) -> str:
    return "\n".join(f"{p.where}:{p.kind}:{p.message}" for p in report.problems)


# ---------------------------------------------------------------------------
# The green case, so every red case below means something
# ---------------------------------------------------------------------------


class TestAWellFormedIndex:
    def test_a_page_source_and_a_reference_verify(self, repo: Path) -> None:
        _index(repo, [_page_source(repo, 1), _reference(repo)],
               names_that_are_not_sources=DECLARED)
        report = si.verify(repo)
        assert report.ok, _messages(report)
        assert report.sources_checked == ("SRC-P1", "SRC-SYNTH")
        assert report.transcribed == ("SRC-P1",)
        assert report.spans_resolved == 1

    def test_the_transcription_is_the_function_the_verifier_replays(self, repo: Path) -> None:
        """The generator and the verifier must share one implementation.

        If they did not, a green check would only prove two extractors agree by
        luck. `read_page_text` is the declared method's single implementation.
        """
        assert _page_text(repo, 1) == si.read_page_text(
            repo / "docs/stored/synthetic.pdf", 1
        )


# ---------------------------------------------------------------------------
# Transcription — the anti-fabrication leg
# ---------------------------------------------------------------------------


class TestTranscription:
    def test_edited_text_fails_the_byte_equal_replay(self, repo: Path) -> None:
        """The check the whole module exists for.

        A single character changed in the stored text — the kind of edit that
        makes a quotation say what a draft needs — must fail.
        """
        source = _page_source(repo, 1)
        source["text"] = source["text"].replace("cooperation", "co-operation")
        _index(repo, [source])
        report = si.verify(repo)
        assert not report.ok
        assert "not byte-equal" in _messages(report)

    def test_a_reference_may_not_carry_text(self, repo: Path) -> None:
        """Text on an unstored source is the laundering route, so it is refused."""
        _index(repo, [_page_source(repo, 1),
                      _reference(repo, text="SYNTH guarantees interoperability.")])
        report = si.verify(repo)
        assert not report.ok
        assert "carries text" in _messages(report)

    def test_a_reference_may_not_carry_spans(self, repo: Path) -> None:
        _index(repo, [_page_source(repo, 1), _reference(repo, spans=[
            {"span_id": "SRC-SYNTH#0-5", "start": 0, "end": 5, "quote": "SYNTH"}
        ])])
        report = si.verify(repo)
        assert not report.ok
        assert "carries spans" in _messages(report)

    def test_an_untranscribed_source_must_say_why(self, repo: Path) -> None:
        _index(repo, [_page_source(repo, 1),
                      _reference(repo, transcription={"state": "cited_only"})])
        report = si.verify(repo)
        assert not report.ok
        assert "must say why" in _messages(report)

    def test_an_unreplayable_method_is_refused(self, repo: Path) -> None:
        """A method the verifier cannot re-run is a transcription nobody checks."""
        source = _page_source(repo, 1)
        source["transcription"] = {"state": "transcribed", "method": "hand_typed"}
        _index(repo, [source])
        report = si.verify(repo)
        assert not report.ok
        assert "only method this module can replay" in _messages(report)

    def test_the_kind_must_match_the_state(self, repo: Path) -> None:
        source = _page_source(repo, 1)
        source["kind"] = "external_reference"
        _index(repo, [source])
        report = si.verify(repo)
        assert not report.ok
        assert "requires state" in _messages(report)

    def test_a_missing_stored_file_fails_rather_than_passes(self, repo: Path) -> None:
        source = _page_source(repo, 1)
        source["resolves_to"]["stored_path"] = "docs/stored/absent.pdf"
        _index(repo, [source])
        report = si.verify(repo)
        assert not report.ok
        assert "cannot be replayed" in _messages(report) or "not a file" in _messages(report)


# ---------------------------------------------------------------------------
# Spans
# ---------------------------------------------------------------------------


class TestSpans:
    def test_a_quote_that_is_not_the_text_at_those_offsets_fails(self, repo: Path) -> None:
        source = _page_source(repo, 1)
        source["spans"][0]["quote"] = "OTHER"
        _index(repo, [source])
        report = si.verify(repo)
        assert not report.ok
        assert "is not the text at" in _messages(report)

    def test_an_offset_past_the_end_of_the_text_fails(self, repo: Path) -> None:
        source = _page_source(repo, 1)
        source["spans"][0]["end"] = len(source["text"]) + 10
        _index(repo, [source])
        report = si.verify(repo)
        assert not report.ok
        assert "exceeds the text" in _messages(report)

    def test_a_claim_ref_must_name_a_concept_claim(self, repo: Path) -> None:
        source = _page_source(repo, 1)
        source["spans"][0]["claim_refs"] = ["C99"]
        _index(repo, [source])
        report = si.verify(repo)
        assert not report.ok
        assert "not a concept claim" in _messages(report)

    def test_a_duplicate_span_id_fails(self, repo: Path) -> None:
        source = _page_source(repo, 1)
        source["spans"].append(dict(source["spans"][0]))
        _index(repo, [source])
        report = si.verify(repo)
        assert not report.ok
        assert "declared twice" in _messages(report)


# ---------------------------------------------------------------------------
# Anchors — what makes an unstored reference resolvable
# ---------------------------------------------------------------------------


class TestAnchors:
    def test_a_reference_the_document_does_not_name_fails(self, repo: Path) -> None:
        """The ticket's third criterion, in its sharpest form.

        A reference claiming a citation the anchoring text does not make is a
        source described as supporting something it does not contain.
        """
        _index(repo, [_page_source(repo, 1),
                      _reference(repo, names=["SYNTH"],
                                 anchor={"via_source": "SRC-P1",
                                         "span_id": _page_source(repo, 1)["spans"][0]["span_id"],
                                         "verbatim": "NEVER-NAMED"})])
        report = si.verify(repo)
        assert not report.ok
        assert "does not occur in span" in _messages(report)

    def test_an_anchor_naming_an_unknown_source_fails(self, repo: Path) -> None:
        _index(repo, [_page_source(repo, 1),
                      _reference(repo, anchor={"via_source": "SRC-ABSENT",
                                               "span_id": "x", "verbatim": "SYNTH"})])
        report = si.verify(repo)
        assert not report.ok
        assert "is not a source in this index" in _messages(report)

    def test_an_anchor_naming_an_unknown_span_fails(self, repo: Path) -> None:
        _index(repo, [_page_source(repo, 1),
                      _reference(repo, anchor={"via_source": "SRC-P1",
                                               "span_id": "SRC-P1#0-1",
                                               "verbatim": "SYNTH"})])
        report = si.verify(repo)
        assert not report.ok
        assert "is not a span of" in _messages(report)

    def test_a_reference_with_no_anchor_fails(self, repo: Path) -> None:
        reference = _reference(repo)
        del reference["anchor"]
        _index(repo, [_page_source(repo, 1), reference])
        report = si.verify(repo)
        assert not report.ok
        assert "needs an anchor" in _messages(report)

    def test_an_artifact_anchor_is_checked_against_the_file(self, repo: Path) -> None:
        brief = "docs/tier3_project_instantiation/project_brief/concept_note.md"
        good = _reference(repo, anchor={"artifact": brief, "verbatim": "Synthetic Typology"})
        _index(repo, [_page_source(repo, 1), good], names_that_are_not_sources=DECLARED)
        assert si.verify(repo).ok
        bad = _reference(repo, anchor={"artifact": brief, "verbatim": "Absent Typology"})
        _index(repo, [_page_source(repo, 1), bad], names_that_are_not_sources=DECLARED)
        report = si.verify(repo)
        assert not report.ok
        assert "does not occur in" in _messages(report)


# ---------------------------------------------------------------------------
# Resolution and the honest status of an identifier
# ---------------------------------------------------------------------------


class TestResolution:
    def test_an_external_identifier_may_not_be_confirmed(self, repo: Path) -> None:
        """Nothing on this branch resolves an external identifier.

        Recording one from prior knowledge is permitted and flagged (§10.6).
        Calling it Confirmed would assert a resolution that never happened.
        """
        reference = _reference(repo)
        reference["resolves_to"]["identifier_status"] = "Confirmed"
        _index(repo, [_page_source(repo, 1), reference])
        report = si.verify(repo)
        assert not report.ok
        assert "cannot be Confirmed" in _messages(report)

    def test_a_null_identifier_is_allowed_when_an_anchor_resolves(self, repo: Path) -> None:
        """An identifier nobody could verify is better left null than guessed."""
        reference = _reference(repo)
        reference["resolves_to"].update(
            {"identifier": None, "identifier_status": "Unresolved"}
        )
        _index(repo, [_page_source(repo, 1), reference],
               names_that_are_not_sources=DECLARED)
        report = si.verify(repo)
        assert report.ok, _messages(report)

    def test_a_null_identifier_must_be_unresolved(self, repo: Path) -> None:
        reference = _reference(repo)
        reference["resolves_to"]["identifier"] = None
        _index(repo, [_page_source(repo, 1), reference])
        report = si.verify(repo)
        assert not report.ok
        assert "must carry identifier_status Unresolved" in _messages(report)

    def test_an_unregistered_stored_document_fails(self, repo: Path) -> None:
        """§9.6: a stored document this index cites must be in the registry."""
        source = _page_source(repo, 1)
        source["resolves_to"]["document_id"] = "synth.unregistered"
        _index(repo, [source])
        report = si.verify(repo)
        assert not report.ok
        assert "is not registered" in _messages(report)

    def test_a_location_must_say_what_it_holds(self, repo: Path) -> None:
        source = _page_source(repo, 1)
        del source["resolves_to"]["what_it_holds"]
        _index(repo, [source])
        report = si.verify(repo)
        assert not report.ok
        assert "what_it_holds is missing" in _messages(report)


# ---------------------------------------------------------------------------
# Overclaiming
# ---------------------------------------------------------------------------


class TestOverclaim:
    def test_confirmed_without_a_span_fails(self, repo: Path) -> None:
        """A use is Confirmed only when a resolved span carries it."""
        reference = _reference(repo)
        reference["relied_on_for"][0]["status"] = "Confirmed"
        _index(repo, [_page_source(repo, 1), reference])
        report = si.verify(repo)
        assert not report.ok
        assert "Confirmed with no span_refs" in _messages(report)

    def test_a_span_ref_to_a_span_the_source_does_not_declare_fails(self, repo: Path) -> None:
        source = _page_source(repo, 1)
        source["relied_on_for"][0]["span_refs"] = ["SRC-P1#999-1000"]
        _index(repo, [source])
        report = si.verify(repo)
        assert not report.ok
        assert "spans this source does not declare" in _messages(report)

    def test_a_source_nothing_relies_on_fails(self, repo: Path) -> None:
        source = _page_source(repo, 1, relied_on_for=[])
        _index(repo, [source])
        report = si.verify(repo)
        assert not report.ok
        assert "relied_on_for is empty" in _messages(report)

    def test_a_use_must_carry_a_status_category(self, repo: Path) -> None:
        source = _page_source(repo, 1)
        source["relied_on_for"][0]["status"] = "verified"
        _index(repo, [source])
        report = si.verify(repo)
        assert not report.ok
        assert "not a §12.2 status" in _messages(report)


# ---------------------------------------------------------------------------
# The name partition
# ---------------------------------------------------------------------------


class TestTheNamePartition:
    def test_an_unclassified_candidate_fails(self, repo: Path) -> None:
        """The completeness leg: a name in the concept must be disposed of.

        The concept note names "Synthetic Typology". With no source claiming it
        and no declared reason, the check must fail — that is what makes "each
        cited source has an entry" a check rather than an assertion.
        """
        _index(repo, [_page_source(repo, 1), _reference(repo)])
        report = si.verify(repo)
        assert not report.ok
        assert "Synthetic Typology" in _messages(report)
        assert "neither claimed by a source nor declared" in _messages(report)

    def test_a_declared_reason_classifies_it(self, repo: Path) -> None:
        _index(repo, [_page_source(repo, 1), _reference(repo)],
               names_that_are_not_sources={"Synthetic Typology": "A fixture phrase."})
        report = si.verify(repo)
        assert report.ok, _messages(report)

    def test_a_dead_declaration_fails(self, repo: Path) -> None:
        """A declared name the sweep no longer produces hides a drift in the sweep."""
        _index(repo, [_page_source(repo, 1), _reference(repo)],
               names_that_are_not_sources={
                   "Synthetic Typology": "A fixture phrase.",
                   "Retired Framework": "Was named once, no longer is.",
               })
        report = si.verify(repo)
        assert not report.ok
        assert "the derivation does not produce it" in _messages(report)

    def test_a_name_claimed_and_declared_fails(self, repo: Path) -> None:
        _index(repo, [_page_source(repo, 1), _reference(repo)],
               names_that_are_not_sources={"Synthetic Typology": "A fixture phrase.",
                                           "SYNTH": "Also declared, wrongly."})
        report = si.verify(repo)
        assert not report.ok
        assert "also declared not to be a source" in _messages(report)

    def test_a_name_the_concept_never_uses_fails(self, repo: Path) -> None:
        """A source may not claim an alias no swept artifact contains."""
        _index(repo, [_page_source(repo, 1),
                      _reference(repo, names=["SYNTH", "UNUSED"])],
               names_that_are_not_sources={"Synthetic Typology": "A fixture phrase."})
        report = si.verify(repo)
        assert not report.ok
        assert "appears in no swept Tier 3 artifact" in _messages(report)

    def test_two_sources_may_not_claim_one_name(self, repo: Path) -> None:
        _index(repo, [_page_source(repo, 1), _reference(repo),
                      _reference(repo, source_id="SRC-OTHER")],
               names_that_are_not_sources={"Synthetic Typology": "A fixture phrase."})
        report = si.verify(repo)
        assert not report.ok
        assert "claimed by both" in _messages(report)

    def test_the_sweep_finds_acronyms_and_multiword_names(self, repo: Path) -> None:
        candidates = si.candidate_names(repo)
        assert "SYNTH" in candidates
        assert "Synthetic Typology" in candidates

    def test_the_sweep_records_where_each_candidate_was_found(self, repo: Path) -> None:
        candidates = si.candidate_names(repo)
        assert candidates["SYNTH"] == (
            "docs/tier3_project_instantiation/project_brief/concept_note.md",
        )

    def test_single_word_externals_are_a_hand_list_and_say_so(self) -> None:
        """The sweep's declared limit.

        A single capitalised word cannot be told from a sentence opener
        mechanically, so these are listed rather than derived. Pinning the set
        keeps the limit visible instead of implied.
        """
        assert "Copernicus" in si.SINGLE_WORD_EXTERNALS
        assert "The" not in si.SINGLE_WORD_EXTERNALS
        docstring = si.__doc__ or ""
        assert "single" in docstring.lower() and "hand list" in docstring.lower()


# ---------------------------------------------------------------------------
# Fail-closed reading
# ---------------------------------------------------------------------------


class TestFailClosed:
    def test_an_absent_index_is_refused_not_reported_clean(self, repo: Path) -> None:
        with pytest.raises(si.SourceIndexError, match="absent"):
            si.verify(repo)

    def test_an_empty_source_list_is_refused(self, repo: Path) -> None:
        _index(repo, [])
        with pytest.raises(si.SourceIndexError, match="non-empty list"):
            si.verify(repo)

    def test_a_file_that_does_not_declare_itself_a_source_index_is_refused(
        self, repo: Path
    ) -> None:
        _index(repo, [_page_source(repo, 1)], record_type="something_else")
        with pytest.raises(si.SourceIndexError, match="record_type"):
            si.verify(repo)

    def test_no_orch_schema_id_is_coined(self, repo: Path) -> None:
        """§16.3: a Tier 3 source artifact does not invent a registered schema.

        partners.json and roles.json both say so of themselves. The index
        declares what it is through record_type instead.
        """
        _index(repo, [_page_source(repo, 1)], names_that_are_not_sources=DECLARED)
        doc = json.loads((repo / si.SOURCES_REL).read_text(encoding="utf-8"))
        assert "schema_id" not in doc

    def test_a_reasonless_declaration_is_refused(self, repo: Path) -> None:
        _index(repo, [_page_source(repo, 1)],
               names_that_are_not_sources={"Synthetic Typology": "  "})
        with pytest.raises(si.SourceIndexError, match="non-empty reason"):
            si.verify(repo)

    def test_a_page_outside_the_document_is_refused(self, repo: Path) -> None:
        with pytest.raises(si.SourceIndexError, match="outside the document"):
            si.read_page_text(repo / "docs/stored/synthetic.pdf", 99)

    def test_the_transcription_states_are_closed_at_two(self) -> None:
        """No third state. A "paraphrased" source is a claim nobody can check."""
        assert si.TRANSCRIPTION_STATES == frozenset({"transcribed", "cited_only"})


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------


class TestNormalisation:
    def test_only_whitespace_is_collapsed(self) -> None:
        """Every other character survives, or a span would rewrite its source."""
        assert si.normalise_whitespace("a\n b\t\tc ") == "a b c"
        assert si.normalise_whitespace("under ESA’s FuturEO") == "under ESA’s FuturEO"
        assert si.normalise_whitespace("“quoted” – dashed") == (
            "“quoted” – dashed"
        )

    def test_it_agrees_with_the_tier_source_helper(self) -> None:
        """Two normalisers in the repository must not disagree.

        `tests/_tier_sources.norm` normalises the same PDF text for the Tier 2B
        and Tier 1 checks. A divergence would make a span verified by one and
        rejected by the other.
        """
        from tests._tier_sources import norm

        for sample in ("a\n b", " padded ", "curly ’ quote", "en – dash"):
            assert si.normalise_whitespace(sample) == norm(sample)
