"""
Grounding-axis grader — E2 aggregation per evaluator expectation (E5d).

The second of E5's two axes.  Per profile evaluator expectation, this module
answers "is what the section says *traceable to grounded claims*?" — and it
deliberately contributes **no faithfulness judgment of its own**.  E2
(:mod:`harness.status_faithfulness`) stays the single system-of-record for
"does the source entail the claim"; E5d derives its grade from the claims in
the E5b evidence pack and E2's per-claim verdicts, adding only the
*aggregation*: the per-expectation grounding rate and the weakest-link claim.
The coverage axis (E5c) is a separate metric; the two are combined — never
blended — by E5e, whose headline output is the high-coverage / weak-grounding
contradiction cell.

What this module enforces, in code:

* **One system-of-record, zero new faithfulness prompts.**  Any claim that
  still needs judging goes through E2's
  :func:`~harness.status_faithfulness.evaluate_claim` — this module renders no
  prompt and never invokes the judge directly (a test pins both, statically
  and behaviorally).  Every row of the grade is traceable to an individual E2
  :class:`~harness.status_faithfulness.ClaimFaithfulness` verdict.
* **Verdict reuse, no duplicate judge calls.**  Where the section has already
  been judged (a :class:`~harness.status_faithfulness.StatusFaithfulnessResult`
  is supplied), its verdicts are reused — with a fail-closed consistency check,
  because a stale result silently re-attributed would be worse than a re-run.
  A caller-owned *verdict cache* keyed by claim **content**
  ``(claim_summary, status, source_ref)`` dedupes across the nine expectations
  of one grading run: the same pair is never judged twice (budget + the
  one-SoR discipline).
* **Status-aware aggregation, nothing averaged away.**  ``confirmed`` claims
  are the grounding axis proper — a confirmed claim that fails entailment
  (E2's :data:`~harness.status_faithfulness.SEVERITY_INTEGRITY`) dominates:
  one such failure makes the expectation ungrounded regardless of the rate.
  ``assumed`` and ``inferred`` claims are reported in their own buckets,
  never folded into the confirmed rate — an expectation answered *only* by
  assumed/inferred claims has ``grounding_rate = None`` and is **not**
  grounded (that is precisely the weak-grounding cell E5e flags).
* **A truncated claim set is never cleanly grounded.**  If the pack excluded
  relevant *claims* for budget (``over_budget``), the grade was computed over
  a subset — ``grounded`` is forced ``False`` while the raw ``judge_grounded``
  signal stays visible (the E5b/E5c clean-pass discipline, applied at claim
  granularity: span-only truncation does not poison the claim axis).

Routing note: no judge runs under this module's aggregate property key — the
aggregation is deterministic arithmetic over E2 verdicts, and the judge
invocations themselves are routed per-claim inside E2's ``evaluate_claim``
(a green judge never overrides a red predicate).  The aggregate key exists as
a report identity for E5e and is test-pinned to never collide with a
deterministic predicate name.

Constitutional authority:
    Subordinate to CLAUDE.md.  Out-of-band QA substrate; reads frozen section
    artifacts read-only and writes only harness-owned provenance files.  Never
    a runtime gate.  See ``harness/HARNESS.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, MutableMapping

from runner.working_assumptions import WorkingAssumptions
from harness.evidence_pack import (
    DEFAULT_PACK_TOKEN_BUDGET,
    DEFAULT_SPAN_BUDGET_FRACTION,
    EXCLUDED_OVER_BUDGET,
    KIND_CLAIM,
    EvidencePack,
)
from harness.judge import Judge
from harness.rubrics import Rubric, build_pack_for
from harness.status_faithfulness import (
    COMPARISON_SOURCE,
    SEVERITY_CONTENT_DRIFT,
    SEVERITY_INTEGRITY,
    SEVERITY_NONE,
    SEVERITY_SOFT,
    SEVERITY_UNKNOWN_STATUS,
    SEVERITY_UNRESOLVED,
    STATUS_ASSUMED,
    STATUS_CONFIRMED,
    STATUS_INFERRED,
    ClaimFaithfulness,
    SectionClaim,
    SourceTextResolver,
    StatusFaithfulnessResult,
    StatusPolicy,
    evaluate_claim,
)
from harness.verdict import MIN_MAJORITY_SAMPLES

__all__ = [
    "EXPECTATION_GROUNDING_METRIC",
    "VERDICT_FROM_RESULT",
    "VERDICT_FROM_CACHE",
    "VERDICT_NEWLY_JUDGED",
    "GroundingError",
    "grounding_property_key",
    "claim_content_key",
    "VerdictCache",
    "ClaimGroundingRow",
    "GroundingGrade",
    "derive_grounding",
    "derive_expectation_grounding",
]

#: The metric name stamped on the aggregate grade (report identity for E5e).
#: No judge prompt runs under this name — E2's ``status_aware_faithfulness``
#: remains the metric on every underlying verdict.
EXPECTATION_GROUNDING_METRIC: str = "expectation_grounding"

#: How a row's verdict was obtained — reused from a supplied whole-section E2
#: result, reused from the cross-expectation verdict cache, or newly judged
#: through E2's ``evaluate_claim`` by this derivation.
VERDICT_FROM_RESULT: str = "existing_result"
VERDICT_FROM_CACHE: str = "cache"
VERDICT_NEWLY_JUDGED: str = "judged"

#: A caller-owned store of E2 verdicts keyed by claim content
#: (:func:`claim_content_key`).  Pass the same mapping across the nine
#: expectations of one grading run to guarantee no ``(claim, source_ref)``
#: pair is judged twice.  Scope one cache to one judge pin — entries carry no
#: judge identity of their own (the pin is recorded on the grade).
VerdictCache = MutableMapping[tuple[str, str, str], ClaimFaithfulness]


class GroundingError(Exception):
    """The grounding derivation was invoked outside its contract (fail-closed)."""


def grounding_property_key(expectation_key: str, section_id: str) -> str:
    """The aggregate grade's identity key (``expectation_grounding::key::section``).

    A label for reports and E5e, namespaced like E5c's coverage key.  Nothing
    is judged under it — E2 routes each underlying verdict on the claim's
    ``entry_key``.
    """
    return f"{EXPECTATION_GROUNDING_METRIC}::{expectation_key}::{section_id}"


def claim_content_key(claim: SectionClaim) -> tuple[str, str, str]:
    """The dedup key for one judged pair: ``(claim_summary, status, source_ref)``.

    Content-based, not ``entry_key``-based — entry keys are section-scoped and
    repeat across sections, while two entries with identical content are the
    same judged pair wherever they appear (the E3a lesson, applied to reuse).
    """
    return (claim.claim_summary, claim.status, claim.source_ref)


#: Weakest-link ordering: lower rank = weaker grounding.  A confirmed
#: entailment failure is the integrity-critical worst; ``none`` never ranks
#: (only flagged rows compete).
_WEAKEST_RANK: dict[str, int] = {
    SEVERITY_INTEGRITY: 0,
    SEVERITY_CONTENT_DRIFT: 1,
    SEVERITY_UNRESOLVED: 2,
    SEVERITY_UNKNOWN_STATUS: 3,
    SEVERITY_SOFT: 4,
}


@dataclass(frozen=True)
class ClaimGroundingRow:
    """One pack claim with its E2 verdict and how that verdict was obtained.

    ``claim`` is the pack's own entry (identity within *this* section);
    ``finding`` is the E2 verdict it is traceable to — which, on a cache hit,
    may carry the ``entry_key`` of the entry first judged.  ``verdict_source``
    records the reuse path (:data:`VERDICT_FROM_RESULT` /
    :data:`VERDICT_FROM_CACHE` / :data:`VERDICT_NEWLY_JUDGED`).
    """

    claim: SectionClaim
    finding: ClaimFaithfulness
    verdict_source: str
    matched_terms: tuple[str, ...]

    @property
    def severity(self) -> str:
        return self.finding.severity

    @property
    def grounded(self) -> bool:
        """Whether this claim met its E2 status bar (``severity == none``)."""
        return self.finding.severity == SEVERITY_NONE

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_key": self.claim.entry_key,
            "status": self.claim.status,
            "source_ref": self.claim.source_ref,
            "verdict_source": self.verdict_source,
            "matched_terms": list(self.matched_terms),
            "grounded": self.grounded,
            "finding": self.finding.to_dict(),
        }


@dataclass(frozen=True)
class GroundingGrade:
    """The grounding outcome for one ``(expectation, section)`` pair.

    The grounding axis proper is the **confirmed** bucket: ``grounding_rate``
    is the fraction of confirmed claims that met E2's strict bar, and one
    confirmed entailment failure (:data:`~harness.status_faithfulness.SEVERITY_INTEGRITY`)
    dominates — ``judge_grounded`` is ``True`` only when *every* confirmed
    claim is grounded.  ``assumed`` / ``inferred`` rows are reported in their
    own buckets, never averaged into the rate.  ``grounded`` is the clean
    outcome: ``judge_grounded`` combined with the claim-truncation contract —
    a grade computed over a budget-truncated claim set cannot be cleanly
    grounded, whatever the verdicts said (``claims_truncated`` preserves the
    override's visibility, mirroring E5c's ``passed`` / ``judge_passed``).
    """

    expectation_key: str
    criterion_id: str
    section_id: str
    section_path: str
    property_key: str
    pack_status: str
    claims_truncated: bool
    rows: tuple[ClaimGroundingRow, ...]
    judge_model: str | None
    judge_version: str | None

    # -- status buckets ---------------------------------------------------- #

    def rows_for(self, status: str) -> tuple[ClaimGroundingRow, ...]:
        return tuple(r for r in self.rows if r.claim.status == status)

    @property
    def confirmed_rows(self) -> tuple[ClaimGroundingRow, ...]:
        return self.rows_for(STATUS_CONFIRMED)

    @property
    def assumed_rows(self) -> tuple[ClaimGroundingRow, ...]:
        return self.rows_for(STATUS_ASSUMED)

    @property
    def inferred_rows(self) -> tuple[ClaimGroundingRow, ...]:
        return self.rows_for(STATUS_INFERRED)

    # -- the confirmed (grounding) axis ------------------------------------ #

    @property
    def confirmed_total(self) -> int:
        return len(self.confirmed_rows)

    @property
    def confirmed_grounded(self) -> int:
        return sum(1 for r in self.confirmed_rows if r.grounded)

    @property
    def grounding_rate(self) -> float | None:
        """Grounded fraction of the confirmed claims; ``None`` with none to rate.

        Unresolved confirmed claims count against the rate (an unverifiable
        confirmed claim is not grounded), and ``None`` — an expectation with
        no confirmed claims at all — is *weak grounding*, not a vacuous pass.
        """
        if self.confirmed_total == 0:
            return None
        return self.confirmed_grounded / self.confirmed_total

    def integrity_failures(self) -> tuple[ClaimGroundingRow, ...]:
        """The dominating rows: confirmed claims whose entailment failed."""
        return tuple(
            r for r in self.confirmed_rows if r.severity == SEVERITY_INTEGRITY
        )

    @property
    def judge_grounded(self) -> bool | None:
        """The raw verdict-level signal, before the truncation override.

        ``None`` when the pack carries no confirmed claims (nothing to
        entail-check); else ``True`` iff every confirmed claim met its bar —
        one integrity failure (or unresolved confirmed claim) flips it.
        """
        if self.confirmed_total == 0:
            return None
        return self.confirmed_grounded == self.confirmed_total

    @property
    def grounded(self) -> bool:
        """The clean grounding outcome E5e consumes.

        ``True`` iff every confirmed claim is grounded, at least one exists,
        and no relevant claim was excluded for budget.  ``False`` covers the
        weak-grounding cell in all its forms: a failed/unresolved confirmed
        claim, an expectation answered only by assumed/inferred claims, or a
        truncated claim set.
        """
        return self.judge_grounded is True and not self.claims_truncated

    # -- reported-separately buckets --------------------------------------- #

    @property
    def assumed_drift(self) -> int:
        """Assumed claims that do not match their declared value (E2 hard finding)."""
        return sum(
            1 for r in self.assumed_rows if r.severity == SEVERITY_CONTENT_DRIFT
        )

    @property
    def inferred_soft(self) -> int:
        """Inferred claims below E2's soft grounding bar."""
        return sum(1 for r in self.inferred_rows if r.severity == SEVERITY_SOFT)

    # -- weakest link ------------------------------------------------------- #

    @property
    def weakest_link(self) -> ClaimGroundingRow | None:
        """The single row that most undermines grounding; ``None`` if all met their bar.

        Worst severity first (:data:`_WEAKEST_RANK` — a confirmed entailment
        failure outranks everything), then lowest judge score (a scoreless
        flagged row ranks after scored ones), then pack order.
        """
        flagged = [r for r in self.rows if r.severity != SEVERITY_NONE]
        if not flagged:
            return None

        def key(row: ClaimGroundingRow) -> tuple[int, float]:
            score = row.finding.score
            return (
                _WEAKEST_RANK.get(row.severity, len(_WEAKEST_RANK)),
                score if score is not None else float("inf"),
            )

        return min(flagged, key=key)

    # -- reuse accounting --------------------------------------------------- #

    @property
    def reused_count(self) -> int:
        return sum(1 for r in self.rows if r.verdict_source != VERDICT_NEWLY_JUDGED)

    @property
    def judged_count(self) -> int:
        return sum(1 for r in self.rows if r.verdict_source == VERDICT_NEWLY_JUDGED)

    def to_dict(self) -> dict[str, Any]:
        """A JSON-serializable view (report / baseline / E5e input)."""
        weakest = self.weakest_link
        return {
            "metric": EXPECTATION_GROUNDING_METRIC,
            "expectation_key": self.expectation_key,
            "criterion_id": self.criterion_id,
            "section_id": self.section_id,
            "section_path": self.section_path,
            "property_key": self.property_key,
            "pack_status": self.pack_status,
            "claims_truncated": self.claims_truncated,
            "judge_model": self.judge_model,
            "judge_version": self.judge_version,
            "grounded": self.grounded,
            "judge_grounded": self.judge_grounded,
            "grounding_rate": self.grounding_rate,
            "confirmed_total": self.confirmed_total,
            "confirmed_grounded": self.confirmed_grounded,
            "integrity_failure_keys": [
                r.claim.entry_key for r in self.integrity_failures()
            ],
            "assumed_total": len(self.assumed_rows),
            "assumed_drift": self.assumed_drift,
            "inferred_total": len(self.inferred_rows),
            "inferred_soft": self.inferred_soft,
            "weakest_link": weakest.to_dict() if weakest is not None else None,
            "reused_count": self.reused_count,
            "judged_count": self.judged_count,
            "rows": [r.to_dict() for r in self.rows],
        }


