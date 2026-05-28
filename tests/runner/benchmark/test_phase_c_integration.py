"""Integration tests for Phase C provider projection using real Phase B fixture artifacts.

Uses the validated Phase 1 run artifacts (run_id: 028d48e4-0d0d-48d9-8882-502a45bc9bf8)
which have complete Phase A + Phase B artifacts.
"""

import json
import shutil
import unittest.mock as mock
from pathlib import Path

import pytest

from runner.benchmark.report_builder import run_benchmark_reports, run_phase_b_analytics

# Path to the real Phase B fixture artifacts
FIXTURE_RUN_ID = "028d48e4-0d0d-48d9-8882-502a45bc9bf8"
REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_BENCH_DIR = REPO_ROOT / ".claude" / "benchmark" / FIXTURE_RUN_ID
FIXTURE_RUN_SUMMARY = REPO_ROOT / ".claude" / "runs" / FIXTURE_RUN_ID / "run_summary.json"
FIXTURE_CATALOG = REPO_ROOT / ".claude" / "benchmark" / "config" / "provider_catalog.json"

# Known fixture values
EXPECTED_INVOCATION_COUNT = 4
EXPECTED_INPUT_TOKENS = 40402
EXPECTED_OUTPUT_TOKENS = 22170
EXPECTED_TOTAL_TOKENS = 62572


@pytest.fixture
def phase_b_fixture(tmp_path):
    """Copy real Phase B fixtures + catalog to a temp directory.

    Skips when the fixture benchmark data is not present on disk.
    Benchmark data lives in .claude/benchmark/ which is gitignored.
    """
    if not (FIXTURE_BENCH_DIR / "invocation_ledger.jsonl").exists():
        pytest.skip(
            f"Fixture benchmark data not found: {FIXTURE_BENCH_DIR}. "
            "Benchmark data is gitignored and only available after local DAG runs."
        )

    bench_dir = tmp_path / ".claude" / "benchmark" / FIXTURE_RUN_ID
    bench_dir.mkdir(parents=True, exist_ok=True)

    # Copy all Phase A + B artifacts
    for name in [
        "invocation_ledger.jsonl",
        "run_benchmark_summary.json",
        "phase_analytics.json",
        "token_economics.json",
        "timing_profile.json",
    ]:
        src = FIXTURE_BENCH_DIR / name
        if src.exists():
            shutil.copy2(src, bench_dir / name)

    # Copy run_summary if it exists
    run_summary_path = tmp_path / ".claude" / "runs" / FIXTURE_RUN_ID / "run_summary.json"
    if FIXTURE_RUN_SUMMARY.exists():
        run_summary_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(FIXTURE_RUN_SUMMARY, run_summary_path)

    # Copy provider catalog
    cat_dir = tmp_path / ".claude" / "benchmark" / "config"
    cat_dir.mkdir(parents=True, exist_ok=True)
    if FIXTURE_CATALOG.exists():
        shutil.copy2(FIXTURE_CATALOG, cat_dir / "provider_catalog.json")

    return bench_dir, run_summary_path, tmp_path


