"""
Dev-graph identity — canonical JSON, record versions and the snapshot id.

A version is the content hash of a record's canonical form. The snapshot id is
the content hash of the canonical form of the sorted nodes and edges, hashed
recursively through every nested value. Neither reads a clock, a path, or a
file-system stamp, so two builds from the same content agree byte for byte.

The existing directory fingerprint helper (``runner/fingerprints.py``) hashes
direct child names only; it is not reused here on purpose.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

HASH_PREFIX = "sha256:"


def canonical_json(obj: Any) -> bytes:
    """Canonical serialisation: sorted keys, no whitespace, ASCII-escaped."""
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


def content_hash(obj: Any) -> str:
    """``sha256:<hex>`` over :func:`canonical_json` of *obj* (recursive)."""
    return HASH_PREFIX + hashlib.sha256(canonical_json(obj)).hexdigest()


def snapshot_id(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> str:
    """Content-derived snapshot identity over the sorted nodes and edges."""
    return content_hash({"nodes": nodes, "edges": edges})
