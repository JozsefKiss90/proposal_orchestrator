"""
E5f — the paced/checkpointed grading runner (``harness.commands.rubric_grading_run``)
and the E4 rubric-lane baseline (``harness.regression``).

Everything runs offline with the injectable fake backend: the budget plan is
deterministic arithmetic, the grading loop is exercised end-to-end (coverage +
grounding + combine) against a synthetic mini-repo, and resume is proven by
counting backend calls — a resumed run must re-spend nothing that the
checkpoint already holds.
"""

from __future__ import annotations

import json
import pickle
from pathlib import Path

import pytest

import harness.regression as reg
import harness.rubric as hr
import harness.commands.rubric_grading_run as run
from harness.judge import Judge, JudgeConfig
from harness.provenance import ProvenanceLog
from harness.rubrics import Rubric, RubricSet
from runner.working_assumptions import WorkingAssumptions

EMPTY_WA = WorkingAssumptions(present=True)
EMPTY_SPINE = hr.SpineRegistry(facts=())

PASS_JSON = '{"passed": true, "score": 1.0, "rationale": "supported"}'


# --------------------------------------------------------------------------- #
# Fixtures — a mini repo whose claims resolve to real source files
# --------------------------------------------------------------------------- #


def make_rubric(key: str, criterion: str) -> Rubric:
    return Rubric(
        expectation_key=key,
        criterion_id=criterion,
        expectation_text="Soundness of the modelling objectives.",
        rubric="Integrity-framed: addressed AND grounded.",
        evaluation_steps=("Check the spans.", "Check the claims."),
        pass_threshold=0.7,
        selection_terms=("modelling",),
        anchor_sub_section_ids=(),
        source_page=4,
    )


def rubric_set(*rubrics: Rubric) -> RubricSet:
    return RubricSet(
        rubric_set_id="test_set",
        version="0.0.1",
        scorecard_id="sc",
        scorecard_version="v",
        rubrics=rubrics,
    )


#: Two confirmed claims; identical content in every section, so the second
#: cell's grounding is served entirely from the shared verdict cache.
LEDGER = [
    ("C01", "The modelling objective is beyond current practice.", "confirmed", "docs/t3/a.json"),
    ("C02", "The modelling method reuses partner tooling.", "confirmed", "docs/t3/b.json"),
]


def mini_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    sections = root / "docs/tier5_deliverables/proposal_sections"
    sections.mkdir(parents=True, exist_ok=True)
    for name in ("excellence_section", "impact_section", "implementation_section"):
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
                    for cid, summary, status, ref in LEDGER
                ]
            },
        }
        (sections / f"{name}.json").write_text(
            json.dumps(data, ensure_ascii=False), encoding="utf-8"
        )
    sources = root / "docs/t3"
    sources.mkdir(parents=True, exist_ok=True)
    for name in ("a.json", "b.json"):
        (sources / name).write_text(
            json.dumps({"text": "The modelling objective and partner tooling are recorded."}),
            encoding="utf-8",
        )
    return root


class CountingBackend:
    """A fake backend that can be armed to fail after a number of calls."""

    def __init__(self, fail_after: int | None = None):
        self.calls = 0
        self.fail_after = fail_after

    def __call__(self, messages):
        self.calls += 1
        if self.fail_after is not None and self.calls > self.fail_after:
            raise RuntimeError("simulated transport failure (daily cap)")
        return {"content": PASS_JSON}


def make_judge(tmp_path: Path, backend) -> Judge:
    return Judge(
        JudgeConfig(model="fake-judge", version="pin-1"),
        backend=backend,
        provenance_log=ProvenanceLog(tmp_path / "provenance.jsonl"),
        clock=lambda: "2026-08-10T00:00:00+00:00",
    )


TWO_RUBRICS = (make_rubric("exc-obj", "excellence"), make_rubric("imp-path", "impact"))

#: Backend calls for one cell whose claims are all uncached: coverage n=3 plus
#: two claims x n=3 grounding.
FIRST_CELL_CALLS = 3 + 2 * 3
#: The second cell re-judges nothing (content-identical claims hit the cache).
SECOND_CELL_CALLS = 3


def grade(judge, tmp_path, root, *, checkpoint=None, rubrics=TWO_RUBRICS, **kw):
    return run.run_grading(
        judge,
        rubric_set(*rubrics),
        EMPTY_SPINE,
        repo_root=root,
        working_assumptions=EMPTY_WA,
        checkpoint_path=checkpoint or (tmp_path / "ckpt.pkl"),
        log=lambda _: None,
        **kw,
    )


# --------------------------------------------------------------------------- #
# Budget plan
# --------------------------------------------------------------------------- #


