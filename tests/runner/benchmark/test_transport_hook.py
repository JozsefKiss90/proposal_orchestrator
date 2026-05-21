"""Tests for runner.benchmark.transport_hook — instrumented transport wrapper."""

from unittest import mock

import pytest

from runner.benchmark.context import get_ledger, set_ledger
from runner.benchmark.ledger import BenchmarkLedger
from runner.benchmark.transport_hook import instrumented_invoke
from runner.claude_transport import ClaudeCLITimeoutError, ClaudeTransportError


class TestInstrumentedInvokeDisabled:
    """Test behavior when benchmarking is disabled (ledger is None)."""

    def setup_method(self):
        set_ledger(None)

    def teardown_method(self):
        set_ledger(None)

    @mock.patch("runner.claude_transport.invoke_claude_text")
    def test_passthrough_success(self, mock_invoke):
        """When disabled, passes through to invoke_claude_text exactly."""
        mock_invoke.return_value = "response text"
        result = instrumented_invoke(
            system_prompt="sys",
            user_prompt="user",
            model="claude-sonnet-4-6",
            max_tokens=16384,
            timeout_seconds=300,
        )
        assert result == "response text"
        mock_invoke.assert_called_once_with(
            system_prompt="sys",
            user_prompt="user",
            model="claude-sonnet-4-6",
            max_tokens=16384,
            timeout_seconds=300,
            tools=None,
        )

    @mock.patch("runner.claude_transport.invoke_claude_text")
    def test_passthrough_with_tools(self, mock_invoke):
        mock_invoke.return_value = "ok"
        result = instrumented_invoke(
            system_prompt="sys",
            user_prompt="user",
            model="claude-sonnet-4-6",
            max_tokens=16384,
            tools=["Read", "Glob"],
            timeout_seconds=1200,
        )
        assert result == "ok"
        mock_invoke.assert_called_once_with(
            system_prompt="sys",
            user_prompt="user",
            model="claude-sonnet-4-6",
            max_tokens=16384,
            timeout_seconds=1200,
            tools=["Read", "Glob"],
        )

    @mock.patch("runner.claude_transport.invoke_claude_text")
    def test_passthrough_exception(self, mock_invoke):
        """When disabled, re-raises transport exceptions unchanged."""
        mock_invoke.side_effect = ClaudeTransportError("fail")
        with pytest.raises(ClaudeTransportError, match="fail"):
            instrumented_invoke(
                system_prompt="sys",
                user_prompt="user",
                model="claude-sonnet-4-6",
                max_tokens=16384,
            )

    @mock.patch("runner.claude_transport.invoke_claude_text")
    def test_benchmark_metadata_not_passed(self, mock_invoke):
        """Benchmark metadata args are NOT forwarded to transport."""
        mock_invoke.return_value = "ok"
        instrumented_invoke(
            system_prompt="s",
            user_prompt="u",
            model="m",
            max_tokens=100,
            _bench_run_id="rid",
            _bench_skill_id="sid",
            _bench_node_id="nid",
            _bench_predicate_id="pid",
            _bench_invocation_type="skill_tapm",
        )
        call_kwargs = mock_invoke.call_args[1]
        assert "_bench_run_id" not in call_kwargs
        assert "_bench_skill_id" not in call_kwargs


