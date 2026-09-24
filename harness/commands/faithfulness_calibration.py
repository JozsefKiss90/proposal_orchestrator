#!/usr/bin/env python3
"""
E1.5 faithfulness-calibration runner (turnkey, resumable) — "run the first calibration".

Loads the human-labeled gold set, runs the pinned non-drafter judge over every
pair through the freeze runner's paced/retry backend (so ~42 calls don't trip
Groq's 6k tokens/min limit), computes precision/recall, applies the graduation
threshold, and writes a decision-log DRAFT.

Robust by construction (learned from the v1 loss of a full run to one flaky JSON
on the last pair):
  * **Per-pair checkpoint.** Predictions are persisted after every pair to
    `harness/gold_sets/faithfulness_calibration_checkpoint.json`. A crash, a
    daily-cap (TPD) 429, or a Ctrl-C loses nothing — re-run and it resumes,
    judging only the pairs it hasn't done (cheap on a fresh quota).
  * **Malformed-JSON salvage.** Groq's Llama occasionally emits a valid decision
    in slightly-invalid JSON (e.g. a doubled closing quote). The harness parser
    rejects it (no silent repair — correct for the runtime judge). Here, for
    *calibration*, we read the judge's explicit `"passed": true|false` out of the
    rejected response and log it as salvaged — we measure the judge's decision,
    not its JSON hygiene. A pair with no recoverable verdict after retries is
    EXCLUDED (logged), never allowed to abort the run.

Run FROM THE REPO ROOT, on a fresh Groq daily quota (~42 calls ≈ 86k of 100k/day;
if it stops on the daily cap, re-run to resume):

    py -3.10 -m harness.commands.faithfulness_calibration

Judge config comes from `.env.harness` (auto-loaded). Advisory; never a runtime gate.
"""
from __future__ import annotations

import dataclasses
import datetime
import json
import os
import re
from pathlib import Path

from harness.calibration import calibrate, graduation_for
from harness.commands._common import REPO_ROOT as _ROOT
from harness.commands._common import load_harness_env
from harness.commands.freeze_grounding_baselines import PacedRetryingBackend
from harness.faithfulness import judge_pair_supported
from harness.gold_set import GoldSet, gold_set_hash, load_gold_set
from harness.judge import Judge, JudgeResponseError, resolve_judge_config
from harness.provenance import ProvenanceLog
from runner.transport.config import build_openai_backend, resolve_provider_config

GOLD = "harness/gold_sets/faithfulness_gold_excellence.jsonl"
CKPT = "harness/gold_sets/faithfulness_calibration_checkpoint.json"
PROV = "harness/gold_sets/provenance_faithfulness_calibration.jsonl"

#: The judge's decision is a clear "passed": true|false even when the JSON envelope glitches.
_PASSED_RE = re.compile(r'"passed"\s*:\s*(true|false)', re.IGNORECASE)


def _paced_judge(cfg, *, tpm, rpm, max_retries):
    provider = resolve_provider_config()
    if provider.backend_name == "claude_cli":
        raise SystemExit(
            "transport resolves to 'claude_cli' (the drafter transport). Point "
            "ORCHESTRATOR_TRANSPORT_* in .env.harness at the non-drafter Groq judge."
        )
    provider = dataclasses.replace(provider, model=cfg.model)
    inner = build_openai_backend(provider, temperature=cfg.temperature, max_tokens=cfg.max_tokens)
    return Judge(cfg, backend=PacedRetryingBackend(inner, tpm_budget=tpm, rpm_budget=rpm, max_retries=max_retries))


def _env_int(name, default):
    v = os.environ.get(name)
    return int(v) if v else default


def _load_ckpt(path: Path, pin: str) -> dict:
    fresh = {"judge_pin": pin, "pred": {}, "salvaged": [], "excluded": []}
    if not path.is_file():
        return fresh
    try:
        prev = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fresh
    if prev.get("judge_pin") != pin:
        print("  checkpoint is for a different judge pin — starting fresh")
        return fresh
    print(f"  resume: {len(prev.get('pred', {}))} pair(s) already judged for this judge pin")
    for k in ("pred", "salvaged", "excluded"):
        prev.setdefault(k, {} if k == "pred" else [])
    return prev


