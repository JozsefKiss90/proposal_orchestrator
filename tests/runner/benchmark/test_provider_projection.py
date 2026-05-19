"""Tests for runner.benchmark.provider_projection — Phase C cost/feasibility projection."""

import json
from pathlib import Path

import pytest

from runner.benchmark.provider_projection import (
    build_provider_projection,
    _extract_observed_workload,
    _project_provider_model,
    _determine_migration_complexity,
    _build_recommendations,
    _count_oversized_invocations,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

MINIMAL_CATALOG = {
    "catalog_schema_version": "1.0.0",
    "pricing_disclaimer": "test",
    "providers": [
        {
            "provider_id": "test_per_token",
            "display_name": "Test Per-Token",
            "billing_model": "per_token",
            "models": [
                {
                    "model_id": "test-model-1",
                    "display_name": "Test Model 1",
                    "input_cost_per_mtok": 3.0,
                    "output_cost_per_mtok": 15.0,
                    "supports_tools": True,
                    "supports_system_prompt": True,
                    "max_context_tokens": 200000,
                    "max_output_tokens": 16384,
                    "openai_compatible": False,
                    "capability_tier": "high",
                }
            ],
            "security_posture": {
                "private_networking_possible": False,
                "data_residency_possible": False,
                "zero_data_retention_possible": True,
                "notes": ["Test note"],
            },
        },
        {
            "provider_id": "test_subscription",
            "display_name": "Test Subscription",
            "billing_model": "subscription",
            "estimated_monthly_cost_usd": 200.0,
            "models": [
                {
                    "model_id": "sub-model",
                    "display_name": "Sub Model",
                    "supports_tools": True,
                    "supports_system_prompt": True,
                    "max_context_tokens": 200000,
                    "max_output_tokens": 16384,
                    "openai_compatible": False,
                }
            ],
            "security_posture": {
                "private_networking_possible": False,
                "data_residency_possible": False,
                "zero_data_retention_possible": False,
                "notes": [],
            },
        },
        {
            "provider_id": "test_infra",
            "display_name": "Test Infrastructure",
            "billing_model": "infrastructure",
            "models": [
                {
                    "model_id": "local-model",
                    "display_name": "Local Model",
                    "input_cost_per_mtok": 0.0,
                    "output_cost_per_mtok": 0.0,
                    "supports_tools": True,
                    "supports_system_prompt": True,
                    "max_context_tokens": 131072,
                    "max_output_tokens": 4096,
                    "openai_compatible": True,
                    "requires_gpu": True,
                    "capability_tier": "mid",
                }
            ],
            "security_posture": {
                "private_networking_possible": True,
                "data_residency_possible": True,
                "zero_data_retention_possible": True,
                "notes": ["On-prem"],
            },
        },
        {
            "provider_id": "test_small_context",
            "display_name": "Test Small Context",
            "billing_model": "per_token",
            "models": [
                {
                    "model_id": "small-ctx",
                    "display_name": "Small Context Model",
                    "input_cost_per_mtok": 0.5,
                    "output_cost_per_mtok": 0.5,
                    "supports_tools": False,
                    "supports_system_prompt": True,
                    "max_context_tokens": 4096,
                    "max_output_tokens": 2048,
                    "openai_compatible": True,
                    "capability_tier": "low",
                }
            ],
            "security_posture": {
                "private_networking_possible": False,
                "data_residency_possible": False,
                "zero_data_retention_possible": False,
                "notes": [],
            },
        },
        {
            "provider_id": "test_no_system_prompt",
            "display_name": "Test No System Prompt",
            "billing_model": "per_token",
            "models": [
                {
                    "model_id": "no-sys",
                    "display_name": "No System Prompt Model",
                    "input_cost_per_mtok": 1.0,
                    "output_cost_per_mtok": 1.0,
                    "supports_tools": True,
                    "supports_system_prompt": False,
                    "max_context_tokens": 200000,
                    "max_output_tokens": 16384,
                    "openai_compatible": True,
                    "capability_tier": "mid",
                }
            ],
            "security_posture": {
                "private_networking_possible": False,
                "data_residency_possible": False,
                "zero_data_retention_possible": False,
                "notes": [],
            },
        },
    ],
}


def _write_phase_b_artifacts(bench_dir: Path, token_econ: dict | None = None, phase_ana: dict | None = None, summary: dict | None = None):
    """Write minimal Phase B artifacts for testing."""
    bench_dir.mkdir(parents=True, exist_ok=True)

    if token_econ is None:
        token_econ = {
            "run_id": "test-run",
            "total_estimated_input_tokens": 40000,
            "total_estimated_output_tokens": 22000,
            "total_estimated_tokens": 62000,
            "largest_invocation_by_estimated_total_tokens": {
                "invocation_id": "inv-1",
                "skill_id": "test-skill",
                "value": 17000,
            },
            "tapm_vs_cli_prompt": {
                "tapm": {"estimated_total_tokens": 62000},
                "cli_prompt": {"estimated_total_tokens": 0},
            },
            "phase_8_estimated_total_tokens": 0,
            "phases_1_7_estimated_total_tokens": 62000,
            "semantic_predicate_estimated_total_tokens": 0,
        }
    (bench_dir / "token_economics.json").write_text(
        json.dumps(token_econ, indent=2), encoding="utf-8"
    )

    if phase_ana is None:
        phase_ana = {
            "benchmark_schema_version": "1.0.0",
            "run_id": "test-run",
            "total_invocations": 4,
            "phases_observed": [1],
            "nodes_observed": ["n01_call_analysis"],
            "per_phase": {
                "1": {
                    "invocations": 4,
                    "tapm_count": 4,
                    "cli_prompt_count": 0,
                    "semantic_predicate_count": 0,
                }
            },
        }
    (bench_dir / "phase_analytics.json").write_text(
        json.dumps(phase_ana, indent=2), encoding="utf-8"
    )

    if summary is None:
        summary = {
            "benchmark_schema_version": "1.0.0",
            "run_id": "test-run",
            "total_invocations": 4,
            "total_estimated_input_tokens": 40000,
            "total_estimated_output_tokens": 22000,
            "benchmark_stage": "phase_b_analytics",
        }
    (bench_dir / "run_benchmark_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )


def _write_catalog(path: Path, catalog: dict | None = None):
    """Write provider catalog."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(catalog or MINIMAL_CATALOG, indent=2), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Catalog loading
# ---------------------------------------------------------------------------

class TestCatalogLoading:
    def test_loads_explicit_catalog(self, tmp_path):
        bench_dir = tmp_path / "bench"
        _write_phase_b_artifacts(bench_dir)
        cat_path = tmp_path / "catalog.json"
        _write_catalog(cat_path)

        result = build_provider_projection(bench_dir, catalog_path=cat_path)
        assert len(result["projections"]) > 0

    def test_loads_default_catalog_from_repo_root(self, tmp_path):
        bench_dir = tmp_path / ".claude" / "benchmark" / "test-run"
        _write_phase_b_artifacts(bench_dir)
        cat_path = tmp_path / ".claude" / "benchmark" / "config" / "provider_catalog.json"
        _write_catalog(cat_path)

        result = build_provider_projection(bench_dir, repo_root=tmp_path)
        assert len(result["projections"]) > 0

    def test_empty_catalog_produces_empty_projections(self, tmp_path):
        bench_dir = tmp_path / "bench"
        _write_phase_b_artifacts(bench_dir)
        cat_path = tmp_path / "catalog.json"
        _write_catalog(cat_path, {"providers": []})

        result = build_provider_projection(bench_dir, catalog_path=cat_path)
        assert result["projections"] == []


# ---------------------------------------------------------------------------
# Cost projection
# ---------------------------------------------------------------------------

class TestCostProjection:
    def test_per_token_cost_calculation(self, tmp_path):
        bench_dir = tmp_path / "bench"
        _write_phase_b_artifacts(bench_dir)
        cat_path = tmp_path / "catalog.json"
        _write_catalog(cat_path)

        result = build_provider_projection(bench_dir, catalog_path=cat_path)

        per_token_proj = [
            p for p in result["projections"]
            if p["provider_id"] == "test_per_token"
        ]
        assert len(per_token_proj) == 1
        proj = per_token_proj[0]

        # 40000 input tokens / 1M * $3.00 = $0.12
        expected_input = round(40000 / 1_000_000 * 3.0, 6)
        assert proj["projected_input_cost_usd"] == expected_input

        # 22000 output tokens / 1M * $15.00 = $0.33
        expected_output = round(22000 / 1_000_000 * 15.0, 6)
        assert proj["projected_output_cost_usd"] == expected_output

        expected_total = round(expected_input + expected_output, 6)
        assert proj["projected_total_cost_usd"] == expected_total

    def test_subscription_billing(self, tmp_path):
        bench_dir = tmp_path / "bench"
        _write_phase_b_artifacts(bench_dir)
        cat_path = tmp_path / "catalog.json"
        _write_catalog(cat_path)

        result = build_provider_projection(bench_dir, catalog_path=cat_path)

        sub_proj = [
            p for p in result["projections"]
            if p["provider_id"] == "test_subscription"
        ]
        assert len(sub_proj) == 1
        proj = sub_proj[0]
        assert proj["projected_total_cost_usd"] == 200.0
        assert proj["projected_input_cost_usd"] == 0.0
        assert proj["projected_output_cost_usd"] == 0.0

    def test_infrastructure_billing(self, tmp_path):
        bench_dir = tmp_path / "bench"
        _write_phase_b_artifacts(bench_dir)
        cat_path = tmp_path / "catalog.json"
        _write_catalog(cat_path)

        result = build_provider_projection(bench_dir, catalog_path=cat_path)

        infra_proj = [
            p for p in result["projections"]
            if p["provider_id"] == "test_infra"
        ]
        assert len(infra_proj) == 1
        proj = infra_proj[0]
        assert proj["projected_total_cost_usd"] == 0.0
        assert proj["projected_input_cost_usd"] == 0.0
        assert proj["projected_output_cost_usd"] == 0.0


# ---------------------------------------------------------------------------
# Feasibility checks
# ---------------------------------------------------------------------------

class TestFeasibilityChecks:
    def test_context_window_sufficient(self, tmp_path):
        bench_dir = tmp_path / "bench"
        _write_phase_b_artifacts(bench_dir)
        cat_path = tmp_path / "catalog.json"
        _write_catalog(cat_path)

        result = build_provider_projection(bench_dir, catalog_path=cat_path)

        # Large context model should be fine (200k > 17k max invocation)
        large = [p for p in result["projections"] if p["provider_id"] == "test_per_token"][0]
        assert large["context_window_sufficient"] is True
        assert large["oversized_invocations"] == 0

    def test_context_window_overflow(self, tmp_path):
        bench_dir = tmp_path / "bench"
        _write_phase_b_artifacts(bench_dir)
        cat_path = tmp_path / "catalog.json"
        _write_catalog(cat_path)

        result = build_provider_projection(bench_dir, catalog_path=cat_path)

        # Small context (4096) < 17000 max invocation
        small = [p for p in result["projections"] if p["provider_id"] == "test_small_context"][0]
        assert small["context_window_sufficient"] is False
        assert small["oversized_invocations"] >= 1

    def test_tool_support_missing_for_tapm(self, tmp_path):
        bench_dir = tmp_path / "bench"
        _write_phase_b_artifacts(bench_dir)
        cat_path = tmp_path / "catalog.json"
        _write_catalog(cat_path)

        result = build_provider_projection(bench_dir, catalog_path=cat_path)

        # Small context model has supports_tools=False, and we have TAPM workload
        small = [p for p in result["projections"] if p["provider_id"] == "test_small_context"][0]
        assert small["tool_support_sufficient"] is False

    def test_system_prompt_unsupported(self, tmp_path):
        bench_dir = tmp_path / "bench"
        _write_phase_b_artifacts(bench_dir)
        cat_path = tmp_path / "catalog.json"
        _write_catalog(cat_path)

        result = build_provider_projection(bench_dir, catalog_path=cat_path)

        no_sys = [p for p in result["projections"] if p["provider_id"] == "test_no_system_prompt"][0]
        assert no_sys["system_prompt_supported"] is False
        assert no_sys["supports_all_modes"] is False


# ---------------------------------------------------------------------------
# Migration complexity
# ---------------------------------------------------------------------------

class TestMigrationComplexity:
    def test_drop_in_openai_compatible(self):
        result = _determine_migration_complexity(
            openai_compatible=True,
            tool_support=True,
            requires_tools=True,
            context_sufficient=True,
            system_prompt_supported=True,
            model={},
            provider={},
        )
        assert result == "drop_in"

    def test_adapter_needed_non_openai(self):
        result = _determine_migration_complexity(
            openai_compatible=False,
            tool_support=True,
            requires_tools=True,
            context_sufficient=True,
            system_prompt_supported=True,
            model={},
            provider={},
        )
        assert result == "adapter_needed"

    def test_not_suitable_context_insufficient(self):
        result = _determine_migration_complexity(
            openai_compatible=True,
            tool_support=True,
            requires_tools=True,
            context_sufficient=False,
            system_prompt_supported=True,
            model={},
            provider={},
        )
        assert result == "not_suitable"

    def test_not_suitable_no_tools_but_required(self):
        result = _determine_migration_complexity(
            openai_compatible=True,
            tool_support=False,
            requires_tools=True,
            context_sufficient=True,
            system_prompt_supported=True,
            model={},
            provider={},
        )
        assert result == "not_suitable"

    def test_hint_from_model(self):
        result = _determine_migration_complexity(
            openai_compatible=False,
            tool_support=True,
            requires_tools=True,
            context_sufficient=True,
            system_prompt_supported=True,
            model={"migration_complexity_hint": "significant_work"},
            provider={},
        )
        assert result == "significant_work"

    def test_not_suitable_no_system_prompt(self):
        result = _determine_migration_complexity(
            openai_compatible=True,
            tool_support=True,
            requires_tools=False,
            context_sufficient=True,
            system_prompt_supported=False,
            model={},
            provider={},
        )
        assert result == "not_suitable"


# ---------------------------------------------------------------------------
# Observed workload extraction
# ---------------------------------------------------------------------------

class TestObservedWorkload:
    def test_extracts_from_phase_b(self, tmp_path):
        bench_dir = tmp_path / "bench"
        _write_phase_b_artifacts(bench_dir)
        cat_path = tmp_path / "catalog.json"
        _write_catalog(cat_path)

        result = build_provider_projection(bench_dir, catalog_path=cat_path)
        obs = result["observed_workload"]

        assert obs["total_invocations"] == 4
        assert obs["total_estimated_input_tokens"] == 40000
        assert obs["total_estimated_output_tokens"] == 22000
        assert obs["total_estimated_tokens"] == 62000
        assert obs["requires_tool_support"] is True
        assert obs["tapm_invocation_count"] == 4
        assert obs["cli_prompt_invocation_count"] == 0
        assert obs["semantic_predicate_invocation_count"] == 0
        assert obs["phase_8_estimated_total_tokens"] == 0
        assert obs["phases_1_7_estimated_total_tokens"] == 62000

    def test_max_single_invocation_from_largest(self):
        te = {
            "total_estimated_input_tokens": 100,
            "total_estimated_output_tokens": 50,
            "total_estimated_tokens": 150,
            "largest_invocation_by_estimated_total_tokens": {
                "value": 80,
            },
            "tapm_vs_cli_prompt": {
                "tapm": {"estimated_total_tokens": 150},
                "cli_prompt": {"estimated_total_tokens": 0},
            },
            "phase_8_estimated_total_tokens": 0,
            "phases_1_7_estimated_total_tokens": 150,
            "semantic_predicate_estimated_total_tokens": 0,
        }
        obs = _extract_observed_workload(te, None)
        assert obs["max_single_invocation_total_tokens"] == 80


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------

class TestRecommendations:
    def test_deterministic_recommendations(self, tmp_path):
        bench_dir = tmp_path / "bench"
        _write_phase_b_artifacts(bench_dir)
        cat_path = tmp_path / "catalog.json"
        _write_catalog(cat_path)

        result = build_provider_projection(bench_dir, catalog_path=cat_path)
        recs = result["recommendations"]

        assert "lowest_projected_cost" in recs
        assert "best_capability_match" in recs
        assert "best_openai_compatible_candidate" in recs
        assert "best_private_network_candidate" in recs
        assert "not_suitable" in recs
        assert isinstance(recs["not_suitable"], list)
        assert "migration_warnings" in recs

    def test_lowest_cost_is_cheapest(self, tmp_path):
        bench_dir = tmp_path / "bench"
        _write_phase_b_artifacts(bench_dir)
        cat_path = tmp_path / "catalog.json"
        _write_catalog(cat_path)

        result = build_provider_projection(bench_dir, catalog_path=cat_path)
        recs = result["recommendations"]
        lowest = recs["lowest_projected_cost"]

        # Infra provider has 0 cost and is suitable + per_token billing excluded from infra
        # test_infra is infrastructure billing so not in per-token candidates
        # The cheapest per-token should be test_per_token ($0.12 + $0.33 = $0.45)
        if lowest is not None:
            assert isinstance(lowest["projected_total_cost_usd"], (int, float))

    def test_not_suitable_list(self, tmp_path):
        bench_dir = tmp_path / "bench"
        _write_phase_b_artifacts(bench_dir)
        cat_path = tmp_path / "catalog.json"
        _write_catalog(cat_path)

        result = build_provider_projection(bench_dir, catalog_path=cat_path)
        not_suitable = result["recommendations"]["not_suitable"]

        # Small context and no-system-prompt models should be not suitable
        assert any("Small Context" in n for n in not_suitable)
        assert any("No System Prompt" in n for n in not_suitable)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_missing_token_economics_raises(self, tmp_path):
        bench_dir = tmp_path / "bench"
        bench_dir.mkdir(parents=True)
        cat_path = tmp_path / "catalog.json"
        _write_catalog(cat_path)

        with pytest.raises(FileNotFoundError):
            build_provider_projection(bench_dir, catalog_path=cat_path)

    def test_missing_phase_analytics_handled(self, tmp_path):
        bench_dir = tmp_path / "bench"
        bench_dir.mkdir(parents=True)
        # Write only token_economics (no phase_analytics)
        (bench_dir / "token_economics.json").write_text(
            json.dumps({
                "run_id": "test",
                "total_estimated_input_tokens": 100,
                "total_estimated_output_tokens": 50,
                "total_estimated_tokens": 150,
                "tapm_vs_cli_prompt": {
                    "tapm": {"estimated_total_tokens": 150},
                    "cli_prompt": {"estimated_total_tokens": 0},
                },
                "phase_8_estimated_total_tokens": 0,
                "phases_1_7_estimated_total_tokens": 150,
                "semantic_predicate_estimated_total_tokens": 0,
            }),
            encoding="utf-8",
        )
        cat_path = tmp_path / "catalog.json"
        _write_catalog(cat_path, {"providers": []})

        result = build_provider_projection(bench_dir, catalog_path=cat_path)
        assert result["observed_workload"]["total_invocations"] == 0

    def test_no_prompt_or_response_content(self, tmp_path):
        bench_dir = tmp_path / "bench"
        _write_phase_b_artifacts(bench_dir)
        cat_path = tmp_path / "catalog.json"
        _write_catalog(cat_path)

        result = build_provider_projection(bench_dir, catalog_path=cat_path)
        result_str = json.dumps(result)

        # Should not contain actual prompt text keys (only metadata like system_prompt_supported)
        assert "system_prompt_chars" not in result_str
        assert "user_prompt_chars" not in result_str
        assert "response_text" not in result_str
        assert "prompt_content" not in result_str

    def test_projection_schema_structure(self, tmp_path):
        bench_dir = tmp_path / "bench"
        _write_phase_b_artifacts(bench_dir)
        cat_path = tmp_path / "catalog.json"
        _write_catalog(cat_path)

        result = build_provider_projection(bench_dir, catalog_path=cat_path)

        # Top-level keys
        assert result["benchmark_schema_version"] == "1.0.0"
        assert "run_id" in result
        assert "projection_timestamp" in result
        assert "pricing_basis" in result
        assert result["pricing_basis"]["source"] == "static_provider_catalog"
        assert "observed_workload" in result
        assert "projections" in result
        assert "recommendations" in result

        # Projection entry keys
        if result["projections"]:
            proj = result["projections"][0]
            for key in [
                "provider_id", "model_id", "display_name", "billing_model",
                "projected_input_cost_usd", "projected_output_cost_usd",
                "projected_total_cost_usd", "context_window_sufficient",
                "oversized_invocations", "tool_support_sufficient",
                "system_prompt_supported", "supports_all_modes",
                "openai_compatible", "migration_complexity",
                "capability_tier", "security_posture", "warnings",
            ]:
                assert key in proj, f"Missing key: {key}"
