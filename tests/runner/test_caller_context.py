"""
Tests for caller-context passing — context-sensitive skill support.

Covers the fix for the Phase 2 context-passing bug where
``topic-scope-check`` fails with ``MISSING_INPUT`` because the invoking
agent (``concept_refiner``) does not supply concept text as context.

Test groups:
  A. _build_caller_context unit tests (agent_runtime)
  B. TAPM prompt includes caller context (skill_runtime)
  C. cli-prompt mode merges caller context (skill_runtime)
  D. run_agent passes caller_context to run_skill for context-sensitive skills
  E. Fail-closed when concept sources are genuinely absent
  F. Other skills and non-Phase-2 usage unaffected
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import yaml

from runner.agent_runtime import (
    _build_caller_context,
    _SKILL_CONTEXT_SOURCES,
    run_agent,
)
from runner.runtime_models import SkillResult
from runner.skill_runtime import _assemble_tapm_prompt


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_RUN_SKILL_TARGET = "runner.agent_runtime.run_skill"

CONCEPT_NOTE_TEXT = """\
# MAESTRO — Next-Generation AI Agent Architecture

MAESTRO proposes an integrated architecture for autonomous AI agents
with three pillars: neuro-symbolic planning, adaptive memory, and
decentralised multi-agent coordination.
"""

STRATEGIC_POSITIONING_TEXT = """\
# Strategic Positioning

