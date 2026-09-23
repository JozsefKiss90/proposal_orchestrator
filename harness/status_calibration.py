"""
Claim-status calibration — mislabel drift in both directions (E3).

The engine's ``status`` vocabulary (CLAUDE.md §12.2) is a *promise about
evidence*: ``confirmed`` promises direct source support, ``inferred`` promises
only grounded synthesis.  E2 polices the promise a claim *makes*; this module
polices whether the label itself has **drifted** from the evidence:

* **Overclaimed** (:data:`DRIFT_OVERCLAIMED`, ``confirmed_not_grounded``) — a
  ``confirmed`` claim whose own source does not support it.  This is E2's
  ``SEVERITY_INTEGRITY`` finding wearing its calibration hat, so the check
  **reuses E2**: pass an existing
  :class:`~harness.status_faithfulness.StatusFaithfulnessResult` and zero
  additional judge calls are spent on the confirmed direction; without one, E2
  is run internally over the confirmed claims.  A **hard** finding.
* **Underclaimed** (:data:`DRIFT_UNDERCLAIMED`, ``inferred_fully_grounded``) —
  an ``inferred`` claim that would clear the **confirmed bar**: its source
  states or clearly entails it.  Mislabelling down is integrity-*safe* but
  calibration-*wrong* (it understates the proposal's evidence base and blurs
  what ``inferred`` means), so it is a **soft, advisory** drift finding.  The
  judge is asked the confirmed-bar question — E2's own strict standard
  (:func:`~harness.status_faithfulness.build_faithfulness_prompt_for_status`
  with ``confirmed``) applied counterfactually to the inferred claim — and the
  bar decision delegates verbatim to E2's
  :func:`~harness.status_faithfulness.meets_bar` under
  ``DEFAULT_POLICIES["confirmed"]`` (boolean primary; a score refines the bar
  only under an N≥3 panel).

A claim that cannot be checked (unresolvable source; E2 surfaced it
unresolved) is :data:`DRIFT_UNVERIFIABLE` — surfaced, never dropped, and never
conflated with overclaiming.  Every row is keyed by the claim's disambiguated
``entry_key`` (real ledgers repeat ``claim_id`` across drafting blocks).

Reporting-only; zero DAG runs; advisory to a human by construction.

Constitutional authority:
    Subordinate to CLAUDE.md.  Out-of-band QA substrate.  Never a runtime
    gate.  See ``harness/HARNESS.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence

from runner.working_assumptions import WorkingAssumptions
from harness.judge import Judge, MajorityJudgeResult
from harness.report import HarnessReport, build_report
from harness.routing import RoutingDecision, assert_judgeable
from harness.status_faithfulness import (
    COMPARISON_SOURCE,
    DEFAULT_POLICIES,
    SEVERITY_INTEGRITY,
    SEVERITY_UNRESOLVED,
    STATUS_CONFIRMED,
    STATUS_INFERRED,
    SectionClaim,
    SourceResolutionError,
    SourceTextResolver,
    StatusFaithfulnessResult,
    build_faithfulness_prompt_for_status,
    entry_key_for,
    evaluate_status_aware_faithfulness,
    meets_bar,
    resolve_claim_source_text,
)
from harness.verdict import (
    MIN_MAJORITY_SAMPLES,
    MajorityVerdict,
    Verdict,
    validate_sample_count,
)

__all__ = [
    "STATUS_CALIBRATION_METRIC",
    "DRIFT_NONE",
    "DRIFT_OVERCLAIMED",
    "DRIFT_UNDERCLAIMED",
    "DRIFT_UNVERIFIABLE",
    "StatusCalibrationError",
    "ClaimDrift",
    "classify_underclaimed",
    "StatusCalibrationResult",
    "evaluate_status_calibration",
]

#: The metric name stamped on status-calibration verdicts and provenance.
STATUS_CALIBRATION_METRIC: str = "claim_status_calibration"

#: Drift kinds.  ``none`` means the label matches the evidence.
DRIFT_NONE: str = "none"
#: A ``confirmed`` claim its source does not support (mislabelled **up** — the
#: hard direction; identical evidence to E2's integrity finding).
DRIFT_OVERCLAIMED: str = "confirmed_not_grounded"
#: An ``inferred`` claim that clears the confirmed bar (mislabelled **down** —
#: soft, advisory).
DRIFT_UNDERCLAIMED: str = "inferred_fully_grounded"
#: The claim could not be checked (unresolvable source) — surfaced, not judged.
DRIFT_UNVERIFIABLE: str = "unverifiable"


class StatusCalibrationError(Exception):
    """A status-calibration input is inconsistent (e.g. an ``e2_result`` for a
    different section supplied as the confirmed-direction evidence)."""



# --------------------------------------------------------------------------- #
# Per-claim drift row
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class ClaimDrift:
    """The status-calibration outcome for one ledger entry.

    Keyed by ``entry_key`` (``claim_id`` + entry index) — never by the bare,
    ambiguous ``claim_id``.
    """

    claim_id: str
    entry_index: int | None
    status: str
    drift: str
    verdict: Verdict | MajorityVerdict | None = None
    reason: str = ""

    @property
    def entry_key(self) -> str:
        return entry_key_for(self.claim_id, self.entry_index)

    @property
    def is_hard_finding(self) -> bool:
        """Only overclaiming is hard — a confirmed label over an unsupported claim."""
        return self.drift == DRIFT_OVERCLAIMED

    @property
    def flagged(self) -> bool:
        return self.drift != DRIFT_NONE

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "entry_index": self.entry_index,
            "entry_key": self.entry_key,
            "status": self.status,
            "drift": self.drift,
            "is_hard_finding": self.is_hard_finding,
            "flagged": self.flagged,
            "reason": self.reason,
            "verdict": self.verdict.to_dict() if self.verdict is not None else None,
        }


def classify_underclaimed(
    verdict: Verdict | MajorityVerdict, *, n: int
) -> bool:
    """Whether an ``inferred`` claim's strict-bar verdict marks it mislabelled down.

    Delegates to E2's :func:`~harness.status_faithfulness.meets_bar` under the
    ``confirmed`` policy — the exact bar a confirmed claim must clear (boolean
    primary; the ≈1.0 score floor applies only when an N≥3 panel stands behind
    the score).  Pure; unit-testable without a judge.
    """
    return meets_bar(
        DEFAULT_POLICIES[STATUS_CONFIRMED],
        verdict,
        score_informs_decision=n >= MIN_MAJORITY_SAMPLES,
    )


# --------------------------------------------------------------------------- #
# Whole-section result
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class StatusCalibrationResult:
    """The status-calibration outcome for a section's ledger (reporting-only)."""

    section_id: str
    findings: tuple[ClaimDrift, ...]
    skipped_entry_keys: tuple[str, ...] = ()
    routing: tuple[RoutingDecision, ...] = ()
    judge_model: str | None = None
    judge_version: str | None = None
    e2_reused: bool = False

    def overclaimed(self) -> tuple[ClaimDrift, ...]:
        return tuple(f for f in self.findings if f.drift == DRIFT_OVERCLAIMED)

    def underclaimed(self) -> tuple[ClaimDrift, ...]:
        return tuple(f for f in self.findings if f.drift == DRIFT_UNDERCLAIMED)

    def unverifiable(self) -> tuple[ClaimDrift, ...]:
        return tuple(f for f in self.findings if f.drift == DRIFT_UNVERIFIABLE)

    def drifted(self) -> tuple[ClaimDrift, ...]:
        """Every row a human should review (any non-``none`` drift)."""
        return tuple(f for f in self.findings if f.flagged)

    @property
    def drift_counts(self) -> dict[str, int]:
        counts = {
            DRIFT_NONE: 0,
            DRIFT_OVERCLAIMED: 0,
            DRIFT_UNDERCLAIMED: 0,
            DRIFT_UNVERIFIABLE: 0,
        }
        for f in self.findings:
            counts[f.drift] = counts.get(f.drift, 0) + 1
        return counts

    def build_report(self) -> HarnessReport:
        """Assemble the advisory report — ``blocking=False`` by construction."""
        verdicts = [f.verdict for f in self.findings if f.verdict is not None]
        counts = self.drift_counts
        notes = (
            f"section={self.section_id}; entries={len(self.findings)}; "
            f"OVERCLAIMED={counts[DRIFT_OVERCLAIMED]} (hard: confirmed-not-grounded); "
            f"underclaimed={counts[DRIFT_UNDERCLAIMED]} (soft: inferred-fully-grounded); "
            f"unverifiable={counts[DRIFT_UNVERIFIABLE]}; "
            f"aligned={counts[DRIFT_NONE]}; "
            f"skipped_statuses={len(self.skipped_entry_keys)}; "
            f"e2_reused={self.e2_reused}. "
            "Advisory only — never a runtime gate (see harness/HARNESS.md)."
        )
        return build_report(
            STATUS_CALIBRATION_METRIC,
            verdicts,
            routing=self.routing,
            notes=notes,
            judge_model=self.judge_model,
            judge_version=self.judge_version,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_type": "claim_status_calibration_result",
            "metric": STATUS_CALIBRATION_METRIC,
            "section_id": self.section_id,
            "judge_model": self.judge_model,
            "judge_version": self.judge_version,
            "e2_reused": self.e2_reused,
            "drift_counts": self.drift_counts,
            "hard_finding_keys": [f.entry_key for f in self.overclaimed()],
            "underclaimed_keys": [f.entry_key for f in self.underclaimed()],
            "skipped_entry_keys": list(self.skipped_entry_keys),
            "findings": [f.to_dict() for f in self.findings],
        }


