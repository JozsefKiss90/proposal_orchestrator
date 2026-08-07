"""
E5d — grounding-axis grader: E2 reuse (one system-of-record, zero new
faithfulness prompts), fail-closed contract, status-aware aggregation, and the
claim-level truncation override.

Everything runs offline against the injectable fake backend — no network.  The
zero-new-prompts assertions are structural + behavioral (test_boundary.py
shape): a static source check that the module builds no prompt, and a
behavioral check that the backend receives exactly E2's status-specific
prompts when a claim is newly judged.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable

import pytest

import harness.expectation_grounding as eg
import harness.status_faithfulness as sf
from harness.evidence_pack import build_evidence_pack
from harness.judge import Judge, JudgeConfig
from harness.provenance import ProvenanceLog
from harness.routing import RoutingAuthority, deterministic_predicate_names, route
from harness.rubrics import Rubric
from harness.verdict import Verdict
from runner.working_assumptions import WorkingAssumptions

REPO_ROOT = Path(__file__).resolve().parents[2]
EMPTY_WA = WorkingAssumptions(present=True)

JUDGE_MODEL, JUDGE_VERSION = "acme-judge-1", "v1"


# --------------------------------------------------------------------------- #
# Fixtures — a synthetic rubric + section whose claims the terms match
# --------------------------------------------------------------------------- #


def make_rubric(key: str = "exc-obj", terms: tuple[str, ...] = ("modelling",)) -> Rubric:
    return Rubric(
        expectation_key=key,
        criterion_id="excellence",
        expectation_text="Soundness of the modelling objectives.",
        rubric="Integrity-framed: addressed AND grounded, never prose quality.",
        evaluation_steps=("Check the spans.", "Check the claims."),
        pass_threshold=0.7,
        selection_terms=terms,
        anchor_sub_section_ids=(),
        source_page=4,
    )


#: (claim_id, summary, status, source_ref) — every summary matches "modelling".
DEFAULT_LEDGER = [
    ("C01", "The modelling objective is beyond the state of the art.", "confirmed", "docs/t3/a.json#x"),
    ("C02", "The modelling method reuses partner tooling.", "confirmed", "docs/t3/b.json"),
    ("C03", "The modelling approach implies broad applicability.", "inferred", "docs/t3/a.json#y"),
    ("C04", "The host provides modelling infrastructure.", "assumed", "docs/t3/c.json"),
]


def write_section(tmp_path: Path, ledger=DEFAULT_LEDGER, prose: str | None = None) -> Path:
    data = {
        "sub_sections": [
            {
                "sub_section_id": "1.1",
                "title": "Objectives",
                "content": prose
                if prose is not None
                else "The modelling objectives are ambitious.",
            }
        ],
        "validation_status": {
            "claim_statuses": [
                {
                    "claim_id": cid,
                    "claim_summary": summary,
                    "status": status,
                    "source_ref": ref,
                }
                for cid, summary, status, ref in ledger
            ]
        },
    }
    p = tmp_path / "excellence_section.json"
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return p


def make_pack(section_path: Path, rubric: Rubric, **kwargs):
    return build_evidence_pack(
        expectation_key=rubric.expectation_key,
        section_path=section_path,
        selection_terms=rubric.selection_terms,
        anchor_sub_section_ids=rubric.anchor_sub_section_ids,
        **kwargs,
    )


def finding_for(
    claim: sf.SectionClaim,
    severity: str,
    *,
    score: float | None = None,
    passed: bool | None = None,
) -> sf.ClaimFaithfulness:
    """A manual E2 finding consistent with *claim* (identity + comparison)."""
    assumed = claim.status == sf.STATUS_ASSUMED
    verdict = None
    if score is not None or passed is not None:
        verdict = Verdict(
            metric=sf.STATUS_AWARE_FAITHFULNESS_METRIC,
            property_key=claim.entry_key,
            passed=passed,
            score=score,
        )
    return sf.ClaimFaithfulness(
        claim_id=claim.claim_id,
        status=claim.status,
        comparison=sf.COMPARISON_DECLARED_VALUE if assumed else sf.COMPARISON_SOURCE,
        comparison_ref=claim.claim_id if assumed else claim.source_ref,
        severity=severity,
        verdict=verdict,
        reason="test finding",
        entry_index=claim.entry_index,
        claim_summary=claim.claim_summary,
    )


def result_for(
    section_path: Path,
    severities: dict[str, str],
    *,
    scores: dict[str, float] | None = None,
    section_id: str | None = None,
) -> sf.StatusFaithfulnessResult:
    """An existing E2 result over the section's ledger, severity per claim_id."""
    claims = sf.load_section_claims(section_path)
    findings = tuple(
        finding_for(
            c,
            severities.get(c.claim_id, sf.SEVERITY_NONE),
            score=(scores or {}).get(c.claim_id),
        )
        for c in claims
    )
    return sf.StatusFaithfulnessResult(
        section_id=section_id if section_id is not None else section_path.stem,
        findings=findings,
        judge_model=JUDGE_MODEL,
        judge_version=JUDGE_VERSION,
    )


