#!/usr/bin/env python3
"""
E5f — the first real E5 rubric-grid grading run under the judge budget.

Drives the E5a–E5e machinery (``harness.rubric``) over the three committed
Part B sections with the pinned, non-drafter judge, and produces the two E5f
artifacts:

* the frozen grid report (``harness/rubric_reports/rubric_report.json`` — the
  file the ``harness_rubric`` standing lane re-renders), and
* the E4 rubric-lane baseline
  (``harness/regression_baselines/rubric_grid.rubric.json``), frozen via
  :func:`harness.regression.freeze_rubric_baseline` with the budget accounting
  embedded — so a later prompt/model change can be diffed with
  ``py -3.10 -m harness.regression rubric-check``.

Reuses the ``freeze_grounding_baselines`` backend pattern: ``.env.harness``
auto-load, token-accurate TPM/RPM pacing, retry on the transport's own
retryable errors — plus what E5f adds on top:

* **Budget math recorded before the run.**  The full call/token plan (9
  expectations × mapped sections × N≥3, coverage + grounding, cross-pack
  claim dedup) is computed offline and written to
  ``harness/rubric_reports/rubric_run_budget.json`` *before* the first judge
  call.  If the plan does not fit one Groq free-tier day, the recorded plan is
  an explicit multi-day resume — never a silently reduced N or a shrunken
  pack.  ``--plan-only`` stops after this step.
* **Resume from the response checkpoint, bound to content (ticket 02).**
  Every raw judge draw is written to a JSONL response checkpoint
  (:mod:`harness.response_cache`) the moment it arrives, so a daily-cap 429, a
  crash or a Ctrl-C loses nothing already drawn.  A resume replays those draws
  through the same code: every cell is graded again, and the cells and the
  claim verdict cache are rebuilt in memory from the replayed responses; the
  run goes live from the first draw the checkpoint does not hold.  The
  checkpoint is bound to the candidate hash over the section artifacts in the
  grid (the formatting-invariant hash blind assessment uses), the judge pin,
  the rubric-set fingerprint, the profile version, the pack token budget, the
  span budget fraction, n and the judge's inference configuration.  A changed,
  added or removed section moves the candidate hash, so the resume is refused
  with every moved field named: a resume grades exactly the content the
  interrupted run graded, or it does not run.
* **Explicit checkpoint files.**  A new run writes a new numbered checkpoint
  (``.harness/rubric_checkpoints/checkpoint_<short>_<NNNN>.jsonl``, or the file
  ``--checkpoint`` names).  A resume names its file with ``--resume``.  An
  existing file is never opened without ``--resume``.  The checkpoint is kept
  after a completed run; the report and the baseline record the candidate hash
  and how many draws were replayed versus drawn live.

Usage (judge config auto-loads from ``.env.harness``; run FROM THE REPO ROOT):

    py -3.10 -m harness.commands.rubric_grading_run --plan-only   # record the math
    py -3.10 -m harness.commands.rubric_grading_run               # grade (new checkpoint)
    py -3.10 -m harness.commands.rubric_grading_run --resume <checkpoint.jsonl>

Advisory artifact; never a runtime gate (``harness/HARNESS.md``).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

# Offline imports only at module scope: the budget plan and the grading loop
# are unit-tested with a fake judge, and importing this module must not load
# .env.harness or touch the transport.  The live path (main) loads
# .env.harness explicitly and borrows the paced judge from the freeze runner.
from runner.atomic_write import atomic_write_json
from runner.working_assumptions import (
    WorkingAssumptions,
    load_working_assumptions,
)
from harness.content_hash import content_hash, short_hash
from harness.evidence_pack import (
    DEFAULT_PACK_TOKEN_BUDGET,
    DEFAULT_SPAN_BUDGET_FRACTION,
    RUBRIC_PROMPT_ALLOWANCE,
)
from harness.expectation_coverage import grade_expectation
from harness.expectation_grounding import (
    claim_content_key,
    derive_expectation_grounding,
)
from harness.expectations import section_paths_for
from harness.judge import DEFAULT_JUDGE_MAX_TOKENS, Judge
from harness.regression import (
    DEFAULT_RUBRIC_BASELINE_PATH,
    freeze_rubric_baseline,
)
from harness.rubric import (
    DEFAULT_PROVENANCE_PATH,
    DEFAULT_REPORT_PATH,
    ExpectationCell,
    SpineRegistry,
    build_rubric_report,
    combine_axes,
    load_spine_registry,
    render_report,
)
from harness.profile import PreEvaluationProfile
from harness.response_cache import (
    CacheBinding,
    ResponseCache,
    ResponseCacheError,
    next_checkpoint_path,
)
from harness.rubrics import RubricSet, build_pack_for, load_profile_bundle
from harness.verdict import MIN_MAJORITY_SAMPLES

#: Where the pre-run budget accounting is written (harness-owned).
DEFAULT_BUDGET_PATH = Path("harness/rubric_reports/rubric_run_budget.json")

#: Where a new run writes its response checkpoint when none is named, under
#: the repository root (gitignored runtime state, beside blind assessment's
#: ``.harness/checkpoints``).
DEFAULT_CHECKPOINT_DIR: str = ".harness/rubric_checkpoints"

#: Groq free-tier caps for llama-3.3-70b-versatile (the .env.harness judge).
GROQ_TPM, GROQ_RPM, GROQ_TPD, GROQ_RPD = 6000, 30, 100_000, 1000

#: Estimated completion tokens of one rubric verdict (short JSON; the ceiling
#: is the judge's max_tokens, recorded separately in the plan).
COVERAGE_COMPLETION_EST = 400

#: Measured mean total tokens of one E2 faithfulness call under this judge —
#: the E1.5 calibration run measured ~42 calls ≈ 86k tokens (~2050/call);
#: rounded up for headroom.
GROUNDING_TOKENS_PER_CALL_EST = 2100

#: The gate whose pass certifies the impact section is the post-showcase
#: (Opus-for-impact) artifact — the E5f "baseline nuance" check.
_GATE_10B_RESULT = Path(
    "docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/gate_10b_result.json"
)


class BudgetStop(Exception):
    """The measured spend reached the configured daily stop (clean pause)."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _cell_key(expectation_key: str, section_id: str) -> str:
    return f"{expectation_key}::{section_id}"


