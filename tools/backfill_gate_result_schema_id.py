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

Discovery (SCH-1)
-----------------
Gate result files are discovered from the runtime's *own* knowledge of where it
writes them — not by a narrow ``phase_outputs/**/*result*.json`` glob that
silently misses sibling locations.  Three sources, de-duplicated by resolved
path:

  1. **Canonical** — every path in
     :data:`runner.gate_result_registry.GATE_RESULT_PATHS`.  A registry entry
     *is* a gate result location by declaration, so no shape-guessing is needed
     to know where to look.
  2. **Fallback** — every ``*.json`` in the evaluator's fallback subdirectory
     (:data:`~runner.gate_result_registry.GATE_RESULT_FALLBACK_SUBDIR`, i.e.
     ``…/gate_results/``), where ``gate_evaluator._gate_result_path`` writes
     results for gate_ids absent from the registry.  Those files are named
     ``<gate_id>.json`` (no ``result`` token) — which the old glob could never
     match.
  3. **Non-canonical safety net** — a shape-checked sweep of the whole tier-4
     tree for gate-result-shaped ``*.json`` files at locations outside sources 1
     and 2 (e.g. the preserved ``alpha_honest_block/
     phase2_gate_result_HONEST_BLOCK.json`` milestone artifact).  It keys on the
     gate-result *shape* (``gate_id`` + ``gate_kind`` + ``status``), not on a
     filename token, so a preserved result is found regardless of its name.
     These are reported under ``non_canonical`` so a file caught outside the
     runtime's path model is always *visible* — never silently swept in, never
     silently missed.

Root validation (SCH-2)
-----------------------
A wrong ``--repo-root`` used to ``rglob`` a non-existent directory, find nothing,
and exit 0 — indistinguishable from "all conforming".  Now:

  * a ``--repo-root`` with no ``docs/tier4_orchestration_state/`` directory is a
    distinct **INVALID ROOT** failure (exit ``2``), never a silent clean run;
  * discovering **zero** gate results under a valid root is a distinct
    **NOTHING SCANNED** outcome (exit ``3``), reported separately from "all
    conforming" (exit ``0``) so a mis-pointed re-run can never masquerade as
    success.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from runner.gate_result_registry import (  # noqa: E402
    GATE_RESULT_FALLBACK_SUBDIR,
    GATE_RESULT_PATHS,
    GATE_RESULT_SCHEMA_ID,
    TIER4_ROOT_REL,
)

SCHEMA_ID = GATE_RESULT_SCHEMA_ID

#: Distinct process exit codes.  ``0`` clean, ``1`` conflict (fail-closed),
#: ``2`` invalid root, ``3`` nothing scanned — each a different signal so no
#: failure mode can hide behind another (SCH-2).
EXIT_OK = 0
EXIT_CONFLICT = 1
EXIT_INVALID_ROOT = 2
EXIT_NOTHING_SCANNED = 3


def _is_gate_result(d: object) -> bool:
    return isinstance(d, dict) and all(
        k in d for k in ("gate_id", "gate_kind", "status")
    )


