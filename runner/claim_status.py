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

from typing import Any, Iterable

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


def normalize_status(status: Any) -> str | None:
    """Return *status* as its canonical (lowercase) §12.2 form, or ``None``.

    CLAUDE.md §12.2 names the vocabulary in title case (``Confirmed`` /
    ``Inferred`` / ``Assumed`` / ``Unresolved``); the runtime's canonical form
    is lowercase.  Artifacts — especially operator-authored preseed sections and
    reused carry-forwards, neither of which passes through the drafter that would
    lowercase the value — may carry either casing.  This maps any casing of a
    known status to its canonical lowercase spelling and returns ``None`` for a
    value outside the vocabulary.

    Callers comparing a section's status against a canonical value must route
    through this function so a title-case ``Unresolved`` matches ``unresolved``
    (the PRE-1 fail-closed bypass), while an unknown value never spuriously
    matches a canonical status.  This is the single case-normalisation point for
    the §12.2 vocabulary, mirroring how :func:`worst_status` /
    :func:`rollup_inconsistency` own the ordering.
    """
    normalized = str(status).lower()
    return normalized if normalized in STATUS_SEVERITY else None


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


def rollup_inconsistency(data: dict[str, Any], *, prefix: str) -> str | None:
    """Return a failure reason iff *data*'s roll-up over-states its claims.

    Both **supersession** paths for a Phase-8 section — manual preseed
    (:mod:`runner.phase8_preseed`) and reuse (:mod:`runner.phase8_reuse`) —
    admit a finished section artifact without running the derivation pipeline
    that would have produced its ``validation_status.overall_status`` (the
    drafter, then the assumption-applier, §12.2 worst-wins).  Neither can rely
    on the gates to catch a bad roll-up: ``no_unresolved_material_claims`` reads
    only the roll-up and W1 (``assumed_claims_are_operator_declared``) inspects
    only ``assumed`` claims, so an ``unresolved`` claim under a ``confirmed``
    roll-up is invisible to both — a fail-closed honest block silently becomes a
    green.  The check lives here, once, so the two paths cannot drift.

    The rule is one-sided by design: the roll-up may be **more** conservative
    than its claims (declaring a section ``assumed`` over ``confirmed`` claims
    is honest under-claiming, §15), but it may never be more resolved than its
    least-resolved claim.

    *prefix* namespaces the returned reason to the calling path (``"preseed"`` /
    ``"reuse"``).  Returns ``None`` when the artifact is consistent — including
    when it carries no claims.
    """
    validation_status = data.get("validation_status")
    if not isinstance(validation_status, dict):
        return (
            f"{prefix}_validation_status_not_object: 'validation_status' must "
            f"be an object, got {type(validation_status).__name__}"
        )

    overall = validation_status.get("overall_status")
    if not isinstance(overall, str) or overall.lower() not in STATUS_SEVERITY:
        return (
            f"{prefix}_overall_status_invalid: 'validation_status."
            f"overall_status' must be one of {sorted(STATUS_SEVERITY)}, got "
            f"{overall!r}"
        )

    claim_statuses = validation_status.get("claim_statuses", [])
    if not isinstance(claim_statuses, list):
        return (
            f"{prefix}_claim_statuses_not_array: 'validation_status."
            "claim_statuses' must be an array, got "
            f"{type(claim_statuses).__name__}"
        )

    worst = worst_status(
        claim.get("status", "")
        for claim in claim_statuses
        if isinstance(claim, dict)
    )
    if STATUS_SEVERITY[overall.lower()] < STATUS_SEVERITY[worst]:
        return (
            f"{prefix}_overall_status_overstated: 'validation_status."
            f"overall_status' is {overall!r} but the worst claim status is "
            f"{worst!r} (CLAUDE.md §12.2 worst-wins); the roll-up may be more "
            "conservative than its claims, never more resolved"
        )
    return None