# --------------------------------------------------------------------------- #
# Budget math — computed offline, recorded before the first judge call
# --------------------------------------------------------------------------- #


def _gate_10b_note(repo_root: Path) -> dict[str, Any]:
    """Best-effort read of the gate_10b pass — the impact baseline nuance."""
    path = repo_root / _GATE_10B_RESULT
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        return {
            "gate_id": data.get("gate_id"),
            "status": data.get("status"),
            "run_id": data.get("run_id"),
            "evaluated_at": data.get("evaluated_at"),
        }
    except OSError:
        return {"status": "absent", "path": path.as_posix()}
    except json.JSONDecodeError:
        return {"status": "unreadable", "path": path.as_posix()}


def compute_budget_plan(
    rubric_set: RubricSet,
    *,
    repo_root: Path,
    sections_dir: Path | str | None = None,
    token_budget: int = DEFAULT_PACK_TOKEN_BUDGET,
    span_budget_fraction: float = DEFAULT_SPAN_BUDGET_FRACTION,
    n: int = MIN_MAJORITY_SAMPLES,
    tpm: int = GROQ_TPM,
    rpm: int = GROQ_RPM,
    tpd: int = GROQ_TPD,
    rpd: int = GROQ_RPD,
    judge_model: str | None = None,
    judge_version: str | None = None,
    judge_max_tokens: int = DEFAULT_JUDGE_MAX_TOKENS,
    profile: PreEvaluationProfile | None = None,
) -> dict[str, Any]:
    """The deterministic pre-run call/token plan — no judge, no network.

    Builds every evidence pack exactly as the grading run will (same budget,
    same span fraction), counts coverage calls (cells × *n*) and grounding
    calls (cross-pack *unique* claims × *n* — the shared verdict cache never
    judges the same content twice), and assesses the totals against the
    per-minute and per-day caps.  The honest outcome on the free tier may be
    a multi-day resume plan; the plan records that instead of shrinking
    anything.
    """
    section_kwargs: dict[str, Any] = {"repo_root": repo_root, "profile": profile}
    if sections_dir is not None:
        section_kwargs["sections_dir"] = sections_dir

    cells: list[dict[str, Any]] = []
    seen_claims: set[tuple[str, str, str]] = set()
    coverage_tokens = 0
    for rubric in rubric_set.rubrics:
        for section_path in section_paths_for(rubric.criterion_id, **section_kwargs):
            pack = build_pack_for(
                rubric,
                section_path,
                token_budget=token_budget,
                span_budget_fraction=span_budget_fraction,
            )
            new_keys = [
                claim_content_key(pc.claim)
                for pc in pack.claims
                if claim_content_key(pc.claim) not in seen_claims
            ]
            seen_claims.update(new_keys)
            per_call = pack.token_estimate + RUBRIC_PROMPT_ALLOWANCE + COVERAGE_COMPLETION_EST
            coverage_tokens += per_call * n
            cells.append(
                {
                    "expectation_key": rubric.expectation_key,
                    "criterion_id": rubric.criterion_id,
                    "section_id": section_path.stem,
                    "pack_status": pack.status,
                    "pack_token_estimate": pack.token_estimate,
                    "claims_in_pack": len(pack.claims),
                    "claims_excluded_over_budget": sum(
                        1 for e in pack.excluded if e.reason == "over_budget"
                    ),
                    "new_unique_claims": len(new_keys),
                    "coverage_calls": n,
                    "coverage_tokens_per_call_est": per_call,
                    "coverage_tokens_per_call_ceiling": (
                        token_budget + RUBRIC_PROMPT_ALLOWANCE + judge_max_tokens
                    ),
                    "grounding_calls_est": len(new_keys) * n,
                }
            )

    coverage_calls = sum(c["coverage_calls"] for c in cells)
    grounding_calls = sum(c["grounding_calls_est"] for c in cells)
    grounding_tokens = grounding_calls * GROUNDING_TOKENS_PER_CALL_EST
    total_calls = coverage_calls + grounding_calls
    total_tokens = coverage_tokens + grounding_tokens
    max_call_ceiling = max(
        (c["coverage_tokens_per_call_ceiling"] for c in cells), default=0
    )
    estimated_days = max(1, math.ceil(total_tokens / tpd)) if tpd else 1
    fits_one_day = total_tokens <= tpd and total_calls <= rpd

    notes = [
        "N and the pack budget are never reduced to fit the caps; if the plan "
        "exceeds one day, the recorded approach is an explicit multi-day "
        "resume from the per-cell checkpoint.",
        "grounding tokens/call is the measured mean of the E1.5 calibration "
        f"run under this judge (~{GROUNDING_TOKENS_PER_CALL_EST}); coverage "
        "tokens/call is the pack estimate plus the pinned prompt allowance "
        f"plus ~{COVERAGE_COMPLETION_EST} completion tokens.",
        "grounding calls are an upper bound: the shared verdict cache judges "
        "each unique (claim_summary, status, source_ref) once across the "
        "whole grid.",
        "the local Ollama judge path ($0, uncapped) is not available on this "
        "machine (no ollama install); the run uses the pinned Groq free-tier "
        "judge with pacing.",
        "on the committed sections, packs at the designed budget are expected "
        "insufficient_context (E5b measured 5-18k tokens of material per "
        "expectation): the truncation is EXPLICIT — pack_status travels on "
        "every grade, clean_pass is structurally forbidden over a truncated "
        "pack, and exclusions are itemized. Raising the pack ceiling requires "
        "an E5b MAX_PACK_TOKEN_BUDGET change (it is TPM-derived), out of E5f "
        "scope even under an uncapped judge.",
    ]

    return {
        "record_type": "rubric_run_budget",
        "computed_at": _utc_now(),
        "judge_model": judge_model,
        "judge_version": judge_version,
        "rubric_set_id": rubric_set.rubric_set_id,
        "rubric_set_version": rubric_set.version,
        "rubric_set_fingerprint": rubric_set.fingerprint,
        "n": n,
        "token_budget": token_budget,
        "span_budget_fraction": span_budget_fraction,
        "caps": {"tpm": tpm, "rpm": rpm, "tpd": tpd, "rpd": rpd},
        "impact_baseline_nuance": {
            "note": (
                "impact is graded against the post-showcase artifact; "
                "gate_10b_impact_completeness certifies the Opus-for-impact "
                "authoring landed"
            ),
            "gate_10b": _gate_10b_note(repo_root),
        },
        "cells": cells,
        "totals": {
            "cells": len(cells),
            "unique_claims": len(seen_claims),
            "coverage_calls": coverage_calls,
            "coverage_tokens_est": coverage_tokens,
            "grounding_calls_est": grounding_calls,
            "grounding_tokens_est": grounding_tokens,
            "calls_est": total_calls,
            "tokens_est": total_tokens,
        },
        "assessment": {
            "max_call_ceiling_fits_tpm": max_call_ceiling <= tpm,
            "max_call_ceiling": max_call_ceiling,
            "fits_one_day": fits_one_day,
            "estimated_days": estimated_days,
            "plan": "single_day" if fits_one_day else "multi_day_resume",
            "notes": notes,
        },
    }


