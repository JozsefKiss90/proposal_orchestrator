"""
Benchmark data models — immutable records for invocation telemetry.

All models use ``@dataclass(frozen=True)`` for immutability.
Only ``RunBenchmarkSummary`` is mutable (populated incrementally).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class BenchmarkInvocationRecord:
    """Immutable record of a single ``invoke_claude_text()`` call."""

    # Identity
    invocation_id: str
    run_id: str
    node_id: str | None
    skill_id: str | None
    predicate_id: str | None

    # Classification
    invocation_type: str  # "skill_tapm" | "skill_cli_prompt" | "semantic_predicate"
    execution_mode: str   # "tapm" | "cli-prompt"

    # Model configuration
    model: str
    timeout_seconds: int
    tools_enabled: list[str]

    # Prompt metrics (character counts only, never content)
    system_prompt_chars: int
    user_prompt_chars: int

    # Response metrics
    response_chars: int | None
    response_status: str  # "success" | "timeout" | "error" | "empty"

    # Timing
    wall_clock_start: float
    wall_clock_end: float
    wall_clock_seconds: float
    timestamp_utc: str

    # Token estimates
    estimated_input_tokens: int
    estimated_output_tokens: int

    # Error context
    error_class: str | None
    error_message: str | None


@dataclass(frozen=True)
class NodeBenchmarkRecord:
    """Aggregated benchmark data for a single node dispatch."""

    node_id: str
    dispatch_wall_clock_seconds: float
    total_invocations: int
    total_estimated_input_tokens: int
    total_estimated_output_tokens: int


@dataclass(frozen=True)
class PhaseBenchmarkRecord:
    """Aggregated benchmark data for a complete phase."""

    phase_number: int
    phase_id: str
    total_wall_clock_seconds: float
    nodes_dispatched: int
    total_invocations: int
    total_estimated_input_tokens: int
    total_estimated_output_tokens: int


@dataclass
class RunBenchmarkSummary:
    """Minimal run-level benchmark summary for Phase A."""

    run_id: str
    benchmark_version: str = "1.0.0"
    started_at: str = ""
    completed_at: str = ""
    total_invocations: int = 0
    total_estimated_input_tokens: int = 0
    total_estimated_output_tokens: int = 0
    total_wall_clock_seconds: float = 0.0
    node_records: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dict."""
        return {
            "benchmark_schema_version": self.benchmark_version,
            "run_id": self.run_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "total_invocations": self.total_invocations,
            "total_estimated_input_tokens": self.total_estimated_input_tokens,
            "total_estimated_output_tokens": self.total_estimated_output_tokens,
            "total_wall_clock_seconds": self.total_wall_clock_seconds,
            "node_records": self.node_records,
        }