class RuleBackend:
    """A fake OpenAI-compatible backend: (system, user) → JSON verdict dict."""

    def __init__(self, rule: Callable[[str, str], dict[str, Any]]) -> None:
        self._rule = rule
        self.calls: list[tuple[str, str]] = []

    def __call__(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        system, user = messages[0]["content"], messages[1]["content"]
        self.calls.append((system, user))
        return {"content": json.dumps(self._rule(system, user)), "tool_calls": None}


def make_judge(
    tmp_path: Path,
    rule: Callable[[str, str], dict[str, Any]] | None = None,
    *,
    with_log: bool = True,
    model: str = JUDGE_MODEL,
    version: str = JUDGE_VERSION,
) -> tuple[Judge, RuleBackend]:
    backend = RuleBackend(
        rule or (lambda s, u: {"passed": True, "score": 0.95, "rationale": "ok"})
    )
    judge = Judge(
        JudgeConfig(model=model, version=version),
        backend=backend,
        provenance_log=(
            ProvenanceLog(tmp_path / "provenance.jsonl") if with_log else None
        ),
    )
    return judge, backend


def fixed_source(text: str) -> sf.SourceTextResolver:
    return lambda source_ref, repo_root: text


# --------------------------------------------------------------------------- #
# Contract — every guard fails closed
# --------------------------------------------------------------------------- #


class TestContract:
    def test_mismatched_pack_refused(self, tmp_path):
        section = write_section(tmp_path)
        other_pack = make_pack(section, make_rubric(key="impl-host"))
        with pytest.raises(eg.GroundingError, match="mismatched"):
            eg.derive_grounding(make_rubric(), other_pack, existing=result_for(section, {}))

    def test_missing_verdicts_without_judge_raise_and_name_the_entries(self, tmp_path):
        section = write_section(tmp_path)
        pack = make_pack(section, make_rubric())
        with pytest.raises(eg.GroundingError, match=r"C01#0"):
            eg.derive_grounding(make_rubric(), pack)

    def test_partial_existing_result_still_fails_closed(self, tmp_path):
        # An existing result missing one pack claim must not silently grade a subset.
        section = write_section(tmp_path)
        pack = make_pack(section, make_rubric())
        full = result_for(section, {})
        partial = sf.StatusFaithfulnessResult(
            section_id=full.section_id,
            findings=full.findings[:-1],
            judge_model=JUDGE_MODEL,
            judge_version=JUDGE_VERSION,
        )
        with pytest.raises(eg.GroundingError, match=r"C04#3"):
            eg.derive_grounding(make_rubric(), pack, existing=partial)

    def test_cross_section_existing_refused(self, tmp_path):
        section = write_section(tmp_path)
        pack = make_pack(section, make_rubric())
        other = result_for(section, {}, section_id="impact_section")
        with pytest.raises(eg.GroundingError, match="cross-section"):
            eg.derive_grounding(make_rubric(), pack, existing=other)

    def test_stale_existing_result_refused(self, tmp_path):
        # Same entry_key, but the ledger's status changed since the E2 run.
        section = write_section(tmp_path)
        pack = make_pack(section, make_rubric())
        existing = result_for(section, {})
        drifted = write_section(
            tmp_path,
            ledger=[
                (cid, summary, "inferred" if cid == "C01" else status, ref)
                for cid, summary, status, ref in DEFAULT_LEDGER
            ],
        )
        drifted_pack = make_pack(drifted, make_rubric())
        with pytest.raises(eg.GroundingError, match="stale"):
            eg.derive_grounding(make_rubric(), drifted_pack, existing=existing)
        # The un-drifted pack still reuses cleanly.
        assert eg.derive_grounding(make_rubric(), pack, existing=existing).rows

    def test_stale_claim_wording_refused(self, tmp_path):
        # Same entry_key/id/status/source_ref, but the claim's own wording was
        # rewritten since the E2 run — the verdict is no longer for this text.
        section = write_section(tmp_path)
        existing = result_for(section, {})
        reworded = write_section(
            tmp_path,
            ledger=[
                (
                    cid,
                    summary.replace("beyond the state of the art", "modelling adequate")
                    if cid == "C01"
                    else summary,
                    status,
                    ref,
                )
                for cid, summary, status, ref in DEFAULT_LEDGER
            ],
        )
        pack = make_pack(reworded, make_rubric())
        with pytest.raises(eg.GroundingError, match="wording changed"):
            eg.derive_grounding(make_rubric(), pack, existing=existing)

    def test_legacy_finding_without_claim_summary_is_still_reusable(self, tmp_path):
        # Findings frozen before ClaimFaithfulness carried claim_summary have
        # it empty — wording drift is undetectable there, so the check skips
        # rather than refusing every legacy result.
        import dataclasses

        section = write_section(tmp_path)
        full = result_for(section, {})
        legacy = sf.StatusFaithfulnessResult(
            section_id=full.section_id,
            findings=tuple(
                dataclasses.replace(f, claim_summary="") for f in full.findings
            ),
            judge_model=JUDGE_MODEL,
            judge_version=JUDGE_VERSION,
        )
        grade = eg.derive_grounding(
            make_rubric(), make_pack(section, make_rubric()), existing=legacy
        )
        assert all(r.verdict_source == eg.VERDICT_FROM_RESULT for r in grade.rows)

    def test_judge_without_provenance_log_refused(self, tmp_path):
        section = write_section(tmp_path)
        pack = make_pack(section, make_rubric())
        judge, backend = make_judge(tmp_path, with_log=False)
        with pytest.raises(eg.GroundingError, match="ProvenanceLog"):
            eg.derive_grounding(
                make_rubric(), pack, judge=judge,
                repo_root=tmp_path, working_assumptions=EMPTY_WA,
            )
        assert backend.calls == []

    def test_judge_below_majority_n_rejected(self, tmp_path):
        section = write_section(tmp_path)
        pack = make_pack(section, make_rubric())
        judge, _ = make_judge(tmp_path)
        with pytest.raises(ValueError, match="N≥3"):
            eg.derive_grounding(
                make_rubric(), pack, judge=judge, n=1,
                repo_root=tmp_path, working_assumptions=EMPTY_WA,
            )

    def test_judge_pin_mismatch_with_existing_refused(self, tmp_path):
        section = write_section(tmp_path)
        pack = make_pack(section, make_rubric())
        judge, backend = make_judge(tmp_path, version="v2-repinned")
        with pytest.raises(eg.GroundingError, match="repin"):
            eg.derive_grounding(
                make_rubric(), pack, existing=result_for(section, {}), judge=judge,
                repo_root=tmp_path, working_assumptions=EMPTY_WA,
            )
        assert backend.calls == []

    def test_judge_without_resolution_inputs_refused(self, tmp_path):
        section = write_section(tmp_path)
        pack = make_pack(section, make_rubric())
        judge, _ = make_judge(tmp_path)
        with pytest.raises(eg.GroundingError, match="working_assumptions"):
            eg.derive_grounding(make_rubric(), pack, judge=judge)


# --------------------------------------------------------------------------- #
# Reuse — existing result, cross-expectation cache, no duplicate calls
# --------------------------------------------------------------------------- #


class TestVerdictReuse:
    def test_existing_result_means_zero_judge_calls(self, tmp_path):
        section = write_section(tmp_path)
        pack = make_pack(section, make_rubric())
        judge, backend = make_judge(tmp_path)
        grade = eg.derive_grounding(
            make_rubric(), pack, existing=result_for(section, {}), judge=judge,
            repo_root=tmp_path, working_assumptions=EMPTY_WA,
        )
        assert backend.calls == []  # every verdict reused, none re-judged
        assert len(grade.rows) == len(pack.claims)
        assert all(r.verdict_source == eg.VERDICT_FROM_RESULT for r in grade.rows)
        assert grade.reused_count == len(grade.rows) and grade.judged_count == 0
        assert (grade.judge_model, grade.judge_version) == (JUDGE_MODEL, JUDGE_VERSION)

    def test_cache_dedupes_across_expectations(self, tmp_path):
        # Two expectations over the same section: the shared cache means the
        # same (claim, source_ref) pair is judged exactly once.
        section = write_section(tmp_path)
        rubric_a, rubric_b = make_rubric("exc-obj"), make_rubric("exc-meth")
        pack_a, pack_b = make_pack(section, rubric_a), make_pack(section, rubric_b)
        judge, backend = make_judge(tmp_path)
        cache: eg.VerdictCache = {}

        grade_a = eg.derive_grounding(
            rubric_a, pack_a, judge=judge, verdict_cache=cache,
            repo_root=tmp_path, working_assumptions=EMPTY_WA,
            source_text_resolver=fixed_source("modelling source text"),
        )
        calls_after_a = len(backend.calls)
        # N≥3 per newly judged claim; the assumed claim (no declaration in the
        # empty WA) is surfaced unresolved by E2 without any judge call.
        judged = [c for c in pack_a.claims if c.claim.status != "assumed"]
        assert calls_after_a == len(judged) * 3
        assert all(r.verdict_source == eg.VERDICT_NEWLY_JUDGED for r in grade_a.rows)

        grade_b = eg.derive_grounding(
            rubric_b, pack_b, judge=judge, verdict_cache=cache,
            repo_root=tmp_path, working_assumptions=EMPTY_WA,
            source_text_resolver=fixed_source("modelling source text"),
        )
        assert len(backend.calls) == calls_after_a  # zero duplicate judge calls
        assert all(r.verdict_source == eg.VERDICT_FROM_CACHE for r in grade_b.rows)

    def test_cache_is_populated_from_an_existing_result(self, tmp_path):
        # Reuse chain: existing result seeds the cache; a later expectation
        # derives entirely from the cache with neither result nor judge.
        section = write_section(tmp_path)
        cache: eg.VerdictCache = {}
        eg.derive_grounding(
            make_rubric("exc-obj"),
            make_pack(section, make_rubric("exc-obj")),
            existing=result_for(section, {}),
            verdict_cache=cache,
        )
        grade = eg.derive_grounding(
            make_rubric("exc-meth"),
            make_pack(section, make_rubric("exc-meth")),
            verdict_cache=cache,
        )
        assert all(r.verdict_source == eg.VERDICT_FROM_CACHE for r in grade.rows)
        # Cache entries carry no pin of their own — the caller scopes the cache.
        assert (grade.judge_model, grade.judge_version) == (None, None)


# --------------------------------------------------------------------------- #
# Aggregation — status-aware, confirmed dominates, nothing averaged away
# --------------------------------------------------------------------------- #


class TestAggregation:
    def test_all_confirmed_grounded(self, tmp_path):
        section = write_section(tmp_path)
        pack = make_pack(section, make_rubric())
        grade = eg.derive_grounding(
            make_rubric(), pack, existing=result_for(section, {})
        )
        assert grade.confirmed_total == 2
        assert grade.grounding_rate == 1.0
        assert grade.judge_grounded is True
        assert grade.grounded is True
        assert grade.weakest_link is None
        assert grade.integrity_failures() == ()

    def test_confirmed_integrity_failure_dominates(self, tmp_path):
        # One "gap masked as confirmed" flips the grade whatever the rate.
        section = write_section(tmp_path)
        pack = make_pack(section, make_rubric())
        grade = eg.derive_grounding(
            make_rubric(), pack,
            existing=result_for(section, {"C02": sf.SEVERITY_INTEGRITY}),
        )
        assert grade.grounding_rate == 0.5
        assert grade.judge_grounded is False
        assert grade.grounded is False
        assert [r.claim.entry_key for r in grade.integrity_failures()] == ["C02#1"]
        assert grade.weakest_link is not None
        assert grade.weakest_link.claim.entry_key == "C02#1"

    def test_unresolved_confirmed_counts_against_the_rate(self, tmp_path):
        section = write_section(tmp_path)
        pack = make_pack(section, make_rubric())
        grade = eg.derive_grounding(
            make_rubric(), pack,
            existing=result_for(section, {"C01": sf.SEVERITY_UNRESOLVED}),
        )
        assert grade.grounding_rate == 0.5
        assert grade.judge_grounded is False  # unverifiable is not grounded
        assert grade.integrity_failures() == ()  # ...but not an entailment failure

    def test_assumed_and_inferred_are_reported_separately(self, tmp_path):
        # Assumed drift + inferred softness live in their own buckets and do
        # not move the confirmed axis — but they are named, never dropped.
        section = write_section(tmp_path)
        pack = make_pack(section, make_rubric())
        grade = eg.derive_grounding(
            make_rubric(), pack,
            existing=result_for(
                section,
                {"C03": sf.SEVERITY_SOFT, "C04": sf.SEVERITY_CONTENT_DRIFT},
            ),
        )
        assert grade.grounding_rate == 1.0  # the confirmed axis is untouched
        assert grade.grounded is True
        assert grade.assumed_drift == 1 and grade.inferred_soft == 1
        # The weakest link still names the worst flagged row (drift > soft).
        assert grade.weakest_link.claim.entry_key == "C04#3"

    def test_no_confirmed_claims_is_weak_grounding_not_a_vacuous_pass(self, tmp_path):
        ledger = [row for row in DEFAULT_LEDGER if row[2] != "confirmed"]
        section = write_section(tmp_path, ledger=ledger)
        pack = make_pack(section, make_rubric())
        grade = eg.derive_grounding(
            make_rubric(), pack, existing=result_for(section, {})
        )
        assert grade.confirmed_total == 0
        assert grade.grounding_rate is None
        assert grade.judge_grounded is None
        assert grade.grounded is False  # only assumed/inferred back it → weak

    def test_weakest_link_orders_by_severity_then_score(self, tmp_path):
        section = write_section(
            tmp_path,
            ledger=[
                ("C01", "modelling claim one", "confirmed", "docs/a.json"),
                ("C02", "modelling claim two", "confirmed", "docs/b.json"),
                ("C03", "modelling claim three", "inferred", "docs/c.json"),
            ],
        )
        pack = make_pack(section, make_rubric())
        grade = eg.derive_grounding(
            make_rubric(), pack,
            existing=result_for(
                section,
                {
                    "C01": sf.SEVERITY_INTEGRITY,
                    "C02": sf.SEVERITY_INTEGRITY,
                    "C03": sf.SEVERITY_SOFT,
                },
                scores={"C01": 0.4, "C02": 0.1, "C03": 0.05},
            ),
        )
        # Integrity outranks soft even at a higher score; lower score breaks
        # the tie within the same severity.
        assert grade.weakest_link.claim.entry_key == "C02#1"


# --------------------------------------------------------------------------- #
# Truncation — a budget-truncated claim set is never cleanly grounded
# --------------------------------------------------------------------------- #


class TestTruncation:
    def test_claims_excluded_over_budget_forbid_clean_grounded(self, tmp_path):
        # Prose matches nothing (all budget goes to claims); the budget fits
        # some claims but not all → the grade is over a subset.
        long = "The modelling claim padded far beyond a tiny budget " * 8
        section = write_section(
            tmp_path,
            ledger=[
                ("C01", "modelling claim small", "confirmed", "docs/a.json"),
                ("C02", long, "confirmed", "docs/b.json"),
            ],
            prose="No matching prose here.",
        )
        pack = make_pack(section, make_rubric(), token_budget=120)
        assert any(
            e.kind == "claim" and e.reason == "over_budget" for e in pack.excluded
        )
        grade = eg.derive_grounding(
            make_rubric(), pack, existing=result_for(section, {})
        )
        assert grade.claims_truncated is True
        assert grade.judge_grounded is True  # every judged claim passed...
        assert grade.grounded is False  # ...but the set was truncated

    def test_span_only_truncation_does_not_poison_the_claim_axis(self, tmp_path):
        # Spans overflow their budget share, but every relevant claim fits:
        # the pack is insufficient_context (coverage axis), yet the claim set
        # is complete, so a clean grounded outcome is still possible.
        prose = "\n\n".join(
            f"Paragraph {i} about modelling detail " + "x " * 120 for i in range(6)
        )
        section = write_section(
            tmp_path,
            ledger=[("C01", "modelling claim small", "confirmed", "docs/a.json")],
            prose=prose,
        )
        pack = make_pack(section, make_rubric(), token_budget=400)
        assert pack.status == "insufficient_context"
        assert not any(
            e.kind == "claim" and e.reason == "over_budget" for e in pack.excluded
        )
        grade = eg.derive_grounding(
            make_rubric(), pack, existing=result_for(section, {})
        )
        assert grade.claims_truncated is False
        assert grade.grounded is True
        assert grade.pack_status == "insufficient_context"  # visible to E5e


# --------------------------------------------------------------------------- #
# One system-of-record — zero new faithfulness prompts (E2 stays the SoR)
# --------------------------------------------------------------------------- #


class TestZeroNewPrompts:
    def test_newly_judged_claims_use_exactly_e2_prompts(self, tmp_path):
        # Behavioral: what the backend receives is byte-identical to E2's
        # status-specific prompt pair — E5d added no prompt of its own.
        section = write_section(
            tmp_path,
            ledger=[("C01", "modelling claim", "confirmed", "docs/a.json")],
        )
        rubric = make_rubric()
        pack = make_pack(section, rubric)
        judge, backend = make_judge(tmp_path)
        eg.derive_grounding(
            rubric, pack, judge=judge,
            repo_root=tmp_path, working_assumptions=EMPTY_WA,
            source_text_resolver=fixed_source("the source text"),
        )
        claim = sf.load_section_claims(section)[0]
        expected_system, expected_user = sf.build_faithfulness_prompt_for_status(
            claim.status,
            claim.claim_summary,
            "the source text",
            comparison=sf.COMPARISON_SOURCE,
            source_ref=claim.source_ref,
        )
        assert backend.calls  # the claim was judged (through E2)
        for system, user in backend.calls:
            assert system == expected_system
            assert user == expected_user

    def test_module_builds_no_prompt_and_never_invokes_the_judge_itself(self):
        # Static source check (test_boundary.py shape): the module must not
        # import prompt builders or call the judge directly — evaluate_claim
        # is its only path to a verdict.
        text = (REPO_ROOT / "harness" / "expectation_grounding.py").read_text(
            encoding="utf-8"
        )
        forbidden = re.compile(
            r"build_faithfulness_prompt|build_claim_user_prompt|PREAMBLE"
            r"|evaluate_majority|judge\.evaluate|from harness\.faithfulness"
            r"|build_rubric_prompts"
        )
        assert not forbidden.search(text), (
            "harness/expectation_grounding.py must not build prompts or invoke "
            "the judge directly — E2 is the single system-of-record"
        )

    def test_aggregate_key_never_collides_with_a_deterministic_predicate(self):
        preds = deterministic_predicate_names()
        assert eg.EXPECTATION_GROUNDING_METRIC not in preds
        key = eg.grounding_property_key("exc-obj", "excellence_section")
        assert key not in preds
        assert route(key).authority == RoutingAuthority.SEMANTIC_GAP

    def test_e2_routing_still_applies_to_newly_judged_claims(self, tmp_path, monkeypatch):
        # The per-claim judge calls inherit E2's routing: a claim whose
        # entry_key is deterministically covered is refused, not judged.
        from harness.routing import DeterministicCoverageError

        section = write_section(
            tmp_path,
            ledger=[("C01", "modelling claim", "confirmed", "docs/a.json")],
        )
        rubric = make_rubric()
        pack = make_pack(section, rubric)
        monkeypatch.setattr(
            "harness.routing.deterministic_predicate_names",
            lambda: frozenset({"C01#0"}),
        )
        judge, backend = make_judge(tmp_path)
        with pytest.raises(DeterministicCoverageError):
            eg.derive_grounding(
                rubric, pack, judge=judge,
                repo_root=tmp_path, working_assumptions=EMPTY_WA,
                source_text_resolver=fixed_source("src"),
            )
        assert backend.calls == []


# --------------------------------------------------------------------------- #
# Convenience entry point + serialization
# --------------------------------------------------------------------------- #


class TestDeriveExpectationGrounding:
    def test_builds_pack_from_rubric_basis(self, tmp_path):
        section = write_section(tmp_path)
        grade = eg.derive_expectation_grounding(
            make_rubric(), section, existing=result_for(section, {})
        )
        assert grade.expectation_key == "exc-obj"
        assert grade.section_id == "excellence_section"
        assert grade.section_path == str(section)
        assert len(grade.rows) == 4  # every term-matching ledger entry

    def test_to_dict_is_json_serializable_and_traceable(self, tmp_path):
        section = write_section(tmp_path)
        grade = eg.derive_expectation_grounding(
            make_rubric(), section,
            existing=result_for(section, {"C02": sf.SEVERITY_INTEGRITY}),
        )
        d = grade.to_dict()
        json.dumps(d)  # round-trippable
        assert d["metric"] == eg.EXPECTATION_GROUNDING_METRIC
        assert d["grounded"] is False
        assert d["grounding_rate"] == 0.5
        assert d["integrity_failure_keys"] == ["C02#1"]
        assert d["weakest_link"]["entry_key"] == "C02#1"
        assert d["assumed_total"] == 1 and d["inferred_total"] == 1
        # Every row is traceable to its individual E2 verdict.
        for row in d["rows"]:
            assert row["finding"]["entry_key"] == row["entry_key"]
            assert "severity" in row["finding"]
