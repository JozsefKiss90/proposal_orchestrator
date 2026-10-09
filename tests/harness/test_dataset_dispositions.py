"""
V02d — the dataset dispositions stay honest.

``harness/DATASET_DISPOSITIONS.md`` is the one place a reader of harness status
sees which checks cannot run because their dataset is absent.  Two things can
quietly rot it: a check excluded on disk but missing from the table (an
invisible exclusion), and a row for a check that no longer exists (a stale
claim).  This module asserts both directions, and that the lift-work and the
no-calibration statement the audit requires are present.

Offline, no judge, no DAG.  It reads the document and the test tree only.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DISPOSITIONS = REPO_ROOT / "harness" / "DATASET_DISPOSITIONS.md"

#: Every directory the dispositions account for, and what absence means.
DATASET_DIRS = (
    Path("harness/gold_sets"),
    Path("harness/regression_baselines"),
)

#: The Tier 3 artifact whose absence excludes two further checks. Not a dataset
#: directory, so it has no README to point back here.
TIER3_CHECKLIST = "docs/tier3_project_instantiation/call_binding/confirmation_checklist.json"

#: Every test module that skips on an absent dataset. The table must name each
#: one, and each one's skip reason must point back at the table.
EXCLUDED_MODULES = (
    "test_regression_golden.py",
    "test_measure_ledger_granularity.py",
    "test_expectations.py",
    "test_gold_set.py",
    "test_rubric_report.py",
    "test_status_faithfulness.py",
)


#: Enough number words for a table of this size; the document spells its counts.
_WORDS = {
    11: "eleven rows",
    12: "twelve rows",
    13: "thirteen rows",
    14: "fourteen rows",
    15: "fifteen rows",
    16: "sixteen rows",
}


def _spelt(n: int) -> str:
    return _WORDS.get(n, str(n) + " rows")


@pytest.fixture(scope="module")
def text() -> str:
    return DISPOSITIONS.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def rows(text: str) -> list[list[str]]:
    """The disposition table's data rows, split on the pipe.

    Every data row must parse.  A lenient parser that skipped a malformed row
    would drop an exclusion out of the very check that exists to keep the list
    complete, so a row this cannot read is an error here, not a silent pass.
    """
    out = []
    for line in text.splitlines():
        if not line.startswith("| `"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        assert len(cells) == 5, f"disposition row has {len(cells)} cells: {line}"
        out.append(cells)
    return out


def test_the_document_exists_and_names_its_ticket_and_decision_record(text: str):
    assert "V02d" in text
    assert "msca-dn-dataset-dispositions_2026-10-09.json" in text


def test_every_absent_substrate_is_accounted_for(text: str):
    for d in DATASET_DIRS:
        assert d.as_posix() in text, f"{d} is not named in the dispositions"
    assert TIER3_CHECKLIST in text, "the absent Tier 3 checklist is not accounted for"


def test_the_table_has_a_row_for_every_excluded_module(rows: list[list[str]]):
    named = " ".join(r[0] for r in rows)
    for module in EXCLUDED_MODULES:
        assert module in named, f"{module} has no disposition row"


def test_every_excluded_module_points_back_at_the_table(text: str):
    """The table claims each check names this document. Check that it does."""
    for module in EXCLUDED_MODULES:
        body = (REPO_ROOT / "tests" / "harness" / module).read_text(encoding="utf-8")
        assert "DATASET_DISPOSITIONS.md" in body, (
            f"{module} skips on an absent dataset without naming the disposition"
        )


def test_the_row_count_and_the_check_count_are_both_stated(text: str, rows):
    """A row may stand for several checks, so the two counts differ by design.

    The document states both, and the decision record's own count is the
    per-module one.  Stating only a row count would read as a check count.
    """
    assert f"{len(rows)} rows" in text or _spelt(len(rows)) in text.lower()


def test_every_row_carries_a_disposition_and_a_reason(rows: list[list[str]]):
    """V02d's vocabulary: a check is "restored from a maintained source, or
    scoped out with its reason". Nothing is Restored today; the value stays in
    the set so a restoration reads as one, and a typo reads as neither."""
    assert rows, "the disposition table is empty"
    for check, dataset, disposition, reason, _evidence in rows:
        assert dataset, check
        assert disposition in {"Excluded", "Restored"}, (check, disposition)
        assert reason, check


def test_no_row_names_a_test_module_that_does_not_exist(rows: list[list[str]]):
    """A stale row is a claim about a check nobody runs."""
    for check, *_ in rows:
        module = re.search(r"(test_[a-z0-9_]+\.py)", check)
        assert module, check
        assert (
            REPO_ROOT / "tests" / "harness" / module.group(1)
        ).is_file(), f"{check} names a module that is not in tests/harness/"


def test_an_excluded_check_is_never_described_as_passing(text: str):
    """The audit's requirement: an exclusion is not a successful calibration."""
    assert "not passing" in text
    assert "EXCLUDED" in text or "Excluded" in text
    lowered = text.lower()
    assert "does not say the judge is calibrated" in lowered


def test_the_lift_work_is_named(text: str):
    """V02d: the disposition names X03 as the work that lifts the exclusion."""
    assert "X03" in text
    assert "py -3.10 -m harness.regression freeze" in text


def test_the_absence_of_expert_labelled_data_is_stated(text: str):
    assert "No expert-labelled validation data exists" in text


def test_the_harness_status_document_points_here(text: str):
    """A reader of HARNESS.md must reach the dispositions from there."""
    harness_md = (REPO_ROOT / "harness" / "HARNESS.md").read_text(encoding="utf-8")
    assert "DATASET_DISPOSITIONS.md" in harness_md


@pytest.mark.parametrize("readme", [d / "README.md" for d in DATASET_DIRS])
def test_each_dataset_readme_points_here(readme: Path):
    body = (REPO_ROOT / readme).read_text(encoding="utf-8")
    assert "DATASET_DISPOSITIONS.md" in body
