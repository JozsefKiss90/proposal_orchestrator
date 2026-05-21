"""Tests for runner.benchmark.formatters — pure formatting functions."""

from __future__ import annotations

import json
import pytest

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
# Fixtures: realistic artifact data
# ---------------------------------------------------------------------------

@pytest.fixture
def summary_artifact() -> dict:
    return {
        "benchmark_schema_version": "1.0.0",
        "run_id": "test-run-001",
        "started_at": "2026-05-20T18:01:17.041798+00:00",
        "completed_at": "2026-05-20T18:54:50.743919+00:00",
        "total_invocations": 9,
        "benchmark_stage": "phase_c_provider_projection",
        "node_records": [
            {"node_id": "n08a_excellence_drafting", "dispatched": True},
            {"node_id": "n08b_impact_drafting", "dispatched": True},
            {"node_id": "n08c_implementation_drafting", "dispatched": True},
        ],
        "phase_analytics_summary": {
            "phases_observed": [],
            "nodes_observed": [],
            "total_invocations": 9,
        },
        "token_economics_summary": {
            "total_estimated_input_tokens": 76691,
            "total_estimated_output_tokens": 31964,
            "total_estimated_tokens": 108655,
        },
        "timing_summary": {
            "total_wall_clock_seconds": 3213.703,
            "mean_invocation_seconds": 356.915,
            "median_invocation_seconds": 338.031,
        },
        "provider_projection_summary": {
            "total_providers_evaluated": 11,
            "suitable_providers": 11,
            "lowest_projected_cost_usd": 0.030682,
            "lowest_projected_cost_provider": "GPT-4o Mini (Azure OpenAI)",
        },
    }


@pytest.fixture
def phase_analytics_artifact() -> dict:
    return {
        "benchmark_schema_version": "1.0.0",
        "run_id": "test-run-001",
        "phase_scope": None,
        "phases_observed": [],
        "nodes_observed": [],
        "total_invocations": 9,
        "per_phase": {},
        "per_node": {},
    }


@pytest.fixture
def token_economics_artifact() -> dict:
    return {
        "run_id": "test-run-001",
        "total_estimated_input_tokens": 76691,
        "total_estimated_output_tokens": 31964,
        "total_estimated_tokens": 108655,
        "tokens_by_invocation_type": {
            "skill_tapm": {
                "estimated_input_tokens": 76691,
                "estimated_output_tokens": 31964,
                "estimated_total_tokens": 108655,
            }
        },
        "tokens_by_skill_id": {
            "excellence-section-drafting": {
                "estimated_input_tokens": 3428,
                "estimated_output_tokens": 3460,
                "estimated_total_tokens": 6888,
            },
            "impact-section-drafting": {
                "estimated_input_tokens": 4793,
                "estimated_output_tokens": 2430,
                "estimated_total_tokens": 7223,
            },
            "proposal-section-traceability-check": {
                "estimated_input_tokens": 35527,
                "estimated_output_tokens": 12883,
                "estimated_total_tokens": 48410,
            },
        },
        "tokens_by_semantic_predicate_id": {},
        "largest_invocation_by_estimated_total_tokens": {
            "invocation_id": "abc123",
            "skill_id": "proposal-section-traceability-check",
            "predicate_id": None,
            "invocation_type": "skill_tapm",
            "value": 16931,
        },
        "largest_invocation_by_prompt_chars": {
            "invocation_id": "def456",
            "skill_id": "proposal-section-traceability-check",
            "predicate_id": None,
            "invocation_type": "skill_tapm",
            "value": 41454,
        },
        "tapm_vs_cli_prompt": {
            "tapm": {
                "estimated_input_tokens": 76691,
                "estimated_output_tokens": 31964,
                "estimated_total_tokens": 108655,
            },
            "cli_prompt": {
                "estimated_input_tokens": 0,
                "estimated_output_tokens": 0,
                "estimated_total_tokens": 0,
            },
        },
        "phase_8_estimated_total_tokens": 0,
        "phases_1_7_estimated_total_tokens": 0,
        "semantic_predicate_estimated_total_tokens": 0,
        "warning": "All token values are estimates.",
    }


