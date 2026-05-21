"""
Benchmark report formatters — pure functions producing human-readable text.

All functions are deterministic, stdlib-only, and produce plain text
suitable for terminal output and snapshot testing.  No color codes,
no external packages, no terminal-width detection.

Artifacts are read-only: formatters never write to benchmark directories.
"""

from __future__ import annotations

import json
from typing import Any


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _val(d: dict | None, *keys: str, default: Any = None) -> Any:
    """Safely traverse nested dicts."""
    cur: Any = d
    for k in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k, default)
    return cur


def _fmt_tokens(n: int | float | None) -> str:
    if n is None:
        return "n/a"
    return f"{int(n):,}"


def _fmt_cost(n: float | None) -> str:
    if n is None:
        return "n/a"
    return f"${n:,.6f}"


def _fmt_seconds(n: float | None) -> str:
    if n is None:
        return "n/a"
    return f"{n:,.3f}s"


def _fmt_pct(n: float | None) -> str:
    if n is None:
        return "n/a"
    return f"{n:.1f}%"


def _section_header(title: str) -> str:
    return f"\n{title}\n{'=' * len(title)}\n"


def _warn_missing(name: str) -> str:
    return f"  [WARNING] {name} artifact is missing — section may be incomplete.\n"


def _kv(label: str, value: str, width: int = 42) -> str:
    return f"  {label:<{width}} {value}\n"


def _table_row(cells: list[str], widths: list[int]) -> str:
    parts = []
    for cell, w in zip(cells, widths):
        parts.append(f"{cell:<{w}}")
    return "  " + "  ".join(parts) + "\n"


def _table_separator(widths: list[int]) -> str:
    total = sum(widths) + 2 * (len(widths) - 1) + 2
    return "  " + "-" * (total) + "\n"


# ---------------------------------------------------------------------------
# Section: Summary
# ---------------------------------------------------------------------------

def format_summary_report(
    summary: dict | None,
    phase_analytics: dict | None = None,
    token_economics: dict | None = None,
    provider_projection: dict | None = None,
    quality_warnings: list[str] | None = None,
) -> str:
    out = _section_header("Benchmark Summary")
    if summary is None:
        out += "  [WARNING] run_benchmark_summary.json is missing.\n"
        return out

    out += _kv("Run ID:", summary.get("run_id", "unknown"))
    out += _kv("Benchmark Stage:", summary.get("benchmark_stage", "unknown"))
    out += _kv("Started:", summary.get("started_at", "unknown"))
    out += _kv("Completed:", summary.get("completed_at", "unknown"))
    out += _kv("Total Invocations:", str(summary.get("total_invocations", 0)))

    # Token summary
    te_sum = summary.get("token_economics_summary", {})
    out += _kv("Estimated Input Tokens:", _fmt_tokens(te_sum.get("total_estimated_input_tokens")))
    out += _kv("Estimated Output Tokens:", _fmt_tokens(te_sum.get("total_estimated_output_tokens")))
    out += _kv("Estimated Total Tokens:", _fmt_tokens(te_sum.get("total_estimated_tokens")))

    # Timing summary
    ts = summary.get("timing_summary", {})
    out += _kv("Total Wall-Clock:", _fmt_seconds(ts.get("total_wall_clock_seconds")))

    # Phase analytics summary
    pa_sum = summary.get("phase_analytics_summary", {})
    phases_obs = pa_sum.get("phases_observed", [])
    nodes_obs = pa_sum.get("nodes_observed", [])
    out += _kv("Phases Observed:", str(phases_obs) if phases_obs else "(none)")
    out += _kv("Nodes Observed:", str(nodes_obs) if nodes_obs else "(none)")

    # Provider projection availability
    pp_sum = summary.get("provider_projection_summary")
    if pp_sum:
        out += _kv("Provider Projection:", "available")
        out += _kv("  Suitable Providers:", str(pp_sum.get("suitable_providers", 0)))
        out += _kv("  Lowest Projected Cost:", _fmt_cost(pp_sum.get("lowest_projected_cost_usd")))
    else:
        out += _kv("Provider Projection:", "not available")

    # Quality warnings count
    wc = len(quality_warnings) if quality_warnings else 0
    out += _kv("Data Quality Warnings:", str(wc))

    return out