def _run(gs, judge, ckpt_path: Path, prov: ProvenanceLog, retries: int):
    """Judge every not-yet-checkpointed pair; salvage/retry on parse misses; persist per pair."""
    pin = f"{judge.config.model}@{judge.config.version}"
    ck = _load_ckpt(ckpt_path, pin)
    pred_by_id: dict = dict(ck["pred"])
    salvaged: list = list(ck["salvaged"])
    excluded: list = list(ck["excluded"])

    def persist():
        ckpt_path.write_text(
            json.dumps({"judge_pin": pin, "pred": pred_by_id, "salvaged": salvaged, "excluded": excluded},
                       ensure_ascii=False, indent=2), encoding="utf-8")

    for pair in gs.pairs:
        if pair.pair_id in pred_by_id or pair.pair_id in excluded:
            continue
        pred = None
        salv = False
        for attempt in range(retries + 1):
            try:
                res = judge_pair_supported(judge, pair, repo_root=_ROOT)
                if res.verdict.passed is None:
                    raise JudgeResponseError("judge returned no boolean 'supported' verdict")
                prov.append(res.provenance)
                pred = bool(res.verdict.passed)
                break
            except JudgeResponseError as exc:
                m = _PASSED_RE.search(str(exc))          # decision is clear even if JSON isn't
                if m is not None:
                    pred = (m.group(1).lower() == "true")
                    salv = True
                    print(f"  {pair.pair_id}: salvaged passed={pred} from malformed JSON")
                    break
                print(f"  {pair.pair_id}: unparseable verdict (attempt {attempt + 1}/{retries + 1}) — re-sampling")
        if pred is None:
            excluded.append(pair.pair_id)
            print(f"  {pair.pair_id}: EXCLUDED — no parseable verdict after {retries + 1} tries")
        else:
            pred_by_id[pair.pair_id] = pred
            if salv:
                salvaged.append(pair.pair_id)
        persist()  # checkpoint after EVERY pair -> fully resumable
    return pred_by_id, salvaged, excluded


