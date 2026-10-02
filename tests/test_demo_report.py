"""The demo report, held to the artifacts it reads.

``plans/reports/dev_graph_demo_report_2026-10-03.md`` answers the four questions
the scope record fixed and lists the open defects as Milestone 2 candidates. A
report is prose and goes stale, so each load-bearing figure it states is
re-derived here from the Tier 4 artifact the report names beside it. A test
that fails here means the world moved after the report was written, and the
report (or its record) needs amending, not the test.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
REPORT = REPO / "plans/reports/dev_graph_demo_report_2026-10-03.md"
DECISION = REPO / "docs/tier4_orchestration_state/decision_log/demo-report_2026-10-03.json"
VALIDATION = REPO / "docs/tier4_orchestration_state/validation_reports/demo-report_2026-10-03.json"
SCOPE = REPO / "docs/tier4_orchestration_state/decision_log/dev-graph-demo-scope_2026-09-29.json"
SUMMARY = REPO / "docs/tier4_orchestration_state/dev_graph/demo_snapshot_summary.json"
SNAPSHOT_RECORD = REPO / "docs/tier4_orchestration_state/decision_log/demo-dev-graph-snapshot_2026-09-30.json"
SCENARIOS = REPO / "docs/tier4_orchestration_state/dev_graph/change_scenarios"
RERUN = SCENARIOS / "deliverable_month_moves/reruns/synthetic-rerun-2026-10-02.json"
PHASE_OUTPUTS = REPO / "docs/tier4_orchestration_state/phase_outputs"
RUN_COST = REPO / "docs/tier4_orchestration_state/run_cost"
BLIND = REPO / "harness/blind_reports/blind_e518c50023ee_0001.json"
CHANGE_SCENARIOS_RECORD = REPO / "docs/tier4_orchestration_state/decision_log/demo-change-scenarios_2026-10-02.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


@pytest.fixture(scope="module")
def report() -> str:
    return REPORT.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def decision() -> dict:
    return _load(DECISION)


@pytest.fixture(scope="module")
def validation() -> dict:
    return _load(VALIDATION)


def _fmt(n: int) -> str:
    return f"{n:,}"


class TestTheReportExistsAndIsRecorded:
    def test_the_report_and_both_records_exist(self) -> None:
        assert REPORT.is_file()
        assert DECISION.is_file()
        assert VALIDATION.is_file()

    def test_the_records_name_the_report_and_each_other(self, decision, validation) -> None:
        assert decision["report"] == "plans/reports/dev_graph_demo_report_2026-10-03.md"
        assert decision["validation_report"] == str(VALIDATION.relative_to(REPO)).replace("\\", "/")
        assert validation["report_id"] == decision["id"] == "demo-report_2026-10-03"

    def test_the_decision_record_closes_all_three_boxes(self, decision) -> None:
        criteria = decision["acceptance_criteria"]
        assert len(criteria) == 3
        assert all(v.startswith("MET") for v in criteria.values())

    def test_no_placeholder_survived(self, report, validation) -> None:
        assert "{SCAN_COUNT}" not in report
        assert "{SUITE_LINE}" not in report
        assert "{SUITE_LINE}" not in json.dumps(validation)


class TestEveryScopeQuestionIsAnswered:
    """Box 1: every scope question has an answer backed by a Tier 4 artifact."""

    def test_the_four_questions_are_the_scope_records(self, report) -> None:
        scope = _load(SCOPE)
        assert len(scope["questions"]) == 4
        table = report.split("## The four scope questions, answered", 1)[1].split("\n## ", 1)[0]
        rows = [l for l in table.splitlines() if l.startswith("| ") and "?" in l.split("|")[1]]
        assert len(rows) == 4

    def test_every_answer_row_names_an_artifact_that_exists(self, report) -> None:
        table = report.split("## The four scope questions, answered", 1)[1].split("\n## ", 1)[0]
        rows = [l for l in table.splitlines() if l.startswith("| ") and "?" in l.split("|")[1]]
        for row in rows:
            evidence = row.rsplit("|", 2)[1]
            paths = re.findall(r"`([^`]+)`", evidence)
            assert paths, row
            for p in paths:
                candidates = [REPO / p, REPO / "docs/tier4_orchestration_state" / p]
                assert any(c.exists() for c in candidates), p


class TestTheSnapshotFigures:
    def test_first_and_current_counts(self, report) -> None:
        first = _load(SNAPSHOT_RECORD)["snapshot"]
        current = _load(SUMMARY)
        assert f"{first['node_count']} nodes and {first['edge_count']} edges" in report
        assert f"{current['node_count']} nodes and {current['edge_count']} edges" in report
        assert current["snapshot_id"][7:15] in report

    def test_the_package_table_is_the_summarys(self, report) -> None:
        summary = _load(SUMMARY)
        assert f"default budget of {summary['budget']}" in report
        for p in summary["packages"]:
            row = (
                f"| {p['task']} | {p['view']} | {p['included_count']} | {p['mandatory_count']} "
                f"| {p['over_budget_count']} | {p['over_budget_required_count']} | {p['first_item_that_did_not_fit']} |"
            )
            assert row in report, row
        assert all(p["completeness"] == "incomplete" for p in summary["packages"])
        assert f"All {len(summary['packages'])} packages are incomplete" in report or "All\neighteen are incomplete" in report

    def test_the_exclusion_totals(self, report) -> None:
        ex = _load(SUMMARY)["exclusions_by_reason_total"]
        assert f"{_fmt(ex['over_budget'])} over-budget exclusions against {ex['not_relevant']} not-relevant and {ex['policy_forbidden']} policy-forbidden" in report

    def test_the_not_confirmed_count(self, report) -> None:
        n = sum(len(p["not_confirmed"]) for p in _load(SUMMARY)["packages"])
        assert f"{n}\nnot-confirmed items" in report or f"{n} not-confirmed items" in report


class TestTheScenarioFigures:
    def test_seven_scenarios_eleven_arms_sixteen_refusals(self, report) -> None:
        scenarios = [_load(p) for p in sorted(SCENARIOS.glob("*/scenario.json"))]
        arms = [a for s in scenarios for a in s["arms"]]
        comparisons = [c for a in arms for c in (a.get("shadow_comparisons") or [])]
        assert len(scenarios) == 7 and "Seven scenarios were scripted" in report
        assert len(arms) == 12 and "They hold twelve arms" in report
        assert len(comparisons) == 18 and all(c.get("refused") for c in comparisons)
        assert "Eighteen comparisons, eighteen refusals" in report
        assert {c["refused"]["kind"] for c in comparisons} == {"no_reuse_decision"}

    def test_the_synthetic_rows(self, report) -> None:
        rerun = _load(RERUN)
        rows = [r for c in rerun["comparisons"] for r in c["rows"]]
        narrower = [r for r in rows if r["diagnostic"] == "planner_narrower"]
        assert len(rows) == 6 and len(narrower) == 3
        assert "Three narrower rows of six, no broader row" in report
        assert rerun["run_id"] in report
        assert rerun["investigation"].startswith("DECLARED SYNTHETIC RUN")
        assert "declared synthetic run" in report

    def test_the_milestone_2_ids_m1_to_m6_are_the_records_own(self, report) -> None:
        record = _load(CHANGE_SCENARIOS_RECORD)
        ids = [m["id"] for m in record["milestone_2_candidates"]]
        assert ids == ["M1", "M2", "M3", "M4", "M5", "M6"]
        section = report.split("## 8 · Defects as candidate Milestone 2 tickets", 1)[1].split("\n## ", 1)[0]
        for i in range(1, 27):
            assert f"| M{i} |" in section, f"M{i}"
        assert "| M27 |" not in section


class TestTheRunnerFigures:
    def test_fourteen_gate_results_all_pass(self, report) -> None:
        gates = [_load(p) for p in sorted(PHASE_OUTPUTS.glob("*/gate*result*.json"))]
        assert len(gates) == 14 and all(g["status"] == "pass" for g in gates)
        passed = sum(
            len(g["deterministic_predicates"].get("passed", [])) + len(g["semantic_predicates"].get("passed", []))
            for g in gates
        )
        assert f"{len(gates)} gate results, all pass, {passed} predicates passed" in report

    def test_the_run_cost_totals(self, report) -> None:
        for p in RUN_COST.glob("*.json"):
            d = _load(p)
            t = d["totals"]
            assert f"| {t['invocations']} | {_fmt(t['estimated_total_tokens'])} | {_fmt(round(t['wall_clock_seconds']))} s |" in report, p.name
        rerun = _load(RUN_COST / "import uuid; print(uuid.uuid4()).json")
        u = rerun["unattributed_after_last_gate"]
        assert f"| {u['invocations']} | {_fmt(u['estimated_total_tokens'])} | {_fmt(round(u['wall_clock_seconds']))} s |" in report
        assert rerun["monetary_cost"]["status"] == "Unresolved" and "monetary cost is Unresolved" in report


class TestTheBlindLaneFigures:
    def test_the_cells_and_the_pin(self, report) -> None:
        blind = _load(BLIND)
        assert blind["scope"] == "complete"
        assert blind["assessor_pin"] in report
        scores = [f"{c['score']:.3f}" for c in blind["cells"]]
        for s in scores:
            assert s in report, s

    def test_the_scan_count_is_the_scans_own(self, report, validation) -> None:
        from runner.leakage_scan import iter_scanned_files

        scanned = len(iter_scanned_files(REPO))
        assert f"over {scanned} files" in report
        assert validation["figures"]["leakage_scan"]["files_scanned"] == scanned
        assert validation["figures"]["leakage_scan"]["new_leaks"] == 0


class TestTheTicketIsClosed:
    def test_the_three_boxes_are_ticked(self) -> None:
        text = (REPO / "plans/dev_graph_demo_tickets.md").read_text(encoding="utf-8")
        section = text.split("## Demo report", 1)[1]
        assert section.count("- [x]") == 3
        assert "- [ ]" not in section
        assert "**Done 2026-10-03.**" in section
