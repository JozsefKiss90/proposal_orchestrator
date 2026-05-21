"""Tests for runner.benchmark.report_builder — Phase B artifact generation."""

import json
import shutil
from pathlib import Path

import pytest

from runner.benchmark.report_builder import run_phase_b_analytics


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_ledger(bench_dir: Path, records: list[dict] | None = None) -> Path:
    """Create a minimal invocation_ledger.jsonl in bench_dir."""
    bench_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = bench_dir / "invocation_ledger.jsonl"
    if records is None:
        records = [_default_record()]
    lines = [json.dumps(r, separators=(",", ":")) for r in records]
    ledger_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return ledger_path


def _create_phase_a_summary(bench_dir: Path, overrides: dict | None = None) -> Path:
    bench_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "benchmark_schema_version": "1.0.0",
        "run_id": "test-run",
        "started_at": "2026-01-01T00:00:00+00:00",
        "completed_at": "2026-01-01T00:01:00+00:00",
        "total_invocations": 1,
        "total_estimated_input_tokens": 1000,
        "total_estimated_output_tokens": 500,
        "total_wall_clock_seconds": 60.0,
        "node_records": [{"node_id": "n01_call_analysis", "dispatched": True}],
    }
    if overrides:
        summary.update(overrides)
    path = bench_dir / "run_benchmark_summary.json"
    path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return path


def _create_run_summary(path: Path, overrides: dict | None = None) -> Path:
    summary = {
        "run_id": "test-run",
        "phase_scope": 1,
        "phase_scope_nodes": ["n01_call_analysis"],
        "overall_status": "pass",
        "node_states": {"n01_call_analysis": "released"},
        "dispatched_nodes": ["n01_call_analysis"],
    }
    if overrides:
        summary.update(overrides)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return path


