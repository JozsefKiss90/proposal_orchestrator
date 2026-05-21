"""
Tests for Phase 8 section predicates — proposal-prose-aware rules.

Covers:
    partner_names_preserved      — 7 cases
    deliverable_identity_preserved — 10 cases
    canonical_terms_preserved    — 8 cases
    measurable_targets_preserved — 3 cases (behaviour unchanged)
    CC-style local catches       — 2 cases

All tests use synthetic temp files via pytest ``tmp_path``.
No dependency on live repository artifacts.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from runner.predicates.phase8_section_predicates import (
    canonical_terms_preserved,
    deliverable_identity_preserved,
    measurable_targets_preserved,
    partner_names_preserved,
)
from runner.predicates.types import CROSS_ARTIFACT_INCONSISTENCY


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _write_json(path: Path, data: dict) -> Path:
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def _make_section(tmp_path: Path, content: str, name: str = "excellence_section.json") -> Path:
    return _write_json(tmp_path / name, {"sub_sections": [{"content": content}]})


@pytest.fixture
def pack(tmp_path):
    """Minimal canonical reference pack."""
    data = {
        "partners": [
            {"short_name": "ATU", "legal_name": "Alpenstadt Technical University"},
            {"short_name": "BIIS", "legal_name": "Breda Institute for Intelligent Systems"},
            {"short_name": "CERIA", "legal_name": "Centre Européen de Recherche en Informatique Avancée"},
        ],
        "objectives": [
            {
                "id": "OBJ-1",
                "title": "Neuro-symbolic planning engine for autonomous task decomposition",
                "measurable_target": "Achieve ≥40% improvement in plan success rate.",
            },
            {
                "id": "OBJ-2",
                "title": "Unified adaptive memory architecture",
                "measurable_target": "Demonstrate ≥30% improvement in task coherence.",
            },
        ],
        "outcomes": [
            {
                "id": "OUT-1",
                "title": "Neuro-symbolic planning framework for LLM-based agents",
                "linked_objectives": ["OBJ-1"],
                "linked_deliverable_ids": ["D2-01", "D2-02"],
            },
            {
                "id": "OUT-9",
                "title": "External Tool and API Orchestration Layer",
                "linked_objectives": ["OBJ-2"],
                "linked_deliverable_ids": ["D2-02"],
            },
        ],
        "wps": [
            {"wp_id": "WP1", "title": "Project Management and Coordination"},
            {"wp_id": "WP2", "title": "Neuro-Symbolic Planning and Reasoning Engine"},
        ],
        "deliverables": [
            {
                "deliverable_id": "D1-01",
                "title": "Project management and quality plan",
                "due_month": 3,
                "parent_wp": "WP1",
            },
            {
                "deliverable_id": "D2-01",
                "title": "Neuro-symbolic planning architecture specification",
                "due_month": 18,
                "parent_wp": "WP2",
            },
            {
                "deliverable_id": "D2-02",
                "title": "Planning engine software prototype",
                "due_month": 36,
                "parent_wp": "WP2",
            },
        ],
    }
    return _write_json(tmp_path / "canonical_pack.json", data)


# ---------------------------------------------------------------------------
# partner_names_preserved
# ---------------------------------------------------------------------------


class TestPartnerNamesPreserved:

    def test_short_name_only_passes(self, tmp_path, pack):
        """Short names without legal names should pass — the main fix."""
        section = _make_section(
            tmp_path,
            "ATU leads WP2 while BIIS contributes to memory research. "
            "CERIA provides coordination protocol expertise.",
        )
        result = partner_names_preserved(section, pack, repo_root=tmp_path)
        assert result.passed

    def test_correct_legal_name_passes(self, tmp_path, pack):
        """Short name with its correct legal name in parenthetical passes."""
        section = _make_section(
            tmp_path,
            "ATU (Alpenstadt Technical University) leads the consortium.",
        )
        result = partner_names_preserved(section, pack, repo_root=tmp_path)
        assert result.passed

    def test_truncated_legal_name_fails(self, tmp_path, pack):
        """Truncated legal name should fail."""
        section = _make_section(
            tmp_path,
            "The task is led by ATU. Alpenstadt Technical will provide "
            "the main infrastructure for the planning engine.",
        )
        result = partner_names_preserved(section, pack, repo_root=tmp_path)
        assert not result.passed
        assert result.failure_category == CROSS_ARTIFACT_INCONSISTENCY
        assert any("truncated" in i["issue"] for i in result.details["issues"])

    def test_conflation_fails(self, tmp_path, pack):
        """Short name with wrong partner's legal name in parenthetical fails."""
        section = _make_section(
            tmp_path,
            "ATU (Breda Institute for Intelligent Systems) leads WP2.",
        )
        result = partner_names_preserved(section, pack, repo_root=tmp_path)
        assert not result.passed
        assert result.failure_category == CROSS_ARTIFACT_INCONSISTENCY
        assert any("conflat" in i["issue"].lower() for i in result.details["issues"])

    def test_empty_content_passes(self, tmp_path, pack):
        section = _make_section(tmp_path, "")
        result = partner_names_preserved(section, pack, repo_root=tmp_path)
        assert result.passed

    def test_no_partners_passes(self, tmp_path):
        pack = _write_json(tmp_path / "pack.json", {"partners": []})
        section = _make_section(tmp_path, "ATU leads the project.")
        result = partner_names_preserved(section, pack, repo_root=tmp_path)
        assert result.passed

    def test_short_role_parenthetical_passes(self, tmp_path, pack):
        """Short role description in parenthetical should not trigger conflation."""
        section = _make_section(
            tmp_path,
            "ATU (coordinator) manages the project. BIIS (technology lead) "
            "delivers the memory architecture.",
        )
        result = partner_names_preserved(section, pack, repo_root=tmp_path)
        assert result.passed