class TestInstrumentedInvokeEnabled:
    """Test behavior when benchmarking is enabled (ledger is active)."""

    def setup_method(self):
        self.ledger = BenchmarkLedger()
        set_ledger(self.ledger)

    def teardown_method(self):
        set_ledger(None)

    @mock.patch("runner.claude_transport.invoke_claude_text")
    def test_success_records_telemetry(self, mock_invoke):
        """Successful invocation appends a record to the ledger."""
        mock_invoke.return_value = "response text"
        result = instrumented_invoke(
            system_prompt="sys prompt",
            user_prompt="user prompt",
            model="claude-sonnet-4-6",
            max_tokens=16384,
            _bench_run_id="run-001",
            _bench_skill_id="call-analysis",
            _bench_node_id="n01",
            _bench_invocation_type="skill_tapm",
        )
        assert result == "response text"
        assert len(self.ledger.records) == 1

        rec = self.ledger.records[0]
        assert rec.run_id == "run-001"
        assert rec.skill_id == "call-analysis"
        assert rec.node_id == "n01"
        assert rec.invocation_type == "skill_tapm"
        assert rec.execution_mode == "cli-prompt"  # no tools
        assert rec.model == "claude-sonnet-4-6"
        assert rec.system_prompt_chars == len("sys prompt")
        assert rec.user_prompt_chars == len("user prompt")
        assert rec.response_chars == len("response text")
        assert rec.response_status == "success"
        assert rec.error_class is None
        assert rec.wall_clock_seconds >= 0

    @mock.patch("runner.claude_transport.invoke_claude_text")
    def test_success_with_tools(self, mock_invoke):
        """TAPM mode sets execution_mode to 'tapm'."""
        mock_invoke.return_value = "ok"
        instrumented_invoke(
            system_prompt="s",
            user_prompt="u",
            model="claude-sonnet-4-6",
            max_tokens=16384,
            tools=["Read", "Glob"],
            timeout_seconds=1200,
            _bench_invocation_type="skill_tapm",
        )
        rec = self.ledger.records[0]
        assert rec.execution_mode == "tapm"
        assert rec.tools_enabled == ["Read", "Glob"]
        assert rec.timeout_seconds == 1200

    @mock.patch("runner.claude_transport.invoke_claude_text")
    def test_exception_records_telemetry(self, mock_invoke):
        """Transport exception is re-raised AND records error telemetry."""
        mock_invoke.side_effect = ClaudeTransportError("transport fail")
        with pytest.raises(ClaudeTransportError, match="transport fail"):
            instrumented_invoke(
                system_prompt="sys",
                user_prompt="user",
                model="claude-sonnet-4-6",
                max_tokens=16384,
                _bench_run_id="run-002",
            )
        assert len(self.ledger.records) == 1
        rec = self.ledger.records[0]
        assert rec.response_status == "error"
        assert rec.error_class == "ClaudeTransportError"
        assert "transport fail" in rec.error_message
        assert rec.response_chars is None

    @mock.patch("runner.claude_transport.invoke_claude_text")
    def test_timeout_records_timeout_status(self, mock_invoke):
        """Timeout exception is recorded with status 'timeout'."""
        mock_invoke.side_effect = ClaudeCLITimeoutError(
            "timed out",
            timeout_seconds=300,
            elapsed_seconds=300.0,
        )
        with pytest.raises(ClaudeCLITimeoutError):
            instrumented_invoke(
                system_prompt="sys",
                user_prompt="user",
                model="claude-sonnet-4-6",
                max_tokens=16384,
            )
        rec = self.ledger.records[0]
        assert rec.response_status == "timeout"
        assert rec.error_class == "ClaudeCLITimeoutError"

    @mock.patch("runner.claude_transport.invoke_claude_text")
    def test_token_estimates_populated(self, mock_invoke):
        """Token estimates are computed from character counts."""
        mock_invoke.return_value = "x" * 350  # 350 chars
        instrumented_invoke(
            system_prompt="a" * 1750,  # 1750 chars
            user_prompt="b" * 1750,    # 1750 chars
            model="claude-sonnet-4-6",
            max_tokens=16384,
        )
        rec = self.ledger.records[0]
        # Input: 3500 chars / 3.5 = 1000 tokens
        assert rec.estimated_input_tokens == 1000
        # Output: 350 chars / 3.5 = 100 tokens
        assert rec.estimated_output_tokens == 100

    @mock.patch("runner.claude_transport.invoke_claude_text")
    def test_semantic_predicate_metadata(self, mock_invoke):
        """Semantic predicate invocations carry correct metadata."""
        mock_invoke.return_value = '{"status": "pass"}'
        instrumented_invoke(
            system_prompt="sys",
            user_prompt="user",
            model="claude-sonnet-4-6",
            max_tokens=2048,
            _bench_run_id="run-003",
            _bench_predicate_id="no_unresolved_scope_conflicts",
            _bench_invocation_type="semantic_predicate",
        )
        rec = self.ledger.records[0]
        assert rec.predicate_id == "no_unresolved_scope_conflicts"
        assert rec.invocation_type == "semantic_predicate"
        assert rec.skill_id is None

    @mock.patch("runner.claude_transport.invoke_claude_text")
    def test_no_prompt_content_stored(self, mock_invoke):
        """Verify that prompt content is NOT stored in the record."""
        secret = "CONFIDENTIAL_PROJECT_DATA_12345"
        mock_invoke.return_value = "ok"
        instrumented_invoke(
            system_prompt=f"system {secret}",
            user_prompt=f"user {secret}",
            model="claude-sonnet-4-6",
            max_tokens=16384,
        )
        rec = self.ledger.records[0]
        # Record should have char counts, never content
        assert secret not in str(rec.invocation_id)
        assert secret not in str(rec.run_id)
        assert not hasattr(rec, "system_prompt")
        assert not hasattr(rec, "user_prompt")
        assert not hasattr(rec, "response_text")

    @mock.patch("runner.claude_transport.invoke_claude_text")
    def test_invocation_id_unique(self, mock_invoke):
        """Each invocation gets a unique ID."""
        mock_invoke.return_value = "ok"
        for _ in range(5):
            instrumented_invoke(
                system_prompt="s",
                user_prompt="u",
                model="m",
                max_tokens=100,
            )
        ids = {r.invocation_id for r in self.ledger.records}
        assert len(ids) == 5

    @mock.patch("runner.claude_transport.invoke_claude_text")
    def test_return_value_preserved_exactly(self, mock_invoke):
        """Return value is the exact same object from invoke_claude_text."""
        expected = "exact response"
        mock_invoke.return_value = expected
        result = instrumented_invoke(
            system_prompt="s",
            user_prompt="u",
            model="m",
            max_tokens=100,
        )
        assert result is expected


class TestInstrumentedInvokeBenchmarkFailureIsolation:
    """Test that benchmark failures never affect orchestration."""

    def teardown_method(self):
        set_ledger(None)

    @mock.patch("runner.claude_transport.invoke_claude_text")
    def test_ledger_append_failure_swallowed(self, mock_invoke):
        """If ledger.append raises, transport still succeeds."""
        mock_invoke.return_value = "ok"
        ledger = BenchmarkLedger()
        with mock.patch.object(ledger, "append", side_effect=RuntimeError("boom")):
            set_ledger(ledger)
            # Should NOT raise — benchmark failure is swallowed
            result = instrumented_invoke(
                system_prompt="s",
                user_prompt="u",
                model="m",
                max_tokens=100,
            )
            assert result == "ok"
