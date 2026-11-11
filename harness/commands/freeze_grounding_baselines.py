#!/usr/bin/env python3
"""
Resilient E4 judge-lane grounding-baseline freeze — safe on a rate-limited judge.

Freezes the *judge half* of the E4 regression golden-set: runs E2 status-aware
faithfulness over each committed Part B section under the pinned, non-drafter
judge and writes one ``<section_id>.grounding.json`` baseline next to the
deterministic ``*.golden.json`` fingerprints (``harness/regression_baselines/``).

Why this exists instead of a one-liner
--------------------------------------
``harness.regression``'s CLI only freezes the DETERMINISTIC lane.  The judge
lane (``freeze_section_grounding``) is a Python function, and on a rate-limited
judge — Groq free tier for ``llama-3.3-70b-versatile`` is 30 RPM / 6,000 TPM /
1,000 RPD — a naive ~400-call burst trips the per-minute token cap.  The
transport marks a 429 ``retryable`` (``runner/transport/errors.py``) but nothing
acts on it, and E2's per-claim loop is out of reach of any outer pacing.  So
this runner asks the judge factory (:mod:`harness.judge_factory`) for the
``openai-compatible`` route, whose backend wrapper (the one place every judge
call passes through):

  * paces every judge call under a TPM/RPM budget, using the backend's REAL
    ``last_usage`` token counts (not an estimate), and
  * retries the provider's own ``retryable`` errors (429 / 500 / 502 / 503 /
    timeout) with exponential backoff, honouring a "try again in Ns" hint when
    the provider sends one,

then freezes SECTION-BY-SECTION with resume: a section already frozen under the
current judge pin is skipped on re-run, so a stall costs one section, never the
whole run — and a run that bumps the daily request ceiling can simply be re-run
later to finish.

Advisory artifact; never a runtime gate (``harness/HARNESS.md``).  The baseline
is keyed to the judge pin it was frozen under (``FaithfulnessBaseline.applies_to``);
a repin re-opens advisory, mirroring E1.5 — so choose a ``HARNESS_JUDGE_VERSION``
you intend to keep, and freeze + later ``check`` under the same pin.

Usage (Groq free tier, run FROM THE REPO ROOT)
----------------------------------------------
    ORCHESTRATOR_TRANSPORT_PRESET=GENERIC_OPENAI_COMPATIBLE \
    ORCHESTRATOR_TRANSPORT_ENDPOINT=https://api.groq.com/openai/v1 \
    ORCHESTRATOR_TRANSPORT_API_KEY=<groq-key> \
    ORCHESTRATOR_TRANSPORT_MODEL=llama-3.3-70b-versatile \
    HARNESS_JUDGE_MODEL=llama-3.3-70b-versatile \
    HARNESS_JUDGE_VERSION=groq-llama-3.3-70b@2026-08-03 \
    py -3.10 -m harness.commands.freeze_grounding_baselines

    # MEASURE FIRST (recommended): freeze the smallest section alone, read the
    # measured tokens/call it prints, confirm the full ~406-claim run fits caps:
    py -3.10 -m harness.commands.freeze_grounding_baselines --only implementation

Local judge alternative (no limits, no pacing needed — the cost-policy path):
    ORCHESTRATOR_TRANSPORT_PRESET=OLLAMA_LOCAL ORCHESTRATOR_TRANSPORT_MODEL=<id> \
    HARNESS_JUDGE_MODEL=<id> HARNESS_JUDGE_VERSION=<pin> \
    py -3.10 -m harness.commands.freeze_grounding_baselines --tpm 1000000 --rpm 100000 --n 3

All flags have env fallbacks: --n, --tpm, --rpm, --max-retries, --only,
--repo-root, --sections, --out, --refreeze.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

from harness.commands._common import load_harness_env
from harness.judge import JudgeError, resolve_judge_config
from harness.judge_factory import ROUTE_OPENAI_COMPATIBLE, build_judge
from harness.regression import (
    DEFAULT_GOLDEN_DIR,
    DEFAULT_SECTIONS_DIR,
    freeze_section_grounding,
)
from harness.status_faithfulness import load_baseline, write_baseline
from runner.working_assumptions import load_working_assumptions

#: Suffix for the judge-lane baseline — distinct from the deterministic
#: ``*.golden.json`` so ``harness.regression``'s ``load_golden_set`` never reads it.
GROUNDING_SUFFIX = ".grounding.json"


def _env_int(name: str, default: int) -> int:
    v = os.environ.get(name)
    return int(v) if v else default


def main(argv=None) -> int:
    load_harness_env()
    ap = argparse.ArgumentParser(
        description="Freeze E4 judge-lane grounding baselines (resilient / rate-limit-safe)."
    )
    ap.add_argument("--repo-root", default=os.environ.get("HARNESS_REPO_ROOT", "."))
    ap.add_argument("--sections", default=None,
                    help="dir of section JSONs (default: docs/tier5_deliverables/proposal_sections)")
    ap.add_argument("--out", default=None,
                    help="output dir (default: harness/regression_baselines)")
    ap.add_argument("--n", type=int, default=_env_int("HARNESS_GROUNDING_N", 1),
                    help="judge samples per claim: 1, or >=3 for majority. Default 1 "
                         "(n=3 x ~406 claims > Groq free RPD 1000).")
    ap.add_argument("--tpm", type=int, default=_env_int("HARNESS_TPM_BUDGET", 5500),
                    help="tokens-per-minute pacing budget (headroom under the cap; Groq free = 6000).")
    ap.add_argument("--rpm", type=int, default=_env_int("HARNESS_RPM_BUDGET", 28),
                    help="requests-per-minute pacing budget (Groq free = 30).")
    ap.add_argument("--max-retries", type=int, default=_env_int("HARNESS_MAX_RETRIES", 6))
    ap.add_argument("--only", default=os.environ.get("HARNESS_ONLY_SECTION"),
                    help="freeze only sections whose filename contains this substring.")
    ap.add_argument("--refreeze", action="store_true",
                    help="ignore existing baselines and re-freeze every section.")
    args = ap.parse_args(argv)

    if args.n == 2 or args.n < 1:
        raise SystemExit("--n must be 1 or >=3 (E2 routes n>=3 through majority; n=2 is invalid).")

    repo_root = Path(args.repo_root).resolve()
    sections_dir = Path(args.sections) if args.sections else repo_root / DEFAULT_SECTIONS_DIR
    out_dir = Path(args.out) if args.out else repo_root / DEFAULT_GOLDEN_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    cfg = resolve_judge_config()   # fail-closed if HARNESS_JUDGE_MODEL / _VERSION unset
    wa = load_working_assumptions(repo_root)
    try:
        judge, wrapper = build_judge(
            ROUTE_OPENAI_COMPATIBLE,
            cfg,
            tpm=args.tpm,
            rpm=args.rpm,
            max_retries=args.max_retries,
            prov_path=out_dir / "provenance_grounding_freeze.jsonl",
        )
    except JudgeError as exc:
        raise SystemExit(str(exc)) from exc

    sections = sorted(sections_dir.glob("*.json"))
    if args.only:
        sections = [s for s in sections if args.only in s.name]
    if not sections:
        print(
            f"no section JSONs to freeze in {sections_dir}"
            + (f" matching {args.only!r}" if args.only else ""),
            file=sys.stderr,
        )
        return 2

    print(f"judge : {cfg.model}@{cfg.version}")
    print(f"pacing: <= {args.tpm} TPM / {args.rpm} RPM, retry x{args.max_retries} on 429/5xx/timeout")
    print(f"plan  : {len(sections)} section(s), n={args.n}")
    if args.n >= 3:
        print(f"  ! n={args.n}: ~{args.n}x the claim count in calls — may exceed Groq free "
              "RPD 1000; prefer n=1 on the free tier, or use a local judge.")

    froze, skipped, failed = [], [], []
    for sp in sections:
        out = out_dir / f"{sp.stem}{GROUNDING_SUFFIX}"
        if out.exists() and not args.refreeze:
            try:
                existing = load_baseline(out)
                if existing.applies_to(cfg.model, cfg.version):
                    print(f"skip  {sp.stem}: baseline already present for this judge pin ({out.name})")
                    skipped.append(sp.stem)
                    continue
                print(f"stale {sp.stem}: existing baseline was frozen under a different judge pin — re-freezing")
            except Exception as exc:  # unreadable/old baseline: re-freeze rather than trust it
                print(f"warn  {sp.stem}: could not load existing baseline ({exc}); re-freezing")

        t0 = time.monotonic()
        c0, r0 = wrapper.calls, wrapper.retries
        try:
            baseline = freeze_section_grounding(
                sp,
                judge,
                repo_root=repo_root,
                working_assumptions=wa,
                baseline_id=f"grounding:{sp.stem}",
                n=args.n,
            )
        except Exception as exc:
            # A section that exhausts retries (or any other error) must not kill
            # the whole run: keep completed sections, report, allow a resume re-run.
            print(f"FAIL  {sp.stem}: {type(exc).__name__}: {exc}")
            print("        other sections continue; re-run to retry this one "
                  "(completed sections are skipped).")
            failed.append(sp.stem)
            continue

        write_baseline(baseline, out)
        dt = time.monotonic() - t0
        print(
            f"froze {sp.stem}: {len(baseline.snapshots)} claim snapshots in {dt / 60:.1f} min, "
            f"{wrapper.calls - c0} calls (+{wrapper.retries - r0} retries) -> {out.name}"
        )
        froze.append(sp.stem)

    print("\nsummary")
    print(f"  froze   : {froze or '-'}")
    print(f"  skipped : {skipped or '-'}")
    print(f"  failed  : {failed or '-'}")
    print(f"  judge calls: {wrapper.calls}  retries: {wrapper.retries}  "
          f"measured tokens: {wrapper.total_tokens:,}")
    if wrapper.calls:
        print(f"  observed mean: {wrapper.total_tokens / wrapper.calls:.0f} tokens/call "
              "(use this to confirm the full run fits your RPD/TPM headroom)")
    if failed:
        print("\n  -> re-run the same command to retry the failed section(s); the "
              "frozen ones are skipped automatically.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())