# ---------------------------------------------------------------------------
# Section: Tokens
# ---------------------------------------------------------------------------

def format_token_report(
    token_economics: dict | None,
    summary: dict | None = None,
) -> str:
    out = _section_header("Token Report")
    if token_economics is None:
        out += _warn_missing("token_economics.json")
        return out

    out += "  NOTE: All token values are estimates based on char-to-token ratios.\n\n"

    out += _kv("Total Input Tokens:", _fmt_tokens(token_economics.get("total_estimated_input_tokens")))
    out += _kv("Total Output Tokens:", _fmt_tokens(token_economics.get("total_estimated_output_tokens")))
    out += _kv("Total Tokens:", _fmt_tokens(token_economics.get("total_estimated_tokens")))

    # TAPM vs cli-prompt
    tapm_cli = token_economics.get("tapm_vs_cli_prompt", {})
    tapm = tapm_cli.get("tapm", {})
    cli = tapm_cli.get("cli_prompt", {})
    out += "\n"
    out += _kv("TAPM Tokens:", _fmt_tokens(tapm.get("estimated_total_tokens")))
    out += _kv("CLI-Prompt Tokens:", _fmt_tokens(cli.get("estimated_total_tokens")))

    # Semantic predicate tokens
    out += _kv("Semantic Predicate Tokens:", _fmt_tokens(token_economics.get("semantic_predicate_estimated_total_tokens")))

    # Phase 8 vs Phases 1-7
    out += _kv("Phase 8 Tokens:", _fmt_tokens(token_economics.get("phase_8_estimated_total_tokens")))
    out += _kv("Phases 1-7 Tokens:", _fmt_tokens(token_economics.get("phases_1_7_estimated_total_tokens")))

    # Top skills by tokens
    skills = token_economics.get("tokens_by_skill_id", {})
    if skills:
        sorted_skills = sorted(
            skills.items(),
            key=lambda x: x[1].get("estimated_total_tokens", 0),
            reverse=True,
        )
        out += "\n  Top Skills by Estimated Tokens:\n"
        widths = [45, 15]
        out += _table_row(["Skill", "Tokens"], widths)
        out += _table_separator(widths)
        for skill_id, data in sorted_skills[:10]:
            out += _table_row(
                [skill_id, _fmt_tokens(data.get("estimated_total_tokens"))],
                widths,
            )

    # Largest invocation
    largest = token_economics.get("largest_invocation_by_estimated_total_tokens")
    if largest:
        out += "\n"
        out += _kv("Largest Invocation (tokens):", f"{_fmt_tokens(largest.get('value'))} ({largest.get('skill_id', 'unknown')})")

    largest_prompt = token_economics.get("largest_invocation_by_prompt_chars")
    if largest_prompt:
        out += _kv("Largest Invocation (prompt):", f"{_fmt_tokens(largest_prompt.get('value'))} chars ({largest_prompt.get('skill_id', 'unknown')})")

    return out


# ---------------------------------------------------------------------------
# Section: Timing
# ---------------------------------------------------------------------------

