"""
Deterministic-first routing — the judge runs only in the semantic gap (E1).

The load-bearing rule of the whole harness (strategy §0/§2, guardrails):

    For any property a deterministic predicate *can* check, the predicate is
    authoritative; the judge runs only where no deterministic check exists, and
    a green judge never overrides a red predicate.

Re-implementing a deterministic check as an LLM judge would trade a proof for a
probabilistic opinion — a regression.  This module is the mechanism that
prevents it.  A *property* is named by a key; if that key is the name of a
deterministic predicate the runtime actually dispatches
(``runner.gate_evaluator.PREDICATE_REGISTRY``), routing refuses to judge it.
Otherwise the property sits in the semantic gap and a judge may run.

Deliberately, the *semantic* in-run gates (``semantic_dispatch.SEMANTIC_REGISTRY``
— e.g. ``no_unsupported_tier5_claims``) are **not** treated as deterministic
coverage.  They are themselves same-model-family LLM judgments inside the system
under test, which the strategy says must not be trusted alone; the out-of-band
judge legitimately *re-checks* them with an independent model.  Only the
deterministic predicate set preempts the judge.

The semantic property a metric judges must therefore carry a name *distinct*
from the deterministic predicate whose gap it fills — e.g. the deterministic
``source_refs_present`` (a field is non-blank) leaves open the semantic
``source_entails_claim`` (the cited source actually supports the sentence).
Routing enforces that you cannot register the former as judgeable.

Constitutional authority:
    Subordinate to CLAUDE.md.  Out-of-band QA substrate.  This module reads the
    runtime predicate registry but never evaluates a gate, and nothing here can
    make a run pass or fail.  See ``harness/HARNESS.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

__all__ = [
    "DeterministicCoverageError",
    "RoutingAuthority",
    "RoutingDecision",
    "deterministic_predicate_names",
    "semantic_inrun_predicate_names",
    "route",
    "assert_judgeable",
]


class DeterministicCoverageError(Exception):
    """Raised when a caller tries to judge a deterministically-covered property.

    Carries the offending ``property_key`` and the ``covering_predicate`` so the
    caller can rename the property to the *semantic* question the predicate
    leaves open, rather than duplicating the predicate as a judge.
    """

    def __init__(self, property_key: str, covering_predicate: str) -> None:
        self.property_key = property_key
        self.covering_predicate = covering_predicate
        super().__init__(
            f"Property {property_key!r} is already covered by the deterministic "
            f"predicate {covering_predicate!r}; it must not be judged (a green "
            f"judge never overrides a red predicate). Judge the *semantic gap* "
            f"the predicate leaves open under a distinct property key instead."
        )


#: Authority strings for a :class:`RoutingDecision`.
class RoutingAuthority:
    DETERMINISTIC_PREDICATE = "deterministic_predicate"
    SEMANTIC_GAP = "semantic_gap"


@dataclass(frozen=True)
class RoutingDecision:
    """The routing outcome for a single property key.

    Attributes
    ----------
    property_key:
        The property considered.
    deterministically_covered:
        ``True`` iff a deterministic predicate owns this property.
    judge_permitted:
        Exactly ``not deterministically_covered`` — the judge may run only in
        the semantic gap.
    authority:
        :data:`RoutingAuthority.DETERMINISTIC_PREDICATE` when covered, else
        :data:`RoutingAuthority.SEMANTIC_GAP`.
    covering_predicate:
        The predicate name that owns the property, or ``None`` in the gap.
    """

    property_key: str
    deterministically_covered: bool
    judge_permitted: bool
    authority: str
    covering_predicate: str | None

    def to_dict(self) -> dict:
        return {
            "property_key": self.property_key,
            "deterministically_covered": self.deterministically_covered,
            "judge_permitted": self.judge_permitted,
            "authority": self.authority,
            "covering_predicate": self.covering_predicate,
        }


def deterministic_predicate_names() -> frozenset[str]:
    """Return the authoritative set of deterministic predicate function names.

    Sourced live from ``runner.gate_evaluator.PREDICATE_REGISTRY`` — the exact
    set of pure JSON/string checks the scheduler dispatches as hard gates — so
    the harness's notion of "already provable" never drifts from the runtime's.
    Imported lazily to keep this module cheap to import and free of any
    scheduler-adjacent import coupling.
    """
    from runner.gate_evaluator import PREDICATE_REGISTRY

    return frozenset(PREDICATE_REGISTRY.keys())


def semantic_inrun_predicate_names() -> frozenset[str]:
    """Return the in-run *semantic* predicate names (informational only).

    These are the same-model-family LLM gates
    (``semantic_dispatch.SEMANTIC_REGISTRY``).  They are **not** deterministic
    coverage and do **not** preempt the out-of-band judge; exposed so callers
    can see, and document, which properties the harness deliberately re-checks
    with an independent model.
    """
    from runner.semantic_dispatch import SEMANTIC_REGISTRY

    return frozenset(SEMANTIC_REGISTRY.keys())


def route(
    property_key: str,
    *,
    extra_covered: Iterable[str] | None = None,
) -> RoutingDecision:
    """Decide whether *property_key* may be judged.

    Parameters
    ----------
    property_key:
        The property a metric wants to judge.
    extra_covered:
        Additional property keys the caller declares as deterministically
        covered (e.g. a byte-equal CI check that is not a registry predicate).
        Treated with the same authority as a registry predicate.

    Returns
    -------
    RoutingDecision
        ``judge_permitted`` is ``False`` when the property is covered.
    """
    covered = deterministic_predicate_names()
    extra = frozenset(extra_covered or ())
    if property_key in covered or property_key in extra:
        return RoutingDecision(
            property_key=property_key,
            deterministically_covered=True,
            judge_permitted=False,
            authority=RoutingAuthority.DETERMINISTIC_PREDICATE,
            covering_predicate=property_key,
        )
    return RoutingDecision(
        property_key=property_key,
        deterministically_covered=False,
        judge_permitted=True,
        authority=RoutingAuthority.SEMANTIC_GAP,
        covering_predicate=None,
    )


def assert_judgeable(
    property_key: str,
    *,
    extra_covered: Iterable[str] | None = None,
) -> RoutingDecision:
    """Return the routing decision, raising if the property must not be judged.

    The enforcement entry point for metric authors: call it before invoking the
    judge, and a deterministically-covered property fails loudly
    (:class:`DeterministicCoverageError`) rather than being silently double-checked.
    """
    decision = route(property_key, extra_covered=extra_covered)
    if not decision.judge_permitted:
        raise DeterministicCoverageError(
            property_key, decision.covering_predicate or property_key
        )
    return decision
