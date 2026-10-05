"""
The frozen blind baseline — one blind report, checked, copied and bound (spec PE-06).

Why this module exists
----------------------
The blind report is advisory and immutable on its own, but nothing marks
*which* report later stages read.  The integrity audit (PE-07) must show that
the snapshot id it ran over is the one the baseline stamped, and the ESR
comparison (PE-08) is built over "the frozen blind report".  Both need a single
durable record that names the report by content hash and carries every binding
the report declares.  That record is the freeze.

What a freeze checks, and refuses without
-----------------------------------------
A report is frozen only when all of the following hold.  Each is one named
check in :func:`check_baseline_report`; a failing check names itself, and the
freeze writes nothing.

* The report binds to the candidate hash, profile version and assessor pin
  (``load_report`` has already re-bound it to the candidate on disk).
* The evidence came through the dev-graph route: snapshot id, package id and
  policy version are present.  A directory-route report is never leakage-
  checked and cannot be a baseline.
* The evidence preflight is bound: pack-set hash and preflight report present,
  the preflight file readable, and its ``pack_set_hash`` equal to the one the
  report carries.  A preflight that cannot be re-read is a refusal, not a blank.
* The assessor pin names the transport.  ``assessor_transport`` is present and
  the version tag contains it (spec decision 10).
* Scope is complete.
* Cells are present, every one with an N>=3 panel and an agreement value.
* Criterion scores are present for every criterion, every one with a median
  and a spread from at least the default panel of five samples (spec decision
  11), and the total is determined.

What a freeze does not do
-------------------------
It does not re-run anything, does not change the report, and does not judge
the scores.  The spread it copies is **within-assessor repeatability** (spec
decision 11) and the record says so in the same words the report does.

The freeze is advisory and never a runtime gate (``harness/HARNESS.md``).
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from runner.atomic_write import atomic_write_json
from harness.blind_assessment import (
    BLIND_REPORT_RECORD_TYPE,
    EVIDENCE_SOURCE_DEV_GRAPH,
    SCOPE_COMPLETE,
    BlindAssessmentError,
    _utc_now,
    load_report,
)
from harness.criterion_scoring import DEFAULT_CRITERION_SAMPLES
from harness.evidence_preflight import file_sha256, load_preflight
from harness.profile import PreEvaluationProfile
from harness.verdict import MIN_MAJORITY_SAMPLES

__all__ = [
    "BASELINE_CHECKS",
    "BASELINE_FREEZE_RECORD_TYPE",
    "BASELINE_FREEZE_SCHEMA_VERSION",
    "BlindBaselineError",
    "FrozenBaseline",
    "check_baseline_report",
    "freeze_baseline",
    "load_frozen_baseline",
    "render_freeze",
]

BASELINE_FREEZE_RECORD_TYPE: str = "harness.blind_baseline_freeze"
BASELINE_FREEZE_SCHEMA_VERSION: str = "1.0.0"

#: Every named condition, in the order :func:`check_baseline_report` runs them.
#: The freeze record's ``checks_passed`` is derived as this set minus the
#: failures, so it cannot claim a check the function did not make.
BASELINE_CHECKS: tuple[str, ...] = (
    "record_type",
    "binding_fields",
    "evidence_source",
    "evidence_bindings",
    "preflight_binding",
    "preflight_rebound",
    "assessor_transport",
    "pin_names_transport",
    "scope",
    "cells_present",
    "cell_spreads",
    "criterion_scores_present",
    "criterion_spreads",
    "criterion_samples",
    "criterion_total",
)

#: File names under the baseline directory: the byte copy of the report and
#: the freeze record, both named by the report's content hash.
_COPY_NAME: str = "blind_baseline_{short}.json"
_FREEZE_NAME: str = "blind_baseline_{short}.freeze.json"
_FREEZE_GLOB: str = "*.freeze.json"
_SHORT_LEN: int = 12

_FREEZE_NOTE: str = (
    "Frozen blind baseline. Advisory to a human, never run-blocking. Later "
    "stages that claim to read the baseline read the report copy named here "
    "and check its sha256 against report_sha256; a stage whose snapshot id "
    "differs from bindings.snapshot_id has re-derived the baseline and must say "
    "so. Spreads are within-assessor repeatability only."
)


class BlindBaselineError(BlindAssessmentError):
    """The report cannot be frozen, or the frozen record is not what it claims."""


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# --------------------------------------------------------------------------- #
# The checks
# --------------------------------------------------------------------------- #


def _present(data: Mapping[str, Any], key: str) -> bool:
    value = data.get(key)
    return value is not None and str(value) != ""


def _resolve_preflight(report: Mapping[str, Any], repo_root: Path | str | None) -> Path | None:
    """The preflight file the report names, as given or under *repo_root*."""
    rel = str(report.get("preflight_report") or "")
    if not rel:
        return None
    candidates = [Path(rel)]
    if repo_root is not None:
        candidates.append(Path(repo_root) / rel)
    for p in candidates:
        if p.is_file():
            return p
    return None


def check_baseline_report(
    report: Mapping[str, Any], *, repo_root: Path | str | None = None
) -> tuple[tuple[str, str], ...]:
    """Return every failed check as ``(check_name, reason)``; empty means frozen-ready.

    Pure over the report dict except for one read: the preflight file the
    report names is loaded and its ``pack_set_hash`` compared with the report's
    (``preflight_rebound``).  The candidate re-binding is ``load_report``'s and
    is not repeated here.  Every name this function can emit is in
    :data:`BASELINE_CHECKS`.
    """
    failures: list[tuple[str, str]] = []

    def fail(name: str, reason: str) -> None:
        assert name in BASELINE_CHECKS, name
        failures.append((name, reason))

    if report.get("record_type") != BLIND_REPORT_RECORD_TYPE:
        fail("record_type", f"not a {BLIND_REPORT_RECORD_TYPE!r} record")
    for key in ("candidate_hash", "profile_version", "assessor_pin"):
        if not _present(report, key):
            fail("binding_fields", f"{key} is empty")
    if report.get("evidence_source") != EVIDENCE_SOURCE_DEV_GRAPH:
        fail(
            "evidence_source",
            f"evidence_source is {report.get('evidence_source')!r}; a baseline is built "
            "through the dev-graph route, which is the only one the leakage guard checks",
        )
    for key in ("snapshot_id", "package_id", "policy_version"):
        if not _present(report, key):
            fail("evidence_bindings", f"{key} is empty")
    for key in ("preflight_pack_set_hash", "preflight_report"):
        if not _present(report, key):
            fail("preflight_binding", f"{key} is empty")
    if _present(report, "preflight_report"):
        preflight_path = _resolve_preflight(report, repo_root)
        if preflight_path is None:
            fail(
                "preflight_rebound",
                f"the preflight report {report.get('preflight_report')!r} cannot be read; "
                "a baseline whose preflight is gone cannot be re-bound",
            )
        else:
            try:
                recorded = str(load_preflight(preflight_path).get("pack_set_hash") or "")
            except BlindAssessmentError as exc:
                fail("preflight_rebound", f"the preflight report is not loadable: {exc}")
            else:
                if recorded != str(report.get("preflight_pack_set_hash") or ""):
                    fail(
                        "preflight_rebound",
                        f"the preflight file carries pack_set_hash {recorded!r}, the report "
                        f"{report.get('preflight_pack_set_hash')!r}",
                    )

    transport = str(report.get("assessor_transport") or "")
    version = str(report.get("assessor_version") or "")
    if not transport:
        fail("assessor_transport", "assessor_transport is empty; the report does not say what it spoke")
    elif transport not in version:
        fail(
            "pin_names_transport",
            f"assessor_version {version!r} does not name the transport {transport!r} "
            "(spec decision 10)",
        )

    if report.get("scope") != SCOPE_COMPLETE:
        fail("scope", f"scope is {report.get('scope')!r}; a partial candidate is not a baseline")

    cells = report.get("cells")
    if not isinstance(cells, list) or not cells:
        fail("cells_present", "the report carries no cells")
    else:
        for i, cell in enumerate(cells):
            verdict = (cell.get("coverage") or {}).get("verdict") if isinstance(cell, Mapping) else None
            if not isinstance(verdict, Mapping):
                fail("cell_spreads", f"cells[{i}] carries no verdict")
                continue
            n = verdict.get("n")
            if not isinstance(n, int) or n < MIN_MAJORITY_SAMPLES:
                fail("cell_spreads", f"cells[{i}] panel n={n!r}, below {MIN_MAJORITY_SAMPLES}")
            if verdict.get("agreement") is None:
                fail("cell_spreads", f"cells[{i}] carries no agreement value")

    scoring = report.get("criterion_scoring")
    if not isinstance(scoring, Mapping):
        fail("criterion_scores_present", "the report carries no criterion_scoring stage")
    else:
        scores = scoring.get("scores")
        if not isinstance(scores, list) or not scores:
            fail("criterion_scores_present", "criterion_scoring carries no scores")
        else:
            for i, score in enumerate(scores):
                if not isinstance(score, Mapping):
                    fail("criterion_spreads", f"scores[{i}] is not an object")
                    continue
                cid = score.get("criterion_id", f"#{i}")
                if score.get("score") is None:
                    fail("criterion_spreads", f"criterion {cid} is not scored")
                if score.get("spread") is None:
                    fail("criterion_spreads", f"criterion {cid} carries no spread")
        if scoring.get("unscored_criteria"):
            fail(
                "criterion_scores_present",
                f"unscored criteria: {', '.join(map(str, scoring['unscored_criteria']))}",
            )
        samples = scoring.get("samples_per_criterion")
        if not isinstance(samples, int) or samples < DEFAULT_CRITERION_SAMPLES:
            fail(
                "criterion_samples",
                f"samples_per_criterion is {samples!r}, below the baseline panel of "
                f"{DEFAULT_CRITERION_SAMPLES} (spec decision 11)",
            )
        if scoring.get("total") is None:
            fail("criterion_total", "the total is undetermined")
    return tuple(failures)


# --------------------------------------------------------------------------- #
# The record
# --------------------------------------------------------------------------- #


def _cell_summary(cell: Mapping[str, Any]) -> dict[str, Any]:
    verdict = (cell.get("coverage") or {}).get("verdict") or {}
    members = verdict.get("members") or []
    scores: list[float] = [
        float(m["score"]) for m in members
        if isinstance(m, Mapping) and isinstance(m.get("score"), (int, float))
    ]
    return {
        "criterion_id": cell.get("criterion_id"),
        "expectation_key": cell.get("expectation_key"),
        "section_id": cell.get("section_id"),
        "addressal": cell.get("addressal"),
        "grounding": cell.get("grounding"),
        "clean_pass": cell.get("clean_pass"),
        "score": cell.get("score"),
        "n": verdict.get("n"),
        "agreement": verdict.get("agreement"),
        "score_spread": (round(max(scores) - min(scores), 4) if len(scores) >= 2 else None),
    }


def _criterion_summary(score: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "criterion_id": score.get("criterion_id"),
        "score": score.get("score"),
        "spread": score.get("spread"),
        "threshold": score.get("threshold"),
        "threshold_met": score.get("threshold_met"),
        "weighted_points": score.get("weighted_points"),
        "input_hash": score.get("input_hash"),
        "shortcomings": score.get("shortcomings"),
    }


_BINDING_KEYS: tuple[str, ...] = (
    "candidate_hash",
    "candidate_path",
    "profile_id",
    "profile_version",
    "assessor_model",
    "assessor_version",
    "assessor_pin",
    "assessor_transport",
    "snapshot_id",
    "package_id",
    "policy_version",
    "evidence_view",
    "evidence_source",
    "preflight_pack_set_hash",
    "preflight_report",
    "rubric_set_id",
    "rubric_set_version",
    "rubric_set_fingerprint",
    "scorecard_id",
    "scorecard_version",
    "include_claims",
    "intake_id",
    "esr_availability",
    "assessed_at",
    "assessor_invocation",
)


@dataclass(frozen=True)
class FrozenBaseline:
    """The freeze record and the paths it was written to."""

    record: dict[str, Any]
    freeze_path: Path
    copy_path: Path


def _build_record(
    report: Mapping[str, Any],
    *,
    report_path: str,
    report_sha256: str,
    copy_name: str,
    preflight_sha256: str,
    frozen_at: str,
) -> dict[str, Any]:
    scoring = report.get("criterion_scoring") or {}
    return {
        "record_type": BASELINE_FREEZE_RECORD_TYPE,
        "schema_version": BASELINE_FREEZE_SCHEMA_VERSION,
        "advisory": True,
        "blocking": False,
        "frozen_at": frozen_at,
        "report_path": report_path,
        "report_sha256": report_sha256,
        "report_copy": copy_name,
        "bindings": {key: report.get(key) for key in _BINDING_KEYS},
        "preflight_report_sha256": preflight_sha256,
        # Derived, not declared: a check is listed only because it ran and did
        # not fail.  An empty failure list is the only way to reach this point.
        "checks_passed": list(BASELINE_CHECKS),
        "cells": [_cell_summary(c) for c in report.get("cells", [])],
        "criterion_scores": [_criterion_summary(s) for s in scoring.get("scores", [])],
        "criterion_total": {
            "formula": scoring.get("formula"),
            "total": scoring.get("total"),
            "overall_max": scoring.get("overall_max"),
            "overall_threshold": scoring.get("overall_threshold"),
            "overall_threshold_met": scoring.get("overall_threshold_met"),
            "samples_per_criterion": scoring.get("samples_per_criterion"),
        },
        "spread_label": scoring.get("spread_label"),
        "summary": report.get("summary"),
        "notes": _FREEZE_NOTE,
    }


def freeze_baseline(
    report_path: Path | str,
    candidate_dir: Path | str,
    profile: PreEvaluationProfile,
    *,
    baseline_dir: Path | str,
    profile_version: str | None = None,
    repo_root: Path | str | None = None,
    clock: Callable[[], str] | None = None,
) -> FrozenBaseline:
    """Check *report_path*, copy it under *baseline_dir* and write the freeze record.

    Raises :class:`BlindBaselineError` when any check fails or when
    *baseline_dir* already holds a freeze: a frozen baseline is not replaced,
    a second baseline goes in another directory.  Nothing is written on
    refusal.
    """
    path = Path(report_path)
    data = load_report(path, candidate_dir, profile, profile_version=profile_version)
    failures = check_baseline_report(data, repo_root=repo_root)
    if failures:
        lines = "; ".join(f"{name}: {reason}" for name, reason in failures)
        raise BlindBaselineError(f"report {path} cannot be frozen as a baseline: {lines}")

    target = Path(baseline_dir)
    existing = sorted(target.glob(_FREEZE_GLOB)) if target.is_dir() else []
    if existing:
        raise BlindBaselineError(
            f"{target} already holds a frozen baseline ({existing[0].name}); a frozen "
            "baseline is never replaced. Freeze a second baseline into another directory."
        )

    digest = _sha256_bytes(path.read_bytes())
    short = digest[:_SHORT_LEN]
    copy_path = target / _COPY_NAME.format(short=short)
    freeze_path = target / _FREEZE_NAME.format(short=short)
    if copy_path.exists() or freeze_path.exists():
        raise BlindBaselineError(f"{copy_path} or {freeze_path} already exists; nothing overwritten.")

    # check_baseline_report has already established the file exists and re-binds.
    preflight_path = _resolve_preflight(data, repo_root)
    assert preflight_path is not None
    record = _build_record(
        data,
        report_path=_portable(path, repo_root),
        report_sha256=digest,
        copy_name=copy_path.name,
        preflight_sha256=file_sha256(preflight_path),
        frozen_at=(clock or _utc_now)(),
    )
    target.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(path, copy_path)
    atomic_write_json(record, freeze_path)
    return FrozenBaseline(record=record, freeze_path=freeze_path, copy_path=copy_path)


def _portable(path: Path, repo_root: Path | str | None) -> str:
    """*path* relative to *repo_root* when it lies under it, else as given."""
    if repo_root is not None:
        try:
            return path.resolve().relative_to(Path(repo_root).resolve()).as_posix()
        except ValueError:
            pass
    return path.as_posix()


def load_frozen_baseline(baseline_dir: Path | str) -> FrozenBaseline:
    """Load the one freeze under *baseline_dir* and check the copy's hash.

    Later stages read the baseline through this so a copy edited after the
    freeze is refused rather than read.
    """
    target = Path(baseline_dir)
    freezes = sorted(target.glob(_FREEZE_GLOB)) if target.is_dir() else []
    if not freezes:
        raise BlindBaselineError(f"{target} holds no frozen baseline.")
    if len(freezes) > 1:
        raise BlindBaselineError(
            f"{target} holds {len(freezes)} freeze records; a baseline directory holds one."
        )
    freeze_path = freezes[0]
    try:
        record = json.loads(freeze_path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise BlindBaselineError(f"{freeze_path} is not valid JSON: {exc}") from exc
    if not isinstance(record, Mapping) or record.get("record_type") != BASELINE_FREEZE_RECORD_TYPE:
        raise BlindBaselineError(f"{freeze_path} is not a {BASELINE_FREEZE_RECORD_TYPE!r} record.")
    if record.get("advisory") is not True or record.get("blocking") is not False:
        raise BlindBaselineError(f"{freeze_path} must carry advisory=true and blocking=false.")
    copy_name = str(record.get("report_copy") or "")
    if not re.fullmatch(r"blind_baseline_[0-9a-f]{%d}\.json" % _SHORT_LEN, copy_name):
        raise BlindBaselineError(f"{freeze_path} names an unexpected report copy {copy_name!r}.")
    copy_path = target / copy_name
    if not copy_path.is_file():
        raise BlindBaselineError(f"the frozen report copy {copy_path} is missing.")
    actual = file_sha256(copy_path)
    if actual != record.get("report_sha256"):
        raise BlindBaselineError(
            f"the frozen report copy {copy_path} hashes to {actual}, the freeze says "
            f"{record.get('report_sha256')}; the baseline was edited after it was frozen."
        )
    return FrozenBaseline(record=dict(record), freeze_path=freeze_path, copy_path=copy_path)


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #


def render_freeze(record: Mapping[str, Any]) -> str:
    """One screen of text: what was frozen and what it is bound to."""
    b = record.get("bindings") or {}
    lines = [
        f"FROZEN BLIND BASELINE  {record.get('report_copy')}",
        f"report sha256: {record.get('report_sha256')}",
        f"frozen at:     {record.get('frozen_at')}",
        f"candidate:     {str(b.get('candidate_hash') or '')[:19]}",
        f"profile:       {b.get('profile_id')} [{str(b.get('profile_version') or '')[:19]}]",
        f"assessor:      {b.get('assessor_pin')}  transport={b.get('assessor_transport')}",
        f"snapshot:      {str(b.get('snapshot_id') or '')[:19]}  package={str(b.get('package_id') or '')[:19]}",
        f"preflight:     pack set {str(b.get('preflight_pack_set_hash') or '')[:19]}  {b.get('preflight_report')}",
        f"cells:         {len(record.get('cells') or [])}  "
        f"criterion scores: {len(record.get('criterion_scores') or [])}",
    ]
    total = record.get("criterion_total") or {}
    if total.get("total") is not None:
        lines.append(
            f"total:         {total.get('formula')} = {total.get('total')} / {total.get('overall_max')}"
        )
    for s in record.get("criterion_scores") or []:
        lines.append(
            f"  - {s.get('criterion_id')}: {s.get('score')} (spread {s.get('spread')})"
        )
    lines.append(f"spread label:  {record.get('spread_label')}")
    return "\n".join(lines)