class TestBudgetPlan:
    def plan(self, tmp_path, **kw):
        return run.compute_budget_plan(
            rubric_set(*TWO_RUBRICS), repo_root=mini_repo(tmp_path), **kw
        )

    def test_counts_cells_calls_and_deduped_claims(self, tmp_path):
        plan = self.plan(tmp_path)
        t = plan["totals"]
        assert t["cells"] == 2
        assert t["coverage_calls"] == 2 * 3
        # Content-identical claims across the two sections count once.
        assert t["unique_claims"] == 2
        assert t["grounding_calls_est"] == 2 * 3
        assert t["tokens_est"] == t["coverage_tokens_est"] + t["grounding_tokens_est"]
        assert plan["cells"][1]["new_unique_claims"] == 0

    def test_assessment_single_day_vs_multi_day(self, tmp_path):
        generous = self.plan(tmp_path, tpd=10_000_000, rpd=100_000)
        assert generous["assessment"]["fits_one_day"] is True
        assert generous["assessment"]["plan"] == "single_day"
        assert generous["assessment"]["estimated_days"] == 1

        tight = self.plan(tmp_path, tpd=1000)
        a = tight["assessment"]
        assert a["fits_one_day"] is False
        assert a["plan"] == "multi_day_resume"
        assert a["estimated_days"] >= tight["totals"]["tokens_est"] // 1000

    def test_per_call_ceiling_vs_tpm(self, tmp_path):
        plan = self.plan(tmp_path)
        a = plan["assessment"]
        assert a["max_call_ceiling"] == (
            plan["token_budget"] + run.RUBRIC_PROMPT_ALLOWANCE + 2048
        )
        assert a["max_call_ceiling_fits_tpm"] is (a["max_call_ceiling"] <= 6000)

    def test_deterministic_apart_from_timestamp(self, tmp_path):
        p1, p2 = self.plan(tmp_path), self.plan(tmp_path)
        p1.pop("computed_at"), p2.pop("computed_at")
        assert p1 == p2


# --------------------------------------------------------------------------- #
# Checkpoint
# --------------------------------------------------------------------------- #


class TestCheckpoint:
    META = {"judge_pin": "fake-judge@pin-1", "n": 3}

    def test_round_trip(self, tmp_path):
        p = tmp_path / "ckpt.pkl"
        run.save_checkpoint(p, self.META, {"k": "cell"}, {("a", "b", "c"): "finding"})
        cells, cache = run.load_checkpoint(p, self.META, log=lambda _: None)
        assert cells == {"k": "cell"}
        assert cache == {("a", "b", "c"): "finding"}

    def test_absent_checkpoint_is_a_fresh_start(self, tmp_path):
        cells, cache = run.load_checkpoint(tmp_path / "none.pkl", self.META)
        assert cells == {} and cache == {}

    def test_meta_mismatch_refuses_to_resume(self, tmp_path):
        p = tmp_path / "ckpt.pkl"
        run.save_checkpoint(p, self.META, {}, {})
        with pytest.raises(SystemExit, match="different run parameters"):
            run.load_checkpoint(p, {**self.META, "n": 1}, log=lambda _: None)

    def test_corrupt_checkpoint_fails_closed(self, tmp_path):
        p = tmp_path / "ckpt.pkl"
        p.write_bytes(b"not a pickle")
        with pytest.raises(SystemExit, match="--fresh"):
            run.load_checkpoint(p, self.META, log=lambda _: None)


# --------------------------------------------------------------------------- #
# The grading loop — end-to-end offline, resume proven by call counting
# --------------------------------------------------------------------------- #


