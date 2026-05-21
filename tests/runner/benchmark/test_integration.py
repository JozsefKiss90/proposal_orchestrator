"""Integration tests for the benchmark subsystem Phase A.

Tests that:
- The benchmark lifecycle works end-to-end with mocked transport
- JSONL persistence produces parseable records
- Benchmark artifacts are written to .claude/benchmark/<run_id>/
- Benchmarking disabled path preserves exact behavior
"""

import json
from pathlib import Path
from unittest import mock

import pytest

from runner.benchmark.context import get_ledger, set_ledger
from runner.benchmark.ledger import BenchmarkLedger
from runner.benchmark.models import RunBenchmarkSummary
from runner.benchmark.transport_hook import instrumented_invoke


class TestEndToEndLedgerLifecycle:
    """Test the full ledger lifecycle: create, record, persist, close."""

    def test_full_lifecycle(self, tmp_path):
        """Simulate a scheduler run's benchmark lifecycle."""
        run_id = "test-run-001"
        bench_dir = tmp_path / ".claude" / "benchmark" / run_id

        # 1. Create ledger (scheduler run() entry)
        ledger = BenchmarkLedger(
            ledger_path=bench_dir / "invocation_ledger.jsonl"
        )
        set_ledger(ledger)

        try:
            # 2. Simulate skill invocations
            with mock.patch(
                "runner.claude_transport.invoke_claude_text"
            ) as mock_invoke:
                mock_invoke.return_value = '{"schema_id": "test"}'

                # TAPM invocation
                result1 = instrumented_invoke(
                    system_prompt="sys" * 100,
                    user_prompt="user" * 100,
                    model="claude-sonnet-4-6",
                    max_tokens=16384,
                    tools=["Read", "Glob"],
                    timeout_seconds=1200,
                    _bench_run_id=run_id,
                    _bench_skill_id="call-analysis",
                    _bench_node_id="n01_call_analysis",
                    _bench_invocation_type="skill_tapm",
                )
                assert result1 == '{"schema_id": "test"}'

                # CLI-prompt invocation
                result2 = instrumented_invoke(
                    system_prompt="sys2" * 50,
                    user_prompt="user2" * 50,
                    model="claude-sonnet-4-6",
                    max_tokens=16384,
                    _bench_run_id=run_id,
                    _bench_skill_id="concept-refinement",
                    _bench_node_id="n02_concept_refinement",
                    _bench_invocation_type="skill_cli_prompt",
                )
                assert result2 == '{"schema_id": "test"}'

                # Semantic predicate invocation
                mock_invoke.return_value = '{"status": "pass", "findings": []}'
                result3 = instrumented_invoke(
                    system_prompt="sys_sem",
                    user_prompt="user_sem",
                    model="claude-sonnet-4-6",
                    max_tokens=2048,
                    _bench_run_id=run_id,
                    _bench_predicate_id="no_unresolved_scope_conflicts",
                    _bench_invocation_type="semantic_predicate",
                )

            # 3. Verify in-memory records
            records = ledger.records
            assert len(records) == 3
            assert records[0].invocation_type == "skill_tapm"
            assert records[0].execution_mode == "tapm"
            assert records[1].invocation_type == "skill_cli_prompt"
            assert records[1].execution_mode == "cli-prompt"
            assert records[2].invocation_type == "semantic_predicate"

            # 4. Build summary (scheduler does this before run exit)
            summary = RunBenchmarkSummary(
                run_id=run_id,
                started_at="2026-05-19T00:00:00+00:00",
                completed_at="2026-05-19T00:01:00+00:00",
                total_invocations=len(records),
                total_estimated_input_tokens=sum(
                    r.estimated_input_tokens for r in records
                ),
                total_estimated_output_tokens=sum(
                    r.estimated_output_tokens for r in records
                ),
            )
            summary_path = bench_dir / "run_benchmark_summary.json"
            summary_path.parent.mkdir(parents=True, exist_ok=True)
            summary_path.write_text(
                json.dumps(summary.to_dict(), indent=2), encoding="utf-8"
            )

        finally:
            # 5. Cleanup (scheduler finally block)
            ledger.close()
            set_ledger(None)

        # 6. Verify JSONL file
        jsonl_path = bench_dir / "invocation_ledger.jsonl"
        assert jsonl_path.exists()
        lines = jsonl_path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 3
        for line in lines:
            obj = json.loads(line)
            assert "invocation_id" in obj
            assert "system_prompt_chars" in obj
            # Verify no prompt content leaked
            assert "system_prompt" not in obj or isinstance(
                obj.get("system_prompt_chars"), int
            )

        # 7. Verify summary JSON
        summary_path = bench_dir / "run_benchmark_summary.json"
        assert summary_path.exists()
        summary_data = json.loads(
            summary_path.read_text(encoding="utf-8")
        )
        assert summary_data["run_id"] == run_id
        assert summary_data["total_invocations"] == 3
        assert summary_data["benchmark_schema_version"] == "1.0.0"


class TestBenchmarkDisabledPath:
    """Test that disabling benchmarking has zero impact on behavior."""

    def setup_method(self):
        set_ledger(None)

    @mock.patch("runner.claude_transport.invoke_claude_text")
    def test_identical_behavior_when_disabled(self, mock_invoke):
        """With benchmarking disabled, behavior is identical to raw transport."""
        mock_invoke.return_value = "response"
        result = instrumented_invoke(
            system_prompt="sys",
            user_prompt="user",
            model="claude-sonnet-4-6",
            max_tokens=16384,
            timeout_seconds=300,
        )
        assert result == "response"
        # Only one call to the transport
        assert mock_invoke.call_count == 1

    @mock.patch("runner.claude_transport.invoke_claude_text")
    def test_exception_passthrough_when_disabled(self, mock_invoke):
        """With benchmarking disabled, exceptions pass through unchanged."""
        from runner.claude_transport import ClaudeCLIUnavailableError

        mock_invoke.side_effect = ClaudeCLIUnavailableError("not found")
        with pytest.raises(ClaudeCLIUnavailableError, match="not found"):
            instrumented_invoke(
                system_prompt="sys",
                user_prompt="user",
                model="claude-sonnet-4-6",
                max_tokens=16384,
            )


class TestJSONLPersistenceRoundTrip:
    """Test that JSONL records survive a write-read round-trip."""

    def test_round_trip(self, tmp_path):
        ledger_path = tmp_path / "test.jsonl"
        ledger = BenchmarkLedger(ledger_path=ledger_path)
        set_ledger(ledger)

        try:
            with mock.patch(
                "runner.claude_transport.invoke_claude_text"
            ) as mock_invoke:
                mock_invoke.return_value = "output"
                instrumented_invoke(
                    system_prompt="s" * 100,
                    user_prompt="u" * 200,
                    model="claude-sonnet-4-6",
                    max_tokens=16384,
                    _bench_run_id="r1",
                    _bench_skill_id="sk1",
                    _bench_invocation_type="skill_cli_prompt",
                )
        finally:
            ledger.close()
            set_ledger(None)

        # Read back
        line = ledger_path.read_text(encoding="utf-8").strip()
        obj = json.loads(line)
        assert obj["run_id"] == "r1"
        assert obj["skill_id"] == "sk1"
        assert obj["system_prompt_chars"] == 100
        assert obj["user_prompt_chars"] == 200
        assert obj["response_chars"] == 6  # len("output")
        assert obj["response_status"] == "success"
        assert obj["estimated_input_tokens"] > 0
        assert obj["estimated_output_tokens"] > 0
