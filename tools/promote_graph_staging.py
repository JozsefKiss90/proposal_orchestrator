#!/usr/bin/env python3
"""
Promote graph-compiled staging artifacts to their canonical ``docs/**`` paths.

Milestone-2, ticket 10 — the **explicit** half of the open-Q #4 resolution
("parallel + explicit promote"). The graph->docs compiler (``--from-graph``) is
non-destructive: it writes to
``docs/tier4_orchestration_state/graph_compile/staging/docs/**`` and diffs against
the hand-lift, never overwriting ``docs/``. This script performs the deliberate,
opt-in promotion of that staged output onto the canonical ``docs/**`` paths the
runner consumes. The graph does NOT auto-overwrite; a human runs this.

Fail-closed guards
  * Refuses unless the staging's ``project_id`` matches the ``project_id`` of the
    ``graph.config.yaml`` passed in — so a stale toy/second-instance staging
    (e.g. BorrowBrella) can never clobber the MSCA docs.
  * Refuses if the staging tree or its reports are missing (nothing to promote).
  * Dry-run by default; ``--apply`` is required to write.

Reversibility / provenance
  * Overwritten canonical files are copied to
    ``docs/tier4_orchestration_state/graph_compile/pre_promote_backup/`` first.
  * ``promote_record.json`` logs {project_id, promoted, changed, promoted_at}.
  * Also fully reversible via git (docs/** is tracked).

Deterministic and Claude-free: a project-id-guarded byte copy, no domain
reasoning. Same staging => same promotion.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

STAGING_REL = "docs/tier4_orchestration_state/graph_compile/staging"
DIFF_REPORT_REL = "docs/tier4_orchestration_state/graph_compile/diff_report.json"
PART_B_REPORT_REL = "docs/tier4_orchestration_state/graph_compile/part_b_report.json"
BACKUP_REL = "docs/tier4_orchestration_state/graph_compile/pre_promote_backup"
RECORD_REL = "docs/tier4_orchestration_state/graph_compile/promote_record.json"


class PromoteError(Exception):
    """Raised when promotion must fail closed."""


def _read_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def _config_project_id(config_path: Path) -> str:
    if not config_path.is_file():
        raise PromoteError(f"config not found: {config_path}")
    for line in config_path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s.startswith("project_id:"):
            return s.split(":", 1)[1].strip().strip("\"'")
    raise PromoteError(f"no project_id line in {config_path}")


def _staging_project_id(repo_root: Path) -> str:
    for rel in (PART_B_REPORT_REL, DIFF_REPORT_REL):
        p = repo_root / rel
        if p.is_file():
            pid = _read_json(p).get("project_id")
            if pid:
                return pid
    raise PromoteError(
        "cannot determine staging project_id (no diff_report / part_b_report). "
        "Run `python -m runner --from-graph <config>` first."
    )


def promote(repo_root: Path, config_path: Path, apply: bool) -> dict:
    staging_docs = repo_root / STAGING_REL / "docs"
    if not staging_docs.is_dir():
        raise PromoteError(
            f"no staging tree at {staging_docs}. Run --from-graph first."
        )

    expected = _config_project_id(config_path)
    staged = _staging_project_id(repo_root)
    if expected != staged:
        raise PromoteError(
            f"REFUSING to promote: staging project_id {staged!r} != config "
            f"project_id {expected!r}. Staging holds a different instance — "
            f"re-run `python -m runner --from-graph {config_path}` first."
        )

    files = sorted(p for p in staging_docs.rglob("*.json") if p.is_file())
    if not files:
        raise PromoteError(f"no staged artifacts under {staging_docs}")

    promoted: list[str] = []
    changed: list[str] = []
    backup_root = repo_root / BACKUP_REL
    for src in files:
        rel = src.relative_to(repo_root / STAGING_REL)  # docs/....json
        rel_str = str(rel).replace("\\", "/")
        dst = repo_root / rel
        promoted.append(rel_str)
        if not (dst.is_file() and dst.read_bytes() == src.read_bytes()):
            changed.append(rel_str)
        if apply:
            if dst.is_file():
                bpath = backup_root / rel
                bpath.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(dst, bpath)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

    record = {
        "record_type": "graph_promote",
        "project_id": expected,
        "apply": apply,
        "promoted_files": promoted,
        "changed_files": changed,
        "source_reports": [DIFF_REPORT_REL, PART_B_REPORT_REL],
        "promoted_at": datetime.now(timezone.utc).isoformat(),
        "open_q4_resolution": "parallel + explicit promote (M2-T10)",
        "note": (
            "Overwritten canonical files backed up under pre_promote_backup/. "
            "Reversible via git or the backup. The hand-lift remains the fallback."
        ),
    }
    if apply:
        (repo_root / RECORD_REL).write_text(
            json.dumps(record, indent=2), encoding="utf-8"
        )
    return record


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="promote_graph_staging")
    ap.add_argument(
        "--config", required=True,
        help="path to the graph.config.yaml whose --from-graph compile is staged",
    )
    ap.add_argument("--repo-root", default=".")
    ap.add_argument(
        "--apply", action="store_true",
        help="write the promotion (default: dry-run, prints what would change)",
    )
    a = ap.parse_args(argv)
    repo_root = Path(a.repo_root).resolve()
    try:
        rec = promote(repo_root, Path(a.config), a.apply)
    except PromoteError as exc:
        print(f"[PROMOTE] FAIL-CLOSED: {exc}", file=sys.stderr)
        return 2
    mode = "APPLIED" if a.apply else "DRY-RUN"
    print(
        f"[PROMOTE] {mode}  project={rec['project_id']}  "
        f"files={len(rec['promoted_files'])}  changed={len(rec['changed_files'])}"
    )
    for f in rec["changed_files"]:
        print(f"  changed: {f}")
    if not a.apply:
        print("[PROMOTE] dry-run only — re-run with --apply to write.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