class TestPhaseCIntegrationWithRealFixtures:
    """Full integration: run Phase B + C through report builder with real fixtures."""

    def test_provider_projection_generated(self, phase_b_fixture):
        bench_dir, run_summary_path, repo_root = phase_b_fixture
        paths = run_benchmark_reports(
            bench_dir,
            run_summary_path=run_summary_path,
            repo_root=repo_root,
        )

        proj_path = bench_dir / "provider_projection.json"
        assert proj_path.exists(), "provider_projection.json not generated"
        assert proj_path in paths

    def test_summary_has_phase_c_stage(self, phase_b_fixture):
        bench_dir, run_summary_path, repo_root = phase_b_fixture
        run_benchmark_reports(
            bench_dir,
            run_summary_path=run_summary_path,
            repo_root=repo_root,
        )

        summary = json.loads(
            (bench_dir / "run_benchmark_summary.json").read_text(encoding="utf-8")
        )
        assert summary["benchmark_stage"] == "phase_c_provider_projection"

    def test_summary_has_provider_projection_summary(self, phase_b_fixture):
        bench_dir, run_summary_path, repo_root = phase_b_fixture
        run_benchmark_reports(
            bench_dir,
            run_summary_path=run_summary_path,
            repo_root=repo_root,
        )

        summary = json.loads(
            (bench_dir / "run_benchmark_summary.json").read_text(encoding="utf-8")
        )
        assert "provider_projection_summary" in summary
        pps = summary["provider_projection_summary"]
        assert "total_providers_evaluated" in pps
        assert "suitable_providers" in pps
        assert pps["total_providers_evaluated"] > 0

    def test_phase_a_fields_preserved(self, phase_b_fixture):
        bench_dir, run_summary_path, repo_root = phase_b_fixture

        # Read original before Phase C
        original = json.loads(
            (bench_dir / "run_benchmark_summary.json").read_text(encoding="utf-8")
        )

        run_benchmark_reports(
            bench_dir,
            run_summary_path=run_summary_path,
            repo_root=repo_root,
        )

        expanded = json.loads(
            (bench_dir / "run_benchmark_summary.json").read_text(encoding="utf-8")
        )

        # All Phase A fields preserved
        for key in ["benchmark_schema_version", "run_id", "started_at",
                     "completed_at", "total_invocations",
                     "total_estimated_input_tokens",
                     "total_estimated_output_tokens",
                     "total_wall_clock_seconds", "node_records"]:
            assert key in expanded, f"Phase A field '{key}' missing"
            assert expanded[key] == original[key], (
                f"Phase A field '{key}' changed"
            )

    def test_phase_b_fields_preserved(self, phase_b_fixture):
        bench_dir, run_summary_path, repo_root = phase_b_fixture

        # Read original Phase B summary
        original = json.loads(
            (bench_dir / "run_benchmark_summary.json").read_text(encoding="utf-8")
        )

        run_benchmark_reports(
            bench_dir,
            run_summary_path=run_summary_path,
            repo_root=repo_root,
        )

        expanded = json.loads(
            (bench_dir / "run_benchmark_summary.json").read_text(encoding="utf-8")
        )

        # Phase B fields preserved
        for key in ["phase_analytics_summary", "token_economics_summary",
                     "timing_summary", "phase_b_artifact_paths"]:
            assert key in expanded, f"Phase B field '{key}' missing"

    def test_phase_b_artifacts_still_exist(self, phase_b_fixture):
        bench_dir, run_summary_path, repo_root = phase_b_fixture
        run_benchmark_reports(
            bench_dir,
            run_summary_path=run_summary_path,
            repo_root=repo_root,
        )

        assert (bench_dir / "phase_analytics.json").exists()
        assert (bench_dir / "token_economics.json").exists()
        assert (bench_dir / "timing_profile.json").exists()

    def test_projection_observed_workload(self, phase_b_fixture):
        bench_dir, run_summary_path, repo_root = phase_b_fixture
        run_benchmark_reports(
            bench_dir,
            run_summary_path=run_summary_path,
            repo_root=repo_root,
        )

        proj = json.loads(
            (bench_dir / "provider_projection.json").read_text(encoding="utf-8")
        )
        obs = proj["observed_workload"]

        assert obs["total_invocations"] == EXPECTED_INVOCATION_COUNT
        assert obs["total_estimated_input_tokens"] == EXPECTED_INPUT_TOKENS
        assert obs["total_estimated_output_tokens"] == EXPECTED_OUTPUT_TOKENS
        assert obs["total_estimated_tokens"] == EXPECTED_TOTAL_TOKENS

        # Internal consistency
        assert (
            obs["total_estimated_input_tokens"]
            + obs["total_estimated_output_tokens"]
            == obs["total_estimated_tokens"]
        )
        assert obs["tapm_invocation_count"] == EXPECTED_INVOCATION_COUNT
        assert obs["cli_prompt_invocation_count"] == 0
        assert obs["phases_1_7_estimated_total_tokens"] == EXPECTED_TOTAL_TOKENS
        assert obs["phase_8_estimated_total_tokens"] == 0

    def test_projection_has_routing_recommendations(self, phase_b_fixture):
        bench_dir, run_summary_path, repo_root = phase_b_fixture
        run_benchmark_reports(
            bench_dir,
            run_summary_path=run_summary_path,
            repo_root=repo_root,
        )

        proj = json.loads(
            (bench_dir / "provider_projection.json").read_text(encoding="utf-8")
        )
        assert "routing_recommendations" in proj
        assert isinstance(proj["routing_recommendations"], list)

    def test_no_prompt_content_in_projection(self, phase_b_fixture):
        bench_dir, run_summary_path, repo_root = phase_b_fixture
        run_benchmark_reports(
            bench_dir,
            run_summary_path=run_summary_path,
            repo_root=repo_root,
        )

        content = (bench_dir / "provider_projection.json").read_text(encoding="utf-8")
        # Should not contain actual prompt content keys (system_prompt_supported is fine)
        assert "system_prompt_chars" not in content
        assert "user_prompt_chars" not in content
        assert "response_text" not in content
        assert "prompt_content" not in content

    def test_no_prompt_content_in_any_artifact(self, phase_b_fixture):
        bench_dir, run_summary_path, repo_root = phase_b_fixture
        run_benchmark_reports(
            bench_dir,
            run_summary_path=run_summary_path,
            repo_root=repo_root,
        )

        for name in [
            "phase_analytics.json",
            "token_economics.json",
            "timing_profile.json",
            "run_benchmark_summary.json",
            "provider_projection.json",
        ]:
            path = bench_dir / name
            if path.exists():
                content = path.read_text(encoding="utf-8")
                # No actual prompt/response content — only metadata counts are acceptable
                assert "response_text" not in content
                assert "prompt_content" not in content

    def test_catalog_has_no_secrets(self, phase_b_fixture):
        _, _, repo_root = phase_b_fixture
        cat_path = repo_root / ".claude" / "benchmark" / "config" / "provider_catalog.json"
        if cat_path.exists():
            content = cat_path.read_text(encoding="utf-8")
            for secret_term in ["api_key", "secret", "token\":", "password",
                                "tenant_id", "organization_id"]:
                assert secret_term not in content.lower(), (
                    f"Potential secret found in catalog: {secret_term}"
                )


