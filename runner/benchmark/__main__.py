"""
CLI entry point for benchmark reporting.

Usage:
    python -m runner.benchmark --run-id <run_id>
    python -m runner.benchmark --run-id <run_id> --section summary
    python -m runner.benchmark --run-id <run_id> --json
    python -m runner.benchmark --list
    python -m runner.benchmark --benchmark-root <path> --list

Exit codes:
    0  Report generated (even with data-quality warnings)
    1  Requested run_id not found
    2  Invalid CLI arguments
    3  Unexpected internal error
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from runner.benchmark.formatters import (
    compute_quality_warnings,
    format_full_report,
    format_json_report,
    format_provider_report,
    format_quality_report,
    format_routing_report,
    format_summary_report,
    format_timing_report,
    format_token_report,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_SECTIONS = ("summary", "tokens", "timing", "providers", "routing", "quality")

DEFAULT_BENCHMARK_ROOT = os.path.join(".claude", "benchmark")

ARTIFACT_NAMES = (
    "run_benchmark_summary.json",
    "phase_analytics.json",
    "token_economics.json",
    "timing_profile.json",
    "provider_projection.json",
    "invocation_ledger.jsonl",
)


# ---------------------------------------------------------------------------
# Artifact loading
# ---------------------------------------------------------------------------

def _read_json_safe(path: Path) -> dict | None:
    """Read a JSON file, returning None on any failure."""
    try:
        if not path.exists():
            return None
        text = path.read_text(encoding="utf-8")
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


def _load_artifacts(run_dir: Path) -> dict[str, Any]:
    """Load all benchmark artifacts from a run directory.

    Returns a dict with keys: summary, phase_analytics, token_economics,
    timing_profile, provider_projection, ledger_exists, loaded_artifacts.
    """
    loaded: list[str] = []

    summary = _read_json_safe(run_dir / "run_benchmark_summary.json")
    if summary is not None:
        loaded.append("run_benchmark_summary.json")

    phase_analytics = _read_json_safe(run_dir / "phase_analytics.json")
    if phase_analytics is not None:
        loaded.append("phase_analytics.json")

    token_economics = _read_json_safe(run_dir / "token_economics.json")
    if token_economics is not None:
        loaded.append("token_economics.json")

    timing_profile = _read_json_safe(run_dir / "timing_profile.json")
    if timing_profile is not None:
        loaded.append("timing_profile.json")

    provider_projection = _read_json_safe(run_dir / "provider_projection.json")
    if provider_projection is not None:
        loaded.append("provider_projection.json")

    ledger_exists = (run_dir / "invocation_ledger.jsonl").exists()
    if ledger_exists:
        loaded.append("invocation_ledger.jsonl")

    return {
        "summary": summary,
        "phase_analytics": phase_analytics,
        "token_economics": token_economics,
        "timing_profile": timing_profile,
        "provider_projection": provider_projection,
        "ledger_exists": ledger_exists,
        "loaded_artifacts": loaded,
    }


# ---------------------------------------------------------------------------
# Listing
# ---------------------------------------------------------------------------

def _list_runs(benchmark_root: Path) -> str:
    """List available benchmark run IDs, newest first by mtime."""
    if not benchmark_root.exists():
        return "No benchmark directory found.\n"

    entries = []
    for child in benchmark_root.iterdir():
        if child.is_dir() and child.name != "config":
            try:
                mtime = child.stat().st_mtime
            except OSError:
                mtime = 0.0
            entries.append((child.name, mtime))

    if not entries:
        return "No benchmark runs found.\n"

    # Sort newest first
    entries.sort(key=lambda e: e[1], reverse=True)

    lines = ["Available benchmark runs:\n"]
    for run_id, _ in entries:
        # Check what artifacts exist
        run_dir = benchmark_root / run_id
        summary = _read_json_safe(run_dir / "run_benchmark_summary.json")
        stage = "(unknown)"
        invocations = ""
        if summary:
            stage = summary.get("benchmark_stage", "unknown")
            n = summary.get("total_invocations")
            if n is not None:
                invocations = f"  invocations={n}"
        lines.append(f"  {run_id}  stage={stage}{invocations}")

    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Section dispatch
# ---------------------------------------------------------------------------

def _render_section(
    section: str,
    artifacts: dict[str, Any],
    quality_warnings: list[str],
) -> str:
    if section == "summary":
        return format_summary_report(
            artifacts["summary"],
            phase_analytics=artifacts["phase_analytics"],
            token_economics=artifacts["token_economics"],
            provider_projection=artifacts["provider_projection"],
            quality_warnings=quality_warnings,
        )
    elif section == "tokens":
        return format_token_report(
            artifacts["token_economics"],
            summary=artifacts["summary"],
        )
    elif section == "timing":
        return format_timing_report(artifacts["timing_profile"])
    elif section == "providers":
        return format_provider_report(artifacts["provider_projection"])
    elif section == "routing":
        return format_routing_report(artifacts["provider_projection"])
    elif section == "quality":
        return format_quality_report(quality_warnings)
    else:
        return f"Unknown section: {section}\n"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m runner.benchmark",
        description="Human-readable benchmark reporting over .claude/benchmark/ artifacts.",
    )
    parser.add_argument(
        "--run-id",
        type=str,
        default=None,
        help="Benchmark run ID to report on.",
    )
    parser.add_argument(
        "--section",
        type=str,
        default=None,
        choices=VALID_SECTIONS,
        help="Render only a specific report section.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        dest="json_mode",
        help="Emit merged JSON output instead of human-readable text.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        default=False,
        dest="list_runs",
        help="List available benchmark run IDs.",
    )
    parser.add_argument(
        "--benchmark-root",
        type=str,
        default=None,
        help="Path to benchmark root directory (default: .claude/benchmark).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns exit code."""
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return 2 if e.code != 0 else 0

    benchmark_root = Path(args.benchmark_root) if args.benchmark_root else Path(DEFAULT_BENCHMARK_ROOT)

    # --list mode
    if args.list_runs:
        sys.stdout.write(_list_runs(benchmark_root))
        return 0

    # All other modes require --run-id
    if not args.run_id:
        sys.stderr.write("Error: --run-id is required (or use --list).\n")
        return 2

    run_dir = benchmark_root / args.run_id
    if not run_dir.is_dir():
        sys.stderr.write(f"Error: Run directory not found: {run_dir}\n")
        return 1

    try:
        artifacts = _load_artifacts(run_dir)
        quality_warnings = compute_quality_warnings(
            summary=artifacts["summary"],
            phase_analytics=artifacts["phase_analytics"],
            token_economics=artifacts["token_economics"],
            timing_profile=artifacts["timing_profile"],
            provider_projection=artifacts["provider_projection"],
            ledger_exists=artifacts["ledger_exists"],
        )

        # --json mode
        if args.json_mode:
            output = format_json_report(
                run_id=args.run_id,
                summary=artifacts["summary"],
                phase_analytics=artifacts["phase_analytics"],
                token_economics=artifacts["token_economics"],
                timing_profile=artifacts["timing_profile"],
                provider_projection=artifacts["provider_projection"],
                quality_warnings=quality_warnings,
                loaded_artifacts=artifacts["loaded_artifacts"],
            )
            sys.stdout.write(output)
            return 0

        # --section mode
        if args.section:
            output = _render_section(args.section, artifacts, quality_warnings)
            sys.stdout.write(output)
            return 0

        # Full report (default)
        output = format_full_report(
            summary=artifacts["summary"],
            phase_analytics=artifacts["phase_analytics"],
            token_economics=artifacts["token_economics"],
            timing_profile=artifacts["timing_profile"],
            provider_projection=artifacts["provider_projection"],
            quality_warnings=quality_warnings,
        )
        sys.stdout.write(output)
        return 0

    except Exception as exc:
        sys.stderr.write(f"Internal error: {exc}\n")
        return 3


if __name__ == "__main__":
    sys.exit(main())
