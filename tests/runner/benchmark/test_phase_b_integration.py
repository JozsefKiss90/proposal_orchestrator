"""Integration tests for Phase B analytics using real Phase A fixture artifacts.

Uses the actual Phase 1 run artifacts (run_id: 4bb9ce95-342c-4662-8a95-d30a9388b621)
as regression fixtures.
"""

import json
import shutil
from pathlib import Path

import pytest

from runner.benchmark.report_builder import run_phase_b_analytics

# Path to the real Phase A fixture artifacts
FIXTURE_RUN_ID = "4bb9ce95-342c-4662-8a95-d30a9388b621"
REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_BENCH_DIR = REPO_ROOT / ".claude" / "benchmark" / FIXTURE_RUN_ID
FIXTURE_RUN_SUMMARY = REPO_ROOT / ".claude" / "runs" / FIXTURE_RUN_ID / "run_summary.json"

# Known Phase A totals for regression validation
EXPECTED_INVOCATION_COUNT = 4
EXPECTED_INPUT_TOKENS = 40402
EXPECTED_OUTPUT_TOKENS = 22944
EXPECTED_TOTAL_WALL_CLOCK = 922.203


@pytest.fixture
def phase_a_fixture(tmp_path):
    """Copy real Phase A fixtures to a temp directory."""
    bench_dir = tmp_path / ".claude" / "benchmark" / FIXTURE_RUN_ID
    bench_dir.mkdir(parents=True, exist_ok=True)

    # Copy ledger and summary
    shutil.copy2(
        FIXTURE_BENCH_DIR / "invocation_ledger.jsonl",
        bench_dir / "invocation_ledger.jsonl",
    )
    shutil.copy2(
        FIXTURE_BENCH_DIR / "run_benchmark_summary.json",
        bench_dir / "run_benchmark_summary.json",
    )

    # Copy run_summary if it exists
    run_summary_path = tmp_path / ".claude" / "runs" / FIXTURE_RUN_ID / "run_summary.json"
    if FIXTURE_RUN_SUMMARY.exists():
        run_summary_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(FIXTURE_RUN_SUMMARY, run_summary_path)

    return bench_dir, run_summary_path


