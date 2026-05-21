"""
Tests for Phase 8 drafting skill spec hygiene.

Verifies that drafting skill specs do not contain bloated patterns (CCR rules,
Self-Check sections, revise-before-output loops) and respect size limits.
Also confirms gate_10d cross-section consistency still functions.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

SKILLS_DIR = Path(__file__).resolve().parents[2] / ".claude" / "skills"

DRAFTING_SKILLS = [
    "excellence-section-drafting.md",
    "impact-section-drafting.md",
    "implementation-section-drafting.md",
]

SIZE_LIMITS = {
    "excellence-section-drafting.md": 8_000,
    "impact-section-drafting.md": 8_000,
    "implementation-section-drafting.md": 10_000,
}


def _read_skill(name: str) -> str:
    path = SKILLS_DIR / name
    assert path.is_file(), f"Skill spec not found: {path}"
    return path.read_text(encoding="utf-8")


# ===========================================================================
# Banned patterns
# ===========================================================================


class TestNoBannedPatterns:
    """No drafting skill may contain bloated CCR/Self-Check/audit patterns."""

    @pytest.mark.parametrize("skill", DRAFTING_SKILLS)
    def test_no_self_check(self, skill: str) -> None:
        text = _read_skill(skill)
        assert "Self-Check" not in text, (
            f"{skill} contains 'Self-Check' — remove all self-check sections"
        )

    @pytest.mark.parametrize("skill", DRAFTING_SKILLS)
    def test_no_ccr_references(self, skill: str) -> None:
        text = _read_skill(skill)
        assert "CCR-" not in text, (
            f"{skill} contains 'CCR-' — remove all CCR rule references"
        )

    @pytest.mark.parametrize("skill", DRAFTING_SKILLS)
    def test_no_revise_before_output(self, skill: str) -> None:
        text = _read_skill(skill).lower()
        assert "revise before output" not in text, (
            f"{skill} contains 'revise before output' — remove audit loops"
        )


# ===========================================================================
# Size limits
# ===========================================================================


class TestSizeLimits:
    """Each drafting skill must be below its target character count."""

    @pytest.mark.parametrize("skill", DRAFTING_SKILLS)
    def test_under_size_limit(self, skill: str) -> None:
        text = _read_skill(skill)
        limit = SIZE_LIMITS[skill]
        assert len(text) <= limit, (
            f"{skill} is {len(text)} chars, limit is {limit}"
        )


# ===========================================================================
# gate_10d cross-section consistency still works
# ===========================================================================


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _make_assembled_draft(consistency_log: list[dict]) -> dict:
    return {
        "schema_id": "orch.tier5.part_b_assembled_draft.v1",
        "sections": [
            {"section_id": "s1", "criterion": "Excellence", "order": 1,
             "artifact_path": "a.json"},
            {"section_id": "s2", "criterion": "Impact", "order": 2,
             "artifact_path": "b.json"},
            {"section_id": "s3", "criterion": "Implementation", "order": 3,
             "artifact_path": "c.json"},
        ],
        "consistency_log": consistency_log,
    }


class TestGate10dStillWorks:
    """gate_10d cross-section consistency predicate still functions."""

    def test_consistent_draft_passes(self, tmp_path: Path) -> None:
        from runner.predicates.criterion_predicates import cross_section_consistency

        draft = _make_assembled_draft([
            {"check_id": "CC-01", "status": "consistent", "description": "ok"},
            {"check_id": "CC-02", "status": "consistent", "description": "ok"},
            {"check_id": "CC-03", "status": "consistent", "description": "ok"},
            {"check_id": "CC-04", "status": "consistent", "description": "ok"},
        ])
        _write_json(tmp_path / "assembled.json", draft)
        result = cross_section_consistency(
            "assembled.json", "sections/", "tier3/", repo_root=tmp_path,
        )
        assert result.passed

    def test_inconsistency_flagged_fails(self, tmp_path: Path) -> None:
        from runner.predicates.criterion_predicates import cross_section_consistency

        draft = _make_assembled_draft([
            {"check_id": "CC-03", "status": "inconsistency_flagged",
             "description": "partner name mismatch"},
        ])
        _write_json(tmp_path / "assembled.json", draft)
        result = cross_section_consistency(
            "assembled.json", "sections/", "tier3/", repo_root=tmp_path,
        )
        assert not result.passed
        assert "CC-03" in result.details.get("flagged_checks", [])

    def test_multiple_flags_all_reported(self, tmp_path: Path) -> None:
        from runner.predicates.criterion_predicates import cross_section_consistency

        draft = _make_assembled_draft([
            {"check_id": "CC-03", "status": "inconsistency_flagged",
             "description": "partner name mismatch"},
            {"check_id": "CC-04", "status": "inconsistency_flagged",
             "description": "deliverable identity conflict"},
        ])
        _write_json(tmp_path / "assembled.json", draft)
        result = cross_section_consistency(
            "assembled.json", "sections/", "tier3/", repo_root=tmp_path,
        )
        assert not result.passed
        assert result.details["flagged_count"] == 2
        assert "CC-03" in result.details["flagged_checks"]
        assert "CC-04" in result.details["flagged_checks"]