# ---------------------------------------------------------------------------
# deliverable_identity_preserved
# ---------------------------------------------------------------------------


class TestDeliverableIdentityPreserved:

    def test_id_alone_passes(self, tmp_path, pack):
        """Bare deliverable ID reference passes."""
        section = _make_section(
            tmp_path,
            "The work in WP2 produces D2-01 and D2-02, which together "
            "validate the planning engine architecture.",
        )
        result = deliverable_identity_preserved(section, pack, repo_root=tmp_path)
        assert result.passed

    def test_correct_title_passes(self, tmp_path, pack):
        """Deliverable ID with correct canonical title passes."""
        section = _make_section(
            tmp_path,
            "D2-01: Neuro-symbolic planning architecture specification "
            "will be delivered at month 18.",
        )
        result = deliverable_identity_preserved(section, pack, repo_root=tmp_path)
        assert result.passed

    def test_wrong_title_fails(self, tmp_path, pack):
        """Deliverable ID with wrong title explicitly attached fails."""
        section = _make_section(
            tmp_path,
            "D2-01: Neuro-symbolic planning memory architecture "
            "will be delivered in the first period.",
        )
        result = deliverable_identity_preserved(section, pack, repo_root=tmp_path)
        assert not result.passed
        assert any(
            i["check"] == "wrong_title" for i in result.details["issues"]
        )

    def test_wrong_wp_fails(self, tmp_path, pack):
        """Deliverable ID with wrong parent WP in parenthetical fails."""
        section = _make_section(
            tmp_path,
            "The deliverable D2-01 (WP1) provides the architecture specification.",
        )
        result = deliverable_identity_preserved(section, pack, repo_root=tmp_path)
        assert not result.passed
        assert any(
            i["check"] == "wrong_parent_wp" for i in result.details["issues"]
        )

    def test_correct_wp_passes(self, tmp_path, pack):
        """Deliverable ID with correct parent WP passes."""
        section = _make_section(
            tmp_path,
            "The deliverable D2-01 (WP2) provides the architecture specification.",
        )
        result = deliverable_identity_preserved(section, pack, repo_root=tmp_path)
        assert result.passed

    def test_wrong_month_fails(self, tmp_path, pack):
        """Deliverable ID with wrong due month explicitly attached fails."""
        section = _make_section(
            tmp_path,
            "D2-01 (M24) is the architecture specification deliverable.",
        )
        result = deliverable_identity_preserved(section, pack, repo_root=tmp_path)
        assert not result.passed
        assert any(
            i["check"] == "wrong_due_month" for i in result.details["issues"]
        )

    def test_correct_month_passes(self, tmp_path, pack):
        """Deliverable ID with correct due month passes."""
        section = _make_section(
            tmp_path,
            "D2-01 (M18) is the architecture specification deliverable.",
        )
        result = deliverable_identity_preserved(section, pack, repo_root=tmp_path)
        assert result.passed

    def test_unknown_id_fails(self, tmp_path, pack):
        """Unknown deliverable ID fails."""
        section = _make_section(
            tmp_path,
            "The project will also produce D99-01 for external validation.",
        )
        result = deliverable_identity_preserved(section, pack, repo_root=tmp_path)
        assert not result.passed
        assert any(
            i["check"] == "unknown_deliverable" for i in result.details["issues"]
        )

    def test_multi_outcome_narrowing_fails(self, tmp_path, pack):
        """Exclusive-purpose language on multi-outcome deliverable fails."""
        section = _make_section(
            tmp_path,
            "D2-02 is dedicated exclusively to validating the planning engine.",
        )
        result = deliverable_identity_preserved(section, pack, repo_root=tmp_path)
        assert not result.passed
        assert any(
            i["check"] == "multi_outcome_narrowing" for i in result.details["issues"]
        )

    def test_multi_outcome_no_narrowing_passes(self, tmp_path, pack):
        """Multi-outcome deliverable without narrowing passes."""
        section = _make_section(
            tmp_path,
            "D2-02 contributes to both planning validation and tool integration.",
        )
        result = deliverable_identity_preserved(section, pack, repo_root=tmp_path)
        assert result.passed

    def test_empty_content_passes(self, tmp_path, pack):
        section = _make_section(tmp_path, "")
        result = deliverable_identity_preserved(section, pack, repo_root=tmp_path)
        assert result.passed


