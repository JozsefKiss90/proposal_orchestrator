"""
Tests for runner.node_resolver — node_id → agent resolution layer.

Covers §14 test cases 1–3:
  1. node_id → agent_id resolution for all 11 nodes
  2. prompt spec loading (path existence verification)
  3. skill list resolution from manifest

Additional tests:
  - sub_agent resolution (n03 → dependency_mapper, others → None)
  - pre_gate_agent resolution (n07 → budget_interface_coordinator, others → None)
  - agent definition path exists on disk
  - prompt spec path exists on disk
  - NodeResolverError for unknown node_id
  - phase_id resolution for all nodes
  - node_ids() returns all 11 in manifest order
"""

from __future__ import annotations

from pathlib import Path

import pytest

from runner.node_resolver import NodeResolver, NodeResolverError
from runner.paths import find_repo_root


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def resolver() -> NodeResolver:
    """Production NodeResolver loaded from the real manifest."""
    root = find_repo_root()
    return NodeResolver(repo_root=root)


@pytest.fixture(scope="module")
def repo_root() -> Path:
    return find_repo_root()


# ---------------------------------------------------------------------------
# Expected manifest data
# ---------------------------------------------------------------------------

_EXPECTED_NODES = [
    "n01_call_analysis",
    "n02_concept_refinement",
    "n03_wp_design",
    "n04_gantt_milestones",
    "n05_impact_architecture",
    "n06_implementation_architecture",
    "n07_budget_gate",
    "n08a_section_drafting",
    "n08b_assembly",
    "n08c_evaluator_review",
    "n08d_revision",
]

_NODE_TO_AGENT = {
    "n01_call_analysis": "call_analyzer",
    "n02_concept_refinement": "concept_refiner",
    "n03_wp_design": "wp_designer",
    "n04_gantt_milestones": "gantt_designer",
    "n05_impact_architecture": "impact_architect",
    "n06_implementation_architecture": "implementation_architect",
    "n07_budget_gate": "budget_gate_validator",
    "n08a_section_drafting": "proposal_writer",
    "n08b_assembly": "proposal_writer",
    "n08c_evaluator_review": "evaluator_reviewer",
    "n08d_revision": "revision_integrator",
}

_NODE_TO_PHASE = {
    "n01_call_analysis": "phase_01_call_analysis",
    "n02_concept_refinement": "phase_02_concept_refinement",
    "n03_wp_design": "phase_03_wp_design_and_dependency_mapping",
    "n04_gantt_milestones": "phase_04_gantt_and_milestones",
    "n05_impact_architecture": "phase_05_impact_architecture",
    "n06_implementation_architecture": "phase_06_implementation_architecture",
    "n07_budget_gate": "phase_07_budget_gate",
    "n08a_section_drafting": "phase_08a_section_drafting",
    "n08b_assembly": "phase_08b_assembly",
    "n08c_evaluator_review": "phase_08c_evaluator_review",
    "n08d_revision": "phase_08d_revision",
}


# ---------------------------------------------------------------------------
# §14 test 1 — node_id → agent_id resolution
# ---------------------------------------------------------------------------


class TestAgentIdResolution:
    """Verify that the node registry lookup correctly maps node identifiers
    to agent identifiers using manifest.compile.yaml."""

    @pytest.mark.parametrize("node_id,expected_agent", list(_NODE_TO_AGENT.items()))
    def test_resolve_agent_id(
        self, resolver: NodeResolver, node_id: str, expected_agent: str
    ) -> None:
        assert resolver.resolve_agent_id(node_id) == expected_agent

    def test_phase8_nodes_share_proposal_writer(self, resolver: NodeResolver) -> None:
        """n08a and n08b share the same agent_id (proposal_writer)."""
        assert resolver.resolve_agent_id("n08a_section_drafting") == "proposal_writer"
        assert resolver.resolve_agent_id("n08b_assembly") == "proposal_writer"


# ---------------------------------------------------------------------------
# §14 test 2 — prompt spec loading
# ---------------------------------------------------------------------------


class TestPromptSpecPaths:
    """Confirm that prompt specifications are correctly loaded from
    .claude/agents/prompts/ for each agent invocation."""

    @pytest.mark.parametrize("agent_id", sorted(set(_NODE_TO_AGENT.values())))
    def test_prompt_spec_path_exists(
        self, resolver: NodeResolver, agent_id: str
    ) -> None:
        path = resolver.agent_prompt_spec_path(agent_id)
        assert path.exists(), f"Prompt spec missing: {path}"
        assert path.suffix == ".md"

    @pytest.mark.parametrize("agent_id", sorted(set(_NODE_TO_AGENT.values())))
    def test_agent_definition_path_exists(
        self, resolver: NodeResolver, agent_id: str
    ) -> None:
        path = resolver.agent_definition_path(agent_id)
        assert path.exists(), f"Agent definition missing: {path}"
        assert path.suffix == ".md"


