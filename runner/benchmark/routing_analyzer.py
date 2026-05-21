"""
Phase C routing analyzer — offline advisory workload classification.

Classifies observed benchmark workload into segments and produces advisory
routing recommendations. This is NOT runtime routing. It does not modify
scheduler behavior, transport configuration, or orchestration outcomes.

All output is advisory-only and included in provider_projection.json.
"""

from __future__ import annotations

from typing import Any


def classify_workload_segments(
    token_economics: dict,
    phase_analytics: dict | None = None,
) -> list[dict[str, Any]]:
    """Classify observed workload into advisory segments.

    Parameters
    ----------
    token_economics
        Phase B token_economics.json payload.
    phase_analytics
        Phase B phase_analytics.json payload (optional).

    Returns
    -------
    list[dict]
        List of workload segment classifications with advisory notes.
    """
    segments: list[dict[str, Any]] = []

    tapm_data = token_economics.get("tapm_vs_cli_prompt", {})
    tapm_tokens = tapm_data.get("tapm", {}).get("estimated_total_tokens", 0)
    cli_tokens = tapm_data.get("cli_prompt", {}).get("estimated_total_tokens", 0)
    sem_pred_tokens = token_economics.get(
        "semantic_predicate_estimated_total_tokens", 0
    )
    phase8_tokens = token_economics.get("phase_8_estimated_total_tokens", 0)
    phases_1_7_tokens = token_economics.get(
        "phases_1_7_estimated_total_tokens", 0
    )

    # Segment: phases 1-7 skill work
    if phases_1_7_tokens > 0:
        candidate_tier = _tier_for_extraction_work(phases_1_7_tokens)
        segments.append({
            "workload_segment": "phase_1_7_skill_work",
            "estimated_tokens": phases_1_7_tokens,
            "candidate_tier": candidate_tier,
            "notes": [
                "Structured extraction/normalization workload.",
                "Validate quality before downshifting to lower-tier models.",
            ],
        })

    # Segment: phase 8 drafting work
    if phase8_tokens > 0:
        segments.append({
            "workload_segment": "phase_8_drafting_work",
            "estimated_tokens": phase8_tokens,
            "candidate_tier": "high",
            "notes": [
                "Evaluator-oriented drafting requires high capability.",
                "Quality is critical — do not downshift without validation.",
            ],
        })

    # Segment: semantic predicate work
    if sem_pred_tokens > 0:
        segments.append({
            "workload_segment": "semantic_predicate_work",
            "estimated_tokens": sem_pred_tokens,
            "candidate_tier": "mid_or_high",
            "notes": [
                "Gate predicate evaluation — binary/structured output.",
                "May tolerate mid-tier models if output format is validated.",
            ],
        })

    # Segment: TAPM tool-augmented work
    if tapm_tokens > 0:
        segments.append({
            "workload_segment": "tapm_tool_augmented_work",
            "estimated_tokens": tapm_tokens,
            "candidate_tier": "mid_or_high",
            "notes": [
                "Requires tool use (Read, Glob) support.",
                "Provider must support function calling / tool use API.",
            ],
        })

    # Segment: CLI prompt work (no tools)
    if cli_tokens > 0:
        segments.append({
            "workload_segment": "cli_prompt_work",
            "estimated_tokens": cli_tokens,
            "candidate_tier": "mid",
            "notes": [
                "Plain prompt-response work without tool use.",
                "Broader provider compatibility — no tool support required.",
            ],
        })

    return segments


def build_routing_recommendations(
    token_economics: dict,
    phase_analytics: dict | None = None,
) -> list[dict[str, Any]]:
    """Build advisory routing recommendations from workload classification.

    Returns the same structure as classify_workload_segments but labeled
    as routing_recommendations for inclusion in provider_projection.json.
    """
    return classify_workload_segments(token_economics, phase_analytics)


def _tier_for_extraction_work(token_count: int) -> str:
    """Suggest candidate tier for extraction/normalization workload."""
    # Extraction quality is important — suggest mid_or_high for non-trivial loads
    if token_count > 100_000:
        return "high"
    return "mid_or_high"
