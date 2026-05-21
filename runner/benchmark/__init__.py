"""
Benchmarking subsystem — passive observability layer (Phase A).

Captures per-invocation telemetry for all ``invoke_claude_text()`` calls
without modifying the transport function, gate logic, artifact schemas,
or scheduler state machine semantics.

Benchmark artifacts are runtime execution memory (``.claude/benchmark/``),
not constitutional source truth (``docs/``).  Benchmark failures never
affect orchestration outcomes.

Public API
----------
get_ledger / set_ledger
    Context variable for the active benchmark ledger.
BenchmarkLedger
    Append-only invocation log.
instrumented_invoke
    Drop-in wrapper around ``invoke_claude_text()`` that captures telemetry.
BenchmarkInvocationRecord
    Immutable record of a single Claude invocation.
estimate_tokens
    Character-count-based token estimation.
"""

from runner.benchmark.context import get_ledger, set_ledger
from runner.benchmark.ledger import BenchmarkLedger
from runner.benchmark.models import BenchmarkInvocationRecord
from runner.benchmark.token_estimator import estimate_tokens
from runner.benchmark.transport_hook import instrumented_invoke

__all__ = [
    "get_ledger",
    "set_ledger",
    "BenchmarkLedger",
    "BenchmarkInvocationRecord",
    "estimate_tokens",
    "instrumented_invoke",
]
