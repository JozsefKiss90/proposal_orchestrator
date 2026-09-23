"""
Shared append-only JSONL log — one JSON object per line, atomic rewrite (E1.5).

The harness keeps two out-of-band audit trails with the same shape: the
per-verdict :class:`~harness.provenance.ProvenanceLog` and the per-run
:class:`~harness.calibration.CalibrationLog` (and E2+ will add more).  Each is an
append-only JSONL file rewritten atomically on every append (Python owns the
write, §9/§17.5.3; a reader never sees a torn line).  This base consolidates that
machinery — ``__init__`` seeds from any pre-existing file, ``append_dict`` mirrors
in memory and atomically re-serializes — so each concrete log only supplies its
filename prefix and a typed ``append`` that serializes its record type.

Volume is low (verdicts/runs per QA pass), so the read-once/rewrite-per-append
cost is immaterial and buys torn-write safety plus trivial testability.  Nothing
in :mod:`runner` reads these files.

Constitutional authority:
    Subordinate to CLAUDE.md.  Out-of-band QA substrate.  See ``harness/HARNESS.md``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from runner.atomic_write import atomic_write_text

__all__ = ["JsonlLog"]


class JsonlLog:
    """An append-only JSONL sink written atomically on every append.

    Concrete logs subclass this and add a typed ``append`` that calls
    :meth:`append_dict` with ``record.to_dict()``.

    Parameters
    ----------
    path:
        Destination ``.jsonl`` file; parent directories are created on first append.
    prefix:
        Temp-file prefix passed to the atomic writer (identifies the writer).
    """

    def __init__(self, path: Path | str, *, prefix: str = "jsonl_") -> None:
        self._path = Path(path)
        self._prefix = prefix
        # Seed the in-memory mirror from any pre-existing log so appends are
        # order-preserving across process restarts without re-reading per call.
        self._records: list[dict[str, Any]] = self._load_existing()

    @property
    def path(self) -> Path:
        return self._path

    def _load_existing(self) -> list[dict[str, Any]]:
        if not self._path.is_file():
            return []
        out: list[dict[str, Any]] = []
        for line in self._path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                out.append(json.loads(line))
        return out

    def append_dict(self, record: dict[str, Any]) -> None:
        """Append one record dict and atomically rewrite the log."""
        self._records.append(record)
        body = "".join(
            json.dumps(rec, ensure_ascii=False) + "\n" for rec in self._records
        )
        atomic_write_text(body, self._path, prefix=self._prefix)

    def records(self) -> list[dict[str, Any]]:
        """Return a copy of every logged record, in append order."""
        return list(self._records)

    def __len__(self) -> int:
        return len(self._records)
