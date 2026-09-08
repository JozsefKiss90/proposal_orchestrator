"""Smoke and consistency tests for tools/build_partb1_refactored.py (no Word export needed)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools import build_partb1_refactored as build
from tools import partb1_refactor_lib as lib

pytestmark = pytest.mark.skipif(not build.BASELINE_DOCX.exists(),
                                reason="sealed Part B-1 baseline DOCX not present")


@pytest.fixture(scope="module")
def built(tmp_path_factory) -> Path:
    out_dir = tmp_path_factory.mktemp("partb1")
    return build.build_docx(out_dir / "refactored.docx", out_dir / "gantt.png")


def test_docx_validation_has_no_failures(built: Path):
    assert build.validate_docx(built) == []


def test_every_cut_is_charged_exactly_once(built: Path):
    charged = [c for e in build.EDITS for c in e.cuts]
    assert sorted(charged) == sorted(c.cut_id for c in build.CUT_LEDGER)


def test_each_finding_in_scope_is_addressed(built: Path):
    addressed = {f for e in build.EDITS for f in e.findings}
    in_scope = {f"F-{i:02d}" for i in range(1, 24)} - {"F-09", "F-19"}  # B-2 / Part A findings
    assert in_scope <= addressed


def test_gantt_labels_follow_the_deliverable_months():
    labelled = {}
    for text, month in list(build.GANTT.deliverables_a) + list(build.GANTT.deliverables_b):
        for part in text.split(";"):
            wp, ids = part.strip().split(".")
            for i in ids.split("/"):
                labelled[f"D{wp}.{i}"] = month
    assert labelled == build.DELIVERABLE_MONTHS
    assert {f"MS{m}" for m, _ in build.GANTT.milestones} == set(build.MILESTONE_MONTHS)


def test_effort_matrix_is_consistent():
    assert lib.check_effort_model(build.EFFORT_MATRIX, build.PERIOD_TOTALS, build.WP_TOTALS, 30.0) == []


def test_baseline_is_never_modified(built: Path):
    import hashlib

    # SHA-256 prefix of the sealed editable source recorded on 2026-09-08 before any build
    assert hashlib.sha256(build.BASELINE_DOCX.read_bytes()).hexdigest().startswith("79e23ee5357e")


def test_layout_checks_read_the_pdf_report():
    ok = {"per_page": [{"first_line": "", "images": 0} for _ in range(10)]}
    ok["per_page"][7]["first_line"] = "3."
    ok["per_page"][8]["images"] = 1
    ok["per_page"][9]["first_line"] = "3.2"
    assert build.layout_checks(ok) == []
    bad = {"per_page": ok["per_page"][:9]}
    assert build.layout_checks(bad) == ["page count is not 10; layout targets not evaluated"]
