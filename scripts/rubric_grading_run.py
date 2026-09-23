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
* **Per-cell checkpoint, resumable.**  Every completed (expectation, section)
  cell and the cross-expectation verdict cache are persisted after each cell
  (and on failure), so a daily-cap 429, a crash, or a Ctrl-C loses at most the
  cell in flight; re-running resumes without re-spending judge budget.  The
  checkpoint is run-local scratch (pickle; the durable records are the report,
  the baseline, and the provenance JSONL) and is keyed to the judge pin,
  rubric fingerprint, pack budget, and N — a mismatch refuses to resume
  rather than silently mixing runs (pass ``--fresh`` to discard).

Usage (judge config auto-loads from ``.env.harness``; run FROM THE REPO ROOT):

    py -3.10 scripts/rubric_grading_run.py --plan-only   # record the math
    py -3.10 scripts/rubric_grading_run.py               # grade (resumable)

Advisory artifact; never a runtime gate (``harness/HARNESS.md``).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import pickle
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for cand in (here.parent, *here.parents):
        if (cand / "harness").is_dir() and (cand / "runner").is_dir():
            return cand
    return here.parents[1] if len(here.parents) >= 2 else here.parent


_REPO_ROOT = _find_repo_root()
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Offline imports only at module scope: the budget plan and the grading loop
# are unit-tested with a fake judge, and importing this module must not load
# .env.harness or touch the transport.  The live path (main) imports the
# freeze-runner module lazily, which does both.
from runner.atomic_write import atomic_write_json  # noqa: E402
from runner.working_assumptions import (  # noqa: E402
    WorkingAssumptions,
    load_working_assumptions,
)
from harness.evidence_pack import (  # noqa: E402
    DEFAULT_PACK_TOKEN_BUDGET,
    DEFAULT_SPAN_BUDGET_FRACTION,
    RUBRIC_PROMPT_ALLOWANCE,
)
from harness.expectation_coverage import grade_expectation  # noqa: E402
from harness.expectation_grounding import (  # noqa: E402
    claim_content_key,
    derive_expectation_grounding,
)
from harness.expectations import section_paths_for  # noqa: E402
from harness.judge import DEFAULT_JUDGE_MAX_TOKENS, Judge  # noqa: E402
from harness.regression import (  # noqa: E402
    DEFAULT_RUBRIC_BASELINE_PATH,
    freeze_rubric_baseline,
)
from harness.rubric import (  # noqa: E402
    DEFAULT_PROVENANCE_PATH,
    DEFAULT_REPORT_PATH,
    ExpectationCell,
    SpineRegistry,
    build_rubric_report,
    combine_axes,
    load_spine_registry,
    render_report,
)
from harness.rubrics import RubricSet, build_pack_for, load_rubric_set  # noqa: E402
from harness.verdict import MIN_MAJORITY_SAMPLES  # noqa: E402

#: Where the pre-run budget accounting is written (harness-owned).
DEFAULT_BUDGET_PATH = Path("harness/rubric_reports/rubric_run_budget.json")

#: Run-local checkpoint (pickle scratch, retired on completion — the durable
#: records are the report, the baseline, and the provenance JSONL).
DEFAULT_CHECKPOINT_PATH = Path("harness/rubric_reports/rubric_run_checkpoint.pkl")

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
    section_kwargs: dict[str, Any] = {"repo_root": repo_root}
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
# Checkpoint — per-cell, resumable, keyed to the run parameters
# --------------------------------------------------------------------------- #


def run_meta(
    judge: Judge,
    rubric_set: RubricSet,
    *,
    token_budget: int,
    span_budget_fraction: float,
    n: int,
    sections_dir: str | None,
) -> dict[str, Any]:
    """The parameters a checkpoint is keyed to — a mismatch refuses to resume."""
    return {
        "judge_pin": f"{judge.config.model}@{judge.config.version}",
        "rubric_set_fingerprint": rubric_set.fingerprint,
        "token_budget": token_budget,
        "span_budget_fraction": span_budget_fraction,
        "n": n,
        "sections_dir": sections_dir,
    }