MAESTRO differentiates from existing approaches by combining formal
symbolic guarantees with LLM flexibility.
"""

PROJECT_SUMMARY = {
    "project_acronym": "MAESTRO",
    "project_title": "Next-Generation AI Agent Architecture",
    "duration_months": 48,
    "requested_eu_contribution": 18500000,
}


def _write_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data), encoding="utf-8")


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _write_concept_sources(repo_root: Path) -> None:
    """Write synthetic concept source files to project_brief/."""
    brief_dir = repo_root / "docs" / "tier3_project_instantiation" / "project_brief"
    brief_dir.mkdir(parents=True, exist_ok=True)
    (brief_dir / "concept_note.md").write_text(
        CONCEPT_NOTE_TEXT, encoding="utf-8"
    )
    (brief_dir / "strategic_positioning.md").write_text(
        STRATEGIC_POSITIONING_TEXT, encoding="utf-8"
    )
    _write_json(brief_dir / "project_summary.json", PROJECT_SUMMARY)


@pytest.fixture(autouse=True)
def _clear_caches() -> None:
    """Clear module-level caches between tests."""
    import runner.agent_runtime as _ar
    import runner.skill_runtime as _sr
    _ar._agent_catalog_cache.clear()
    _ar._artifact_registry_cache.clear()
    _sr._catalog_cache.clear()
    _sr._schema_spec_cache.clear()


def _success_skill(outputs: list[str] | None = None) -> SkillResult:
    return SkillResult(status="success", outputs_written=outputs or [])


def _failure_skill(
    category: str = "MISSING_INPUT",
    reason: str = "test failure",
) -> SkillResult:
    return SkillResult(
        status="failure",
        failure_reason=reason,
        failure_category=category,
    )


# ---------------------------------------------------------------------------
# A. _build_caller_context unit tests
# ---------------------------------------------------------------------------


class TestBuildCallerContext:
    """Unit tests for _build_caller_context()."""

    def test_returns_concept_text_for_topic_scope_check(
        self, tmp_path: Path
    ) -> None:
        """topic-scope-check gets concept text from project_brief."""
        _write_concept_sources(tmp_path)
        resolved_inputs: dict[str, Any] = {}

        ctx = _build_caller_context("topic-scope-check", resolved_inputs, tmp_path)

        assert len(ctx) == 3
        cn_key = "docs/tier3_project_instantiation/project_brief/concept_note.md"
        sp_key = "docs/tier3_project_instantiation/project_brief/strategic_positioning.md"
        ps_key = "docs/tier3_project_instantiation/project_brief/project_summary.json"

        assert cn_key in ctx
        assert "MAESTRO" in ctx[cn_key]
        assert sp_key in ctx
        assert "Strategic Positioning" in ctx[sp_key]
        assert ps_key in ctx
        assert ctx[ps_key]["project_acronym"] == "MAESTRO"

    def test_uses_resolved_inputs_for_json(self, tmp_path: Path) -> None:
        """JSON files already in resolved_inputs are used directly."""
        _write_concept_sources(tmp_path)
        ps_key = "docs/tier3_project_instantiation/project_brief/project_summary.json"
        # Pre-populate resolved_inputs with modified JSON
        modified = {"project_acronym": "MODIFIED", "custom_field": True}
        resolved_inputs: dict[str, Any] = {ps_key: modified}

        ctx = _build_caller_context("topic-scope-check", resolved_inputs, tmp_path)

        # JSON came from resolved_inputs, not disk
        assert ctx[ps_key]["project_acronym"] == "MODIFIED"
        assert ctx[ps_key]["custom_field"] is True

    def test_reads_md_files_from_disk(self, tmp_path: Path) -> None:
        """.md files are read from disk since _resolve_agent_inputs skips them."""
        _write_concept_sources(tmp_path)
        resolved_inputs: dict[str, Any] = {}

        ctx = _build_caller_context("topic-scope-check", resolved_inputs, tmp_path)

        cn_key = "docs/tier3_project_instantiation/project_brief/concept_note.md"
        assert cn_key in ctx
        assert isinstance(ctx[cn_key], str)
        assert "neuro-symbolic planning" in ctx[cn_key]

    def test_empty_dict_for_non_context_skill(self, tmp_path: Path) -> None:
        """Non-context-sensitive skills get empty dict."""
        _write_concept_sources(tmp_path)
        ctx = _build_caller_context("concept-alignment-check", {}, tmp_path)
        assert ctx == {}

    def test_empty_dict_for_decision_log_update(self, tmp_path: Path) -> None:
        ctx = _build_caller_context("decision-log-update", {}, tmp_path)
        assert ctx == {}

    def test_empty_dict_when_sources_absent(self, tmp_path: Path) -> None:
        """When concept files don't exist, returns empty dict (fail-closed)."""
        # Don't write any concept sources
        ctx = _build_caller_context("topic-scope-check", {}, tmp_path)
        assert ctx == {}

    def test_partial_sources(self, tmp_path: Path) -> None:
        """When only some concept files exist, returns what's available."""
        brief_dir = (
            tmp_path / "docs" / "tier3_project_instantiation" / "project_brief"
        )
        brief_dir.mkdir(parents=True, exist_ok=True)
        (brief_dir / "concept_note.md").write_text(
            CONCEPT_NOTE_TEXT, encoding="utf-8"
        )
        # strategic_positioning.md and project_summary.json absent

        ctx = _build_caller_context("topic-scope-check", {}, tmp_path)

        assert len(ctx) == 1
        cn_key = "docs/tier3_project_instantiation/project_brief/concept_note.md"
        assert cn_key in ctx

    def test_skill_context_sources_registry_has_topic_scope_check(self) -> None:
        """Verify the registry entry exists."""
        assert "topic-scope-check" in _SKILL_CONTEXT_SOURCES
        sources = _SKILL_CONTEXT_SOURCES["topic-scope-check"]
        assert len(sources) == 3
        assert any("concept_note.md" in s for s in sources)
        assert any("strategic_positioning.md" in s for s in sources)
        assert any("project_summary.json" in s for s in sources)


# ---------------------------------------------------------------------------
# B. TAPM prompt includes caller context
# ---------------------------------------------------------------------------