def format_timing_report(timing_profile: dict | None) -> str:
    out = _section_header("Timing Report")
    if timing_profile is None:
        out += _warn_missing("timing_profile.json")
        return out

    out += _kv("Total Wall-Clock:", _fmt_seconds(timing_profile.get("total_wall_clock_seconds")))
    out += _kv("Sum Invocation Time:", _fmt_seconds(timing_profile.get("sum_invocation_wall_clock_seconds")))
    out += _kv("Idle / Non-Model Estimate:", _fmt_seconds(timing_profile.get("idle_non_model_seconds_estimate")))
    out += "\n"
    out += _kv("Mean Invocation:", _fmt_seconds(timing_profile.get("mean_invocation_seconds")))
    out += _kv("Median Invocation:", _fmt_seconds(timing_profile.get("median_invocation_seconds")))
    out += _kv("P95 Invocation:", _fmt_seconds(timing_profile.get("p95_invocation_seconds")))
    out += _kv("P99 Invocation:", _fmt_seconds(timing_profile.get("p99_invocation_seconds")))
    out += "\n"
    out += _kv("Timeout Count:", str(timing_profile.get("timeout_count", 0)))
    out += _kv("Failed Invocation Count:", str(timing_profile.get("failed_invocation_count", 0)))

    # Top skills by timing
    skills = timing_profile.get("timing_by_skill_id", {})
    if skills:
        sorted_skills = sorted(
            skills.items(),
            key=lambda x: x[1].get("total_seconds", 0),
            reverse=True,
        )
        out += "\n  Slowest Skills by Total Time:\n"
        widths = [45, 12, 12]
        out += _table_row(["Skill", "Total", "Count"], widths)
        out += _table_separator(widths)
        for skill_id, data in sorted_skills[:10]:
            out += _table_row(
                [
                    skill_id,
                    _fmt_seconds(data.get("total_seconds")),
                    str(data.get("count", 0)),
                ],
                widths,
            )

    return out


# ---------------------------------------------------------------------------
# Section: Providers
# ---------------------------------------------------------------------------

def format_provider_report(provider_projection: dict | None) -> str:
    out = _section_header("Provider Projection")
    if provider_projection is None:
        out += _warn_missing("provider_projection.json")
        return out

    # Pricing basis warning
    pb = provider_projection.get("pricing_basis", {})
    if pb.get("warning"):
        out += f"  NOTE: {pb['warning']}\n\n"

    # Observed workload
    ow = provider_projection.get("observed_workload", {})
    out += _kv("Total Invocations:", str(ow.get("total_invocations", 0)))
    out += _kv("Total Estimated Tokens:", _fmt_tokens(ow.get("total_estimated_tokens")))
    out += _kv("Requires Tool Support:", str(ow.get("requires_tool_support", False)))
    out += "\n"

    # Recommendations
    recs = provider_projection.get("recommendations", {})
    lowest = recs.get("lowest_projected_cost")
    best_cap = recs.get("best_capability_match")
    best_oai = recs.get("best_openai_compatible_candidate")
    best_priv = recs.get("best_private_network_candidate")

    if lowest:
        out += _kv("Lowest Cost:", f"{lowest.get('display_name', 'n/a')} ({_fmt_cost(lowest.get('projected_total_cost_usd'))})")
    if best_cap:
        out += _kv("Best Capability Match:", f"{best_cap.get('display_name', 'n/a')} (tier: {best_cap.get('capability_tier', 'n/a')})")
    if best_oai:
        out += _kv("Best OpenAI-Compatible:", best_oai.get("display_name", "n/a"))
    if best_priv:
        out += _kv("Best Private Network:", best_priv.get("display_name", "n/a"))
    out += "\n"

    # Provider table
    projections = provider_projection.get("projections", [])
    if projections:
        widths = [45, 14, 12, 18]
        out += _table_row(["Provider / Model", "Cost USD", "Suitable", "Migration"], widths)
        out += _table_separator(widths)
        for p in projections:
            cost_str = _fmt_cost(p.get("projected_total_cost_usd"))
            if p.get("billing_model") == "subscription":
                cost_str += " /mo"
            elif p.get("billing_model") == "infrastructure":
                cost_str += " *"
            suitable = "yes" if p.get("supports_all_modes") else "no"
            migration = p.get("migration_complexity", "unknown")
            out += _table_row(
                [p.get("display_name", "unknown"), cost_str, suitable, migration],
                widths,
            )
        out += "\n  * Infrastructure billing: token cost zero, external hardware cost applies.\n"

    # Not suitable
    not_suitable = recs.get("not_suitable", [])
    if not_suitable:
        out += f"\n  Not Suitable: {', '.join(not_suitable)}\n"

    # Migration warnings
    mw = recs.get("migration_warnings", [])
    if mw:
        out += "\n  Migration Warnings:\n"
        for w in mw:
            out += f"    - {w}\n"

    return out