def save_checkpoint(path: Path, meta: Mapping[str, Any], cells: dict, cache: dict) -> None:
    """Persist the run state atomically (pickle scratch; same-code resume)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "wb") as fh:
        pickle.dump({"meta": dict(meta), "cells": cells, "verdict_cache": cache}, fh)
    os.replace(tmp, path)


def load_checkpoint(
    path: Path, meta: Mapping[str, Any], *, log: Callable[[str], None] = print
) -> tuple[dict, dict]:
    """Load the resumable state, fail-closed on any mismatch.

    An unreadable checkpoint or one written under different run parameters
    raises ``SystemExit`` telling the operator to pass ``--fresh`` — silently
    restarting would re-spend judge budget, silently mixing runs would
    aggregate grades across pins.
    """
    if not path.is_file():
        return {}, {}
    try:
        with open(path, "rb") as fh:
            state = pickle.load(fh)
    except Exception as exc:
        raise SystemExit(
            f"checkpoint {path} is unreadable ({type(exc).__name__}: {exc}) — "
            "likely written by different code. Re-run with --fresh to discard "
            "it (the already-spent verdicts survive only in provenance)."
        ) from exc
    if state.get("meta") != dict(meta):
        raise SystemExit(
            f"checkpoint {path} was written under different run parameters:\n"
            f"  checkpoint: {state.get('meta')}\n  current   : {dict(meta)}\n"
            "Refusing to mix runs. Re-run with the original parameters, or "
            "--fresh to discard the checkpoint."
        )
    cells, cache = state.get("cells", {}), state.get("verdict_cache", {})
    log(f"  resume: {len(cells)} cell(s) + {len(cache)} cached verdict(s) from {path.name}")
    return cells, cache


# --------------------------------------------------------------------------- #
# The grading loop — cell by cell, persisted after every cell
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
    tokens_spent: Callable[[], int] | None = None,
    tpd_stop: int = 0,
    log: Callable[[str], None] = print,
) -> tuple[ExpectationCell, ...]:
    """Grade every (expectation, section) cell, checkpointing after each.

    The semantic body of :func:`harness.rubric.grade_all` with E5f's run
    control around it: completed cells are skipped on resume, the shared
    verdict cache is persisted with them (so a resumed run re-spends nothing),
    and a configured *tpd_stop* raises :class:`BudgetStop` cleanly *between*
    cells once the measured spend reaches it.  On any failure the state
    gathered so far — including cache entries from a partially graded cell —
    is persisted before the error propagates.
    """
    wa = (
        working_assumptions
        if working_assumptions is not None
        else load_working_assumptions(repo_root)
    )
    meta = run_meta(
        judge,
        rubric_set,
        token_budget=token_budget,
        span_budget_fraction=span_budget_fraction,
        n=n,
        sections_dir=str(sections_dir) if sections_dir is not None else None,
    )
    cells, cache = load_checkpoint(checkpoint_path, meta, log=log)

    section_kwargs: dict[str, Any] = {"repo_root": repo_root}
    if sections_dir is not None:
        section_kwargs["sections_dir"] = sections_dir

    ordered_keys: list[str] = []
    try:
        for rubric in rubric_set.rubrics:
            for section_path in section_paths_for(rubric.criterion_id, **section_kwargs):
                key = _cell_key(rubric.expectation_key, section_path.stem)
                ordered_keys.append(key)
                if key in cells:
                    log(f"  skip  {key}: already graded (checkpoint)")
                    continue
                if tpd_stop and tokens_spent is not None and tokens_spent() >= tpd_stop:
                    raise BudgetStop(
                        f"measured spend {tokens_spent()} tokens reached the "
                        f"daily stop ({tpd_stop}) — pausing cleanly before {key}."
                    )
                t0 = time.monotonic()
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
                    verdict_cache=cache,
                )
                cells[key] = combine_axes(coverage, grounding, spine)
                save_checkpoint(checkpoint_path, meta, cells, cache)
                log(
                    f"  cell  {key}: cell={cells[key].cell} "
                    f"({(time.monotonic() - t0) / 60:.1f} min; checkpointed)"
                )
    except BaseException:
        # BaseException, not Exception: a Ctrl-C (KeyboardInterrupt) must also
        # persist whatever the in-flight cell contributed to the shared
        # verdict cache — a resume re-runs the cell but re-spends only the
        # unjudged part.
        save_checkpoint(checkpoint_path, meta, cells, cache)
        raise

    return tuple(cells[k] for k in ordered_keys)


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


def main(argv=None) -> int:
    """Exit codes: ``0`` clean grid; ``1`` grid frozen with contradiction(s)
    (advisory); ``2`` stopped on an error (checkpointed — re-run to resume);
    ``3`` paused cleanly on the daily budget stop (re-run after the reset)."""
    ap = argparse.ArgumentParser(
        description=(
            "E5f: first real E5 rubric-grid grading run — budget math recorded "
            "before the run, per-cell checkpoint, frozen report + E4 "
            "rubric-lane baseline. Advisory; never a runtime gate."
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
    ap.add_argument("--plan-only", action="store_true",
                    help="record the budget math and stop before any judge call")
    ap.add_argument("--fresh", action="store_true",
                    help="discard an existing checkpoint instead of resuming")
    ap.add_argument("--out", default=str(DEFAULT_REPORT_PATH))
    ap.add_argument("--baseline-out", default=str(DEFAULT_RUBRIC_BASELINE_PATH))
    ap.add_argument("--budget-out", default=str(DEFAULT_BUDGET_PATH))
    ap.add_argument("--checkpoint", default=str(DEFAULT_CHECKPOINT_PATH))
    ap.add_argument("--provenance", default=str(DEFAULT_PROVENANCE_PATH))
    args = ap.parse_args(argv)

    # The live-judge bootstrap: importing the freeze runner loads .env.harness
    # (override=True) before any transport/judge resolution, and provides the
    # paced/retrying backend wrapper.
    from scripts.freeze_grounding_baselines import build_paced_judge
    from harness.judge import resolve_judge_config

    repo_root = Path(args.repo_root).resolve()
    cfg = resolve_judge_config()  # fail-closed if the judge pin is unset

    rubric_set = load_rubric_set(
        repo_root / "harness/rubrics_msca_pf.json",
        registry_path=repo_root
        / "docs/tier2a_instrument_schemas/extracted/evaluator_expectation_registry.json",
        scorecard_path=repo_root / "harness/evaluator_scorecard_msca_pf.json",
    )
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
    )
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

    checkpoint_path = repo_root / args.checkpoint
    if args.fresh and checkpoint_path.is_file():
        checkpoint_path.unlink()
        print(f"discarded checkpoint {checkpoint_path.name} (--fresh)")

    judge, wrapper = build_paced_judge(
        cfg,
        tpm=args.tpm,
        rpm=args.rpm,
        max_retries=args.max_retries,
        prov_path=repo_root / args.provenance,
    )
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
            tokens_spent=lambda: wrapper.total_tokens,
            tpd_stop=args.tpd_stop,
        )
    except BudgetStop as exc:
        print(f"\nPAUSED: {exc}")
        print(f"  {_spent_line(wrapper)}")
        print(
            "  Progress is checkpointed. Re-run the same command after the "
            "daily reset to resume — completed cells and cached verdicts are "
            "never re-spent."
        )
        return 3
    except Exception as exc:
        print(f"\nSTOPPED: {type(exc).__name__}: {exc}")
        print(f"  {_spent_line(wrapper)}")
        print(
            "  Progress is checkpointed (completed cells + the verdict cache). "
            "If this is the Groq daily cap, wait for the reset and re-run the "
            "same command; it resumes without re-spending."
        )
        return 2

    report = build_rubric_report(
        cells,
        rubric_set=rubric_set,
        judge_model=cfg.model,
        judge_version=cfg.version,
        spine_source=spine.source_path,
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
            "measured over this invocation only; a resumed run's earlier "
            "spend is visible in the provenance JSONL"
        ),
    }
    baseline = freeze_rubric_baseline(
        data, budget_record={"plan": plan, "measured_this_invocation": measured}
    )
    baseline_path = repo_root / args.baseline_out
    atomic_write_json(baseline, baseline_path, prefix="rubric_baseline_")

    if checkpoint_path.is_file():
        checkpoint_path.unlink()
    print(f"\nfrozen report   -> {out_path}")
    print(f"frozen baseline -> {baseline_path} (budget accounting embedded)")
    print(_spent_line(wrapper))
    return 1 if report.contradictions else 0


if __name__ == "__main__":
    raise SystemExit(main())
