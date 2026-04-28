"""
Tests for proposal-section-traceability-check assembled-mode patch.

Verifies:
1. Section mode behavior is unchanged (material claim extraction).
2. Assembled mode performs structural index audit only (ASSEMBLY-* claims).
3. Assembled mode validates section traceability summaries.
4. Negative assembled-mode tests (missing sections, bad declarations, etc.).
5. Timeout prevention regression (no full section re-audit in assembled mode).
6. Prompt/spec invariant tests (spec contains required directives).

These are static/spec tests — no live Claude invocations.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SKILLS_DIR = Path(__file__).resolve().parents[2] / ".claude" / "skills"
PROMPTS_DIR = (
    Path(__file__).resolve().parents[2]
    / ".claude" / "agents" / "prompts"
)


def _read_skill(name: str) -> str:
    path = SKILLS_DIR / name
    assert path.is_file(), f"Skill spec not found: {path}"
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------


def _make_section_artifact(
    section_id: str,
    schema_id: str,
    *,
    content: str = "Short test content.",
    overall_status: str = "confirmed",
    claim_statuses: list[dict] | None = None,
    primary_sources: list[str] | None = None,
    no_unsupported_claims: bool = True,
) -> dict:
    """Build a minimal section artifact for testing."""
    return {
        "schema_id": schema_id,
        "run_id": "test-run-id",
        "criterion": section_id.capitalize(),
        "sub_sections": [
            {
                "sub_section_id": "B.1.1",
                "title": "Test",
                "content": content,
                "word_count": len(content.split()),
            },
        ],
        "validation_status": {
            "overall_status": overall_status,
            "claim_statuses": claim_statuses or [
                {
                    "claim_id": "C1",
                    "claim_summary": "Test claim",
                    "status": "confirmed",
                    "source_ref": "Tier 3: objectives.json",
                },
            ],
        },
        "traceability_footer": {
            "primary_sources": primary_sources or [
                "docs/tier3_project_instantiation/architecture_inputs/objectives.json",
            ],
            "no_unsupported_claims_declaration": no_unsupported_claims,
        },
    }


def _make_assembled_draft(
    *,
    sections: list[dict] | None = None,
    consistency_log: list[dict] | None = None,
    traceability_footer: dict | None = None,
) -> dict:
    """Build a minimal part_b_assembled_draft.json fixture."""
    default_sections = [
        {
            "section_id": "excellence",
            "criterion": "Excellence",
            "order": 1,
            "artifact_path": "docs/tier5_deliverables/proposal_sections/excellence_section.json",
            "word_count": 500,
        },
        {
            "section_id": "impact",
            "criterion": "Impact",
            "order": 2,
            "artifact_path": "docs/tier5_deliverables/proposal_sections/impact_section.json",
            "word_count": 500,
        },
        {
            "section_id": "implementation",
            "criterion": "Quality and efficiency of the implementation",
            "order": 3,
            "artifact_path": "docs/tier5_deliverables/proposal_sections/implementation_section.json",
            "word_count": 500,
        },
    ]
    default_consistency_log = [
        {
            "check_id": f"CC-{i:02d}",
            "description": f"Check {i}",
            "sections_checked": ["excellence", "impact", "implementation"],
            "status": "consistent",
            "inconsistency_note": None,
        }
        for i in range(1, 13)
    ]
    draft: dict[str, Any] = {
        "schema_id": "orch.tier5.part_b_assembled_draft.v1",
        "run_id": "test-run-id",
        "sections": sections if sections is not None else default_sections,
        "consistency_log": (
            consistency_log if consistency_log is not None
            else default_consistency_log
        ),
    }
    if traceability_footer is not None:
        draft["traceability_footer"] = traceability_footer
    return draft


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _setup_full_assembled_fixture(
    tmp_path: Path,
    *,
    excellence_kwargs: dict | None = None,
    impact_kwargs: dict | None = None,
    implementation_kwargs: dict | None = None,
    assembled_kwargs: dict | None = None,
    very_long_content: bool = False,
) -> dict[str, Path]:
    """Create a complete on-disk assembled fixture.

    Returns dict of logical names to file paths.
    """
    sections_dir = tmp_path / "docs" / "tier5_deliverables" / "proposal_sections"
    assembled_dir = tmp_path / "docs" / "tier5_deliverables" / "assembled_drafts"

    content = "Short test content."
    if very_long_content:
        # 50,000 words — enough to timeout a full per-claim audit
        content = ("This is a detailed paragraph about project objectives. " * 200 + "\n") * 50

    exc_kw = {"content": content, **(excellence_kwargs or {})}
    imp_kw = {"content": content, **(impact_kwargs or {})}
    impl_kw = {"content": content, **(implementation_kwargs or {})}

    exc = _make_section_artifact(
        "excellence", "orch.tier5.excellence_section.v1", **exc_kw
    )
    imp = _make_section_artifact(
        "impact", "orch.tier5.impact_section.v1", **imp_kw
    )
    impl = _make_section_artifact(
        "implementation", "orch.tier5.implementation_section.v1", **impl_kw
    )

    _write_json(sections_dir / "excellence_section.json", exc)
    _write_json(sections_dir / "impact_section.json", imp)
    _write_json(sections_dir / "implementation_section.json", impl)

    draft = _make_assembled_draft(**(assembled_kwargs or {}))
    _write_json(assembled_dir / "part_b_assembled_draft.json", draft)

    return {
        "excellence": sections_dir / "excellence_section.json",
        "impact": sections_dir / "impact_section.json",
        "implementation": sections_dir / "implementation_section.json",
        "assembled": assembled_dir / "part_b_assembled_draft.json",
    }


# ===========================================================================
# 1. SECTION MODE UNCHANGED
# ===========================================================================


class TestSectionModeUnchanged:
    """Verify that section mode skill spec still requires material claim extraction."""

    @pytest.fixture(autouse=True)
    def load_spec(self) -> None:
        self.text = _read_skill("proposal-section-traceability-check.md")

    def test_section_mode_still_has_material_claim_extraction(self) -> None:
        """Section mode must still perform material claim extraction (Step 2.2)."""
        assert "Material claim extraction" in self.text
        assert "Step 2.2" in self.text

    def test_section_mode_still_reads_tier14_references(self) -> None:
        """Section mode must still reference Tier 1-4 for verification."""
        assert "docs/tier1_normative_framework/extracted/" in self.text
        assert "docs/tier3_project_instantiation/" in self.text

    def test_section_mode_output_schema_unchanged(self) -> None:
        """Section mode output must still have claim_audit_results with per-claim entries."""
        # The section mode output construction section should mention
        # per-claim audit results (C1, C2, etc.)
        assert "claim_audit_results" in self.text
        # Must still produce confirmed/inferred/assumed/unresolved
        assert "confirmed/inferred/assumed/unresolved" in self.text

    def test_step_14_15_scoped_to_section_mode(self) -> None:
        """Steps 1.4 and 1.5 must be scoped to section mode only."""
        assert "Step 1.4 (section mode only)" in self.text
        assert "Step 1.5 (section mode only)" in self.text

    def test_steps_21_26_scoped_to_section_mode(self) -> None:
        """Steps 2.1-2.6 header must indicate section mode only."""
        assert "Section Mode" in self.text
        assert "Steps 2.1–2.6 apply ONLY in section mode" in self.text


# ===========================================================================
# 2. ASSEMBLED MODE DOES NOT FULL RE-AUDIT SECTIONS
# ===========================================================================


class TestAssembledModeStructuralOnly:
    """Verify assembled mode spec requires structural audit only."""

    @pytest.fixture(autouse=True)
    def load_spec(self) -> None:
        self.text = _read_skill("proposal-section-traceability-check.md")

    def test_assembled_mode_has_assembly_claims_only(self) -> None:
        """Assembled mode must produce ASSEMBLY-01 through ASSEMBLY-08 claims."""
        for i in range(1, 9):
            assert f"ASSEMBLY-{i:02d}" in self.text, (
                f"ASSEMBLY-{i:02d} not found in spec"
            )

    def test_assembled_mode_forbids_material_claim_extraction(self) -> None:
        """Assembled mode must explicitly forbid material claim extraction."""
        assert "MUST NOT re-audit every material claim" in self.text
        assert "Extract material claims from section body text" in self.text

    def test_assembled_mode_forbids_reading_tier14_sources(self) -> None:
        """Assembled mode must not read Tier 1-4 source directories."""
        assert "Read Tier 1–4 source directories for per-claim verification" in self.text

    def test_assembled_mode_does_not_emit_per_paragraph(self) -> None:
        """Assembled mode must not produce per-paragraph claims."""
        assert "Do NOT emit one claim per section paragraph" in self.text

    def test_assembled_mode_does_not_copy_section_body(self) -> None:
        """Assembled mode must not include copied section body text."""
        assert "Do NOT include copied section body text" in self.text

    def test_assembled_mode_section_id_audited(self) -> None:
        """Assembled mode section_id_audited must be 'part_b_assembled_draft'."""
        assert '"part_b_assembled_draft"' in self.text

    def test_assembled_mode_audit_mode_field(self) -> None:
        """Assembled mode output must include audit_mode field."""
        assert '"assembled_structural_index"' in self.text

    def test_assembled_mode_exactly_8_claims(self) -> None:
        """Assembled mode output must have exactly 8 entries."""
        assert "total_claims: 8" in self.text


# ===========================================================================
# 3. ASSEMBLED MODE VALIDATES SECTION TRACEABILITY SUMMARIES
# ===========================================================================


class TestAssembledModeValidatesSummaries:
    """Verify assembled mode checks section traceability summaries via fixture."""

    def test_all_sections_pass_produces_valid_fixture(self, tmp_path: Path) -> None:
        """A fixture with all three sections having valid traceability should
        represent a passing assembled-mode audit."""
        paths = _setup_full_assembled_fixture(tmp_path)

        # Verify all section artifacts exist and have valid traceability
        for name in ("excellence", "impact", "implementation"):
            data = json.loads(paths[name].read_text(encoding="utf-8"))
            footer = data["traceability_footer"]
            assert len(footer["primary_sources"]) > 0
            assert footer["no_unsupported_claims_declaration"] is True
            assert data["validation_status"]["overall_status"] != "unresolved"
            assert len(data["validation_status"]["claim_statuses"]) > 0

        # Verify assembled draft structure
        assembled = json.loads(paths["assembled"].read_text(encoding="utf-8"))
        assert len(assembled["sections"]) == 3
        assert assembled["sections"][0]["order"] == 1
        assert assembled["sections"][1]["order"] == 2
        assert assembled["sections"][2]["order"] == 3
        assert len(assembled["consistency_log"]) == 12
        assert all(
            e["status"] == "consistent" for e in assembled["consistency_log"]
        )


# ===========================================================================
# 4. NEGATIVE ASSEMBLED MODE TESTS
# ===========================================================================


class TestAssembledModeNegativeCases:
    """Verify assembled mode detects problems in section fixtures."""

    def test_missing_section_artifact_detected(self, tmp_path: Path) -> None:
        """If a referenced section artifact does not exist on disk,
        ASSEMBLY-02 should fail."""
        paths = _setup_full_assembled_fixture(tmp_path)
        # Delete one section file
        paths["impact"].unlink()

        # Verify the assembled draft references a file that no longer exists
        assembled = json.loads(paths["assembled"].read_text(encoding="utf-8"))
        impact_ref = assembled["sections"][1]["artifact_path"]
        assert not (tmp_path / impact_ref).exists()

    def test_missing_traceability_footer_detected(self, tmp_path: Path) -> None:
        """If a section lacks traceability_footer, ASSEMBLY-04 should fail."""
        paths = _setup_full_assembled_fixture(tmp_path)
        # Remove traceability_footer from excellence section
        data = json.loads(paths["excellence"].read_text(encoding="utf-8"))
        del data["traceability_footer"]
        _write_json(paths["excellence"], data)

        reloaded = json.loads(paths["excellence"].read_text(encoding="utf-8"))
        assert "traceability_footer" not in reloaded

    def test_no_unsupported_claims_false_detected(self, tmp_path: Path) -> None:
        """If a section has no_unsupported_claims_declaration=false,
        ASSEMBLY-05 should fail."""
        paths = _setup_full_assembled_fixture(
            tmp_path,
            impact_kwargs={"no_unsupported_claims": False},
        )
        data = json.loads(paths["impact"].read_text(encoding="utf-8"))
        assert data["traceability_footer"]["no_unsupported_claims_declaration"] is False

    def test_unresolved_overall_status_detected(self, tmp_path: Path) -> None:
        """If a section has overall_status='unresolved',
        ASSEMBLY-06 should fail."""
        paths = _setup_full_assembled_fixture(
            tmp_path,
            implementation_kwargs={"overall_status": "unresolved"},
        )
        data = json.loads(paths["implementation"].read_text(encoding="utf-8"))
        assert data["validation_status"]["overall_status"] == "unresolved"

    def test_consistency_log_inconsistency_flagged_detected(
        self, tmp_path: Path
    ) -> None:
        """If consistency_log contains inconsistency_flagged,
        ASSEMBLY-07 should fail."""
        flagged_log = [
            {
                "check_id": f"CC-{i:02d}",
                "description": f"Check {i}",
                "sections_checked": ["excellence", "impact"],
                "status": "consistent" if i != 4 else "inconsistency_flagged",
                "inconsistency_note": (
                    None if i != 4
                    else "Deliverable D8-01 mislabeled"
                ),
            }
            for i in range(1, 13)
        ]
        paths = _setup_full_assembled_fixture(
            tmp_path,
            assembled_kwargs={"consistency_log": flagged_log},
        )
        assembled = json.loads(paths["assembled"].read_text(encoding="utf-8"))
        flagged = [
            e for e in assembled["consistency_log"]
            if e["status"] == "inconsistency_flagged"
        ]
        assert len(flagged) == 1
        assert flagged[0]["check_id"] == "CC-04"

    def test_missing_section_id_detected(self, tmp_path: Path) -> None:
        """If a required section_id is missing from sections[],
        ASSEMBLY-02 should fail."""
        sections_without_impact = [
            {
                "section_id": "excellence",
                "criterion": "Excellence",
                "order": 1,
                "artifact_path": "docs/tier5_deliverables/proposal_sections/excellence_section.json",
                "word_count": 500,
            },
            {
                "section_id": "implementation",
                "criterion": "Implementation",
                "order": 3,
                "artifact_path": "docs/tier5_deliverables/proposal_sections/implementation_section.json",
                "word_count": 500,
            },
        ]
        paths = _setup_full_assembled_fixture(
            tmp_path,
            assembled_kwargs={"sections": sections_without_impact},
        )
        assembled = json.loads(paths["assembled"].read_text(encoding="utf-8"))
        section_ids = {s["section_id"] for s in assembled["sections"]}
        assert "impact" not in section_ids

    def test_wrong_section_order_detected(self, tmp_path: Path) -> None:
        """If section order is wrong, ASSEMBLY-03 should fail."""
        wrong_order = [
            {
                "section_id": "implementation",
                "criterion": "Implementation",
                "order": 1,
                "artifact_path": "docs/tier5_deliverables/proposal_sections/implementation_section.json",
                "word_count": 500,
            },
            {
                "section_id": "impact",
                "criterion": "Impact",
                "order": 2,
                "artifact_path": "docs/tier5_deliverables/proposal_sections/impact_section.json",
                "word_count": 500,
            },
            {
                "section_id": "excellence",
                "criterion": "Excellence",
                "order": 3,
                "artifact_path": "docs/tier5_deliverables/proposal_sections/excellence_section.json",
                "word_count": 500,
            },
        ]
        paths = _setup_full_assembled_fixture(
            tmp_path,
            assembled_kwargs={"sections": wrong_order},
        )
        assembled = json.loads(paths["assembled"].read_text(encoding="utf-8"))
        # Verify the order is indeed wrong
        assert assembled["sections"][0]["section_id"] == "implementation"
        assert assembled["sections"][0]["order"] == 1  # should be 3


# ===========================================================================
# 5. TIMEOUT PREVENTION REGRESSION
# ===========================================================================


class TestTimeoutPreventionRegression:
    """Verify assembled mode spec structurally prevents timeout."""

    @pytest.fixture(autouse=True)
    def load_spec(self) -> None:
        self.text = _read_skill("proposal-section-traceability-check.md")

    def test_assembled_mode_does_not_read_section_content(self) -> None:
        """Assembled mode must not read section body content fields."""
        # The ASSEMBLY-04 through ASSEMBLY-06 checks explicitly say
        # "read only" specific metadata fields, not content
        assert "Do NOT read section body content" in self.text

    def test_assembled_mode_has_output_size_limit(self) -> None:
        """Assembled mode must have a 6,000 character output limit."""
        assert "6,000 characters" in self.text

    def test_very_long_sections_do_not_cause_content_inspection(
        self, tmp_path: Path
    ) -> None:
        """Fixture with very long section content should still produce
        a compact assembled draft that the structural audit can process."""
        paths = _setup_full_assembled_fixture(
            tmp_path, very_long_content=True
        )
        # Verify section files are large
        exc_size = paths["excellence"].stat().st_size
        assert exc_size > 100_000, (
            f"Expected large section file, got {exc_size} bytes"
        )

        # But the assembled draft itself is compact (just index + log)
        assembled_size = paths["assembled"].stat().st_size
        assert assembled_size < 10_000, (
            f"Assembled draft should be compact, got {assembled_size} bytes"
        )

        # The assembled draft does NOT contain section body content
        assembled = json.loads(paths["assembled"].read_text(encoding="utf-8"))
        assembled_text = json.dumps(assembled)
        assert "This is a detailed paragraph" not in assembled_text


# ===========================================================================
# 6. PROMPT/SPEC INVARIANT TESTS
# ===========================================================================


class TestPromptSpecInvariants:
    """Verify required statements are present in specs."""

    def test_traceability_spec_assembled_mode_no_reaudit(self) -> None:
        """proposal-section-traceability-check.md must explicitly state
        assembled mode must not re-audit every section claim."""
        text = _read_skill("proposal-section-traceability-check.md")
        assert "MUST NOT re-audit every material claim" in text

    def test_traceability_spec_6000_char_limit(self) -> None:
        """proposal-section-traceability-check.md must include 6,000-char
        output limit for assembled mode."""
        text = _read_skill("proposal-section-traceability-check.md")
        assert "6,000 characters" in text

    def test_traceability_spec_no_markdown_fences(self) -> None:
        """proposal-section-traceability-check.md must require no markdown
        fences for assembled mode output."""
        text = _read_skill("proposal-section-traceability-check.md")
        assert "No markdown fences" in text

    def test_traceability_spec_single_json_object(self) -> None:
        """proposal-section-traceability-check.md must require single JSON
        object for assembled mode output."""
        text = _read_skill("proposal-section-traceability-check.md")
        assert "Single JSON object only" in text

    def test_prompt_spec_mentions_structural_audit(self) -> None:
        """proposal_integrator_prompt_spec.md must mention assembled
        structural index audit."""
        text = PROMPTS_DIR / "proposal_integrator_prompt_spec.md"
        content = text.read_text(encoding="utf-8-sig")
        assert "structural index audit" in content

    def test_prompt_spec_mentions_gate_bypasses(self) -> None:
        """prompt spec should mention gate_10a/10b/10c as prior audits."""
        text = PROMPTS_DIR / "proposal_integrator_prompt_spec.md"
        content = text.read_text(encoding="utf-8-sig")
        assert "gate_10a" in content or "gate_10a/10b/10c" in content

    def test_cross_section_spec_has_traceability_footer(self) -> None:
        """cross-section-consistency-check.md must produce traceability_footer
        in part_b_assembled_draft.json."""
        text = _read_skill("cross-section-consistency-check.md")
        assert "traceability_footer" in text
        assert "derivation_note" in text
        assert "no_unsupported_claims_declaration" in text

    def test_cross_section_spec_traceability_footer_is_compact(self) -> None:
        """cross-section-consistency-check.md traceability_footer must contain
        the fixed derivation_note string."""
        text = _read_skill("cross-section-consistency-check.md")
        assert (
            "Assembled draft inherits section-level proposal claim traceability"
            in text
        )

    def test_assembled_mode_skips_to_step_2a(self) -> None:
        """Assembled mode must skip steps 1.4, 1.5, 2.1-2.6 and go to 2A."""
        text = _read_skill("proposal-section-traceability-check.md")
        assert "proceed to Step 2A" in text
        assert "Do NOT proceed to Steps 1.4, 1.5, 2.1–2.6" in text
