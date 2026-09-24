"""
E5e — contradiction detector + report/CLI wiring: the deterministic E5c × E5d
combination rule, spine-awareness, the advisory-by-construction report, the
side-by-side renderer (no blended score), and the ``harness.rubric`` CLI.

Everything runs offline — coverage grades come from the injectable fake
backend, grounding grades from a pre-built E2 result (no judge call).  The
standing ``harness_rubric`` lane (real-file pins) lives in the marked class at
the bottom.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
import re
from pathlib import Path

import pytest

import harness.rubric as hr
import harness.expectation_grounding as eg
import harness.status_faithfulness as sf
from harness.evidence_pack import (
    PACK_INSUFFICIENT_CONTEXT,
    _render_frame,
    estimate_tokens,
)
from harness.expectation_coverage import grade_coverage
from harness.judge import Judge, JudgeConfig
from harness.provenance import ProvenanceLog
from harness.rubrics import Rubric, RubricSet, build_pack_for
from harness.verdict import Verdict
from runner.working_assumptions import Declaration, WorkingAssumptions

REPO_ROOT = Path(__file__).resolve().parents[2]
EMPTY_WA = WorkingAssumptions(present=True)

CHECKLIST_REF = (
    "docs/tier3_project_instantiation/call_binding/confirmation_checklist.json"
)

PASS_3 = ['{"passed": true, "score": 0.8, "rationale": "addressed in 1.1"}'] * 3
FAIL_3 = ['{"passed": false, "score": 0.2, "rationale": "not addressed"}'] * 3


# --------------------------------------------------------------------------- #
# Fixture helpers — synthetic rubric, section, grades
# --------------------------------------------------------------------------- #


def make_rubric(key: str = "exc-obj", criterion: str = "excellence") -> Rubric:
    return Rubric(
        expectation_key=key,
        criterion_id=criterion,
        expectation_text="Soundness of the modelling objectives.",
        rubric="Integrity-framed: addressed AND grounded, never prose quality.",
        evaluation_steps=("Check the spans.", "Check the claims."),
        pass_threshold=0.7,
        selection_terms=("modelling",),
        anchor_sub_section_ids=(),
        source_page=4,
    )


#: (claim_id, summary, status, source_ref) — every summary matches "modelling".
CONFIRMED_LEDGER = [
    ("C01", "The modelling objective is beyond the state of the art.", "confirmed", "docs/t3/a.json#x"),
    ("C02", "The modelling method reuses partner tooling.", "confirmed", "docs/t3/b.json"),
]

SPINE_LEDGER = CONFIRMED_LEDGER + [
    ("HOST", "The host provides modelling infrastructure.", "assumed", CHECKLIST_REF),
]


def write_section(tmp_path: Path, ledger, name: str = "excellence_section") -> Path:
    data = {
        "sub_sections": [
            {
                "sub_section_id": "1.1",
                "title": "Objectives",
                "content": "The modelling objectives are ambitious.",
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
    tmp_path.mkdir(parents=True, exist_ok=True)
    p = tmp_path / f"{name}.json"
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return p


def make_judge(tmp_path: Path, responses):
    calls = []

    def backend(messages):
        calls.append(messages)
        return {"content": responses[min(len(calls) - 1, len(responses) - 1)]}

    return Judge(
        JudgeConfig(model="fake-judge", version="pin-1"),
        backend=backend,
        provenance_log=ProvenanceLog(tmp_path / "provenance.jsonl"),
        clock=lambda: "2026-08-07T00:00:00+00:00",
    )


def finding_for(claim: sf.SectionClaim, severity: str) -> sf.ClaimFaithfulness:
    assumed = claim.status == sf.STATUS_ASSUMED
    return sf.ClaimFaithfulness(
        claim_id=claim.claim_id,
        status=claim.status,
        comparison=sf.COMPARISON_DECLARED_VALUE if assumed else sf.COMPARISON_SOURCE,
        comparison_ref=claim.claim_id if assumed else claim.source_ref,
        severity=severity,
        verdict=Verdict(
            metric=sf.STATUS_AWARE_FAITHFULNESS_METRIC,
            property_key=claim.entry_key,
            passed=severity == sf.SEVERITY_NONE,
            score=1.0 if severity == sf.SEVERITY_NONE else 0.1,
        ),
        reason="test finding",
        entry_index=claim.entry_index,
        claim_summary=claim.claim_summary,
    )


def result_for(section_path: Path, severities: dict) -> sf.StatusFaithfulnessResult:
    claims = sf.load_section_claims(section_path)
    return sf.StatusFaithfulnessResult(
        section_id=section_path.stem,
        findings=tuple(
            finding_for(c, severities.get(c.claim_id, sf.SEVERITY_NONE))
            for c in claims
        ),
        judge_model="acme-judge-1",
        judge_version="v1",
    )


def make_coverage(tmp_path, rubric, section_path, responses, *, token_budget=None):
    kwargs = {"token_budget": token_budget} if token_budget else {}
    pack = build_pack_for(rubric, section_path, **kwargs)
    return grade_coverage(make_judge(tmp_path, responses), rubric, pack)


def make_grounding(rubric, section_path, severities=None, *, token_budget=None):
    kwargs = {"token_budget": token_budget} if token_budget else {}
    pack = build_pack_for(rubric, section_path, **kwargs)
    return eg.derive_grounding(
        rubric, pack, existing=result_for(section_path, severities or {})
    )


def write_checklist(
    tmp_path: Path,
    *,
    host_status: str = "Unresolved",
    extra_spine=(),
) -> Path:
    data = {
        "spine_identity": [
            {"id": "HOST", "role": "Beneficiary / host organisation", "status": host_status},
            {"id": "FELLOW", "role": "The applicant", "status": "Confirmed"},
            *extra_spine,
        ],
        "project_decisions": [
            {"id": "RQ1", "question": "First crop", "status": "Confirmed"},
        ],
    }
    tmp_path.mkdir(parents=True, exist_ok=True)
    p = tmp_path / "confirmation_checklist.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def registry(tmp_path, *, host_status="Unresolved", wa=EMPTY_WA, **kw) -> hr.SpineRegistry:
    return hr.load_spine_registry(
        tmp_path,
        checklist_path=write_checklist(tmp_path, host_status=host_status, **kw),
        working_assumptions=wa,
    )


EMPTY_SPINE = hr.SpineRegistry(facts=())


# --------------------------------------------------------------------------- #
# Spine registry
# --------------------------------------------------------------------------- #


class TestSpineRegistry:
    def test_loads_and_classifies(self, tmp_path):
        reg = registry(tmp_path, host_status="Unresolved")
        assert {f.fact_id for f in reg.facts} == {"HOST", "FELLOW", "RQ1"}
        host = reg.by_id()["HOST"]
        assert host.kind == hr.KIND_SPINE_IDENTITY
        assert host.effective_status == "Unresolved"
        assert host.unconfirmed is True
        assert reg.by_id()["FELLOW"].unconfirmed is False
        assert reg.by_id()["RQ1"].kind == hr.KIND_PROJECT_DECISION
        assert [f.fact_id for f in reg.unconfirmed()] == ["HOST"]

    def test_missing_checklist_fails_closed(self, tmp_path):
        with pytest.raises(hr.RubricReportError, match="not found"):
            hr.load_spine_registry(
                tmp_path,
                checklist_path=tmp_path / "nope.json",
                working_assumptions=EMPTY_WA,
            )

    def test_default_checklist_path_under_repo_root(self, tmp_path):
        # The canonical Tier-3 location is resolved when no override is given.
        target = tmp_path / hr.DEFAULT_CHECKLIST_PATH
        target.parent.mkdir(parents=True)
        target.write_text(
            write_checklist(tmp_path / "src").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        reg = hr.load_spine_registry(tmp_path, working_assumptions=EMPTY_WA)
        assert "HOST" in reg.by_id()

    def test_status_outside_vocabulary_fails_closed(self, tmp_path):
        with pytest.raises(hr.RubricReportError, match="12.2"):
            registry(tmp_path, host_status="Probably fine")

    def test_empty_spine_fails_closed(self, tmp_path):
        p = tmp_path / "c.json"
        p.write_text(json.dumps({"spine_identity": [], "project_decisions": []}))
        with pytest.raises(hr.RubricReportError, match="spine_identity"):
            hr.load_spine_registry(
                tmp_path, checklist_path=p, working_assumptions=EMPTY_WA
            )

    def test_duplicate_fact_id_fails_closed(self, tmp_path):
        with pytest.raises(hr.RubricReportError, match="duplicate"):
            registry(
                tmp_path,
                extra_spine=[{"id": "HOST", "role": "again", "status": "Confirmed"}],
            )

    def test_declaration_overlay_makes_assumed_never_confirmed(self, tmp_path):
        wa = WorkingAssumptions(
            present=True,
            declarations=(
                Declaration(
                    key="host_country",
                    value="HU",
                    declared_by="op",
                    declared_on="2026-08-07",
                    checklist_ref="HOST",
                ),
            ),
        )
        host = registry(tmp_path, host_status="Unresolved", wa=wa).by_id()["HOST"]
        assert host.declared is True
        assert host.effective_status == "Assumed"  # declared, never Confirmed
        assert host.unconfirmed is True  # still fires the contradiction

    def test_declaration_by_key_also_counts(self, tmp_path):
        wa = WorkingAssumptions(
            present=True,
            declarations=(
                Declaration(
                    key="HOST", value="ELTE", declared_by="op", declared_on="2026-08-07"
                ),
            ),
        )
        assert registry(tmp_path, wa=wa).by_id()["HOST"].declared is True

    def test_confirmed_checklist_status_wins_over_declaration(self, tmp_path):
        host = registry(tmp_path, host_status="Confirmed").by_id()["HOST"]
        assert host.effective_status == "Confirmed"
        assert host.unconfirmed is False


class TestSpineClaimBridge:
    def test_claim_id_token_links(self, tmp_path):
        reg = registry(tmp_path)
        facts = reg.facts_for_claim("HOST", "docs/t3/a.json")
        assert [f.fact_id for f in facts] == ["HOST"]

    def test_checklist_source_ref_token_links(self, tmp_path):
        reg = registry(tmp_path)
        ref = f"{CHECKLIST_REF} (spine items FELLOWSHIP_TYPE, DURATION, HOST)"
        assert [f.fact_id for f in reg.facts_for_claim("C-01", ref)] == ["HOST"]

    def test_token_in_non_checklist_ref_does_not_link(self, tmp_path):
        reg = registry(tmp_path)
        assert reg.facts_for_claim("C-01", "docs/t3/HOST_notes.json") == ()

    def test_word_boundary_within_token_alphabet(self, tmp_path):
        reg = registry(tmp_path)
        assert reg.facts_for_claim("C-01", f"{CHECKLIST_REF} (HOSTING)") == ()
        assert reg.facts_for_claim("C-01", f"{CHECKLIST_REF} (NON_HOST)") == ()
        assert [
            f.fact_id for f in reg.facts_for_claim("C-01", f"{CHECKLIST_REF} (HOST)")
        ] == ["HOST"]


# --------------------------------------------------------------------------- #
# The combination rule
# --------------------------------------------------------------------------- #


class TestCombineAxes:
    def test_covered_and_grounded_is_clean(self, tmp_path):
        rubric = make_rubric()
        section = write_section(tmp_path, CONFIRMED_LEDGER)
        cell = hr.combine_axes(
            make_coverage(tmp_path, rubric, section, PASS_3),
            make_grounding(rubric, section),
            EMPTY_SPINE,
        )
        assert cell.cell == hr.CELL_COVERED_GROUNDED
        assert cell.covered is True and cell.grounded is True
        assert cell.contradictions == ()

    def test_integrity_failure_is_the_contradiction_cell(self, tmp_path):
        rubric = make_rubric()
        section = write_section(tmp_path, CONFIRMED_LEDGER)
        cell = hr.combine_axes(
            make_coverage(tmp_path, rubric, section, PASS_3),
            make_grounding(rubric, section, {"C01": sf.SEVERITY_INTEGRITY}),
            EMPTY_SPINE,
        )
        assert cell.cell == hr.CELL_COVERED_UNGROUNDED
        (finding,) = cell.contradictions
        assert finding.kind == hr.CONTRADICTION_COVERAGE_GROUNDING
        assert "failed entailment" in finding.detail
        assert rubric.expectation_key in finding.detail
        assert any(
            c["entry_key"].startswith("C01") for c in finding.offending_claims
        )

    def test_truncation_override_cannot_hide_the_contradiction(self, tmp_path):
        # Coverage's clean pass is forced False over a truncated pack, but the
        # cell's covered axis uses the raw majority — a genuinely-covered,
        # weakly-grounded expectation stays in the contradiction column.
        rubric = make_rubric()
        section = write_section(tmp_path, CONFIRMED_LEDGER)
        budget = estimate_tokens(
            _render_frame(rubric.expectation_key, section.stem, PACK_INSUFFICIENT_CONTEXT)
        ) + 5
        coverage = make_coverage(tmp_path, rubric, section, PASS_3, token_budget=budget)
        assert coverage.judge_passed is True and coverage.passed is False
        grounding = make_grounding(rubric, section, token_budget=budget)
        assert grounding.claims_truncated is True and grounding.grounded is False
        cell = hr.combine_axes(coverage, grounding, EMPTY_SPINE)
        assert cell.cell == hr.CELL_COVERED_UNGROUNDED
        (finding,) = cell.contradictions
        assert "over budget" in finding.detail

    def test_assumed_only_answer_is_named_weak_grounding(self, tmp_path):
        rubric = make_rubric()
        section = write_section(
            tmp_path,
            [
                ("A01", "The modelling host is assumed capable.", "assumed", "docs/t3/c.json"),
                ("I01", "The modelling gain is inferred.", "inferred", "docs/t3/d.json"),
            ],
        )
        cell = hr.combine_axes(
            make_coverage(tmp_path, rubric, section, PASS_3),
            make_grounding(rubric, section),
            EMPTY_SPINE,
        )
        assert cell.cell == hr.CELL_COVERED_UNGROUNDED
        (finding,) = cell.contradictions
        assert "no confirmed claims" in finding.detail
        assert {c["entry_key"].split("#")[0] for c in finding.offending_claims} == {
            "A01",
            "I01",
        }

    def test_uncovered_never_contradicts(self, tmp_path):
        rubric = make_rubric()
        section = write_section(tmp_path, SPINE_LEDGER)
        cell = hr.combine_axes(
            make_coverage(tmp_path, rubric, section, FAIL_3),
            make_grounding(rubric, section, {"C01": sf.SEVERITY_INTEGRITY}),
            registry(tmp_path, host_status="Unresolved"),
        )
        assert cell.covered is False
        assert cell.cell == hr.CELL_UNCOVERED_UNGROUNDED
        assert cell.contradictions == ()

    def test_mismatched_axes_fail_closed(self, tmp_path):
        rubric_a, rubric_b = make_rubric("exc-obj"), make_rubric("exc-meth")
        section = write_section(tmp_path, CONFIRMED_LEDGER)
        cov = make_coverage(tmp_path, rubric_a, section, PASS_3)
        with pytest.raises(hr.RubricReportError, match="axis mismatch"):
            hr.combine_axes(cov, make_grounding(rubric_b, section), EMPTY_SPINE)

    def test_mismatched_sections_fail_closed(self, tmp_path):
        rubric = make_rubric()
        s1 = write_section(tmp_path, CONFIRMED_LEDGER, name="excellence_section")
        s2 = write_section(tmp_path, CONFIRMED_LEDGER, name="impact_section")
        with pytest.raises(hr.RubricReportError, match="cross-section"):
            hr.combine_axes(
                make_coverage(tmp_path, rubric, s1, PASS_3),
                make_grounding(rubric, s2),
                EMPTY_SPINE,
            )


class TestSpineContradiction:
    def test_unconfirmed_spine_fact_is_named_even_when_grounded(self, tmp_path):
        # The ticket's headline sentence: coverage scored well, every claim
        # individually met its bar, yet the answer rests on an undeclared host.
        rubric = make_rubric()
        section = write_section(tmp_path, SPINE_LEDGER)
        cell = hr.combine_axes(
            make_coverage(tmp_path, rubric, section, PASS_3),
            make_grounding(rubric, section),
            registry(tmp_path, host_status="Unresolved"),
        )
        assert cell.grounded is True  # both confirmed claims met their bar
        assert cell.cell == hr.CELL_COVERED_GROUNDED
        (finding,) = cell.contradictions
        assert finding.kind == hr.CONTRADICTION_SPINE
        assert "HOST" in finding.detail and "Unresolved" in finding.detail
        assert finding.spine_fact["fact_id"] == "HOST"
        assert any(c["entry_key"].startswith("HOST") for c in finding.offending_claims)

    def test_declared_spine_fact_still_fires_marked_declared(self, tmp_path):
        rubric = make_rubric()
        section = write_section(tmp_path, SPINE_LEDGER)
        wa = WorkingAssumptions(
            present=True,
            declarations=(
                Declaration(
                    key="host_country",
                    value="HU",
                    declared_by="op",
                    declared_on="2026-08-07",
                    checklist_ref="HOST",
                ),
            ),
        )
        cell = hr.combine_axes(
            make_coverage(tmp_path, rubric, section, PASS_3),
            make_grounding(rubric, section),
            registry(tmp_path, host_status="Unresolved", wa=wa),
        )
        (finding,) = cell.contradictions
        assert "Assumed" in finding.detail
        assert "operator-declared" in finding.detail

    def test_confirmed_spine_fact_does_not_fire_but_is_recorded(self, tmp_path):
        rubric = make_rubric()
        section = write_section(tmp_path, SPINE_LEDGER)
        cell = hr.combine_axes(
            make_coverage(tmp_path, rubric, section, PASS_3),
            make_grounding(rubric, section),
            registry(tmp_path, host_status="Confirmed"),
        )
        assert cell.contradictions == ()
        # The audit trail keeps what was cross-referenced, not only what fired.
        assert [f.fact_id for f in cell.spine_facts] == ["HOST"]

    def test_spine_finding_survives_budget_truncation(self, tmp_path):
        # The honest common outcome on real sections is a truncated pack
        # (E5b): the spine claim itself is then often among the excluded.
        # The named spine finding must survive — via the exclusion record's
        # additive status/source_ref identity — not vanish with the budget.
        rubric = make_rubric("impl-cap", "implementation")
        section = write_section(
            tmp_path,
            [
                (
                    "C-01",
                    "The modelling fellowship is hosted with full infrastructure.",
                    "confirmed",
                    f"{CHECKLIST_REF} (spine items HOST)",
                )
            ],
            name="implementation_section",
        )
        budget = estimate_tokens(
            _render_frame(
                rubric.expectation_key, section.stem, PACK_INSUFFICIENT_CONTEXT
            )
        ) + 5
        coverage = make_coverage(tmp_path, rubric, section, PASS_3, token_budget=budget)
        grounding = make_grounding(rubric, section, token_budget=budget)
        assert grounding.rows == ()  # the spine claim never reached the judge
        cell = hr.combine_axes(
            coverage, grounding, registry(tmp_path, host_status="Unresolved")
        )
        spine_findings = [
            c for c in cell.contradictions if c.kind == hr.CONTRADICTION_SPINE
        ]
        (finding,) = spine_findings
        assert finding.spine_fact["fact_id"] == "HOST"
        assert "excluded over budget" in finding.detail
        (ref,) = finding.offending_claims
        assert ref["entry_key"].startswith("C-01")
        assert ref["status"] == "confirmed"
        assert ref["excluded"] == "over_budget"

    def test_source_ref_bridge_links_implementation_style_claims(self, tmp_path):
        rubric = make_rubric("impl-cap", "implementation")
        section = write_section(
            tmp_path,
            [
                (
                    "C-01",
                    "The modelling fellowship is hosted with full infrastructure.",
                    "confirmed",
                    f"{CHECKLIST_REF} (spine items FELLOWSHIP_TYPE, HOST)",
                )
            ],
            name="implementation_section",
        )
        cell = hr.combine_axes(
            make_coverage(tmp_path, rubric, section, PASS_3),
            make_grounding(rubric, section),
            registry(tmp_path, host_status="Unresolved"),
        )
        (finding,) = cell.contradictions
        assert finding.kind == hr.CONTRADICTION_SPINE
        assert finding.spine_fact["fact_id"] == "HOST"


# --------------------------------------------------------------------------- #
# The report — advisory by construction, no blended score
# --------------------------------------------------------------------------- #


def _one_cell_report(tmp_path, *, contradiction: bool) -> hr.RubricReport:
    rubric = make_rubric()
    section = write_section(tmp_path, CONFIRMED_LEDGER)
    severities = {"C01": sf.SEVERITY_INTEGRITY} if contradiction else {}
    cell = hr.combine_axes(
        make_coverage(tmp_path, rubric, section, PASS_3),
        make_grounding(rubric, section, severities),
        EMPTY_SPINE,
    )
    return hr.build_rubric_report(
        [cell], judge_model="fake-judge", judge_version="pin-1"
    )


class TestRubricReport:
    def test_advisory_and_blocking_are_enforced_structurally(self):
        with pytest.raises(ValueError, match="advisory"):
            hr.RubricReport(cells=(), advisory=False)
        with pytest.raises(ValueError, match="blocking"):
            hr.RubricReport(cells=(), blocking=True)

    def test_to_dict_carries_both_axes_and_no_blend(self, tmp_path):
        report = _one_cell_report(tmp_path, contradiction=True)
        d = report.to_dict()
        json.dumps(d)  # round-trippable
        assert d["record_type"] == hr.RUBRIC_REPORT_RECORD_TYPE
        assert d["advisory"] is True and d["blocking"] is False
        cell = d["cells"][0]
        assert cell["coverage"]["metric"] == "expectation_coverage"
        assert cell["grounding"]["metric"] == "expectation_grounding"

        # No blended-score *field* anywhere — the axes stay separate all the
        # way through the serialized record (keys checked recursively; the
        # advisory note prose legitimately *says* "no blended score").
        def keys_of(node):
            if isinstance(node, dict):
                for k, v in node.items():
                    yield k
                    yield from keys_of(v)
            elif isinstance(node, list):
                for item in node:
                    yield from keys_of(item)

        all_keys = set(keys_of(d))
        for forbidden in ("blended", "blended_score", "combined_score", "overall_score", "weighted_score"):
            assert forbidden not in all_keys

    def test_summary_counts(self, tmp_path):
        report = _one_cell_report(tmp_path, contradiction=True)
        s = report.summary
        assert s["cells"] == 1
        assert s["covered"] == 1
        assert s["grounded"] == 0
        assert s["contradictions"] == 1
        assert s["spine_contradictions"] == 0
        assert s["cells_by_class"] == {hr.CELL_COVERED_UNGROUNDED: 1}


class TestRender:
    def test_axes_side_by_side_per_row(self, tmp_path):
        report = _one_cell_report(tmp_path, contradiction=False)
        text = hr.render_report(report.to_dict())
        row = next(line for line in text.splitlines() if "exc-obj" in line)
        assert "judge=" in row and "grounded=" in row  # both axes on one line
        assert hr.CELL_COVERED_GROUNDED in row
        assert "no blended score" in text

    def test_contradictions_are_sentences_with_named_claims(self, tmp_path):
        report = _one_cell_report(tmp_path, contradiction=True)
        text = hr.render_report(report.to_dict())
        assert f"[{hr.CONTRADICTION_COVERAGE_GROUNDING}]" in text
        assert "failed entailment" in text
        assert re.search(r"claims: C01#\d+ \(confirmed/", text)

    def test_render_is_ascii_safe(self, tmp_path):
        report = _one_cell_report(tmp_path, contradiction=True)
        text = hr.render_report(report.to_dict())
        text.encode("ascii")  # must not raise (Windows cp125x console)

    def test_render_of_persisted_report_is_identical(self, tmp_path):
        report = _one_cell_report(tmp_path, contradiction=True)
        d = report.to_dict()
        roundtrip = json.loads(json.dumps(d))
        assert hr.render_report(roundtrip) == hr.render_report(d)


# --------------------------------------------------------------------------- #
# grade_all orchestration + CLI
# --------------------------------------------------------------------------- #


def _mini_repo(tmp_path) -> Path:
    root = tmp_path / "repo"
    sections = root / "docs/tier5_deliverables/proposal_sections"
    sections.mkdir(parents=True)
    for name in ("excellence_section", "impact_section", "implementation_section"):
        write_section(sections, CONFIRMED_LEDGER, name=name)
    checklist = root / hr.DEFAULT_CHECKLIST_PATH
    checklist.parent.mkdir(parents=True)
    checklist.write_text(
        write_checklist(tmp_path / "chk").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return root


def _rubric_set(*rubrics: Rubric) -> RubricSet:
    return RubricSet(
        rubric_set_id="test_set",
        version="0.0.1",
        scorecard_id="sc",
        scorecard_version="v",
        rubrics=rubrics,
    )


class TestGradeAll:
    def test_iterates_rubrics_and_shares_one_verdict_cache(self, tmp_path, monkeypatch):
        root = _mini_repo(tmp_path)
        rubric_set = _rubric_set(
            make_rubric("exc-obj", "excellence"), make_rubric("imp-path", "impact")
        )
        spine = registry(tmp_path, host_status="Confirmed")
        judge = make_judge(tmp_path, PASS_3)

        seen = []

        def fake_grounding(rubric, section_path, **kwargs):
            seen.append((rubric.expectation_key, kwargs["verdict_cache"]))
            return make_grounding(rubric, Path(section_path))

        monkeypatch.setattr(hr, "derive_expectation_grounding", fake_grounding)
        cells = hr.grade_all(
            judge, rubric_set, spine, repo_root=root, working_assumptions=EMPTY_WA
        )
        assert [c.expectation_key for c in cells] == ["exc-obj", "imp-path"]
        assert [c.section_id for c in cells] == ["excellence_section", "impact_section"]
        # One shared cache across every expectation of the run (E5d discipline).
        caches = [cache for _, cache in seen]
        assert all(cache is caches[0] for cache in caches)

    def test_missing_section_artifact_fails_closed(self, tmp_path):
        root = _mini_repo(tmp_path)
        (root / "docs/tier5_deliverables/proposal_sections/impact_section.json").unlink()
        with pytest.raises(Exception, match="impact_section"):
            hr.grade_all(
                make_judge(tmp_path, PASS_3),
                _rubric_set(make_rubric("imp-path", "impact")),
                registry(tmp_path),
                repo_root=root,
                working_assumptions=EMPTY_WA,
            )


class TestCLI:
    def _write_report(self, tmp_path, *, contradiction: bool) -> Path:
        report = _one_cell_report(tmp_path, contradiction=contradiction)
        p = tmp_path / "report.json"
        p.write_text(json.dumps(report.to_dict()), encoding="utf-8")
        return p

    def test_report_clean_exits_zero(self, tmp_path, capsys):
        p = self._write_report(tmp_path, contradiction=False)
        assert hr.main(["report", "--in", str(p)]) == 0
        out = capsys.readouterr().out
        assert "EXPECTATION RUBRIC GRID" in out
        assert "CONTRADICTIONS: none" in out

    def test_report_with_contradictions_exits_one(self, tmp_path, capsys):
        p = self._write_report(tmp_path, contradiction=True)
        assert hr.main(["report", "--in", str(p)]) == 1
        assert "CONTRADICTIONS (1):" in capsys.readouterr().out

    def test_report_missing_file_fails_closed(self, tmp_path, capsys):
        assert hr.main(["report", "--in", str(tmp_path / "nope.json")]) == 2
        assert "fail-closed" in capsys.readouterr().err

    def test_report_wrong_record_type_fails_closed(self, tmp_path):
        p = tmp_path / "other.json"
        p.write_text(json.dumps({"record_type": "something_else"}), encoding="utf-8")
        assert hr.main(["report", "--in", str(p)]) == 2

    def test_grade_wires_report_and_exit_code(self, tmp_path, monkeypatch, capsys):
        # The wiring test: grade loads spine + rubric set, assembles the
        # report, renders it, writes --out, and exits 1 on a contradiction.
        root = _mini_repo(tmp_path)
        rubric = make_rubric()
        section = write_section(tmp_path / "s", CONFIRMED_LEDGER)
        cell = hr.combine_axes(
            make_coverage(tmp_path, rubric, section, PASS_3),
            make_grounding(rubric, section, {"C01": sf.SEVERITY_INTEGRITY}),
            EMPTY_SPINE,
        )
        judge = make_judge(tmp_path, PASS_3)
        monkeypatch.setattr(hr, "_build_judge", lambda path: judge)
        bundle = SimpleNamespace(
            rubric_set=_rubric_set(rubric),
            profile=None,
            profile_id="test_profile",
            version="sha256:test-profile-version",
        )
        monkeypatch.setattr(hr, "load_profile_bundle", lambda *a, **k: bundle)
        monkeypatch.setattr(hr, "grade_all", lambda *a, **k: (cell,))

        out_path = tmp_path / "out" / "report.json"
        rc = hr.main(
            [
                "grade",
                "--repo-root",
                str(root),
                "--out",
                str(out_path),
                "--provenance",
                str(tmp_path / "prov.jsonl"),
            ]
        )
        assert rc == 1
        written = json.loads(out_path.read_text(encoding="utf-8"))
        assert written["record_type"] == hr.RUBRIC_REPORT_RECORD_TYPE
        assert written["rubric_set_id"] == "test_set"
        assert written["profile_id"] == "test_profile"
        assert written["profile_version"] == "sha256:test-profile-version"
        assert written["judge_model"] == "fake-judge"
        assert written["spine_source"].endswith("confirmation_checklist.json")
        assert "EXPECTATION RUBRIC GRID" in capsys.readouterr().out

    def test_grade_fails_closed_without_judge_env(self, tmp_path, monkeypatch, capsys):
        for var in ("HARNESS_JUDGE_MODEL", "HARNESS_JUDGE_VERSION"):
            monkeypatch.delenv(var, raising=False)
        root = _mini_repo(tmp_path)
        assert hr.main(["grade", "--repo-root", str(root)]) == 2
        assert "fail-closed" in capsys.readouterr().err


# --------------------------------------------------------------------------- #
# Boundary + marker wiring
# --------------------------------------------------------------------------- #


class TestBoundary:
    def test_rubric_module_never_imports_the_drafter_stack(self):
        forbidden = re.compile(
            r"^\s*(?:from|import)\s+runner\.(?:claude_transport|skill_runtime|"
            r"semantic_dispatch|agent_runtime)\b",
            re.MULTILINE,
        )
        text = (REPO_ROOT / "harness" / "rubric.py").read_text(encoding="utf-8")
        assert not forbidden.search(text)

    def test_marker_is_registered(self):
        pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        assert "harness_rubric" in pyproject


# --------------------------------------------------------------------------- #
# Standing lane — real-file pins (the harness_rubric marker)
# --------------------------------------------------------------------------- #


@pytest.mark.harness_rubric
class TestStandingLane:
    def test_real_spine_register_loads_and_is_fully_confirmed(self):
        # The committed 13B state: 9 spine items + 10 project decisions, all
        # operator-confirmed.  A revert to an open spine (or a vocabulary
        # drift) fails this advisory lane and surfaces to a human.
        reg = hr.load_spine_registry(REPO_ROOT)
        spine = [f for f in reg.facts if f.kind == hr.KIND_SPINE_IDENTITY]
        decisions = [f for f in reg.facts if f.kind == hr.KIND_PROJECT_DECISION]
        assert len(spine) == 9
        assert len(decisions) == 10
        assert {"HOST", "FELLOW", "SUPERVISOR"} <= {f.fact_id for f in spine}
        assert reg.unconfirmed() == ()

    def test_frozen_report_renders_if_present(self):
        # E5f freezes the first real report; until then this lane records the
        # gap by skipping, never by pretending.
        path = REPO_ROOT / hr.DEFAULT_REPORT_PATH
        if not path.is_file():
            pytest.skip("no frozen rubric report yet (E5f pending)")
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        assert data["record_type"] == hr.RUBRIC_REPORT_RECORD_TYPE
        assert data["advisory"] is True and data["blocking"] is False
        hr.render_report(data)  # must render without raising
