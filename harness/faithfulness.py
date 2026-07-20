"""
The atomic faithfulness question — "does this source support this claim?" (E1.5).

Calibration (:mod:`harness.calibration`) measures the judge's precision/recall on
*faithfulness verdicts*, so it needs a way to ask the judge exactly one bounded
question about a ``(claim, source)`` pair and read back a boolean: **is the claim
supported by the source it cites?**  This module owns that minimal primitive —
the prompt and the judge wiring — and nothing more.

It is deliberately the *atomic* unit, not the E2 metric.  E2 (status-aware
faithfulness) will build on the same question by partitioning claims by ``status``
and applying status-specific thresholds (``confirmed`` → ≈1.0 vs source;
``assumed`` → vs the declared value; ``inferred`` → softer); that partitioning is
E2's, not built here.  Keeping the primitive separate means E1.5 and E2 ask the
judge the same question the gold set is labeled against.

The judge answers with the default verdict schema: ``passed`` is ``True`` iff the
source supports the claim.  As always the verdict is ``Inferred`` and never
overrides a deterministic predicate — faithfulness (semantic entailment) is
precisely the gap no predicate can check.

Constitutional authority:
    Subordinate to CLAUDE.md.  Out-of-band QA substrate.  See ``harness/HARNESS.md``.
"""

from __future__ import annotations

from pathlib import Path

from runner.paths import resolve_repo_path
from harness.gold_set import GoldPair
from harness.judge import Judge, JudgeResult

__all__ = [
    "FAITHFULNESS_METRIC",
    "INDEPENDENCE_PREAMBLE",
    "build_claim_user_prompt",
    "build_faithfulness_prompt",
    "resolve_source_text",
    "judge_pair_supported",
]

#: The metric name stamped on faithfulness verdicts and their provenance.
FAITHFULNESS_METRIC: str = "faithfulness_atomic"

#: The shared opening of every harness faithfulness system prompt — the
#: grader/generator-independence framing (strategy §1).  Exposed so E2's
#: status-specific prompts (:mod:`harness.status_faithfulness`) open with the
#: *same* words rather than a near-duplicate, keeping "the judge is a different
#: model, judging only from the material" a single source of truth.
INDEPENDENCE_PREAMBLE: str = (
    "You are an independent faithfulness judge for a research-proposal "
    "integrity harness. You are deliberately a different model from the one "
    "that drafted the text, and you judge ONLY from the material provided "
    "— never from prior knowledge or plausibility.\n\n"
)

_SYSTEM_PROMPT: str = (
    INDEPENDENCE_PREAMBLE
    + "Your single task: decide whether the SOURCE passage genuinely SUPPORTS "
    "the CLAIM. The source supports the claim only if it states the claim or "
    "clearly entails it. If the source is silent on the claim, contradicts it, "
    "or only loosely relates to it, the claim is NOT supported.\n\n"
    "Return ONLY a JSON object, no prose before or after:\n"
    '{"passed": <true if the source supports the claim, false otherwise>, '
    '"score": <optional 0.0–1.0 confidence the claim is supported>, '
    '"rationale": "<one sentence citing the decisive part of the source>"}\n\n'
    "Do not infer support the source does not actually provide. When in doubt, "
    'answer "passed": false.'
)


def build_claim_user_prompt(
    claim: str,
    material: str,
    *,
    question: str,
    material_label: str = "SOURCE PASSAGE",
    source_ref: str | None = None,
) -> str:
    """Return the user-turn text for a claim-vs-material faithfulness question.

    The shared user-prompt shape both the atomic question and E2's status-aware
    metric build: the ``CLAIM``, an optional ``SOURCE REF`` provenance label, the
    material under a caller-chosen *material_label* (``SOURCE PASSAGE`` for a
    source, ``DECLARED VALUE`` for an assumed claim), and the closing *question*.
    """
    ref_line = f"SOURCE REF (label only): {source_ref}\n" if source_ref else ""
    return (
        f"CLAIM:\n{claim}\n\n"
        f"{ref_line}"
        f"{material_label}:\n{material}\n\n"
        f"{question}"
    )


def build_faithfulness_prompt(
    claim: str,
    source_excerpt: str,
    *,
    source_ref: str | None = None,
) -> tuple[str, str]:
    """Return the ``(system_prompt, user_prompt)`` for the atomic faithfulness question.

    The judge is asked whether *source_excerpt* supports *claim*; ``passed=True``
    means supported.  *source_ref* is included only as a provenance label in the
    user turn — the judgment is made against the excerpt text.
    """
    user_prompt = build_claim_user_prompt(
        claim,
        source_excerpt,
        question="Does the SOURCE PASSAGE support the CLAIM? Return the JSON verdict.",
        material_label="SOURCE PASSAGE",
        source_ref=source_ref,
    )
    return _SYSTEM_PROMPT, user_prompt


def resolve_source_text(pair: GoldPair, *, repo_root: Path | None = None) -> str:
    """Return the source text to judge *pair* against.

    Prefers the pair's inline ``source_excerpt`` (self-contained and
    reproducible — the passage the human labeled against).  Falls back to reading
    ``source_ref`` from disk when *repo_root* is supplied.  Raises ``ValueError``
    if neither is available — the judge must never be asked to rule on an empty
    source.
    """
    if pair.source_excerpt and pair.source_excerpt.strip():
        return pair.source_excerpt
    if repo_root is not None:
        resolved = resolve_repo_path(pair.source_ref, repo_root)
        if resolved.is_file():
            return resolved.read_text(encoding="utf-8-sig")
        raise ValueError(
            f"gold pair {pair.pair_id!r}: source_ref {pair.source_ref!r} not found "
            f"under {repo_root}, and no inline source_excerpt is present."
        )
    raise ValueError(
        f"gold pair {pair.pair_id!r}: no source_excerpt and no repo_root to resolve "
        f"source_ref {pair.source_ref!r}; cannot judge faithfulness without a source."
    )


def judge_pair_supported(
    judge: Judge,
    pair: GoldPair,
    *,
    repo_root: Path | None = None,
) -> JudgeResult:
    """Ask *judge* whether *pair*'s source supports its claim.

    Returns the :class:`~harness.judge.JudgeResult`; ``result.verdict.passed`` is
    the judge's ``supported`` call (``True`` = supported).  The property key is
    the pair's id so the verdict and its provenance are traceable to the gold pair.
    """
    source_text = resolve_source_text(pair, repo_root=repo_root)
    system_prompt, user_prompt = build_faithfulness_prompt(
        pair.claim, source_text, source_ref=pair.source_ref
    )
    return judge.evaluate(
        system_prompt,
        user_prompt,
        metric=FAITHFULNESS_METRIC,
        property_key=pair.pair_id,
    )
