"""
Shared atomic-write helpers (temp file + rename), house style (§9, §17.5.3).

Python owns every canonical artifact write, and each write is **atomic**: the
bytes are written to a temporary file on the same filesystem, then renamed over
the target (so a reader never observes a half-written artifact), with
cleanup-on-failure so a fault leaves neither a partial target nor a stray temp
file.  On Windows ``os.rename`` requires the target to be absent, so an existing
target is unlinked first.

This module consolidates the writer that was previously copy-pasted across the
deterministic components (section assembler, unit-cost budget deriver,
decomposed drafting) and the ``.docx`` exporter.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Callable

__all__ = [
    "atomic_write_json",
    "atomic_write_text",
    "atomic_write_via",
    "canonical_json_bytes",
]


def canonical_json_bytes(obj: Any) -> bytes:
    """*obj* as the canonical pretty UTF-8 JSON this module writes.

    ``indent=2, ensure_ascii=False`` — the serialisation every byte-equal
    replay check depends on. Exposed so a caller that compares bytes against
    an artifact on disk compares against the same function that wrote it,
    rather than a second copy of the options that could drift from this one.
    """
    return json.dumps(obj, indent=2, ensure_ascii=False).encode("utf-8")


def _finalize(tmp_path: str, output_path: Path) -> None:
    """Rename *tmp_path* over *output_path* (Windows-safe)."""
    if output_path.exists():
        output_path.unlink()
    os.rename(tmp_path, str(output_path))


def atomic_write_json(
    obj: Any,
    output_path: Path,
    *,
    prefix: str = "atomic_",
) -> None:
    """Write *obj* as pretty UTF-8 JSON to *output_path*, atomically.

    Uses ``indent=2, ensure_ascii=False`` — the canonical serialisation the
    byte-equal replay checks depend on.  Creates parent directories as needed.
    Raises on any failure, leaving no partial output.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    data = canonical_json_bytes(obj)

    fd, tmp_path = tempfile.mkstemp(
        dir=str(output_path.parent), suffix=".tmp", prefix=prefix
    )
    try:
        os.write(fd, data)
        os.close(fd)
        fd = -1
        _finalize(tmp_path, output_path)
    except Exception:
        if fd >= 0:
            os.close(fd)
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def atomic_write_text(
    text: str,
    output_path: Path,
    *,
    prefix: str = "atomic_",
) -> None:
    """Write *text* as UTF-8 to *output_path*, atomically.

    The text sibling of :func:`atomic_write_json`, for producers that emit
    markdown or other text artifacts (e.g. the docs→graph projector's mirror
    nodes).  Newlines are written verbatim (``\\n`` is not translated), so output
    is byte-identical across platforms.  Creates parent directories as needed.
    Raises on any failure, leaving no partial output.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    data = text.encode("utf-8")

    fd, tmp_path = tempfile.mkstemp(
        dir=str(output_path.parent), suffix=".tmp", prefix=prefix
    )
    try:
        os.write(fd, data)
        os.close(fd)
        fd = -1
        _finalize(tmp_path, output_path)
    except Exception:
        if fd >= 0:
            os.close(fd)
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def atomic_write_via(
    output_path: Path,
    save: Callable[[str], None],
    *,
    prefix: str = "atomic_",
) -> None:
    """Atomically produce a (binary) file whose bytes a *save* callback writes.

    For producers that write their own bytes to a path — e.g. python-docx's
    ``Document.save(path)`` — rather than returning them.  *save* is called with
    a temp path; on success the temp file is renamed over *output_path*, on
    failure it is removed.  Creates parent directories as needed.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        dir=str(output_path.parent), suffix=".tmp", prefix=prefix
    )
    os.close(fd)  # the callback owns writing the bytes; we only need the path
    try:
        save(tmp_path)
        _finalize(tmp_path, output_path)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