# --------------------------------------------------------------------------- #
# Checkpoint binding — the content graded and the parameters it was graded under
# --------------------------------------------------------------------------- #


def _grid_section_paths(
    rubric_set: RubricSet,
    *,
    repo_root: Path,
    sections_dir: Path | str | None,
    profile: PreEvaluationProfile | None,
) -> tuple[Path, ...]:
    """Every section artifact the grid grades, once each, in grid order."""
    section_kwargs: dict[str, Any] = {"repo_root": repo_root, "profile": profile}
    if sections_dir is not None:
        section_kwargs["sections_dir"] = sections_dir
    seen: dict[Path, None] = {}
    for rubric in rubric_set.rubrics:
        for path in section_paths_for(rubric.criterion_id, **section_kwargs):
            seen.setdefault(path, None)
    return tuple(seen)


def grid_candidate_hash(
    rubric_set: RubricSet,
    *,
    repo_root: Path,
    sections_dir: Path | str | None = None,
    profile: PreEvaluationProfile | None = None,
) -> str:
    """The candidate hash over the section artifacts in the grid.

    The same formatting-invariant content hash blind assessment takes
    (:func:`harness.blind_assessment.candidate_hash`): the parsed artifacts
    keyed by section id.  Rewriting a section's content, or adding or removing
    a section from the grid, moves it.
    """
    contents: dict[str, Any] = {}
    for path in _grid_section_paths(
        rubric_set, repo_root=repo_root, sections_dir=sections_dir, profile=profile
    ):
        contents[path.stem] = json.loads(path.read_text(encoding="utf-8-sig"))
    return content_hash({sid: contents[sid] for sid in sorted(contents)})


