"""
Judge verdict vocabulary — typed ``Inferred``, never ``Confirmed`` (E1).

A harness verdict is the out-of-band judge's opinion about a semantic property
no deterministic predicate can reach (does the source *entail* the sentence, is
a ``confirmed`` claim genuinely grounded, did an assertion escape the ledger).
Because an LLM-as-judge is stochastic and can be confidently wrong (strategy
§2/§10), its output is **evidence, not proof**.  The harness therefore stamps
every verdict with the CLAUDE.md §12.2 status ``Inferred`` — *"derived by
logical reasoning from confirmed evidence"* — and it is impossible to construct
a verdict typed ``Confirmed``.  This mirrors the pipeline's own discipline: a
score raised by a judge may *advise* a human decision about the pipeline, but it
never certifies a fact and never fail-closes a run.

This module is pure: no I/O, no network, no domain reasoning — just the verdict
types and the N≥3 majority-vote scaffold the guardrails require *"where a score
will inform a decision."*  The judge (:mod:`harness.judge`) produces
:class:`Verdict` objects; the provenance log (:mod:`harness.provenance`) records
them; the report (:mod:`harness.report`) aggregates them.  None of that lives
here.

Constitutional authority:
    Subordinate to CLAUDE.md.  Out-of-band QA substrate.  This module does not
    evaluate gates, invoke agents, write canonical artifacts, or modify
    scheduler state.  See ``harness/HARNESS.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

__all__ = [
    "EVIDENCE_TYPE_INFERRED",
    "MIN_MAJORITY_SAMPLES",
    "Verdict",
    "MajorityVerdict",
    "majority_vote",
    "validate_sample_count",
]

#: The only admissible evidence type for a judge verdict (CLAUDE.md §12.2).
#: A judge verdict is ``Inferred`` — derived by reasoning — never ``Confirmed``
#: (directly evidenced by a named Tier 1–3 source).  Enforced in
#: :meth:`Verdict.__post_init__` and :meth:`MajorityVerdict.__post_init__`.
EVIDENCE_TYPE_INFERRED: str = "Inferred"

#: Minimum samples for a majority vote.  The guardrails require N≥3 majority
#: "where a score will inform a decision"; a smaller panel cannot break a tie
#: nor absorb residual judge non-determinism, so :func:`majority_vote` rejects
#: fewer than this many samples.
MIN_MAJORITY_SAMPLES: int = 3


def validate_sample_count(n: int) -> None:
    """Reject any panel size other than 1 (single verdict) or ≥3 (majority).

    The shared entry-point guard every metric applies to its ``n`` parameter
    (E2's status faithfulness, E3's materiality/ledger/status-calibration):
    a single sample is the cheap default, an N≥3 panel is the guardrails'
    rule where a score will inform a decision, and n=2 is rejected because it
    can neither break a tie nor absorb residual non-determinism.
    """
    if n != 1 and n < MIN_MAJORITY_SAMPLES:
        raise ValueError(
            f"n must be 1 (single verdict) or ≥{MIN_MAJORITY_SAMPLES} (majority, "
            f"the guardrails' N≥3 rule where a score informs a decision); got {n}. "
            f"n=2 cannot break a tie."
        )


def _validate_inferred(evidence_type: str, what: str) -> None:
    """Reject any evidence type other than ``Inferred``.

    The single choke point behind the "judge output is Inferred, never
    Confirmed" guarantee.  A ``Confirmed`` (or ``Assumed`` / ``Unresolved``)
    judge verdict would misrepresent a probabilistic opinion as a proof — the
    exact confusion the harness exists to avoid — so construction fails loudly.
    """
    if evidence_type != EVIDENCE_TYPE_INFERRED:
        raise ValueError(
            f"{what} evidence_type must be {EVIDENCE_TYPE_INFERRED!r} "
            f"(a judge verdict is Inferred, never Confirmed); "
            f"got {evidence_type!r}."
        )


@dataclass(frozen=True)
class Verdict:
    """A single judge opinion about one semantic property.

    Attributes
    ----------
    metric:
        The harness metric that produced this verdict (e.g.
        ``"status_aware_faithfulness"``).  Free-form; E2–E9 own the vocabulary.
    property_key:
        The specific property judged — an identifier that is *not* the name of a
        deterministic predicate (see :mod:`harness.routing`).  For a per-claim
        metric this is typically the ``claim_id``.
    passed:
        The judge's boolean call, when the metric is boolean (e.g. "is this
        ``confirmed`` claim supported by its source?").  ``None`` for a
        score-only metric.
    score:
        A numeric score in ``[0.0, 1.0]`` when the metric emits one; ``None``
        otherwise.  ``passed`` and ``score`` may both be present (a threshold
        applied to a score) or either alone.
    rationale:
        The judge's stated reason.  May be empty, but callers are encouraged to
        require a non-empty rationale for auditability.
    evidence_type:
        Always :data:`EVIDENCE_TYPE_INFERRED`; any other value is rejected at
        construction.  Present as a field (rather than hard-coded) so the
        guarantee is explicit in every serialized record.
    sample_index:
        Position of this verdict within a majority panel, when applicable;
        ``None`` for a standalone verdict.
    """

    metric: str
    property_key: str
    passed: bool | None = None
    score: float | None = None
    rationale: str = ""
    evidence_type: str = EVIDENCE_TYPE_INFERRED
    sample_index: int | None = None

    def __post_init__(self) -> None:
        _validate_inferred(self.evidence_type, "Verdict")
        if self.score is not None and not (0.0 <= float(self.score) <= 1.0):
            raise ValueError(
                f"Verdict score must lie in [0.0, 1.0]; got {self.score!r}."
            )

    def to_dict(self) -> dict:
        """Return a plain-dict view for serialization (report / provenance)."""
        return {
            "metric": self.metric,
            "property_key": self.property_key,
            "passed": self.passed,
            "score": self.score,
            "rationale": self.rationale,
            "evidence_type": self.evidence_type,
            "sample_index": self.sample_index,
        }


@dataclass(frozen=True)
class MajorityVerdict:
    """The combined result of an N≥3 majority vote over :class:`Verdict` panel.

    Produced only by :func:`majority_vote`.  Like its members it is typed
    :data:`EVIDENCE_TYPE_INFERRED` — a vote of opinions is still an opinion.

    Attributes
    ----------
    metric, property_key:
        Copied from the (identical across the panel) member verdicts.
    passed:
        Majority boolean call over members with a non-``None`` ``passed``.
        A **tie resolves to ``False``** — integrity-weighted: an evenly split
        panel is not agreement that a claim is supported.  ``None`` when no
        member carried a boolean (a score-only panel).
    score:
        Mean of member scores (those that are non-``None``); ``None`` when no
        member carried a score.
    agreement:
        Fraction of boolean members that agree with :attr:`passed`
        (``max(true, false) / total_boolean``); ``1.0`` means unanimous,
        ``None`` for a score-only panel.  A low agreement on a temp-0 panel is
        itself a signal that the property is genuinely borderline.
    n:
        Panel size (``len(members)``).
    members:
        The individual verdicts, in order.
    rationale:
        A one-line synthesis of the vote (counts + agreement); member
        rationales remain available via :attr:`members`.
    """

    metric: str
    property_key: str
    passed: bool | None
    score: float | None
    agreement: float | None
    n: int
    members: tuple[Verdict, ...]
    rationale: str = ""
    evidence_type: str = EVIDENCE_TYPE_INFERRED

    def __post_init__(self) -> None:
        _validate_inferred(self.evidence_type, "MajorityVerdict")

    def to_dict(self) -> dict:
        """Return a plain-dict view for serialization (report / provenance)."""
        return {
            "metric": self.metric,
            "property_key": self.property_key,
            "passed": self.passed,
            "score": self.score,
            "agreement": self.agreement,
            "n": self.n,
            "evidence_type": self.evidence_type,
            "rationale": self.rationale,
            "members": [m.to_dict() for m in self.members],
        }


def majority_vote(verdicts: Sequence[Verdict]) -> MajorityVerdict:
    """Combine an N≥3 panel of verdicts about the *same* property into one.

    The scaffold the guardrails mandate for any score that will inform a
    decision.  It requires at least :data:`MIN_MAJORITY_SAMPLES` samples (a
    smaller panel cannot break a tie or absorb residual non-determinism) and
    that every member concern the same ``metric`` / ``property_key`` (a vote
    mixes samples of *one* judgment, not different ones).

    Boolean rule: majority over members with a non-``None`` ``passed``; a tie
    resolves conservatively to ``False``.  Score rule: mean of non-``None``
    scores.  Both may be present, both may be absent.

    Raises
    ------
    ValueError
        If fewer than :data:`MIN_MAJORITY_SAMPLES` verdicts are supplied, or if
        the members disagree on ``metric`` / ``property_key``.
    """
    members = tuple(verdicts)
    if len(members) < MIN_MAJORITY_SAMPLES:
        raise ValueError(
            f"majority_vote requires at least {MIN_MAJORITY_SAMPLES} samples "
            f"(the guardrails' N≥3 rule where a score informs a decision); "
            f"got {len(members)}."
        )

    metric = members[0].metric
    property_key = members[0].property_key
    for v in members[1:]:
        if v.metric != metric or v.property_key != property_key:
            raise ValueError(
                "majority_vote members must all concern the same "
                f"(metric, property_key); expected ({metric!r}, {property_key!r}) "
                f"but found ({v.metric!r}, {v.property_key!r})."
            )

    booleans = [v.passed for v in members if v.passed is not None]
    if booleans:
        true_count = sum(1 for b in booleans if b)
        false_count = len(booleans) - true_count
        passed: bool | None = true_count > false_count  # tie -> False
        agreement: float | None = max(true_count, false_count) / len(booleans)
    else:
        true_count = false_count = 0
        passed = None
        agreement = None

    scores = [float(v.score) for v in members if v.score is not None]
    score: float | None = (sum(scores) / len(scores)) if scores else None

    rationale = _synthesize_rationale(
        n=len(members),
        true_count=true_count,
        false_count=false_count,
        passed=passed,
        agreement=agreement,
        score=score,
    )

    return MajorityVerdict(
        metric=metric,
        property_key=property_key,
        passed=passed,
        score=score,
        agreement=agreement,
        n=len(members),
        members=members,
        rationale=rationale,
    )


def _synthesize_rationale(
    *,
    n: int,
    true_count: int,
    false_count: int,
    passed: bool | None,
    agreement: float | None,
    score: float | None,
) -> str:
    """Build the one-line vote synthesis stored on :class:`MajorityVerdict`."""
    parts: list[str] = [f"majority over n={n}"]
    if passed is not None:
        agree_pct = f"{agreement:.0%}" if agreement is not None else "n/a"
        parts.append(
            f"passed={passed} ({true_count} true / {false_count} false, "
            f"agreement {agree_pct})"
        )
    if score is not None:
        parts.append(f"mean score={score:.3f}")
    return "; ".join(parts)