class TestRunGrading:
    def test_full_run_grades_every_cell_and_shares_the_cache(self, tmp_path):
        root = mini_repo(tmp_path)
        backend = CountingBackend()
        cells = grade(make_judge(tmp_path, backend), tmp_path, root)
        assert [c.expectation_key for c in cells] == ["exc-obj", "imp-path"]
        assert [c.section_id for c in cells] == ["excellence_section", "impact_section"]
        assert backend.calls == FIRST_CELL_CALLS + SECOND_CELL_CALLS
        # The second cell's grounding rows all came from the shared cache.
        assert all(
            r.verdict_source == "cache" for r in cells[1].grounding.rows
        )

    def test_completed_run_retires_into_a_report(self, tmp_path):
        root = mini_repo(tmp_path)
        cells = grade(make_judge(tmp_path, CountingBackend()), tmp_path, root)
        report = hr.build_rubric_report(
            cells, judge_model="fake-judge", judge_version="pin-1"
        )
        assert report.summary["cells"] == 2
        hr.render_report(report.to_dict())  # renders without raising

    def test_failure_checkpoints_and_resume_respends_nothing(self, tmp_path):
        root = mini_repo(tmp_path)
        ckpt = tmp_path / "ckpt.pkl"

        # Fail during the second cell's coverage grading.
        failing = CountingBackend(fail_after=FIRST_CELL_CALLS)
        with pytest.raises(RuntimeError, match="simulated"):
            grade(make_judge(tmp_path, failing), tmp_path, root, checkpoint=ckpt)
        assert ckpt.is_file()
        state = pickle.loads(ckpt.read_bytes())
        assert list(state["cells"]) == ["exc-obj::excellence_section"]
        assert len(state["verdict_cache"]) == 2  # cell 1's judged claims survive

        # Resume with a healthy judge: cell 1 skipped, cell 2's grounding
        # served from the persisted cache — only its coverage is judged.
        resumed = CountingBackend()
        cells = grade(make_judge(tmp_path, resumed), tmp_path, root, checkpoint=ckpt)
        assert resumed.calls == SECOND_CELL_CALLS
        assert len(cells) == 2
        assert all(
            r.verdict_source == "cache" for r in cells[1].grounding.rows
        )

    def test_budget_stop_pauses_cleanly_between_cells(self, tmp_path):
        root = mini_repo(tmp_path)
        ckpt = tmp_path / "ckpt.pkl"
        backend = CountingBackend()
        spent = {"tokens": 0}

        def tokens_spent():
            return spent["tokens"]

        with pytest.raises(run.BudgetStop, match="daily stop"):
            spent["tokens"] = 99_999
            grade(
                make_judge(tmp_path, backend),
                tmp_path,
                root,
                checkpoint=ckpt,
                tokens_spent=tokens_spent,
                tpd_stop=1000,
            )
        assert backend.calls == 0  # stopped before the first judge call
        assert ckpt.is_file()

    def test_checkpoint_from_other_parameters_refuses(self, tmp_path):
        root = mini_repo(tmp_path)
        ckpt = tmp_path / "ckpt.pkl"
        grade(make_judge(tmp_path, CountingBackend()), tmp_path, root, checkpoint=ckpt)
        with pytest.raises(SystemExit, match="different run parameters"):
            grade(
                make_judge(tmp_path, CountingBackend()),
                tmp_path,
                root,
                checkpoint=ckpt,
                token_budget=500,
            )


# --------------------------------------------------------------------------- #
# Rubric-lane baseline (harness.regression) — freeze / load / compare
# --------------------------------------------------------------------------- #


def cell_dict(
    key: str = "exc-obj",
    section: str = "excellence_section",
    *,
    covered: bool = True,
    grounded: bool = True,
    clean: bool = True,
    contradictions: tuple[str, ...] = (),
) -> dict:
    return {
        "expectation_key": key,
        "section_id": section,
        "cell": "covered_grounded" if covered and grounded else "other",
        "covered": covered,
        "grounded": grounded,
        "coverage": {"passed": clean},
        "grounding": {},
        "contradictions": [{"kind": k} for k in contradictions],
    }


def report_dict(*cells: dict, judge=("j-model", "j-v1"), fingerprint="fp-1") -> dict:
    return {
        "record_type": "rubric_grade_report",
        "metric": "expectation_rubric_grid",
        "advisory": True,
        "blocking": False,
        "judge_model": judge[0],
        "judge_version": judge[1],
        "rubric_set_id": "rs",
        "rubric_set_version": "1.0.0",
        "rubric_set_fingerprint": fingerprint,
        "cells": list(cells) or [cell_dict()],
    }


class TestFreezeRubricBaseline:
    def test_freeze_embeds_report_pin_and_budget(self):
        report = report_dict()
        baseline = reg.freeze_rubric_baseline(
            report, frozen_at="2026-08-10", budget_record={"plan": "x"}
        )
        assert baseline["record_type"] == reg.RUBRIC_BASELINE_RECORD_TYPE
        assert baseline["judge_model"] == "j-model"
        assert baseline["rubric_set_fingerprint"] == "fp-1"
        assert baseline["budget_record"] == {"plan": "x"}
        assert baseline["report"] == report

    @pytest.mark.parametrize(
        "mutation, match",
        [
            ({"record_type": "other"}, "record"),
            ({"advisory": False}, "advisory"),
            ({"cells": []}, "no cells"),
            ({"judge_model": ""}, "judge pin"),
        ],
    )
    def test_freeze_fails_closed_on_a_malformed_report(self, mutation, match):
        report = {**report_dict(), **mutation}
        with pytest.raises(reg.RegressionError, match=match):
            reg.freeze_rubric_baseline(report)

    def test_load_round_trip_and_fail_closed(self, tmp_path):
        p = tmp_path / "b.rubric.json"
        baseline = reg.freeze_rubric_baseline(report_dict(), frozen_at="t")
        p.write_text(json.dumps(baseline), encoding="utf-8")
        assert reg.load_rubric_baseline(p)["frozen_at"] == "t"
        with pytest.raises(reg.RegressionError, match="not found"):
            reg.load_rubric_baseline(tmp_path / "nope.json")
        bad = tmp_path / "bad.json"
        bad.write_text('{"record_type": "other"}', encoding="utf-8")
        with pytest.raises(reg.RegressionError, match="record"):
            reg.load_rubric_baseline(bad)