def rubric_binding(
    judge: Judge,
    rubric_set: RubricSet,
    *,
    candidate_hash: str,
    profile_version: str,
    token_budget: int,
    span_budget_fraction: float,
    n: int,
) -> CacheBinding:
    """The binding a rubric grading run's checkpoint carries.

    The rubric fields of :class:`~harness.response_cache.CacheBinding` plus the
    shared ones a rubric run decides: the candidate hash, the judge pin (in the
    ``assessor_pin`` field), the profile version (empty when no profile is
    given), n and the judge's inference configuration.  The blind-only fields
    keep their defaults.
    """
    return CacheBinding(
        candidate_hash=candidate_hash,
        profile_version=profile_version,
        assessor_pin=f"{judge.config.model}@{judge.config.version}",
        n=n,
        temperature=judge.config.temperature,
        max_tokens=judge.config.max_tokens,
        rubric_set_fingerprint=rubric_set.fingerprint,
        pack_token_budget=token_budget,
        span_budget_fraction=span_budget_fraction,
    )


def default_checkpoint_path(repo_root: Path, candidate_hash: str) -> Path:
    """The next free numbered checkpoint under :data:`DEFAULT_CHECKPOINT_DIR`."""
    return next_checkpoint_path(Path(repo_root) / DEFAULT_CHECKPOINT_DIR, candidate_hash)


