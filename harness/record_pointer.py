"""Resolving a field pointer into a parsed JSON record.

One grammar, shared by the records that cite each other by pointer: a
``/``-separated key path into objects, with ``#N`` for a position in a list.
That is all of it. Nothing resolves by identity — a keyed list is indexed by
position here, deliberately, so that a reader who has met the
identity-resolving dialect of :func:`harness.esr_comparison.resolve_pointer`
does not carry that rule across.

:data:`UNRESOLVED` is a sentinel distinct from a resolved ``None``, because a
record that holds ``null`` at a pointer and a record that holds nothing there
are different facts, and a checker has to report them differently.

Constitutional authority:
    Subordinate to CLAUDE.md. Out-of-band QA; reads nothing from disk and
    writes nothing. See ``harness/HARNESS.md``.
"""

from __future__ import annotations

from typing import Any, Mapping

__all__ = ["UNRESOLVED", "resolve_field"]


class _Unresolved:
    """The field did not resolve. Distinct from a resolved ``None``."""

    def __repr__(self) -> str:  # pragma: no cover - diagnostic only
        return "UNRESOLVED"


UNRESOLVED = _Unresolved()


def resolve_field(data: Any, field: str) -> Any:
    """Resolve *field* into *data*, or :data:`UNRESOLVED`.

    A segment indexes an object by key. ``#N`` indexes a list by position.
    """
    node: Any = data
    for seg in [s for s in field.split("/") if s != ""]:
        if isinstance(node, Mapping):
            if seg not in node:
                return UNRESOLVED
            node = node[seg]
        elif isinstance(node, list) and seg.startswith("#"):
            index = seg[1:]
            if not index.lstrip("-").isdigit():
                return UNRESOLVED
            try:
                node = node[int(index)]
            except IndexError:
                return UNRESOLVED
        else:
            return UNRESOLVED
    return node
