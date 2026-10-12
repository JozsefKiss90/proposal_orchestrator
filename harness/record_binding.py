"""Binding a successor record to the records it reads, by the sha256 of their bytes.

A successor artifact — an open-deferral register, a rule-equivalence matrix —
points at the records it was derived from and pins each by hash. Two roles
separate two different defects when a pinned record's bytes move:

* ``immutable_evidence`` is a historical record. Its bytes moving is an **edit**,
  and an edit to a historical record is reported as one.
* ``tracked_input`` is a record allowed to move, such as a ticket ledger or a
  configuration file. Its bytes moving means the successor is **stale** and has
  to be re-derived.

Both fail a check. They are separate findings because an edited historical
record and a stale successor are different defects with different fixes, and
reporting the second for the first sends a reader to the wrong place.

This module holds what every such record needs and none of what any one of them
means: the two roles, the review-state and evidence-status vocabularies, the
hash, the binding check, and the two text helpers a rendered reading uses. The
record's own vocabulary — what kinds of row it has, what its verdicts mean —
stays in its own module.

What is deliberately *not* here are the fail-closed field readers. Each record
raises its own exception type on a malformed declaration, and its tests assert
that type; sharing the readers would mean either threading an exception class
through every call site or collapsing two documented contracts into one. The
dozen lines they duplicate cost less than either.

Constitutional authority:
    Subordinate to CLAUDE.md. Out-of-band QA; reads the bound records read-only
    and writes nothing. Never a runtime gate. See ``harness/HARNESS.md``.
"""

from __future__ import annotations

import hashlib
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Protocol, runtime_checkable

__all__ = [
    "SOURCE_ROLES",
    "REVIEW_STATES",
    "STATUSES",
    "Unreadable",
    "Bound",
    "BindingCheck",
    "file_sha256",
    "check_bindings",
    "one_line",
    "wrap",
]

#: How a bound record is treated when its bytes move.
SOURCE_ROLES: tuple[str, ...] = ("immutable_evidence", "tracked_input")

#: Who has reviewed a successor record. One vocabulary, so a reader does not
#: meet a second spelling of the same fact in a sibling artifact.
REVIEW_STATES: tuple[str, ...] = ("agent_drafted_pending_operator_review", "operator_reviewed")

#: The four evidence statuses CLAUDE.md section 12.2 defines.
STATUSES: tuple[str, ...] = ("Confirmed", "Inferred", "Assumed", "Unresolved")


@dataclass(frozen=True)
class Unreadable:
    """A bound record that could not be parsed, and why.

    Kept distinct from a field that did not resolve. A record that cannot be
    read at all is a different defect from one whose shape moved.
    """

    why: str


@runtime_checkable
class Bound(Protocol):
    """What :func:`check_bindings` needs of a source entry."""

    #: Repository-relative, POSIX separators.
    path: str
    #: sha256 of the bytes, hex, no prefix.
    sha256: str
    #: One of :data:`SOURCE_ROLES`.
    role: str


@dataclass(frozen=True)
class BindingCheck:
    """Bound records read against the tree."""

    missing: tuple[str, ...] = ()
    edited_immutable: tuple[str, ...] = ()
    stale_tracked: tuple[str, ...] = ()

    @property
    def green(self) -> bool:
        return not (self.missing or self.edited_immutable or self.stale_tracked)


def file_sha256(path: Path) -> str:
    """The sha256 of *path*'s bytes, hex, no prefix."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_bindings(sources: Iterable[Bound], repo_root: Path) -> BindingCheck:
    """Read each of *sources* against the tree, splitting the two defects.

    A source whose bytes cannot be compared because the file is absent is
    reported once, as missing, and not a second time as moved.
    """
    missing: list[str] = []
    edited: list[str] = []
    stale: list[str] = []
    for source in sources:
        path = repo_root / source.path
        if not path.is_file():
            missing.append(source.path)
            continue
        if file_sha256(path) != source.sha256:
            if source.role == "immutable_evidence":
                edited.append(source.path)
            else:
                stale.append(source.path)
    return BindingCheck(
        missing=tuple(missing),
        edited_immutable=tuple(edited),
        stale_tracked=tuple(stale),
    )


def one_line(text: str) -> str:
    """*text* with its newlines collapsed, for a table cell."""
    return " ".join(str(text).split())


def wrap(text: str) -> str:
    """*text* hard-wrapped, the width the repository's rendered readings use."""
    return "\n".join(textwrap.wrap(one_line(text), width=98))