# --------------------------------------------------------------------------- #
# The grading loop — cell by cell, every draw checkpointed as it arrives
# --------------------------------------------------------------------------- #


def run_grading(
    judge: Judge,
    rubric_set: RubricSet,
    spine: SpineRegistry,
    *,
    repo_root: Path,
    sections_dir: Path | str | None = None,
    working_assumptions: WorkingAssumptions | None = None,
    token_budget: int = DEFAULT_PACK_TOKEN_BUDGET,
    span_budget_fraction: float = DEFAULT_SPAN_BUDGET_FRACTION,
    n: int = MIN_MAJORITY_SAMPLES,
    checkpoint_path: Path,
    resume: bool = False,
    tokens_spent: Callable[[], int] | None = None,
    tpd_stop: int = 0,
    log: Callable[[str], None] = print,
    profile: PreEvaluationProfile | None = None,
    profile_version: str = "",
) -> tuple[ExpectationCell, ...]:
    """Grade every (expectation, section) cell under a response checkpoint.

    The semantic body of :func:`harness.rubric.grade_all` with E5f's run
    control around it.  The checkpoint at *checkpoint_path* is opened before
    the first draw and attached to *judge*: a new one (``resume=False``; the
    file must not exist) records every draw as it arrives; a resumed one
    (``resume=True``) must carry this run's binding (see
    :func:`rubric_binding`; the candidate hash is
    :func:`grid_candidate_hash`) or
    :class:`~harness.response_cache.ResponseCacheError` names every field that
    moved.  On resume every cell is graded again through the same code; the
    draws the checkpoint holds are replayed, which rebuilds the cells and the
    claim verdict cache in memory, and the run goes live from the first draw
    it does not hold.

    A configured *tpd_stop* raises :class:`BudgetStop` cleanly *between* cells
    once the measured spend reaches it.  Replayed draws spend nothing, so a
    resume after a stop continues from the first draw it has not yet made.
    """
    wa = (
        working_assumptions
        if working_assumptions is not None
        else load_working_assumptions(repo_root)
    )
    binding = rubric_binding(
        judge,
        rubric_set,
        candidate_hash=grid_candidate_hash(
            rubric_set, repo_root=repo_root, sections_dir=sections_dir, profile=profile
        ),
        profile_version=profile_version,
        token_budget=token_budget,
        span_budget_fraction=span_budget_fraction,
        n=n,
    )
    checkpoint_path = Path(checkpoint_path)
    if not resume:
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint = ResponseCache(checkpoint_path, binding, resume=resume)
    judge.attach_response_cache(checkpoint)
    if resume:
        log(
            f"  resume: replaying {checkpoint.replayable} recorded draw(s) from "
            f"{checkpoint_path.name} before going live"
        )

    verdict_cache: dict = {}
    section_kwargs: dict[str, Any] = {"repo_root": repo_root, "profile": profile}
    if sections_dir is not None:
        section_kwargs["sections_dir"] = sections_dir

    cells: list[ExpectationCell] = []
    for rubric in rubric_set.rubrics:
        for section_path in section_paths_for(rubric.criterion_id, **section_kwargs):
            key = _cell_key(rubric.expectation_key, section_path.stem)
            if tpd_stop and tokens_spent is not None and tokens_spent() >= tpd_stop:
                raise BudgetStop(
                    f"measured spend {tokens_spent()} tokens reached the "
                    f"daily stop ({tpd_stop}) — pausing cleanly before {key}."
                )
            t0 = time.monotonic()
            live_before = checkpoint.live
            coverage = grade_expectation(
                judge,
                rubric,
                section_path,
                token_budget=token_budget,
                span_budget_fraction=span_budget_fraction,
                n=n,
            )
            grounding = derive_expectation_grounding(
                rubric,
                section_path,
                token_budget=token_budget,
                span_budget_fraction=span_budget_fraction,
                judge=judge,
                repo_root=repo_root,
                working_assumptions=wa,
                n=n,
                verdict_cache=verdict_cache,
            )
            cells.append(combine_axes(coverage, grounding, spine))
            log(
                f"  cell  {key}: cell={cells[-1].cell} "
                f"({checkpoint.live - live_before} live draw(s); "
                f"{(time.monotonic() - t0) / 60:.1f} min)"
            )
    return tuple(cells)


