"""
Tests for the Tier 5 skill applicability guard in agent_runtime.

Covers the fix for the phase-applicability bug where
``proposal-section-traceability-check`` blocks Phase 2 solely because
Tier 5 deliverable artifacts do not yet exist.

Test cases:
  1. Phase 2 / pre-Tier-5: skill is skipped as not_applicable
  2. Phase 8 / Tier-5-present: skill runs normally; fail-closed preserved
  3. No fabricated outputs when skipped
  4. Existing Phase 2 skills (concept-alignment-check, decision-log-update)
     are unaffected by the guard
  5. Agent result is not marked as failed when only non-applicable skills
     are skipped
  6. _check_skill_applicability unit tests
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from runner.agent_runtime import (
    _check_skill_applicability,
    run_agent,
)
from runner.runtime_models import SkillResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_RUN_SKILL_TARGET = "runner.agent_runtime.run_skill"


def _write_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data), encoding="utf-8")


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _success_skill(outputs: list[str] | None = None) -> SkillResult:
    return SkillResult(status="success", outputs_written=outputs or [])


def _failure_skill(
    category: str = "MISSING_INPUT", reason: str = "test failure"
) -> SkillResult:
    return SkillResult(
        status="failure", failure_reason=reason, failure_category=category
    )


@pytest.fixture(autouse=True)
def _clear_caches() -> None:
    """Clear module-level caches between tests."""
    import runner.agent_runtime as _ar
    import runner.skill_runtime as _sr

    _ar._agent_catalog_cache.clear()
    _ar._artifact_registry_cache.clear()
    _sr._catalog_cache.clear()
    _sr._schema_spec_cache.clear()


def _make_phase2_env(
    tmp_path: Path,
    *,
    skill_ids: list[str] | None = None,
    create_tier5: bool = False,
) -> dict:
    """Create a synthetic Phase 2 environment for run_agent().

    When *create_tier5* is True, Tier 5 proposal section directories
    are populated to simulate a Tier-5-applicable phase.
    """
    repo_root = tmp_path
    agent_id = "concept_refiner"
    node_id = "n02_concept_refinement"

    if skill_ids is None:
        skill_ids = [
            "concept-alignment-check",
            "topic-scope-check",
            "proposal-section-traceability-check",
            "decision-log-update",
        ]

    reads_from = [
        "docs/tier3_project_instantiation/project_brief/",
        "docs/tier2b_topic_and_call_sources/extracted/",
    ]

    # Agent catalog
    _write_yaml(
        repo_root
        / ".claude"
        / "workflows"
        / "system_orchestration"
        / "agent_catalog.yaml",
        {
            "agent_catalog": [
                {
                    "id": agent_id,
                    "reads_from": reads_from,
                    "writes_to": [
                        "docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/"
                    ],
                }
            ]
        },
    )

    # Skill catalog
    skill_catalog = []
    for sid in skill_ids:
        entry: dict[str, Any] = {
            "id": sid,
            "reads_from": reads_from.copy(),
            "writes_to": [
                "docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/"
            ],
            "constitutional_constraints": [],
            "used_by_agents": [agent_id],
        }
        if sid == "proposal-section-traceability-check":
            entry["reads_from"] = [
                "docs/tier5_deliverables/proposal_sections/",
                "docs/tier5_deliverables/assembled_drafts/",
                "docs/tier1_normative_framework/extracted/",
                "docs/tier2a_instrument_schemas/extracted/",
                "docs/tier2b_topic_and_call_sources/extracted/",
                "docs/tier3_project_instantiation/",
            ]
            entry["writes_to"] = [
                "docs/tier4_orchestration_state/validation_reports/"
            ]
        skill_catalog.append(entry)

    _write_yaml(
        repo_root
        / ".claude"
        / "workflows"
        / "system_orchestration"
        / "skill_catalog.yaml",
        {"skill_catalog": skill_catalog},
    )

    # Manifest with artifact registry
    artifact_registry = [
        {
            "path": "docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/concept_refinement_summary.json",
            "produced_by": node_id,
            "tier": "tier4_phase_output",
        }
    ]
    manifest_path = repo_root / "manifest_test.yaml"
    _write_yaml(
        manifest_path,
        {
            "name": "test",
            "version": "1.1",
            "node_registry": [
                {
                    "node_id": node_id,
                    "agent": agent_id,
                    "skills": skill_ids,
                    "phase_id": "phase_02_concept_refinement",
                    "exit_gate": "phase_02_gate",
                }
            ],
            "edge_registry": [],
            "artifact_registry": artifact_registry,
        },
    )

    # Agent definition and prompt spec
    agent_dir = repo_root / ".claude" / "agents"
    (agent_dir / f"{agent_id}.md").parent.mkdir(parents=True, exist_ok=True)
    (agent_dir / f"{agent_id}.md").write_text(
        f"# {agent_id}\nConcept refiner agent.", encoding="utf-8"
    )
    prompts_dir = agent_dir / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    prompt_content = f"# {agent_id} prompt spec\n\n"
    for sid in skill_ids:
        prompt_content += f"Invoke {sid}.\n"
    (prompts_dir / f"{agent_id}_prompt_spec.md").write_text(
        prompt_content, encoding="utf-8"
    )

    # Create input directories with minimal content
    _write_json(
        repo_root / "docs" / "tier3_project_instantiation" / "project_brief" / "concept_note.json",
        {"concept": "test"},
    )
    _write_json(
        repo_root / "docs" / "tier2b_topic_and_call_sources" / "extracted" / "call_constraints.json",
        {"constraints": []},
    )

    # Optionally populate Tier 5
    if create_tier5:
        _write_json(
            repo_root / "docs" / "tier5_deliverables" / "proposal_sections" / "section_1.json",
            {"content": "test proposal section", "schema_id": "orch.tier5.proposal_section.v1"},
        )

    return {
        "agent_id": agent_id,
        "node_id": node_id,
        "run_id": "run-test-phase2",
        "repo_root": repo_root,
        "manifest_path": manifest_path,
        "skill_ids": skill_ids,
        "phase_id": "phase_02_concept_refinement",
    }


# ---------------------------------------------------------------------------
# 1. _check_skill_applicability unit tests
# ---------------------------------------------------------------------------


class TestCheckSkillApplicability:
    """Direct unit tests for the applicability guard function."""

    def test_non_tier5_skill_always_applicable(self, tmp_path: Path) -> None:
        """Skills not in _TIER5_AUDIT_SKILLS are always applicable."""
        applicable, reason = _check_skill_applicability(
            "concept-alignment-check", tmp_path
        )
        assert applicable is True
        assert reason is None

    def test_traceability_not_applicable_no_tier5(self, tmp_path: Path) -> None:
        """proposal-section-traceability-check is not applicable when
        Tier 5 directories are absent."""
        applicable, reason = _check_skill_applicability(
            "proposal-section-traceability-check", tmp_path
        )
        assert applicable is False
        assert reason is not None
        assert "not yet exist" in reason
        assert "Tier 5" in reason

    def test_traceability_not_applicable_empty_tier5_dirs(
        self, tmp_path: Path
    ) -> None:
        """Not applicable when Tier 5 dirs exist but contain no JSON files."""
        (tmp_path / "docs" / "tier5_deliverables" / "proposal_sections").mkdir(
            parents=True
        )
        (tmp_path / "docs" / "tier5_deliverables" / "assembled_drafts").mkdir(
            parents=True
        )
        applicable, reason = _check_skill_applicability(
            "proposal-section-traceability-check", tmp_path
        )
        assert applicable is False
        assert reason is not None

    def test_traceability_applicable_with_proposal_sections(
        self, tmp_path: Path
    ) -> None:
        """Applicable when proposal_sections/ contains JSON files."""
        _write_json(
            tmp_path / "docs" / "tier5_deliverables" / "proposal_sections" / "s1.json",
            {"content": "test"},
        )
        applicable, reason = _check_skill_applicability(
            "proposal-section-traceability-check", tmp_path
        )
        assert applicable is True
        assert reason is None

    def test_traceability_applicable_with_assembled_drafts(
        self, tmp_path: Path
    ) -> None:
        """Applicable when assembled_drafts/ contains JSON files."""
        _write_json(
            tmp_path / "docs" / "tier5_deliverables" / "assembled_drafts" / "assembled_draft.json",
            {"sections": []},
        )
        applicable, reason = _check_skill_applicability(
            "proposal-section-traceability-check", tmp_path
        )
        assert applicable is True
        assert reason is None


# ---------------------------------------------------------------------------
# 2. Phase 2 / pre-Tier-5: skill skipped as not_applicable
# ---------------------------------------------------------------------------


class TestPhase2SkillSkipped:
    """In Phase 2, proposal-section-traceability-check must be skipped
    (not failed) when Tier 5 artifacts are absent."""

    def test_traceability_skipped_in_phase2(self, tmp_path: Path) -> None:
        from unittest.mock import patch

        kwargs = _make_phase2_env(tmp_path, create_tier5=False)
        # Write gate-relevant artifact
        _write_json(
            tmp_path
            / "docs"
            / "tier4_orchestration_state"
            / "phase_outputs"
            / "phase2_concept_refinement"
            / "concept_refinement_summary.json",
            {"summary": "done"},
        )

        with patch(_RUN_SKILL_TARGET, return_value=_success_skill()):
            result = run_agent(**kwargs)

        # Agent should succeed — traceability skip is non-blocking
        assert result.status == "success"
        assert result.can_evaluate_exit_gate is True

        # Verify traceability skill was recorded as not_applicable
        traceability_records = [
            r
            for r in result.invoked_skills
            if r.skill_id == "proposal-section-traceability-check"
        ]
        assert len(traceability_records) == 1
        assert traceability_records[0].status == "not_applicable"
        assert "not yet exist" in (traceability_records[0].failure_reason or "")

    def test_traceability_skip_does_not_block_other_skills(
        self, tmp_path: Path
    ) -> None:
        from unittest.mock import patch

        kwargs = _make_phase2_env(tmp_path, create_tier5=False)
        _write_json(
            tmp_path
            / "docs"
            / "tier4_orchestration_state"
            / "phase_outputs"
            / "phase2_concept_refinement"
            / "concept_refinement_summary.json",
            {"summary": "done"},
        )

        invoked_skills: list[str] = []

        def _track(skill_id, *args, **kw):
            invoked_skills.append(skill_id)
            return _success_skill()

        with patch(_RUN_SKILL_TARGET, side_effect=_track):
            result = run_agent(**kwargs)

        assert result.status == "success"
        # proposal-section-traceability-check was NOT passed to run_skill
        assert "proposal-section-traceability-check" not in invoked_skills
        # Other skills were invoked
        assert "concept-alignment-check" in invoked_skills
        assert "topic-scope-check" in invoked_skills
        assert "decision-log-update" in invoked_skills


# ---------------------------------------------------------------------------
# 3. Applicable-phase fail-closed behavior preserved
# ---------------------------------------------------------------------------


class TestApplicablePhaseFail:
    """When Tier 5 exists, the skill must run and fail normally on
    missing required inputs — fail-closed is preserved."""

    def test_traceability_skipped_when_no_auditable_artifact(self, tmp_path: Path) -> None:
        """Even when Tier 5 exists, if no earlier skill in the agent body
        produced an auditable artifact, the traceability check is skipped
        (artifact_path injection finds nothing to audit)."""
        from unittest.mock import patch

        kwargs = _make_phase2_env(tmp_path, create_tier5=True)
        _write_json(
            tmp_path
            / "docs"
            / "tier4_orchestration_state"
            / "phase_outputs"
            / "phase2_concept_refinement"
            / "concept_refinement_summary.json",
            {"summary": "done"},
        )

        invoked_skills: list[str] = []

        def _track(skill_id, *args, **kw):
            invoked_skills.append(skill_id)
            return _success_skill()

        with patch(_RUN_SKILL_TARGET, side_effect=_track):
            result = run_agent(**kwargs)

        # Traceability check is NOT invoked via run_skill — it is skipped
        # because no auditable artifact was produced by earlier skills
        assert "proposal-section-traceability-check" not in invoked_skills
        # But it IS recorded in invoked_skills as a failure
        traceability_records = [
            r for r in result.invoked_skills
            if r.skill_id == "proposal-section-traceability-check"
        ]
        assert len(traceability_records) == 1
        assert traceability_records[0].status == "failure"
        assert traceability_records[0].failure_category == "MISSING_INPUT"

    def test_traceability_failure_propagates_when_no_artifact(
        self, tmp_path: Path
    ) -> None:
        """When no auditable artifact was produced by earlier skills,
        the traceability check is skipped with MISSING_INPUT and the
        failure propagates to the agent result — fail-closed preserved."""
        from unittest.mock import patch

        kwargs = _make_phase2_env(tmp_path, create_tier5=True)

        with patch(_RUN_SKILL_TARGET, return_value=_success_skill()):
            result = run_agent(**kwargs)

        # Failure is propagated — fail-closed preserved
        assert result.status == "failure"
        assert result.failure_category == "SKILL_FAILURE"


# ---------------------------------------------------------------------------
# 4. No fabricated outputs when skipped
# ---------------------------------------------------------------------------


class TestNoFabricatedOutputs:
    """When skipped, no validation report or fake artifact is produced."""

    def test_no_artifacts_written_for_skipped_skill(
        self, tmp_path: Path
    ) -> None:
        from unittest.mock import patch

        kwargs = _make_phase2_env(tmp_path, create_tier5=False)
        _write_json(
            tmp_path
            / "docs"
            / "tier4_orchestration_state"
            / "phase_outputs"
            / "phase2_concept_refinement"
            / "concept_refinement_summary.json",
            {"summary": "done"},
        )

        with patch(_RUN_SKILL_TARGET, return_value=_success_skill()):
            result = run_agent(**kwargs)

        # No validation report directory content from the skipped skill
        validation_dir = (
            tmp_path / "docs" / "tier4_orchestration_state" / "validation_reports"
        )
        if validation_dir.exists():
            json_files = list(validation_dir.glob("*.json"))
            traceability_files = [
                f for f in json_files if "traceability" in f.name
            ]
            assert len(traceability_files) == 0, (
                "Skipped skill must not produce validation reports"
            )

        # The skipped invocation record has no outputs_written
        traceability_records = [
            r
            for r in result.invoked_skills
            if r.skill_id == "proposal-section-traceability-check"
        ]
        assert traceability_records[0].outputs_written == []


# ---------------------------------------------------------------------------
# 5. Existing Phase 2 skills unaffected
# ---------------------------------------------------------------------------


class TestOtherSkillsUnaffected:
    """concept-alignment-check and decision-log-update must not be
    affected by the applicability guard."""

    def test_non_tier5_skills_always_invoked(self, tmp_path: Path) -> None:
        from unittest.mock import patch

        kwargs = _make_phase2_env(tmp_path, create_tier5=False)
        _write_json(
            tmp_path
            / "docs"
            / "tier4_orchestration_state"
            / "phase_outputs"
            / "phase2_concept_refinement"
            / "concept_refinement_summary.json",
            {"summary": "done"},
        )

        invoked_skills: list[str] = []

        def _track(skill_id, *args, **kw):
            invoked_skills.append(skill_id)
            return _success_skill()

        with patch(_RUN_SKILL_TARGET, side_effect=_track):
            result = run_agent(**kwargs)

        assert result.status == "success"
        # All non-tier5 skills were invoked normally
        assert "concept-alignment-check" in invoked_skills
        assert "topic-scope-check" in invoked_skills
        assert "decision-log-update" in invoked_skills

    def test_guard_returns_true_for_all_other_skills(self) -> None:
        """_check_skill_applicability returns (True, None) for skills
        not in _TIER5_AUDIT_SKILLS, regardless of disk state."""
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            for skill in [
                "concept-alignment-check",
                "topic-scope-check",
                "decision-log-update",
                "work-package-normalization",
                "call-scope-extraction",
            ]:
                applicable, reason = _check_skill_applicability(skill, p)
                assert applicable is True, f"{skill} should always be applicable"
                assert reason is None


# ---------------------------------------------------------------------------
# 6. Agent result not marked failed from non-applicable skill alone
# ---------------------------------------------------------------------------


class TestAgentResultNotFailed:
    """run_agent() must not set status='failure' solely because a
    non-applicable skill was skipped."""

    def test_only_nonapplicable_skips_still_success(
        self, tmp_path: Path
    ) -> None:
        from unittest.mock import patch

        kwargs = _make_phase2_env(
            tmp_path,
            skill_ids=["proposal-section-traceability-check", "concept-alignment-check"],
            create_tier5=False,
        )
        _write_json(
            tmp_path
            / "docs"
            / "tier4_orchestration_state"
            / "phase_outputs"
            / "phase2_concept_refinement"
            / "concept_refinement_summary.json",
            {"summary": "done"},
        )

        with patch(_RUN_SKILL_TARGET, return_value=_success_skill()):
            result = run_agent(**kwargs)

        assert result.status == "success"
        assert result.failure_reason is None
        assert result.failure_category is None

    def test_real_failure_still_propagated_alongside_skip(
        self, tmp_path: Path
    ) -> None:
        """If another skill genuinely fails, that failure is still
        propagated even when a non-applicable skill is skipped."""
        from unittest.mock import patch

        kwargs = _make_phase2_env(
            tmp_path,
            skill_ids=[
                "proposal-section-traceability-check",
                "concept-alignment-check",
                "decision-log-update",
            ],
            create_tier5=False,
        )

        def _fail_second(skill_id, *args, **kw):
            if skill_id == "decision-log-update":
                return _failure_skill("MISSING_INPUT", "log dir missing")
            return _success_skill()

        with patch(_RUN_SKILL_TARGET, side_effect=_fail_second):
            result = run_agent(**kwargs)

        # The real failure is propagated
        assert result.status == "failure"
        assert result.failure_category == "SKILL_FAILURE"
        assert "log dir missing" in (result.failure_reason or "")

        # But the traceability skill was still recorded as not_applicable
        traceability = [
            r
            for r in result.invoked_skills
            if r.skill_id == "proposal-section-traceability-check"
        ]
        assert traceability[0].status == "not_applicable"
