"""
Append-only JSONL benchmark ledger.

Thread-safe, flush-after-append, exception-swallowing.  Benchmark
failures never propagate to orchestration.

The ledger accumulates records in memory for later summary computation
and simultaneously writes each record as a JSONL line to disk for
crash-recovery.
"""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import asdict
from pathlib import Path
from typing import TextIO

from runner.benchmark.models import BenchmarkInvocationRecord

logger = logging.getLogger(__name__)


def _record_to_dict(record: BenchmarkInvocationRecord) -> dict:
    """Convert a frozen dataclass record to a JSON-serializable dict."""
    return asdict(record)


class BenchmarkLedger:
    """Append-only invocation ledger with JSONL persistence."""

    def __init__(self, ledger_path: Path | None = None) -> None:
        self._records: list[BenchmarkInvocationRecord] = []
        self._lock = threading.Lock()
        self._file: TextIO | None = None
        self._ledger_path = ledger_path

        if ledger_path is not None:
            try:
                ledger_path.parent.mkdir(parents=True, exist_ok=True)
                self._file = open(ledger_path, "a", encoding="utf-8")
            except Exception:
                logger.debug(
                    "Benchmark ledger file open failed: %s (non-blocking)",
                    ledger_path,
                    exc_info=True,
                )
                self._file = None

    @property
    def records(self) -> list[BenchmarkInvocationRecord]:
        """Return the in-memory list of accumulated records."""
        return list(self._records)

    def append(self, record: BenchmarkInvocationRecord) -> None:
        """Append a record to the ledger. Never raises."""
        try:
            with self._lock:
                self._records.append(record)
                if self._file is not None:
                    line = json.dumps(_record_to_dict(record), separators=(",", ":"))
                    self._file.write(line + "\n")
                    self._file.flush()
        except Exception:
            logger.debug(
                "Benchmark record append failed for invocation %s (non-blocking)",
                getattr(record, "invocation_id", "unknown"),
                exc_info=True,
            )

    def close(self) -> None:
        """Close the ledger file handle. Never raises."""
        try:
            if self._file is not None:
                self._file.close()
                self._file = None
        except Exception:
            logger.debug(
                "Benchmark ledger close failed (non-blocking)",
                exc_info=True,
            )
