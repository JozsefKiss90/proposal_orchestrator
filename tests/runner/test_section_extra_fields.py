"""Tests for runner.decomposed_drafting.source_section_extra_fields (ticket 9).

Deterministic derivation of the section-specific ``extra_fields`` the assembler
requires (``section_assembler.REQUIRED_EXTRA_FIELDS``), sourced from the upstream
phase outputs.  These are what let Impact and Implementation draft and assemble
(they die at the assembler without them), and they must satisfy the
``impact_pathways_covered`` / ``implementation_coverage_complete`` gate rules.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from runner.decomposed_drafting import (
    DecomposedDraftingError,
    source_section_extra_fields,
    _IMPACT_ARCH_REL,
    _WP_STRUCTURE_REL,
    _GANTT_ARTIFACT_REL,
    _IMPL_ARCH_REL,
)


def _write(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _seed_impact(root: Path) -> None:
    _write(root / _IMPACT_ARCH_REL, {
        "impact_pathways": [
            {"pathway_id": "PWY-EI-01"},
            {"pathway_id": "PWY-EI-02"},
            {"id": "PWY-EI-03"},
        ],
        "dissemination_plan": {
            "activities": ["open-access papers", "communication to growers"],
        },
        "exploitation_plan": {"activities": ["demonstrator uptake"], "ipr_strategy": "open"},
    })


def _seed_impl(root: Path) -> None:
    _write(root / _WP_STRUCTURE_REL, {
        "work_packages": [{"wp_id": "WP1"}, {"wp_id": "WP2"}, {"id": "WP3"}],
    })
    _write(root / _GANTT_ARTIFACT_REL, {
        "milestones": [{"milestone_id": "MS1"}, {"id": "MS2"}],
    })
    _write(root / _IMPL_ARCH_REL, {"risk_register": [{"risk_id": "R1"}]})


class TestSourceSectionExtraFields:
    def test_excellence_needs_none(self, tmp_path: Path) -> None:
        assert source_section_extra_fields(tmp_path, "excellence") == {}

    def test_impact_refs_cover_all_pathways(self, tmp_path: Path) -> None:
        _seed_impact(tmp_path)
        ef = source_section_extra_fields(tmp_path, "impact")
        # Every pathway id present → impact_pathways_covered will pass.
        assert set(ef["impact_pathway_refs"]) == {
            "PWY-EI-01", "PWY-EI-02", "PWY-EI-03",
        }
        assert ef["dec_coverage"] == {
            "dissemination_addressed": True,
            "exploitation_addressed": True,
            "communication_addressed": True,  # 'communication' in dissemination
        }

    def test_implementation_fields(self, tmp_path: Path) -> None:
        _seed_impl(tmp_path)
        ef = source_section_extra_fields(tmp_path, "implementation")
        assert set(ef["wp_table_refs"]) == {"WP1", "WP2", "WP3"}
        assert set(ef["milestone_refs"]) == {"MS1", "MS2"}
        assert ef["gantt_ref"] == _GANTT_ARTIFACT_REL
        assert ef["risk_register_ref"] == _IMPL_ARCH_REL

    def test_communication_false_when_absent(self, tmp_path: Path) -> None:
        _write(tmp_path / _IMPACT_ARCH_REL, {
            "impact_pathways": [{"pathway_id": "PWY-01"}],
            "dissemination_plan": {"activities": ["open-access papers"]},
            "exploitation_plan": {"activities": ["uptake"]},
        })
        ef = source_section_extra_fields(tmp_path, "impact")
        assert ef["dec_coverage"]["communication_addressed"] is False

    def test_impact_fails_closed_when_arch_missing(self, tmp_path: Path) -> None:
        with pytest.raises(DecomposedDraftingError):
            source_section_extra_fields(tmp_path, "impact")

    def test_implementation_fails_closed_when_wp_missing(
        self, tmp_path: Path
    ) -> None:
        # gantt + impl present, wp_structure absent → fail closed BEFORE drafting.
        _write(tmp_path / _GANTT_ARTIFACT_REL, {"milestones": []})
        _write(tmp_path / _IMPL_ARCH_REL, {"risk_register": []})
        with pytest.raises(DecomposedDraftingError):
            source_section_extra_fields(tmp_path, "implementation")

    def test_unknown_slug_fails_closed(self, tmp_path: Path) -> None:
        with pytest.raises(DecomposedDraftingError):
            source_section_extra_fields(tmp_path, "budget")
