"""LG-1 measurement — pins the load-bearing facts behind the coarse-ledger decision.

``harness/ledger_granularity.py`` is a deterministic, offline (no judge, no DAG)
measurement composing harness E2/E3/E4 primitives.  This suite asserts the
measured facts the decision-log entry
(``decision_log/lg1-coarse-claim-ledger-measured_2026-07-27.json``) relies on, so
a future compiler or golden-baseline change that would invalidate the
ACCEPT-COARSE decision surfaces as a red test rather than sliding through.

Offline by construction: ``build_report`` invokes no judge and reads only the
committed graph-sourced sections and the E4 golden baselines.

Coupling note: the drafter-era side is the E4 golden baselines
(``harness/regression_baselines/*.golden.json``), which still hold the 191/119/96
drafter ledger.  If those goldens are ever *refrozen* to the graph-sourced
sections (e.g. to green the standing ``harness_regression`` lane under DOD-1),
this suite's drafter-era expectations must be re-pointed at the committed
measurement report
(``decision_log/lg1_ledger_granularity_measurement_2026-07-27.json``, which
preserves every drafter-era number) or re-sourced from git history at the
graph-cutover commit.  A red here after such a refreeze is that signal, not a bug.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import harness.ledger_granularity as mlg

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def report():
    return mlg.build_report(REPO_ROOT)


def test_report_shape_and_offline(report):
    assert report["record_type"] == "lg1_ledger_granularity_measurement"
    assert report["deterministic"] is True
    # The judge layer is honestly recorded as not-run (no independent backend).
    assert report["judge_layer_status"].startswith("NOT RUN")
    assert set(report["sections"]) == {"excellence", "impact", "implementation"}


def test_prose_byte_identical_all_sub_sections(report):
    # The decision's core premise: the ledger is the ONLY variable between the
    # two generations, so the cardinality deficit is exact, not confounded.
    assert report["totals"]["prose_byte_identical_all"] is True
    for section in report["sections"].values():
        assert section["prose_byte_identical"] is True
        assert all(d["identical"] for d in section["prose_byte_identity_detail"])


def test_cardinality_gap(report):
    totals = report["totals"]
    assert totals["graph_sourced_claims"] == 12
    assert totals["drafter_era_claims"] == 406
    assert totals["sub_sections"] == 12
    assert totals["graph_claims_per_sub_section"] == 1.0
    # graph ~1/sub-section vs drafter ~34/sub-section — an order-plus gap.
    assert totals["cardinality_ratio_drafter_over_graph"] > 20

    expected = {"excellence": (191, 5), "impact": (119, 4), "implementation": (96, 3)}
    for slug, (drafter_n, graph_n) in expected.items():
        section = report["sections"][slug]
        assert section["drafter_era"]["claims"] == drafter_n
        assert section["graph_sourced"]["claims"] == graph_n


def test_status_axis_graph_honest_vs_drafter_confirmed_heavy(report):
    # Graph ledger asserts zero 'confirmed' claims; the drafter ledger is
    # confirmed-heavy (the E2 integrity-risk surface the decision rests on).
    for section in report["sections"].values():
        graph_part = section["graph_sourced"]["status_partition"]
        assert graph_part.get("confirmed", 0) == 0
        assert graph_part.get("inferred", 0) == section["graph_sourced"]["claims"]
        assert section["drafter_era"]["status_partition"].get("confirmed", 0) > 0


def test_e4_golden_diff_detects_the_gap(report):
    # The real E4 harness metric (deterministic) must flag the collapse.
    e4 = report["e4_regression"]
    assert e4["summary"]["breaking"] > 0
    by_section = {sec["section_id"]: sec for sec in e4["sections"]}
    for sid in ("excellence_section", "impact_section", "implementation_section"):
        sec = by_section[sid]
        assert sec["regressed"] is True
        assert sec["findings_by_kind"].get("claim_removed", 0) > 0
