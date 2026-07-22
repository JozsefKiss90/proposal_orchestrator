#!/usr/bin/env python3
"""
One-time backfill: add the required ``schema_id`` to legacy gate result files.

``artifact_schema_specification.yaml`` (gate_result_schema) requires every gate
result file to carry ``schema_id: "orch.gate_result.v1"``.  The gate evaluator
historically omitted it (fixed in ``runner/gate_evaluator.py``); this backfills
the field into gate result files written *before* that fix, so consumers that
enforce the schema — e.g. ``checkpoint-publish`` at n08f — accept them.

Format-only migration: it adds ``schema_id`` and touches nothing else.  No
status, predicate, ``evaluated_at``, or fingerprint is changed, so no gate
decision is altered — it makes an already-decided result conform to its declared
schema.  Idempotent; only files with the gate-result shape (``gate_id`` +
``gate_kind`` + ``status``) are touched.  Dry-run by default.  Recorded in the
decision log.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCHEMA_ID = "orch.gate_result.v1"
PHASE_OUTPUTS_REL = "docs/tier4_orchestration_state/phase_outputs"


def _is_gate_result(d: object) -> bool:
    return isinstance(d, dict) and all(
        k in d for k in ("gate_id", "gate_kind", "status")
    )


def backfill(repo_root: Path, apply: bool) -> dict:
    root = repo_root / PHASE_OUTPUTS_REL
    changed: list[str] = []
    already: list[str] = []
    skipped_non_gate = 0
    for f in sorted(root.rglob("*result*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not _is_gate_result(d):
            skipped_non_gate += 1
            continue
        rel = str(f.relative_to(repo_root)).replace("\\", "/")
        if d.get("schema_id") == SCHEMA_ID:
            already.append(rel)
            continue
        changed.append(rel)
        if apply:
            nd = {"schema_id": SCHEMA_ID}
            nd.update({k: v for k, v in d.items() if k != "schema_id"})
            f.write_text(json.dumps(nd, indent=2), encoding="utf-8")
    return {
        "changed": changed,
        "already_ok": already,
        "skipped_non_gate": skipped_non_gate,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="backfill_gate_result_schema_id")
    ap.add_argument("--repo-root", default=".")
    ap.add_argument(
        "--apply", action="store_true",
        help="write the backfill (default: dry-run)",
    )
    a = ap.parse_args(argv)
    r = backfill(Path(a.repo_root).resolve(), a.apply)
    mode = "APPLIED" if a.apply else "DRY-RUN"
    print(
        f"[BACKFILL] {mode}  changed={len(r['changed'])}  "
        f"already_ok={len(r['already_ok'])}  "
        f"skipped_non_gate={r['skipped_non_gate']}"
    )
    for c in r["changed"]:
        print(f"  + {c}")
    if not a.apply:
        print("[BACKFILL] dry-run only — re-run with --apply to write.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
