"""
The DN record chain: one way to load a record against its predecessors.

The DN pre-evaluation records form a chain::

    evidence preflight -> blind report -> blind baseline -> integrity audit
        -> ESR comparison (+ revisions) -> operator review / comparison diff

Each record names its predecessors by file hash. A **record kind** declares,
once, what this module needs to load one: its record type, the predecessor
references it carries, and the error class a refusal raises. Two operations:

* :func:`load_record` reads a record of a kind, checks its type and its
  advisory/blocking flags, runs the kind's own shape check, and re-hashes every
  predecessor the record names. A predecessor whose bytes moved is refused,
  naming the record, the predecessor and both hashes.
* :func:`write_record` writes a record of a kind to the next numbered path,
  atomically, and returns the path and its file hash.

The chain is shared; the readers are not. Each record keeps its own vocabulary,
field readers and shape rules in its own module (``harness/record_binding.py``
explains why). The error class is declared on the kind, so no call site threads
it through.

Predecessor references are read from fields records already carry
(``report_sha256``, ``esr_record/sha256``, ``comparison_sha256`` ...). No
record format changes. Path resolution follows the rule each record was
written under:

* an absolute path is read as written;
* a relative path is read under the repository root: the one the caller
  passes, or else the nearest ancestor of the record that holds the path, or
  else the repository this module belongs to.

The revisions artifact beside a comparison, recorded as an absolute path from
the run that wrote it and with no hash, stays with ``comparison_diff``'s own
rule: it is found by name beside the comparison.

Hashing and short forms come from :mod:`harness.content_hash`.

Constitutional authority:
    Subordinate to CLAUDE.md. Out-of-band QA; never a runtime gate. Reads the
    bound records read-only; writes only the record it is given. See
    ``harness/HARNESS.md``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from runner.atomic_write import atomic_write_json

from harness.content_hash import file_hash, next_numbered_path, short_hash
from harness.record_pointer import UNRESOLVED, resolve_field

__all__ = [
    "Predecessor",
    "RecordKind",
    "LoadedRecord",
    "WrittenRecord",
    "load_record",
    "write_record",
]

#: The repository this module belongs to: the last place a relative path is looked for.
_HOME = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Predecessor:
    """One predecessor a record names, read from the record's own fields.

    *path* is a field pointer (``/``-separated, :mod:`harness.record_pointer`),
    or a tuple of pointers whose values join into one path (a directory and a
    file name). *sha256* points at the recorded file hash. A record that names
    neither has no such predecessor; a record that names one without the other
    is refused. With *each*, a pointer to a list, *path* and *sha256* point
    into every entry of that list (the audits a comparison names).
    """

    #: How a refusal names it, e.g. ``"the ESR record"``.
    name: str
    path: str | tuple[str, ...]
    sha256: str
    each: str | None = None


@dataclass(frozen=True)
class RecordKind:
    """A record kind, declared once."""

    #: How a refusal names a record of this kind, e.g. ``"comparison"``.
    name: str
    record_type: str
    #: Raised on every refusal.
    error: type[Exception]
    #: The file-name prefix :func:`write_record` numbers under.
    prefix: str = ""
    predecessors: tuple[Predecessor, ...] = ()
    #: The record's own shape rules, run after the type and flags and before
    #: any predecessor is read: ``check_shape(path, data)`` raises or returns.
    check_shape: Callable[[Path, Mapping[str, Any]], None] | None = None


@dataclass(frozen=True)
class LoadedRecord:
    """A record read and verified against its predecessors on disk."""

    path: Path
    #: The record's own file hash.
    sha256: str
    data: dict[str, Any]


@dataclass(frozen=True)
class WrittenRecord:
    path: Path
    sha256: str


def _article(word: str) -> str:
    return "an" if word[:1].lower() in "aeiou" else "a"


def _check_type_and_flags(kind: RecordKind, path: Path | str, data: Any) -> None:
    if not isinstance(data, Mapping) or data.get("record_type") != kind.record_type:
        raise kind.error(f"{path} is not {_article(kind.record_type)} {kind.record_type!r} record.")
    if data.get("advisory") is not True or data.get("blocking") is not False:
        raise kind.error(f"{kind.name} {path} must carry advisory=true and blocking=false.")


def _field(data: Mapping[str, Any], pointer: str) -> str | None:
    value = resolve_field(data, pointer)
    if value is UNRESOLVED or value is None or value == "":
        return None
    return str(value)


def _raw_path(data: Mapping[str, Any], pointers: str | tuple[str, ...]) -> str | None:
    parts = [_field(data, p) for p in ((pointers,) if isinstance(pointers, str) else pointers)]
    if all(part is None for part in parts):
        return None
    if any(part is None for part in parts):
        return ""
    return Path(*parts).as_posix()


def _locate(raw: str, record: Path, repo_root: Path | None) -> Path:
    p = Path(raw)
    if p.is_absolute():
        return p
    if repo_root is not None:
        return Path(repo_root) / p
    for root in (*record.resolve().parents, _HOME):
        if (root / p).exists():
            return root / p
    return _HOME / p


def _verify(
    kind: RecordKind, path: Path, data: Mapping[str, Any], repo_root: Path | None
) -> None:
    for pred in kind.predecessors:
        if pred.each is None:
            _verify_one(kind, path, pred, data, repo_root)
            continue
        entries = resolve_field(data, pred.each)
        for entry in entries if isinstance(entries, list) else ():
            if not isinstance(entry, Mapping):
                raise kind.error(f"{kind.name} {path} names {pred.name} that is not an object.")
            _verify_one(kind, path, pred, entry, repo_root)


def _verify_one(
    kind: RecordKind,
    path: Path,
    pred: Predecessor,
    data: Mapping[str, Any],
    repo_root: Path | None,
) -> None:
    raw = _raw_path(data, pred.path)
    recorded = _field(data, pred.sha256)
    if raw is None and recorded is None:
        return
    if not raw or recorded is None:
        raise kind.error(
            f"{kind.name} {path} names {pred.name} without both its path and its hash."
        )
    located = _locate(raw, path, repo_root)
    if not located.is_file():
        raise kind.error(
            f"{kind.name} {path} names {pred.name} at {located}, which is not a file."
        )
    actual = file_hash(located)
    if actual != recorded:
        raise kind.error(
            f"{kind.name} {path} names {pred.name} at {located}, which hashes to "
            f"{short_hash(actual)}; the {kind.name} recorded {short_hash(recorded)}. "
            f"Refused: {pred.name} moved after the {kind.name} was written."
        )


def load_record(
    kind: RecordKind, path: Path | str, *, repo_root: Path | str | None = None
) -> LoadedRecord:
    """Load a record of *kind*, verified against its predecessors on disk.

    Refused with ``kind.error`` when the file is absent or not JSON, when its
    type or advisory/blocking flags are wrong, when its shape check fails, and
    when a predecessor it names is missing or its bytes moved.
    """
    p = Path(path)
    if not p.is_file():
        raise kind.error(f"{kind.name} not found: {p}")
    raw = p.read_bytes()
    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise kind.error(f"{kind.name} {p} is not valid JSON: {exc}") from exc
    _check_type_and_flags(kind, p, data)
    if kind.check_shape is not None:
        kind.check_shape(p, data)
    _verify(kind, p, data, None if repo_root is None else Path(repo_root))
    return LoadedRecord(path=p, sha256=file_hash(raw), data=dict(data))


def write_record(
    kind: RecordKind,
    data: Mapping[str, Any],
    out_dir: Path | str,
    *,
    digest: str,
    complete: Callable[[Path], Mapping[str, Any]] | None = None,
) -> WrittenRecord:
    """Write a record of *kind* to the next numbered path under *out_dir*.

    The path is ``<prefix>_<short form of digest>_<NNNN>.json``; nothing is
    overwritten. *complete*, when given, receives that path before anything is
    written and returns the record to write, so a record can name itself and
    write companions that share its sequence number. The record is checked for
    the kind's type and flags first; a record of another kind is not written.
    """
    _check_type_and_flags(kind, "(unwritten)", data)
    target = next_numbered_path(out_dir, digest, prefix=kind.prefix, suffix=".json")
    record = data if complete is None else complete(target)
    _check_type_and_flags(kind, target, record)
    atomic_write_json(dict(record), target, prefix=f"{kind.prefix}_")
    return WrittenRecord(path=target, sha256=file_hash(target))