class TestTapmPromptCallerContext:
    """Verify _assemble_tapm_prompt renders caller context into the prompt."""

    def _make_tapm_env(self, tmp_path: Path) -> Path:
        """Create minimal environment for TAPM prompt assembly."""
        _write_yaml(
            tmp_path / ".claude" / "workflows" / "system_orchestration"
            / "artifact_schema_specification.yaml",
            {"tier4_phase_output_schemas": {}},
        )
        return tmp_path

    def test_context_appears_in_prompt(self, tmp_path: Path) -> None:
        repo_root = self._make_tapm_env(tmp_path)
        ctx = {
            "docs/project_brief/concept_note.md": "Test concept text about AI agents.",
            "docs/project_brief/summary.json": {"acronym": "TEST"},
        }

        _sys, user = _assemble_tapm_prompt(
            skill_spec="# test skill\nDo something.",
            skill_id="topic-scope-check",
            run_id="run-001",
            reads_from=["docs/scope.json"],
            writes_to=["docs/decision_log/"],
            constraints=[],
            repo_root=repo_root,
            caller_context=ctx,
        )

        assert "# Caller-Supplied Context" in user
        assert "concept_note.md" in user
        assert "Test concept text about AI agents." in user
        assert '"acronym": "TEST"' in user

    def test_no_context_section_when_empty(self, tmp_path: Path) -> None:
        repo_root = self._make_tapm_env(tmp_path)

        _sys, user = _assemble_tapm_prompt(
            skill_spec="# test skill",
            skill_id="other-skill",
            run_id="run-001",
            reads_from=[],
            writes_to=["docs/out/"],
            constraints=[],
            repo_root=repo_root,
            caller_context=None,
        )

        assert "Caller-Supplied Context" not in user

    def test_no_context_section_when_empty_dict(self, tmp_path: Path) -> None:
        repo_root = self._make_tapm_env(tmp_path)

        _sys, user = _assemble_tapm_prompt(
            skill_spec="# test skill",
            skill_id="other-skill",
            run_id="run-001",
            reads_from=[],
            writes_to=["docs/out/"],
            constraints=[],
            repo_root=repo_root,
            caller_context={},
        )

        assert "Caller-Supplied Context" not in user

    def test_context_before_output_requirements(self, tmp_path: Path) -> None:
        """Caller context appears before Output Requirements section."""
        repo_root = self._make_tapm_env(tmp_path)
        ctx = {"docs/concept.md": "Some concept text."}

        _sys, user = _assemble_tapm_prompt(
            skill_spec="# test skill",
            skill_id="topic-scope-check",
            run_id="run-001",
            reads_from=[],
            writes_to=["docs/out/"],
            constraints=[],
            repo_root=repo_root,
            caller_context=ctx,
        )

        ctx_pos = user.index("Caller-Supplied Context")
        out_pos = user.index("Output Requirements")
        assert ctx_pos < out_pos


# ---------------------------------------------------------------------------
# C. cli-prompt mode merges caller context
# ---------------------------------------------------------------------------


class TestCliPromptCallerContext:
    """Verify that caller_context is merged into inputs for cli-prompt mode."""

    def _make_cli_skill_env(self, tmp_path: Path) -> Path:
        """Create environment for cli-prompt skill execution."""
        repo_root = tmp_path
        _write_yaml(
            repo_root / ".claude" / "workflows" / "system_orchestration"
            / "skill_catalog.yaml",
            {"skill_catalog": [{
                "id": "test-skill",
                "execution_mode": "cli-prompt",
                "reads_from": ["docs/scope.json"],
                "writes_to": ["docs/out/result.json"],
                "constitutional_constraints": [],
            }]},
        )
        _write_yaml(
            repo_root / ".claude" / "workflows" / "system_orchestration"
            / "artifact_schema_specification.yaml",
            {"tier4_phase_output_schemas": {
                "test_result": {
                    "canonical_path": "docs/out/result.json",
                    "schema_id_value": "test_v1",
                    "fields": {
                        "schema_id": {"required": True},
                        "run_id": {"required": True},
                        "result": {"required": True},
                    },
                }
            }},
        )
        spec_dir = repo_root / ".claude" / "skills"
        spec_dir.mkdir(parents=True, exist_ok=True)
        (spec_dir / "test-skill.md").write_text(
            "# test-skill\nTest spec.", encoding="utf-8"
        )
        _write_json(repo_root / "docs" / "scope.json", {"scope": "test"})
        return repo_root

    def test_context_merged_into_prompt(self, tmp_path: Path) -> None:
        """In cli-prompt mode, caller_context content appears in the prompt."""
        from runner.skill_runtime import run_skill

        repo_root = self._make_cli_skill_env(tmp_path)
        ctx = {"docs/concept.md": "Concept text for checking."}
        captured_prompts: list[str] = []

        def _capture_claude(*, system_prompt, user_prompt, **kw):
            captured_prompts.append(user_prompt)
            return json.dumps({
                "schema_id": "test_v1",
                "run_id": "run-001",
                "result": "ok",
            })

        with patch(
            "runner.skill_runtime.invoke_claude_text",
            side_effect=_capture_claude,
        ):
            run_skill(
                "test-skill", "run-001", repo_root,
                caller_context=ctx,
            )

        assert len(captured_prompts) == 1
        assert "Concept text for checking." in captured_prompts[0]


