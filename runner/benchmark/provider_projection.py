"""
Phase C provider projection — offline cost/feasibility projection over benchmark data.

Reads Phase B artifacts (token_economics.json, phase_analytics.json) and a static
provider catalog to produce provider_projection.json: per-provider cost estimates,
feasibility checks, migration complexity, security posture, and recommendations.

This module is read-only over existing benchmark artifacts. It does not:
- make provider API calls
- fetch live pricing
- modify transport, scheduler, or orchestration behavior
- write to docs/ (Tier 1-5)

All projections are deterministic and offline.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Default catalog path relative to repo root
_DEFAULT_CATALOG_REL = ".claude/benchmark/config/provider_catalog.json"


def build_provider_projection(
    bench_dir: Path,
    *,
    catalog_path: Path | None = None,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Build provider projection from Phase B artifacts and static catalog.

    Parameters
    ----------
    bench_dir
        Path to ``.claude/benchmark/<run_id>/`` containing Phase B artifacts.
    catalog_path
        Explicit path to provider_catalog.json. If None, uses default location.
    repo_root
        Repository root for resolving default catalog path.

    Returns
    -------
    dict
        The provider_projection.json payload.

    Raises
    ------
    FileNotFoundError
        If required Phase B artifacts are missing.
    """
    # Load catalog
    catalog = _load_catalog(catalog_path, repo_root=repo_root, bench_dir=bench_dir)

    # Load Phase B artifacts
    token_economics = _read_json(bench_dir / "token_economics.json")
    phase_analytics = _read_json(bench_dir / "phase_analytics.json")
    summary = _read_json(bench_dir / "run_benchmark_summary.json")

    if token_economics is None:
        raise FileNotFoundError(f"token_economics.json not found in {bench_dir}")

    # Extract observed workload
    observed = _extract_observed_workload(token_economics, phase_analytics)

    # Build per-provider projections
    projections = []
    for provider in catalog.get("providers", []):
        for model in provider.get("models", []):
            proj = _project_provider_model(
                provider=provider,
                model=model,
                observed=observed,
            )
            projections.append(proj)

    # Build recommendations
    recommendations = _build_recommendations(projections)

    run_id = ""
    if summary:
        run_id = summary.get("run_id", "")
    elif token_economics:
        run_id = token_economics.get("run_id", "")

    return {
        "benchmark_schema_version": "1.0.0",
        "run_id": run_id,
        "projection_timestamp": datetime.now(timezone.utc).isoformat(),
        "pricing_basis": {
            "source": "static_provider_catalog",
            "warning": "Static configurable estimates; not authoritative billing data.",
        },
        "observed_workload": observed,
        "projections": projections,
        "recommendations": recommendations,
    }


# ---------------------------------------------------------------------------
# Observed workload extraction
# ---------------------------------------------------------------------------