class TestPhaseBIntegrationWithRealFixtures:
    """Full integration test using real Phase A artifacts."""

    def test_phase_b_generates_all_artifacts(self, phase_a_fixture):
        bench_dir, run_summary_path = phase_a_fixture
        paths = run_phase_b_analytics(bench_dir, run_summary_path=run_summary_path)

        assert len(paths) == 4
        assert (bench_dir / "phase_analytics.json").exists()
        assert (bench_dir / "token_economics.json").exists()
        assert (bench_dir / "timing_profile.json").exists()
        assert (bench_dir / "run_benchmark_summary.json").exists()

    def test_expanded_summary_has_phase_b_stage(self, phase_a_fixture):
        bench_dir, run_summary_path = phase_a_fixture
        run_phase_b_analytics(bench_dir, run_summary_path=run_summary_path)

        summary = json.loads(
            (bench_dir / "run_benchmark_summary.json").read_text(encoding="utf-8")
        )
        assert summary["benchmark_stage"] == "phase_b_analytics"

    def test_invocation_count_matches(self, phase_a_fixture):
        bench_dir, run_summary_path = phase_a_fixture
        run_phase_b_analytics(bench_dir, run_summary_path=run_summary_path)

        pa = json.loads(
            (bench_dir / "phase_analytics.json").read_text(encoding="utf-8")
        )
        assert pa["total_invocations"] == EXPECTED_INVOCATION_COUNT

    def test_input_token_total_matches(self, phase_a_fixture):
        bench_dir, run_summary_path = phase_a_fixture
        run_phase_b_analytics(bench_dir, run_summary_path=run_summary_path)

        te = json.loads(
            (bench_dir / "token_economics.json").read_text(encoding="utf-8")
        )
        assert te["total_estimated_input_tokens"] == EXPECTED_INPUT_TOKENS

    def test_output_token_total_matches(self, phase_a_fixture):
        bench_dir, run_summary_path = phase_a_fixture
        run_phase_b_analytics(bench_dir, run_summary_path=run_summary_path)

        te = json.loads(
            (bench_dir / "token_economics.json").read_text(encoding="utf-8")
        )
        assert te["total_estimated_output_tokens"] == EXPECTED_OUTPUT_TOKENS

    def test_total_tokens_consistent(self, phase_a_fixture):
        bench_dir, run_summary_path = phase_a_fixture
        run_phase_b_analytics(bench_dir, run_summary_path=run_summary_path)

        te = json.loads(
            (bench_dir / "token_economics.json").read_text(encoding="utf-8")
        )
        assert te["total_estimated_tokens"] == EXPECTED_INPUT_TOKENS + EXPECTED_OUTPUT_TOKENS

    def test_timing_profile_wall_clock(self, phase_a_fixture):
        bench_dir, run_summary_path = phase_a_fixture
        run_phase_b_analytics(bench_dir, run_summary_path=run_summary_path)

        tp = json.loads(
            (bench_dir / "timing_profile.json").read_text(encoding="utf-8")
        )
        assert tp["total_wall_clock_seconds"] == EXPECTED_TOTAL_WALL_CLOCK

    def test_phase_analytics_shows_phase_1(self, phase_a_fixture):
        bench_dir, run_summary_path = phase_a_fixture
        run_phase_b_analytics(bench_dir, run_summary_path=run_summary_path)

        pa = json.loads(
            (bench_dir / "phase_analytics.json").read_text(encoding="utf-8")
        )
        assert pa["phase_scope"] == 1
        assert 1 in pa["phases_observed"]

    def test_all_invocations_are_tapm(self, phase_a_fixture):
        """All 4 fixture invocations are TAPM."""
        bench_dir, run_summary_path = phase_a_fixture
        run_phase_b_analytics(bench_dir, run_summary_path=run_summary_path)

        te = json.loads(
            (bench_dir / "token_economics.json").read_text(encoding="utf-8")
        )
        tapm_total = te["tapm_vs_cli_prompt"]["tapm"]["estimated_total_tokens"]
        cli_total = te["tapm_vs_cli_prompt"]["cli_prompt"]["estimated_total_tokens"]
        assert tapm_total == EXPECTED_INPUT_TOKENS + EXPECTED_OUTPUT_TOKENS
        assert cli_total == 0

    def test_no_prompt_content_in_any_artifact(self, phase_a_fixture):
        """Verify no prompt or response content leaks into Phase B artifacts."""
        bench_dir, run_summary_path = phase_a_fixture
        run_phase_b_analytics(bench_dir, run_summary_path=run_summary_path)

        for name in [
            "phase_analytics.json",
            "token_economics.json",
            "timing_profile.json",
            "run_benchmark_summary.json",
        ]:
            content = (bench_dir / name).read_text(encoding="utf-8")
            # Should not contain actual prompt text — only char counts
            assert "system_prompt\":" not in content
            assert "user_prompt\":" not in content
            assert "response_text" not in content

    def test_expanded_summary_preserves_phase_a_fields(self, phase_a_fixture):
        bench_dir, run_summary_path = phase_a_fixture

        # Read Phase A summary before Phase B
        original = json.loads(
            (bench_dir / "run_benchmark_summary.json").read_text(encoding="utf-8")
        )

        run_phase_b_analytics(bench_dir, run_summary_path=run_summary_path)

        expanded = json.loads(
            (bench_dir / "run_benchmark_summary.json").read_text(encoding="utf-8")
        )

        # All Phase A fields still present
        for key in original:
            assert key in expanded, f"Phase A field '{key}' missing from expanded summary"
            if key != "node_records":  # node_records is a list, compare directly
                assert expanded[key] == original[key], (
                    f"Phase A field '{key}' changed: {original[key]} -> {expanded[key]}"
                )

    def test_skill_id_breakdown(self, phase_a_fixture):
        """Verify all 4 skill IDs appear in token economics."""
        bench_dir, run_summary_path = phase_a_fixture
        run_phase_b_analytics(bench_dir, run_summary_path=run_summary_path)

        te = json.loads(
            (bench_dir / "token_economics.json").read_text(encoding="utf-8")
        )
        expected_skills = {
            "call-requirements-extraction",
            "evaluation-matrix-builder",
            "instrument-schema-normalization",
            "topic-scope-check",
        }
        assert set(te["tokens_by_skill_id"].keys()) == expected_skills

    def test_fixture_files_not_mutated(self, phase_a_fixture):
        """Verify the original fixture files in the repo are not modified."""
        # Read originals
        original_ledger = FIXTURE_BENCH_DIR / "invocation_ledger.jsonl"
        original_summary = FIXTURE_BENCH_DIR / "run_benchmark_summary.json"

        original_ledger_content = original_ledger.read_text(encoding="utf-8")
        original_summary_content = original_summary.read_text(encoding="utf-8")

        # Run Phase B on the temp copy
        bench_dir, run_summary_path = phase_a_fixture
        run_phase_b_analytics(bench_dir, run_summary_path=run_summary_path)

        # Verify originals unchanged
        assert original_ledger.read_text(encoding="utf-8") == original_ledger_content
        assert original_summary.read_text(encoding="utf-8") == original_summary_content
