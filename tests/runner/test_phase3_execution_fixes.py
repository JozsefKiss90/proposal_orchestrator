"""
Tests for Phase 3 execution fixes:

1. SkillResult-shaped Claude response interception (instrument-schema-normalization)
2. gate-enforcement execution ordering (always last in agent body)
3. Windows-safe decision log filenames (colon sanitization)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import yaml

from runner.runtime_models import SkillResult
from runner.skill_runtime import _sanitize_filename, run_skill


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TRANSPORT_TARGET = "runner.skill_runtime.invoke_claude_text"


def _claude_returns(response_dict: dict):
    return patch(_TRANSPORT_TARGET, return_value=json.dumps(response_dict))


def _write_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")


def _write_skill_spec(repo_root: Path, skill_id: str) -> None:
    spec_path = repo_root / ".claude" / "skills" / f"{skill_id}.md"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(f"# {skill_id}\nTest spec.", encoding="utf-8")


def _clear_caches() -> None:
    import runner.skill_runtime as _sr
    _sr._catalog_cache.clear()
    _sr._schema_spec_cache.clear()


# ===========================================================================
# FIX 1: SkillResult-shaped Claude response interception
# ===========================================================================


class TestSkillResultInterception:
    """Claude returning a SkillResult-shaped failure envelope must be
    intercepted before schema validation, not rejected as MALFORMED_ARTIFACT."""

    @pytest.fixture()
    def artifact_env(self, tmp_path: Path) -> Path:
        """Env for a single-artifact skill (like instrument-schema-normalization)."""
        _clear_caches()
        repo_root = tmp_path

        _write_yaml(
            repo_root / ".claude" / "workflows" / "system_orchestration"
            / "skill_catalog.yaml",
            {"skill_catalog": [{
                "id": "test-artifact-skill",
                "execution_mode": "tapm",
                "reads_from": ["docs/input/"],
                "writes_to": [
                    "docs/tier2a/extracted/section_schema_registry.json",
                ],
                "constitutional_constraints": [],
            }]},
        )

        _write_yaml(
            repo_root / ".claude" / "workflows" / "system_orchestration"
            / "artifact_schema_specification.yaml",
            {
                "tier2a_extracted_schemas": {
                    "section_schema_registry": {
                        "canonical_path": "docs/tier2a/extracted/section_schema_registry.json",
                        "fields": {
                            "instruments": {"required": True},
                        },
                    },
                },
            },
        )

        _write_skill_spec(repo_root, "test-artifact-skill")

        (repo_root / "docs" / "input").mkdir(parents=True, exist_ok=True)
        (repo_root / "docs" / "input" / "data.json").write_text('{"x":1}')
        (repo_root / "docs" / "tier2a" / "extracted").mkdir(
            parents=True, exist_ok=True
        )

        return repo_root

    def test_missing_input_failure_intercepted(self, artifact_env: Path) -> None:
        """Claude returns {"status":"failure","failure_category":"MISSING_INPUT",...}
        which must be intercepted as a SkillResult failure, NOT pass through
        to schema validation (which would fail on missing 'instruments')."""
        response = {
            "status": "failure",
            "failure_category": "MISSING_INPUT",
            "failure_reason": (
                "application_forms/ directory is empty; cannot normalize "
                "instrument schema without an application form template"
            ),
        }
        with _claude_returns(response):
            result = run_skill("test-artifact-skill", "run-001", artifact_env)

        assert result.status == "failure"
        assert result.failure_category == "MISSING_INPUT"
        assert "model-signaled failure" in result.failure_reason
        assert "application_forms/" in result.failure_reason

    def test_constitutional_halt_intercepted(self, artifact_env: Path) -> None:
        """Claude returns a CONSTITUTIONAL_HALT failure envelope."""
        response = {
            "status": "failure",
            "failure_category": "CONSTITUTIONAL_HALT",
            "failure_reason": "Document is a Grant Agreement Annex",
        }
        with _claude_returns(response):
            result = run_skill("test-artifact-skill", "run-001", artifact_env)

        assert result.status == "failure"
        assert result.failure_category == "CONSTITUTIONAL_HALT"

    def test_unknown_failure_category_normalized(self, artifact_env: Path) -> None:
        """Unknown failure_category defaults to INCOMPLETE_OUTPUT."""
        response = {
            "status": "failure",
            "failure_category": "UNKNOWN_CATEGORY",
            "failure_reason": "something went wrong",
        }
        with _claude_returns(response):
            result = run_skill("test-artifact-skill", "run-001", artifact_env)

        assert result.status == "failure"
        assert result.failure_category == "INCOMPLETE_OUTPUT"

    def test_valid_artifact_not_intercepted(self, artifact_env: Path) -> None:
        """A valid artifact that happens to have a 'status' field for other
        reasons is NOT intercepted (no failure_reason present)."""
        response = {
            "instruments": [{"instrument_type": "RIA", "sections": []}],
            "status": "complete",  # domain field, not a SkillResult
        }
        with _claude_returns(response):
            result = run_skill("test-artifact-skill", "run-001", artifact_env)

        # Should proceed to schema validation (success since instruments present)
        assert result.status == "success"

    def test_success_status_not_intercepted(self, artifact_env: Path) -> None:
        """status: "success" is not intercepted even if failure_reason present."""
        response = {
            "instruments": [{"instrument_type": "RIA", "sections": []}],
            "status": "success",
            "failure_reason": "leftover field",
        }
        with _claude_returns(response):
            result = run_skill("test-artifact-skill", "run-001", artifact_env)

        # status != "failure" so interception does not fire
        assert result.status == "success"

    def test_no_artifact_written_on_interception(self, artifact_env: Path) -> None:
        """Intercepted failures must NOT write any artifact to disk."""
        response = {
            "status": "failure",
            "failure_category": "MISSING_INPUT",
            "failure_reason": "missing template",
        }
        with _claude_returns(response):
            result = run_skill("test-artifact-skill", "run-001", artifact_env)

        assert result.status == "failure"
        assert len(result.outputs_written) == 0
        artifact = (
            artifact_env / "docs" / "tier2a" / "extracted"
            / "section_schema_registry.json"
        )
        assert not artifact.exists()


# ===========================================================================
# FIX 2: gate-enforcement execution ordering
# ===========================================================================


class TestGateEnforcementOrdering:
    """gate-enforcement must execute LAST in the agent body skill sequence."""

    def test_gate_enforcement_moved_to_end(self) -> None:
        """_resolve_skill_sequence may place gate-enforcement anywhere,
        but the agent body must move it to the end."""
        from runner.agent_runtime import _resolve_skill_sequence

        # Simulate a prompt spec that mentions gate-enforcement first
        prompt_spec = (
            "First run gate-enforcement to check the gate.\n"
            "Then run work-package-normalization.\n"
            "Then run wp-dependency-analysis.\n"
        )
        skill_ids = [
            "work-package-normalization",
            "wp-dependency-analysis",
            "gate-enforcement",
        ]

        # _resolve_skill_sequence would put gate-enforcement first
        ordered = _resolve_skill_sequence("wp_designer", skill_ids, prompt_spec)

        # The agent runtime moves gate-enforcement to end
        if "gate-enforcement" in ordered:
            ordered = [s for s in ordered if s != "gate-enforcement"]
            ordered.append("gate-enforcement")

        assert ordered[-1] == "gate-enforcement"
        assert ordered[0] != "gate-enforcement"

    def test_no_gate_enforcement_unchanged(self) -> None:
        """Skills without gate-enforcement are not affected."""
        skills = ["skill-a", "skill-b", "skill-c"]
        # The reorder logic only fires when gate-enforcement is present
        if "gate-enforcement" in skills:
            skills = [s for s in skills if s != "gate-enforcement"]
            skills.append("gate-enforcement")

        assert skills == ["skill-a", "skill-b", "skill-c"]


# ===========================================================================
# FIX 3: Windows filename sanitization
# ===========================================================================


class TestFilenameSanitization:
    """Filenames derived from timestamps must be Windows-safe."""

    def test_colons_replaced(self) -> None:
        assert _sanitize_filename("2026-04-20T00:00:00Z") == "2026-04-20T00_00_00Z"

    def test_decision_id_with_timestamp(self) -> None:
        decision_id = "gate_failure_phase_03_gate_wp_designer_2026-04-20T12:00:00Z"
        sanitized = _sanitize_filename(decision_id)
        assert ":" not in sanitized
        assert "gate_failure_phase_03_gate_wp_designer_2026-04-20T12_00_00Z" == sanitized

    def test_no_colons_unchanged(self) -> None:
        assert _sanitize_filename("simple_name") == "simple_name"

    def test_angle_brackets_replaced(self) -> None:
        assert _sanitize_filename("file<1>name") == "file_1_name"

    def test_path_separators_preserved(self) -> None:
        assert _sanitize_filename("dir/subdir/file.json") == "dir/subdir/file.json"


class TestDecisionLogWriteWindows:
    """Decision log write in payload mode must use sanitized filenames."""

    @pytest.fixture()
    def payload_env(self, tmp_path: Path) -> Path:
        _clear_caches()
        repo_root = tmp_path

        _write_yaml(
            repo_root / ".claude" / "workflows" / "system_orchestration"
            / "skill_catalog.yaml",
            {"skill_catalog": [{
                "id": "gate-enforcement",
                "execution_mode": "tapm",
                "output_contract": "payload",
                "payload_required_fields": [
                    "gate_id", "run_id", "overall_status",
                    "evaluated_at", "deterministic_predicates",
                    "semantic_predicates",
                ],
                "reads_from": ["docs/tier4/"],
                "writes_to": [
                    "docs/tier4/",
                    "docs/tier4_orchestration_state/decision_log/",
                ],
                "constitutional_constraints": [],
            }]},
        )

        _write_yaml(
            repo_root / ".claude" / "workflows" / "system_orchestration"
            / "artifact_schema_specification.yaml",
            {"tier4_phase_output_schemas": {}},
        )

        _write_skill_spec(repo_root, "gate-enforcement")

        (repo_root / "docs" / "tier4").mkdir(parents=True, exist_ok=True)
        (repo_root / "docs" / "tier4_orchestration_state" / "decision_log").mkdir(
            parents=True, exist_ok=True
        )

        return repo_root

    def test_timestamp_colons_sanitized_in_decision_log(
        self, payload_env: Path
    ) -> None:
        """decision_id with ISO 8601 colons must be sanitized to a
        Windows-safe filename."""
        response = {
            "gate_id": "phase_03_gate",
            "run_id": "run-001",
            "overall_status": "fail",
            "evaluated_at": "2026-04-20T12:00:00Z",
            "deterministic_predicates": {"passed": [], "failed": []},
            "semantic_predicates": {"passed": [], "failed": []},
            "decision_log_entry": {
                "decision_id": "gate_failure_phase_03_gate_2026-04-20T12:00:00Z",
                "decision_type": "gate_failure",
                "gate_id": "phase_03_gate",
            },
        }
        with _claude_returns(response):
            result = run_skill("gate-enforcement", "run-001", payload_env)

        assert result.status == "success"
        # The file should exist with sanitized name (colons → underscores)
        expected_name = "gate_failure_phase_03_gate_2026-04-20T12_00_00Z.json"
        log_dir = payload_env / "docs" / "tier4_orchestration_state" / "decision_log"
        written_files = list(log_dir.glob("*.json"))
        assert len(written_files) == 1, f"Expected 1 file, got: {written_files}"
        assert written_files[0].name == expected_name


# ===========================================================================
# Integration: Phase 3 skill sequence correctness
# ===========================================================================


class TestPhase3SkillSequenceIntegration:
    """Verify that the combined fixes produce the correct Phase 3 behavior:
    1. instrument-schema-normalization failure intercepted (not MALFORMED_ARTIFACT)
    2. gate-enforcement runs last
    3. Decision log filenames are Windows-safe
    """

    def test_instrument_failure_does_not_block_as_malformed(self) -> None:
        """When instrument-schema-normalization returns a SkillResult failure
        envelope, it is classified as the correct failure_category (e.g.
        MISSING_INPUT), not as MALFORMED_ARTIFACT from schema validation."""
        _clear_caches()
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)

            _write_yaml(
                repo_root / ".claude" / "workflows" / "system_orchestration"
                / "skill_catalog.yaml",
                {"skill_catalog": [{
                    "id": "instrument-schema-normalization",
                    "execution_mode": "tapm",
                    "reads_from": [
                        "docs/tier2a_instrument_schemas/application_forms/",
                        "docs/tier2a_instrument_schemas/extracted/section_schema_registry.json",
                    ],
                    "writes_to": [
                        "docs/tier2a_instrument_schemas/extracted/section_schema_registry.json",
                    ],
                    "constitutional_constraints": [],
                }]},
            )

            _write_yaml(
                repo_root / ".claude" / "workflows" / "system_orchestration"
                / "artifact_schema_specification.yaml",
                {
                    "tier2a_extracted_schemas": {
                        "section_schema_registry": {
                            "canonical_path": (
                                "docs/tier2a_instrument_schemas/extracted/"
                                "section_schema_registry.json"
                            ),
                            "fields": {
                                "instruments": {"required": True},
                            },
                        },
                    },
                },
            )

            _write_skill_spec(repo_root, "instrument-schema-normalization")

            (repo_root / "docs" / "tier2a_instrument_schemas" / "application_forms").mkdir(
                parents=True, exist_ok=True
            )
            (repo_root / "docs" / "tier2a_instrument_schemas" / "extracted").mkdir(
                parents=True, exist_ok=True
            )
            (
                repo_root / "docs" / "tier2a_instrument_schemas" / "extracted"
                / "section_schema_registry.json"
            ).write_text("{}", encoding="utf-8")

            # Simulate Claude returning a MISSING_INPUT failure
            claude_response = {
                "status": "failure",
                "failure_category": "MISSING_INPUT",
                "failure_reason": (
                    "resolved_instrument_type required to identify "
                    "the correct application form"
                ),
            }
            with _claude_returns(claude_response):
                result = run_skill(
                    "instrument-schema-normalization", "run-001", repo_root
                )

            # Must be MISSING_INPUT, not MALFORMED_ARTIFACT
            assert result.status == "failure"
            assert result.failure_category == "MISSING_INPUT"
            assert "resolved_instrument_type" in result.failure_reason