# --------------------------------------------------------------------------- #
# Verdict resolution — reuse first, judge last, never silent
# --------------------------------------------------------------------------- #


def _check_reused_finding(
    finding: ClaimFaithfulness, claim: SectionClaim, section_id: str
) -> None:
    """Fail closed if a reused verdict does not match the pack claim's content.

    An ``entry_key`` hit against a *stale* E2 result (the ledger changed since
    the section was judged) would silently attribute the wrong verdict — the
    exact mis-pairing the E3a identity discipline exists to prevent.  The
    check covers everything :class:`ClaimFaithfulness` carries: id, status,
    the claim's own wording (``claim_summary`` — empty only on findings frozen
    before the field existed, where wording drift is undetectable), and (for
    source comparisons) the ``source_ref`` it was judged against.
    """
    stale: list[str] = []
    if finding.claim_id != claim.claim_id:
        stale.append(f"claim_id {finding.claim_id!r} != {claim.claim_id!r}")
    if finding.status != claim.status:
        stale.append(f"status {finding.status!r} != {claim.status!r}")
    if finding.claim_summary and finding.claim_summary != claim.claim_summary:
        stale.append(
            f"claim wording changed since judged: {finding.claim_summary!r} != "
            f"{claim.claim_summary!r}"
        )
    if finding.comparison == COMPARISON_SOURCE and finding.comparison_ref != claim.source_ref:
        stale.append(
            f"source_ref {finding.comparison_ref!r} != {claim.source_ref!r}"
        )
    if stale:
        raise GroundingError(
            f"existing E2 result for section {section_id!r} is stale at entry "
            f"{claim.entry_key!r}: {'; '.join(stale)} — re-run E2 on the current "
            "ledger instead of silently re-attributing verdicts."
        )