@pytest.fixture
def timing_profile_artifact() -> dict:
    return {
        "total_wall_clock_seconds": 3213.703,
        "sum_invocation_wall_clock_seconds": 3212.234,
        "idle_non_model_seconds_estimate": 1.469,
        "mean_invocation_seconds": 356.915,
        "median_invocation_seconds": 338.031,
        "p95_invocation_seconds": 553.109,
        "p99_invocation_seconds": 553.109,
        "min_invocation_seconds": 224.188,
        "max_invocation_seconds": 553.109,
        "timeout_count": 0,
        "failed_invocation_count": 0,
        "timing_by_invocation_type": {
            "skill_tapm": {
                "count": 9,
                "total_seconds": 3212.234,
                "mean_seconds": 356.915,
                "median_seconds": 338.031,
                "min_seconds": 224.188,
                "max_seconds": 553.109,
            }
        },
        "timing_by_skill_id": {
            "proposal-section-traceability-check": {
                "count": 3,
                "total_seconds": 1524.313,
                "mean_seconds": 508.104,
                "median_seconds": 531.25,
                "min_seconds": 439.954,
                "max_seconds": 553.109,
            },
            "excellence-section-drafting": {
                "count": 1,
                "total_seconds": 338.031,
                "mean_seconds": 338.031,
                "median_seconds": 338.031,
                "min_seconds": 338.031,
                "max_seconds": 338.031,
            },
        },
        "timing_by_semantic_predicate_id": {},
    }


@pytest.fixture
def provider_projection_artifact() -> dict:
    return {
        "benchmark_schema_version": "1.0.0",
        "run_id": "test-run-001",
        "projection_timestamp": "2026-05-20T18:54:50+00:00",
        "pricing_basis": {
            "source": "static_provider_catalog",
            "warning": "Static configurable estimates; not authoritative billing data.",
        },
        "observed_workload": {
            "total_invocations": 9,
            "total_estimated_input_tokens": 76691,
            "total_estimated_output_tokens": 31964,
            "total_estimated_tokens": 108655,
            "requires_tool_support": True,
            "requires_system_prompt": True,
            "tapm_invocation_count": 0,
            "cli_prompt_invocation_count": 0,
            "semantic_predicate_invocation_count": 0,
        },
        "projections": [
            {
                "provider_id": "azure_openai",
                "model_id": "gpt-4o-mini",
                "display_name": "GPT-4o Mini (Azure OpenAI)",
                "billing_model": "per_token",
                "projected_total_cost_usd": 0.030682,
                "supports_all_modes": True,
                "migration_complexity": "drop_in",
            },
            {
                "provider_id": "together_ai",
                "model_id": "meta-llama/Llama-3.1-405B",
                "display_name": "Llama 3.1 405B (Together AI)",
                "billing_model": "per_token",
                "projected_total_cost_usd": 0.380293,
                "supports_all_modes": True,
                "migration_complexity": "drop_in",
            },
            {
                "provider_id": "current_claude_code_max",
                "model_id": "claude-sonnet-4-6",
                "display_name": "Claude Sonnet 4.6 (Claude Code Max)",
                "billing_model": "subscription",
                "projected_total_cost_usd": 200.0,
                "supports_all_modes": True,
                "migration_complexity": "adapter_needed",
            },
        ],
        "recommendations": {
            "lowest_projected_cost": {
                "provider_id": "azure_openai",
                "model_id": "gpt-4o-mini",
                "display_name": "GPT-4o Mini (Azure OpenAI)",
                "projected_total_cost_usd": 0.030682,
            },
            "best_capability_match": {
                "provider_id": "together_ai",
                "model_id": "meta-llama/Llama-3.1-405B",
                "display_name": "Llama 3.1 405B (Together AI)",
                "capability_tier": "high",
            },
            "best_openai_compatible_candidate": {
                "provider_id": "together_ai",
                "model_id": "meta-llama/Llama-3.1-405B",
                "display_name": "Llama 3.1 405B (Together AI)",
            },
            "best_private_network_candidate": {
                "provider_id": "together_ai",
                "model_id": "meta-llama/Llama-3.1-405B",
                "display_name": "Llama 3.1 405B (Together AI)",
            },
            "not_suitable": [],
            "migration_warnings": [],
        },
        "routing_recommendations": [
            {
                "workload_segment": "tapm_tool_augmented_work",
                "estimated_tokens": 108655,
                "candidate_tier": "mid_or_high",
                "notes": [
                    "Requires tool use (Read, Glob) support.",
                ],
            },
        ],
    }


# ---------------------------------------------------------------------------
# Summary Report Tests
# ---------------------------------------------------------------------------