def main() -> int:
    load_harness_env()
    gold_path = _ROOT / GOLD
    ckpt_path = _ROOT / CKPT
    cfg = resolve_judge_config()
    gs = load_gold_set(str(gold_path))  # require_labeled=True
    neg = sum(1 for p in gs.pairs if p.supported is False)
    pos = sum(1 for p in gs.pairs if p.supported is True)
    print(f"judge : {cfg.model}@{cfg.version}")
    print(f"gold  : {len(gs)} pairs ({pos} supported / {neg} unsupported)  {gold_set_hash(gs)[:23]}...")
    if neg == 0:
        print("  ! 0 labeled negatives -> precision would be spurious; aborting.")
        return 2
    tpm, rpm, mr = _env_int("HARNESS_TPM_BUDGET", 5500), _env_int("HARNESS_RPM_BUDGET", 28), _env_int("HARNESS_MAX_RETRIES", 6)
    jr = _env_int("HARNESS_JUDGE_JSON_RETRIES", 3)
    print(f"pacing: <= {tpm} TPM / {rpm} RPM, transport-retry x{mr}; parse-retry x{jr}; checkpoint -> {CKPT}")

    judge = _paced_judge(cfg, tpm=tpm, rpm=rpm, max_retries=mr)
    prov = ProvenanceLog(_ROOT / PROV)
    try:
        pred_by_id, salvaged, excluded = _run(gs, judge, ckpt_path, prov, retries=jr)
    except Exception as exc:  # e.g. a daily-cap (TPD) 429 that outlived the transport retries
        judged = 0
        if ckpt_path.is_file():
            judged = len(json.loads(ckpt_path.read_text(encoding="utf-8")).get("pred", {}))
        print(f"\nSTOPPED: {type(exc).__name__}: {exc}")
        print(f"Progress saved ({judged}/{len(gs)} pairs in {CKPT}). If this is a Groq TPD 429, "
              "wait for the daily reset and re-run — it resumes from the checkpoint (no re-spend).")
        return 1

    # Calibrate over the pairs we have verdicts for (excluded pairs left out, logged).
    kept = [p for p in gs.pairs if p.pair_id in pred_by_id]
    gs_kept = GoldSet(pairs=tuple(kept), gold_set_id=gs.gold_set_id)
    preds = [pred_by_id[p.pair_id] for p in kept]
    report = calibrate(gs_kept, preds, judge_model=cfg.model, judge_version=cfg.version)
    decision = graduation_for(cfg, report)
    c = report.confusion

    print("\n=== result ===")
    if excluded:
        print(f"EXCLUDED (no parseable verdict): {excluded}  -> calibrated on {len(kept)}/{len(gs)} pairs")
    if salvaged:
        print(f"salvaged from malformed JSON: {salvaged}")
    print(f"precision {report.precision}  recall {report.recall}  "
          f"gap-detection-recall {c.gap_detection_recall}  f1 {c.f1}")
    print(f"confusion  tp={c.tp} fp={c.fp} tn={c.tn} fn={c.fn}  (n={c.total})")
    print(f"threshold  min_precision={report.threshold.min_precision} min_recall={report.threshold.min_recall}")
    print(f"decision   {decision.status}   ({decision.reason})")

    stamp = datetime.date.today().isoformat()
    draft = {
        "decision_id": f"e1.5_faithfulness_calibration_{stamp}",
        "decision_type": "eval_harness_e1.5_faithfulness_calibration_run",
        "invoking_agent": "harness.commands.faithfulness_calibration (E1.5)",
        "phase_context": (
            "Out-of-band QA/CI track (harness/). First judge-reliability calibration of the "
            "status-aware faithfulness judge against a human-labelled gold set: 30 supported "
            "positives (seeded from the confirmed ledger) + 12 human-verified unsupported negatives "
            "(constructed, so precision -- the gap-masked-as-confirmed direction -- is real). Never a runtime gate."
        ),
        "run_id_reference": "harness-branch (offline; Groq-hosted non-drafter judge over the OpenAI-compatible transport)",
        "authority": [
            "harness_plan/tickets_eval_harness.md E1.5 (judge-reliability calibration)",
            "harness/calibration.py (calibrate + graduation_for)",
            "harness/gold_set.py (human-labelled gold set; fail-closed loader)",
            "E1.5 independence rule (human ground-truth labels; no AI labelling for an AI judge)",
        ],
        "judge": {"model": cfg.model, "version": cfg.version},
        "gold_set": {
            "path": str(gold_path),
            "gold_set_id": report.gold_set_id,
            "gold_set_hash": report.gold_set_hash,
            "n_pairs_calibrated": report.n_pairs,
            "labeled_positives": pos,
            "labeled_negatives": neg,
            "excluded_pairs": excluded,
            "salvaged_verdicts": salvaged,
            "labelers": sorted({p.labeler for p in gs.pairs if p.labeler}),
        },
        "calibration_result": report.to_dict(),
        "threshold": report.threshold.to_dict(),
        "decision": decision.status,
        "rationale": "<AUTO-DRAFT - human to complete: graduate or stay advisory, given precision/recall + confusion above>",
        "constitutional_check": "<AUTO-DRAFT - human to confirm: E1.5 evaluates no gate; advisory by construction; verdicts Inferred; labels human ground truth>",
        "open_items": [
            "Decision is keyed to this exact judge model+version; a repin re-opens advisory.",
            "N is modest (30 pos + 12 neg); enlarge negatives before relying on gating.",
            "Port the labeled-negatives None-guard into calibration.py (defense for future negative-light re-seeds).",
        ] + ([f"Salvaged {len(salvaged)} malformed-JSON verdict(s); consider enabling JSON mode on the judge backend."] if salvaged else [])
          + ([f"Excluded {len(excluded)} pair(s) with no parseable verdict; re-run or hand-check."] if excluded else []),
        "resolution_status": "draft",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    out = _ROOT / "harness" / "gold_sets" / f"e1.5-faithfulness-calibration_DRAFT_{stamp}.json"
    out.write_text(json.dumps(draft, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote {out}")
    print("-> complete the two <AUTO-DRAFT> fields, then move it into "
          "docs/tier4_orchestration_state/decision_log/ (resolution_status: resolved).")
    # a clean finish can retire the checkpoint
    if not excluded:
        try:
            ckpt_path.unlink()
            print(f"(removed {CKPT} — run complete)")
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