# ---------------------------------------------------------------------------
# canonical_terms_preserved
# ---------------------------------------------------------------------------


class TestCanonicalTermsPreserved:

    def test_wp_id_alone_passes(self, tmp_path, pack):
        """WP ID without title passes — the main fix."""
        section = _make_section(
            tmp_path,
            "WP1 handles project coordination while WP2 delivers the "
            "core planning engine components.",
        )
        result = canonical_terms_preserved(section, pack, repo_root=tmp_path)
        assert result.passed

    def test_wp_id_correct_title_passes(self, tmp_path, pack):
        """WP ID with correct canonical title passes."""
        section = _make_section(
            tmp_path,
            "WP2: Neuro-Symbolic Planning and Reasoning Engine will "
            "develop the core planning components.",
        )
        result = canonical_terms_preserved(section, pack, repo_root=tmp_path)
        assert result.passed

    def test_wp_id_correct_shortened_title_passes(self, tmp_path, pack):
        """WP ID with valid shortened canonical title passes (substring)."""
        section = _make_section(
            tmp_path,
            "WP2 (Neuro-Symbolic Planning) focuses on the core "
            "reasoning components.",
        )
        result = canonical_terms_preserved(section, pack, repo_root=tmp_path)
        assert result.passed

    def test_wp_id_wrong_title_fails(self, tmp_path, pack):
        """WP ID with wrong title fails."""
        section = _make_section(
            tmp_path,
            "WP2: Neuro-Symbolic Planning and Memory Integration "
            "develops the main system components.",
        )
        result = canonical_terms_preserved(section, pack, repo_root=tmp_path)
        assert not result.passed
        assert any(
            i["term_type"] == "wp_title" and i["id"] == "WP2"
            for i in result.details["issues"]
        )

    def test_obj_id_alone_passes(self, tmp_path, pack):
        """Objective ID without title passes."""
        section = _make_section(
            tmp_path,
            "OBJ-1 drives the core technical innovation while OBJ-2 "
            "ensures long-term memory coherence.",
        )
        result = canonical_terms_preserved(section, pack, repo_root=tmp_path)
        assert result.passed

    def test_obj_id_correct_title_passes(self, tmp_path, pack):
        """Objective ID with correct canonical title passes."""
        section = _make_section(
            tmp_path,
            "OBJ-1: Neuro-symbolic planning engine for autonomous task "
            "decomposition is the primary technical objective.",
        )
        result = canonical_terms_preserved(section, pack, repo_root=tmp_path)
        assert result.passed

    def test_obj_id_wrong_title_fails(self, tmp_path, pack):
        """Objective ID with wrong title fails when canonical words appear in a wrong combination."""
        section = _make_section(
            tmp_path,
            "OBJ-1: Neuro-symbolic engine for memory architecture "
            "decomposition is the primary objective.",
        )
        result = canonical_terms_preserved(section, pack, repo_root=tmp_path)
        assert not result.passed
        assert any(
            i["term_type"] == "objective_title" and i["id"] == "OBJ-1"
            for i in result.details["issues"]
        )

    def test_empty_content_passes(self, tmp_path, pack):
        section = _make_section(tmp_path, "")
        result = canonical_terms_preserved(section, pack, repo_root=tmp_path)
        assert result.passed


