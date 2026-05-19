"""Tests for runner.benchmark.analytics — aggregation from ledger records."""

import pytest

from runner.benchmark.analytics import build_phase_analytics, build_token_economics


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _make_record(
    invocation_id="inv-001",
    run_id="run-001",
    node_id=None,
    skill_id=None,
    predicate_id=None,
    invocation_type="skill_tapm",
    execution_mode="tapm",
    estimated_input_tokens=1000,
    estimated_output_tokens=500,
    wall_clock_seconds=10.0,
    response_status="success",
    system_prompt_chars=3500,
    user_prompt_chars=7000,
    **kwargs,
):
    rec = {
        "invocation_id": invocation_id,
        "run_id": run_id,
        "node_id": node_id,
        "skill_id": skill_id,
        "predicate_id": predicate_id,
        "invocation_type": invocation_type,
        "execution_mode": execution_mode,
        "estimated_input_tokens": estimated_input_tokens,
        "estimated_output_tokens": estimated_output_tokens,
        "wall_clock_seconds": wall_clock_seconds,
        "response_status": response_status,
        "system_prompt_chars": system_prompt_chars,
        "user_prompt_chars": user_prompt_chars,
    }
    rec.update(kwargs)
    return rec


FIXTURE_LEDGER = [
    _make_record(
        invocation_id="inv-001",
        skill_id="call-requirements-extraction",
        invocation_type="skill_tapm",
        execution_mode="tapm",
        estimated_input_tokens=10357,
        estimated_output_tokens=7571,
        wall_clock_seconds=307.563,
        system_prompt_chars=1155,
        user_prompt_chars=35097,
    ),
    _make_record(
        invocation_id="inv-002",
        skill_id="evaluation-matrix-builder",
        invocation_type="skill_tapm",
        execution_mode="tapm",
        estimated_input_tokens=7541,
        estimated_output_tokens=2753,
        wall_clock_seconds=138.281,
        system_prompt_chars=1218,
        user_prompt_chars=25177,
    ),
    _make_record(
        invocation_id="inv-003",
        skill_id="instrument-schema-normalization",
        invocation_type="skill_tapm",
        execution_mode="tapm",
        estimated_input_tokens=8394,
        estimated_output_tokens=9339,
        wall_clock_seconds=277.219,
        system_prompt_chars=1200,
        user_prompt_chars=28180,
    ),
    _make_record(
        invocation_id="inv-004",
        skill_id="topic-scope-check",
        invocation_type="skill_tapm",
        execution_mode="tapm",
        estimated_input_tokens=14110,
        estimated_output_tokens=3281,
        wall_clock_seconds=198.297,
        system_prompt_chars=1114,
        user_prompt_chars=48272,
    ),
]


# ---------------------------------------------------------------------------
# build_phase_analytics
# ---------------------------------------------------------------------------

class TestBuildPhaseAnalytics:
    def test_basic_from_fixture(self):
        run_summary = {
            "phase_scope": 1,
            "phase_scope_nodes": ["n01_call_analysis"],
        }
        result = build_phase_analytics(
            FIXTURE_LEDGER,
            run_id="run-001",
            phase_scope=1,
            run_summary=run_summary,
        )
        assert result["run_id"] == "run-001"
        assert result["phase_scope"] == 1
        assert result["total_invocations"] == 4
        assert result["phases_observed"] == [1]

    def test_per_phase_aggregation(self):
        run_summary = {"phase_scope": 1}
        result = build_phase_analytics(
            FIXTURE_LEDGER,
            run_summary=run_summary,
        )
        assert "1" in result["per_phase"]
        phase1 = result["per_phase"]["1"]
        assert phase1["invocations"] == 4
        assert phase1["estimated_input_tokens"] == 40402
        assert phase1["estimated_output_tokens"] == 22944

    def test_nodes_observed_with_node_ids(self):
        records = [
            _make_record(node_id="n01_call_analysis"),
            _make_record(node_id="n02_concept_refinement"),
        ]
        result = build_phase_analytics(records)
        assert "n01_call_analysis" in result["nodes_observed"]
        assert "n02_concept_refinement" in result["nodes_observed"]

    def test_per_node_aggregation(self):
        records = [
            _make_record(node_id="n01_call_analysis", estimated_input_tokens=100),
            _make_record(node_id="n01_call_analysis", estimated_input_tokens=200),
            _make_record(node_id="n02_concept_refinement", estimated_input_tokens=300),
        ]
        result = build_phase_analytics(records)
        assert result["per_node"]["n01_call_analysis"]["invocations"] == 2
        assert result["per_node"]["n01_call_analysis"]["estimated_input_tokens"] == 300
        assert result["per_node"]["n02_concept_refinement"]["invocations"] == 1

    def test_phase_inference_from_node_id(self):
        records = [
            _make_record(node_id="n01_call_analysis"),
            _make_record(node_id="n08a_excellence_drafting"),
        ]
        result = build_phase_analytics(records)
        assert 1 in result["phases_observed"]
        assert 8 in result["phases_observed"]

    def test_phase_inference_from_run_summary(self):
        records = [_make_record(node_id=None)]
        run_summary = {"phase_scope": 1}
        result = build_phase_analytics(records, run_summary=run_summary)
        assert result["phases_observed"] == [1]

    def test_empty_records(self):
        result = build_phase_analytics([])
        assert result["total_invocations"] == 0
        assert result["phases_observed"] == []

    def test_tapm_cli_split(self):
        records = [
            _make_record(execution_mode="tapm"),
            _make_record(execution_mode="tapm"),
            _make_record(execution_mode="cli-prompt"),
        ]
        records_with_nodes = [
            _make_record(execution_mode="tapm", node_id="n01_call_analysis"),
            _make_record(execution_mode="tapm", node_id="n01_call_analysis"),
            _make_record(execution_mode="cli-prompt", node_id="n01_call_analysis"),
        ]
        result = build_phase_analytics(records_with_nodes)
        node_data = result["per_node"]["n01_call_analysis"]
        assert node_data["tapm_count"] == 2
        assert node_data["cli_prompt_count"] == 1

    def test_failed_and_timeout_count(self):
        records = [
            _make_record(node_id="n01_call_analysis", response_status="success"),
            _make_record(node_id="n01_call_analysis", response_status="timeout"),
            _make_record(node_id="n01_call_analysis", response_status="error"),
        ]
        result = build_phase_analytics(records)
        node_data = result["per_node"]["n01_call_analysis"]
        assert node_data["failed_count"] == 2
        assert node_data["timeout_count"] == 1

    def test_semantic_predicate_count(self):
        records = [
            _make_record(
                node_id="n01_call_analysis",
                invocation_type="semantic_predicate",
                predicate_id="scope_check",
            ),
            _make_record(
                node_id="n01_call_analysis",
                invocation_type="skill_tapm",
            ),
        ]
        result = build_phase_analytics(records)
        node_data = result["per_node"]["n01_call_analysis"]
        assert node_data["semantic_predicate_count"] == 1


