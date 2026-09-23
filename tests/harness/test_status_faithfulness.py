"""
Tests for harness/status_faithfulness.py — the E2 status-aware faithfulness metric.

Fully offline: the judge is driven by an injected fake backend (no network), and
source text is either injected via ``source_text_resolver`` or read from a
``tmp_path`` fixture, so nothing here touches a live model or a real DAG run.

Coverage:
  - SectionClaim / load_section_claims (schema, status lowercasing, fail-closed)
  - source-ref resolution: fragment (#id) + trailing annotation, whole-file
    fallback, non-JSON source, missing file, char bound
  - StatusPolicy / meets_bar / classify_severity (strict vs soft bars)
  - prompt builders (per-status standard, SOURCE PASSAGE vs DECLARED VALUE)
  - evaluate_claim per status: confirmed→source, assumed→declared value,
    inferred→soft; the "gap masked as confirmed" hard finding; un-judged cases
  - routing enforcement (a predicate-named property is refused)
  - whole-section evaluate + advisory report boundary + provenance
  - M3 baseline freeze / compare invariance (regression, status change, drop,
    score drop, added, judge repin)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import pytest

from harness.judge import Judge, JudgeConfig
from harness.provenance import ProvenanceLog
from harness.routing import DeterministicCoverageError, deterministic_predicate_names
from harness.verdict import Verdict
from runner.working_assumptions import Declaration, WorkingAssumptions
import harness.status_faithfulness as sf


# --------------------------------------------------------------------------- #
# Fakes
# --------------------------------------------------------------------------- #


class RuleBackend:
    """A fake OpenAI-compatible backend: (system, user) → JSON verdict dict."""

    def __init__(self, rule: Callable[[str, str], dict[str, Any]]) -> None:
        self._rule = rule
        self.calls: list[tuple[str, str]] = []

    def __call__(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        system = messages[0]["content"]
        user = messages[1]["content"]
        self.calls.append((system, user))
        return {"content": json.dumps(self._rule(system, user)), "tool_calls": None}


def make_judge(
    rule: Callable[[str, str], dict[str, Any]],
    *,
    provenance_log: ProvenanceLog | None = None,
) -> tuple[Judge, RuleBackend]:
    backend = RuleBackend(rule)
    judge = Judge(
        JudgeConfig(model="acme-judge-1", version="v1"),
        backend=backend,
        provenance_log=provenance_log,
    )
    return judge, backend


def always(payload: dict[str, Any]) -> Callable[[str, str], dict[str, Any]]:
    return lambda system, user: dict(payload)


EMPTY_WA = WorkingAssumptions(present=True)


def claim(cid="C1", summary="the claim", status="confirmed", source_ref="docs/x.json"):
    return sf.SectionClaim(
        claim_id=cid, claim_summary=summary, status=status, source_ref=source_ref
    )


def fixed_source(text: str) -> sf.SourceTextResolver:
    return lambda source_ref, repo_root: text


# --------------------------------------------------------------------------- #
# SectionClaim / load_section_claims
# --------------------------------------------------------------------------- #


class TestSectionClaim:
    def test_from_dict_lowercases_status(self):
        c = sf.SectionClaim.from_dict(
            {"claim_id": "C1", "claim_summary": "x", "status": "Confirmed", "source_ref": "d"}
        )
        assert c.status == "confirmed"

    def test_empty_claim_summary_raises(self):
        with pytest.raises(sf.StatusFaithfulnessError):
            sf.SectionClaim(claim_id="C1", claim_summary="  ", status="confirmed", source_ref="d")

    def test_empty_claim_id_raises(self):
        with pytest.raises(sf.StatusFaithfulnessError):
            sf.SectionClaim(claim_id="", claim_summary="x", status="confirmed", source_ref="d")

    def test_load_section_claims(self, tmp_path):
        section = {
            "validation_status": {
                "claim_statuses": [
                    {"claim_id": "C1", "claim_summary": "a", "status": "confirmed", "source_ref": "d1"},
                    {"claim_id": "C2", "claim_summary": "b", "status": "inferred", "source_ref": "d2"},
                ]
            }
        }
        p = tmp_path / "sec.json"
        p.write_text(json.dumps(section), encoding="utf-8")
        claims = sf.load_section_claims(p)
        assert [c.claim_id for c in claims] == ["C1", "C2"]
        assert claims[1].status == "inferred"

    def test_load_missing_file_raises(self, tmp_path):
        with pytest.raises(sf.StatusFaithfulnessError, match="not found"):
            sf.load_section_claims(tmp_path / "nope.json")

    def test_load_no_claim_statuses_raises(self, tmp_path):
        p = tmp_path / "sec.json"
        p.write_text(json.dumps({"validation_status": {}}), encoding="utf-8")
        with pytest.raises(sf.StatusFaithfulnessError, match="claim_statuses"):
            sf.load_section_claims(p)


# --------------------------------------------------------------------------- #
# Source-ref resolution
# --------------------------------------------------------------------------- #


class TestSplitSourceRef:
    def test_bare_path(self):
        assert sf._split_source_ref("docs/x.json") == ("docs/x.json", None)

    def test_fragment(self):
        assert sf._split_source_ref("docs/x.json#FELLOW") == ("docs/x.json", "FELLOW")

    def test_fragment_with_trailing_annotation(self):
        path, frag = sf._split_source_ref(
            "docs/a/impacts.json#IMP-1 (validation_status: Inferred x)"
        )
        assert (path, frag) == ("docs/a/impacts.json", "IMP-1")


class TestResolveClaimSourceText:
    def _write(self, tmp_path, rel, obj):
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(obj), encoding="utf-8")
        return p

    def test_fragment_by_id_in_list(self, tmp_path):
        self._write(
            tmp_path,
            "docs/spine.json",
            {"spine_identity": [{"id": "FELLOW", "confirmed_value": "Dr. Example"}]},
        )
        txt = sf.resolve_claim_source_text("docs/spine.json#FELLOW", tmp_path)
        assert "Dr. Example" in txt
        assert "FELLOW" in txt  # id string leaf is rendered too

    def test_fragment_not_found_falls_back_to_whole_file(self, tmp_path):
        self._write(tmp_path, "docs/a.json", {"k": "wholetext"})
        txt = sf.resolve_claim_source_text("docs/a.json#NOPE", tmp_path)
        assert "wholetext" in txt

    def test_non_json_source_returns_raw(self, tmp_path):
        p = tmp_path / "docs" / "notes.md"
        p.parent.mkdir(parents=True)
        p.write_text("# heading\nplain markdown body", encoding="utf-8")
        txt = sf.resolve_claim_source_text("docs/notes.md", tmp_path)
        assert "plain markdown body" in txt

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(sf.SourceResolutionError, match="none of the cited paths exist"):
            sf.resolve_claim_source_text("docs/missing.json", tmp_path)

    def test_compound_ref_concatenates_both_sources(self, tmp_path):
        self._write(tmp_path, "docs/a.json", {"k": "AAA"})
        self._write(tmp_path, "docs/b.json", {"k": "BBB"})
        txt = sf.resolve_claim_source_text("docs/a.json (x) and docs/b.json (y)", tmp_path)
        assert "AAA" in txt and "BBB" in txt
        assert "[source: docs/a.json]" in txt  # labelled when multi-source

    def test_semicolon_separated_ref(self, tmp_path):
        self._write(tmp_path, "docs/a.json", {"k": "AAA"})
        self._write(tmp_path, "docs/b.json", {"k": "BBB"})
        txt = sf.resolve_claim_source_text("docs/a.json; docs/b.json", tmp_path)
        assert "AAA" in txt and "BBB" in txt

    def test_hint_narrows_whole_file_to_matching_id(self, tmp_path):
        self._write(
            tmp_path, "docs/spine.json",
            {"spine_identity": [
                {"id": "FELLOW", "confirmed_value": "the fellow entry"},
                {"id": "HOST", "confirmed_value": "UNRELATED-HOST-TEXT"},
            ]},
        )
        txt = sf.resolve_claim_source_text("docs/spine.json (spine_identity FELLOW)", tmp_path)
        assert "the fellow entry" in txt
        assert "UNRELATED-HOST-TEXT" not in txt  # narrowed to FELLOW, not the whole file

    def test_partial_resolution_notes_missing_but_returns_present(self, tmp_path):
        self._write(tmp_path, "docs/a.json", {"k": "PRESENT"})
        txt = sf.resolve_claim_source_text("docs/a.json (x) and docs/gone.json (y)", tmp_path)
        assert "PRESENT" in txt
        assert "not found" in txt and "docs/gone.json" in txt

    def test_trailing_prose_after_path_is_ignored(self, tmp_path):
        # A ref that trails an English sentence (containing 'and' and parens) must
        # still resolve the real path and not mistake the prose for a source.
        self._write(tmp_path, "docs/a.json", {"k": "REAL"})
        ref = "docs/a.json (researcher) — the fellow (plant science) and the host (geoinformatics)"
        txt = sf.resolve_claim_source_text(ref, tmp_path)
        assert "REAL" in txt
        assert "not found" not in txt  # the prose tail is dropped, not a missing source

    def test_truncation_is_loud_not_silent(self, tmp_path):
        # A source that exceeds the cap must NOT be silently truncated — a silent
        # drop of the grounding sentence could manufacture a false integrity
        # finding on the headline signal (Spec (c)).
        self._write(tmp_path, "docs/big.json", {"blob": "x" * 5000})
        txt = sf.resolve_claim_source_text("docs/big.json", tmp_path, max_chars=100)
        assert "SOURCE TRUNCATED" in txt
        assert "x" * 100 in txt  # the retained head is present

    def test_no_marker_when_within_cap(self, tmp_path):
        self._write(tmp_path, "docs/small.json", {"blob": "short"})
        txt = sf.resolve_claim_source_text("docs/small.json", tmp_path)
        assert "SOURCE TRUNCATED" not in txt

    def test_real_checklist_blob_not_truncated_at_default_cap(self):
        # The real whole-file cite (confirmation_checklist.json, ~6.5KB rendered)
        # must fit under the default cap so no confirmed claim is judged against a
        # silently-cut source.
        root = Path(__file__).resolve().parents[2]
        ref = "docs/tier3_project_instantiation/call_binding/confirmation_checklist.json"
        if not (root / ref).is_file():
            pytest.skip("confirmation_checklist.json not present")
        txt = sf.resolve_claim_source_text(ref, root)
        assert "SOURCE TRUNCATED" not in txt


# --------------------------------------------------------------------------- #
# Policy / meets_bar / severity
# --------------------------------------------------------------------------- #


class TestPolicyAndBar:
    def test_default_policies_shape(self):
        assert sf.DEFAULT_POLICIES["confirmed"].comparison == sf.COMPARISON_SOURCE
        assert sf.DEFAULT_POLICIES["confirmed"].strict is True
        assert sf.DEFAULT_POLICIES["inferred"].strict is False
        assert sf.DEFAULT_POLICIES["assumed"].comparison == sf.COMPARISON_DECLARED_VALUE

    def test_min_score_out_of_range_rejected(self):
        with pytest.raises(ValueError):
            sf.StatusPolicy("s", sf.COMPARISON_SOURCE, min_score=1.5, strict=True, fail_severity=sf.SEVERITY_SOFT)

    def _v(self, passed=None, score=None):
        return Verdict(metric="m", property_key="k", passed=passed, score=score)

    def test_strict_boolean_only_when_score_does_not_inform(self):
        # n==1: a single sample's score never drives the decision — boolean governs.
        pol = sf.DEFAULT_POLICIES["confirmed"]
        assert sf.meets_bar(pol, self._v(passed=True, score=0.5)) is True  # score ignored at n=1
        assert sf.meets_bar(pol, self._v(passed=False, score=0.95)) is False
        assert sf.meets_bar(pol, self._v(passed=True)) is True

    def test_strict_score_floor_applies_only_when_score_informs(self):
        # n>=3: the ≈1.0 floor kicks in.
        pol = sf.DEFAULT_POLICIES["confirmed"]
        assert sf.meets_bar(pol, self._v(passed=True, score=0.95), score_informs_decision=True) is True
        assert sf.meets_bar(pol, self._v(passed=True, score=0.5), score_informs_decision=True) is False
        assert sf.meets_bar(pol, self._v(passed=False, score=0.95), score_informs_decision=True) is False
        # No score present → boolean governs even when a score would inform.
        assert sf.meets_bar(pol, self._v(passed=True), score_informs_decision=True) is True

    def test_soft_boolean_carries_at_n1_score_rescues_only_when_informing(self):
        pol = sf.DEFAULT_POLICIES["inferred"]
        assert sf.meets_bar(pol, self._v(passed=True, score=0.2)) is True  # boolean carries it
        # At n=1 a score cannot rescue a passed=False inferred claim.
        assert sf.meets_bar(pol, self._v(passed=False, score=0.6)) is False
        # With a majority panel, the score may rescue it.
        assert sf.meets_bar(pol, self._v(passed=False, score=0.6), score_informs_decision=True) is True
        assert sf.meets_bar(pol, self._v(passed=False, score=0.3), score_informs_decision=True) is False

    def test_neither_signal_never_meets_bar(self):
        pol = sf.DEFAULT_POLICIES["inferred"]
        assert sf.meets_bar(pol, self._v()) is False
        assert sf.meets_bar(pol, self._v(), score_informs_decision=True) is False

    def test_classify_severity(self):
        pol = sf.DEFAULT_POLICIES["confirmed"]
        assert sf.classify_severity(pol, self._v(passed=True, score=0.95)) == sf.SEVERITY_NONE
        assert sf.classify_severity(pol, self._v(passed=False)) == sf.SEVERITY_INTEGRITY
        # score below the floor is only an integrity finding when the score informs.
        assert sf.classify_severity(pol, self._v(passed=True, score=0.5)) == sf.SEVERITY_NONE
        assert (
            sf.classify_severity(pol, self._v(passed=True, score=0.5), score_informs_decision=True)
            == sf.SEVERITY_INTEGRITY
        )


# --------------------------------------------------------------------------- #
# Prompt builders
# --------------------------------------------------------------------------- #


class TestPrompts:
    def test_confirmed_standard_and_source_label(self):
        sys, usr = sf.build_faithfulness_prompt_for_status(
            "confirmed", "the claim", "the source", comparison=sf.COMPARISON_SOURCE, source_ref="docs/x.json"
        )
        assert "CONFIRMED" in sys
        assert "different model" in sys
        assert "SOURCE PASSAGE" in usr
        assert "SOURCE REF (label only): docs/x.json" in usr

    def test_assumed_declared_value_label_no_source_ref(self):
        sys, usr = sf.build_faithfulness_prompt_for_status(
            "assumed", "the claim", "BE", comparison=sf.COMPARISON_DECLARED_VALUE, source_ref="ignored"
        )
        assert "ASSUMED" in sys
        assert "DECLARED VALUE" in usr
        assert "SOURCE REF" not in usr  # a declared value has no source ref line

    def test_inferred_soft_standard(self):
        sys, _ = sf.build_faithfulness_prompt_for_status(
            "inferred", "c", "s", comparison=sf.COMPARISON_SOURCE
        )
        assert "INFERRED" in sys
        assert "SOFTER" in sys

    def test_unknown_status_raises(self):
        with pytest.raises(sf.StatusFaithfulnessError):
            sf.build_faithfulness_prompt_for_status("weird", "c", "s", comparison=sf.COMPARISON_SOURCE)


# --------------------------------------------------------------------------- #
# evaluate_claim — per status
# --------------------------------------------------------------------------- #


class TestEvaluateClaimConfirmed:
    def test_supported_confirmed_is_clean(self):
        judge, _ = make_judge(always({"passed": True, "score": 0.97, "rationale": "stated"}))
        cf = sf.evaluate_claim(
            judge, claim(status="confirmed"), repo_root=Path("."),
            working_assumptions=EMPTY_WA, source_text_resolver=fixed_source("states the claim"),
        )
        assert cf.severity == sf.SEVERITY_NONE
        assert cf.flagged is False
        assert cf.comparison == sf.COMPARISON_SOURCE

    def test_unsupported_confirmed_is_hard_integrity_finding(self):
        judge, _ = make_judge(always({"passed": False, "score": 0.1, "rationale": "silent"}))
        cf = sf.evaluate_claim(
            judge, claim(status="confirmed"), repo_root=Path("."),
            working_assumptions=EMPTY_WA, source_text_resolver=fixed_source("unrelated"),
        )
        assert cf.severity == sf.SEVERITY_INTEGRITY
        assert cf.is_hard_finding is True
        assert cf.flagged is True

    def test_confirmed_judged_against_source_text(self):
        judge, backend = make_judge(always({"passed": True, "rationale": "ok"}))
        sf.evaluate_claim(
            judge, claim(status="confirmed", summary="THE-CLAIM"), repo_root=Path("."),
            working_assumptions=EMPTY_WA, source_text_resolver=fixed_source("SRC-TEXT-XYZ"),
        )
        _, user = backend.calls[0]
        assert "THE-CLAIM" in user and "SRC-TEXT-XYZ" in user

    def test_unresolved_source_is_flagged_not_judged(self):
        def boom(source_ref, repo_root):
            raise sf.SourceResolutionError("gone")

        judge, backend = make_judge(always({"passed": True}))
        cf = sf.evaluate_claim(
            judge, claim(status="confirmed"), repo_root=Path("."),
            working_assumptions=EMPTY_WA, source_text_resolver=boom,
        )
        assert cf.severity == sf.SEVERITY_UNRESOLVED
        assert cf.verdict is None
        assert backend.calls == []  # judge never invoked without a source


class TestEvaluateClaimInferred:
    def test_inferred_score_rescues_only_with_majority_panel(self):
        # passed=False, score=0.6 → at n=1 the score cannot rescue (boolean governs)…
        judge, _ = make_judge(always({"passed": False, "score": 0.6, "rationale": "framing ok"}))
        cf1 = sf.evaluate_claim(
            judge, claim(status="inferred"), repo_root=Path("."),
            working_assumptions=EMPTY_WA, source_text_resolver=fixed_source("related context"),
        )
        assert cf1.severity == sf.SEVERITY_SOFT  # single sample: score does not inform
        # …but with an N>=3 panel the score clears the soft bar.
        judge3, _ = make_judge(always({"passed": False, "score": 0.6, "rationale": "framing ok"}))
        cf3 = sf.evaluate_claim(
            judge3, claim(status="inferred"), repo_root=Path("."),
            working_assumptions=EMPTY_WA, n=3, source_text_resolver=fixed_source("related context"),
        )
        assert cf3.severity == sf.SEVERITY_NONE

    def test_inferred_below_soft_bar_is_soft_finding(self):
        judge, _ = make_judge(always({"passed": False, "score": 0.2, "rationale": "unsupported"}))
        cf = sf.evaluate_claim(
            judge, claim(status="inferred"), repo_root=Path("."),
            working_assumptions=EMPTY_WA, source_text_resolver=fixed_source("unrelated"),
        )
        assert cf.severity == sf.SEVERITY_SOFT
        assert cf.is_hard_finding is False  # soft is a concern, not a hard finding
        assert cf.flagged is True


class TestEvaluateClaimAssumed:
    def _wa(self, key="host_country", value="BE", checklist_ref=None):
        return WorkingAssumptions(
            present=True,
            declarations=(
                Declaration(
                    key=key, value=value, declared_by="op@x", declared_on="2026-07-13T00:00:00Z",
                    checklist_ref=checklist_ref,
                ),
            ),
        )

    def test_assumed_judged_against_declared_value_by_key(self):
        judge, backend = make_judge(always({"passed": True, "score": 0.95, "rationale": "matches"}))
        wa = self._wa(key="HOST", value="Belgium")
        cf = sf.evaluate_claim(
            judge, claim(cid="HOST", status="assumed", summary="Host is in Belgium"),
            repo_root=Path("."), working_assumptions=wa,
            source_text_resolver=fixed_source("SHOULD-NOT-BE-USED"),
        )
        assert cf.severity == sf.SEVERITY_NONE
        assert cf.comparison == sf.COMPARISON_DECLARED_VALUE
        _, user = backend.calls[0]
        assert "DECLARED VALUE" in user and "Belgium" in user
        assert "SHOULD-NOT-BE-USED" not in user  # source is NOT consulted for assumed

    def test_assumed_bridged_by_checklist_ref(self):
        judge, backend = make_judge(always({"passed": True, "rationale": "ok"}))
        wa = self._wa(key="host_country", value="BE", checklist_ref="HOST")
        cf = sf.evaluate_claim(
            judge, claim(cid="HOST", status="assumed", summary="Host country BE"),
            repo_root=Path("."), working_assumptions=wa, source_text_resolver=fixed_source("x"),
        )
        assert cf.severity == sf.SEVERITY_NONE
        _, user = backend.calls[0]
        assert "BE" in user

    def test_assumed_content_drift_when_claim_mismatches_declared(self):
        judge, _ = make_judge(always({"passed": False, "score": 0.1, "rationale": "differs"}))
        wa = self._wa(key="HOST", value="Belgium")
        cf = sf.evaluate_claim(
            judge, claim(cid="HOST", status="assumed", summary="Host is in Germany"),
            repo_root=Path("."), working_assumptions=wa, source_text_resolver=fixed_source("x"),
        )
        assert cf.severity == sf.SEVERITY_CONTENT_DRIFT
        assert cf.is_hard_finding is True

    def test_assumed_without_declaration_is_unresolved_not_judged(self):
        judge, backend = make_judge(always({"passed": True}))
        cf = sf.evaluate_claim(
            judge, claim(cid="HOST", status="assumed", summary="Host is X"),
            repo_root=Path("."), working_assumptions=EMPTY_WA, source_text_resolver=fixed_source("x"),
        )
        assert cf.severity == sf.SEVERITY_UNRESOLVED
        assert cf.verdict is None
        assert backend.calls == []


class TestEvaluateClaimEdgeCases:
    def test_unknown_status_surfaced_not_judged(self):
        judge, backend = make_judge(always({"passed": True}))
        cf = sf.evaluate_claim(
            judge, claim(status="provisional"), repo_root=Path("."),
            working_assumptions=EMPTY_WA, source_text_resolver=fixed_source("x"),
        )
        assert cf.severity == sf.SEVERITY_UNKNOWN_STATUS
        assert cf.verdict is None
        assert backend.calls == []

    def test_routing_refuses_predicate_named_claim(self):
        predicate_name = next(iter(deterministic_predicate_names()))
        judge, _ = make_judge(always({"passed": True}))
        with pytest.raises(DeterministicCoverageError):
            sf.evaluate_claim(
                judge, claim(cid=predicate_name, status="confirmed"), repo_root=Path("."),
                working_assumptions=EMPTY_WA, source_text_resolver=fixed_source("x"),
            )

    def test_n_two_rejected(self):
        judge, _ = make_judge(always({"passed": True}))
        with pytest.raises(ValueError, match="tie"):
            sf.evaluate_claim(
                judge, claim(status="confirmed"), repo_root=Path("."),
                working_assumptions=EMPTY_WA, n=2, source_text_resolver=fixed_source("x"),
            )

    def test_majority_n3_produces_majority_verdict(self):
        judge, backend = make_judge(always({"passed": True, "score": 0.9, "rationale": "ok"}))
        cf = sf.evaluate_claim(
            judge, claim(status="confirmed"), repo_root=Path("."),
            working_assumptions=EMPTY_WA, n=3, source_text_resolver=fixed_source("supports"),
        )
        assert len(backend.calls) == 3
        assert cf.severity == sf.SEVERITY_NONE
        assert cf.verdict.n == 3  # a MajorityVerdict

    def test_provenance_logged_per_verdict(self, tmp_path):
        log = ProvenanceLog(tmp_path / "prov.jsonl")
        judge, _ = make_judge(always({"passed": True, "rationale": "ok"}), provenance_log=log)
        sf.evaluate_claim(
            judge, claim(status="confirmed"), repo_root=Path("."),
            working_assumptions=EMPTY_WA, source_text_resolver=fixed_source("supports"),
        )
        assert len(log) == 1
        rec = log.records()[0]
        assert rec["judge_model"] == "acme-judge-1" and rec["metric"] == sf.STATUS_AWARE_FAITHFULNESS_METRIC


# --------------------------------------------------------------------------- #
# Whole-section evaluation + report
# --------------------------------------------------------------------------- #


class TestEvaluateSection:
    def _claims(self):
        return [
            claim(cid="C1", status="confirmed", summary="confirmed-good"),
            claim(cid="C2", status="confirmed", summary="confirmed-bad"),
            claim(cid="C3", status="inferred", summary="inferred-ok"),
        ]

    def _rule(self, system, user):
        # confirmed-bad → unsupported; everything else supported.
        if "confirmed-bad" in user:
            return {"passed": False, "score": 0.1, "rationale": "silent"}
        return {"passed": True, "score": 0.95, "rationale": "ok"}

    def test_partitions_and_surfaces_integrity(self):
        judge, _ = make_judge(self._rule)
        result = sf.evaluate_status_aware_faithfulness(
            self._claims(), judge, repo_root=Path("."), working_assumptions=EMPTY_WA,
            section_id="excellence", source_text_resolver=fixed_source("SRC"),
        )
        assert len(result.findings) == 3
        integ = result.integrity_findings()
        assert [f.claim_id for f in integ] == ["C2"]
        assert result.severity_counts[sf.SEVERITY_INTEGRITY] == 1
        assert set(result.by_status().keys()) == {"confirmed", "inferred"}

    def test_claim_filter_subsets(self):
        judge, backend = make_judge(self._rule)
        result = sf.evaluate_status_aware_faithfulness(
            self._claims(), judge, repo_root=Path("."), working_assumptions=EMPTY_WA,
            source_text_resolver=fixed_source("SRC"),
            claim_filter=lambda c: c.status == "confirmed",
        )
        assert [f.claim_id for f in result.findings] == ["C1", "C2"]

    def test_report_is_advisory_and_never_blocking(self):
        judge, _ = make_judge(self._rule)
        result = sf.evaluate_status_aware_faithfulness(
            self._claims(), judge, repo_root=Path("."), working_assumptions=EMPTY_WA,
            source_text_resolver=fixed_source("SRC"),
        )
        report = result.build_report()
        assert report.advisory is True and report.blocking is False
        assert report.metric == sf.STATUS_AWARE_FAITHFULNESS_METRIC
        assert report.judge_model == "acme-judge-1"
        # findings in the report are the real judge verdicts (3 judged claims)
        assert report.summary["total"] == 3
        assert "hard_findings=1" in report.notes

    def test_routing_decisions_collected(self):
        judge, _ = make_judge(self._rule)
        result = sf.evaluate_status_aware_faithfulness(
            self._claims(), judge, repo_root=Path("."), working_assumptions=EMPTY_WA,
            source_text_resolver=fixed_source("SRC"),
        )
        assert len(result.routing) == 3
        assert all(r.judge_permitted for r in result.routing)


# --------------------------------------------------------------------------- #
# M3 baseline freeze + invariance
# --------------------------------------------------------------------------- #


def _finding(cid, status, severity, passed=None, score=None):
    v = None
    if passed is not None or score is not None:
        v = Verdict(metric=sf.STATUS_AWARE_FAITHFULNESS_METRIC, property_key=cid, passed=passed, score=score)
    return sf.ClaimFaithfulness(
        claim_id=cid, status=status, comparison=sf.COMPARISON_SOURCE,
        comparison_ref="x", severity=severity, verdict=v,
    )


def _result(findings, model="acme-judge-1", version="v1", section="excellence"):
    return sf.StatusFaithfulnessResult(
        section_id=section, findings=tuple(findings), judge_model=model, judge_version=version
    )


class TestM3Baseline:
    def _base(self):
        return _result([
            _finding("C1", "confirmed", sf.SEVERITY_NONE, passed=True, score=0.95),
            _finding("C2", "inferred", sf.SEVERITY_NONE, passed=True, score=0.7),
        ])

    def test_freeze_and_roundtrip(self, tmp_path):
        base = sf.freeze_baseline(self._base(), baseline_id="b1")
        p = tmp_path / "base.json"
        sf.write_baseline(base, p)
        loaded = sf.load_baseline(p)
        assert loaded.baseline_id == "b1"
        assert set(loaded.by_id()) == {"C1", "C2"}
        assert loaded.applies_to("acme-judge-1", "v1")
        assert not loaded.applies_to("other", "v1")

    def test_identical_rerun_is_invariant(self):
        base = sf.freeze_baseline(self._base())
        rep = sf.compare_to_baseline(base, self._base())
        assert rep.invariant is True
        assert rep.violations == ()
        assert rep.compared == 2

    def test_bar_regression_breaks_invariance(self):
        base = sf.freeze_baseline(self._base())
        weakened = _result([
            _finding("C1", "confirmed", sf.SEVERITY_INTEGRITY, passed=False, score=0.1),
            _finding("C2", "inferred", sf.SEVERITY_NONE, passed=True, score=0.7),
        ])
        rep = sf.compare_to_baseline(base, weakened)
        assert rep.invariant is False
        kinds = {(v.claim_id, v.kind) for v in rep.breaking_violations}
        assert ("C1", sf.VIOLATION_BAR_REGRESSION) in kinds

    def test_status_change_breaks_invariance(self):
        base = sf.freeze_baseline(self._base())
        mutated = _result([
            _finding("C1", "inferred", sf.SEVERITY_NONE, passed=True, score=0.95),  # was confirmed
            _finding("C2", "inferred", sf.SEVERITY_NONE, passed=True, score=0.7),
        ])
        rep = sf.compare_to_baseline(base, mutated)
        assert rep.invariant is False
        assert any(v.kind == sf.VIOLATION_STATUS_CHANGED for v in rep.violations)

    def test_dropped_claim_breaks_invariance(self):
        base = sf.freeze_baseline(self._base())
        dropped = _result([_finding("C1", "confirmed", sf.SEVERITY_NONE, passed=True, score=0.95)])
        rep = sf.compare_to_baseline(base, dropped)
        assert rep.invariant is False
        assert any(v.kind == sf.VIOLATION_DROPPED and v.claim_id == "C2" for v in rep.violations)

    def test_score_drop_is_soft_not_breaking(self):
        base = sf.freeze_baseline(self._base())
        score_dropped = _result([
            _finding("C1", "confirmed", sf.SEVERITY_NONE, passed=True, score=0.95),
            _finding("C2", "inferred", sf.SEVERITY_NONE, passed=True, score=0.4),  # dropped 0.7→0.4, still meets bar
        ])
        rep = sf.compare_to_baseline(base, score_dropped)
        assert rep.invariant is True  # score drop does not break invariance
        assert any(v.kind == sf.VIOLATION_SCORE_DROP and not v.breaking for v in rep.violations)

    def test_added_claim_surfaced_not_breaking(self):
        base = sf.freeze_baseline(self._base())
        added = _result([
            _finding("C1", "confirmed", sf.SEVERITY_NONE, passed=True, score=0.95),
            _finding("C2", "inferred", sf.SEVERITY_NONE, passed=True, score=0.7),
            _finding("C3", "confirmed", sf.SEVERITY_NONE, passed=True, score=0.9),
        ])
        rep = sf.compare_to_baseline(base, added)
        assert rep.invariant is True
        assert rep.added_claim_ids == ("C3",)

    def test_judge_repin_flagged(self):
        base = sf.freeze_baseline(self._base())
        repinned = _result([
            _finding("C1", "confirmed", sf.SEVERITY_NONE, passed=True, score=0.95),
            _finding("C2", "inferred", sf.SEVERITY_NONE, passed=True, score=0.7),
        ], model="acme-judge-2", version="v2")
        rep = sf.compare_to_baseline(base, repinned)
        assert rep.judge_repinned is True


# --------------------------------------------------------------------------- #
# Claim identity — duplicate claim_ids disambiguated by entry_index/entry_key
# --------------------------------------------------------------------------- #


class TestClaimIdentityDisambiguation:
    """Real ledgers repeat claim_ids across independently-numbered drafting
    blocks (excellence: 191 entries / 128 unique ids; three unrelated C01s), so
    claim_id alone is not a key.  entry_index (position in claim_statuses) and
    the derived entry_key ("C01#7") disambiguate every downstream surface."""

    def test_load_section_claims_populates_entry_index(self, tmp_path):
        section = {
            "validation_status": {
                "claim_statuses": [
                    {"claim_id": "C1", "claim_summary": "a", "status": "confirmed", "source_ref": "d1"},
                    {"claim_id": "C1", "claim_summary": "b", "status": "inferred", "source_ref": "d2"},
                ]
            }
        }
        p = tmp_path / "sec.json"
        p.write_text(json.dumps(section), encoding="utf-8")
        claims = sf.load_section_claims(p)
        assert [c.entry_index for c in claims] == [0, 1]
        assert [c.entry_key for c in claims] == ["C1#0", "C1#1"]

    def test_entry_key_falls_back_to_claim_id_without_index(self):
        c = claim(cid="C7")
        assert c.entry_index is None
        assert c.entry_key == "C7"

    def test_duplicate_ids_get_distinct_property_keys_and_hard_finding_ids(self):
        # Two unrelated claims sharing the id "C01" (the real C01 collision):
        # the unsupported one must be reportable without ambiguity.
        claims = [
            sf.SectionClaim(
                claim_id="C01", claim_summary="crop is tomato", status="confirmed",
                source_ref="docs/a.json", entry_index=0,
            ),
            sf.SectionClaim(
                claim_id="C01", claim_summary="the fellow is Dr. X", status="confirmed",
                source_ref="docs/b.json", entry_index=171,
            ),
        ]

        def rule(system, user):
            return {"passed": "tomato" in user, "score": 0.9, "rationale": "r"}

        judge, _ = make_judge(rule)
        result = sf.evaluate_status_aware_faithfulness(
            claims, judge, repo_root=Path("."), working_assumptions=EMPTY_WA,
            source_text_resolver=fixed_source("SRC"),
        )
        keys = [f.verdict.property_key for f in result.findings]
        assert keys == ["C01#0", "C01#171"]
        assert result.to_dict()["hard_finding_ids"] == ["C01#171"]
        assert [f.entry_key for f in result.integrity_findings()] == ["C01#171"]

    def test_baseline_does_not_collapse_duplicate_ids(self):
        findings = [
            _finding("C01", "confirmed", sf.SEVERITY_NONE, passed=True, score=0.95),
            _finding("C01", "confirmed", sf.SEVERITY_NONE, passed=True, score=0.9),
        ]
        findings = [
            sf.ClaimFaithfulness(
                claim_id=f.claim_id, status=f.status, comparison=f.comparison,
                comparison_ref=f.comparison_ref, severity=f.severity,
                verdict=f.verdict, entry_index=i,
            )
            for i, f in enumerate(findings)
        ]
        base = sf.freeze_baseline(_result(findings))
        assert len(base.by_id()) == 2  # not collapsed to one "C01"
        rep = sf.compare_to_baseline(base, _result(findings))
        assert rep.invariant is True
        assert rep.compared == 2

    def test_baseline_regression_names_the_exact_entry(self):
        def with_index(f, i):
            return sf.ClaimFaithfulness(
                claim_id=f.claim_id, status=f.status, comparison=f.comparison,
                comparison_ref=f.comparison_ref, severity=f.severity,
                verdict=f.verdict, entry_index=i,
            )

        base_findings = [
            with_index(_finding("C01", "confirmed", sf.SEVERITY_NONE, passed=True), 0),
            with_index(_finding("C01", "confirmed", sf.SEVERITY_NONE, passed=True), 171),
        ]
        weakened = [
            with_index(_finding("C01", "confirmed", sf.SEVERITY_NONE, passed=True), 0),
            with_index(_finding("C01", "confirmed", sf.SEVERITY_INTEGRITY, passed=False), 171),
        ]
        base = sf.freeze_baseline(_result(base_findings))
        rep = sf.compare_to_baseline(base, _result(weakened))
        assert rep.invariant is False
        assert [v.claim_id for v in rep.breaking_violations] == ["C01#171"]

    def test_old_baseline_without_entry_index_still_loads(self, tmp_path):
        # A baseline written before entry_index existed keys by bare claim_id.
        old = {
            "record_type": "status_faithfulness_baseline",
            "baseline_id": "b-old",
            "section_id": "s",
            "judge_model": "acme-judge-1",
            "judge_version": "v1",
            "snapshots": [
                {"claim_id": "C1", "status": "confirmed", "comparison": "source",
                 "severity": "none", "met_bar": True, "passed": True, "score": 0.9},
            ],
        }
        p = tmp_path / "old.json"
        p.write_text(json.dumps(old), encoding="utf-8")
        loaded = sf.load_baseline(p)
        assert set(loaded.by_id()) == {"C1"}
        assert loaded.snapshots[0].entry_index is None


# --------------------------------------------------------------------------- #
# Integration on the real excellence section (offline, injected judge)
# --------------------------------------------------------------------------- #


class TestRealSectionOffline:
    """Exercises load + real fragment resolution + partitioning on real data,
    with a deterministic injected judge (no network)."""

    def _repo_root(self) -> Path:
        # tests/ is directly under the repo root
        return Path(__file__).resolve().parents[2]

    def test_all_supported_yields_no_integrity_findings(self):
        root = self._repo_root()
        section = root / "docs/tier5_deliverables/proposal_sections/excellence_section.json"
        if not section.is_file():
            pytest.skip("excellence_section.json not present")
        claims = sf.load_section_claims(section)
        judge, _ = make_judge(always({"passed": True, "score": 0.95, "rationale": "ok"}))
        # limit to a small deterministic slice to keep the test fast
        subset = claims[:12]
        result = sf.evaluate_status_aware_faithfulness(
            subset, judge, repo_root=root, working_assumptions=EMPTY_WA, section_id="excellence",
        )
        assert len(result.findings) == len(subset)
        assert result.integrity_findings() == ()  # judge blessed everything → no gap
        assert result.build_report().blocking is False
