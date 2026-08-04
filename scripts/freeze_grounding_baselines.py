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
this runner injects a single choke-point backend wrapper (the one place every
judge call passes through) that:

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
    py -3.10 scripts/freeze_grounding_baselines.py

    # MEASURE FIRST (recommended): freeze the smallest section alone, read the
    # measured tokens/call it prints, confirm the full ~406-claim run fits caps:
    py -3.10 scripts/freeze_grounding_baselines.py --only implementation

Local judge alternative (no limits, no pacing needed — the cost-policy path):
    ORCHESTRATOR_TRANSPORT_PRESET=OLLAMA_LOCAL ORCHESTRATOR_TRANSPORT_MODEL=<id> \
    HARNESS_JUDGE_MODEL=<id> HARNESS_JUDGE_VERSION=<pin> \
    py -3.10 scripts/freeze_grounding_baselines.py --tpm 1000000 --rpm 100000 --n 3

All flags have env fallbacks: --n, --tpm, --rpm, --max-retries, --only,
--repo-root, --sections, --out, --refreeze.
"""
from __future__ import annotations

import argparse
import dataclasses
import os
import re
import sys
import time
from collections import deque
from pathlib import Path


def _find_repo_root() -> Path:
    """Return the repo root — the nearest ancestor holding both ``harness/`` and
    ``runner/``.  Falls back to the parent of this script's dir."""
    here = Path(__file__).resolve()
    for cand in (here.parent, *here.parents):
        if (cand / "harness").is_dir() and (cand / "runner").is_dir():
            return cand
    return here.parents[1] if len(here.parents) >= 2 else here.parent


#: The repo root, put on ``sys.path`` so ``harness`` / ``runner`` import however
#: the script is launched (``py scripts/...`` otherwise only sees *scripts/*).
_REPO_ROOT = _find_repo_root()
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _load_harness_env() -> None:
    """Load a dedicated ``.env.harness`` (if present), overriding the pipeline's
    ``.env`` for judge/transport keys only.

    ``HARNESS_COST_POLICY.md`` intends the judge config to live apart from the
    pipeline's ``.env`` (which points at the Bedrock/Claude drafter transport).
    ``runner.transport.config`` loads ``.env`` at import with ``override=False``;
    loading ``.env.harness`` here with ``override=True`` *before* that import
    makes the harness file win, so ``HARNESS_JUDGE_*`` and the Groq
    ``ORCHESTRATOR_TRANSPORT_*`` need never be exported by hand.  Absent file or
    absent python-dotenv: harmless no-op (fall back to real env vars).
    """
    try:
        from dotenv import load_dotenv
    except Exception:
        return
    for name in (".env.harness", ".env.judge"):
        p = _REPO_ROOT / name
        if p.is_file():
            load_dotenv(p, override=True)
            return


_load_harness_env()

from harness.judge import Judge, resolve_judge_config
from harness.provenance import ProvenanceLog
from harness.regression import (
    DEFAULT_GOLDEN_DIR,
    DEFAULT_SECTIONS_DIR,
    freeze_section_grounding,
)
from harness.status_faithfulness import load_baseline, write_baseline
from runner.transport.config import build_openai_backend, resolve_provider_config
from runner.transport.errors import OpenAICompatTransportError
from runner.working_assumptions import load_working_assumptions

#: Suffix for the judge-lane baseline — distinct from the deterministic
#: ``*.golden.json`` so ``harness.regression``'s ``load_golden_set`` never reads it.
GROUNDING_SUFFIX = ".grounding.json"

#: Cold-start token estimate before any real usage is observed. Faithfulness
#: calls carry a source excerpt, so they are not tiny — bias high to be safe.
_COLD_ESTIMATE_TOKENS = 3000

#: Parse a provider "please try again in 8.5s" hint out of a 429 body, if present.
_RETRY_AFTER_RE = re.compile(r"try again in\s*([0-9.]+)\s*s", re.IGNORECASE)