# ---------------------------------------------------------------------------
# §14 test 3 — skill list resolution from manifest
# ---------------------------------------------------------------------------


class TestSkillListResolution:
    """Validate that the agent runtime correctly retrieves the ordered skill
    list for a node from the manifest's skill registry."""

    def test_n01_skill_count(self, resolver: NodeResolver) -> None:
        skills = resolver.resolve_skill_ids("n01_call_analysis")
        assert len(skills) == 5

    def test_n01_skill_list(self, resolver: NodeResolver) -> None:
        skills = resolver.resolve_skill_ids("n01_call_analysis")
        assert "call-requirements-extraction" in skills
        assert "evaluation-matrix-builder" in skills
        assert "instrument-schema-normalization" in skills
        assert "topic-scope-check" in skills
        assert "gate-enforcement" in skills

    def test_n03_skills_include_sub_agent_skills(self, resolver: NodeResolver) -> None:
        skills = resolver.resolve_skill_ids("n03_wp_design")
        assert "work-package-normalization" in skills
        assert "wp-dependency-analysis" in skills

    def test_n07_skills(self, resolver: NodeResolver) -> None:
        skills = resolver.resolve_skill_ids("n07_budget_gate")
        assert "budget-interface-validation" in skills
        assert "gate-enforcement" in skills

    @pytest.mark.parametrize("node_id", _EXPECTED_NODES)
    def test_all_nodes_have_skills(self, resolver: NodeResolver, node_id: str) -> None:
        skills = resolver.resolve_skill_ids(node_id)
        assert isinstance(skills, list)
        assert len(skills) > 0, f"Node {node_id} has no skills"

    def test_skill_list_is_ordered(self, resolver: NodeResolver) -> None:
        """Skills are returned in manifest order (list, not set)."""
        skills = resolver.resolve_skill_ids("n01_call_analysis")
        assert isinstance(skills, list)


# ---------------------------------------------------------------------------
# Sub-agent and pre-gate agent resolution
# ---------------------------------------------------------------------------


class TestSubAgentResolution:
    def test_n03_has_dependency_mapper(self, resolver: NodeResolver) -> None:
        assert resolver.resolve_sub_agent_id("n03_wp_design") == "dependency_mapper"

    @pytest.mark.parametrize("node_id", [
        n for n in _EXPECTED_NODES if n != "n03_wp_design"
    ])
    def test_other_nodes_no_sub_agent(
        self, resolver: NodeResolver, node_id: str
    ) -> None:
        assert resolver.resolve_sub_agent_id(node_id) is None


class TestPreGateAgentResolution:
    def test_n07_has_budget_interface_coordinator(self, resolver: NodeResolver) -> None:
        assert (
            resolver.resolve_pre_gate_agent_id("n07_budget_gate")
            == "budget_interface_coordinator"
        )

    @pytest.mark.parametrize("node_id", [
        n for n in _EXPECTED_NODES if n != "n07_budget_gate"
    ])
    def test_other_nodes_no_pre_gate_agent(
        self, resolver: NodeResolver, node_id: str
    ) -> None:
        assert resolver.resolve_pre_gate_agent_id(node_id) is None


# ---------------------------------------------------------------------------
# Phase ID resolution
# ---------------------------------------------------------------------------


class TestPhaseIdResolution:
    @pytest.mark.parametrize("node_id,expected_phase", list(_NODE_TO_PHASE.items()))
    def test_resolve_phase_id(
        self, resolver: NodeResolver, node_id: str, expected_phase: str
    ) -> None:
        assert resolver.resolve_phase_id(node_id) == expected_phase


# ---------------------------------------------------------------------------
# node_ids() order
# ---------------------------------------------------------------------------


class TestNodeIds:
    def test_returns_all_11_nodes(self, resolver: NodeResolver) -> None:
        assert resolver.node_ids() == _EXPECTED_NODES

    def test_returns_list(self, resolver: NodeResolver) -> None:
        assert isinstance(resolver.node_ids(), list)


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestNodeResolverError:
    def test_unknown_node_id(self, resolver: NodeResolver) -> None:
        with pytest.raises(NodeResolverError):
            resolver.resolve_agent_id("n99_nonexistent")

    def test_unknown_agent_definition(self, resolver: NodeResolver) -> None:
        with pytest.raises(NodeResolverError):
            resolver.agent_definition_path("nonexistent_agent")

    def test_unknown_prompt_spec(self, resolver: NodeResolver) -> None:
        with pytest.raises(NodeResolverError):
            resolver.agent_prompt_spec_path("nonexistent_agent")

    def test_missing_manifest(self, tmp_path: Path) -> None:
        with pytest.raises(NodeResolverError, match="not found"):
            NodeResolver(
                manifest_path=tmp_path / "does_not_exist.yaml",
                repo_root=tmp_path,
            )
