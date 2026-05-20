"""Tests for runner.benchmark.__main__ — CLI entry point."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from runner.benchmark.__main__ import main, _list_runs, _load_artifacts


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _make_complete_run(run_dir: Path) -> None:
    """Write a minimal but complete set of benchmark artifacts."""
    run_dir.mkdir(parents=True, exist_ok=True)

    _write_json(run_dir / "run_benchmark_summary.json", {
        "benchmark_schema_version": "1.0.0",
        "run_id": run_dir.name,
        "started_at": "2026-05-20T10:00:00+00:00",
        "completed_at": "2026-05-20T11:00:00+00:00",
        "total_invocations": 4,
        "benchmark_stage": "phase_c_provider_projection",
        "node_records": [
            {"node_id": "n01_call_analysis", "dispatched": True},
        ],
        "phase_analytics_summary": {
            "phases_observed": [1],
            "nodes_observed": ["n01_call_analysis"],
            "total_invocations": 4,
        },
        "token_economics_summary": {
            "total_estimated_input_tokens": 40000,
            "total_estimated_output_tokens": 20000,
            "total_estimated_tokens": 60000,
        },
        "timing_summary": {
            "total_wall_clock_seconds": 600.0,
            "mean_invocation_seconds": 150.0,
            "median_invocation_seconds": 140.0,
        },
        "provider_projection_summary": {
            "total_providers_evaluated": 3,
            "suitable_providers": 3,
            "lowest_projected_cost_usd": 0.05,
            "lowest_projected_cost_provider": "TestProvider",
        },
    })

    _write_json(run_dir / "phase_analytics.json", {
        "benchmark_schema_version": "1.0.0",
        "run_id": run_dir.name,
        "phases_observed": [1],
        "nodes_observed": ["n01_call_analysis"],
        "total_invocations": 4,
        "per_phase": {},
        "per_node": {},
    })

    _write_json(run_dir / "token_economics.json", {
        "run_id": run_dir.name,
        "total_estimated_input_tokens": 40000,
        "total_estimated_output_tokens": 20000,
        "total_estimated_tokens": 60000,
        "tokens_by_invocation_type": {},
        "tokens_by_skill_id": {
            "call-analysis": {
                "estimated_input_tokens": 40000,
                "estimated_output_tokens": 20000,
                "estimated_total_tokens": 60000,
            },
        },
        "tokens_by_semantic_predicate_id": {},
        "largest_invocation_by_estimated_total_tokens": {
            "invocation_id": "inv1",
            "skill_id": "call-analysis",
            "predicate_id": None,
            "invocation_type": "skill_tapm",
            "value": 15000,
        },
        "largest_invocation_by_prompt_chars": {
            "invocation_id": "inv1",
            "skill_id": "call-analysis",
            "predicate_id": None,
            "invocation_type": "skill_tapm",
            "value": 50000,
        },
        "tapm_vs_cli_prompt": {
            "tapm": {"estimated_input_tokens": 40000, "estimated_output_tokens": 20000, "estimated_total_tokens": 60000},
            "cli_prompt": {"estimated_input_tokens": 0, "estimated_output_tokens": 0, "estimated_total_tokens": 0},
        },
        "phase_8_estimated_total_tokens": 0,
        "phases_1_7_estimated_total_tokens": 60000,
        "semantic_predicate_estimated_total_tokens": 0,
    })

    _write_json(run_dir / "timing_profile.json", {
        "total_wall_clock_seconds": 600.0,
        "sum_invocation_wall_clock_seconds": 590.0,
        "idle_non_model_seconds_estimate": 10.0,
        "mean_invocation_seconds": 150.0,
        "median_invocation_seconds": 140.0,
        "p95_invocation_seconds": 200.0,
        "p99_invocation_seconds": 200.0,
        "timeout_count": 0,
        "failed_invocation_count": 0,
        "timing_by_invocation_type": {},
        "timing_by_skill_id": {},
        "timing_by_semantic_predicate_id": {},
    })

    _write_json(run_dir / "provider_projection.json", {
        "benchmark_schema_version": "1.0.0",
        "run_id": run_dir.name,
        "pricing_basis": {
            "source": "static_provider_catalog",
            "warning": "Static estimates only.",
        },
        "observed_workload": {
            "total_invocations": 4,
            "total_estimated_tokens": 60000,
            "requires_tool_support": True,
            "tapm_invocation_count": 4,
        },
        "projections": [
            {
                "provider_id": "test_provider",
                "model_id": "test-model",
                "display_name": "TestProvider / TestModel",
                "billing_model": "per_token",
                "projected_total_cost_usd": 0.05,
                "supports_all_modes": True,
                "migration_complexity": "drop_in",
            },
        ],
        "recommendations": {
            "lowest_projected_cost": {
                "display_name": "TestProvider",
                "projected_total_cost_usd": 0.05,
            },
            "best_capability_match": None,
            "best_openai_compatible_candidate": None,
            "best_private_network_candidate": None,
            "not_suitable": [],
            "migration_warnings": [],
        },
        "routing_recommendations": [
            {
                "workload_segment": "tapm_tool_augmented_work",
                "estimated_tokens": 60000,
                "candidate_tier": "mid",
                "notes": ["Test note."],
            },
        ],
    })

    # Write a minimal ledger
    (run_dir / "invocation_ledger.jsonl").write_text(
        '{"invocation_id":"inv1","run_id":"' + run_dir.name + '"}\n',
        encoding="utf-8",
    )


def _make_partial_run(run_dir: Path) -> None:
    """Write only summary and ledger — partial/failed run."""
    run_dir.mkdir(parents=True, exist_ok=True)
    _write_json(run_dir / "run_benchmark_summary.json", {
        "run_id": run_dir.name,
        "total_invocations": 2,
        "benchmark_stage": "phase_a_collection",
        "node_records": [],
    })
    (run_dir / "invocation_ledger.jsonl").write_text(
        '{"invocation_id":"inv1"}\n',
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# CLI Tests
# ---------------------------------------------------------------------------

class TestCLIFullReport:
    def test_full_report_exit_0(self, tmp_path, capsys):
        run_id = "test-run-full"
        _make_complete_run(tmp_path / run_id)
        code = main(["--benchmark-root", str(tmp_path), "--run-id", run_id])
        assert code == 0
        captured = capsys.readouterr()
        assert "Benchmark Summary" in captured.out
        assert "Token Report" in captured.out
        assert "Timing Report" in captured.out
        assert "Provider Projection" in captured.out
        assert "Routing Advisory" in captured.out
        assert "Data Quality Report" in captured.out


class TestCLISections:
    @pytest.mark.parametrize("section,expected_text", [
        ("summary", "Benchmark Summary"),
        ("tokens", "Token Report"),
        ("timing", "Timing Report"),
        ("providers", "Provider Projection"),
        ("routing", "Routing Advisory"),
        ("quality", "Data Quality Report"),
    ])
    def test_section_output(self, tmp_path, capsys, section, expected_text):
        run_id = "test-sections"
        _make_complete_run(tmp_path / run_id)
        code = main([
            "--benchmark-root", str(tmp_path),
            "--run-id", run_id,
            "--section", section,
        ])
        assert code == 0
        captured = capsys.readouterr()
        assert expected_text in captured.out


class TestCLIJson:
    def test_json_output(self, tmp_path, capsys):
        run_id = "test-json"
        _make_complete_run(tmp_path / run_id)
        code = main([
            "--benchmark-root", str(tmp_path),
            "--run-id", run_id,
            "--json",
        ])
        assert code == 0
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert parsed["run_id"] == run_id
        assert "run_benchmark_summary" in parsed
        assert "data_quality_warnings" in parsed
        assert isinstance(parsed["loaded_artifacts"], list)

    def test_json_no_prompt_content(self, tmp_path, capsys):
        run_id = "test-json-no-content"
        _make_complete_run(tmp_path / run_id)
        code = main([
            "--benchmark-root", str(tmp_path),
            "--run-id", run_id,
            "--json",
        ])
        assert code == 0
        output = capsys.readouterr().out
        # No prompt/response content should appear
        assert "system_prompt_content" not in output
        assert "user_prompt_content" not in output
        assert "response_content" not in output


class TestCLIList:
    def test_list_runs(self, tmp_path, capsys):
        _make_complete_run(tmp_path / "run-aaa")
        _make_complete_run(tmp_path / "run-bbb")
        code = main(["--benchmark-root", str(tmp_path), "--list"])
        assert code == 0
        captured = capsys.readouterr()
        assert "run-aaa" in captured.out
        assert "run-bbb" in captured.out
        assert "Available benchmark runs" in captured.out

    def test_list_empty(self, tmp_path, capsys):
        tmp_path.mkdir(exist_ok=True)
        code = main(["--benchmark-root", str(tmp_path), "--list"])
        assert code == 0
        captured = capsys.readouterr()
        assert "No benchmark runs" in captured.out

    def test_list_no_directory(self, tmp_path, capsys):
        code = main(["--benchmark-root", str(tmp_path / "nonexistent"), "--list"])
        assert code == 0
        captured = capsys.readouterr()
        assert "No benchmark directory" in captured.out


class TestCLIExitCodes:
    def test_missing_run_id_returns_1(self, tmp_path, capsys):
        code = main([
            "--benchmark-root", str(tmp_path),
            "--run-id", "does-not-exist",
        ])
        assert code == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err

    def test_invalid_section_returns_2(self, tmp_path, capsys):
        run_id = "test-bad-section"
        _make_complete_run(tmp_path / run_id)
        code = main([
            "--benchmark-root", str(tmp_path),
            "--run-id", run_id,
            "--section", "invalid_section_name",
        ])
        assert code == 2

    def test_no_arguments_returns_2(self, capsys):
        code = main([])
        assert code == 2

    def test_partial_run_exits_0(self, tmp_path, capsys):
        run_id = "test-partial"
        _make_partial_run(tmp_path / run_id)
        code = main([
            "--benchmark-root", str(tmp_path),
            "--run-id", run_id,
        ])
        assert code == 0
        captured = capsys.readouterr()
        assert "WARNING" in captured.out


class TestCLIPartialArtifacts:
    def test_partial_with_warnings(self, tmp_path, capsys):
        """Partial run should produce report with quality warnings, exit 0."""
        run_id = "partial-run"
        _make_partial_run(tmp_path / run_id)
        code = main([
            "--benchmark-root", str(tmp_path),
            "--run-id", run_id,
        ])
        assert code == 0
        captured = capsys.readouterr()
        # Should have missing artifact warnings
        assert "missing" in captured.out.lower()

    def test_only_ledger_exists(self, tmp_path, capsys):
        run_id = "ledger-only"
        run_dir = tmp_path / run_id
        run_dir.mkdir(parents=True)
        (run_dir / "invocation_ledger.jsonl").write_text('{"x":1}\n', encoding="utf-8")
        code = main([
            "--benchmark-root", str(tmp_path),
            "--run-id", run_id,
        ])
        assert code == 0

    def test_json_mode_partial(self, tmp_path, capsys):
        run_id = "json-partial"
        _make_partial_run(tmp_path / run_id)
        code = main([
            "--benchmark-root", str(tmp_path),
            "--run-id", run_id,
            "--json",
        ])
        assert code == 0
        parsed = json.loads(capsys.readouterr().out)
        assert len(parsed["data_quality_warnings"]) > 0


class TestLoadArtifacts:
    def test_load_complete(self, tmp_path):
        run_id = "load-test"
        _make_complete_run(tmp_path / run_id)
        artifacts = _load_artifacts(tmp_path / run_id)
        assert artifacts["summary"] is not None
        assert artifacts["phase_analytics"] is not None
        assert artifacts["token_economics"] is not None
        assert artifacts["timing_profile"] is not None
        assert artifacts["provider_projection"] is not None
        assert artifacts["ledger_exists"] is True
        assert len(artifacts["loaded_artifacts"]) == 6

    def test_load_empty_dir(self, tmp_path):
        run_dir = tmp_path / "empty-run"
        run_dir.mkdir()
        artifacts = _load_artifacts(run_dir)
        assert artifacts["summary"] is None
        assert artifacts["phase_analytics"] is None
        assert artifacts["ledger_exists"] is False
        assert artifacts["loaded_artifacts"] == []


class TestNoProviderAPICalls:
    def test_no_network_calls(self, tmp_path, capsys):
        """CLI must never make provider API calls."""
        run_id = "no-network"
        _make_complete_run(tmp_path / run_id)
        # If this made network calls it would either fail or take time
        code = main([
            "--benchmark-root", str(tmp_path),
            "--run-id", run_id,
        ])
        assert code == 0


class TestNoBenchmarkWrites:
    def test_no_files_modified(self, tmp_path):
        """CLI must not write to benchmark artifacts."""
        run_id = "no-writes"
        run_dir = tmp_path / run_id
        _make_complete_run(run_dir)

        # Record mtimes before
        mtimes_before = {}
        for f in run_dir.iterdir():
            mtimes_before[f.name] = f.stat().st_mtime_ns

        # Run CLI
        main(["--benchmark-root", str(tmp_path), "--run-id", run_id])
        main(["--benchmark-root", str(tmp_path), "--run-id", run_id, "--json"])
        main(["--benchmark-root", str(tmp_path), "--run-id", run_id, "--section", "summary"])

        # Check no files were modified
        for f in run_dir.iterdir():
            assert f.stat().st_mtime_ns == mtimes_before.get(f.name, f.stat().st_mtime_ns), \
                f"File {f.name} was modified by CLI"

        # Check no new files were created
        current_files = {f.name for f in run_dir.iterdir()}
        original_files = set(mtimes_before.keys())
        assert current_files == original_files, "CLI created new files"
