"""Tests for runner.benchmark.models — data model classes."""

import pytest
from dataclasses import FrozenInstanceError

from runner.benchmark.models import (
    BenchmarkInvocationRecord,
    NodeBenchmarkRecord,
    PhaseBenchmarkRecord,
    RunBenchmarkSummary,
)


def _make_record(**overrides) -> BenchmarkInvocationRecord:
    """Factory helper for BenchmarkInvocationRecord with defaults."""
    defaults = dict(
        invocation_id="abc123",
        run_id="run-001",
        node_id="n01_call_analysis",
        skill_id="call-analysis",
        predicate_id=None,
        invocation_type="skill_tapm",
        execution_mode="tapm",
        model="claude-sonnet-4-6",
        timeout_seconds=1200,
        tools_enabled=["Read", "Glob"],
        system_prompt_chars=5000,
        user_prompt_chars=3000,
        response_chars=2000,
        response_status="success",
        wall_clock_start=100.0,
        wall_clock_end=110.0,
        wall_clock_seconds=10.0,
        timestamp_utc="2026-05-19T00:00:00+00:00",
        estimated_input_tokens=2285,
        estimated_output_tokens=571,
        error_class=None,
        error_message=None,
    )
    defaults.update(overrides)
    return BenchmarkInvocationRecord(**defaults)


class TestBenchmarkInvocationRecord:
    """Test BenchmarkInvocationRecord frozen dataclass."""

    def test_construction(self):
        r = _make_record()
        assert r.invocation_id == "abc123"
        assert r.model == "claude-sonnet-4-6"
        assert r.tools_enabled == ["Read", "Glob"]

    def test_frozen(self):
        r = _make_record()
        with pytest.raises(FrozenInstanceError):
            r.invocation_id = "other"  # type: ignore[misc]

    def test_none_fields(self):
        r = _make_record(node_id=None, skill_id=None, response_chars=None)
        assert r.node_id is None
        assert r.skill_id is None
        assert r.response_chars is None

    def test_error_fields(self):
        r = _make_record(
            response_status="error",
            error_class="ClaudeTransportError",
            error_message="CLI failed",
            response_chars=None,
        )
        assert r.error_class == "ClaudeTransportError"
        assert r.response_status == "error"

    def test_semantic_predicate_record(self):
        r = _make_record(
            skill_id=None,
            predicate_id="no_unresolved_scope_conflicts",
            invocation_type="semantic_predicate",
            execution_mode="cli-prompt",
            tools_enabled=[],
        )
        assert r.predicate_id == "no_unresolved_scope_conflicts"
        assert r.invocation_type == "semantic_predicate"


class TestNodeBenchmarkRecord:
    """Test NodeBenchmarkRecord frozen dataclass."""

    def test_construction(self):
        r = NodeBenchmarkRecord(
            node_id="n01_call_analysis",
            dispatch_wall_clock_seconds=45.5,
            total_invocations=3,
            total_estimated_input_tokens=10000,
            total_estimated_output_tokens=3000,
        )
        assert r.node_id == "n01_call_analysis"
        assert r.total_invocations == 3

    def test_frozen(self):
        r = NodeBenchmarkRecord(
            node_id="n01",
            dispatch_wall_clock_seconds=1.0,
            total_invocations=1,
            total_estimated_input_tokens=100,
            total_estimated_output_tokens=50,
        )
        with pytest.raises(FrozenInstanceError):
            r.node_id = "other"  # type: ignore[misc]


class TestPhaseBenchmarkRecord:
    """Test PhaseBenchmarkRecord frozen dataclass."""

    def test_construction(self):
        r = PhaseBenchmarkRecord(
            phase_number=1,
            phase_id="phase1_call_analysis",
            total_wall_clock_seconds=120.0,
            nodes_dispatched=1,
            total_invocations=5,
            total_estimated_input_tokens=20000,
            total_estimated_output_tokens=5000,
        )
        assert r.phase_number == 1
        assert r.total_invocations == 5


class TestRunBenchmarkSummary:
    """Test RunBenchmarkSummary mutable dataclass."""

    def test_construction_defaults(self):
        s = RunBenchmarkSummary(run_id="run-001")
        assert s.run_id == "run-001"
        assert s.benchmark_version == "1.0.0"
        assert s.total_invocations == 0
        assert s.node_records == []

    def test_to_dict(self):
        s = RunBenchmarkSummary(run_id="run-001", total_invocations=5)
        d = s.to_dict()
        assert d["benchmark_schema_version"] == "1.0.0"
        assert d["run_id"] == "run-001"
        assert d["total_invocations"] == 5
        assert isinstance(d["node_records"], list)

    def test_mutable(self):
        s = RunBenchmarkSummary(run_id="run-001")
        s.total_invocations = 10
        assert s.total_invocations == 10

    def test_to_dict_with_node_records(self):
        s = RunBenchmarkSummary(
            run_id="r",
            node_records=[{"node_id": "n01", "dispatched": True}],
        )
        d = s.to_dict()
        assert len(d["node_records"]) == 1
        assert d["node_records"][0]["node_id"] == "n01"