# ---------------------------------------------------------------------------
# build_token_economics
# ---------------------------------------------------------------------------

class TestBuildTokenEconomics:
    def test_totals_from_fixture(self):
        result = build_token_economics(FIXTURE_LEDGER, run_id="run-001")
        assert result["total_estimated_input_tokens"] == 40402
        assert result["total_estimated_output_tokens"] == 22944
        assert result["total_estimated_tokens"] == 63346

    def test_by_invocation_type(self):
        records = [
            _make_record(invocation_type="skill_tapm", estimated_input_tokens=100, estimated_output_tokens=50),
            _make_record(invocation_type="semantic_predicate", estimated_input_tokens=200, estimated_output_tokens=30),
        ]
        result = build_token_economics(records)
        assert "skill_tapm" in result["tokens_by_invocation_type"]
        assert result["tokens_by_invocation_type"]["skill_tapm"]["estimated_total_tokens"] == 150
        assert result["tokens_by_invocation_type"]["semantic_predicate"]["estimated_total_tokens"] == 230

    def test_by_skill_id(self):
        result = build_token_economics(FIXTURE_LEDGER)
        assert "call-requirements-extraction" in result["tokens_by_skill_id"]
        skill_data = result["tokens_by_skill_id"]["call-requirements-extraction"]
        assert skill_data["estimated_input_tokens"] == 10357
        assert skill_data["estimated_output_tokens"] == 7571

    def test_by_predicate_id(self):
        records = [
            _make_record(predicate_id="scope_check", invocation_type="semantic_predicate",
                         estimated_input_tokens=100, estimated_output_tokens=50),
        ]
        result = build_token_economics(records)
        assert "scope_check" in result["tokens_by_semantic_predicate_id"]

    def test_largest_invocation_by_tokens(self):
        result = build_token_economics(FIXTURE_LEDGER)
        largest = result["largest_invocation_by_estimated_total_tokens"]
        assert largest is not None
        # inv-001: 10357+7571=17928; inv-003: 8394+9339=17733
        assert largest["invocation_id"] == "inv-001"
        assert largest["value"] == 17928

    def test_largest_invocation_by_prompt_chars(self):
        result = build_token_economics(FIXTURE_LEDGER)
        largest = result["largest_invocation_by_prompt_chars"]
        assert largest is not None
        # inv-004 has 1114+48272=49386 prompt chars (largest)
        assert largest["invocation_id"] == "inv-004"
        assert largest["value"] == 49386

    def test_tapm_vs_cli_prompt(self):
        records = [
            _make_record(execution_mode="tapm", estimated_input_tokens=100, estimated_output_tokens=50),
            _make_record(execution_mode="cli-prompt", estimated_input_tokens=200, estimated_output_tokens=30),
        ]
        result = build_token_economics(records)
        assert result["tapm_vs_cli_prompt"]["tapm"]["estimated_total_tokens"] == 150
        assert result["tapm_vs_cli_prompt"]["cli_prompt"]["estimated_total_tokens"] == 230

    def test_semantic_predicate_total(self):
        records = [
            _make_record(invocation_type="semantic_predicate", estimated_input_tokens=100, estimated_output_tokens=50),
            _make_record(invocation_type="skill_tapm", estimated_input_tokens=200, estimated_output_tokens=30),
        ]
        result = build_token_economics(records)
        assert result["semantic_predicate_estimated_total_tokens"] == 150

    def test_phases_1_7_total(self):
        records = [
            _make_record(node_id="n01_call_analysis", estimated_input_tokens=100, estimated_output_tokens=50),
            _make_record(node_id="n08a_excellence_drafting", estimated_input_tokens=200, estimated_output_tokens=30),
        ]
        result = build_token_economics(records)
        assert result["phases_1_7_estimated_total_tokens"] == 150
        assert result["phase_8_estimated_total_tokens"] == 230

    def test_empty_records(self):
        result = build_token_economics([])
        assert result["total_estimated_tokens"] == 0
        assert result["largest_invocation_by_estimated_total_tokens"] is None

    def test_warning_present(self):
        result = build_token_economics([])
        assert "warning" in result
        assert "not billing-grade" in result["warning"]