def _extract_observed_workload(
    token_economics: dict,
    phase_analytics: dict | None,
) -> dict[str, Any]:
    """Extract observed workload summary from Phase B artifacts."""
    total_in = token_economics.get("total_estimated_input_tokens", 0)
    total_out = token_economics.get("total_estimated_output_tokens", 0)
    total_all = token_economics.get("total_estimated_tokens", total_in + total_out)

    # Max single invocation tokens
    largest_by_tokens = token_economics.get(
        "largest_invocation_by_estimated_total_tokens"
    )
    max_single_total = 0
    if isinstance(largest_by_tokens, dict):
        max_single_total = largest_by_tokens.get("value", 0)

    # Estimate max single input/output from the largest invocation
    # We don't have per-invocation breakdown in token_economics, so use totals
    # as conservative upper bound for single invocation
    max_single_input = max_single_total  # conservative: assume all could be input
    max_single_output = max_single_total  # conservative: assume all could be output

    # TAPM vs CLI
    tapm_data = token_economics.get("tapm_vs_cli_prompt", {})
    tapm_total = tapm_data.get("tapm", {}).get("estimated_total_tokens", 0)
    cli_total = tapm_data.get("cli_prompt", {}).get("estimated_total_tokens", 0)

    # Invocation counts from phase_analytics
    total_invocations = 0
    tapm_count = 0
    cli_count = 0
    sem_pred_count = 0

    if phase_analytics:
        total_invocations = phase_analytics.get("total_invocations", 0)
        # Aggregate from per_phase or per_node
        for details in (phase_analytics.get("per_phase") or {}).values():
            if isinstance(details, dict):
                tapm_count += details.get("tapm_count", 0)
                cli_count += details.get("cli_prompt_count", 0)
                sem_pred_count += details.get("semantic_predicate_count", 0)

    # Determine if tool support is required
    requires_tool_support = tapm_count > 0 or tapm_total > 0

    phase8_tokens = token_economics.get("phase_8_estimated_total_tokens", 0)
    phases_1_7_tokens = token_economics.get("phases_1_7_estimated_total_tokens", 0)
    sem_pred_tokens = token_economics.get(
        "semantic_predicate_estimated_total_tokens", 0
    )

    return {
        "total_invocations": total_invocations,
        "total_estimated_input_tokens": total_in,
        "total_estimated_output_tokens": total_out,
        "total_estimated_tokens": total_all,
        "max_single_invocation_input_tokens": max_single_input,
        "max_single_invocation_output_tokens": max_single_output,
        "max_single_invocation_total_tokens": max_single_total,
        "requires_tool_support": requires_tool_support,
        "requires_system_prompt": True,  # all invocations use system prompts
        "tapm_invocation_count": tapm_count,
        "cli_prompt_invocation_count": cli_count,
        "semantic_predicate_invocation_count": sem_pred_count,
        "phase_8_estimated_total_tokens": phase8_tokens,
        "phases_1_7_estimated_total_tokens": phases_1_7_tokens,
    }


# ---------------------------------------------------------------------------
# Per-provider/model projection
# ---------------------------------------------------------------------------

def _project_provider_model(
    *,
    provider: dict,
    model: dict,
    observed: dict,
) -> dict[str, Any]:
    """Build projection for a single provider/model combination."""
    provider_id = provider.get("provider_id", "unknown")
    model_id = model.get("model_id", "unknown")
    billing_model = provider.get("billing_model", "per_token")

    total_in = observed.get("total_estimated_input_tokens", 0)
    total_out = observed.get("total_estimated_output_tokens", 0)
    max_single_total = observed.get("max_single_invocation_total_tokens", 0)
    requires_tools = observed.get("requires_tool_support", False)
    tapm_count = observed.get("tapm_invocation_count", 0)

    # Cost projection
    projected_input_cost = 0.0
    projected_output_cost = 0.0
    projected_total_cost: float | None = 0.0

    if billing_model == "per_token":
        input_cpm = model.get("input_cost_per_mtok", 0.0)
        output_cpm = model.get("output_cost_per_mtok", 0.0)
        projected_input_cost = round(total_in / 1_000_000 * input_cpm, 6)
        projected_output_cost = round(total_out / 1_000_000 * output_cpm, 6)
        projected_total_cost = round(projected_input_cost + projected_output_cost, 6)
    elif billing_model == "subscription":
        projected_total_cost = provider.get("estimated_monthly_cost_usd")
        projected_input_cost = 0.0
        projected_output_cost = 0.0
    elif billing_model == "infrastructure":
        projected_total_cost = 0.0
        projected_input_cost = 0.0
        projected_output_cost = 0.0

    # Feasibility checks
    max_context = model.get("max_context_tokens", 0)
    context_sufficient = max_single_total <= max_context if max_context > 0 else False
    oversized = _count_oversized_invocations(observed, max_context)

    tool_support = model.get("supports_tools", False)
    tool_sufficient = tool_support or not requires_tools

    system_prompt_supported = model.get("supports_system_prompt", True)

    supports_all_modes = context_sufficient and tool_sufficient and system_prompt_supported

    openai_compatible = model.get("openai_compatible", False)

    # Migration complexity
    migration = _determine_migration_complexity(
        openai_compatible=openai_compatible,
        tool_support=tool_support,
        requires_tools=requires_tools,
        context_sufficient=context_sufficient,
        system_prompt_supported=system_prompt_supported,
        model=model,
        provider=provider,
    )

    # Capability tier
    capability_tier = model.get("capability_tier", "unknown")

    # Security posture
    sec = provider.get("security_posture", {})
    security_posture = {
        "private_networking_possible": sec.get("private_networking_possible", False),
        "data_residency_possible": sec.get("data_residency_possible", False),
        "zero_data_retention_possible": sec.get("zero_data_retention_possible", False),
        "notes": sec.get("notes", []),
    }

    # Warnings
    warnings = _build_warnings(
        billing_model=billing_model,
        context_sufficient=context_sufficient,
        tool_sufficient=tool_sufficient,
        system_prompt_supported=system_prompt_supported,
        oversized=oversized,
        tapm_count=tapm_count,
        model=model,
        provider=provider,
    )

    return {
        "provider_id": provider_id,
        "model_id": model_id,
        "display_name": model.get("display_name", f"{provider_id}/{model_id}"),
        "billing_model": billing_model,
        "projected_input_cost_usd": projected_input_cost,
        "projected_output_cost_usd": projected_output_cost,
        "projected_total_cost_usd": projected_total_cost,
        "context_window_sufficient": context_sufficient,
        "oversized_invocations": oversized,
        "tool_support_sufficient": tool_sufficient,
        "system_prompt_supported": system_prompt_supported,
        "supports_all_modes": supports_all_modes,
        "openai_compatible": openai_compatible,
        "migration_complexity": migration,
        "capability_tier": capability_tier,
        "security_posture": security_posture,
        "warnings": warnings,
    }


