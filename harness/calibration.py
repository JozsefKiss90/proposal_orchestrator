"""
Judge-reliability calibration — the advisory→gating mechanism (E1.5).

The guardrails say the harness is *"advisory to a human, not auto-blocking,
until judge reliability is characterized."*  Without a mechanism, that clause has
no teeth and the harness is advisory forever.  This module is the mechanism: it
measures the pinned judge's precision/recall on a **human-labeled** faithfulness
gold set, records ``{judge_model, judge_version, precision, recall}``, and turns
that into a graduation decision — until a *fresh, applicable, above-threshold*
calibration exists, every metric stays CI-advisory (human-decided).

Two properties make it fail-safe:

* **Repin re-opens advisory-only.**  A calibration is valid only for the exact
  ``{judge_model, judge_version}`` it was measured on.  Change either and the
  stored calibration no longer applies — :func:`graduation_for` returns advisory
  until the new pin is re-characterized.
* **Undefined ⇒ not graduated.**  A precision/recall that can't be computed (no
  positive predictions, empty class) is treated as *not* meeting the bar, never
  as a pass.

The confusion matrix takes the **positive class = "supported"** (the judge's
``passed=True``).  In that frame a false positive — judge blesses a claim its
source does not support — is the integrity-critical error (a "gap masked as
confirmed" the judge failed to catch), so ``precision`` (of the supported
verdict) is the number that most directly bounds how often the judge blesses a
gap.  Both ``precision`` and ``recall`` are reported and thresholded, per the
ticket.

Constitutional authority:
    Subordinate to CLAUDE.md.  Out-of-band QA substrate; never a runtime gate —
    graduation permits a *human* to gate a merge, it does not itself block one.
    See ``harness/HARNESS.md``.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

from harness.faithfulness import judge_pair_supported
from harness.gold_set import GoldSet, gold_set_hash
from harness.jsonl_log import JsonlLog
from harness.judge import Judge, JudgeConfig
from harness.provenance import ProvenanceLog

__all__ = [
    "GRADUATION_ADVISORY",
    "GRADUATION_GATING_PERMITTED",
    "DEFAULT_GRADUATION_THRESHOLD",
    "CalibrationError",
    "ConfusionMatrix",
    "GraduationThreshold",
    "CalibrationReport",
    "GraduationDecision",
    "confusion_from_labels",
    "calibrate",
    "calibrate_with_judge",
    "graduation_for",
    "CalibrationLog",
]

#: Graduation statuses.  Advisory is the fail-safe default.
GRADUATION_ADVISORY: str = "advisory"
GRADUATION_GATING_PERMITTED: str = "gating_permitted"


class CalibrationError(Exception):
    """Calibration could not be computed (misaligned inputs, non-boolean verdict)."""


def _default_clock() -> str:
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------- #
# Confusion matrix (positive class = "supported")
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class ConfusionMatrix:
    """Counts for the judge's ``supported`` verdict vs the human label.

    Positive class = ``supported`` (judge ``passed=True``).

    * ``tp`` — judge supported,   human supported.
    * ``fp`` — judge supported,   human UNsupported  → **blessed a gap** (critical).
    * ``fn`` — judge UNsupported, human supported     → over-flag (safe).
    * ``tn`` — judge UNsupported, human UNsupported   → correctly caught a gap.
    """

    tp: int
    fp: int
    tn: int
    fn: int

    @property
    def total(self) -> int:
        return self.tp + self.fp + self.tn + self.fn

    @property
    def precision(self) -> float | None:
        """TP / (TP+FP) — trust in a ``supported`` verdict.  ``None`` if undefined."""
        denom = self.tp + self.fp
        return self.tp / denom if denom else None

    @property
    def recall(self) -> float | None:
        """TP / (TP+FN) — coverage of truly-supported claims.  ``None`` if undefined."""
        denom = self.tp + self.fn
        return self.tp / denom if denom else None

    @property
    def f1(self) -> float | None:
        p, r = self.precision, self.recall
        if p is None or r is None or (p + r) == 0:
            return None
        return 2 * p * r / (p + r)

    @property
    def accuracy(self) -> float | None:
        return (self.tp + self.tn) / self.total if self.total else None

    @property
    def gap_detection_recall(self) -> float | None:
        """TN / (TN+FP) — of truly-unsupported claims, the fraction the judge caught."""
        denom = self.tn + self.fp
        return self.tn / denom if denom else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "tp": self.tp,
            "fp": self.fp,
            "tn": self.tn,
            "fn": self.fn,
            "total": self.total,
            "precision": self.precision,
            "recall": self.recall,
            "f1": self.f1,
            "accuracy": self.accuracy,
            "gap_detection_recall": self.gap_detection_recall,
        }


def confusion_from_labels(
    truth: Sequence[bool], pred: Sequence[bool]
) -> ConfusionMatrix:
    """Build a :class:`ConfusionMatrix` from aligned human labels and judge predictions.

    Both sequences are ``supported`` booleans (positive class ``True``) and must
    be the same length.
    """
    if len(truth) != len(pred):
        raise CalibrationError(
            f"truth ({len(truth)}) and pred ({len(pred)}) lengths differ."
        )
    tp = fp = tn = fn = 0
    for t, p in zip(truth, pred):
        if p and t:
            tp += 1
        elif p and not t:
            fp += 1
        elif not p and t:
            fn += 1
        else:
            tn += 1
    return ConfusionMatrix(tp=tp, fp=fp, tn=tn, fn=fn)


# --------------------------------------------------------------------------- #
# Graduation threshold
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class GraduationThreshold:
    """The bar a judge must clear before a metric may graduate advisory→gating.

    ``min_precision`` and ``min_recall`` are the ticket's precision/recall bar.
    The values are **operator policy**, not physics — pick them from the cost of
    a blessed gap vs an over-flag on your artifacts.  :data:`DEFAULT_GRADUATION_THRESHOLD`
    is a deliberately conservative starting point, not an endorsement.
    """

    min_precision: float
    min_recall: float

    def __post_init__(self) -> None:
        for name, v in (("min_precision", self.min_precision), ("min_recall", self.min_recall)):
            if not (0.0 <= float(v) <= 1.0):
                raise ValueError(f"{name} must lie in [0.0, 1.0]; got {v!r}.")

    def to_dict(self) -> dict[str, float]:
        return {"min_precision": self.min_precision, "min_recall": self.min_recall}


#: Conservative starting bar — the operator MUST review this against their own
#: cost model before relying on it to gate merges.
DEFAULT_GRADUATION_THRESHOLD: GraduationThreshold = GraduationThreshold(
    min_precision=0.90, min_recall=0.80
)


# --------------------------------------------------------------------------- #
# Calibration report
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class CalibrationReport:
    """The record of one calibration run, keyed by the exact pinned judge.

    Carries the ticket's required provenance ``{judge_model, judge_version,
    precision, recall}`` at top level, plus the confusion matrix, the gold-set
    identity/hash, the threshold, and the graduation verdict.
    """

    judge_model: str
    judge_version: str
    precision: float | None
    recall: float | None
    confusion: ConfusionMatrix
    gold_set_id: str
    gold_set_hash: str
    n_pairs: int
    threshold: GraduationThreshold
    graduated: bool
    timestamp: str | None = None

    def meets(self, threshold: GraduationThreshold | None = None) -> bool:
        """Whether this run clears *threshold* (defaults to the run's own).

        Fail-safe: an undefined precision/recall never meets the bar.
        """
        thr = threshold or self.threshold
        if self.precision is None or self.recall is None:
            return False
        return self.precision >= thr.min_precision and self.recall >= thr.min_recall

    def applies_to(self, config: JudgeConfig) -> bool:
        """Whether this calibration applies to *config*'s exact model+version.

        A repin (model or version change) makes it stale — the graduation it
        supports no longer holds.
        """
        return (
            self.judge_model == config.model
            and self.judge_version == config.version
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_type": "judge_calibration",
            "judge_model": self.judge_model,
            "judge_version": self.judge_version,
            "precision": self.precision,
            "recall": self.recall,
            "graduated": self.graduated,
            "threshold": self.threshold.to_dict(),
            "gold_set_id": self.gold_set_id,
            "gold_set_hash": self.gold_set_hash,
            "n_pairs": self.n_pairs,
            "confusion": self.confusion.to_dict(),
            "timestamp": self.timestamp,
        }


# --------------------------------------------------------------------------- #
# calibrate
# --------------------------------------------------------------------------- #


def calibrate(
    gold_set: GoldSet,
    predictions: Sequence[bool],
    *,
    judge_model: str,
    judge_version: str,
    threshold: GraduationThreshold = DEFAULT_GRADUATION_THRESHOLD,
    clock: Callable[[], str] | None = None,
) -> CalibrationReport:
    """Compute a :class:`CalibrationReport` from a labeled gold set + judge predictions.

    Pure: no judge invocation.  *predictions* are the judge's ``supported``
    booleans aligned to ``gold_set``'s pairs (in order).  The gold set must be
    fully human-labeled (:meth:`GoldSet.require_fully_labeled`); an unlabeled set
    raises before any measurement.
    """
    gold_set.require_fully_labeled()
    truth = [bool(p.supported) for p in gold_set.pairs]
    if len(predictions) != len(truth):
        raise CalibrationError(
            f"predictions ({len(predictions)}) must align to the {len(truth)} "
            f"labeled gold pairs."
        )
    confusion = confusion_from_labels(truth, [bool(x) for x in predictions])
    report = CalibrationReport(
        judge_model=judge_model,
        judge_version=judge_version,
        precision=confusion.precision,
        recall=confusion.recall,
        confusion=confusion,
        gold_set_id=gold_set.gold_set_id,
        gold_set_hash=gold_set_hash(gold_set),
        n_pairs=len(truth),
        threshold=threshold,
        graduated=False,  # replaced below
        timestamp=(clock or _default_clock)(),
    )
    # Recompute graduated against the report's threshold now that metrics exist.
    return _with_graduated(report)


def _with_graduated(report: CalibrationReport) -> CalibrationReport:
    return replace(report, graduated=report.meets(report.threshold))


def calibrate_with_judge(
    gold_set: GoldSet,
    judge: Judge,
    *,
    threshold: GraduationThreshold = DEFAULT_GRADUATION_THRESHOLD,
    repo_root: Path | None = None,
    provenance_log: ProvenanceLog | None = None,
    clock: Callable[[], str] | None = None,
) -> tuple[CalibrationReport, list]:
    """Run *judge* over every labeled gold pair and calibrate it.

    Returns ``(report, judge_results)``.  Each per-pair faithfulness verdict is a
    real ``Inferred`` judge call (logged to *provenance_log* if attached), so the
    calibration's evidence is itself auditable.  A verdict that does not answer
    the boolean faithfulness question (``passed is None``) raises
    :class:`CalibrationError` — the judge must give a yes/no, never a shrug.
    """
    gold_set.require_fully_labeled()
    results = []
    predictions: list[bool] = []
    for pair in gold_set.pairs:
        result = judge_pair_supported(judge, pair, repo_root=repo_root)
        if provenance_log is not None:
            provenance_log.append(result.provenance)
        if result.verdict.passed is None:
            raise CalibrationError(
                f"gold pair {pair.pair_id!r}: judge returned no boolean "
                f"'supported' verdict (passed is None); cannot calibrate."
            )
        results.append(result)
        predictions.append(bool(result.verdict.passed))

    report = calibrate(
        gold_set,
        predictions,
        judge_model=judge.config.model,
        judge_version=judge.config.version,
        threshold=threshold,
        clock=clock,
    )
    return report, results


# --------------------------------------------------------------------------- #
# Graduation decision (the advisory→gating switch)
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class GraduationDecision:
    """Whether a metric may graduate from advisory to (human-)gating.

    ``status`` is :data:`GRADUATION_ADVISORY` or
    :data:`GRADUATION_GATING_PERMITTED`.  Advisory is the fail-safe default: no
    calibration, a stale (repinned) calibration, or a below-threshold one all
    yield advisory.  Even ``gating_permitted`` only clears a **human** to gate a
    merge — nothing here blocks a run.
    """

    status: str
    reason: str
    applies: bool
    report: CalibrationReport | None

    @property
    def gating_permitted(self) -> bool:
        return self.status == GRADUATION_GATING_PERMITTED


def graduation_for(
    config: JudgeConfig,
    report: CalibrationReport | None,
    *,
    threshold: GraduationThreshold | None = None,
) -> GraduationDecision:
    """Decide the graduation status for *config* given the latest *report*.

    Fail-safe cascade:
      1. No report                       → advisory.
      2. Report does not apply to *config* (a model/version repin) → advisory.
      3. Report applies but misses the bar → advisory.
      4. Report applies and clears the bar → gating permitted.
    """
    if report is None:
        return GraduationDecision(
            status=GRADUATION_ADVISORY,
            reason="no calibration on record for this judge",
            applies=False,
            report=None,
        )
    if not report.applies_to(config):
        return GraduationDecision(
            status=GRADUATION_ADVISORY,
            reason=(
                f"calibration is for {report.judge_model}@{report.judge_version} "
                f"but the current judge is {config.model}@{config.version} "
                f"(a repin re-opens the advisory-only state)"
            ),
            applies=False,
            report=report,
        )
    thr = threshold or report.threshold
    if report.meets(thr):
        return GraduationDecision(
            status=GRADUATION_GATING_PERMITTED,
            reason=(
                f"judge cleared the bar (precision={report.precision}, "
                f"recall={report.recall} ≥ {thr.to_dict()})"
            ),
            applies=True,
            report=report,
        )
    return GraduationDecision(
        status=GRADUATION_ADVISORY,
        reason=(
            f"judge below the bar (precision={report.precision}, "
            f"recall={report.recall} < {thr.to_dict()})"
        ),
        applies=True,
        report=report,
    )


# --------------------------------------------------------------------------- #
# Calibration log (history across repins)
# --------------------------------------------------------------------------- #


class CalibrationLog(JsonlLog):
    """Append-only JSONL history of :class:`CalibrationReport` — one line per run.

    A :class:`~harness.jsonl_log.JsonlLog` that keeps every calibration (across
    repins) so the graduation status for the *current* judge is a lookup by its
    model+version.  Out-of-band; nothing in :mod:`runner` reads it.
    """

    def __init__(self, path: Path | str) -> None:
        super().__init__(path, prefix="calibration_")

    def append(self, report: CalibrationReport) -> None:
        """Append one calibration report and atomically rewrite the log."""
        self.append_dict(report.to_dict())

    def latest_for(self, model: str, version: str) -> dict[str, Any] | None:
        """Return the most recent recorded run matching *model* + *version*, or ``None``."""
        for rec in reversed(self._records):
            if rec.get("judge_model") == model and rec.get("judge_version") == version:
                return rec
        return None