# --------------------------------------------------------------------------- #
# main — plan, grade, freeze
# --------------------------------------------------------------------------- #


def _env_int(name: str, default: int) -> int:
    v = os.environ.get(name)
    return int(v) if v else default


def _spent_line(wrapper) -> str:
    return (
        f"spent this invocation: {wrapper.calls} calls / "
        f"{wrapper.total_tokens:,} measured tokens (+{wrapper.retries} retries)"
    )


def build_parser() -> argparse.ArgumentParser:
    """The command line (offline; building it loads nothing)."""
    ap = argparse.ArgumentParser(
        description=(
            "E5f: first real E5 rubric-grid grading run — budget math recorded "
            "before the run, every judge draw checkpointed as it arrives, frozen "
            "report + E4 rubric-lane baseline. Advisory; never a runtime gate."
        )
    )
    ap.add_argument("--repo-root", default=os.environ.get("HARNESS_REPO_ROOT", "."))
    ap.add_argument("--sections", default=None,
                    help="override the sections dir (default: the E5a criterion map)")
    ap.add_argument("--budget", type=int, default=DEFAULT_PACK_TOKEN_BUDGET,
                    help="evidence-pack token budget per expectation")
    ap.add_argument("--span-fraction", type=float, default=DEFAULT_SPAN_BUDGET_FRACTION)
    ap.add_argument("--n", type=int, default=MIN_MAJORITY_SAMPLES,
                    help="judge samples per verdict (majority; N>=3 enforced downstream)")
    ap.add_argument("--tpm", type=int, default=_env_int("HARNESS_TPM_BUDGET", 5500),
                    help="tokens-per-minute pacing budget (headroom under the provider cap)")
    ap.add_argument("--rpm", type=int, default=_env_int("HARNESS_RPM_BUDGET", 28),
                    help="requests-per-minute pacing budget")
    ap.add_argument("--cap-tpm", type=int, default=GROQ_TPM,
                    help="the provider's hard TPM cap the plan is assessed against")
    ap.add_argument("--cap-rpm", type=int, default=GROQ_RPM)
    ap.add_argument("--cap-tpd", type=int, default=GROQ_TPD)
    ap.add_argument("--cap-rpd", type=int, default=GROQ_RPD)
    ap.add_argument("--max-retries", type=int, default=_env_int("HARNESS_MAX_RETRIES", 6))
    ap.add_argument("--tpd-stop", type=int, default=_env_int("HARNESS_TPD_STOP", 96_000),
                    help="pause cleanly once this many measured tokens are spent "
                         "in this invocation (0 disables; resume next day)")
    ap.add_argument("--profile", default=None,
                    help="pre-evaluation profile JSON (default: the harness default profile)")
    ap.add_argument("--plan-only", action="store_true",
                    help="record the budget math and stop before any judge call")
    ap.add_argument("--out", default=str(DEFAULT_REPORT_PATH))
    ap.add_argument("--baseline-out", default=str(DEFAULT_RUBRIC_BASELINE_PATH))
    ap.add_argument("--budget-out", default=str(DEFAULT_BUDGET_PATH))
    ap.add_argument("--provenance", default=str(DEFAULT_PROVENANCE_PATH))
    ckpt = ap.add_mutually_exclusive_group()
    ckpt.add_argument(
        "--checkpoint", default=None,
        help=(
            "where a new run checkpoints every raw judge draw as it arrives "
            f"(default: {DEFAULT_CHECKPOINT_DIR}/checkpoint_<short>_<NNNN>.jsonl "
            "under --repo-root, numbered after the candidate hash). An existing "
            "file is never opened without --resume"
        ),
    )
    ckpt.add_argument(
        "--resume", default=None,
        help=(
            "resume an earlier run from its checkpoint: every draw the file holds "
            "is replayed through the same code and the run goes live from the "
            "first draw it does not hold, appending to the same file. The "
            "binding - candidate hash over the graded sections, judge pin, rubric "
            "fingerprint, profile version, pack budget, span fraction, n - must "
            "equal this run's, or the resume is refused naming what moved"
        ),
    )
    return ap