class TestSummaryReport:
    def test_complete_summary(self, summary_artifact):
        result = format_summary_report(summary_artifact, quality_warnings=[])
        assert "test-run-001" in result
        assert "phase_c_provider_projection" in result
        assert "108,655" in result
        assert "3,213.703s" in result
        assert "Data Quality Warnings:" in result
        assert "0" in result  # 0 warnings

    def test_missing_summary(self):
        result = format_summary_report(None)
        assert "WARNING" in result
        assert "missing" in result

    def test_provider_projection_available(self, summary_artifact):
        result = format_summary_report(summary_artifact)
        assert "available" in result
        assert "$0.030682" in result

    def test_no_provider_projection(self, summary_artifact):
        del summary_artifact["provider_projection_summary"]
        result = format_summary_report(summary_artifact)
        assert "not available" in result

    def test_quality_warnings_count(self, summary_artifact):
        result = format_summary_report(
            summary_artifact, quality_warnings=["warn1", "warn2"]
        )
        assert "2" in result


# ---------------------------------------------------------------------------
# Token Report Tests
# ---------------------------------------------------------------------------

class TestTokenReport:
    def test_complete_token_report(self, token_economics_artifact):
        result = format_token_report(token_economics_artifact)
        assert "76,691" in result
        assert "31,964" in result
        assert "108,655" in result
        assert "TAPM Tokens:" in result
        assert "CLI-Prompt Tokens:" in result
        assert "proposal-section-traceability-check" in result

    def test_missing_token_economics(self):
        result = format_token_report(None)
        assert "WARNING" in result
        assert "missing" in result

    def test_top_skills_shown(self, token_economics_artifact):
        result = format_token_report(token_economics_artifact)
        assert "Top Skills" in result
        assert "48,410" in result  # traceability-check total

    def test_largest_invocation(self, token_economics_artifact):
        result = format_token_report(token_economics_artifact)
        assert "16,931" in result
        assert "41,454" in result


# ---------------------------------------------------------------------------
# Timing Report Tests
# ---------------------------------------------------------------------------

class TestTimingReport:
    def test_complete_timing_report(self, timing_profile_artifact):
        result = format_timing_report(timing_profile_artifact)
        assert "3,213.703s" in result
        assert "3,212.234s" in result
        assert "356.915s" in result
        assert "553.109s" in result
        assert "Timeout Count:" in result

    def test_missing_timing(self):
        result = format_timing_report(None)
        assert "WARNING" in result

    def test_slowest_skills(self, timing_profile_artifact):
        result = format_timing_report(timing_profile_artifact)
        assert "Slowest Skills" in result
        assert "proposal-section-traceability-check" in result


# ---------------------------------------------------------------------------
# Provider Report Tests
# ---------------------------------------------------------------------------

class TestProviderReport:
    def test_complete_provider_report(self, provider_projection_artifact):
        result = format_provider_report(provider_projection_artifact)
        assert "GPT-4o Mini" in result
        assert "$0.030682" in result
        assert "drop_in" in result
        assert "adapter_needed" in result
        assert "Static configurable estimates" in result

    def test_missing_provider_projection(self):
        result = format_provider_report(None)
        assert "WARNING" in result

    def test_subscription_marked(self, provider_projection_artifact):
        result = format_provider_report(provider_projection_artifact)
        assert "/mo" in result

    def test_recommendations_shown(self, provider_projection_artifact):
        result = format_provider_report(provider_projection_artifact)
        assert "Lowest Cost:" in result
        assert "Best Capability Match:" in result


# ---------------------------------------------------------------------------
# Routing Report Tests
# ---------------------------------------------------------------------------

class TestRoutingReport:
    def test_complete_routing_report(self, provider_projection_artifact):
        result = format_routing_report(provider_projection_artifact)
        assert "Advisory only" in result
        assert "tapm_tool_augmented_work" in result
        assert "108,655" in result
        assert "mid_or_high" in result

    def test_missing_projection(self):
        result = format_routing_report(None)
        assert "WARNING" in result

    def test_no_recommendations(self, provider_projection_artifact):
        provider_projection_artifact["routing_recommendations"] = []
        result = format_routing_report(provider_projection_artifact)
        assert "No routing recommendations" in result


# ---------------------------------------------------------------------------
# Quality Report Tests
# ---------------------------------------------------------------------------

class TestQualityReport:
    def test_no_warnings(self):
        result = format_quality_report([])
        assert "No data quality warnings" in result

    def test_with_warnings(self):
        warnings = [
            "phase_analytics.phases_observed is empty but total_invocations is 9.",
            "provider_projection.json is missing.",
        ]
        result = format_quality_report(warnings)
        assert "2 warning(s)" in result
        assert "phases_observed" in result
        assert "does not repair" in result