def _discover(repo_root: Path) -> tuple[list[Path], set[Path]]:
    """Return ``(ordered_candidates, non_canonical_resolved)``.

    Candidates are drawn — in priority order, de-duplicated by resolved absolute
    path — from the registry (canonical), the evaluator fallback subdir, and a
    tier-4 ``*result*.json`` safety-net sweep.  A path first seen via the sweep
    (i.e. outside the canonical registry and fallback locations) is recorded in
    the returned set so the caller can report it distinctly.
    """
    tier4 = repo_root / TIER4_ROOT_REL
    ordered: list[Path] = []
    seen: set[Path] = set()
    non_canonical: set[Path] = set()

    def _add(p: Path, *, is_non_canonical: bool) -> None:
        if not p.is_file():
            return
        rp = p.resolve()
        if rp in seen:
            return
        seen.add(rp)
        ordered.append(p)
        if is_non_canonical:
            non_canonical.add(rp)

    # 1. Canonical registry locations — gate results by declaration.
    for rel in GATE_RESULT_PATHS.values():
        _add(tier4 / rel, is_non_canonical=False)

    # 2. Evaluator fallback subdir — unregistered gate_ids → <gate_id>.json.
    fallback_dir = tier4 / GATE_RESULT_FALLBACK_SUBDIR
    if fallback_dir.is_dir():
        for p in sorted(fallback_dir.glob("*.json")):
            _add(p, is_non_canonical=False)

    # 3. Safety net — gate-result-shaped files preserved elsewhere in tier-4.
    #    Keyed on the gate-result *shape* (checked in backfill(), below), not on
    #    a filename token, so a preserved result is found regardless of its name
    #    (e.g. ``phase2_gate_HONEST_BLOCK.json``).  Non-gate ``*.json`` swept in
    #    here are counted as skipped_non_gate, never touched.
    if tier4.is_dir():
        for p in sorted(tier4.rglob("*.json")):
            _add(p, is_non_canonical=True)

    return ordered, non_canonical


def backfill(repo_root: Path, apply: bool) -> dict:
    candidates, non_canonical_set = _discover(repo_root)
    changed: list[str] = []
    already: list[str] = []
    conflicts: list[dict] = []
    non_canonical: list[str] = []
    skipped_non_gate = 0
    for f in candidates:
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not _is_gate_result(d):
            skipped_non_gate += 1
            continue
        rel = str(f.relative_to(repo_root)).replace("\\", "/")
        if f.resolve() in non_canonical_set:
            non_canonical.append(rel)
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
        "non_canonical": non_canonical,
        "skipped_non_gate": skipped_non_gate,
        # Total gate-result-shaped files examined (across all locations).  The
        # discriminator for zero-scan vs all-conforming (SCH-2).
        "gate_results_scanned": len(changed) + len(already) + len(conflicts),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="backfill_gate_result_schema_id")
    ap.add_argument("--repo-root", default=".")
    ap.add_argument(
        "--apply", action="store_true",
        help="write the backfill (default: dry-run)",
    )
    a = ap.parse_args(argv)
    repo_root = Path(a.repo_root).resolve()

    # SCH-2: a --repo-root without the tier-4 tree is a distinct failure, never
    # a silent clean run.  The old rglob-on-missing-dir returned 0, which reads
    # identically to "all conforming".
    if not (repo_root / TIER4_ROOT_REL).is_dir():
        print(
            f"[BACKFILL] INVALID ROOT — {TIER4_ROOT_REL}/ not found under "
            f"{repo_root}.  Is --repo-root correct?"
        )
        return EXIT_INVALID_ROOT

    r = backfill(repo_root, a.apply)
    mode = "APPLIED" if a.apply else "DRY-RUN"
    print(
        f"[BACKFILL] {mode}  scanned={r['gate_results_scanned']}  "
        f"changed={len(r['changed'])}  "
        f"already_ok={len(r['already_ok'])}  "
        f"conflicts={len(r['conflicts'])}  "
        f"non_canonical={len(r['non_canonical'])}  "
        f"skipped_non_gate={r['skipped_non_gate']}"
    )
    for c in r["changed"]:
        print(f"  + {c}")
    for c in r["non_canonical"]:
        print(f"  ~ {c}  (found outside canonical registry / fallback locations)")
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
        return EXIT_CONFLICT
    # SCH-2: zero gate results under a valid root is reported distinctly from
    # "all conforming" and is never a silent success.
    if r["gate_results_scanned"] == 0:
        print(
            f"[BACKFILL] NOTHING SCANNED — no gate results were discovered "
            f"under {repo_root}.  This is *not* 'all conforming': either the "
            f"root has no orchestration runs yet, or --repo-root is misdirected "
            f"(skipped_non_gate={r['skipped_non_gate']})."
        )
        return EXIT_NOTHING_SCANNED
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
