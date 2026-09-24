"""
Coverage-axis grader — "does the section substantively address this expectation?" (E5c).

The first of E5's two axes.  Per profile evaluator expectation, the judge is
asked one question over the E5b evidence pack: *does the section, as evidenced
by this pack, substantively address (and ground) the expectation* — the
semantic residue the deterministic ``instrument_sections_addressed`` predicate
cannot reach.  The predicate proves a section artifact exists and is non-empty;
only a judge can say whether the prose actually answers the evaluator's
question.  The grounding axis (E5d) is a separate metric built on E2; the two
are combined — never blended — by E5e.

What this module enforces, in code:

* **Routing.**  Every grade is routed through
  :func:`~harness.routing.assert_judgeable` under a property key
  (:func:`coverage_property_key`) that is *distinct* from any deterministic
  predicate name — if the key ever collides with the runtime's
  ``PREDICATE_REGISTRY``, grading raises
  :class:`~harness.routing.DeterministicCoverageError` instead of silently
  double-checking a proof with an opinion.  The routing decision is recorded on
  the grade.
* **N≥3 majority.**  The verdict is an
  :meth:`~harness.judge.Judge.evaluate_majority` panel (never a single
  sample) — the guardrails' rule wherever a score will inform a decision.
  Every member and the combined majority are typed ``Inferred``.
* **Provenance is mandatory.**  ``grade_coverage`` refuses a judge without an
  attached :class:`~harness.provenance.ProvenanceLog` — an E5c score that is
  not in a durable provenance trail does not exist.  Each sample's
  ``prompt_hash`` equals the offline-computable
  :func:`~harness.rubrics.rubric_prompt_hash`, so a report can pin the exact
  prompts without re-invoking the judge.
* **A truncated pack is never a clean pass.**  The grade's ``passed`` field is
  derived through :func:`~harness.evidence_pack.clean_pass`, never read off
  the raw verdict: whatever the judge answered over an
  ``insufficient_context`` pack, the combined outcome is not a clean pass.
  The raw majority call is preserved separately (``judge_passed``) so the
  override is visible, not silent.

Grader/generator independence (the E5c ticket's structural assertion) is
enforced upstream and asserted in ``tests/harness/test_expectation_coverage.py``:
the :class:`~harness.judge.JudgeConfig` model guard rejects the drafter /
in-run-reviewer models (the ``evaluator-criteria-review`` skill's
``SKILL_MODEL``), the default backend rejects the ``claude_cli`` drafter
transport, and this module's judge context is exactly the frozen artifact's
evidence pack — it never touches the in-run drafting context or the drafter
transport stack.

Constitutional authority:
    Subordinate to CLAUDE.md.  Out-of-band QA substrate; reads frozen section
    artifacts read-only and writes only harness-owned provenance files.  Never
    a runtime gate.  See ``harness/HARNESS.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harness.evidence_pack import (
    DEFAULT_PACK_TOKEN_BUDGET,
    DEFAULT_SPAN_BUDGET_FRACTION,
    EvidencePack,
    clean_pass,
)
from harness.judge import Judge
from harness.provenance import ProvenanceRecord
from harness.routing import RoutingDecision, assert_judgeable
from harness.rubrics import (
    Rubric,
    build_pack_for,
    build_rubric_prompts,
    rubric_fingerprint,
    rubric_prompt_hash,
)
from harness.verdict import MIN_MAJORITY_SAMPLES, MajorityVerdict

__all__ = [
    "EXPECTATION_COVERAGE_METRIC",
    "CoverageError",
    "coverage_property_key",
    "CoverageGrade",
    "grade_coverage",
    "grade_expectation",
]

#: The metric name stamped on every coverage verdict and its provenance.
#: Deliberately NOT the name of the deterministic ``instrument_sections_addressed``
#: predicate — that predicate proves a section exists/is non-empty; this metric
#: judges the semantic residue (does the prose substantively address the
#: expectation).  Routing refuses any key the predicate registry covers.
EXPECTATION_COVERAGE_METRIC: str = "expectation_coverage"


class CoverageError(Exception):
    """The coverage grader was invoked outside its contract (fail-closed)."""


def coverage_property_key(expectation_key: str, section_id: str) -> str:
    """The property key one ``(expectation, section)`` coverage grade is judged under.

    Namespaced with the metric name so it can never collide with a
    deterministic predicate's bare function name; routed through
    :func:`~harness.routing.assert_judgeable` on every grade regardless.
    """
    return f"{EXPECTATION_COVERAGE_METRIC}::{expectation_key}::{section_id}"


@dataclass(frozen=True)
class CoverageGrade:
    """One coverage verdict for one ``(expectation, section)`` pair.

    ``passed`` is the *clean-pass* outcome — the judge's majority call combined
    with the pack's truncation contract via
    :func:`~harness.evidence_pack.clean_pass`; ``judge_passed`` preserves the
    raw majority call so a truncation override is visible.  ``pack_record`` is
    the pack's full selection record (inclusions, exclusions with reasons,
    budget) — the no-silent-caps audit trail travels with the score.
    """

    expectation_key: str
    criterion_id: str
    section_id: str
    section_path: str
    property_key: str
    routing: RoutingDecision
    rubric_fingerprint: str
    prompt_hash: str
    pack_status: str
    pack_token_estimate: int
    pack_record: dict[str, Any]
    verdict: MajorityVerdict
    provenance: tuple[ProvenanceRecord, ...]
    passed: bool
    judge_passed: bool | None
    score: float | None
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        """A JSON-serializable view (report / baseline input)."""
        return {
            "metric": EXPECTATION_COVERAGE_METRIC,
            "expectation_key": self.expectation_key,
            "criterion_id": self.criterion_id,
            "section_id": self.section_id,
            "section_path": self.section_path,
            "property_key": self.property_key,
            "routing": self.routing.to_dict(),
            "rubric_fingerprint": self.rubric_fingerprint,
            "prompt_hash": self.prompt_hash,
            "pack_status": self.pack_status,
            "pack_token_estimate": self.pack_token_estimate,
            "pack_record": self.pack_record,
            "verdict": self.verdict.to_dict(),
            "provenance": [p.to_dict() for p in self.provenance],
            "passed": self.passed,
            "judge_passed": self.judge_passed,
            "score": self.score,
            "rationale": self.rationale,
        }


def grade_coverage(
    judge: Judge,
    rubric: Rubric,
    pack: EvidencePack,
    *,
    n: int = MIN_MAJORITY_SAMPLES,
) -> CoverageGrade:
    """Grade one ``(expectation, section)`` coverage question, fail-closed.

    Sequence — each step's guard raises rather than degrading:

    1. **Provenance is mandatory:** a judge without an attached
       :class:`~harness.provenance.ProvenanceLog` is refused
       (:class:`CoverageError`) — every E5c verdict must land in a durable
       provenance trail.
    2. **Routing:** the property key is checked against the runtime's
       deterministic predicate registry
       (:class:`~harness.routing.DeterministicCoverageError` on collision).
    3. **Prompts:** rendered by :func:`~harness.rubrics.build_rubric_prompts`,
       which refuses a pack built for a different expectation.
    4. **Judge:** an N≥3 majority panel (``ValueError`` below
       :data:`~harness.verdict.MIN_MAJORITY_SAMPLES`); every sample's
       provenance is logged.
    5. **Clean pass:** ``passed`` is derived through
       :func:`~harness.evidence_pack.clean_pass` — a truncated pack cannot
       yield a clean pass whatever the judge answered.
    """
    if judge.provenance_log is None:
        raise CoverageError(
            "grade_coverage requires a Judge with an attached ProvenanceLog — "
            "every coverage verdict must land in a durable provenance trail "
            "(construct the Judge with provenance_log=ProvenanceLog(...))."
        )

    property_key = coverage_property_key(pack.expectation_key, pack.section_id)
    routing = assert_judgeable(property_key)

    system_prompt, user_prompt = build_rubric_prompts(rubric, pack)
    result = judge.evaluate_majority(
        system_prompt,
        user_prompt,
        metric=EXPECTATION_COVERAGE_METRIC,
        property_key=property_key,
        n=n,
    )
    majority = result.majority

    return CoverageGrade(
        expectation_key=rubric.expectation_key,
        criterion_id=rubric.criterion_id,
        section_id=pack.section_id,
        section_path=pack.section_path,
        property_key=property_key,
        routing=routing,
        rubric_fingerprint=rubric_fingerprint(rubric),
        prompt_hash=rubric_prompt_hash(rubric, pack),
        pack_status=pack.status,
        pack_token_estimate=pack.token_estimate,
        pack_record=pack.to_dict(),
        verdict=majority,
        provenance=result.provenance,
        passed=clean_pass(pack, majority.passed),
        judge_passed=majority.passed,
        score=majority.score,
        rationale=majority.rationale,
    )


def grade_expectation(
    judge: Judge,
    rubric: Rubric,
    section_path: Path | str,
    *,
    token_budget: int = DEFAULT_PACK_TOKEN_BUDGET,
    span_budget_fraction: float = DEFAULT_SPAN_BUDGET_FRACTION,
    n: int = MIN_MAJORITY_SAMPLES,
) -> CoverageGrade:
    """Build the rubric's evidence pack over *section_path* and grade it.

    The one-call form E5f drives: pack construction goes through
    :func:`~harness.rubrics.build_pack_for` so the selection provably used the
    rubric's versioned basis, then :func:`grade_coverage` applies every guard.
    """
    pack = build_pack_for(
        rubric,
        section_path,
        token_budget=token_budget,
        span_budget_fraction=span_budget_fraction,
    )
    return grade_coverage(judge, rubric, pack, n=n)