# ---------------------------------------------------------------------------
# D. run_agent passes caller_context for context-sensitive skills
# ---------------------------------------------------------------------------


def _make_concept_refiner_env(
    tmp_path: Path,
    *,
    write_concept_sources: bool = True,
) -> dict:
    """Create a synthetic environment mimicking concept_refiner in Phase 2."""
    repo_root = tmp_path

    reads_from = [
        "docs/tier3_project_instantiation/project_brief/",
        "docs/tier2b_topic_and_call_sources/extracted/",
    ]

    skill_ids = ["concept-alignment-check", "topic-scope-check"]

    # Agent catalog
    _write_yaml(
        repo_root / ".claude" / "workflows" / "system_orchestration"
        / "agent_catalog.yaml",
        {"agent_catalog": [{
            "id": "concept_refiner",
            "reads_from": reads_from,
            "writes_to": [
                "docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/",
            ],
        }]},
    )

    # Skill catalog — concept-alignment-check and topic-scope-check
    _write_yaml(
        repo_root / ".claude" / "workflows" / "system_orchestration"
        / "skill_catalog.yaml",
        {"skill_catalog": [
            {
                "id": "concept-alignment-check",
                "execution_mode": "tapm",
                "reads_from": ["docs/tier2b_topic_and_call_sources/extracted/"],
                "writes_to": ["docs/tier4_orchestration_state/decision_log/"],
                "constitutional_constraints": [],
                "used_by_agents": ["concept_refiner"],
            },
            {
                "id": "topic-scope-check",
                "execution_mode": "tapm",
                "reads_from": [
                    "docs/tier2b_topic_and_call_sources/extracted/scope_requirements.json",
                    "docs/tier2b_topic_and_call_sources/extracted/call_constraints.json",
                ],
                "writes_to": ["docs/tier4_orchestration_state/decision_log/"],
                "constitutional_constraints": [],
                "used_by_agents": ["concept_refiner"],
            },
        ]},
    )

    # Manifest with artifact_registry
    manifest_path = repo_root / "manifest_test.yaml"
    _write_yaml(manifest_path, {
        "name": "test",
        "version": "1.1",
        "node_registry": [{
            "node_id": "n02_concept_refinement",
            "agent": "concept_refiner",
            "skills": skill_ids,
            "phase_id": "phase_02_concept_refinement",
            "exit_gate": "phase_02_gate",
        }],
        "edge_registry": [],
        "artifact_registry": [{
            "path": "docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/concept_refinement_summary.json",
            "produced_by": "n02_concept_refinement",
            "tier": "tier4_phase_output",
        }],
    })

    # Agent definition and prompt spec
    agent_dir = repo_root / ".claude" / "agents"
    agent_dir.mkdir(parents=True, exist_ok=True)
    (agent_dir / "concept_refiner.md").write_text(
        "# concept_refiner\nPhase 2 agent.", encoding="utf-8"
    )
    prompts_dir = agent_dir / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    (prompts_dir / "concept_refiner_prompt_spec.md").write_text(
        "# concept_refiner prompt\n\n"
        "Invoke concept-alignment-check.\n"
        "Invoke topic-scope-check.\n",
        encoding="utf-8",
    )

    # Input artifacts
    if write_concept_sources:
        _write_concept_sources(repo_root)

    # Tier 2B extracted (needed by concept-alignment-check reads_from)
    extracted_dir = (
        repo_root / "docs" / "tier2b_topic_and_call_sources" / "extracted"
    )
    extracted_dir.mkdir(parents=True, exist_ok=True)
    _write_json(
        extracted_dir / "scope_requirements.json",
        {"requirements": [{"requirement_id": "SR-01", "mandatory": True}]},
    )
    _write_json(
        extracted_dir / "call_constraints.json",
        {"constraints": []},
    )

    return {
        "agent_id": "concept_refiner",
        "node_id": "n02_concept_refinement",
        "run_id": "run-test-002",
        "repo_root": repo_root,
        "manifest_path": manifest_path,
        "skill_ids": skill_ids,
        "phase_id": "phase_02_concept_refinement",
    }