def _resolve(repo_root: Path, path: str) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else repo_root / candidate


def main(argv=None) -> int:
    """Exit codes: ``0`` clean grid; ``1`` grid frozen with contradiction(s)
    (advisory); ``2`` stopped on an error or a refused checkpoint (every draw
    so far is checkpointed — ``--resume`` it); ``3`` paused cleanly on the
    daily budget stop (``--resume`` after the reset)."""
    args = build_parser().parse_args(argv)

    # The live-judge bootstrap: load .env.harness (override=True) before any
    # transport/judge resolution; the judge comes from the factory's paced,
    # retrying openai-compatible route.
    from harness.commands._common import load_harness_env
    from harness.judge import JudgeError, resolve_judge_config
    from harness.judge_factory import ROUTE_OPENAI_COMPATIBLE, build_judge

    load_harness_env()
    repo_root = Path(args.repo_root).resolve()
    cfg = resolve_judge_config()  # fail-closed if the judge pin is unset

    bundle = load_profile_bundle(args.profile, repo_root=repo_root)
    rubric_set = bundle.rubric_set
    wa = load_working_assumptions(repo_root)
    spine = load_spine_registry(repo_root, working_assumptions=wa)

    # The plan is assessed against the PROVIDER caps; the self-imposed pacing
    # values (--tpm/--rpm, deliberately under the caps) are recorded alongside.
    plan = compute_budget_plan(
        rubric_set,
        repo_root=repo_root,
        sections_dir=args.sections,
        token_budget=args.budget,
        span_budget_fraction=args.span_fraction,
        n=args.n,
        tpm=args.cap_tpm,
        rpm=args.cap_rpm,
        tpd=args.cap_tpd,
        rpd=args.cap_rpd,
        judge_model=cfg.model,
        judge_version=cfg.version,
        judge_max_tokens=cfg.max_tokens,
        profile=bundle.profile,
    )
    plan["profile"] = {"profile_id": bundle.profile_id, "profile_version": bundle.version}
    plan["pacing"] = {
        "tpm": args.tpm,
        "rpm": args.rpm,
        "max_retries": args.max_retries,
        "tpd_stop": args.tpd_stop,
    }
    gate = plan["impact_baseline_nuance"]["gate_10b"]
    if gate.get("status") != "pass":
        print(
            f"WARNING: gate_10b_impact_completeness is {gate.get('status')!r} — "
            "the impact section may predate the Opus-for-impact authoring; the "
            "frozen impact baseline would diff against a to-be-discarded "
            "version (the E5f baseline nuance)."
        )
    budget_path = repo_root / args.budget_out
    atomic_write_json(plan, budget_path, prefix="rubric_run_budget_")
    t, a = plan["totals"], plan["assessment"]
    print(f"judge : {cfg.model}@{cfg.version}")
    print(f"profile: {bundle.profile_id} [{short_hash(bundle.version, keep_prefix=True)}]")
    print(
        f"plan  : {t['cells']} cells, {t['unique_claims']} unique claims -> "
        f"~{t['calls_est']} calls / ~{t['tokens_est']:,} tokens "
        f"(coverage ~{t['coverage_tokens_est']:,} + grounding ~{t['grounding_tokens_est']:,})"
    )
    print(
        f"caps  : {plan['caps']['tpm']} TPM / {plan['caps']['rpm']} RPM / "
        f"{plan['caps']['tpd']:,} TPD / {plan['caps']['rpd']} RPD -> "
        f"{a['plan']} (~{a['estimated_days']} day(s))"
    )
    print(f"budget math recorded -> {budget_path}")
    if args.plan_only:
        return 0

    resume = args.resume is not None
    if resume:
        checkpoint_path = _resolve(repo_root, args.resume)
    elif args.checkpoint is not None:
        checkpoint_path = _resolve(repo_root, args.checkpoint)
    else:
        checkpoint_path = default_checkpoint_path(
            repo_root,
            grid_candidate_hash(
                rubric_set,
                repo_root=repo_root,
                sections_dir=args.sections,
                profile=bundle.profile,
            ),
        )

    try:
        judge, wrapper = build_judge(
            ROUTE_OPENAI_COMPATIBLE,
            cfg,
            tpm=args.tpm,
            rpm=args.rpm,
            max_retries=args.max_retries,
            prov_path=repo_root / args.provenance,
        )
    except JudgeError as exc:
        raise SystemExit(str(exc)) from exc
    print(
        f"pacing: <= {args.tpm} TPM / {args.rpm} RPM, retry x{args.max_retries}; "
        f"daily stop at {args.tpd_stop:,} measured tokens"
        if args.tpd_stop
        else "pacing: no daily stop configured"
    )

    try:
        cells = run_grading(
            judge,
            rubric_set,
            spine,
            repo_root=repo_root,
            sections_dir=args.sections,
            working_assumptions=wa,
            token_budget=args.budget,
            span_budget_fraction=args.span_fraction,
            n=args.n,
            checkpoint_path=checkpoint_path,
            resume=resume,
            tokens_spent=lambda: wrapper.total_tokens,
            tpd_stop=args.tpd_stop,
            profile=bundle.profile,
            profile_version=bundle.version,
        )
    except ResponseCacheError as exc:
        print(f"\nREFUSED: {exc}")
        return 2
    except BudgetStop as exc:
        print(f"\nPAUSED: {exc}")
        print(f"  {_spent_line(wrapper)}")
        print(
            "  Every draw so far is checkpointed. After the daily reset, re-run "
            f"the same command with --resume {checkpoint_path}; the recorded "
            "draws are replayed, never re-spent."
        )
        return 3
    except Exception as exc:
        print(f"\nSTOPPED: {type(exc).__name__}: {exc}")
        print(f"  {_spent_line(wrapper)}")
        print(
            "  Every draw so far is checkpointed. If this is the Groq daily cap, "
            "wait for the reset and re-run the same command with --resume "
            f"{checkpoint_path}; the recorded draws are replayed, never re-spent."
        )
        return 2

    checkpoint = judge.response_cache
    stats = checkpoint.stats()
    report = build_rubric_report(
        cells,
        rubric_set=rubric_set,
        profile=bundle,
        judge_model=cfg.model,
        judge_version=cfg.version,
        spine_source=spine.source_path,
        candidate_hash=checkpoint.binding.candidate_hash,
        replayed_calls=stats["replayed_calls"],
        live_calls=stats["live_calls"],
    )
    data = report.to_dict()
    print()
    print(render_report(data))

    out_path = repo_root / args.out
    atomic_write_json(data, out_path, prefix="rubric_report_")
    measured = {
        "calls": wrapper.calls,
        "retries": wrapper.retries,
        "measured_tokens": wrapper.total_tokens,
        "note": (
            "measured over this invocation only; draws replayed from a resumed "
            "checkpoint spend nothing and are counted in the report's "
            "replayed_calls, and their earlier spend is visible in the "
            "provenance JSONL"
        ),
    }
    baseline = freeze_rubric_baseline(
        data, budget_record={"plan": plan, "measured_this_invocation": measured}
    )
    baseline_path = repo_root / args.baseline_out
    atomic_write_json(baseline, baseline_path, prefix="rubric_baseline_")

    print(f"\nfrozen report   -> {out_path}")
    print(f"frozen baseline -> {baseline_path} (budget accounting embedded)")
    print(f"checkpoint kept -> {checkpoint_path}")
    print(_spent_line(wrapper))
    return 1 if report.contradictions else 0


if __name__ == "__main__":
    raise SystemExit(main())
