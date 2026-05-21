"""
Tests for evaluator-criteria-review TAPM conversion (CC-07).

Verifies:
  1. Manifest/runtime mode: evaluator-criteria-review is configured as TAPM.
  2. Prompt-size regression: TAPM prompt does not inline full section artifacts.
  3. Skill spec invariants: bounded review rules present in spec.
  4. Anti-regression: verbose appendices removed from spec.
  5. Output schema fixture: mock review_packet conforms to orch.tier5.review_packet.v1.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from runner.skill_runtime import (
    _assemble_tapm_prompt,
    _get_skill_entry,
    _load_skill_catalog,
    _validate_skill_output,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = REPO_ROOT / ".claude" / "skills"
SKILL_CATALOG_PATH = (
    REPO_ROOT / ".claude" / "workflows" / "system_orchestration"
    / "skill_catalog.yaml"
)


def _read_skill(name: str) -> str:
    path = SKILLS_DIR / name
    assert path.is_file(), f"Skill spec not found: {path}"
    return path.read_text(encoding="utf-8")


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Synthetic environment for TAPM prompt tests
# ---------------------------------------------------------------------------


def _write_skill_catalog(repo_root: Path, entries: list[dict]) -> None:
    catalog_path = (
        repo_root / ".claude" / "workflows" / "system_orchestration"
        / "skill_catalog.yaml"
    )
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.write_text(
        yaml.dump({"skill_catalog": entries}), encoding="utf-8"
    )


def _write_artifact_schema(repo_root: Path) -> None:
    spec_path = (
        repo_root / ".claude" / "workflows" / "system_orchestration"
        / "artifact_schema_specification.yaml"
    )
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    schemas = {
        "tier5_deliverable_schemas": {
            "review_packet": {
                "canonical_path": (
                    "docs/tier5_deliverables/review_packets/review_packet.json"
                ),
                "schema_id_value": "orch.tier5.review_packet.v1",
                "fields": {
                    "schema_id": {"required": True},
                    "run_id": {"required": True},
                    "findings": {"required": True},
                    "revision_actions": {"required": True},
                },
            },
        },
    }
    spec_path.write_text(yaml.dump(schemas), encoding="utf-8")


def _make_tapm_env(tmp_path: Path) -> Path:
    """Create a synthetic environment for TAPM prompt assembly tests.

    Creates:
      - artifact schema specification
      - large section artifacts on disk (to verify they are NOT inlined)
      - skill catalog entry for evaluator-criteria-review
    """
    repo_root = tmp_path

    _write_artifact_schema(repo_root)

    # Large section artifacts — distinctive markers to detect inlining
    sections_dir = repo_root / "docs" / "tier5_deliverables" / "proposal_sections"
    sections_dir.mkdir(parents=True, exist_ok=True)
    for name in ("excellence_section.json", "impact_section.json",
                 "implementation_section.json"):
        # ~20KB per section — same order as the real sections
        big_content = "MARKER_SECTION_CONTENT_SHOULD_NOT_BE_INLINED " * 2000
        _write_json(sections_dir / name, {
            "schema_id": f"orch.tier5.{name.replace('.json', '')}.v1",
            "run_id": "test-run",
            "criterion": name.split("_")[0].capitalize(),
            "sub_sections": [{"sub_section_id": "B.1.1", "title": "Test",
                              "content": big_content, "word_count": 2000}],
            "validation_status": {"overall_status": "confirmed"},
            "traceability_footer": {"primary_sources": []},
        })

    # Assembled draft
    assembled_dir = repo_root / "docs" / "tier5_deliverables" / "assembled_drafts"
    assembled_dir.mkdir(parents=True, exist_ok=True)
    _write_json(assembled_dir / "part_b_assembled_draft.json", {
        "schema_id": "orch.tier5.part_b_assembled_draft.v1",
        "run_id": "test-run",
        "sections": [
            {"section_id": "excellence",
             "artifact_path": "docs/tier5_deliverables/proposal_sections/excellence_section.json"},
            {"section_id": "impact",
             "artifact_path": "docs/tier5_deliverables/proposal_sections/impact_section.json"},
            {"section_id": "implementation",
             "artifact_path": "docs/tier5_deliverables/proposal_sections/implementation_section.json"},
        ],
    })

    # Call analysis summary
    phase1_dir = (
        repo_root / "docs" / "tier4_orchestration_state"
        / "phase_outputs" / "phase1_call_analysis"
    )
    phase1_dir.mkdir(parents=True, exist_ok=True)
    _write_json(phase1_dir / "call_analysis_summary.json", {
        "schema_id": "orch.phase1.call_analysis_summary.v1",
        "run_id": "test-run",
        "evaluation_matrix": [
            {"criterion_id": "EXC", "criterion_name": "Excellence",
             "weight": 50},
            {"criterion_id": "IMP", "criterion_name": "Impact",
             "weight": 30},
            {"criterion_id": "IMPL", "criterion_name": "Implementation",
             "weight": 20},
        ],
    })

    # Evaluation form
    eval_dir = repo_root / "docs" / "tier2a_instrument_schemas" / "evaluation_forms"
    eval_dir.mkdir(parents=True, exist_ok=True)
    (eval_dir / "ria_evaluation_form.txt").write_text(
        "RIA Evaluation Form\nExcellence\nImpact\nImplementation\n",
        encoding="utf-8",
    )

    # Skill catalog with evaluator-criteria-review as TAPM
    _write_skill_catalog(repo_root, [{
        "id": "evaluator-criteria-review",
        "execution_mode": "tapm",
        "reads_from": [
            "docs/tier2a_instrument_schemas/evaluation_forms/",
            "docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/",
            "docs/tier5_deliverables/assembled_drafts/part_b_assembled_draft.json",
            "docs/tier5_deliverables/proposal_sections/",
        ],
        "writes_to": [
            "docs/tier5_deliverables/review_packets/",
        ],
        "constitutional_constraints": [
            "Evaluation must apply the active instrument evaluation criteria only",
            "Must not evaluate against grant agreement annex requirements",
            "Weakness severity (critical/major/minor) must be assigned to each finding",
        ],
    }])

    # Skill spec
    skill_spec_dir = repo_root / ".claude" / "skills"
    skill_spec_dir.mkdir(parents=True, exist_ok=True)
    # Copy the real spec
    real_spec = _read_skill("evaluator-criteria-review.md")
    (skill_spec_dir / "evaluator-criteria-review.md").write_text(
        real_spec, encoding="utf-8"
    )

    return repo_root


# ===========================================================================
# 1. MANIFEST/RUNTIME MODE TEST
# ===========================================================================


class TestEvaluatorTAPMMode:
    """Assert evaluator-criteria-review is configured as TAPM in the real catalog."""

    def test_execution_mode_is_tapm(self) -> None:
        """The skill catalog must declare execution_mode: 'tapm'."""
        # Clear cache to ensure fresh read
        from runner.skill_runtime import _catalog_cache
        _catalog_cache.pop(str(REPO_ROOT), None)

        entry = _get_skill_entry("evaluator-criteria-review", REPO_ROOT)
        assert entry.get("execution_mode") == "tapm", (
            f"evaluator-criteria-review execution_mode should be 'tapm', "
            f"got {entry.get('execution_mode')!r}"
        )

    def test_reads_from_includes_required_paths(self) -> None:
        """reads_from must include assembled_drafts, evaluation_forms, etc."""
        from runner.skill_runtime import _catalog_cache
        _catalog_cache.pop(str(REPO_ROOT), None)

        entry = _get_skill_entry("evaluator-criteria-review", REPO_ROOT)
        reads_from = entry.get("reads_from", [])
        assert "docs/tier5_deliverables/assembled_drafts/part_b_assembled_draft.json" in reads_from
        assert "docs/tier2a_instrument_schemas/evaluation_forms/" in reads_from
        assert "docs/tier5_deliverables/proposal_sections/" in reads_from

    def test_writes_to_review_packets(self) -> None:
        """writes_to must target review_packets/."""
        from runner.skill_runtime import _catalog_cache
        _catalog_cache.pop(str(REPO_ROOT), None)

        entry = _get_skill_entry("evaluator-criteria-review", REPO_ROOT)
        writes_to = entry.get("writes_to", [])
        assert "docs/tier5_deliverables/review_packets/" in writes_to


# ===========================================================================
# 2. PROMPT-SIZE REGRESSION TEST
# ===========================================================================


class TestPromptSizeRegression:
    """Verify TAPM prompt does not inline full section artifact contents."""

    def test_tapm_prompt_does_not_contain_section_content(
        self, tmp_path: Path
    ) -> None:
        """The user prompt must NOT contain the distinctive section marker."""
        repo_root = _make_tapm_env(tmp_path)

        skill_spec = _read_skill("evaluator-criteria-review.md")

        _sys, user = _assemble_tapm_prompt(
            skill_spec=skill_spec,
            skill_id="evaluator-criteria-review",
            run_id="test-run-123",
            reads_from=[
                "docs/tier2a_instrument_schemas/evaluation_forms/",
                "docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/",
                "docs/tier5_deliverables/assembled_drafts/part_b_assembled_draft.json",
                "docs/tier5_deliverables/proposal_sections/",
            ],
            writes_to=["docs/tier5_deliverables/review_packets/"],
            constraints=[
                "Evaluation must apply the active instrument evaluation criteria only",
            ],
            repo_root=repo_root,
            node_id="n08e_evaluator_review",
        )

        # The marker from the large section artifacts must NOT be in the prompt
        assert "MARKER_SECTION_CONTENT_SHOULD_NOT_BE_INLINED" not in user, (
            "TAPM prompt must not inline section artifact content"
        )

    def test_tapm_prompt_contains_file_paths(
        self, tmp_path: Path
    ) -> None:
        """The user prompt must contain declared input file paths."""
        repo_root = _make_tapm_env(tmp_path)

        skill_spec = _read_skill("evaluator-criteria-review.md")

        _sys, user = _assemble_tapm_prompt(
            skill_spec=skill_spec,
            skill_id="evaluator-criteria-review",
            run_id="test-run-123",
            reads_from=[
                "docs/tier2a_instrument_schemas/evaluation_forms/",
                "docs/tier5_deliverables/assembled_drafts/part_b_assembled_draft.json",
                "docs/tier5_deliverables/proposal_sections/",
            ],
            writes_to=["docs/tier5_deliverables/review_packets/"],
            constraints=[],
            repo_root=repo_root,
        )

        # File paths must be present in the prompt
        assert "evaluation_forms" in user
        assert "part_b_assembled_draft.json" in user
        assert "proposal_sections" in user

    def test_tapm_prompt_size_below_threshold(
        self, tmp_path: Path
    ) -> None:
        """User prompt must be substantially below the prior 83,159 chars.

        Target: below 25,000 chars (skill spec + metadata + paths).
        """
        repo_root = _make_tapm_env(tmp_path)

        skill_spec = _read_skill("evaluator-criteria-review.md")

        _sys, user = _assemble_tapm_prompt(
            skill_spec=skill_spec,
            skill_id="evaluator-criteria-review",
            run_id="test-run-123",
            reads_from=[
                "docs/tier2a_instrument_schemas/evaluation_forms/",
                "docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/",
                "docs/tier5_deliverables/assembled_drafts/part_b_assembled_draft.json",
                "docs/tier5_deliverables/proposal_sections/",
            ],
            writes_to=["docs/tier5_deliverables/review_packets/"],
            constraints=[
                "Evaluation must apply the active instrument evaluation criteria only",
                "Must not evaluate against grant agreement annex requirements",
                "Weakness severity (critical/major/minor) must be assigned to each finding",
            ],
            repo_root=repo_root,
            node_id="n08e_evaluator_review",
        )

        total = len(_sys) + len(user)
        assert total < 25_000, (
            f"Combined prompt size {total} chars exceeds 25,000 char target. "
            f"Prior bloated prompt was 83,159 chars. System: {len(_sys)}, "
            f"User: {len(user)}"
        )


# ===========================================================================
# 3. SKILL SPEC INVARIANT TESTS
# ===========================================================================


class TestSkillSpecInvariants:
    """Assert evaluator-criteria-review.md contains required bounded review rules."""

    @pytest.fixture(autouse=True)
    def load_spec(self) -> None:
        self.text = _read_skill("evaluator-criteria-review.md")

    def test_contains_bounded_evaluator_review(self) -> None:
        assert "bounded evaluator review" in self.text.lower()

    def test_contains_maximum_12_findings(self) -> None:
        assert "maximum 12 findings total" in self.text.lower()

    def test_contains_maximum_4_per_criterion(self) -> None:
        assert "maximum 4" in self.text.lower()
        assert "per criterion" in self.text.lower()

    def test_contains_do_not_rerun_traceability(self) -> None:
        assert "do not re-run traceability" in self.text.lower()

    def test_contains_do_not_rerun_cross_section_consistency(self) -> None:
        assert "do not re-run cross-section consistency" in self.text.lower()

    def test_contains_active_evaluation_criteria_only(self) -> None:
        assert "active evaluation criteria only" in self.text.lower()

    def test_contains_severity(self) -> None:
        assert "severity" in self.text.lower()
        assert "critical" in self.text.lower()
        assert "major" in self.text.lower()
        assert "minor" in self.text.lower()

    def test_contains_tapm_input_boundary(self) -> None:
        assert "Read" in self.text
        assert "Glob" in self.text

    def test_schema_id_present(self) -> None:
        assert "orch.tier5.review_packet.v1" in self.text

    def test_no_grant_agreement_annex_evaluation(self) -> None:
        assert "grant agreement annex" in self.text.lower()
        assert "must not evaluate against" in self.text.lower() or \
               "do not" in self.text.lower()


# ===========================================================================
# 4. ANTI-REGRESSION TESTS
# ===========================================================================


class TestAntiRegression:
    """Assert verbose appendices have been removed from the skill spec."""

    @pytest.fixture(autouse=True)
    def load_spec(self) -> None:
        self.text = _read_skill("evaluator-criteria-review.md")

    def test_no_universal_failure_rules_section(self) -> None:
        """The verbose 'Universal Failure Rules' section should be removed."""
        assert "### Universal Failure Rules" not in self.text

    def test_no_long_schema_validation_section(self) -> None:
        """The verbose 'Schema Validation' analysis section should be removed."""
        assert "## Schema Validation" not in self.text
        assert "Step 8 implementation" not in self.text

    def test_no_constitutional_constraint_enforcement_section(self) -> None:
        """The verbose Constitutional Constraint Enforcement section should be removed."""
        assert "## Constitutional Constraint Enforcement" not in self.text
        assert "Step 6 implementation" not in self.text

    def test_no_verbose_failure_protocol_section(self) -> None:
        """The verbose per-category Failure Protocol appendix should be removed."""
        # The old spec had ### MISSING_INPUT, ### MALFORMED_ARTIFACT, etc.
        # as verbose multi-paragraph sections. New spec has a compact table.
        assert "### MISSING_INPUT" not in self.text
        assert "### MALFORMED_ARTIFACT" not in self.text
        assert "### CONSTRAINT_VIOLATION" not in self.text
        assert "### INCOMPLETE_OUTPUT" not in self.text
        assert "### CONSTITUTIONAL_HALT" not in self.text

    def test_spec_size_reduced(self) -> None:
        """Spec should be substantially smaller than the prior ~288 lines."""
        lines = self.text.strip().splitlines()
        assert len(lines) < 200, (
            f"Spec has {len(lines)} lines; expected < 200 after trimming "
            f"verbose appendices (prior spec was ~288 lines)"
        )

    def test_no_serialized_canonical_input_blocks(self) -> None:
        """Spec should not contain inline ```json blocks with serialized artifacts."""
        # The old cli-prompt mode would have inputs serialized into the prompt.
        # The TAPM spec should not contain such blocks (except the output example).
        json_blocks = self.text.count("```json")
        assert json_blocks <= 2, (
            f"Spec has {json_blocks} ```json blocks; TAPM spec should have "
            f"at most 1-2 (output example only)"
        )


