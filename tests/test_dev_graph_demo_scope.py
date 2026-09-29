"""The demo scope record is the anchor every later instance-two ticket cites.

`plans/dev_graph_demo_tickets.md` opens instance two on the `dev_graph_demo`
branch, and its first ticket fixes the demo's scope in one Tier 4 decision log
entry (CLAUDE.md §9.4). These checks pin that record's identity, the commits it
claims to descend from, and the four questions the demo exists to answer.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from runner.paths import find_repo_root

REPO = find_repo_root()
DECISION_LOG = REPO / "docs/tier4_orchestration_state/decision_log"
TICKETS = REPO / "plans/dev_graph_demo_tickets.md"

STEM = "dev-graph-demo-scope"
BRANCH = "dev_graph_demo"
TOPIC = "HORIZON-CL6-2027-01-BIODIV-01"

#: The scope questions the demo report must answer, keyed as the record keys them.
SCOPE_QUESTIONS = (
    "snapshot_on_real_records",
    "packages_within_budget",
    "planner_agrees_with_reruns",
    "blind_lane_stays_leak_free",
)

#: The commits the record claims instance two descends from, each paired with the
#: key holding the subject line the record attributes to it.
BASELINE_COMMITS = (
    ("base_commit", "base_commit_subject"),
    ("milestone_1_closure_commit", "milestone_1_closure_subject"),
    ("milestone_1_followup_commit", "milestone_1_followup_subject"),
)

SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(REPO), *args], capture_output=True, text=True
    )


def _commit_exists(sha: str) -> bool:
    if shutil.which("git") is None:
        return False
    return _git("rev-parse", "--verify", f"{sha}^{{commit}}").returncode == 0


@pytest.fixture(scope="module")
def record() -> dict:
    entries = sorted(DECISION_LOG.glob(f"{STEM}_*.json"))
    assert len(entries) == 1, f"expected exactly one {STEM} entry, found {entries}"
    return json.loads(entries[0].read_text(encoding="utf-8"))


class TestScopeRecord:
    def test_it_is_a_decision_record_under_its_own_id(self, record: dict) -> None:
        assert record["record_type"] == "decision"
        assert record["id"] == STEM

    def test_it_names_the_branch(self, record: dict) -> None:
        assert record["branch"] == BRANCH

    def test_it_records_the_baseline_commits_as_full_shas(self, record: dict) -> None:
        for key, _ in BASELINE_COMMITS:
            sha = record["baseline"][key]
            assert SHA_RE.match(sha), f"{key} is not a full SHA: {sha!r}"

    def test_the_demo_is_recorded_as_never_submitted_and_anonymised(
        self, record: dict
    ) -> None:
        scope = record["scope"]
        assert scope["instance"] == "two"
        assert scope["submission"] == "never submitted"
        assert scope["consortium"] == "anonymised"

    def test_it_fixes_the_four_dev_graph_questions(self, record: dict) -> None:
        questions = record["questions"]
        assert tuple(questions) == SCOPE_QUESTIONS
        for key, text in questions.items():
            assert text.strip(), key

    def test_the_recorded_topic_is_the_one_the_ticket_file_opens_on(
        self, record: dict
    ) -> None:
        recorded = record["scope"]["topic"]
        assert recorded == TOPIC
        assert recorded in TICKETS.read_text(encoding="utf-8")


class TestBaselineCommits:
    """A wrong SHA is the one error the shape checks cannot catch.

    Ancestry alone does not catch it: every dev-graph commit is an ancestor of
    HEAD, so a swapped or substituted SHA still passes. The subject line is what
    binds a SHA to the commit the record claims it is.
    """

    @pytest.mark.parametrize("key,subject_key", BASELINE_COMMITS)
    def test_each_recorded_commit_carries_the_subject_the_record_gives_it(
        self, record: dict, key: str, subject_key: str
    ) -> None:
        sha = record["baseline"][key]
        if not _commit_exists(sha):
            pytest.skip("git unavailable or commit not present in this clone")
        subject = _git("log", "-1", "--format=%s", sha).stdout.strip()
        assert subject == record["baseline"][subject_key], key

    @pytest.mark.parametrize("key,subject_key", BASELINE_COMMITS)
    def test_each_recorded_commit_is_an_ancestor_of_head(
        self, record: dict, key: str, subject_key: str
    ) -> None:
        sha = record["baseline"][key]
        if not _commit_exists(sha):
            pytest.skip("git unavailable or commit not present in this clone")
        result = _git("merge-base", "--is-ancestor", sha, "HEAD")
        assert result.returncode == 0, f"{key} {sha} is not an ancestor of HEAD"
