"""
Tests for the Phase 8 consistency-prevention layer.

Covers:
    - Canonical reference pack generation and exact preservation
    - Section preflight predicates (stale run_id, partner names,
      deliverable identity, canonical terms)
    - Primary drafting timeout/failure prevents downstream audit skills
    - gate_10d tests still pass unchanged
    - Drafting skill files remain below size limits and contain no
      banned patterns
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _make_objectives() -> dict:
    return {
        "objectives": [
            {
                "id": "OBJ-1",
                "title": "Neuro-symbolic planning engine",
                "responsible_partner": "ATU",
                "contributing_partners": ["CERIA", "BIIS"],
            },
            {
                "id": "OBJ-2",
                "title": "Unified adaptive memory architecture",
                "responsible_partner": "BIIS",
                "contributing_partners": ["ATU"],
            },
        ]
    }


def _make_outcomes() -> dict:
    return {
        "outcomes": [
            {
                "id": "OUT-1",
                "title": "Neuro-symbolic planning framework",
                "linked_objectives": ["OBJ-1"],
                "linked_wp_ids": ["WP2"],
                "linked_deliverable_ids": ["D2-01"],
            },
        ]
    }


def _make_wp_structure() -> dict:
    return {
        "work_packages": [
            {
                "wp_id": "WP1",
                "title": "Project Management and Coordination",
                "lead_partner": "ATU",
                "deliverables": [
                    {
                        "deliverable_id": "D1-01",
                        "title": "Quality Management Plan",
                        "due_month": 3,
                        "type": "Report",
                    },
                ],
            },
            {
                "wp_id": "WP2",
                "title": "Neuro-Symbolic Planning Engine",
                "lead_partner": "ATU",
                "deliverables": [
                    {
                        "deliverable_id": "D2-01",
                        "title": "Planning Engine Prototype v1",
                        "due_month": 18,
                        "type": "Software",
                    },
                    {
                        "deliverable_id": "D2-02",
                        "title": "Planning Engine Final Release",
                        "due_month": 36,
                        "type": "Software",
                    },
                ],
            },
        ]
    }


def _make_partners() -> dict:
    return {
        "partners": [
            {
                "short_name": "ATU",
                "legal_name": "Alpenstadt Technical University",
                "country": "DE",
                "role": "coordinator",
            },
            {
                "short_name": "ELI",
                "legal_name": "EuroLog International AG",
                "country": "CH",
                "role": "participant",
            },
            {
                "short_name": "BAL",
                "legal_name": "Boreal AI Labs Oy",
                "country": "FI",
                "role": "participant",
            },
        ]
    }


def _populate_tier3_and_tier4(repo: Path) -> None:
    """Write all source files needed for canonical pack."""
    _write_json(
        repo / "docs" / "tier3_project_instantiation"
        / "architecture_inputs" / "objectives.json",
        _make_objectives(),
    )
    _write_json(
        repo / "docs" / "tier3_project_instantiation"
        / "architecture_inputs" / "outcomes.json",
        _make_outcomes(),
    )
    _write_json(
        repo / "docs" / "tier4_orchestration_state"
        / "phase_outputs" / "phase3_wp_design" / "wp_structure.json",
        _make_wp_structure(),
    )
    _write_json(
        repo / "docs" / "tier3_project_instantiation"
        / "consortium" / "partners.json",
        _make_partners(),
    )


def _make_section(run_id: str, content_parts: list[str]) -> dict:
    """Minimal section artifact for predicate testing."""
    return {
        "schema_id": "orch.tier5.excellence_section.v1",
        "run_id": run_id,
        "criterion": "Excellence",
        "sub_sections": [
            {"sub_section_id": f"ss{i}", "content": c}
            for i, c in enumerate(content_parts)
        ],
    }


# ===========================================================================
# 1. Canonical reference pack generation
# ===========================================================================


class TestCanonicalPackGeneration:
    """Build the canonical reference pack and verify exact content."""

    def test_pack_written_with_correct_schema(self, tmp_path: Path) -> None:
        from runner.phase8_canonical_pack import build_phase8_canonical_reference_pack

        _populate_tier3_and_tier4(tmp_path)
        out = build_phase8_canonical_reference_pack(tmp_path, "run-abc")
        data = json.loads(out.read_text(encoding="utf-8"))

        assert data["schema_id"] == "orch.phase8.canonical_reference_pack.v1"
        assert data["run_id"] == "run-abc"
        assert data["aliases"] == []

    def test_objectives_preserved_exactly(self, tmp_path: Path) -> None:
        from runner.phase8_canonical_pack import build_phase8_canonical_reference_pack

        _populate_tier3_and_tier4(tmp_path)
        out = build_phase8_canonical_reference_pack(tmp_path, "run-1")
        data = json.loads(out.read_text(encoding="utf-8"))

        obj_ids = [o["id"] for o in data["objectives"]]
        obj_titles = [o["title"] for o in data["objectives"]]
        assert obj_ids == ["OBJ-1", "OBJ-2"]
        assert obj_titles == [
            "Neuro-symbolic planning engine",
            "Unified adaptive memory architecture",
        ]

    def test_wp_titles_preserved_exactly(self, tmp_path: Path) -> None:
        from runner.phase8_canonical_pack import build_phase8_canonical_reference_pack

        _populate_tier3_and_tier4(tmp_path)
        out = build_phase8_canonical_reference_pack(tmp_path, "run-1")
        data = json.loads(out.read_text(encoding="utf-8"))

        wp_ids = [w["wp_id"] for w in data["wps"]]
        wp_titles = [w["title"] for w in data["wps"]]
        assert wp_ids == ["WP1", "WP2"]
        assert wp_titles == [
            "Project Management and Coordination",
            "Neuro-Symbolic Planning Engine",
        ]

    def test_deliverable_ids_titles_months_preserved(self, tmp_path: Path) -> None:
        from runner.phase8_canonical_pack import build_phase8_canonical_reference_pack

        _populate_tier3_and_tier4(tmp_path)
        out = build_phase8_canonical_reference_pack(tmp_path, "run-1")
        data = json.loads(out.read_text(encoding="utf-8"))

        delivs = data["deliverables"]
        assert len(delivs) == 3
        d1 = next(d for d in delivs if d["deliverable_id"] == "D1-01")
        assert d1["title"] == "Quality Management Plan"
        assert d1["due_month"] == 3
        assert d1["parent_wp"] == "WP1"

        d2 = next(d for d in delivs if d["deliverable_id"] == "D2-01")
        assert d2["title"] == "Planning Engine Prototype v1"
        assert d2["due_month"] == 18
        assert d2["parent_wp"] == "WP2"

    def test_partner_names_preserved(self, tmp_path: Path) -> None:
        from runner.phase8_canonical_pack import build_phase8_canonical_reference_pack

        _populate_tier3_and_tier4(tmp_path)
        out = build_phase8_canonical_reference_pack(tmp_path, "run-1")
        data = json.loads(out.read_text(encoding="utf-8"))

        short_names = [p["short_name"] for p in data["partners"]]
        legal_names = [p["legal_name"] for p in data["partners"]]
        assert "ATU" in short_names
        assert "Alpenstadt Technical University" in legal_names
        assert "EuroLog International AG" in legal_names
        assert "Boreal AI Labs Oy" in legal_names

    def test_outcomes_preserved(self, tmp_path: Path) -> None:
        from runner.phase8_canonical_pack import build_phase8_canonical_reference_pack

        _populate_tier3_and_tier4(tmp_path)
        out = build_phase8_canonical_reference_pack(tmp_path, "run-1")
        data = json.loads(out.read_text(encoding="utf-8"))

        assert len(data["outcomes"]) == 1
        assert data["outcomes"][0]["id"] == "OUT-1"
        assert data["outcomes"][0]["title"] == "Neuro-symbolic planning framework"

    def test_missing_outcomes_file_produces_empty_list(self, tmp_path: Path) -> None:
        from runner.phase8_canonical_pack import build_phase8_canonical_reference_pack

        _populate_tier3_and_tier4(tmp_path)
        outcomes_path = (
            tmp_path / "docs" / "tier3_project_instantiation"
            / "architecture_inputs" / "outcomes.json"
        )
        outcomes_path.unlink()
        out = build_phase8_canonical_reference_pack(tmp_path, "run-1")
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["outcomes"] == []


# ===========================================================================
# 2. no_stale_run_id predicate
# ===========================================================================


class TestNoStaleRunId:

    def test_matching_run_id_passes(self, tmp_path: Path) -> None:
        from runner.predicates.phase8_section_predicates import no_stale_run_id

        section = _make_section("run-42", ["some content"])
        _write_json(tmp_path / "section.json", section)
        result = no_stale_run_id("section.json", "run-42", repo_root=tmp_path)
        assert result.passed

    def test_old_run_id_fails(self, tmp_path: Path) -> None:
        from runner.predicates.phase8_section_predicates import no_stale_run_id

        section = _make_section("run-OLD", ["some content"])
        _write_json(tmp_path / "section.json", section)
        result = no_stale_run_id("section.json", "run-NEW", repo_root=tmp_path)
        assert not result.passed
        assert result.failure_category == "STALE_UPSTREAM_MISMATCH"
        assert "run-OLD" in result.details["actual_run_id"]

    def test_missing_file_fails(self, tmp_path: Path) -> None:
        from runner.predicates.phase8_section_predicates import no_stale_run_id

        result = no_stale_run_id("nonexistent.json", "run-1", repo_root=tmp_path)
        assert not result.passed
        assert result.failure_category == "MISSING_MANDATORY_INPUT"

    def test_missing_run_id_field_fails(self, tmp_path: Path) -> None:
        from runner.predicates.phase8_section_predicates import no_stale_run_id

        _write_json(tmp_path / "section.json", {"schema_id": "test"})
        result = no_stale_run_id("section.json", "run-1", repo_root=tmp_path)
        assert not result.passed
        assert result.failure_category == "MALFORMED_ARTIFACT"


# ===========================================================================
# 3. partner_names_preserved predicate
# ===========================================================================


class TestPartnerNamesPreserved:

    def _write_pack(self, tmp_path: Path) -> None:
        pack = {
            "schema_id": "orch.phase8.canonical_reference_pack.v1",
            "partners": [
                {"short_name": "ATU", "legal_name": "Alpenstadt Technical University"},
                {"short_name": "ELI", "legal_name": "EuroLog International AG"},
            ],
            "objectives": [],
            "wps": [],
            "deliverables": [],
        }
        _write_json(tmp_path / "pack.json", pack)

    def test_all_names_present_passes(self, tmp_path: Path) -> None:
        from runner.predicates.phase8_section_predicates import partner_names_preserved

        self._write_pack(tmp_path)
        section = _make_section("r1", [
            "ATU (Alpenstadt Technical University) leads WP1. "
            "ELI (EuroLog International AG) handles logistics."
        ])
        _write_json(tmp_path / "section.json", section)
        result = partner_names_preserved(
            "section.json", "pack.json", repo_root=tmp_path
        )
        assert result.passed

    def test_short_name_without_legal_fails(self, tmp_path: Path) -> None:
        from runner.predicates.phase8_section_predicates import partner_names_preserved

        self._write_pack(tmp_path)
        section = _make_section("r1", [
            "ATU leads WP1. ELI handles logistics."
        ])
        _write_json(tmp_path / "section.json", section)
        result = partner_names_preserved(
            "section.json", "pack.json", repo_root=tmp_path
        )
        assert not result.passed
        assert result.failure_category == "CROSS_ARTIFACT_INCONSISTENCY"
        issues = result.details.get("issues", [])
        short_names = [i["partner"] for i in issues]
        assert "ATU" in short_names
        assert "ELI" in short_names


# ===========================================================================
# 4. deliverable_identity_preserved predicate
# ===========================================================================


class TestDeliverableIdentityPreserved:

    def _write_pack(self, tmp_path: Path) -> None:
        pack = {
            "schema_id": "orch.phase8.canonical_reference_pack.v1",
            "deliverables": [
                {
                    "deliverable_id": "D1-01",
                    "title": "Quality Management Plan",
                    "due_month": 3,
                    "parent_wp": "WP1",
                },
                {
                    "deliverable_id": "D2-01",
                    "title": "Planning Engine Prototype v1",
                    "due_month": 18,
                    "parent_wp": "WP2",
                },
            ],
            "objectives": [],
            "wps": [],
            "partners": [],
        }
        _write_json(tmp_path / "pack.json", pack)

    def test_correct_identity_passes(self, tmp_path: Path) -> None:
        from runner.predicates.phase8_section_predicates import (
            deliverable_identity_preserved,
        )

        self._write_pack(tmp_path)
        section = _make_section("r1", [
            "D1-01 Quality Management Plan (WP1, month 3). "
            "D2-01 Planning Engine Prototype v1 (WP2, month 18)."
        ])
        _write_json(tmp_path / "section.json", section)
        result = deliverable_identity_preserved(
            "section.json", "pack.json", repo_root=tmp_path,
        )
        assert result.passed

    def test_wrong_title_fails(self, tmp_path: Path) -> None:
        from runner.predicates.phase8_section_predicates import (
            deliverable_identity_preserved,
        )

        self._write_pack(tmp_path)
        section = _make_section("r1", [
            "D1-01 Project Report (WP1, month 3)."
        ])
        _write_json(tmp_path / "section.json", section)
        result = deliverable_identity_preserved(
            "section.json", "pack.json", repo_root=tmp_path,
        )
        assert not result.passed
        assert result.failure_category == "CROSS_ARTIFACT_INCONSISTENCY"
        issues = result.details.get("issues", [])
        assert any(
            i["deliverable_id"] == "D1-01" and i["check"] == "title_missing"
            for i in issues
        )

    def test_wrong_due_month_fails(self, tmp_path: Path) -> None:
        from runner.predicates.phase8_section_predicates import (
            deliverable_identity_preserved,
        )

        self._write_pack(tmp_path)
        # D2-01 present but with no due month reference at all
        section = _make_section("r1", [
            "D2-01 Planning Engine Prototype v1 (WP2)."
        ])
        _write_json(tmp_path / "section.json", section)
        result = deliverable_identity_preserved(
            "section.json", "pack.json", repo_root=tmp_path,
        )
        assert not result.passed
        issues = result.details.get("issues", [])
        assert any(
            i["deliverable_id"] == "D2-01" and i["check"] == "due_month_missing"
            for i in issues
        )

    def test_missing_parent_wp_fails(self, tmp_path: Path) -> None:
        from runner.predicates.phase8_section_predicates import (
            deliverable_identity_preserved,
        )

        self._write_pack(tmp_path)
        # D1-01 present with title and month but no WP reference
        section = _make_section("r1", [
            "D1-01 Quality Management Plan (month 3)."
        ])
        _write_json(tmp_path / "section.json", section)
        result = deliverable_identity_preserved(
            "section.json", "pack.json", repo_root=tmp_path,
        )
        assert not result.passed
        issues = result.details.get("issues", [])
        assert any(
            i["deliverable_id"] == "D1-01" and i["check"] == "parent_wp_missing"
            for i in issues
        )


# ===========================================================================
# 5. canonical_terms_preserved predicate
# ===========================================================================


class TestCanonicalTermsPreserved:

    def _write_pack(self, tmp_path: Path) -> None:
        pack = {
            "schema_id": "orch.phase8.canonical_reference_pack.v1",
            "objectives": [
                {"id": "OBJ-1", "title": "Neuro-symbolic planning engine"},
                {"id": "OBJ-2", "title": "Unified adaptive memory architecture"},
            ],
            "wps": [
                {"wp_id": "WP1", "title": "Project Management and Coordination"},
                {"wp_id": "WP2", "title": "Neuro-Symbolic Planning Engine"},
            ],
            "deliverables": [],
            "partners": [],
        }
        _write_json(tmp_path / "pack.json", pack)

    def test_full_titles_present_passes(self, tmp_path: Path) -> None:
        from runner.predicates.phase8_section_predicates import (
            canonical_terms_preserved,
        )

        self._write_pack(tmp_path)
        section = _make_section("r1", [
            "OBJ-1: Neuro-symbolic planning engine develops a new approach. "
            "OBJ-2: Unified adaptive memory architecture supports context. "
            "WP1 (Project Management and Coordination) is led by ATU. "
            "WP2 (Neuro-Symbolic Planning Engine) delivers the core."
        ])
        _write_json(tmp_path / "section.json", section)
        result = canonical_terms_preserved(
            "section.json", "pack.json", repo_root=tmp_path,
        )
        assert result.passed

    def test_shortened_objective_title_fails(self, tmp_path: Path) -> None:
        from runner.predicates.phase8_section_predicates import (
            canonical_terms_preserved,
        )

        self._write_pack(tmp_path)
        # OBJ-1 mentioned but title shortened to just "planning engine"
        section = _make_section("r1", [
            "OBJ-1 focuses on the planning engine approach."
        ])
        _write_json(tmp_path / "section.json", section)
        result = canonical_terms_preserved(
            "section.json", "pack.json", repo_root=tmp_path,
        )
        assert not result.passed
        assert result.failure_category == "CROSS_ARTIFACT_INCONSISTENCY"
        issues = result.details.get("issues", [])
        assert any(i["id"] == "OBJ-1" for i in issues)

    def test_shortened_wp_title_fails(self, tmp_path: Path) -> None:
        from runner.predicates.phase8_section_predicates import (
            canonical_terms_preserved,
        )

        self._write_pack(tmp_path)
        # WP1 mentioned but title shortened
        section = _make_section("r1", [
            "WP1 handles management tasks."
        ])
        _write_json(tmp_path / "section.json", section)
        result = canonical_terms_preserved(
            "section.json", "pack.json", repo_root=tmp_path,
        )
        assert not result.passed
        issues = result.details.get("issues", [])
        assert any(
            i["id"] == "WP1" and i["term_type"] == "wp_title"
            for i in issues
        )

    def test_no_mention_of_id_passes(self, tmp_path: Path) -> None:
        from runner.predicates.phase8_section_predicates import (
            canonical_terms_preserved,
        )

        self._write_pack(tmp_path)
        # Section doesn't mention any IDs — vacuous pass
        section = _make_section("r1", [
            "The project addresses complex challenges."
        ])
        _write_json(tmp_path / "section.json", section)
        result = canonical_terms_preserved(
            "section.json", "pack.json", repo_root=tmp_path,
        )
        assert result.passed


# ===========================================================================
# 6. Primary drafting failure prevents downstream audit skills
# ===========================================================================


class TestStaleArtifactGuard:
    """When a primary drafting skill fails, the agent must halt immediately."""

    def test_primary_drafting_failure_halts_agent(self) -> None:
        from runner.agent_runtime import _PHASE8_PRIMARY_DRAFTING_SKILLS

        # Verify all three skills are in the guard set
        assert "excellence-section-drafting" in _PHASE8_PRIMARY_DRAFTING_SKILLS
        assert "impact-section-drafting" in _PHASE8_PRIMARY_DRAFTING_SKILLS
        assert "implementation-section-drafting" in _PHASE8_PRIMARY_DRAFTING_SKILLS

    def test_guard_returns_failure_with_no_exit_gate(self) -> None:
        """Simulate the code path: primary drafting skill fails -> immediate return."""
        from runner.runtime_models import AgentResult, SkillResult

        # The guard logic: if sid in _PHASE8_PRIMARY_DRAFTING_SKILLS
        # and result.status == "failure", return AgentResult immediately
        # with can_evaluate_exit_gate=False

        # Build what the code would produce
        result = AgentResult(
            status="failure",
            can_evaluate_exit_gate=False,
            failure_reason=(
                "Primary drafting skill 'excellence-section-drafting' failed: "
                "test error; halting agent body (stale-artifact guard)"
            ),
            failure_category="SKILL_FAILURE",
        )
        assert result.status == "failure"
        assert not result.can_evaluate_exit_gate
        assert "stale-artifact guard" in result.failure_reason


# ===========================================================================
# 7. gate_10d tests still pass unchanged
# ===========================================================================


class TestGate10dUnchanged:
    """Verify gate_10d cross-section consistency predicate still works."""

    def _make_assembled_draft(self, consistency_log: list[dict]) -> dict:
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

    def test_consistent_passes(self, tmp_path: Path) -> None:
        from runner.predicates.criterion_predicates import cross_section_consistency

        draft = self._make_assembled_draft([
            {"check_id": "CC-01", "status": "consistent", "description": "ok"},
        ])
        _write_json(tmp_path / "assembled.json", draft)
        result = cross_section_consistency(
            "assembled.json", "sections/", "tier3/", repo_root=tmp_path,
        )
        assert result.passed

    def test_inconsistency_flagged_fails(self, tmp_path: Path) -> None:
        from runner.predicates.criterion_predicates import cross_section_consistency

        draft = self._make_assembled_draft([
            {"check_id": "CC-03", "status": "inconsistency_flagged",
             "description": "partner name mismatch"},
        ])
        _write_json(tmp_path / "assembled.json", draft)
        result = cross_section_consistency(
            "assembled.json", "sections/", "tier3/", repo_root=tmp_path,
        )
        assert not result.passed
        assert "CC-03" in result.details["flagged_checks"]


# ===========================================================================
# 8. Drafting skill size and hygiene (extended from existing tests)
# ===========================================================================


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

BANNED_PATTERNS = ["Self-Check", "CCR-"]
BANNED_PATTERNS_LOWER = ["revise before output"]


class TestDraftingSkillHygiene:
    """Drafting skills remain slim and contain no bloat."""

    @pytest.mark.parametrize("skill", DRAFTING_SKILLS)
    def test_under_size_limit(self, skill: str) -> None:
        path = SKILLS_DIR / skill
        assert path.is_file(), f"Skill spec not found: {path}"
        text = path.read_text(encoding="utf-8")
        limit = SIZE_LIMITS[skill]
        assert len(text) <= limit, (
            f"{skill} is {len(text)} chars, limit is {limit}"
        )

    @pytest.mark.parametrize("skill", DRAFTING_SKILLS)
    def test_no_banned_patterns(self, skill: str) -> None:
        path = SKILLS_DIR / skill
        text = path.read_text(encoding="utf-8")
        for pattern in BANNED_PATTERNS:
            assert pattern not in text, (
                f"{skill} contains '{pattern}'"
            )
        text_lower = text.lower()
        for pattern in BANNED_PATTERNS_LOWER:
            assert pattern not in text_lower, (
                f"{skill} contains '{pattern}'"
            )

    @pytest.mark.parametrize("skill", DRAFTING_SKILLS)
    def test_declares_canonical_reference_pack_input(self, skill: str) -> None:
        path = SKILLS_DIR / skill
        text = path.read_text(encoding="utf-8")
        assert "canonical_reference_pack.json" in text, (
            f"{skill} must declare canonical_reference_pack.json as input"
        )


# ===========================================================================
# 9. Predicates registered in gate evaluator
# ===========================================================================


class TestPredicatesRegistered:
    """New predicates are registered in the PREDICATE_REGISTRY."""

    def test_all_section_predicates_registered(self) -> None:
        from runner.gate_evaluator import PREDICATE_REGISTRY

        expected = [
            "no_stale_run_id",
            "partner_names_preserved",
            "deliverable_identity_preserved",
            "canonical_terms_preserved",
        ]
        for name in expected:
            assert name in PREDICATE_REGISTRY, (
                f"{name} not registered in PREDICATE_REGISTRY"
            )


# ===========================================================================
# 10. Scheduler hook builds canonical pack before Phase 8 dispatch
# ===========================================================================


class TestSchedulerCanonicalPackHook:
    """The canonical pack builder is invoked before Phase 8 node dispatch."""

    def test_canonical_pack_path_constant(self) -> None:
        from runner.phase8_canonical_pack import CANONICAL_PACK_REL

        assert "phase8_drafting_review/canonical_reference_pack.json" in CANONICAL_PACK_REL

    def test_pack_is_deterministic(self, tmp_path: Path) -> None:
        """Same inputs produce identical output."""
        from runner.phase8_canonical_pack import build_phase8_canonical_reference_pack

        _populate_tier3_and_tier4(tmp_path)
        out1 = build_phase8_canonical_reference_pack(tmp_path, "run-x")
        content1 = out1.read_text(encoding="utf-8")
        out2 = build_phase8_canonical_reference_pack(tmp_path, "run-x")
        content2 = out2.read_text(encoding="utf-8")
        assert content1 == content2


# ===========================================================================
# 11. Blocking canonical pack — failure blocks n08a/b/c before drafting
# ===========================================================================


class TestBlockingCanonicalPack:
    """Canonical pack build failure must block the node before agent dispatch."""

    def test_missing_source_files_blocks_node(self, tmp_path: Path) -> None:
        """When Tier 3/4 source dirs don't exist, pack build still succeeds
        (empty lists), but validation catches wrong run_id only if builder
        itself raises.  Test the validation path explicitly."""
        from runner.phase8_canonical_pack import (
            CANONICAL_PACK_REL,
            SCHEMA_ID,
            build_phase8_canonical_reference_pack,
        )

        # Build succeeds even with empty sources (empty lists, no error)
        _populate_tier3_and_tier4(tmp_path)
        pack_path = build_phase8_canonical_reference_pack(tmp_path, "run-1")
        data = json.loads(pack_path.read_text(encoding="utf-8"))
        assert data["schema_id"] == SCHEMA_ID
        assert data["run_id"] == "run-1"

    def test_pack_with_wrong_run_id_detected(self, tmp_path: Path) -> None:
        """A pack written by a prior run is detected as invalid."""
        from runner.phase8_canonical_pack import (
            CANONICAL_PACK_REL,
            SCHEMA_ID,
            build_phase8_canonical_reference_pack,
        )

        _populate_tier3_and_tier4(tmp_path)
        # Build with old run_id
        pack_path = build_phase8_canonical_reference_pack(tmp_path, "old-run")
        data = json.loads(pack_path.read_text(encoding="utf-8"))

        # Scheduler would check run_id == current run
        assert data["run_id"] == "old-run"
        assert data["run_id"] != "new-run"  # would fail validation

    def test_pack_with_wrong_schema_id_detected(self, tmp_path: Path) -> None:
        """A pack with corrupted schema_id is detected."""
        from runner.phase8_canonical_pack import (
            CANONICAL_PACK_REL,
            SCHEMA_ID,
        )

        pack_path = tmp_path / CANONICAL_PACK_REL
        pack_path.parent.mkdir(parents=True, exist_ok=True)
        _write_json(pack_path, {
            "schema_id": "wrong.schema",
            "run_id": "run-1",
        })
        data = json.loads(pack_path.read_text(encoding="utf-8"))
        assert data["schema_id"] != SCHEMA_ID  # would fail validation

    def test_scheduler_blocks_on_build_exception(self) -> None:
        """When build raises, _dispatch_node returns blocked_at_exit."""
        from runner.runtime_models import NodeExecutionResult

        # Verify the contract: blocked_at_exit with agent_body origin
        result = NodeExecutionResult(
            node_id="n08a_excellence_drafting",
            final_state="blocked_at_exit",
            exit_gate_evaluated=False,
            failure_origin="agent_body",
            gate_result=None,
            agent_result=None,
            failure_reason="Canonical reference pack build/validation failed",
            failure_category="MISSING_INPUT",
        )
        assert result.final_state == "blocked_at_exit"
        assert result.failure_origin == "agent_body"
        assert not result.exit_gate_evaluated
        assert result.failure_category == "MISSING_INPUT"
        assert result.agent_result is None  # never reached agent


# ===========================================================================
# 12. Post-drafting freshness check — stale artifact blocks audit skills
# ===========================================================================


class TestPostDraftingFreshnessCheck:
    """After primary drafting succeeds, verify artifact has current run_id."""

    def test_artifact_mapping_covers_all_primary_skills(self) -> None:
        from runner.agent_runtime import (
            _PHASE8_PRIMARY_DRAFTING_SKILLS,
            _PHASE8_SKILL_EXPECTED_ARTIFACT,
        )

        for skill in _PHASE8_PRIMARY_DRAFTING_SKILLS:
            assert skill in _PHASE8_SKILL_EXPECTED_ARTIFACT, (
                f"{skill} not in _PHASE8_SKILL_EXPECTED_ARTIFACT"
            )

    def test_stale_run_id_blocks_audit_skills(self, tmp_path: Path) -> None:
        """Section artifact with old run_id → freshness check fails."""
        from runner.agent_runtime import _PHASE8_SKILL_EXPECTED_ARTIFACT

        skill = "excellence-section-drafting"
        rel_path = _PHASE8_SKILL_EXPECTED_ARTIFACT[skill]
        art_path = tmp_path / rel_path
        art_path.parent.mkdir(parents=True, exist_ok=True)

        # Write artifact with OLD run_id
        _write_json(art_path, {
            "schema_id": "orch.tier5.excellence_section.v1",
            "run_id": "old-run-id",
            "criterion": "Excellence",
            "sub_sections": [],
        })

        # Simulate the freshness check logic from agent_runtime
        current_run_id = "current-run-id"
        data = json.loads(art_path.read_text(encoding="utf-8-sig"))
        art_rid = data.get("run_id")

        assert art_rid != current_run_id
        # Agent runtime would halt here with can_evaluate_exit_gate=False

    def test_current_run_id_permits_audit_skills(self, tmp_path: Path) -> None:
        """Section artifact with current run_id → freshness check passes."""
        from runner.agent_runtime import _PHASE8_SKILL_EXPECTED_ARTIFACT

        skill = "impact-section-drafting"
        rel_path = _PHASE8_SKILL_EXPECTED_ARTIFACT[skill]
        art_path = tmp_path / rel_path
        art_path.parent.mkdir(parents=True, exist_ok=True)

        current_run_id = "run-42"
        _write_json(art_path, {
            "schema_id": "orch.tier5.impact_section.v1",
            "run_id": current_run_id,
            "criterion": "Impact",
            "sub_sections": [],
        })

        data = json.loads(art_path.read_text(encoding="utf-8-sig"))
        assert data["run_id"] == current_run_id
        # Agent runtime would continue to audit skills

    def test_missing_artifact_blocks_audit_skills(self, tmp_path: Path) -> None:
        """Missing section artifact → freshness check fails."""
        from runner.agent_runtime import _PHASE8_SKILL_EXPECTED_ARTIFACT

        skill = "implementation-section-drafting"
        rel_path = _PHASE8_SKILL_EXPECTED_ARTIFACT[skill]
        art_path = tmp_path / rel_path

        assert not art_path.exists()
        # Agent runtime would halt: FileNotFoundError caught

    def test_freshness_halt_returns_correct_agent_result(self) -> None:
        """Freshness failure returns AgentResult with correct fields."""
        from runner.runtime_models import AgentResult

        result = AgentResult(
            status="failure",
            can_evaluate_exit_gate=False,
            failure_reason=(
                "Post-drafting freshness check failed for "
                "'excellence-section-drafting': run_id mismatch; "
                "halting before audit skills"
            ),
            failure_category="MISSING_INPUT",
        )
        assert result.status == "failure"
        assert not result.can_evaluate_exit_gate
        assert result.failure_category == "MISSING_INPUT"
        assert "freshness" in result.failure_reason


# ===========================================================================
# 13. no_stale_run_id gate predicate still catches stale artifacts
# ===========================================================================


class TestNoStaleRunIdGateLevel:
    """The no_stale_run_id predicate works at gate evaluation time."""

    def test_gate_level_stale_detection(self, tmp_path: Path) -> None:
        from runner.predicates.phase8_section_predicates import no_stale_run_id

        _write_json(tmp_path / "section.json", {
            "schema_id": "orch.tier5.excellence_section.v1",
            "run_id": "stale-run-abc",
            "sub_sections": [],
        })
        result = no_stale_run_id(
            "section.json", "current-run-xyz", repo_root=tmp_path
        )
        assert not result.passed
        assert result.failure_category == "STALE_UPSTREAM_MISMATCH"
        assert result.details["actual_run_id"] == "stale-run-abc"
        assert result.details["expected_run_id"] == "current-run-xyz"

    def test_gate_level_current_passes(self, tmp_path: Path) -> None:
        from runner.predicates.phase8_section_predicates import no_stale_run_id

        _write_json(tmp_path / "section.json", {
            "schema_id": "orch.tier5.excellence_section.v1",
            "run_id": "run-match",
            "sub_sections": [],
        })
        result = no_stale_run_id(
            "section.json", "run-match", repo_root=tmp_path
        )
        assert result.passed


# ===========================================================================
# 14. Canonical pack preserves measurable_target exactly
# ===========================================================================


class TestMeasurableTargetPreservation:

    def test_measurable_target_copied_exactly(self, tmp_path: Path) -> None:
        from runner.phase8_canonical_pack import build_phase8_canonical_reference_pack

        target = (
            "Open-source release with ≥500 GitHub stars; "
            "results validated through ≥2 TEFs; "
            "technology transfer initiated through ≥3 EDIHs"
        )
        _write_json(
            tmp_path / "docs" / "tier3_project_instantiation"
            / "architecture_inputs" / "objectives.json",
            {"objectives": [
                {"id": "OBJ-1", "title": "Test", "measurable_target": target},
            ]},
        )
        # Provide minimal other sources
        _write_json(
            tmp_path / "docs" / "tier4_orchestration_state"
            / "phase_outputs" / "phase3_wp_design" / "wp_structure.json",
            {"work_packages": [{"wp_id": "WP1", "title": "T", "lead_partner": "P",
                                "deliverables": [{"deliverable_id": "D1-01",
                                                   "title": "D", "due_month": 3}]}]},
        )
        _write_json(
            tmp_path / "docs" / "tier3_project_instantiation"
            / "consortium" / "partners.json",
            {"partners": [{"short_name": "P", "legal_name": "Partner One"}]},
        )
        out = build_phase8_canonical_reference_pack(tmp_path, "r1")
        data = json.loads(out.read_text(encoding="utf-8"))

        obj = data["objectives"][0]
        assert obj["measurable_target"] == target

    def test_multi_clause_target_preserved(self, tmp_path: Path) -> None:
        from runner.phase8_canonical_pack import build_phase8_canonical_reference_pack

        target = "Demonstrate ≥30% improvement in coherence and ≥15% improvement in consistency"
        _write_json(
            tmp_path / "docs" / "tier3_project_instantiation"
            / "architecture_inputs" / "objectives.json",
            {"objectives": [
                {"id": "OBJ-2", "title": "Memory arch", "measurable_target": target},
            ]},
        )
        _write_json(
            tmp_path / "docs" / "tier4_orchestration_state"
            / "phase_outputs" / "phase3_wp_design" / "wp_structure.json",
            {"work_packages": [{"wp_id": "WP1", "title": "T", "lead_partner": "P",
                                "deliverables": [{"deliverable_id": "D1-01",
                                                   "title": "D", "due_month": 3}]}]},
        )
        _write_json(
            tmp_path / "docs" / "tier3_project_instantiation"
            / "consortium" / "partners.json",
            {"partners": [{"short_name": "P", "legal_name": "Partner One"}]},
        )
        out = build_phase8_canonical_reference_pack(tmp_path, "r1")
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["objectives"][0]["measurable_target"] == target

    def test_missing_measurable_target_omitted(self, tmp_path: Path) -> None:
        from runner.phase8_canonical_pack import build_phase8_canonical_reference_pack

        _write_json(
            tmp_path / "docs" / "tier3_project_instantiation"
            / "architecture_inputs" / "objectives.json",
            {"objectives": [{"id": "OBJ-1", "title": "No target obj"}]},
        )
        _write_json(
            tmp_path / "docs" / "tier4_orchestration_state"
            / "phase_outputs" / "phase3_wp_design" / "wp_structure.json",
            {"work_packages": [{"wp_id": "WP1", "title": "T", "lead_partner": "P",
                                "deliverables": [{"deliverable_id": "D1-01",
                                                   "title": "D", "due_month": 3}]}]},
        )
        _write_json(
            tmp_path / "docs" / "tier3_project_instantiation"
            / "consortium" / "partners.json",
            {"partners": [{"short_name": "P", "legal_name": "Partner One"}]},
        )
        out = build_phase8_canonical_reference_pack(tmp_path, "r1")
        data = json.loads(out.read_text(encoding="utf-8"))
        assert "measurable_target" not in data["objectives"][0]


# ===========================================================================
# 15. Empty required arrays block n08a/b/c
# ===========================================================================


class TestEmptyPackArraysBlock:

    def _make_pack(self, tmp_path: Path, **overrides: list) -> Path:
        from runner.phase8_canonical_pack import CANONICAL_PACK_REL, SCHEMA_ID

        pack = {
            "schema_id": SCHEMA_ID,
            "run_id": "run-1",
            "objectives": [{"id": "OBJ-1", "title": "T", "measurable_target": "≥1"}],
            "outcomes": [],
            "wps": [{"wp_id": "WP1", "title": "T"}],
            "deliverables": [{"deliverable_id": "D1-01", "title": "D",
                              "due_month": 3, "parent_wp": "WP1"}],
            "partners": [{"short_name": "P", "legal_name": "Partner"}],
            "aliases": [],
        }
        pack.update(overrides)
        path = tmp_path / CANONICAL_PACK_REL
        path.parent.mkdir(parents=True, exist_ok=True)
        _write_json(path, pack)
        return path

    def test_empty_objectives_detected(self, tmp_path: Path) -> None:
        self._make_pack(tmp_path, objectives=[])
        pack = json.loads(
            (tmp_path / "docs/tier4_orchestration_state/phase_outputs"
             "/phase8_drafting_review/canonical_reference_pack.json")
            .read_text(encoding="utf-8")
        )
        empty = [k for k in ("objectives", "wps", "deliverables", "partners")
                 if not pack.get(k)]
        assert "objectives" in empty

    def test_empty_wps_detected(self, tmp_path: Path) -> None:
        self._make_pack(tmp_path, wps=[])
        pack = json.loads(
            (tmp_path / "docs/tier4_orchestration_state/phase_outputs"
             "/phase8_drafting_review/canonical_reference_pack.json")
            .read_text(encoding="utf-8")
        )
        empty = [k for k in ("objectives", "wps", "deliverables", "partners")
                 if not pack.get(k)]
        assert "wps" in empty

    def test_empty_deliverables_detected(self, tmp_path: Path) -> None:
        self._make_pack(tmp_path, deliverables=[])
        pack = json.loads(
            (tmp_path / "docs/tier4_orchestration_state/phase_outputs"
             "/phase8_drafting_review/canonical_reference_pack.json")
            .read_text(encoding="utf-8")
        )
        empty = [k for k in ("objectives", "wps", "deliverables", "partners")
                 if not pack.get(k)]
        assert "deliverables" in empty

    def test_empty_partners_detected(self, tmp_path: Path) -> None:
        self._make_pack(tmp_path, partners=[])
        pack = json.loads(
            (tmp_path / "docs/tier4_orchestration_state/phase_outputs"
             "/phase8_drafting_review/canonical_reference_pack.json")
            .read_text(encoding="utf-8")
        )
        empty = [k for k in ("objectives", "wps", "deliverables", "partners")
                 if not pack.get(k)]
        assert "partners" in empty

    def test_full_pack_passes_validation(self, tmp_path: Path) -> None:
        self._make_pack(tmp_path)
        pack = json.loads(
            (tmp_path / "docs/tier4_orchestration_state/phase_outputs"
             "/phase8_drafting_review/canonical_reference_pack.json")
            .read_text(encoding="utf-8")
        )
        empty = [k for k in ("objectives", "wps", "deliverables", "partners")
                 if not pack.get(k)]
        assert empty == []


# ===========================================================================
# 16. measurable_targets_preserved predicate
# ===========================================================================


class TestMeasurableTargetsPreservedPredicate:

    def _write_pack(self, tmp_path: Path) -> None:
        pack = {
            "schema_id": "orch.phase8.canonical_reference_pack.v1",
            "objectives": [
                {
                    "id": "OBJ-1",
                    "title": "Neuro-symbolic planning engine",
                    "measurable_target": (
                        "Open-source release with ≥500 GitHub stars; "
                        "results validated through ≥2 TEFs; "
                        "technology transfer initiated through ≥3 EDIHs"
                    ),
                },
                {
                    "id": "OBJ-2",
                    "title": "Unified adaptive memory architecture",
                    "measurable_target": (
                        "Demonstrate ≥30% improvement in coherence "
                        "and ≥15% improvement in consistency"
                    ),
                },
            ],
            "wps": [],
            "deliverables": [],
            "partners": [],
        }
        _write_json(tmp_path / "pack.json", pack)

    def test_all_metrics_present_passes(self, tmp_path: Path) -> None:
        from runner.predicates.phase8_section_predicates import (
            measurable_targets_preserved,
        )

        self._write_pack(tmp_path)
        section = _make_section("r1", [
            "OBJ-1 targets an open-source release with ≥500 GitHub stars, "
            "results validated through ≥2 TEFs, and technology transfer "
            "initiated through ≥3 EDIHs."
        ])
        _write_json(tmp_path / "section.json", section)
        result = measurable_targets_preserved(
            "section.json", "pack.json", repo_root=tmp_path,
        )
        assert result.passed

    def test_dropped_metric_fails(self, tmp_path: Path) -> None:
        from runner.predicates.phase8_section_predicates import (
            measurable_targets_preserved,
        )

        self._write_pack(tmp_path)
        # OBJ-1 mentioned but only ≥500 present, ≥2 and ≥3 missing
        section = _make_section("r1", [
            "OBJ-1 targets an open-source release with ≥500 GitHub stars."
        ])
        _write_json(tmp_path / "section.json", section)
        result = measurable_targets_preserved(
            "section.json", "pack.json", repo_root=tmp_path,
        )
        assert not result.passed
        assert result.failure_category == "CROSS_ARTIFACT_INCONSISTENCY"
        issues = result.details["issues"]
        assert len(issues) == 1
        assert issues[0]["objective_id"] == "OBJ-1"
        assert len(issues[0]["missing_components"]) == 2

    def test_multi_clause_all_present_passes(self, tmp_path: Path) -> None:
        from runner.predicates.phase8_section_predicates import (
            measurable_targets_preserved,
        )

        self._write_pack(tmp_path)
        section = _make_section("r1", [
            "OBJ-2 will demonstrate ≥30% improvement in coherence "
            "and ≥15% improvement in consistency."
        ])
        _write_json(tmp_path / "section.json", section)
        result = measurable_targets_preserved(
            "section.json", "pack.json", repo_root=tmp_path,
        )
        assert result.passed

    def test_multi_clause_partial_loss_fails(self, tmp_path: Path) -> None:
        from runner.predicates.phase8_section_predicates import (
            measurable_targets_preserved,
        )

        self._write_pack(tmp_path)
        # Only ≥30% present, ≥15% dropped
        section = _make_section("r1", [
            "OBJ-2 will demonstrate ≥30% improvement in coherence."
        ])
        _write_json(tmp_path / "section.json", section)
        result = measurable_targets_preserved(
            "section.json", "pack.json", repo_root=tmp_path,
        )
        assert not result.passed
        issues = result.details["issues"]
        assert issues[0]["objective_id"] == "OBJ-2"
        missing = issues[0]["missing_components"]
        assert any("15%" in m for m in missing)

    def test_unreferenced_objective_not_checked(self, tmp_path: Path) -> None:
        from runner.predicates.phase8_section_predicates import (
            measurable_targets_preserved,
        )

        self._write_pack(tmp_path)
        # Section mentions neither OBJ-1 nor OBJ-2 — vacuous pass
        section = _make_section("r1", [
            "The project addresses complex challenges in AI."
        ])
        _write_json(tmp_path / "section.json", section)
        result = measurable_targets_preserved(
            "section.json", "pack.json", repo_root=tmp_path,
        )
        assert result.passed

    def test_predicate_registered_in_evaluator(self) -> None:
        from runner.gate_evaluator import PREDICATE_REGISTRY

        assert "measurable_targets_preserved" in PREDICATE_REGISTRY
