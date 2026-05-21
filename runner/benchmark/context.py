"""
Benchmark context variable — injection mechanism for the active ledger.

The ledger is set by ``DAGScheduler.run()`` at run start and cleared at
run end.  When ``get_ledger()`` returns ``None``, all benchmark recording
is silently skipped with effectively zero overhead (~50ns context-var
lookup).

Uses ``contextvars.ContextVar`` for safe scoping.
"""

from __future__ import annotations

from contextvars import ContextVar
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from runner.benchmark.ledger import BenchmarkLedger

_active_ledger: ContextVar[BenchmarkLedger | None] = ContextVar(
    "_active_ledger", default=None
)


def get_ledger() -> BenchmarkLedger | None:
    """Return the active benchmark ledger, or None if benchmarking is disabled."""
    return _active_ledger.get()


def set_ledger(ledger: BenchmarkLedger | None) -> None:
    """Set the active benchmark ledger for the current execution context."""
    _active_ledger.set(ledger)