# --------------------------------------------------------------------------- #
# Evaluation
# --------------------------------------------------------------------------- #


def _drift_from_e2_finding(finding: Any) -> ClaimDrift:
    """Map one E2 confirmed-claim finding to its drift row."""
    if finding.severity == SEVERITY_INTEGRITY:
        drift = DRIFT_OVERCLAIMED
        reason = (
            "E2 hard integrity finding: the cited source does not support this "
            "confirmed claim (gap masked as confirmed)."
        )
    elif finding.severity == SEVERITY_UNRESOLVED:
        drift = DRIFT_UNVERIFIABLE
        reason = f"cannot verify the confirmed label: {finding.reason}"
    else:
        drift = DRIFT_NONE
        reason = "confirmed label consistent with its source (E2 bar met or soft)."
    return ClaimDrift(
        claim_id=finding.claim_id,
        entry_index=finding.entry_index,
        status=finding.status,
        drift=drift,
        verdict=finding.verdict,
        reason=reason,
    )


def evaluate_status_calibration(
    claims: Sequence[SectionClaim],
    judge: Judge,
    *,
    repo_root: Path,
    working_assumptions: WorkingAssumptions,
    section_id: str = "",
    e2_result: StatusFaithfulnessResult | None = None,
    n: int = 1,
    source_text_resolver: SourceTextResolver | None = None,
) -> StatusCalibrationResult:
    """Run status-calibration drift over a section's claims.

    **Confirmed direction** — reuses *e2_result* when supplied (zero extra
    judge calls; its ``integrity``/``unresolved`` findings map to
    overclaimed/unverifiable), else runs E2 internally over the ``confirmed``
    claims.  A supplied *e2_result* is cross-checked: one stamped for a
    *different* section raises :class:`StatusCalibrationError`, and any
    ``confirmed`` claim in *claims* it does not cover (e.g. it was produced
    with a ``claim_filter``) is surfaced as :data:`DRIFT_UNVERIFIABLE` — never
    silently dropped.  **Inferred direction** — judges each ``inferred`` claim
    against its resolved source under the confirmed-bar standard; clearing it
    is the soft ``underclaimed`` drift.  Claims of any other status are
    skipped and listed in ``skipped_entry_keys`` (visible, not silently
    dropped).
    """
    validate_sample_count(n)
    resolver = source_text_resolver or resolve_claim_source_text
    findings: list[ClaimDrift] = []
    routing: list[RoutingDecision] = []
    skipped: list[str] = []

    # --- confirmed direction (reuse E2 where supplied) --------------------- #
    if e2_result is None:
        internal = evaluate_status_aware_faithfulness(
            claims,
            judge,
            repo_root=repo_root,
            working_assumptions=working_assumptions,
            section_id=section_id,
            n=n,
            source_text_resolver=source_text_resolver,
            claim_filter=lambda c: c.status == STATUS_CONFIRMED,
        )
        confirmed_findings = internal.findings
        routing.extend(internal.routing)
        e2_reused = False
    else:
        if (
            e2_result.section_id
            and section_id
            and e2_result.section_id != section_id
        ):
            raise StatusCalibrationError(
                f"supplied e2_result is for section {e2_result.section_id!r} but "
                f"this calibration targets {section_id!r} — its confirmed-claim "
                f"verdicts do not apply."
            )
        confirmed_findings = tuple(
            f for f in e2_result.findings if f.status == STATUS_CONFIRMED
        )
        e2_reused = True
    findings.extend(_drift_from_e2_finding(f) for f in confirmed_findings)

    if e2_reused:
        # A supplied e2_result may not cover every confirmed claim we were
        # handed (it could have been run with a claim_filter).  Surface the
        # uncovered ones rather than silently dropping their drift rows.
        covered_keys = {f.entry_key for f in confirmed_findings}
        for claim in claims:
            if claim.status == STATUS_CONFIRMED and claim.entry_key not in covered_keys:
                findings.append(
                    ClaimDrift(
                        claim_id=claim.claim_id,
                        entry_index=claim.entry_index,
                        status=claim.status,
                        drift=DRIFT_UNVERIFIABLE,
                        reason=(
                            "supplied e2_result does not cover this confirmed "
                            "claim — re-run E2 over it (or omit e2_result) to "
                            "check its label."
                        ),
                    )
                )

    # --- inferred direction (the counterfactual confirmed-bar question) ---- #
    for claim in claims:
        if claim.status == STATUS_CONFIRMED:
            continue
        if claim.status != STATUS_INFERRED:
            skipped.append(claim.entry_key)
            continue
        routing.append(assert_judgeable(claim.entry_key))
        try:
            material = resolver(claim.source_ref, repo_root)
        except SourceResolutionError as exc:
            findings.append(
                ClaimDrift(
                    claim_id=claim.claim_id,
                    entry_index=claim.entry_index,
                    status=claim.status,
                    drift=DRIFT_UNVERIFIABLE,
                    reason=f"cannot check the inferred label: {exc}",
                )
            )
            continue
        system_prompt, user_prompt = build_faithfulness_prompt_for_status(
            STATUS_CONFIRMED,
            claim.claim_summary,
            material,
            comparison=COMPARISON_SOURCE,
            source_ref=claim.source_ref,
        )
        if n == 1:
            verdict: Verdict | MajorityVerdict = judge.evaluate(
                system_prompt,
                user_prompt,
                metric=STATUS_CALIBRATION_METRIC,
                property_key=claim.entry_key,
            ).verdict
        else:
            majority: MajorityJudgeResult = judge.evaluate_majority(
                system_prompt,
                user_prompt,
                metric=STATUS_CALIBRATION_METRIC,
                property_key=claim.entry_key,
                n=n,
            )
            verdict = majority.majority
        if classify_underclaimed(verdict, n=n):
            findings.append(
                ClaimDrift(
                    claim_id=claim.claim_id,
                    entry_index=claim.entry_index,
                    status=claim.status,
                    drift=DRIFT_UNDERCLAIMED,
                    verdict=verdict,
                    reason=(
                        "this inferred claim clears the confirmed bar — its source "
                        "directly supports it (mislabelled down; soft drift)."
                    ),
                )
            )
        else:
            findings.append(
                ClaimDrift(
                    claim_id=claim.claim_id,
                    entry_index=claim.entry_index,
                    status=claim.status,
                    drift=DRIFT_NONE,
                    verdict=verdict,
                    reason="inferred label consistent (does not clear the confirmed bar).",
                )
            )

    return StatusCalibrationResult(
        section_id=section_id,
        findings=tuple(findings),
        skipped_entry_keys=tuple(skipped),
        routing=tuple(routing),
        judge_model=judge.config.model,
        judge_version=judge.config.version,
        e2_reused=e2_reused,
    )