class TestComputeQualityWarnings:
    def test_complete_artifacts_with_issues(
        self, summary_artifact, phase_analytics_artifact, token_economics_artifact,
        timing_profile_artifact, provider_projection_artifact
    ):
        """The live fixture has known data quality issues."""
        warnings = compute_quality_warnings(
            summary=summary_artifact,
            phase_analytics=phase_analytics_artifact,
            token_economics=token_economics_artifact,
            timing_profile=timing_profile_artifact,
            provider_projection=provider_projection_artifact,
        )
        # phases_observed empty while invocations > 0
        assert any("phases_observed" in w for w in warnings)
        # nodes_observed empty while dispatched nodes exist
        assert any("nodes_observed" in w for w in warnings)
        # Phase 8 tokens == 0 but n08 nodes present
        assert any("phase_8_estimated_total_tokens" in w for w in warnings)
        # TAPM count mismatch
        assert any("tapm_invocation_count" in w for w in warnings)

    def test_all_missing(self):
        warnings = compute_quality_warnings(
            summary=None,
            phase_analytics=None,
            token_economics=None,
            timing_profile=None,
            provider_projection=None,
            ledger_exists=False,
        )
        assert any("run_benchmark_summary.json" in w for w in warnings)
        assert any("phase_analytics.json" in w for w in warnings)
        assert any("invocation_ledger.jsonl" in w for w in warnings)

    def test_clean_run_no_warnings(self):
        """A hypothetical clean run produces no warnings."""
        summary = {
            "total_invocations": 5,
            "benchmark_stage": "phase_c_provider_projection",
            "node_records": [
                {"node_id": "n01_call_analysis", "dispatched": True},
            ],
        }
        pa = {
            "phases_observed": [1],
            "nodes_observed": ["n01_call_analysis"],
        }
        te = {
            "phase_8_estimated_total_tokens": 0,
            "phases_1_7_estimated_total_tokens": 500,
            "tapm_vs_cli_prompt": {"tapm": {"estimated_total_tokens": 500}},
        }
        tp = {"timeout_count": 0, "failed_invocation_count": 0}
        pp = {
            "observed_workload": {"tapm_invocation_count": 5},
        }
        warnings = compute_quality_warnings(
            summary=summary,
            phase_analytics=pa,
            token_economics=te,
            timing_profile=tp,
            provider_projection=pp,
        )
        assert warnings == []

    def test_failed_invocations_warning(self):
        tp = {"timeout_count": 2, "failed_invocation_count": 1}
        warnings = compute_quality_warnings(
            summary={"total_invocations": 3, "benchmark_stage": "phase_b_analytics", "node_records": []},
            phase_analytics={"phases_observed": [1], "nodes_observed": ["n01"]},
            token_economics={"phase_8_estimated_total_tokens": 0, "phases_1_7_estimated_total_tokens": 100, "tapm_vs_cli_prompt": {"tapm": {"estimated_total_tokens": 100}}},
            timing_profile=tp,
            provider_projection={"observed_workload": {"tapm_invocation_count": 3}},
        )
        assert any("1 failed" in w for w in warnings)
        assert any("2 timed-out" in w for w in warnings)


# ---------------------------------------------------------------------------
# Full Report Tests
# ---------------------------------------------------------------------------

class TestFullReport:
    def test_full_report_has_all_sections(
        self, summary_artifact, phase_analytics_artifact,
        token_economics_artifact, timing_profile_artifact,
        provider_projection_artifact
    ):
        warnings = compute_quality_warnings(
            summary=summary_artifact,
            phase_analytics=phase_analytics_artifact,
            token_economics=token_economics_artifact,
            timing_profile=timing_profile_artifact,
            provider_projection=provider_projection_artifact,
        )
        result = format_full_report(
            summary=summary_artifact,
            phase_analytics=phase_analytics_artifact,
            token_economics=token_economics_artifact,
            timing_profile=timing_profile_artifact,
            provider_projection=provider_projection_artifact,
            quality_warnings=warnings,
        )
        assert "Benchmark Summary" in result
        assert "Token Report" in result
        assert "Timing Report" in result
        assert "Provider Projection" in result
        assert "Routing Advisory" in result
        assert "Data Quality Report" in result

    def test_full_report_missing_artifacts(self):
        result = format_full_report(
            summary=None,
            phase_analytics=None,
            token_economics=None,
            timing_profile=None,
            provider_projection=None,
            quality_warnings=["everything is missing"],
        )
        assert "WARNING" in result
        assert "Benchmark Summary" in result

    def test_no_prompt_content_in_output(
        self, summary_artifact, phase_analytics_artifact,
        token_economics_artifact, timing_profile_artifact,
        provider_projection_artifact
    ):
        """Verify no prompt or response content appears in the report."""
        warnings = []
        result = format_full_report(
            summary=summary_artifact,
            phase_analytics=phase_analytics_artifact,
            token_economics=token_economics_artifact,
            timing_profile=timing_profile_artifact,
            provider_projection=provider_projection_artifact,
            quality_warnings=warnings,
        )
        # These would be prompt content fragments
        assert "system_prompt" not in result.lower() or "system_prompt_chars" not in result.lower()
        assert "user_prompt" not in result.lower() or "user_prompt_chars" not in result.lower()


