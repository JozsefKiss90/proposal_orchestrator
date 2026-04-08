"""
CLI entry point for the DAG scheduler.

Invoked as ``python -m runner``.

Exit codes
----------
0  — Run completed; ``overall_status`` is ``pass``.
1  — Run completed; ``overall_status`` is ``fail`` or ``partial_pass``.
2  — Run aborted (``RunAbortedError``).
3  — Configuration error (``DAGSchedulerError``) or unhandled exception.

Arguments
---------
--run-id        (required) Run UUID.
--repo-root     Repository root path (default: auto-discovered via find_repo_root).
--library-path  Path to gate_rules_library.yaml (default: repo_root / LIBRARY_REL_PATH).
--manifest-path Path to manifest.compile.yaml (default: repo_root / MANIFEST_REL_PATH).
--dry-run       Print ready nodes and exit without evaluating gates.
--json          Emit progress as JSON lines to stdout.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from runner.dag_scheduler import DAGScheduler, DAGSchedulerError, ManifestGraph, RunAbortedError
from runner.gate_library import LIBRARY_REL_PATH
from runner.manifest_reader import MANIFEST_REL_PATH
from runner.paths import find_repo_root
from runner.run_context import RunContext


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ts() -> str:
    """Return a UTC ISO-8601 timestamp string."""
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: Optional[list[str]] = None) -> int:
    """
    Parse *argv* (or ``sys.argv[1:]`` when ``None``) and run the DAG.

    Returns the integer exit code; does **not** call ``sys.exit``.
    Designed to be callable from tests without spawning a subprocess.
    """
    parser = argparse.ArgumentParser(
        prog="python -m runner",
        description="Run the proposal orchestration DAG.",
    )
    parser.add_argument("--run-id", required=True, help="Run UUID.")
    parser.add_argument(
        "--repo-root",
        default=None,
        help="Repository root path (default: auto-discovered via find_repo_root).",
    )
    parser.add_argument(
        "--library-path",
        default=None,
        help="Path to gate_rules_library.yaml (default: repo_root / LIBRARY_REL_PATH).",
    )
    parser.add_argument(
        "--manifest-path",
        default=None,
        help="Path to manifest.compile.yaml (default: repo_root / MANIFEST_REL_PATH).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print ready nodes from the initial graph state and exit without evaluating gates.",
    )
    parser.add_argument(
        "--json",
        dest="use_json",
        action="store_true",
        help="Emit progress as JSON lines to stdout.",
    )
    args = parser.parse_args(argv)
    use_json: bool = args.use_json

    # ------------------------------------------------------------------
    # Output helpers (text vs JSON-lines)
    # ------------------------------------------------------------------

    def _out(text: str, event: str, **fields: object) -> None:
        if use_json:
            print(
                json.dumps({"event": event, "timestamp": _ts(), **fields}),
                flush=True,
            )
        else:
            print(text, flush=True)

    def _err(msg: str) -> None:
        if use_json:
            print(
                json.dumps({"event": "error", "message": msg, "timestamp": _ts()}),
                flush=True,
            )
        else:
            print(f"[ERROR] {msg}", file=sys.stderr, flush=True)

    # ------------------------------------------------------------------
    # Configuration / initialisation (exit code 3 on any failure here)
    # ------------------------------------------------------------------

    try:
        repo_root: Path = (
            Path(args.repo_root).resolve()
            if args.repo_root
            else find_repo_root()
        )
        library_path: Path = (
            Path(args.library_path)
            if args.library_path
            else repo_root / LIBRARY_REL_PATH
        )
        manifest_path: Path = (
            Path(args.manifest_path)
            if args.manifest_path
            else repo_root / MANIFEST_REL_PATH
        )
        graph = ManifestGraph.load(manifest_path)
        ctx = RunContext.initialize(repo_root, args.run_id)
    except Exception as exc:
        _err(str(exc))
        return 3

    _out(f"[RUN]   run_id={args.run_id}", "run_start", run_id=args.run_id)

    # ------------------------------------------------------------------
    # Dry run: enumerate ready nodes from initial state, then exit 0
    # ------------------------------------------------------------------

    if args.dry_run:
        ready = [nid for nid in graph.node_ids() if graph.is_ready(nid, ctx)]
        for nid in ready:
            _out(f"[READY] {nid}", "ready", node_id=nid)
        return 0

    # ------------------------------------------------------------------
    # Normal run
    # ------------------------------------------------------------------

    sched = DAGScheduler(
        graph,
        ctx,
        repo_root,
        library_path=library_path,
        manifest_path=manifest_path,
    )

    try:
        summary = sched.run()
        exit_code = 0 if summary.overall_status == "pass" else 1
    except RunAbortedError as exc:
        summary = exc.summary
        exit_code = 2
    except Exception as exc:
        _err(str(exc))
        return 3

    released_count = sum(1 for s in summary.node_states.values() if s == "released")
    _out(
        f"[SUMMARY] overall_status={summary.overall_status}"
        f"  nodes_released={released_count}"
        f"  stalled={len(summary.stalled_nodes)}"
        f"  hard_blocked={len(summary.hard_blocked_nodes)}",
        "summary",
        overall_status=summary.overall_status,
        nodes_released=released_count,
        stalled=len(summary.stalled_nodes),
        hard_blocked=len(summary.hard_blocked_nodes),
    )
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