class TestRunAgentCallerContext:
    """Verify that run_agent builds and passes caller_context for
    context-sensitive skills."""

    def test_topic_scope_check_receives_context(self, tmp_path: Path) -> None:
        """When concept sources exist, topic-scope-check gets caller_context."""
        kwargs = _make_concept_refiner_env(tmp_path)
        # Write gate-relevant artifact
        _write_json(
            tmp_path / "docs" / "tier4_orchestration_state" / "phase_outputs"
            / "phase2_concept_refinement" / "concept_refinement_summary.json",
            {"summary": "done"},
        )
        captured_calls: list[dict] = []

        def _capture_run_skill(skill_id, run_id, repo_root, inputs=None, **kw):
            captured_calls.append({
                "skill_id": skill_id,
                "caller_context": kw.get("caller_context"),
            })
            return _success_skill()

        with patch(_RUN_SKILL_TARGET, side_effect=_capture_run_skill):
            run_agent(**kwargs)

        # Find the topic-scope-check invocation
        tsc_calls = [
            c for c in captured_calls
            if c["skill_id"] == "topic-scope-check"
        ]
        assert len(tsc_calls) == 1
        ctx = tsc_calls[0]["caller_context"]
        assert ctx is not None
        assert len(ctx) == 3

        # Verify concept text is present
        cn_key = "docs/tier3_project_instantiation/project_brief/concept_note.md"
        assert cn_key in ctx
        assert "MAESTRO" in ctx[cn_key]

    def test_other_skill_gets_no_context(self, tmp_path: Path) -> None:
        """concept-alignment-check does NOT get caller_context."""
        kwargs = _make_concept_refiner_env(tmp_path)
        _write_json(
            tmp_path / "docs" / "tier4_orchestration_state" / "phase_outputs"
            / "phase2_concept_refinement" / "concept_refinement_summary.json",
            {"summary": "done"},
        )
        captured_calls: list[dict] = []

        def _capture_run_skill(skill_id, run_id, repo_root, inputs=None, **kw):
            captured_calls.append({
                "skill_id": skill_id,
                "caller_context": kw.get("caller_context"),
            })
            return _success_skill()

        with patch(_RUN_SKILL_TARGET, side_effect=_capture_run_skill):
            run_agent(**kwargs)

        cac_calls = [
            c for c in captured_calls
            if c["skill_id"] == "concept-alignment-check"
        ]
        assert len(cac_calls) == 1
        # No context for non-context-sensitive skills
        assert cac_calls[0]["caller_context"] is None


# ---------------------------------------------------------------------------
# E. Fail-closed when concept sources are absent
# ---------------------------------------------------------------------------


class TestFailClosedAbsentSources:
    """When concept files are genuinely absent, caller_context is empty
    and the skill's own validation produces MISSING_INPUT."""

    def test_empty_context_when_no_concept_files(self, tmp_path: Path) -> None:
        """_build_caller_context returns {} when no concept files exist."""
        ctx = _build_caller_context("topic-scope-check", {}, tmp_path)
        assert ctx == {}

    def test_run_agent_passes_none_when_sources_absent(
        self, tmp_path: Path
    ) -> None:
        """When concept files are absent, caller_context is None (empty dict
        is converted to None by the `or None` expression)."""
        kwargs = _make_concept_refiner_env(
            tmp_path, write_concept_sources=False
        )
        _write_json(
            tmp_path / "docs" / "tier4_orchestration_state" / "phase_outputs"
            / "phase2_concept_refinement" / "concept_refinement_summary.json",
            {"summary": "done"},
        )
        captured_calls: list[dict] = []

        def _capture_run_skill(skill_id, run_id, repo_root, inputs=None, **kw):
            captured_calls.append({
                "skill_id": skill_id,
                "caller_context": kw.get("caller_context"),
            })
            return _success_skill()

        with patch(_RUN_SKILL_TARGET, side_effect=_capture_run_skill):
            run_agent(**kwargs)

        tsc_calls = [
            c for c in captured_calls
            if c["skill_id"] == "topic-scope-check"
        ]
        assert len(tsc_calls) == 1
        # Empty context → None (via `or None` expression)
        assert tsc_calls[0]["caller_context"] is None