def _count_oversized_invocations(observed: dict, max_context: int) -> int:
    """Count invocations that would exceed the context window.

    Since we only have aggregate max_single_invocation_total_tokens,
    return 0 if that fits, or conservatively report total_invocations
    as oversized if it doesn't fit (we lack per-invocation detail).
    """
    if max_context <= 0:
        return observed.get("total_invocations", 0)
    max_single = observed.get("max_single_invocation_total_tokens", 0)
    if max_single > max_context:
        # At least 1 invocation is oversized; without per-invocation data,
        # report 1 as minimum (conservative lower bound)
        return 1
    return 0


def _determine_migration_complexity(
    *,
    openai_compatible: bool,
    tool_support: bool,
    requires_tools: bool,
    context_sufficient: bool,
    system_prompt_supported: bool,
    model: dict,
    provider: dict,
) -> str:
    """Classify migration complexity for a provider/model."""
    if not context_sufficient or not system_prompt_supported:
        return "not_suitable"
    if requires_tools and not tool_support:
        return "not_suitable"
    if openai_compatible and tool_support and context_sufficient:
        return "drop_in"
    if not openai_compatible and tool_support and context_sufficient:
        hint = model.get("migration_complexity_hint")
        if hint:
            return hint
        return "adapter_needed"
    return "significant_work"


def _build_warnings(
    *,
    billing_model: str,
    context_sufficient: bool,
    tool_sufficient: bool,
    system_prompt_supported: bool,
    oversized: int,
    tapm_count: int,
    model: dict,
    provider: dict,
) -> list[str]:
    """Build warning list for a provider/model projection."""
    warnings: list[str] = []
    if billing_model == "subscription":
        warnings.append(
            "Subscription billing — projected cost is monthly subscription, not per-run."
        )
    if billing_model == "infrastructure":
        warnings.append(
            "Infrastructure billing — token cost is zero but GPU/power/maintenance cost is external."
        )
    if not context_sufficient:
        warnings.append(
            f"Context window insufficient: max invocation tokens exceed model limit "
            f"({model.get('max_context_tokens', 'unknown')} tokens)."
        )
    if not tool_sufficient:
        warnings.append(
            f"Tool support missing: {tapm_count} TAPM invocations require tool use."
        )
    if not system_prompt_supported:
        warnings.append("System prompt not supported by this model.")
    if oversized > 0:
        warnings.append(
            f"{oversized} invocation(s) estimated to exceed context window."
        )
    if model.get("requires_gpu"):
        warnings.append("Requires GPU hardware for local deployment.")
    return warnings


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------