class TestPhaseCFailureIsolation:
    """Phase C failure must not break Phase B or orchestration."""

    def test_phase_c_failure_preserves_phase_b(self, phase_b_fixture):
        bench_dir, run_summary_path, repo_root = phase_b_fixture

        # Force Phase C to fail
        with mock.patch(
            "runner.benchmark.report_builder._run_phase_c_projection",
            side_effect=RuntimeError("Phase C boom"),
        ):
            paths = run_benchmark_reports(
                bench_dir,
                run_summary_path=run_summary_path,
                repo_root=repo_root,
            )

        # Phase B artifacts should still be written
        assert len(paths) >= 4  # 3 Phase B artifacts + summary
        assert (bench_dir / "phase_analytics.json").exists()
        assert (bench_dir / "token_economics.json").exists()
        assert (bench_dir / "timing_profile.json").exists()
        assert (bench_dir / "run_benchmark_summary.json").exists()

        # provider_projection should NOT exist since Phase C failed
        assert not (bench_dir / "provider_projection.json").exists()

        # Summary should still be at Phase B stage
        summary = json.loads(
            (bench_dir / "run_benchmark_summary.json").read_text(encoding="utf-8")
        )
        assert summary["benchmark_stage"] == "phase_b_analytics"

    def test_phase_b_failure_skips_phase_c(self, phase_b_fixture):
        bench_dir, run_summary_path, repo_root = phase_b_fixture

        # Force Phase B to fail
        with mock.patch(
            "runner.benchmark.report_builder._run_phase_b_analytics_inner",
            side_effect=RuntimeError("Phase B boom"),
        ):
            paths = run_benchmark_reports(
                bench_dir,
                run_summary_path=run_summary_path,
                repo_root=repo_root,
            )

        # Nothing should be written
        assert paths == []
        assert not (bench_dir / "provider_projection.json").exists()

    def test_run_phase_b_analytics_backward_compat(self, phase_b_fixture):
        """run_phase_b_analytics still works and does NOT run Phase C."""
        bench_dir, run_summary_path, _ = phase_b_fixture
        paths = run_phase_b_analytics(
            bench_dir, run_summary_path=run_summary_path
        )
        assert len(paths) == 4  # Phase B artifacts only

        summary = json.loads(
            (bench_dir / "run_benchmark_summary.json").read_text(encoding="utf-8")
        )
        assert summary["benchmark_stage"] == "phase_b_analytics"
        assert "provider_projection_summary" not in summary


class TestPhaseCWithRealCatalog:
    """Verify projection works with the actual repo catalog."""

    def test_real_catalog_projection_structure(self, phase_b_fixture):
        bench_dir, run_summary_path, repo_root = phase_b_fixture
        run_benchmark_reports(
            bench_dir,
            run_summary_path=run_summary_path,
            repo_root=repo_root,
        )

        proj = json.loads(
            (bench_dir / "provider_projection.json").read_text(encoding="utf-8")
        )

        assert proj["benchmark_schema_version"] == "1.0.0"
        assert proj["pricing_basis"]["source"] == "static_provider_catalog"
        assert len(proj["projections"]) > 0

        # Every projection has required fields
        for p in proj["projections"]:
            assert "provider_id" in p
            assert "model_id" in p
            assert "billing_model" in p
            assert "projected_total_cost_usd" in p
            assert "context_window_sufficient" in p
            assert "migration_complexity" in p
            assert "security_posture" in p

    def test_recommendations_populated(self, phase_b_fixture):
        bench_dir, run_summary_path, repo_root = phase_b_fixture
        run_benchmark_reports(
            bench_dir,
            run_summary_path=run_summary_path,
            repo_root=repo_root,
        )

        proj = json.loads(
            (bench_dir / "provider_projection.json").read_text(encoding="utf-8")
        )

        recs = proj["recommendations"]
        assert recs["lowest_projected_cost"] is not None or recs["best_capability_match"] is not None
        assert isinstance(recs["not_suitable"], list)
        assert isinstance(recs["migration_warnings"], list)