# ---------------------------------------------------------------------------
# Section: Routing Advisory
# ---------------------------------------------------------------------------

def format_routing_report(provider_projection: dict | None) -> str:
    out = _section_header("Routing Advisory")
    if provider_projection is None:
        out += _warn_missing("provider_projection.json")
        return out

    out += "  NOTE: Advisory only — no runtime routing is implemented.\n\n"

    routing = provider_projection.get("routing_recommendations", [])
    if not routing:
        out += "  No routing recommendations available.\n"
        return out

    widths = [35, 15, 18]
    out += _table_row(["Workload Segment", "Est. Tokens", "Candidate Tier"], widths)
    out += _table_separator(widths)
    for r in routing:
        out += _table_row(
            [
                r.get("workload_segment", "unknown"),
                _fmt_tokens(r.get("estimated_tokens")),
                r.get("candidate_tier", "unknown"),
            ],
            widths,
        )
        notes = r.get("notes", [])
        for note in notes:
            out += f"      {note}\n"

    return out


# ---------------------------------------------------------------------------
# Section: Data Quality
# ---------------------------------------------------------------------------

def compute_quality_warnings(
    summary: dict | None,
    phase_analytics: dict | None,
    token_economics: dict | None,
    timing_profile: dict | None,
    provider_projection: dict | None,
    ledger_exists: bool = True,
) -> list[str]:
    """Compute data-quality warnings from loaded artifacts.

    Returns a list of human-readable warning strings.
    """
    warnings: list[str] = []

    # Missing artifacts
    if summary is None:
        warnings.append("run_benchmark_summary.json is missing.")
    if phase_analytics is None:
        warnings.append("phase_analytics.json is missing.")
    if token_economics is None:
        warnings.append("token_economics.json is missing.")
    if timing_profile is None:
        warnings.append("timing_profile.json is missing.")
    if provider_projection is None:
        warnings.append("provider_projection.json is missing.")
    if not ledger_exists:
        warnings.append("invocation_ledger.jsonl is missing.")

    total_invocations = _val(summary, "total_invocations", default=0)

    # phases_observed empty while invocations > 0
    pa_phases = _val(phase_analytics, "phases_observed", default=[])
    if total_invocations > 0 and not pa_phases:
        warnings.append(
            "phase_analytics.phases_observed is empty but "
            f"total_invocations is {total_invocations}."
        )

    # nodes_observed empty while node_records has dispatched nodes
    pa_nodes = _val(phase_analytics, "nodes_observed", default=[])
    node_records = _val(summary, "node_records", default=[])
    dispatched = [n for n in node_records if n.get("dispatched")]
    if dispatched and not pa_nodes:
        warnings.append(
            "phase_analytics.nodes_observed is empty but "
            f"node_records contains {len(dispatched)} dispatched node(s)."
        )

    # Phase 8 tokens == 0 but n08* nodes present
    p8_tokens = _val(token_economics, "phase_8_estimated_total_tokens", default=0)
    n08_nodes = [n for n in node_records if n.get("node_id", "").startswith("n08")]
    if n08_nodes and p8_tokens == 0:
        warnings.append(
            "phase_8_estimated_total_tokens is 0 but "
            f"node_records contains {len(n08_nodes)} Phase 8 node(s)."
        )

    # Phases 1-7 tokens == 0 but n01-n07 nodes present
    p17_tokens = _val(token_economics, "phases_1_7_estimated_total_tokens", default=0)
    n17_nodes = [
        n for n in node_records
        if n.get("node_id", "")[:3] in ("n01", "n02", "n03", "n04", "n05", "n06", "n07")
    ]
    if n17_nodes and p17_tokens == 0:
        warnings.append(
            "phases_1_7_estimated_total_tokens is 0 but "
            f"node_records contains {len(n17_nodes)} Phase 1-7 node(s)."
        )

    # TAPM count mismatch
    pp_tapm = _val(provider_projection, "observed_workload", "tapm_invocation_count", default=0)
    te_tapm = _val(token_economics, "tapm_vs_cli_prompt", "tapm", "estimated_total_tokens", default=0)
    if pp_tapm == 0 and te_tapm > 0:
        warnings.append(
            "provider_projection.observed_workload.tapm_invocation_count is 0 "
            "while token_economics TAPM total tokens > 0."
        )

    # Stale benchmark stage
    stage = _val(summary, "benchmark_stage", default="")
    if stage and stage not in ("phase_c_provider_projection", "phase_b_analytics"):
        warnings.append(
            f"benchmark_stage is '{stage}' — expected 'phase_b_analytics' or "
            "'phase_c_provider_projection'."
        )

    # Failed invocations
    failed = _val(timing_profile, "failed_invocation_count", default=0)
    if failed > 0:
        warnings.append(f"Run has {failed} failed invocation(s).")

    timeout_count = _val(timing_profile, "timeout_count", default=0)
    if timeout_count > 0:
        warnings.append(f"Run has {timeout_count} timed-out invocation(s).")

    return warnings


