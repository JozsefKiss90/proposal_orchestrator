"""
Tests for harness/claim_ledger.py — the E3 escaped-claim detector.

Fully offline: judges are driven by injected fake backends (no network), and
the pipeline's decomposer/materiality classifier are injectable so most tests
exercise pure seams.  The load-bearing cases: an unledgered material assertion
becomes the ESCAPED hard finding; failures (chunk, materiality, coverage) are
surfaced as findings, never dropped and never aborting the batch; matching is
by meaning with candidate *numbers*, never by ambiguous claim ids.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import pytest

import harness.claim_ledger as cl
from harness.judge import Judge, JudgeConfig, JudgeResponseError
from harness.materiality import MaterialityCalibration
from harness.calibration import ConfusionMatrix
from harness.provenance import ProvenanceLog
from harness.status_faithfulness import SectionClaim
from harness.verdict import Verdict


# --------------------------------------------------------------------------- #
# Fakes (E2 idiom)
# --------------------------------------------------------------------------- #


class RuleBackend:
    def __init__(self, rule: Callable[[str, str], Any]) -> None:
        self._rule = rule
        self.calls: list[tuple[str, str]] = []

    def __call__(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        system = messages[0]["content"]
        user = messages[1]["content"]
        self.calls.append((system, user))
        payload = self._rule(system, user)
        content = payload if isinstance(payload, str) else json.dumps(payload)
        return {"content": content, "tool_calls": None}


def make_judge(rule: Callable[[str, str], Any]) -> tuple[Judge, RuleBackend]:
    backend = RuleBackend(rule)
    judge = Judge(JudgeConfig(model="acme-judge-1", version="v1"), backend=backend)
    return judge, backend


def always(payload: Any) -> Callable[[str, str], Any]:
    return lambda system, user: payload if isinstance(payload, str) else dict(payload)


def sub(sub_id="1.1", content="Para one.\n\nPara two.", title="T"):
    return cl.SubSectionProse(sub_section_id=sub_id, title=title, content=content)


def chunk(text="Some passage.", sub_id="1.1", index=0):
    return cl.ProseChunk(sub_section_id=sub_id, chunk_index=index, text=text)


def assertion(aid="1.1:c00:a00", text="the host is ELTE", sub_id="1.1", chunk_id="1.1:c00"):
    return cl.Assertion(assertion_id=aid, text=text, sub_section_id=sub_id, chunk_id=chunk_id)


def claim(cid="C1", summary="the claim", status="confirmed", ref="docs/x.json", idx=None):
    return SectionClaim(
        claim_id=cid, claim_summary=summary, status=status, source_ref=ref, entry_index=idx
    )


def record(summary="Crop selection: tomato", status="confirmed", ref="docs/x.json", keys=("C1#0",)):
    return cl.LedgerRecord(
        claim_summary=summary, status=status, source_ref=ref, entry_keys=tuple(keys)
    )


def material_verdict(passed=True):
    return Verdict(metric="claim_materiality", property_key="k", passed=passed)


# --------------------------------------------------------------------------- #
# Prose loading + chunking
# --------------------------------------------------------------------------- #


class TestLoadSectionProse:
    def test_loads_in_order(self, tmp_path):
        p = tmp_path / "sec.json"
        p.write_text(json.dumps({"sub_sections": [
            {"sub_section_id": "1", "title": "A", "content": "x"},
            {"sub_section_id": "1.1", "title": "B", "content": "y"},
        ]}), encoding="utf-8")
        prose = cl.load_section_prose(p)
        assert [s.sub_section_id for s in prose] == ["1", "1.1"]
        assert prose[1].content == "y"

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(cl.ClaimLedgerError, match="not found"):
            cl.load_section_prose(tmp_path / "nope.json")

    def test_no_sub_sections_raises(self, tmp_path):
        p = tmp_path / "sec.json"
        p.write_text(json.dumps({"validation_status": {}}), encoding="utf-8")
        with pytest.raises(cl.ClaimLedgerError, match="sub_sections"):
            cl.load_section_prose(p)

    def test_non_object_entry_raises(self, tmp_path):
        p = tmp_path / "sec.json"
        p.write_text(json.dumps({"sub_sections": ["nope"]}), encoding="utf-8")
        with pytest.raises(cl.ClaimLedgerError, match="objects"):
            cl.load_section_prose(p)


class TestChunkProse:
    def test_groups_whole_paragraphs_under_cap(self):
        s = sub(content="aaaa\n\nbbbb\n\ncccc")
        chunks = cl.chunk_prose(s, max_chars=11)
        # "aaaa\n\nbbbb" is 10 chars <= 11; adding cccc would exceed.
        assert [c.text for c in chunks] == ["aaaa\n\nbbbb", "cccc"]
        assert [c.chunk_id for c in chunks] == ["1.1:c00", "1.1:c01"]

    def test_oversized_paragraph_becomes_own_chunk_never_split(self):
        big = "x" * 100
        chunks = cl.chunk_prose(sub(content=f"small\n\n{big}\n\nsmall2"), max_chars=20)
        assert [c.text for c in chunks] == ["small", big, "small2"]

    def test_reconstruction_loses_nothing(self):
        s = sub(content="one\n\n\n\ntwo\n\nthree   \n\nfour")
        chunks = cl.chunk_prose(s, max_chars=9)
        rejoined = "\n\n".join(c.text for c in chunks)
        assert rejoined == "one\n\ntwo\n\nthree\n\nfour"

    def test_empty_content_yields_no_chunks(self):
        assert cl.chunk_prose(sub(content="  \n\n ")) == ()


# --------------------------------------------------------------------------- #
# Decomposition parse + judge wrapper
# --------------------------------------------------------------------------- #


class TestParseAssertionsPayload:
    def test_valid(self):
        raw = json.dumps({"assertions": [" a one ", "a two"]})
        assert cl.parse_assertions_payload(raw) == ("a one", "a two")

    def test_empty_list_is_valid(self):
        assert cl.parse_assertions_payload('{"assertions": []}') == ()

    def test_fenced_object_ok(self):
        raw = 'noise\n```json\n{"assertions": ["a"]}\n```'
        assert cl.parse_assertions_payload(raw) == ("a",)

    def test_no_object_raises(self):
        with pytest.raises(cl.ClaimLedgerError, match="no parseable JSON object"):
            cl.parse_assertions_payload("not json")

    def test_bare_top_level_array_raises(self):
        with pytest.raises(cl.ClaimLedgerError, match="no parseable JSON object"):
            cl.parse_assertions_payload('["a", "b"]')

    def test_missing_key_raises(self):
        with pytest.raises(cl.ClaimLedgerError, match="assertions"):
            cl.parse_assertions_payload('{"other": []}')

    def test_non_string_member_raises(self):
        with pytest.raises(cl.ClaimLedgerError, match=r"\[1\]"):
            cl.parse_assertions_payload('{"assertions": ["ok", 42]}')

    def test_blank_member_raises_not_dropped(self):
        with pytest.raises(cl.ClaimLedgerError, match=r"\[0\]"):
            cl.parse_assertions_payload('{"assertions": ["  "]}')


class TestDecomposeChunk:
    def test_returns_texts_and_logs_provenance(self, tmp_path):
        judge, backend = make_judge(always({"assertions": ["the host is ELTE"]}))
        log = ProvenanceLog(tmp_path / "prov.jsonl")
        texts = cl.decompose_chunk(judge, chunk(), provenance_log=log, clock=lambda: "T")
        assert texts == ("the host is ELTE",)
        assert len(backend.calls) == 1
        system, user = backend.calls[0]
        assert "EXHAUSTIVE" in system
        assert "Some passage." in user
        recs = log.records()
        assert len(recs) == 1
        assert recs[0]["metric"] == cl.DECOMPOSITION_METRIC
        assert recs[0]["property_key"] == "1.1:c00"
        assert recs[0]["prompt_hash"].startswith("sha256:")
        assert recs[0]["timestamp"] == "T"

    def test_no_log_anywhere_is_fine(self):
        judge, _ = make_judge(always({"assertions": []}))
        assert cl.decompose_chunk(judge, chunk()) == ()

    def test_falls_back_to_judge_attached_log(self, tmp_path):
        # The standard attach-a-log-to-the-Judge pattern must not silently
        # lose decomposition provenance when no explicit log is passed.
        attached = ProvenanceLog(tmp_path / "attached.jsonl")
        backend = RuleBackend(always({"assertions": ["a fact"]}))
        judge = Judge(
            JudgeConfig(model="acme-judge-1", version="v1"),
            backend=backend,
            provenance_log=attached,
        )
        cl.decompose_chunk(judge, chunk())
        assert len(attached.records()) == 1
        assert attached.records()[0]["metric"] == cl.DECOMPOSITION_METRIC

    def test_explicit_log_takes_precedence_over_attached(self, tmp_path):
        attached = ProvenanceLog(tmp_path / "attached.jsonl")
        explicit = ProvenanceLog(tmp_path / "explicit.jsonl")
        judge = Judge(
            JudgeConfig(model="acme-judge-1", version="v1"),
            backend=RuleBackend(always({"assertions": ["a fact"]})),
            provenance_log=attached,
        )
        cl.decompose_chunk(judge, chunk(), provenance_log=explicit)
        assert len(explicit.records()) == 1
        assert attached.records() == []

    def test_malformed_raises(self):
        judge, _ = make_judge(always("not json"))
        with pytest.raises(cl.ClaimLedgerError):
            cl.decompose_chunk(judge, chunk())


class TestDedupAssertions:
    def test_collapse_keeps_origins(self):
        a1 = assertion(aid="s:c00:a00", text="The host is ELTE.", chunk_id="s:c00")
        a2 = assertion(aid="s:c03:a01", text="the  host is elte.", chunk_id="s:c03")
        a3 = assertion(aid="s:c04:a00", text="Different fact.", chunk_id="s:c04")
        out = cl.dedup_assertions([a1, a2, a3])
        assert [a.assertion_id for a in out] == ["s:c00:a00", "s:c04:a00"]
        assert out[0].also_in == ("s:c03",)


# --------------------------------------------------------------------------- #
# Ledger records + shortlist
# --------------------------------------------------------------------------- #


class TestDedupLedgerClaims:
    def test_true_duplicates_collapse_with_all_entry_keys(self):
        claims = [
            claim("C01", "Crop selection: tomato", idx=0),
            claim("C01", "Crop selection:  TOMATO", idx=43),  # true dup (normalized)
            claim("C01", "the fellow is Dr. X", idx=171),     # same id, different claim
        ]
        records = cl.dedup_ledger_claims(claims)
        assert len(records) == 2
        assert records[0].entry_keys == ("C01#0", "C01#43")
        assert records[0].label == "C01#0"
        assert records[1].entry_keys == ("C01#171",)

    def test_status_and_ref_distinguish(self):
        claims = [
            claim("C1", "same words", status="confirmed"),
            claim("C1", "same words", status="inferred"),
        ]
        assert len(cl.dedup_ledger_claims(claims)) == 2


class TestLexicalShortlist:
    RECORDS = (
        record("Crop selection: tomato for the drought experiment", keys=("C01#0",)),
        record("The fellowship lasts 24 months at ELTE Budapest", keys=("C02#1",)),
        record("Dissemination via two open-access publications", keys=("C03#2",)),
    )

    def test_ranks_relevant_first_and_caps_k(self):
        out = cl.lexical_shortlist("the tomato crop was selected for drought", self.RECORDS, k=2)
        assert out and out[0].label == "C01#0"
        assert len(out) <= 2

    def test_zero_overlap_dropped(self):
        out = cl.lexical_shortlist("quantum flux capacitors", self.RECORDS, k=5)
        assert out == ()

    def test_stopwords_do_not_match(self):
        out = cl.lexical_shortlist("the and for with that", self.RECORDS, k=5)
        assert out == ()

    def test_tie_broken_by_ledger_order(self):
        recs = (record("alpha beta", keys=("A#0",)), record("alpha beta", keys=("B#1",)))
        out = cl.lexical_shortlist("alpha beta", recs, k=2)
        assert [r.label for r in out] == ["A#0", "B#1"]


# --------------------------------------------------------------------------- #
# Coverage prompts + covered_by extraction
# --------------------------------------------------------------------------- #


class TestCoveragePrompt:
    def test_candidates_are_numbered_with_entry_key_labels(self):
        system, user = cl.build_coverage_prompt("the fellow is X", TestLexicalShortlist.RECORDS)
        assert "1. [C01#0]" in user and "3. [C03#2]" in user
        assert "the fellow is X" in user
        assert "NUMBER" in system
        assert '"covered_by"' in system

    def test_empty_candidates_raise(self):
        with pytest.raises(cl.ClaimLedgerError):
            cl.build_coverage_prompt("x", ())


class TestExtractCoveredBy:
    def test_valid_int(self):
        assert cl.extract_covered_by('{"passed": true, "covered_by": 2}', 3) == 2

    def test_digit_string_accepted(self):
        assert cl.extract_covered_by('{"covered_by": "3"}', 3) == 3

    def test_out_of_range_none(self):
        assert cl.extract_covered_by('{"covered_by": 4}', 3) is None

    def test_null_bool_or_garbage_none(self):
        assert cl.extract_covered_by('{"covered_by": null}', 3) is None
        assert cl.extract_covered_by('{"covered_by": true}', 3) is None
        assert cl.extract_covered_by("not json", 3) is None


# --------------------------------------------------------------------------- #
# match_assertion — batched primary, escalation fallback
# --------------------------------------------------------------------------- #


class TestMatchAssertion:
    RECORDS = TestLexicalShortlist.RECORDS

    def test_batched_covered_with_valid_number(self):
        judge, backend = make_judge(
            always({"passed": True, "covered_by": 1, "rationale": "r"})
        )
        out = cl.match_assertion(
            judge, assertion(text="tomato crop selection for drought"), self.RECORDS
        )
        assert out.covered is True
        assert out.matched is not None and out.matched.label == "C01#0"
        assert out.escalated is False
        assert len(backend.calls) == 1  # one batched call, no per-candidate loop

    def test_judged_uncovered(self):
        judge, _ = make_judge(always({"passed": False, "covered_by": None, "rationale": "r"}))
        out = cl.match_assertion(
            judge, assertion(text="tomato crop selection"), self.RECORDS
        )
        assert out.covered is False
        assert out.basis == cl.ESCAPE_JUDGED_UNCOVERED
        assert out.verdict is not None and out.verdict.passed is False

    def test_no_lexical_candidates_no_judge_call(self):
        judge, backend = make_judge(always({"passed": True, "rationale": "r"}))
        out = cl.match_assertion(
            judge, assertion(text="quantum flux capacitors"), self.RECORDS
        )
        assert out.covered is False
        assert out.basis == cl.ESCAPE_NO_LEXICAL_CANDIDATES
        assert out.verdict is None
        assert backend.calls == []

    def test_unattributable_coverage_escalates_and_confirms(self):
        # Batched call says covered but names no valid candidate; the
        # per-candidate escalation then confirms the second candidate.
        def rule(system, user):
            if "CANDIDATE LEDGER CLAIMS" in user:
                return {"passed": True, "covered_by": 99, "rationale": "vague"}
            # pair question: pass only for the fellowship claim
            return {"passed": "fellowship" in user, "rationale": "pair"}

        judge, backend = make_judge(rule)
        out = cl.match_assertion(
            judge, assertion(text="the fellowship lasts 24 months"), self.RECORDS, shortlist_k=3
        )
        assert out.covered is True
        assert out.escalated is True
        assert out.matched is not None and out.matched.label == "C02#1"
        assert len(backend.calls) >= 2  # batched + at least one pair call

    def test_unconfirmed_escalation_is_uncovered_loudly(self):
        def rule(system, user):
            if "CANDIDATE LEDGER CLAIMS" in user:
                return {"passed": True, "covered_by": None, "rationale": "vague"}
            return {"passed": False, "rationale": "pair says no"}

        judge, backend = make_judge(rule)
        # overlaps two records (C02 via fellowship/months, C03 via open-access)
        out = cl.match_assertion(
            judge,
            assertion(text="the fellowship lasts 24 months with open-access publications"),
            self.RECORDS,
            shortlist_k=2,
        )
        assert out.covered is False
        assert out.basis == cl.ESCAPE_ESCALATION_UNCONFIRMED
        assert out.escalated is True
        assert len(backend.calls) == 3  # 1 batched + 2 pair calls

    def test_n2_rejected(self):
        judge, _ = make_judge(always({"passed": True, "rationale": "r"}))
        with pytest.raises(ValueError, match="n=2"):
            cl.match_assertion(judge, assertion(), self.RECORDS, n=2)

    def test_n3_majority_batched(self):
        # Only C02 overlaps lexically, so the shortlist has one candidate and
        # the panel must answer covered_by=1 (candidate NUMBER, not claim id).
        judge, backend = make_judge(
            always({"passed": True, "covered_by": 1, "rationale": "r"})
        )
        out = cl.match_assertion(
            judge, assertion(text="the fellowship lasts 24 months at ELTE"), self.RECORDS, n=3
        )
        assert out.covered is True
        assert out.matched is not None and out.matched.label == "C02#1"
        assert len(backend.calls) == 3  # majority panel over the batched question


class TestJudgeAssertionCoveredBy:
    def test_boolean_and_property_key(self):
        judge, backend = make_judge(always({"passed": True, "rationale": "r"}))
        v = cl.judge_assertion_covered_by(judge, assertion(aid="s:c0:a0"), record(keys=("C7#3",)))
        assert v.passed is True
        assert v.property_key == "s:c0:a0~C7#3"
        assert v.metric == cl.COVERAGE_METRIC
        system, user = backend.calls[0]
        assert "ONE" in system and "C7#3" in user


# --------------------------------------------------------------------------- #
# evaluate_ledger_completeness — the pipeline
# --------------------------------------------------------------------------- #


def _classifier(materiality_by_text: dict[str, bool | None]):
    def classify(text: str, property_key: str):
        result = materiality_by_text.get(text, True)
        if result == "raise":
            raise JudgeResponseError("classifier backend fell over")
        return Verdict(
            metric="claim_materiality", property_key=property_key, passed=result
        )
    return classify


class TestEvaluateLedgerCompleteness:
    CLAIMS = [
        claim("C01", "Crop selection: tomato for the drought experiment", idx=0),
        claim("C02", "The fellowship lasts 24 months at ELTE Budapest", idx=1),
    ]

    def _run(self, backend_rule, decomposed, materiality=None, **kw):
        judge, backend = make_judge(backend_rule)
        result = cl.evaluate_ledger_completeness(
            [sub(content="P1.\n\nP2.")],
            self.CLAIMS,
            judge,
            section_id="excellence",
            decomposer=lambda c: decomposed,
            materiality_classifier=_classifier(materiality or {}),
            **kw,
        )
        return result, backend

    def test_escaped_claim_is_the_hard_finding(self):
        # An assertion about equipment the ledger never logged: material, no cover.
        result, _ = self._run(
            always({"passed": False, "covered_by": None, "rationale": "no cover"}),
            decomposed=("The lab owns a hyperspectral drone imaging rig",),
        )
        escaped = result.escaped()
        assert len(escaped) == 1
        f = escaped[0]
        assert f.is_hard_finding and f.flagged
        assert f.outcome == cl.OUTCOME_ESCAPED
        assert f.material is True
        assert "§10.5" in f.reason
        assert f.assertion.assertion_id == "excellence:1.1:c00:a00"

    def test_covered_assertion_names_entry_key(self):
        result, _ = self._run(
            always({"passed": True, "covered_by": 1, "rationale": "covered"}),
            decomposed=("The tomato crop was selected for the drought experiment",),
        )
        covered = result.covered()
        assert len(covered) == 1
        assert covered[0].matched_entry_key == "C01#0"
        assert result.unreferenced_record_labels == ("C02#1",)

    def test_non_material_excluded_but_counted(self):
        result, backend = self._run(
            always({"passed": True, "covered_by": 1, "rationale": "r"}),
            decomposed=("The following sub-sections describe the methodology",),
            materiality={"The following sub-sections describe the methodology": False},
        )
        assert result.escaped() == ()
        nm = result.non_material()
        assert len(nm) == 1 and nm[0].material is False
        assert backend.calls == []  # never reached the coverage judge
        assert result.outcome_counts[cl.OUTCOME_NON_MATERIAL] == 1

    def test_classifier_failure_surfaced_not_propagated(self):
        result, _ = self._run(
            always({"passed": True, "rationale": "r"}),
            decomposed=("Assertion A", "Assertion B"),
            materiality={"Assertion A": "raise"},
        )
        unjudge = result.unjudgeable()
        assert len(unjudge) == 1
        assert "materiality classification failed" in unjudge[0].reason
        # the batch continued: B was still processed
        assert len(result.findings) == 2

    def test_boolean_less_materiality_is_unjudgeable(self):
        result, _ = self._run(
            always({"passed": True, "rationale": "r"}),
            decomposed=("Assertion A",),
            materiality={"Assertion A": None},
        )
        assert result.unjudgeable()[0].reason.startswith("materiality classifier returned no boolean")

    def test_chunk_failure_surfaced_and_batch_continues(self):
        judge, _ = make_judge(always({"passed": True, "covered_by": 1, "rationale": "r"}))

        def flaky_decomposer(c):
            if c.chunk_index == 0:
                raise cl.ClaimLedgerError("bad decomposition JSON")
            return ("The tomato crop was selected for the drought experiment",)

        result = cl.evaluate_ledger_completeness(
            [sub(content=("A" * 50) + "\n\n" + ("B" * 5000))],  # two chunks
            self.CLAIMS,
            judge,
            section_id="excellence",
            decomposer=flaky_decomposer,
            materiality_classifier=_classifier({}),
        )
        assert len(result.chunk_failures) == 1
        assert result.chunk_failures[0].chunk_id == "excellence:1.1:c00"
        assert len(result.findings) == 1  # second chunk still processed

    def test_zero_assertion_density_signal(self):
        big = "x" * (cl.ZERO_ASSERTION_FLOOR_CHARS + 10)
        judge, _ = make_judge(always({"passed": True, "rationale": "r"}))
        result = cl.evaluate_ledger_completeness(
            [sub(content=big)], self.CLAIMS, judge,
            decomposer=lambda c: (),
            materiality_classifier=_classifier({}),
        )
        assert result.zero_assertion_chunk_ids == ("1.1:c00",)
        assert result.findings == ()

    def test_duplicate_assertions_judged_once_with_origins(self):
        result, _ = self._run(
            always({"passed": False, "covered_by": None, "rationale": "r"}),
            decomposed=("Same assertion", "Same  ASSERTION"),
        )
        assert len(result.findings) == 1
        assert result.findings[0].assertion.also_in == ("excellence:1.1:c00",)

    def test_routing_collected_and_report_boundary(self):
        result, _ = self._run(
            always({"passed": False, "covered_by": None, "rationale": "r"}),
            decomposed=("An unledgered material fact",),
        )
        assert len(result.routing) == 1 and result.routing[0].judge_permitted
        report = result.build_report()
        assert report.advisory is True and report.blocking is False
        assert report.metric == cl.CLAIM_LEDGER_METRIC
        assert "ESCAPED=1" in report.notes
        assert "UNCALIBRATED" in report.notes

    def test_materiality_note_partially_calibrated(self):
        cal = MaterialityCalibration(
            judge_model="acme-judge-1", judge_version="v1",
            recall=0.97, precision=None,
            confusion=ConfusionMatrix(tp=30, fp=0, tn=0, fn=1),
            n_examples=31, labeled_negatives=0, set_hash="sha256:x",
        )
        result, _ = self._run(
            always({"passed": True, "covered_by": 1, "rationale": "r"}),
            decomposed=("The tomato crop was selected",),
            materiality_calibration=cal,
        )
        assert "partially calibrated" in result.build_report().notes
        assert "precision unmeasured" in result.build_report().notes

    def test_materiality_note_repinned(self):
        cal = MaterialityCalibration(
            judge_model="other-judge", judge_version="v9",
            recall=1.0, precision=1.0,
            confusion=ConfusionMatrix(tp=1, fp=0, tn=1, fn=0),
            n_examples=2, labeled_negatives=1, set_hash="sha256:x",
        )
        result, _ = self._run(
            always({"passed": True, "covered_by": 1, "rationale": "r"}),
            decomposed=("The tomato crop was selected",),
            materiality_calibration=cal,
        )
        assert "repinned judge" in result.build_report().notes

    def test_n2_rejected(self):
        judge, _ = make_judge(always({"passed": True, "rationale": "r"}))
        with pytest.raises(ValueError, match="n=2"):
            cl.evaluate_ledger_completeness([sub()], self.CLAIMS, judge, n=2)

    def test_report_summary_counts_every_escape_as_failed(self):
        # A no-candidates escape has NO coverage verdict, and an
        # escalation-unconfirmed escape's batched verdict says passed=True —
        # the report summary must still count both as failed (hard findings),
        # never as absent or passed.
        def rule(system, user):
            if "CANDIDATE LEDGER CLAIMS" in user:
                return {"passed": True, "covered_by": None, "rationale": "vague"}
            return {"passed": False, "rationale": "pair says no"}

        result, _ = self._run(
            rule,
            decomposed=(
                "quantum flux capacitors were installed",       # no lexical candidates
                "the fellowship lasts 24 months",               # escalation unconfirmed
                "framing sentence",                             # non-material
            ),
            materiality={"framing sentence": False},
        )
        assert result.outcome_counts[cl.OUTCOME_ESCAPED] == 2
        report = result.build_report()
        assert report.summary["total"] == 3
        assert report.summary["failed"] == 2       # == escaped, exactly
        assert report.summary["inconclusive"] == 1  # the non-material one
        bases = {f.rationale for f in report.findings if f.passed is False}
        assert any(cl.ESCAPE_NO_LEXICAL_CANDIDATES in b for b in bases)
        assert any(cl.ESCAPE_ESCALATION_UNCONFIRMED in b for b in bases)

    def test_report_summary_counts_covered_as_passed(self):
        result, _ = self._run(
            always({"passed": True, "covered_by": 1, "rationale": "r"}),
            decomposed=("The tomato crop was selected for the drought experiment",),
        )
        report = result.build_report()
        assert report.summary == {
            "total": 1, "passed": 1, "failed": 0, "inconclusive": 0,
        }

    def test_to_dict_shape(self):
        result, _ = self._run(
            always({"passed": False, "covered_by": None, "rationale": "r"}),
            decomposed=("An unledgered material fact",),
        )
        d = result.to_dict()
        assert d["metric"] == cl.CLAIM_LEDGER_METRIC
        assert d["escaped_assertion_ids"] == ["excellence:1.1:c00:a00"]
        assert d["outcome_counts"][cl.OUTCOME_ESCAPED] == 1


# --------------------------------------------------------------------------- #
# Real-data probe: the three shipped sections, zero network
# --------------------------------------------------------------------------- #


class TestRealDataProbe:
    """E3 runs against the real Tier-5 artifacts with a stubbed judge —
    exercising prose loading, chunk bounds, ledger dedup, and the shortlist on
    the real 406-entry ledger.  Zero network, zero DAG runs."""

    SECTIONS = ("excellence", "impact", "implementation")

    def _root(self) -> Path:
        return Path(__file__).resolve().parents[2]

    def _section_path(self, name: str) -> Path:
        p = self._root() / f"docs/tier5_deliverables/proposal_sections/{name}_section.json"
        if not p.is_file():
            pytest.skip(f"{name}_section.json not present")
        return p

    def test_prose_loads_and_chunks_are_bounded(self):
        total_subs = 0
        for name in self.SECTIONS:
            prose = cl.load_section_prose(self._section_path(name))
            total_subs += len(prose)
            for s in prose:
                chunks = cl.chunk_prose(s)
                assert chunks, f"{name}:{s.sub_section_id} produced no chunks"
                for c in chunks:
                    # bounded unless a single paragraph exceeds the cap
                    if len(c.text) > cl.DEFAULT_MAX_CHUNK_CHARS:
                        assert "\n\n" not in c.text
        assert total_subs == 12

    def test_ledger_dedup_and_ambiguous_ids_on_real_data(self):
        from harness.status_faithfulness import load_section_claims

        claims = load_section_claims(self._section_path("excellence"))
        assert len(claims) == 191
        records = cl.dedup_ledger_claims(claims)
        # true duplicates collapse, but distinct same-id claims survive
        assert len(records) < 191
        c01 = [r for r in records if any(k.startswith("C01#") for k in r.entry_keys)]
        assert len(c01) >= 2  # the three C01 entries are ≥2 distinct claims

    def test_shortlist_finds_the_real_claim(self):
        from harness.status_faithfulness import load_section_claims

        claims = load_section_claims(self._section_path("excellence"))
        records = cl.dedup_ledger_claims(claims)
        out = cl.lexical_shortlist(
            "tomato was chosen as the crop for the experiment", records, k=8
        )
        assert any("tomato" in r.claim_summary.lower() for r in out)

    def test_end_to_end_slice_offline(self):
        from harness.status_faithfulness import load_section_claims

        path = self._section_path("excellence")
        prose = cl.load_section_prose(path)
        claims = load_section_claims(path)
        judge, backend = make_judge(
            always({"passed": True, "covered_by": 1, "rationale": "stub"})
        )
        result = cl.evaluate_ledger_completeness(
            prose,
            claims,
            judge,
            section_id="excellence",
            sub_section_filter=lambda s: s.sub_section_id == "1.1",
            decomposer=lambda c: (c.text.split("\n\n")[0][:200],),  # stub: 1st para head
            materiality_classifier=_classifier({}),
        )
        assert result.findings  # every chunk yielded an assertion finding
        assert result.build_report().blocking is False
        assert backend.calls  # coverage judge exercised offline