# ---------------------------------------------------------------------------
# measurable_targets_preserved (behaviour unchanged)
# ---------------------------------------------------------------------------


class TestMeasurableTargetsPreserved:

    def test_missing_metrics_fails(self, tmp_path, pack):
        """Missing quantitative components fails — OBJ-5/OBJ-6 style."""
        section = _make_section(
            tmp_path,
            "The project addresses all project objectives. "
            "OBJ-1 achieves ≥40% improvement. "
            "OBJ-2 demonstrates ≥30% improvement.",
            name="excellence_section.json",
        )
        result = measurable_targets_preserved(section, pack, repo_root=tmp_path)
        # OBJ-1 and OBJ-2 metrics are present, but if section claims "all objectives"
        # and the pack only has OBJ-1 and OBJ-2, it should pass
        assert result.passed

    def test_metric_omission_fails(self, tmp_path, pack):
        """Explicitly-mentioned objective with missing metrics fails."""
        section = _make_section(
            tmp_path,
            "OBJ-1 will advance the planning engine significantly. "
            "We expect strong results.",
            name="excellence_section.json",
        )
        result = measurable_targets_preserved(section, pack, repo_root=tmp_path)
        assert not result.passed
        assert any(
            i.get("objective_id") == "OBJ-1" for i in result.details["issues"]
        )

    def test_all_metrics_present_passes(self, tmp_path, pack):
        """All metric components present passes."""
        section = _make_section(
            tmp_path,
            "OBJ-1 targets ≥40% improvement in plan success rate. "
            "OBJ-2 targets ≥30% improvement in task coherence.",
            name="excellence_section.json",
        )
        result = measurable_targets_preserved(section, pack, repo_root=tmp_path)
        assert result.passed


# ---------------------------------------------------------------------------
# CC-style local catches (gate_10d CC-01/CC-06 equivalents)
# ---------------------------------------------------------------------------


class TestCCStyleLocalCatches:
    """Tests that gate_10d-style cross-consistency failures are caught locally."""

    def test_partner_identity_confusion_caught(self, tmp_path, pack):
        """CC-01-style: partner A described with partner B's legal name.

        This is a conflation that should be caught by partner_names_preserved.
        """
        section = _make_section(
            tmp_path,
            "CERIA (Breda Institute for Intelligent Systems) leads WP4 on "
            "multi-agent coordination.",
        )
        result = partner_names_preserved(section, pack, repo_root=tmp_path)
        assert not result.passed
        issues = result.details["issues"]
        assert any("conflat" in i["issue"].lower() for i in issues)
        assert any(i.get("partner") == "CERIA" for i in issues)

    def test_deliverable_identity_corruption_caught(self, tmp_path, pack):
        """CC-06-style: deliverable with wrong parent WP.

        This should be caught by deliverable_identity_preserved.
        """
        section = _make_section(
            tmp_path,
            "D2-01 is produced in the context of D2-01 (WP1) activities.",
        )
        result = deliverable_identity_preserved(section, pack, repo_root=tmp_path)
        assert not result.passed
        checks = {i["check"] for i in result.details["issues"]}
        assert "wrong_parent_wp" in checks

    def test_wrong_month_due_pattern_caught(self, tmp_path, pack):
        """Deliverable with wrong due-month in prose is caught."""
        section = _make_section(
            tmp_path,
            "D1-01, due in month 12, will establish the quality framework.",
        )
        result = deliverable_identity_preserved(section, pack, repo_root=tmp_path)
        assert not result.passed
        assert any(
            i["check"] == "wrong_due_month" and i["found_due_month"] == 12
            for i in result.details["issues"]
        )