class PacedRetryingBackend:
    """Injected backend wrapper: token-accurate pacing + retry on retryable errors.

    Conforms to the ``ToolLoopBackend`` shape (``messages -> {"content", ...}``)
    and delegates to *inner* (a real ``OpenAICompatBackend``).  It is the single
    point every judge call passes through, which is the only place per-call
    pacing is reachable — E2's per-claim loop is internal to
    ``evaluate_status_aware_faithfulness`` and cannot be paced from outside.
    """

    def __init__(
        self,
        inner,
        *,
        tpm_budget,
        rpm_budget,
        max_retries,
        base_delay=8.0,
        max_delay=90.0,
        log=print,
    ) -> None:
        self._inner = inner
        self._tpm = float(tpm_budget)
        self._min_interval = 60.0 / float(rpm_budget) if rpm_budget else 0.0
        self._max_retries = int(max_retries)
        self._base = float(base_delay)
        self._max = float(max_delay)
        self._log = log
        self._window: deque = deque()   # (monotonic_ts, total_tokens) within the last 60s
        self._recent: deque = deque(maxlen=8)
        self._last_ts = 0.0
        # counters for the run summary
        self.calls = 0
        self.retries = 0
        self.total_tokens = 0

    # -- token-aware pacing --------------------------------------------- #
    def _evict(self, now: float) -> None:
        while self._window and now - self._window[0][0] >= 60.0:
            self._window.popleft()

    def _tokens_in_window(self) -> int:
        return sum(t for _, t in self._window)

    def _estimate_next(self) -> int:
        return max(self._recent) if self._recent else _COLD_ESTIMATE_TOKENS

    def _pace(self) -> None:
        # (1) RPM floor — cheap request spacing.
        if self._min_interval:
            gap = self._min_interval - (time.monotonic() - self._last_ts)
            if gap > 0:
                time.sleep(gap)
        # (2) TPM sliding window — wait until the projected next call fits the budget.
        while self._window:
            now = time.monotonic()
            self._evict(now)
            if not self._window:
                break
            if self._tokens_in_window() + self._estimate_next() <= self._tpm:
                break
            sleep_for = 60.0 - (now - self._window[0][0]) + 0.1
            self._log(
                f"    pacing: {self._tokens_in_window()} tok in the 60s window; "
                f"waiting {sleep_for:.1f}s for TPM headroom"
            )
            time.sleep(max(sleep_for, 0.1))

    # -- backend protocol ----------------------------------------------- #
    def __call__(self, messages):
        delay = self._base
        for attempt in range(self._max_retries + 1):
            self._pace()
            try:
                result = self._inner(messages)
            except OpenAICompatTransportError as exc:
                # Use the transport's OWN retryability flag (verified: 429/5xx/
                # timeout => retryable=True; 400/401/403/404 => False).
                if not getattr(exc, "retryable", False) or attempt >= self._max_retries:
                    raise
                self.retries += 1
                wait = self._retry_after(exc, delay)
                self._log(
                    f"    {getattr(exc.category, 'value', 'error')} "
                    f"(attempt {attempt + 1}/{self._max_retries}) — waiting {wait:.0f}s then retrying"
                )
                time.sleep(wait)
                delay = min(delay * 2, self._max)
                continue
            # success — record REAL usage so pacing tracks actual tokens.
            self._last_ts = time.monotonic()
            usage = getattr(self._inner, "last_usage", None)
            tok = (
                int(usage["total_tokens"])
                if usage and usage.get("total_tokens")
                else self._estimate_next()
            )
            self._window.append((self._last_ts, tok))
            self._recent.append(tok)
            self.calls += 1
            self.total_tokens += tok
            return result
        raise RuntimeError("unreachable: retry loop exited without returning or raising")

    def _retry_after(self, exc, fallback: float) -> float:
        body = getattr(exc, "response_body", "") or ""
        m = _RETRY_AFTER_RE.search(body)
        if m:
            try:
                return min(max(float(m.group(1)) + 0.5, 1.0), self._max)
            except ValueError:
                pass
        return fallback


def build_paced_judge(cfg, *, tpm, rpm, max_retries, prov_path, log=print):
    """Build a :class:`Judge` whose backend is the pacing+retry wrapper.

    Mirrors ``Judge._get_backend`` (resolve provider, reject the ``claude_cli``
    drafter transport, pin the judge model), then wraps the real backend before
    handing it to the judge — so the model-level non-drafter guard
    (``JudgeConfig``) AND the transport-independence check both still hold.
    """
    provider = resolve_provider_config()
    if provider.backend_name == "claude_cli":
        raise SystemExit(
            "transport resolves to 'claude_cli' (the drafter transport). Point "
            "ORCHESTRATOR_TRANSPORT_* at the non-drafter OpenAI-compatible judge "
            "(e.g. the Groq preset) for grader-generator independence."
        )
    provider = dataclasses.replace(provider, model=cfg.model)
    inner = build_openai_backend(
        provider, temperature=cfg.temperature, max_tokens=cfg.max_tokens
    )
    wrapper = PacedRetryingBackend(
        inner, tpm_budget=tpm, rpm_budget=rpm, max_retries=max_retries, log=log
    )
    judge = Judge(cfg, backend=wrapper, provenance_log=ProvenanceLog(prov_path))
    return judge, wrapper


def _env_int(name: str, default: int) -> int:
    v = os.environ.get(name)
    return int(v) if v else default


def main(argv=None) -> int:
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
    judge, wrapper = build_paced_judge(
        cfg,
        tpm=args.tpm,
        rpm=args.rpm,
        max_retries=args.max_retries,
        prov_path=out_dir / "provenance_grounding_freeze.jsonl",
    )

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