def format_quality_report(
    quality_warnings: list[str],
) -> str:
    out = _section_header("Data Quality Report")
    if not quality_warnings:
        out += "  No data quality warnings detected.\n"
        return out

    out += f"  {len(quality_warnings)} warning(s) detected:\n\n"
    for i, w in enumerate(quality_warnings, 1):
        out += f"  {i:>3}. {w}\n"

    out += "\n  NOTE: Phase D does not repair these issues — it only reports them.\n"
    return out


# ---------------------------------------------------------------------------
# Composite reports
# ---------------------------------------------------------------------------

def format_full_report(
    summary: dict | None,
    phase_analytics: dict | None,
    token_economics: dict | None,
    timing_profile: dict | None,
    provider_projection: dict | None,
    quality_warnings: list[str],
) -> str:
    """Produce the complete human-readable benchmark report."""
    parts = [
        format_summary_report(
            summary,
            phase_analytics=phase_analytics,
            token_economics=token_economics,
            provider_projection=provider_projection,
            quality_warnings=quality_warnings,
        ),
        format_token_report(token_economics, summary=summary),
        format_timing_report(timing_profile),
        format_provider_report(provider_projection),
        format_routing_report(provider_projection),
        format_quality_report(quality_warnings),
    ]
    return "\n".join(parts)


def format_json_report(
    run_id: str,
    summary: dict | None,
    phase_analytics: dict | None,
    token_economics: dict | None,
    timing_profile: dict | None,
    provider_projection: dict | None,
    quality_warnings: list[str],
    loaded_artifacts: list[str],
) -> str:
    """Produce a JSON report with all loaded artifacts and quality warnings."""
    report: dict[str, Any] = {
        "run_id": run_id,
        "loaded_artifacts": loaded_artifacts,
        "data_quality_warnings": quality_warnings,
    }
    if summary is not None:
        report["run_benchmark_summary"] = summary
    if phase_analytics is not None:
        report["phase_analytics"] = phase_analytics
    if token_economics is not None:
        report["token_economics"] = token_economics
    if timing_profile is not None:
        report["timing_profile"] = timing_profile
    if provider_projection is not None:
        report["provider_projection"] = provider_projection

    return json.dumps(report, indent=2, ensure_ascii=False) + "\n"