def derive_grounding(
    rubric: Rubric,
    pack: EvidencePack,
    *,
    existing: StatusFaithfulnessResult | None = None,
    judge: Judge | None = None,
    repo_root: Path | None = None,
    working_assumptions: WorkingAssumptions | None = None,
    policies: Mapping[str, StatusPolicy] | None = None,
    n: int = MIN_MAJORITY_SAMPLES,
    source_text_resolver: SourceTextResolver | None = None,
    verdict_cache: VerdictCache | None = None,
) -> GroundingGrade:
    """Derive the grounding grade for one ``(expectation, section)``, fail-closed.

    Each pack claim's E2 verdict is resolved in reuse-first order — any step's
    guard raises rather than degrading:

    1. **Existing result** (*existing*, a whole-section E2 run): matched by
       ``entry_key`` with a staleness check
       (:func:`_check_reused_finding`).  Its judge pin must match a supplied
       *judge*'s pin — aggregating verdicts across a judge repin is refused
       (the E1.5 repin discipline).
    2. **Verdict cache** (*verdict_cache*, caller-owned, shared across the
       nine expectations): matched by claim content
       (:func:`claim_content_key`), so the same ``(claim, source_ref)`` pair
       is never judged twice in one run.
    3. **E2 judging** (*judge*): the claim is judged by
       :func:`~harness.status_faithfulness.evaluate_claim` — E2's prompts,
       E2's policies, E2's routing; this module adds none.  Requires
       *repo_root* + *working_assumptions*, a judge with an attached
       provenance log, and an N≥3 panel (*n*; a score that will inform the
       E5e decision needs a majority behind it).
    4. **Neither** → :class:`GroundingError` naming the unjudgeable entries —
       a grade over partially-judged claims would mask exactly the gap this
       axis exists to surface.

    Every resolved verdict (reused or new) is recorded into *verdict_cache*
    when one is supplied, so later expectations in the run reuse it.
    """
    if pack.expectation_key != rubric.expectation_key:
        raise GroundingError(
            f"evidence pack was built for {pack.expectation_key!r}, not for "
            f"rubric {rubric.expectation_key!r} — refusing to grade a mismatched "
            "pack."
        )
    if (
        existing is not None
        and existing.section_id
        and existing.section_id != pack.section_id
    ):
        raise GroundingError(
            f"existing E2 result is for section {existing.section_id!r}, the "
            f"pack for {pack.section_id!r} — refusing a cross-section reuse."
        )
    if judge is not None:
        if judge.provenance_log is None:
            raise GroundingError(
                "derive_grounding requires a Judge with an attached "
                "ProvenanceLog — every E2 verdict minted for a grounding grade "
                "must land in a durable provenance trail."
            )
        if n < MIN_MAJORITY_SAMPLES:
            raise ValueError(
                f"derive_grounding judges new claims only under an N≥"
                f"{MIN_MAJORITY_SAMPLES} majority (the grounding grade informs "
                f"the E5e decision); got n={n}."
            )
        if existing is not None and (
            existing.judge_model != judge.config.model
            or existing.judge_version != judge.config.version
        ):
            raise GroundingError(
                f"judge pin mismatch: the existing E2 result was judged under "
                f"{existing.judge_model!r}/{existing.judge_version!r}, the "
                f"supplied judge is {judge.config.model!r}/"
                f"{judge.config.version!r} — verdicts across a judge repin must "
                "not be aggregated into one grade (re-run E2 under the current "
                "pin)."
            )
        if repo_root is None or working_assumptions is None:
            raise GroundingError(
                "judging new claims requires repo_root and working_assumptions "
                "(E2's comparison-target resolution needs both)."
            )

    existing_by_key: dict[str, ClaimFaithfulness] = (
        {f.entry_key: f for f in existing.findings} if existing is not None else {}
    )

    rows: list[ClaimGroundingRow] = []
    missing: list[str] = []
    for pack_claim in pack.claims:
        claim = pack_claim.claim
        content_key = claim_content_key(claim)
        finding = existing_by_key.get(claim.entry_key)
        if finding is not None:
            _check_reused_finding(finding, claim, pack.section_id)
            source = VERDICT_FROM_RESULT
        elif verdict_cache is not None and content_key in verdict_cache:
            finding = verdict_cache[content_key]
            source = VERDICT_FROM_CACHE
        elif judge is not None:
            finding = evaluate_claim(
                judge,
                claim,
                repo_root=repo_root,
                working_assumptions=working_assumptions,
                policies=policies,
                n=n,
                source_text_resolver=source_text_resolver,
            )
            source = VERDICT_NEWLY_JUDGED
        else:
            missing.append(claim.entry_key)
            continue
        if verdict_cache is not None:
            verdict_cache.setdefault(content_key, finding)
        rows.append(
            ClaimGroundingRow(
                claim=claim,
                finding=finding,
                verdict_source=source,
                matched_terms=pack_claim.matched_terms,
            )
        )
    if missing:
        raise GroundingError(
            f"no E2 verdict for pack claim(s) {missing} of section "
            f"{pack.section_id!r} and no judge supplied — a grounding grade "
            "over partially-judged claims would mask the gap; supply the "
            "section's StatusFaithfulnessResult or a judge."
        )

    if existing is not None:
        judge_model, judge_version = existing.judge_model, existing.judge_version
    elif judge is not None:
        judge_model, judge_version = judge.config.model, judge.config.version
    else:  # every row came from the (caller-scoped, single-pin) cache
        judge_model, judge_version = None, None

    claims_truncated = any(
        e.kind == KIND_CLAIM and e.reason == EXCLUDED_OVER_BUDGET
        for e in pack.excluded
    )
    return GroundingGrade(
        expectation_key=rubric.expectation_key,
        criterion_id=rubric.criterion_id,
        section_id=pack.section_id,
        section_path=pack.section_path,
        property_key=grounding_property_key(
            rubric.expectation_key, pack.section_id
        ),
        pack_status=pack.status,
        claims_truncated=claims_truncated,
        rows=tuple(rows),
        judge_model=judge_model,
        judge_version=judge_version,
    )


