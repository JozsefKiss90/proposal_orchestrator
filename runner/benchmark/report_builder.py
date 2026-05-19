"""
Phase B report builder — reads Phase A artifacts, writes analytics artifacts.

Responsibilities:
- Read ``invocation_ledger.jsonl``
- Read Phase A ``run_benchmark_summary.json``
- Optionally read ``run_summary.json``
- Write Phase B artifacts atomically (write-to-temp + rename)
- Swallow all failures safely — never propagate to orchestration
- Return list of paths written

This module does NOT call scheduler, agent runtime, skill runtime,
gate evaluator, or transport.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from runner.benchmark.analytics import build_phase_analytics, build_token_economics
from runner.benchmark.timing import build_timing_profile

logger = logging.getLogger(__name__)


def run_phase_b_analytics(
    bench_dir: Path,
    *,
    run_summary_path: Path | None = None,
) -> list[Path]:
    """Execute Phase B analytics and write artifacts.

    Parameters
    ----------
    bench_dir
        Path to ``.claude/benchmark/<run_id>/`` containing Phase A artifacts.
    run_summary_path
        Optional path to ``.claude/runs/<run_id>/run_summary.json``.

    Returns
    -------
    list[Path]
        Paths of all artifacts written. Empty list on failure.
    """
    try:
        return _run_phase_b_analytics_inner(bench_dir, run_summary_path=run_summary_path)
    except Exception:
        logger.debug(
            "Phase B analytics failed (non-blocking)", exc_info=True
        )
        return []


def _run_phase_b_analytics_inner(
    bench_dir: Path,
    *,
    run_summary_path: Path | None = None,
) -> list[Path]:
    """Inner implementation — may raise."""
    # 1. Read invocation ledger
    ledger_path = bench_dir / "invocation_ledger.jsonl"
    records = _read_ledger(ledger_path)

    # 2. Read Phase A summary
    phase_a_summary = _read_json(bench_dir / "run_benchmark_summary.json")

    # 3. Read run_summary (optional)
    run_summary: dict | None = None
    if run_summary_path and run_summary_path.exists():
        run_summary = _read_json(run_summary_path)

    # Extract common fields
    run_id = ""
    phase_scope: int | None = None

    if phase_a_summary:
        run_id = phase_a_summary.get("run_id", "")
    if run_summary:
        run_id = run_summary.get("run_id", run_id)
        phase_scope = run_summary.get("phase_scope")

    total_wall_clock = None
    if phase_a_summary:
        total_wall_clock = phase_a_summary.get("total_wall_clock_seconds")

    # 4. Build analytics
    phase_analytics = build_phase_analytics(
        records,
        run_id=run_id,
        phase_scope=phase_scope,
        run_summary=run_summary,
        phase_a_summary=phase_a_summary,
    )

    token_economics = build_token_economics(
        records,
        run_id=run_id,
        run_summary=run_summary,
        phase_a_summary=phase_a_summary,
    )

    timing_profile = build_timing_profile(
        records,
        total_wall_clock_seconds=total_wall_clock,
    )

    # 5. Write Phase B artifacts
    written: list[Path] = []

    pa_path = bench_dir / "phase_analytics.json"
    _write_json_atomic(pa_path, phase_analytics)
    written.append(pa_path)

    te_path = bench_dir / "token_economics.json"
    _write_json_atomic(te_path, token_economics)
    written.append(te_path)

    tp_path = bench_dir / "timing_profile.json"
    _write_json_atomic(tp_path, timing_profile)
    written.append(tp_path)

    # 6. Expand run_benchmark_summary.json
    expanded = _build_expanded_summary(
        phase_a_summary=phase_a_summary,
        phase_analytics=phase_analytics,
        token_economics=token_economics,
        timing_profile=timing_profile,
        written_paths=written,
        bench_dir=bench_dir,
    )
    summary_path = bench_dir / "run_benchmark_summary.json"
    _write_json_atomic(summary_path, expanded)
    written.append(summary_path)

    return written


# ---------------------------------------------------------------------------
# Reading helpers
# ---------------------------------------------------------------------------

def _read_ledger(path: Path) -> list[dict]:
    """Read JSONL ledger, skipping malformed lines."""
    records: list[dict] = []
    if not path.exists():
        return records

    text = path.read_text(encoding="utf-8")
    for line_num, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if isinstance(obj, dict):
                records.append(obj)
            else:
                logger.debug("Ledger line %d: not a dict, skipped", line_num)
        except json.JSONDecodeError:
            logger.debug("Ledger line %d: malformed JSON, skipped", line_num)

    return records


def _read_json(path: Path) -> dict | None:
    """Read a JSON file. Returns None on any failure."""
    try:
        if not path.exists():
            return None
        text = path.read_text(encoding="utf-8")
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else None
    except Exception:
        logger.debug("Failed to read JSON: %s", path, exc_info=True)
        return None


# ---------------------------------------------------------------------------
# Writing helpers
# ---------------------------------------------------------------------------

def _write_json_atomic(path: Path, data: Any) -> None:
    """Write JSON atomically: write to temp file, then rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(data, indent=2, ensure_ascii=False)

    # Write to temp in same directory, then rename for atomicity
    fd, tmp_path = tempfile.mkstemp(
        dir=str(path.parent),
        prefix=".tmp_",
        suffix=".json",
    )
    try:
        os.write(fd, content.encode("utf-8"))
        os.close(fd)
        # On Windows, os.replace is atomic only on same volume (which it is here)
        os.replace(tmp_path, str(path))
    except Exception:
        os.close(fd) if not os.get_inheritable(fd) else None
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# Summary expansion
# ---------------------------------------------------------------------------

def _build_expanded_summary(
    *,
    phase_a_summary: dict | None,
    phase_analytics: dict,
    token_economics: dict,
    timing_profile: dict,
    written_paths: list[Path],
    bench_dir: Path,
) -> dict:
    """Build expanded run_benchmark_summary preserving all Phase A fields."""
    # Start with all Phase A fields
    expanded: dict[str, Any] = {}
    if phase_a_summary:
        expanded.update(phase_a_summary)

    # Add Phase B summaries
    expanded["phase_analytics_summary"] = {
        "phases_observed": phase_analytics.get("phases_observed", []),
        "nodes_observed": phase_analytics.get("nodes_observed", []),
        "total_invocations": phase_analytics.get("total_invocations", 0),
    }

    expanded["token_economics_summary"] = {
        "total_estimated_input_tokens": token_economics.get("total_estimated_input_tokens", 0),
        "total_estimated_output_tokens": token_economics.get("total_estimated_output_tokens", 0),
        "total_estimated_tokens": token_economics.get("total_estimated_tokens", 0),
    }

    expanded["timing_summary"] = {
        "total_wall_clock_seconds": timing_profile.get("total_wall_clock_seconds", 0),
        "mean_invocation_seconds": timing_profile.get("mean_invocation_seconds", 0),
        "median_invocation_seconds": timing_profile.get("median_invocation_seconds", 0),
    }

    # Artifact paths (relative to bench_dir parent for portability)
    expanded["phase_b_artifact_paths"] = {
        "phase_analytics": str(written_paths[0].name) if len(written_paths) > 0 else None,
        "token_economics": str(written_paths[1].name) if len(written_paths) > 1 else None,
        "timing_profile": str(written_paths[2].name) if len(written_paths) > 2 else None,
    }

    expanded["benchmark_stage"] = "phase_b_analytics"

    return expanded
