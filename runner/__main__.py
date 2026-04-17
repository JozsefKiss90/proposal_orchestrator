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
--phase         Execute only the specified phase (e.g. 1, phase1, phase_01).
--dry-run       Print ready nodes and exit without evaluating gates.
--json          Emit progress as JSON lines to stdout.
--verbose       Enable detailed scheduler logging to stderr.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from runner.dag_scheduler import (
    DAGScheduler,
    DAGSchedulerError,
    ManifestGraph,
    RunAbortedError,
    bootstrap_phase_prerequisites,
)
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


def _parse_phase(raw: str) -> int:
    """Parse a phase argument like ``1``, ``phase1``, ``phase_01``, ``phase_01_call_analysis``."""
    m = re.match(r"^(?:phase[_-]?)?0*(\d+)", raw.lower())
    if not m:
        raise argparse.ArgumentTypeError(
            f"Invalid phase identifier: {raw!r}.  "
            "Expected a phase number (e.g. 1, phase1, phase_01)."
        )
    return int(m.group(1))


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
        "--phase",
        type=_parse_phase,
        default=None,
        help=(
            "Execute only the specified phase (e.g. 1, phase1, phase_01).  "
            "All prerequisite gates and artifacts must already be satisfied.  "
            "No downstream phases are dispatched."
        ),
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
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable detailed scheduler logging to stderr.",
    )
    args = parser.parse_args(argv)
    use_json: bool = args.use_json

    # ------------------------------------------------------------------
    # Configure logging
    # ------------------------------------------------------------------
    sched_logger = logging.getLogger("runner.scheduler")
    skill_logger = logging.getLogger("runner.skill_runtime")
    if args.verbose:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
        sched_logger.setLevel(logging.DEBUG)
        sched_logger.addHandler(handler)
        skill_logger.setLevel(logging.INFO)
        skill_logger.addHandler(handler)
    else:
        # INFO level so phase-scoped messages appear, but only with a handler
        # when --verbose is set; without a handler, messages are silently dropped.
        sched_logger.setLevel(logging.WARNING)
        skill_logger.setLevel(logging.WARNING)

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
        ctx = RunContext.load_or_initialize(repo_root, args.run_id)
    except Exception as exc:
        _err(str(exc))
        return 3

    # ------------------------------------------------------------------
    # Phase-scoped continuation bootstrap
    # ------------------------------------------------------------------
    # When --phase is specified, seed upstream prerequisite nodes as
    # "released" from durable Tier 4 gate result evidence.  This enables
    # phase-by-phase execution with new run-ids (each invocation reads
    # prior-run evidence) and also works with existing run-ids (already-
    # loaded states are preserved; only "pending" nodes are candidates).
    if args.phase is not None:
        try:
            bootstrapped = bootstrap_phase_prerequisites(
                ctx, graph, repo_root, args.phase
            )
            if bootstrapped:
                _out(
                    f"[BOOTSTRAP] Seeded {len(bootstrapped)} upstream node(s) "
                    f"from prior evidence: {bootstrapped}",
                    "bootstrap",
                    bootstrapped_nodes=bootstrapped,
                    count=len(bootstrapped),
                )
        except Exception as exc:
            # Bootstrap failure is non-blocking: the scheduler will detect
            # unmet prerequisites via its normal readiness checks and abort.
            sched_logger.warning("Bootstrap failed (non-blocking): %s", exc)

    phase_label = f"  phase={args.phase}" if args.phase else ""
    run_start_fields: dict[str, object] = {"run_id": args.run_id}
    if args.phase is not None:
        run_start_fields["phase"] = args.phase
    _out(
        f"[RUN]   run_id={args.run_id}{phase_label}",
        "run_start",
        **run_start_fields,
    )

    # ------------------------------------------------------------------
    # Dry run: enumerate ready nodes from initial state, then exit 0
    #
    # Semantics: dry-run is side-effect-MINIMIZING, not side-effect-free.
    # RunContext.initialize() has already run above, creating
    # .claude/runs/<run_id>/run_manifest.json and reuse_policy.json.
    # Dry-run does NOT evaluate any gates and does NOT write run_summary.json.
    # ------------------------------------------------------------------

    if args.dry_run:
        scope = set(graph.nodes_for_phase(args.phase)) if args.phase else None
        ready = [
            nid for nid in graph.node_ids()
            if graph.is_ready(nid, ctx)
            and (scope is None or nid in scope)
        ]
        for nid in ready:
            _out(f"[READY] {nid}", "ready", node_id=nid)
        return 0

    # ------------------------------------------------------------------
    # Normal run (full DAG or phase-scoped)
    # ------------------------------------------------------------------

    sched = DAGScheduler(
        graph,
        ctx,
        repo_root,
        library_path=library_path,
        manifest_path=manifest_path,
        phase=args.phase,
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
    ps = getattr(summary, "phase_scope", None)
    has_phase = isinstance(ps, int)
    phase_info = f"  phase={ps}" if has_phase else ""
    summary_fields: dict[str, object] = {
        "overall_status": summary.overall_status,
        "nodes_released": released_count,
        "stalled": len(summary.stalled_nodes),
        "hard_blocked": len(summary.hard_blocked_nodes),
    }
    if has_phase:
        summary_fields["phase_scope"] = ps
        psn = getattr(summary, "phase_scope_nodes", None)
        summary_fields["phase_scope_nodes"] = list(psn) if isinstance(psn, list) else []
    _out(
        f"[SUMMARY] overall_status={summary.overall_status}"
        f"  nodes_released={released_count}"
        f"  stalled={len(summary.stalled_nodes)}"
        f"  hard_blocked={len(summary.hard_blocked_nodes)}"
        f"{phase_info}",
        "summary",
        **summary_fields,
    )
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
