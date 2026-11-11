"""
The harness's one content-hash module: one canonical rule, two named formats.

Every harness hash is computed here. Records hold two formats, and each has a
name:

- a **content hash** is the hash of a parsed value: canonical JSON (sorted keys,
  compact separators, UTF-8, non-ASCII kept), stored with the ``sha256:`` prefix.
  Candidate hash, profile version, rubric fingerprint and pack-set hash are
  content hashes. It is formatting-invariant: two files holding the same JSON
  value hash alike whatever their whitespace or key order.
- a **file hash** is the hash of raw bytes, stored as bare hex
  (``report_sha256``, ``comparison_sha256``, ...).

Names and display use one **short form** of either: 12 hex characters, the same
for a prefixed and a bare digest of the same bytes. :func:`next_numbered_path`
names files by it, so a bare-hex digest numbers as its prefixed form does.

Nothing here changes a stored format. Two callers keep a historical variant
through an explicit argument: the regression fingerprint stores its canonical
hash unprefixed (``prefixed=False``), and the rubric-set fingerprint escapes
non-ASCII (``ensure_ascii=True``). The gold-set and materiality-set hashes keep
their own field selection and use only :func:`digest`.

The runner has its own fingerprints (``runner/fingerprints.py``); the one-way
import rule means it never imports this module.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

__all__ = [
    "PREFIX",
    "SHORT_LEN",
    "digest",
    "content_hash",
    "file_hash",
    "short_hash",
    "next_numbered_path",
]

#: The prefix a content hash is stored with.
PREFIX: str = "sha256:"

#: Hex characters in the short form.
SHORT_LEN: int = 12


def digest(data: bytes, *, prefixed: bool = False) -> str:
    """The sha256 of *data*: bare hex, or with the ``sha256:`` prefix."""
    hexdigest = hashlib.sha256(data).hexdigest()
    return PREFIX + hexdigest if prefixed else hexdigest


def content_hash(value: Any, *, prefixed: bool = True, ensure_ascii: bool = False) -> str:
    """The content hash of a parsed *value*: its canonical JSON, ``sha256:``-prefixed.

    ``prefixed=False`` is the regression fingerprint's stored format;
    ``ensure_ascii=True`` is the rubric-set fingerprint's. No other caller
    passes either.
    """
    canonical = json.dumps(value, ensure_ascii=ensure_ascii, sort_keys=True, separators=(",", ":"))
    return digest(canonical.encode("utf-8"), prefixed=prefixed)


def file_hash(source: bytes | str | os.PathLike[str]) -> str:
    """The file hash of raw bytes, or of the bytes of the file at a path: bare hex.

    A ``str`` is a path. Hash text by encoding it first.
    """
    data = source if isinstance(source, bytes) else Path(source).read_bytes()
    return digest(data)


def short_hash(value: str, *, keep_prefix: bool = False) -> str:
    """The short form of a content hash or a file hash: its first 12 hex characters.

    A prefixed and a bare digest of the same bytes shorten alike. With
    ``keep_prefix=True`` a prefixed digest keeps its ``sha256:`` label for
    display; a bare one stays bare. An empty value shortens to ``""``.
    """
    labelled = value.startswith(PREFIX)
    hexdigest = value[len(PREFIX):] if labelled else value
    short = hexdigest[:SHORT_LEN]
    return PREFIX + short if keep_prefix and labelled else short


def _numbered_name_re(prefix: str, suffix: str) -> re.Pattern[str]:
    return re.compile(
        rf"^{re.escape(prefix)}_(?P<hash>[0-9a-f]{{{SHORT_LEN}}})_(?P<seq>\d{{4}}){re.escape(suffix)}$"
    )


def next_numbered_path(directory: Path | str, value: str, *, prefix: str, suffix: str) -> Path:
    """The next free ``<prefix>_<short>_<NNNN><suffix>`` under *directory* for *value*.

    *value* is a content hash or a file hash; both name the same file. Nothing
    is ever overwritten: the sequence number follows the highest one taken.
    """
    target = Path(directory)
    short = short_hash(value)
    pattern = _numbered_name_re(prefix, suffix)
    taken = 0
    if target.is_dir():
        for existing in target.iterdir():
            m = pattern.match(existing.name)
            if m and m.group("hash") == short:
                taken = max(taken, int(m.group("seq")))
    return target / f"{prefix}_{short}_{taken + 1:04d}{suffix}"
