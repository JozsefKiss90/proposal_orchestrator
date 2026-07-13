"""
Shared claim-status severity — the single source for §12.2 status ordering.

A Phase-8 section's ``validation_status.overall_status`` is the *worst* status
among its per-claim ``claim_statuses`` (CLAUDE.md §12.2): a section is only as
resolved as its least-resolved claim.  Two components derive that worst status
and must derive it identically, or the section could disagree with itself:

  * the **drafter** (:mod:`runner.decomposed_drafting`) stamps the spine's
    ``overall_status`` from the freshly-drafted per-sub-section claims, and
  * the **assumption-applier** (:mod:`runner.assumption_applier`, ticket 9)
    re-derives it after flipping declared ``unresolved → assumed`` claims, so
    the spine the assembler carries verbatim stays consistent with the flips.

This module owns the ordering and the derivation so both call one function.
It performs no I/O and no domain reasoning — a pure lookup/max over the §12.2
vocabulary — so it is safe for a Claude-free deterministic component to use.
"""

from __future__ import annotations

from typing import Iterable

#: §12.2 validation vocabulary ordered worst-last.  ``confirmed`` is the most
#: resolved (severity 0); ``unresolved`` is the honest block (severity 3).
STATUS_SEVERITY: dict[str, int] = {
    "confirmed": 0,
    "inferred": 1,
    "assumed": 2,
    "unresolved": 3,
}

#: Inverse of :data:`STATUS_SEVERITY` — severity rank back to the status string.
_SEVERITY_STATUS: dict[int, str] = {v: k for k, v in STATUS_SEVERITY.items()}


def worst_status(statuses: Iterable[str]) -> str:
    """Return the worst (least-resolved) status among *statuses*.

    Case-insensitive; unknown/blank statuses are ignored (they cannot make a
    section look *more* resolved or crash the derivation).  An empty iterable
    — a section with no claims — yields ``"confirmed"`` (nothing is unresolved).
    This is the worst-wins rule from CLAUDE.md §12.2.
    """
    worst = 0
    for status in statuses:
        severity = STATUS_SEVERITY.get(str(status).lower())
        if severity is not None and severity > worst:
            worst = severity
    return _SEVERITY_STATUS[worst]