def _default_record() -> dict:
    return {
        "invocation_id": "inv-001",
        "run_id": "test-run",
        "node_id": None,
        "skill_id": "call-requirements-extraction",
        "predicate_id": None,
        "invocation_type": "skill_tapm",
        "execution_mode": "tapm",
        "model": "claude-sonnet-4-6",
        "timeout_seconds": 1200,
        "tools_enabled": ["Read", "Glob"],
        "system_prompt_chars": 1000,
        "user_prompt_chars": 5000,
        "response_chars": 3000,
        "response_status": "success",
        "wall_clock_start": 100.0,
        "wall_clock_end": 110.0,
        "wall_clock_seconds": 10.0,
        "timestamp_utc": "2026-01-01T00:00:00+00:00",
        "estimated_input_tokens": 1000,
        "estimated_output_tokens": 500,
        "error_class": None,
        "error_message": None,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestReportBuilderReadsLedger:
    def test_reads_jsonl_ledger(self, tmp_path):
        bench_dir = tmp_path / ".claude" / "benchmark" / "test-run"
        _create_ledger(bench_dir)
        _create_phase_a_summary(bench_dir)
        paths = run_phase_b_analytics(bench_dir)
        assert len(paths) == 4  # 3 artifacts + expanded summary

    def test_reads_phase_a_summary(self, tmp_path):
        bench_dir = tmp_path / ".claude" / "benchmark" / "test-run"
        _create_ledger(bench_dir)
        _create_phase_a_summary(bench_dir)
        paths = run_phase_b_analytics(bench_dir)

        # Check expanded summary preserves Phase A fields
        summary = json.loads(
            (bench_dir / "run_benchmark_summary.json").read_text(encoding="utf-8")
        )
        assert summary["benchmark_schema_version"] == "1.0.0"
        assert summary["run_id"] == "test-run"
        assert summary["total_invocations"] == 1

    def test_reads_run_summary(self, tmp_path):
        bench_dir = tmp_path / ".claude" / "benchmark" / "test-run"
        _create_ledger(bench_dir)
        _create_phase_a_summary(bench_dir)
        run_summary_path = tmp_path / ".claude" / "runs" / "test-run" / "run_summary.json"
        _create_run_summary(run_summary_path)

        paths = run_phase_b_analytics(bench_dir, run_summary_path=run_summary_path)
        assert len(paths) == 4

        # Phase analytics should reflect phase_scope from run_summary
        pa = json.loads(
            (bench_dir / "phase_analytics.json").read_text(encoding="utf-8")
        )
        assert pa["phase_scope"] == 1


class TestReportBuilderWritesArtifacts:
    def test_writes_phase_analytics(self, tmp_path):
        bench_dir = tmp_path / ".claude" / "benchmark" / "test-run"
        _create_ledger(bench_dir)
        _create_phase_a_summary(bench_dir)
        run_phase_b_analytics(bench_dir)

        path = bench_dir / "phase_analytics.json"
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "total_invocations" in data

    def test_writes_token_economics(self, tmp_path):
        bench_dir = tmp_path / ".claude" / "benchmark" / "test-run"
        _create_ledger(bench_dir)
        _create_phase_a_summary(bench_dir)
        run_phase_b_analytics(bench_dir)

        path = bench_dir / "token_economics.json"
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["total_estimated_tokens"] == 1500

    def test_writes_timing_profile(self, tmp_path):
        bench_dir = tmp_path / ".claude" / "benchmark" / "test-run"
        _create_ledger(bench_dir)
        _create_phase_a_summary(bench_dir)
        run_phase_b_analytics(bench_dir)

        path = bench_dir / "timing_profile.json"
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "mean_invocation_seconds" in data

    def test_expanded_summary_preserves_phase_a(self, tmp_path):
        bench_dir = tmp_path / ".claude" / "benchmark" / "test-run"
        _create_ledger(bench_dir)
        _create_phase_a_summary(bench_dir)
        run_phase_b_analytics(bench_dir)

        summary = json.loads(
            (bench_dir / "run_benchmark_summary.json").read_text(encoding="utf-8")
        )
        # All Phase A fields preserved
        assert summary["benchmark_schema_version"] == "1.0.0"
        assert summary["started_at"] == "2026-01-01T00:00:00+00:00"
        assert summary["completed_at"] == "2026-01-01T00:01:00+00:00"
        assert summary["total_estimated_input_tokens"] == 1000
        assert summary["total_estimated_output_tokens"] == 500
        assert summary["total_wall_clock_seconds"] == 60.0
        assert summary["node_records"] == [{"node_id": "n01_call_analysis", "dispatched": True}]

        # Phase B additions
        assert summary["benchmark_stage"] == "phase_b_analytics"
        assert "phase_analytics_summary" in summary
        assert "token_economics_summary" in summary
        assert "timing_summary" in summary
        assert "phase_b_artifact_paths" in summary


class TestReportBuilderEdgeCases:
    def test_missing_run_summary_handled(self, tmp_path):
        bench_dir = tmp_path / ".claude" / "benchmark" / "test-run"
        _create_ledger(bench_dir)
        _create_phase_a_summary(bench_dir)

        # No run_summary_path provided — should still succeed
        paths = run_phase_b_analytics(bench_dir)
        assert len(paths) == 4

    def test_missing_run_summary_file_handled(self, tmp_path):
        bench_dir = tmp_path / ".claude" / "benchmark" / "test-run"
        _create_ledger(bench_dir)
        _create_phase_a_summary(bench_dir)

        # Point to non-existent file
        paths = run_phase_b_analytics(
            bench_dir,
            run_summary_path=tmp_path / "nonexistent" / "run_summary.json",
        )
        assert len(paths) == 4

    def test_malformed_ledger_line_skipped(self, tmp_path):
        bench_dir = tmp_path / ".claude" / "benchmark" / "test-run"
        bench_dir.mkdir(parents=True, exist_ok=True)

        # Write ledger with one good line and one bad line
        ledger_path = bench_dir / "invocation_ledger.jsonl"
        good_line = json.dumps(_default_record(), separators=(",", ":"))
        ledger_path.write_text(
            good_line + "\n" + "NOT VALID JSON\n" + good_line + "\n",
            encoding="utf-8",
        )
        _create_phase_a_summary(bench_dir)

        paths = run_phase_b_analytics(bench_dir)
        assert len(paths) == 4

        # Should have parsed 2 records (skipped the bad one)
        pa = json.loads(
            (bench_dir / "phase_analytics.json").read_text(encoding="utf-8")
        )
        assert pa["total_invocations"] == 2

    def test_empty_ledger(self, tmp_path):
        bench_dir = tmp_path / ".claude" / "benchmark" / "test-run"
        bench_dir.mkdir(parents=True, exist_ok=True)
        (bench_dir / "invocation_ledger.jsonl").write_text("", encoding="utf-8")
        _create_phase_a_summary(bench_dir)

        paths = run_phase_b_analytics(bench_dir)
        assert len(paths) == 4

    def test_failures_swallowed(self, tmp_path):
        """run_phase_b_analytics should never raise to the caller."""
        import unittest.mock as mock

        bench_dir = tmp_path / ".claude" / "benchmark" / "test-run"
        _create_ledger(bench_dir)
        _create_phase_a_summary(bench_dir)

        # Force an internal error during artifact writing
        with mock.patch(
            "runner.benchmark.report_builder._write_json_atomic",
            side_effect=OSError("disk full"),
        ):
            paths = run_phase_b_analytics(bench_dir)
        assert paths == []

    def test_no_prompt_content_in_artifacts(self, tmp_path):
        bench_dir = tmp_path / ".claude" / "benchmark" / "test-run"
        _create_ledger(bench_dir)
        _create_phase_a_summary(bench_dir)
        run_phase_b_analytics(bench_dir)

        for name in ["phase_analytics.json", "token_economics.json", "timing_profile.json", "run_benchmark_summary.json"]:
            content = (bench_dir / name).read_text(encoding="utf-8")
            assert "system_prompt" not in content or "system_prompt_chars" in content
            assert "user_prompt" not in content or "user_prompt_chars" in content
            assert "response_text" not in content


class TestReportBuilderInference:
    """Verify report_builder passes context for node/phase inference."""

    def test_single_node_inference_end_to_end(self, tmp_path):
        """Records without node_id get node inferred from summaries."""
        bench_dir = tmp_path / ".claude" / "benchmark" / "test-run"
        _create_ledger(bench_dir)  # default record has node_id=None
        _create_phase_a_summary(bench_dir)
        run_summary_path = tmp_path / ".claude" / "runs" / "test-run" / "run_summary.json"
        _create_run_summary(run_summary_path)

        run_phase_b_analytics(bench_dir, run_summary_path=run_summary_path)

        pa = json.loads(
            (bench_dir / "phase_analytics.json").read_text(encoding="utf-8")
        )
        assert pa["phases_observed"] == [1]
        assert pa["nodes_observed"] == ["n01_call_analysis"]
        assert pa["per_phase"]["1"]["invocations"] == 1
        assert pa["per_node"]["n01_call_analysis"]["invocations"] == 1

        te = json.loads(
            (bench_dir / "token_economics.json").read_text(encoding="utf-8")
        )
        assert te["phases_1_7_estimated_total_tokens"] == te["total_estimated_tokens"]
        assert te["phase_8_estimated_total_tokens"] == 0

    def test_inference_from_phase_a_summary_without_run_summary(self, tmp_path):
        """When no run_summary is given, phase_a_summary node_records is used."""
        bench_dir = tmp_path / ".claude" / "benchmark" / "test-run"
        _create_ledger(bench_dir)
        _create_phase_a_summary(bench_dir)
        # No run_summary
        run_phase_b_analytics(bench_dir)

        pa = json.loads(
            (bench_dir / "phase_analytics.json").read_text(encoding="utf-8")
        )
        assert pa["nodes_observed"] == ["n01_call_analysis"]
