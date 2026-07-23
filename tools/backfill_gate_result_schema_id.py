#!/usr/bin/env python3
"""
One-time backfill: add the required ``schema_id`` to legacy gate result files.

``artifact_schema_specification.yaml`` (gate_result_schema) requires every gate
result file to carry ``schema_id: "orch.gate_result.v1"``.  The gate evaluator
historically omitted it (fixed in ``runner/gate_evaluator.py``); this backfills
the field into gate result files written *before* that fix, so consumers that
enforce the schema — e.g. ``checkpoint-publish`` at n08f — accept them.

Format-only migration: it **only ever adds an absent** ``schema_id`` and touches
nothing else.  No status, predicate, ``evaluated_at``, or fingerprint is changed,
so no gate decision is altered — it makes an already-decided result conform to
its declared schema.

A file that already carries a *different* ``schema_id`` is **never rewritten**:
that is a wrong declared schema, and silently repairing it is exactly the
auto-correction CLAUDE.md §17.6.5 forbids.  Such files are reported as
``conflicts`` and the tool exits non-zero so the operator resolves them
explicitly.

Idempotent; only files with the gate-result shape (``gate_id`` + ``gate_kind`` +
``status``) are touched.  Dry-run by default.  Recorded in the decision log.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from runner.gate_result_registry import GATE_RESULT_SCHEMA_ID  # noqa: E402

SCHEMA_ID = GATE_RESULT_SCHEMA_ID
PHASE_OUTPUTS_REL = "docs/tier4_orchestration_state/phase_outputs"


def _is_gate_result(d: object) -> bool:
    return isinstance(d, dict) and all(
        k in d for k in ("gate_id", "gate_kind", "status")
    )


def backfill(repo_root: Path, apply: bool) -> dict:
    root = repo_root / PHASE_OUTPUTS_REL
    changed: list[str] = []
    already: list[str] = []
    conflicts: list[dict] = []
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
        if "schema_id" in d and d["schema_id"] is not None:
            if d["schema_id"] == SCHEMA_ID:
                already.append(rel)
                continue
            # Present but wrong: a validation failure, not a repairable
            # condition (§17.6.5).  Never overwrite; report and fail.
            conflicts.append({"path": rel, "found_schema_id": d["schema_id"]})
            continue
        # Absent (or explicitly null) — the only case this tool writes.
        changed.append(rel)
        if apply:
            nd = {"schema_id": SCHEMA_ID}
            nd.update({k: v for k, v in d.items() if k != "schema_id"})
            f.write_text(json.dumps(nd, indent=2), encoding="utf-8")
    return {
        "changed": changed,
        "already_ok": already,
        "conflicts": conflicts,
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
        f"conflicts={len(r['conflicts'])}  "
        f"skipped_non_gate={r['skipped_non_gate']}"
    )
    for c in r["changed"]:
        print(f"  + {c}")
    for c in r["conflicts"]:
        print(
            f"  ! {c['path']}: declares schema_id "
            f"{c['found_schema_id']!r}, expected {SCHEMA_ID!r} — NOT rewritten"
        )
    if not a.apply:
        print("[BACKFILL] dry-run only — re-run with --apply to write.")
    if r["conflicts"]:
        print(
            "[BACKFILL] FAILED — gate results with a wrong schema_id are a "
            "validation failure, not an auto-correctable condition "
            "(CLAUDE.md §17.6.5).  Resolve them explicitly (re-evaluate the "
            "gate) before re-running."
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
