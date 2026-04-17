"""
Tests for contextual descriptor handling in the skill runtime.

Coverage:
  1. Contextual descriptor skipped by _validate_skill_inputs and _resolve_inputs
  2. Real paths unchanged — continue to fail on true missing inputs
  3. Mixed reads_from list — only real paths validated from disk
  4. decision-log-update compatibility — no longer blocked by path validation
  5. No regression for TAPM and cli-prompt path-based skills
  6. _is_contextual_descriptor predicate correctness
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from runner.skill_runtime import (
    _is_contextual_descriptor,
    _resolve_inputs,
    _validate_skill_inputs,
    run_skill,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TRANSPORT_TARGET = "runner.skill_runtime.invoke_claude_text"


def _write_skill_catalog(repo_root: Path, entries: list[dict]) -> None:
    """Write a synthetic skill_catalog.yaml."""
    catalog_dir = repo_root / ".claude" / "workflows" / "system_orchestration"
    catalog_dir.mkdir(parents=True, exist_ok=True)
    catalog_path = catalog_dir / "skill_catalog.yaml"
    catalog_path.write_text(
        yaml.dump({"skill_catalog": entries}), encoding="utf-8"
    )


def _write_artifact_schema(repo_root: Path) -> None:
    """Write a minimal artifact_schema_specification.yaml."""
    schema_dir = repo_root / ".claude" / "workflows" / "system_orchestration"
    schema_dir.mkdir(parents=True, exist_ok=True)
    schema_path = schema_dir / "artifact_schema_specification.yaml"
    schema_path.write_text(
        yaml.dump({
            "tier4_phase_output_schemas": {},
            "tier5_deliverable_schemas": {},
        }),
        encoding="utf-8",
    )


def _write_skill_spec(repo_root: Path, skill_id: str, content: str = "") -> None:
    """Write a minimal skill .md spec file."""
    spec_dir = repo_root / ".claude" / "skills"
    spec_dir.mkdir(parents=True, exist_ok=True)
    spec_path = spec_dir / f"{skill_id}.md"
    spec_path.write_text(content or f"# {skill_id}\nTest skill spec.", encoding="utf-8")


@pytest.fixture()
def clean_caches():
    """Clear skill runtime module caches before each test."""
    import runner.skill_runtime as _sr
    _sr._catalog_cache.clear()
    _sr._schema_spec_cache.clear()
    yield
    _sr._catalog_cache.clear()
    _sr._schema_spec_cache.clear()


# ===========================================================================
# 1. _is_contextual_descriptor predicate
# ===========================================================================


class TestIsContextualDescriptor:
    """Test the recognition predicate for contextual vs. path entries."""

    def test_prose_descriptor_detected(self):
        assert _is_contextual_descriptor(
            "Any phase context requiring durable recording"
        ) is True

    def test_prose_with_multiple_spaces(self):
        assert _is_contextual_descriptor(
            "Agent in-context decision state"
        ) is True

    def test_real_file_path(self):
        assert _is_contextual_descriptor(
            "docs/tier3_project_instantiation/project_brief/"
        ) is False

    def test_real_json_path(self):
        assert _is_contextual_descriptor(
            "docs/tier2b_topic_and_call_sources/extracted/expected_outcomes.json"
        ) is False

    def test_bare_filename_no_space(self):
        """Bare filenames like CLAUDE.md are real paths (no spaces)."""
        assert _is_contextual_descriptor("CLAUDE.md") is False

    def test_dotted_path_no_space(self):
        assert _is_contextual_descriptor(
            ".claude/workflows/system_orchestration/skill_catalog.yaml"
        ) is False


# ===========================================================================
# 2. Contextual descriptor skipped by _validate_skill_inputs
# ===========================================================================


class TestValidateSkipsContextualDescriptor:
    """_validate_skill_inputs must not produce errors for contextual descriptors."""

    def test_contextual_only_reads_from_no_errors(self, tmp_path: Path):
        """A skill with only a contextual reads_from should pass validation."""
        errors = _validate_skill_inputs(
            "decision-log-update",
            ["Any phase context requiring durable recording"],
            tmp_path,
            {},  # no resolved inputs
        )
        assert errors == []

    def test_real_missing_path_still_fails(self, tmp_path: Path):
        """Real missing paths must still produce validation errors."""
        errors = _validate_skill_inputs(
            "test-skill",
            ["docs/tier3/missing.json"],
            tmp_path,
            {},
        )
        assert len(errors) == 1
        assert "does not exist" in errors[0]

    def test_mixed_list_only_real_paths_validated(self, tmp_path: Path):
        """In a mixed list, contextual descriptors are skipped; real paths validated."""
        # Create the real file so it passes
        real_path = "docs/tier3/input.json"
        abs_real = tmp_path / real_path
        abs_real.parent.mkdir(parents=True, exist_ok=True)
        abs_real.write_text('{"data": "test"}', encoding="utf-8")

        reads_from = [
            "Any phase context requiring durable recording",
            real_path,
        ]
        resolved = {real_path: {"data": "test"}}

        errors = _validate_skill_inputs(
            "test-skill",
            reads_from,
            tmp_path,
            resolved,
        )
        assert errors == []

    def test_mixed_list_real_missing_path_fails(self, tmp_path: Path):
        """Mixed list: contextual descriptor is fine, but missing real path fails."""
        reads_from = [
            "Any phase context requiring durable recording",
            "docs/tier3/nonexistent.json",
        ]

        errors = _validate_skill_inputs(
            "test-skill",
            reads_from,
            tmp_path,
            {},
        )
        assert len(errors) == 1
        assert "nonexistent.json" in errors[0]
        # Contextual descriptor must NOT appear in errors
        assert "Any phase context" not in errors[0]


# ===========================================================================
# 3. Contextual descriptor skipped by _resolve_inputs
# ===========================================================================


class TestResolveSkipsContextualDescriptor:
    """_resolve_inputs must not attempt to read contextual descriptors from disk."""

    def test_contextual_descriptor_not_in_resolved(self, tmp_path: Path):
        """Contextual descriptors should not appear as keys in resolved inputs."""
        resolved = _resolve_inputs(
            ["Any phase context requiring durable recording"],
            tmp_path,
            {},
        )
        assert "Any phase context requiring durable recording" not in resolved

    def test_real_path_still_resolved(self, tmp_path: Path):
        """Real paths continue to be resolved from disk."""
        real_path = "docs/tier3/input.json"
        abs_real = tmp_path / real_path
        abs_real.parent.mkdir(parents=True, exist_ok=True)
        abs_real.write_text('{"data": "resolved"}', encoding="utf-8")

        resolved = _resolve_inputs([real_path], tmp_path, {})
        assert real_path in resolved
        assert resolved[real_path] == {"data": "resolved"}

    def test_mixed_list_only_real_resolved(self, tmp_path: Path):
        """In a mixed list, only the real path is resolved."""
        real_path = "docs/tier3/input.json"
        abs_real = tmp_path / real_path
        abs_real.parent.mkdir(parents=True, exist_ok=True)
        abs_real.write_text('{"key": "val"}', encoding="utf-8")

        resolved = _resolve_inputs(
            [
                "Any phase context requiring durable recording",
                real_path,
            ],
            tmp_path,
            {},
        )
        assert real_path in resolved
        assert "Any phase context requiring durable recording" not in resolved


# ===========================================================================
# 4. decision-log-update compatibility via run_skill
# ===========================================================================


class TestDecisionLogUpdateCompatibility:
    """decision-log-update must not fail at path validation due to its contextual reads_from."""

    def test_no_path_validation_failure(
        self, tmp_path: Path, clean_caches
    ) -> None:
        """run_skill for decision-log-update must not fail with
        'Required input does not exist: Any phase context...'"""
        # Set up catalog with decision-log-update-like entry
        _write_skill_catalog(tmp_path, [
            {
                "id": "decision-log-update",
                "reads_from": [
                    "Any phase context requiring durable recording",
                ],
                "writes_to": [
                    "docs/tier4_orchestration_state/decision_log/",
                ],
                "constitutional_constraints": [],
            },
        ])
        _write_artifact_schema(tmp_path)
        _write_skill_spec(tmp_path, "decision-log-update")

        # Create the decision_log output directory
        (tmp_path / "docs" / "tier4_orchestration_state" / "decision_log").mkdir(
            parents=True, exist_ok=True
        )

        # Mock Claude to return a valid decision log entry
        response = {
            "decision_id": "scope_check_test_2026-04-17T00-00-00Z",
            "decision_type": "scope_check",
            "invoking_agent": "test",
            "phase_context": "phase_02",
            "decision_description": "Test decision",
            "alternatives_considered": [],
            "tier_authority_applied": "CLAUDE.md §9.4",
            "rationale": "Testing",
            "resolution_status": "resolved",
            "timestamp": "2026-04-17T00:00:00Z",
        }
        with patch(_TRANSPORT_TARGET, return_value=json.dumps(response)):
            result = run_skill("decision-log-update", "run-001", tmp_path)

        # Must NOT fail with "Required input does not exist"
        if result.status == "failure" and result.failure_reason:
            assert "Required input does not exist" not in result.failure_reason
            assert "Any phase context" not in result.failure_reason


# ===========================================================================
# 5. Real path-based skills unchanged (no regression)
# ===========================================================================


class TestRealPathSkillsUnchanged:
    """Path-based skills must continue to fail on true missing inputs."""

    def test_missing_real_path_still_fails_at_run_skill(
        self, tmp_path: Path, clean_caches
    ) -> None:
        """A skill with a real missing path fails with MISSING_INPUT."""
        _write_skill_catalog(tmp_path, [
            {
                "id": "test-path-skill",
                "reads_from": ["docs/tier3/nonexistent.json"],
                "writes_to": ["docs/tier4/output.json"],
                "constitutional_constraints": [],
            },
        ])
        _write_artifact_schema(tmp_path)
        _write_skill_spec(tmp_path, "test-path-skill")

        with patch(_TRANSPORT_TARGET) as mock_transport:
            result = run_skill("test-path-skill", "run-001", tmp_path)

        assert result.status == "failure"
        assert result.failure_category == "MISSING_INPUT"
        assert "does not exist" in result.failure_reason
        mock_transport.assert_not_called()

    def test_existing_real_path_passes_validation(
        self, tmp_path: Path, clean_caches
    ) -> None:
        """A skill with existing real inputs passes validation and invokes Claude."""
        _write_skill_catalog(tmp_path, [
            {
                "id": "test-real-skill",
                "reads_from": ["docs/tier3/input.json"],
                "writes_to": ["docs/tier4/output.json"],
                "constitutional_constraints": [],
            },
        ])
        _write_artifact_schema(tmp_path)
        _write_skill_spec(tmp_path, "test-real-skill")

        # Create the real input
        input_path = tmp_path / "docs" / "tier3" / "input.json"
        input_path.parent.mkdir(parents=True, exist_ok=True)
        input_path.write_text('{"data": "present"}', encoding="utf-8")

        response = {"result": "ok"}
        with patch(_TRANSPORT_TARGET, return_value=json.dumps(response)):
            result = run_skill("test-real-skill", "run-001", tmp_path)

        # Should not fail at input validation (may fail at output
        # validation since our response is minimal — that's fine)
        if result.status == "failure":
            assert "does not exist" not in (result.failure_reason or "")
