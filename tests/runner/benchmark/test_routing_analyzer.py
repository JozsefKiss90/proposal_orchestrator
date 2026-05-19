"""Tests for runner.benchmark.routing_analyzer — offline advisory workload classification."""

import pytest

from runner.benchmark.routing_analyzer import (
    classify_workload_segments,
    build_routing_recommendations,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _base_token_economics(**overrides) -> dict:
    """Create a minimal token_economics dict with overrides."""
    te = {
        "run_id": "test-run",
        "total_estimated_input_tokens": 40000,
        "total_estimated_output_tokens": 22000,
        "total_estimated_tokens": 62000,
        "tapm_vs_cli_prompt": {
            "tapm": {"estimated_total_tokens": 62000},
            "cli_prompt": {"estimated_total_tokens": 0},
        },
        "phase_8_estimated_total_tokens": 0,
        "phases_1_7_estimated_total_tokens": 62000,
        "semantic_predicate_estimated_total_tokens": 0,
    }
    te.update(overrides)
    return te


def _base_phase_analytics(**overrides) -> dict:
    pa = {
        "total_invocations": 4,
        "per_phase": {
            "1": {
                "invocations": 4,
                "tapm_count": 4,
                "cli_prompt_count": 0,
                "semantic_predicate_count": 0,
            },
        },
    }
    pa.update(overrides)
    return pa


# ---------------------------------------------------------------------------
# Workload classification
# ---------------------------------------------------------------------------

class TestWorkloadClassification:
    def test_classifies_tapm_workload(self):
        te = _base_token_economics()
        segments = classify_workload_segments(te)

        tapm = [s for s in segments if s["workload_segment"] == "tapm_tool_augmented_work"]
        assert len(tapm) == 1
        assert tapm[0]["estimated_tokens"] == 62000
        assert "tool use" in tapm[0]["notes"][1].lower() or "tool" in tapm[0]["notes"][1].lower()

    def test_classifies_phase_1_7_workload(self):
        te = _base_token_economics()
        segments = classify_workload_segments(te)

        p17 = [s for s in segments if s["workload_segment"] == "phase_1_7_skill_work"]
        assert len(p17) == 1
        assert p17[0]["estimated_tokens"] == 62000
        assert p17[0]["candidate_tier"] in ("mid_or_high", "high")

    def test_classifies_phase_8_workload(self):
        te = _base_token_economics(phase_8_estimated_total_tokens=50000)
        segments = classify_workload_segments(te)

        p8 = [s for s in segments if s["workload_segment"] == "phase_8_drafting_work"]
        assert len(p8) == 1
        assert p8[0]["estimated_tokens"] == 50000
        assert p8[0]["candidate_tier"] == "high"

    def test_classifies_semantic_predicate_workload(self):
        te = _base_token_economics(semantic_predicate_estimated_total_tokens=5000)
        segments = classify_workload_segments(te)

        sp = [s for s in segments if s["workload_segment"] == "semantic_predicate_work"]
        assert len(sp) == 1
        assert sp[0]["estimated_tokens"] == 5000

    def test_classifies_cli_prompt_workload(self):
        te = _base_token_economics()
        te["tapm_vs_cli_prompt"]["cli_prompt"]["estimated_total_tokens"] = 10000
        segments = classify_workload_segments(te)

        cli = [s for s in segments if s["workload_segment"] == "cli_prompt_work"]
        assert len(cli) == 1
        assert cli[0]["estimated_tokens"] == 10000

    def test_empty_workload(self):
        te = {
            "tapm_vs_cli_prompt": {
                "tapm": {"estimated_total_tokens": 0},
                "cli_prompt": {"estimated_total_tokens": 0},
            },
            "phase_8_estimated_total_tokens": 0,
            "phases_1_7_estimated_total_tokens": 0,
            "semantic_predicate_estimated_total_tokens": 0,
        }
        segments = classify_workload_segments(te)
        assert segments == []

    def test_no_phase_8_produces_no_phase_8_segment(self):
        te = _base_token_economics()  # phase_8 = 0 by default
        segments = classify_workload_segments(te)

        p8 = [s for s in segments if s["workload_segment"] == "phase_8_drafting_work"]
        assert len(p8) == 0

    def test_no_semantic_predicate_produces_no_segment(self):
        te = _base_token_economics()  # sem_pred = 0 by default
        segments = classify_workload_segments(te)

        sp = [s for s in segments if s["workload_segment"] == "semantic_predicate_work"]
        assert len(sp) == 0


# ---------------------------------------------------------------------------
# Routing recommendations
# ---------------------------------------------------------------------------

class TestRoutingRecommendations:
    def test_produces_advisory_recommendations(self):
        te = _base_token_economics()
        recs = build_routing_recommendations(te)

        assert isinstance(recs, list)
        for rec in recs:
            assert "workload_segment" in rec
            assert "estimated_tokens" in rec
            assert "candidate_tier" in rec
            assert "notes" in rec

    def test_advisory_only_no_runtime_keys(self):
        te = _base_token_economics()
        recs = build_routing_recommendations(te)

        for rec in recs:
            # Should not contain runtime routing keys
            assert "endpoint" not in rec
            assert "api_key" not in rec
            assert "provider_url" not in rec
            assert "route_to" not in rec

    def test_handles_empty_workload(self):
        te = {
            "tapm_vs_cli_prompt": {
                "tapm": {"estimated_total_tokens": 0},
                "cli_prompt": {"estimated_total_tokens": 0},
            },
            "phase_8_estimated_total_tokens": 0,
            "phases_1_7_estimated_total_tokens": 0,
            "semantic_predicate_estimated_total_tokens": 0,
        }
        recs = build_routing_recommendations(te)
        assert recs == []

    def test_high_token_extraction_recommends_high_tier(self):
        te = _base_token_economics(phases_1_7_estimated_total_tokens=200000)
        segments = classify_workload_segments(te)
        p17 = [s for s in segments if s["workload_segment"] == "phase_1_7_skill_work"]
        assert len(p17) == 1
        assert p17[0]["candidate_tier"] == "high"