def _build_recommendations(projections: list[dict]) -> dict[str, Any]:
    """Build recommendation summary from all projections."""
    suitable = [
        p for p in projections if p.get("supports_all_modes", False)
    ]
    not_suitable = [
        p["display_name"] for p in projections
        if not p.get("supports_all_modes", False)
    ]

    # Lowest cost among suitable per-token providers
    per_token_suitable = [
        p for p in suitable
        if p.get("billing_model") == "per_token"
        and isinstance(p.get("projected_total_cost_usd"), (int, float))
        and p["projected_total_cost_usd"] is not None
    ]
    lowest_cost = None
    if per_token_suitable:
        best = min(per_token_suitable, key=lambda p: p["projected_total_cost_usd"])
        lowest_cost = {
            "provider_id": best["provider_id"],
            "model_id": best["model_id"],
            "display_name": best["display_name"],
            "projected_total_cost_usd": best["projected_total_cost_usd"],
        }

    # Best capability match: highest-tier suitable provider
    tier_order = {"high": 0, "mid": 1, "low": 2, "unknown": 3}
    best_capability = None
    if suitable:
        best = min(
            suitable,
            key=lambda p: tier_order.get(p.get("capability_tier", "unknown"), 3),
        )
        best_capability = {
            "provider_id": best["provider_id"],
            "model_id": best["model_id"],
            "display_name": best["display_name"],
            "capability_tier": best.get("capability_tier"),
        }

    # Best OpenAI-compatible candidate
    oai_suitable = [p for p in suitable if p.get("openai_compatible", False)]
    best_oai = None
    if oai_suitable:
        best = min(
            oai_suitable,
            key=lambda p: (
                tier_order.get(p.get("capability_tier", "unknown"), 3),
                p.get("projected_total_cost_usd") or float("inf"),
            ),
        )
        best_oai = {
            "provider_id": best["provider_id"],
            "model_id": best["model_id"],
            "display_name": best["display_name"],
        }

    # Best private network candidate
    private_suitable = [
        p for p in suitable
        if p.get("security_posture", {}).get("private_networking_possible", False)
    ]
    best_private = None
    if private_suitable:
        best = min(
            private_suitable,
            key=lambda p: tier_order.get(p.get("capability_tier", "unknown"), 3),
        )
        best_private = {
            "provider_id": best["provider_id"],
            "model_id": best["model_id"],
            "display_name": best["display_name"],
        }

    # Migration warnings
    migration_warnings: list[str] = []
    for p in projections:
        mc = p.get("migration_complexity")
        if mc == "significant_work":
            migration_warnings.append(
                f"{p['display_name']}: significant migration work required."
            )
        elif mc == "not_suitable":
            migration_warnings.append(
                f"{p['display_name']}: not suitable for current workload."
            )

    return {
        "lowest_projected_cost": lowest_cost,
        "best_capability_match": best_capability,
        "best_openai_compatible_candidate": best_oai,
        "best_private_network_candidate": best_private,
        "not_suitable": not_suitable,
        "migration_warnings": migration_warnings,
    }


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def _load_catalog(
    catalog_path: Path | None,
    *,
    repo_root: Path | None = None,
    bench_dir: Path | None = None,
) -> dict:
    """Load provider catalog JSON."""
    if catalog_path and catalog_path.exists():
        return _read_json(catalog_path) or {}

    # Try to find catalog relative to repo root
    if repo_root:
        default = repo_root / _DEFAULT_CATALOG_REL
        if default.exists():
            return _read_json(default) or {}

    # Try to infer repo root from bench_dir (.claude/benchmark/<run_id>/)
    if bench_dir:
        candidate = bench_dir.parent.parent.parent / _DEFAULT_CATALOG_REL
        if candidate.exists():
            return _read_json(candidate) or {}

    logger.warning("Provider catalog not found; projection will have no providers.")
    return {"providers": []}


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