# ---------------------------------------------------------------------------
# F. Non-Phase-2 and other-skill usage unaffected
# ---------------------------------------------------------------------------


class TestNonPhase2Usage:
    """Verify that the caller context mechanism does not break existing
    behavior for other agents or skills."""

    def test_call_analyzer_topic_scope_check_also_gets_context(
        self, tmp_path: Path
    ) -> None:
        """topic-scope-check gets context regardless of which agent invokes it,
        as long as the concept files exist."""
        # Simulate a call_analyzer environment
        repo_root = tmp_path

        _write_yaml(
            repo_root / ".claude" / "workflows" / "system_orchestration"
            / "agent_catalog.yaml",
            {"agent_catalog": [{
                "id": "call_analyzer",
                "reads_from": [
                    "docs/tier3_project_instantiation/project_brief/",
                    "docs/tier2b_topic_and_call_sources/extracted/",
                ],
                "writes_to": [
                    "docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/",
                ],
            }]},
        )
        _write_yaml(
            repo_root / ".claude" / "workflows" / "system_orchestration"
            / "skill_catalog.yaml",
            {"skill_catalog": [{
                "id": "topic-scope-check",
                "execution_mode": "tapm",
                "reads_from": [
                    "docs/tier2b_topic_and_call_sources/extracted/scope_requirements.json",
                ],
                "writes_to": ["docs/tier4_orchestration_state/decision_log/"],
                "constitutional_constraints": [],
                "used_by_agents": ["call_analyzer"],
            }]},
        )

        manifest_path = repo_root / "manifest_test.yaml"
        _write_yaml(manifest_path, {
            "name": "test",
            "version": "1.1",
            "node_registry": [{
                "node_id": "n01_call_analysis",
                "agent": "call_analyzer",
                "skills": ["topic-scope-check"],
                "phase_id": "phase_01_call_analysis",
                "exit_gate": "phase_01_gate",
            }],
            "edge_registry": [],
            "artifact_registry": [{
                "path": "docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/call_analysis_summary.json",
                "produced_by": "n01_call_analysis",
                "tier": "tier4_phase_output",
            }],
        })

        agent_dir = repo_root / ".claude" / "agents"
        agent_dir.mkdir(parents=True, exist_ok=True)
        (agent_dir / "call_analyzer.md").write_text(
            "# call_analyzer\nPhase 1.", encoding="utf-8"
        )
        prompts_dir = agent_dir / "prompts"
        prompts_dir.mkdir(parents=True, exist_ok=True)
        (prompts_dir / "call_analyzer_prompt_spec.md").write_text(
            "# call_analyzer prompt\nInvoke topic-scope-check.\n",
            encoding="utf-8",
        )

        _write_concept_sources(repo_root)

        extracted_dir = (
            repo_root / "docs" / "tier2b_topic_and_call_sources" / "extracted"
        )
        extracted_dir.mkdir(parents=True, exist_ok=True)
        _write_json(
            extracted_dir / "scope_requirements.json",
            {"requirements": [{"requirement_id": "SR-01", "mandatory": True}]},
        )

        _write_json(
            repo_root / "docs" / "tier4_orchestration_state" / "phase_outputs"
            / "phase1_call_analysis" / "call_analysis_summary.json",
            {"summary": "done"},
        )

        captured_calls: list[dict] = []

        def _capture_run_skill(skill_id, run_id, repo_root, inputs=None, **kw):
            captured_calls.append({
                "skill_id": skill_id,
                "caller_context": kw.get("caller_context"),
            })
            return _success_skill()

        with patch(_RUN_SKILL_TARGET, side_effect=_capture_run_skill):
            run_agent(
                agent_id="call_analyzer",
                node_id="n01_call_analysis",
                run_id="run-test-003",
                repo_root=repo_root,
                manifest_path=manifest_path,
                skill_ids=["topic-scope-check"],
                phase_id="phase_01_call_analysis",
            )

        tsc_calls = [
            c for c in captured_calls
            if c["skill_id"] == "topic-scope-check"
        ]
        assert len(tsc_calls) == 1
        ctx = tsc_calls[0]["caller_context"]
        assert ctx is not None
        assert len(ctx) == 3
        cn_key = "docs/tier3_project_instantiation/project_brief/concept_note.md"
        assert cn_key in ctx