# ===========================================================================
# 5. OUTPUT SCHEMA FIXTURE TEST
# ===========================================================================


class TestReviewPacketSchema:
    """Verify a mock review_packet conforms to orch.tier5.review_packet.v1."""

    def test_valid_review_packet_passes_validation(self) -> None:
        """A well-formed review_packet should pass validation."""
        review_packet = {
            "schema_id": "orch.tier5.review_packet.v1",
            "run_id": "test-run-abc",
            "findings": [
                {
                    "finding_id": "F-1",
                    "section_id": "excellence",
                    "criterion": "EXC",
                    "description": "Methodology lacks quantification",
                    "severity": "major",
                    "evidence": "The section states 'advanced methods'",
                    "recommendation": "Add specific methodology names",
                },
                {
                    "finding_id": "F-2",
                    "section_id": "impact",
                    "criterion": "IMP",
                    "description": "No KPIs defined for dissemination",
                    "severity": "minor",
                    "evidence": "Dissemination plan is qualitative only",
                    "recommendation": "Add measurable KPIs",
                },
            ],
            "revision_actions": [
                {
                    "action_id": "A-1",
                    "finding_id": "F-1",
                    "priority": 1,
                    "action_description": "Add methodology quantification",
                    "target_section": "excellence",
                    "severity": "major",
                },
                {
                    "action_id": "A-2",
                    "finding_id": "F-2",
                    "priority": 2,
                    "action_description": "Add dissemination KPIs",
                    "target_section": "impact",
                    "severity": "minor",
                },
            ],
        }

        errors = _validate_skill_output(
            response=review_packet,
            run_id="test-run-abc",
            expected_schema_id="orch.tier5.review_packet.v1",
            required_fields=["schema_id", "run_id", "findings", "revision_actions"],
        )
        assert errors == [], f"Validation errors: {errors}"

    def test_empty_findings_passes_validation(self) -> None:
        """A review_packet with empty findings/revision_actions is valid."""
        review_packet = {
            "schema_id": "orch.tier5.review_packet.v1",
            "run_id": "test-run-empty",
            "findings": [],
            "revision_actions": [],
        }

        errors = _validate_skill_output(
            response=review_packet,
            run_id="test-run-empty",
            expected_schema_id="orch.tier5.review_packet.v1",
            required_fields=["schema_id", "run_id", "findings", "revision_actions"],
        )
        assert errors == [], f"Validation errors: {errors}"

    def test_missing_run_id_fails(self) -> None:
        """A review_packet missing run_id should fail validation."""
        review_packet = {
            "schema_id": "orch.tier5.review_packet.v1",
            "findings": [],
            "revision_actions": [],
        }

        errors = _validate_skill_output(
            response=review_packet,
            run_id="test-run-missing",
            expected_schema_id="orch.tier5.review_packet.v1",
            required_fields=["schema_id", "run_id", "findings", "revision_actions"],
        )
        assert len(errors) > 0
        assert any("run_id" in e for e in errors)

    def test_wrong_schema_id_fails(self) -> None:
        """A review_packet with wrong schema_id should fail validation."""
        review_packet = {
            "schema_id": "wrong_schema",
            "run_id": "test-run-wrong",
            "findings": [],
            "revision_actions": [],
        }

        errors = _validate_skill_output(
            response=review_packet,
            run_id="test-run-wrong",
            expected_schema_id="orch.tier5.review_packet.v1",
            required_fields=["schema_id", "run_id", "findings", "revision_actions"],
        )
        assert len(errors) > 0
        assert any("schema_id" in e for e in errors)

    def test_artifact_status_present_fails(self) -> None:
        """artifact_status must be absent at write time."""
        review_packet = {
            "schema_id": "orch.tier5.review_packet.v1",
            "run_id": "test-run-status",
            "findings": [],
            "revision_actions": [],
            "artifact_status": "valid",
        }

        errors = _validate_skill_output(
            response=review_packet,
            run_id="test-run-status",
            expected_schema_id="orch.tier5.review_packet.v1",
            required_fields=["schema_id", "run_id", "findings", "revision_actions"],
        )
        assert len(errors) > 0
        assert any("artifact_status" in e for e in errors)

    def test_findings_bounded_by_spec(self) -> None:
        """Verify the spec enforces max 12 findings (spec-level, not runtime)."""
        text = _read_skill("evaluator-criteria-review.md")
        assert "maximum 12 findings total" in text.lower()

    def test_severity_enum_enforced_in_spec(self) -> None:
        """Verify the spec requires severity for every finding."""
        text = _read_skill("evaluator-criteria-review.md")
        assert "severity required for every finding" in text.lower()