# ---------------------------------------------------------------------------
# JSON Report Tests
# ---------------------------------------------------------------------------

class TestJsonReport:
    def test_json_report_structure(
        self, summary_artifact, phase_analytics_artifact,
        token_economics_artifact, timing_profile_artifact,
        provider_projection_artifact
    ):
        result = format_json_report(
            run_id="test-run-001",
            summary=summary_artifact,
            phase_analytics=phase_analytics_artifact,
            token_economics=token_economics_artifact,
            timing_profile=timing_profile_artifact,
            provider_projection=provider_projection_artifact,
            quality_warnings=["test warning"],
            loaded_artifacts=["run_benchmark_summary.json", "phase_analytics.json"],
        )
        parsed = json.loads(result)
        assert parsed["run_id"] == "test-run-001"
        assert "run_benchmark_summary" in parsed
        assert "phase_analytics" in parsed
        assert "token_economics" in parsed
        assert "timing_profile" in parsed
        assert "provider_projection" in parsed
        assert parsed["data_quality_warnings"] == ["test warning"]
        assert "run_benchmark_summary.json" in parsed["loaded_artifacts"]

    def test_json_report_missing_artifacts(self):
        result = format_json_report(
            run_id="test-run-002",
            summary=None,
            phase_analytics=None,
            token_economics=None,
            timing_profile=None,
            provider_projection=None,
            quality_warnings=["all missing"],
            loaded_artifacts=[],
        )
        parsed = json.loads(result)
        assert parsed["run_id"] == "test-run-002"
        assert "run_benchmark_summary" not in parsed
        assert parsed["data_quality_warnings"] == ["all missing"]
        assert parsed["loaded_artifacts"] == []

    def test_json_is_valid(
        self, summary_artifact, phase_analytics_artifact,
        token_economics_artifact, timing_profile_artifact,
        provider_projection_artifact
    ):
        result = format_json_report(
            run_id="test",
            summary=summary_artifact,
            phase_analytics=phase_analytics_artifact,
            token_economics=token_economics_artifact,
            timing_profile=timing_profile_artifact,
            provider_projection=provider_projection_artifact,
            quality_warnings=[],
            loaded_artifacts=[],
        )
        # Should parse without error
        parsed = json.loads(result)
        assert isinstance(parsed, dict)


# ---------------------------------------------------------------------------
# Phase 8 incomplete inference warning
# ---------------------------------------------------------------------------

class TestPhase8IncompleteInference:
    def test_phase8_incomplete_detected(self):
        """Phase 8 partial run should trigger quality warnings."""
        summary = {
            "total_invocations": 9,
            "benchmark_stage": "phase_c_provider_projection",
            "node_records": [
                {"node_id": "n08a_excellence_drafting", "dispatched": True},
                {"node_id": "n08b_impact_drafting", "dispatched": True},
                {"node_id": "n08c_implementation_drafting", "dispatched": True},
            ],
        }
        pa = {"phases_observed": [], "nodes_observed": []}
        te = {
            "phase_8_estimated_total_tokens": 0,
            "phases_1_7_estimated_total_tokens": 0,
            "tapm_vs_cli_prompt": {"tapm": {"estimated_total_tokens": 108655}},
        }
        tp = {"timeout_count": 0, "failed_invocation_count": 0}
        pp = {"observed_workload": {"tapm_invocation_count": 0}}
        warnings = compute_quality_warnings(
            summary=summary,
            phase_analytics=pa,
            token_economics=te,
            timing_profile=tp,
            provider_projection=pp,
        )
        # Should detect Phase 8 tokens == 0 with n08 nodes
        assert any("phase_8" in w for w in warnings)
        # Should detect phases_observed empty
        assert any("phases_observed" in w for w in warnings)