class TestCompareRubricBaseline:
    def baseline(self, *cells: dict, **kw) -> dict:
        return reg.freeze_rubric_baseline(report_dict(*cells, **kw), frozen_at="t")

    def test_self_comparison_is_clean(self):
        report = report_dict(cell_dict(), cell_dict("imp-path", "impact_section"))
        comparison = reg.compare_rubric_baseline(
            reg.freeze_rubric_baseline(report, frozen_at="t"), report
        )
        assert comparison.regressed is False
        assert comparison.golden_set_findings == ()

    @pytest.mark.parametrize(
        "degraded, axis",
        [
            (dict(covered=False), "covered"),
            (dict(grounded=False), "grounded"),
            (dict(clean=False), "coverage clean pass"),
        ],
    )
    def test_axis_degradation_is_breaking(self, degraded, axis):
        comparison = reg.compare_rubric_baseline(
            self.baseline(cell_dict()), report_dict(cell_dict(**degraded))
        )
        assert comparison.regressed is True
        finding = comparison.golden_set_findings[0]
        assert finding.kind == reg.REGRESSION_RUBRIC_CELL_REGRESSED
        assert axis in finding.detail

    def test_axis_improvement_is_advisory(self):
        comparison = reg.compare_rubric_baseline(
            self.baseline(cell_dict(grounded=False)), report_dict(cell_dict())
        )
        assert comparison.regressed is False
        assert [f.kind for f in comparison.golden_set_findings] == [
            reg.REGRESSION_RUBRIC_CELL_IMPROVED
        ]

    def test_new_contradiction_is_breaking_disappeared_is_advisory(self):
        base = self.baseline(cell_dict(contradictions=("old_kind",)))
        comparison = reg.compare_rubric_baseline(
            base, report_dict(cell_dict(contradictions=("new_kind",)))
        )
        kinds = {f.kind for f in comparison.golden_set_findings}
        assert kinds == {
            reg.REGRESSION_RUBRIC_CONTRADICTION_APPEARED,
            reg.REGRESSION_RUBRIC_CELL_IMPROVED,
        }
        assert comparison.regressed is True

    def test_missing_cell_breaking_added_cell_advisory(self):
        base = self.baseline(cell_dict(), cell_dict("exc-2"))
        comparison = reg.compare_rubric_baseline(
            base, report_dict(cell_dict(), cell_dict("exc-3"))
        )
        by_kind = {f.kind for f in comparison.golden_set_findings}
        assert by_kind == {
            reg.REGRESSION_RUBRIC_CELL_MISSING,
            reg.REGRESSION_RUBRIC_CELL_ADDED,
        }
        assert comparison.regressed is True

    def test_judge_repin_fails_closed(self):
        with pytest.raises(reg.RegressionError, match="repin"):
            reg.compare_rubric_baseline(
                self.baseline(cell_dict()),
                report_dict(cell_dict(), judge=("other", "v9")),
            )

    def test_rubric_fingerprint_drift_fails_closed(self):
        with pytest.raises(reg.RegressionError, match="fingerprint"):
            reg.compare_rubric_baseline(
                self.baseline(cell_dict()),
                report_dict(cell_dict(), fingerprint="fp-2"),
            )


class TestRubricLaneCLI:
    def _paths(self, tmp_path):
        report = tmp_path / "report.json"
        report.write_text(json.dumps(report_dict()), encoding="utf-8")
        baseline = tmp_path / "baseline.rubric.json"
        return report, baseline

    def test_freeze_then_self_check(self, tmp_path, capsys):
        report, baseline = self._paths(tmp_path)
        assert reg.main(
            ["rubric-freeze", "--report", str(report), "--out", str(baseline)]
        ) == 0
        assert "frozen rubric baseline" in capsys.readouterr().out
        assert reg.main(
            ["rubric-check", "--report", str(report), "--baseline", str(baseline)]
        ) == 0

    def test_check_regression_exits_one(self, tmp_path):
        report, baseline = self._paths(tmp_path)
        assert reg.main(
            ["rubric-freeze", "--report", str(report), "--out", str(baseline)]
        ) == 0
        degraded = tmp_path / "degraded.json"
        degraded.write_text(
            json.dumps(report_dict(cell_dict(covered=False))), encoding="utf-8"
        )
        assert reg.main(
            ["rubric-check", "--report", str(degraded), "--baseline", str(baseline)]
        ) == 1

    def test_missing_inputs_fail_closed(self, tmp_path, capsys):
        assert reg.main(
            ["rubric-check", "--report", str(tmp_path / "none.json")]
        ) == 2
        assert "fail-closed" in capsys.readouterr().err