def derive_expectation_grounding(
    rubric: Rubric,
    section_path: Path | str,
    *,
    token_budget: int = DEFAULT_PACK_TOKEN_BUDGET,
    span_budget_fraction: float = DEFAULT_SPAN_BUDGET_FRACTION,
    existing: StatusFaithfulnessResult | None = None,
    judge: Judge | None = None,
    repo_root: Path | None = None,
    working_assumptions: WorkingAssumptions | None = None,
    policies: Mapping[str, StatusPolicy] | None = None,
    n: int = MIN_MAJORITY_SAMPLES,
    source_text_resolver: SourceTextResolver | None = None,
    verdict_cache: VerdictCache | None = None,
) -> GroundingGrade:
    """Build the rubric's evidence pack over *section_path* and derive its grounding.

    The one-call form E5e/E5f drive, mirroring E5c's ``grade_expectation``:
    pack construction goes through :func:`~harness.rubrics.build_pack_for` so
    the claim selection provably used the rubric's versioned basis, then
    :func:`derive_grounding` applies every guard.
    """
    pack = build_pack_for(
        rubric,
        section_path,
        token_budget=token_budget,
        span_budget_fraction=span_budget_fraction,
    )
    return derive_grounding(
        rubric,
        pack,
        existing=existing,
        judge=judge,
        repo_root=repo_root,
        working_assumptions=working_assumptions,
        policies=policies,
        n=n,
        source_text_resolver=source_text_resolver,
        verdict_cache=verdict_cache,
    )
