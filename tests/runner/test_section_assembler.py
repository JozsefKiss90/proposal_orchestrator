"""Tests for runner.section_assembler — the deterministic section assembler.

Covers the C2 roster component (CLAUDE.md §17.5.3, ticket 4):
  - the byte-equal replay check ``assembler(drafts) == section_json`` that
    makes "no synthesis" true by construction (the milestone CI home),
  - verbatim carry of claim_statuses / overall_status / declaration,
  - derivation of *only* word_count and the source_refs union,
  - additive-optional page_estimate + section-specific extra_fields passthrough,
  - fail-closed behavior on every malformed / mismatched input,
  - registration + invocation through the deterministic-component substrate.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from runner.deterministic_components import COMPONENT_REGISTRY, invoke_component
from runner.section_assembler import (
    PROPOSAL_SECTIONS_REL,
    SECTION_DRAFTS_ROOT_REL,
    SectionAssemblerError,
    assemble_section,
)

RUN_ID = "run-assembler-1"


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------


def _drafts_dir(repo_root: Path, slug: str) -> Path:
    d = repo_root / SECTION_DRAFTS_ROOT_REL / slug
    d.mkdir(parents=True, exist_ok=True)
    return d


def _write(path: Path, obj: dict[str, Any]) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def _excellence_spine(**overrides: Any) -> dict[str, Any]:
    spine = {
        "schema_id": "orch.tier5.excellence_section.v1",
        "run_id": RUN_ID,
        "criterion": "Excellence",
        "sub_section_order": ["B.1.1", "B.1.2"],
        "overall_status": "confirmed",
        "no_unsupported_claims_declaration": True,
    }
    spine.update(overrides)
    return spine


def _draft_b11(**overrides: Any) -> dict[str, Any]:
    draft = {
        "sub_section_id": "B.1.1",
        "title": "Objectives and ambition",
        "content": "Alpha beta gamma delta epsilon.",  # 5 words
        "claim_statuses": [
            {
                "claim_id": "CS-01",
                "claim_summary": "OBJ-1 target",
                "status": "confirmed",
                "source_ref": "tier3/objectives.json -> OBJ-1",
            },
        ],
        "source_refs": [
            {"tier": 3, "source_path": "docs/tier3/objectives.json"},
            {"tier": 2, "source_path": "docs/tier2b/scope_requirements.json"},
        ],
    }
    draft.update(overrides)
    return draft


def _draft_b12(**overrides: Any) -> dict[str, Any]:
    draft = {
        "sub_section_id": "B.1.2",
        "title": "Methodology",
        "content": "One two three.",  # 3 words
        "claim_statuses": [
            {
                "claim_id": "CS-02",
                "claim_summary": "WP structure",
                "status": "inferred",
                "source_ref": "tier4/wp_structure.json",
            },
        ],
        "source_refs": [
            # Duplicate of a B.1.1 ref (must be de-duped in the union) plus a new one.
            {"tier": 3, "source_path": "docs/tier3/objectives.json"},
            {"tier": 4, "source_path": "docs/tier4/wp_structure.json"},
        ],
    }
    draft.update(overrides)
    return draft


def _seed_excellence(repo_root: Path) -> None:
    d = _drafts_dir(repo_root, "excellence")
    _write(d / "section_spine.json", _excellence_spine())
    _write(d / "B.1.1.draft.json", _draft_b11())
    _write(d / "B.1.2.draft.json", _draft_b12())


# ---------------------------------------------------------------------------
# The byte-equal CI check — "assembler(drafts) == section_json"
# ---------------------------------------------------------------------------


def _expected_excellence_artifact() -> dict[str, Any]:
    """The section JSON fully determined by the fixture drafts + spine.

    Mirrors the assembler's field order exactly so a serialization of this
    dict is byte-identical to the assembler's output.
    """
    return {
        "schema_id": "orch.tier5.excellence_section.v1",
        "run_id": RUN_ID,
        "criterion": "Excellence",
        "sub_sections": [
            {
                "sub_section_id": "B.1.1",
                "title": "Objectives and ambition",
                "content": "Alpha beta gamma delta epsilon.",
                "word_count": 5,
            },
            {
                "sub_section_id": "B.1.2",
                "title": "Methodology",
                "content": "One two three.",
                "word_count": 3,
            },
        ],
        "validation_status": {
            "overall_status": "confirmed",
            "claim_statuses": [
                {
                    "claim_id": "CS-01",
                    "claim_summary": "OBJ-1 target",
                    "status": "confirmed",
                    "source_ref": "tier3/objectives.json -> OBJ-1",
                },
                {
                    "claim_id": "CS-02",
                    "claim_summary": "WP structure",
                    "status": "inferred",
                    "source_ref": "tier4/wp_structure.json",
                },
            ],
        },
        "traceability_footer": {
            "primary_sources": [
                {"tier": 2, "source_path": "docs/tier2b/scope_requirements.json"},
                {"tier": 3, "source_path": "docs/tier3/objectives.json"},
                {"tier": 4, "source_path": "docs/tier4/wp_structure.json"},
            ],
            "no_unsupported_claims_declaration": True,
        },
    }


class TestByteEqualReplay:
    def test_assembler_output_is_byte_equal_to_expected_section_json(
        self, tmp_path: Path
    ) -> None:
        """The composed section JSON is byte-for-byte the mechanical
        composition of its drafts — the anti-synthesis guarantee."""
        _seed_excellence(tmp_path)

        out_path = assemble_section(RUN_ID, tmp_path, "excellence")
        produced = out_path.read_bytes()

        expected = json.dumps(
            _expected_excellence_artifact(), indent=2, ensure_ascii=False
        ).encode("utf-8")

        assert produced == expected

    def test_assembler_is_idempotent(self, tmp_path: Path) -> None:
        """Re-running on the same drafts yields byte-identical output."""
        _seed_excellence(tmp_path)

        first = assemble_section(RUN_ID, tmp_path, "excellence").read_bytes()
        second = assemble_section(RUN_ID, tmp_path, "excellence").read_bytes()

        assert first == second

    def test_no_content_beyond_drafts(self, tmp_path: Path) -> None:
        """Every sub-section content in the output originates in a draft —
        the assembler authors no prose."""
        _seed_excellence(tmp_path)
        out = json.loads(
            assemble_section(RUN_ID, tmp_path, "excellence").read_text("utf-8")
        )
        draft_contents = {_draft_b11()["content"], _draft_b12()["content"]}
        for sub in out["sub_sections"]:
            assert sub["content"] in draft_contents


# ---------------------------------------------------------------------------
# Verbatim carry
# ---------------------------------------------------------------------------


class TestVerbatimCarry:
    def test_claim_statuses_concatenated_in_spine_order(self, tmp_path: Path) -> None:
        _seed_excellence(tmp_path)
        out = json.loads(
            assemble_section(RUN_ID, tmp_path, "excellence").read_text("utf-8")
        )
        ids = [c["claim_id"] for c in out["validation_status"]["claim_statuses"]]
        assert ids == ["CS-01", "CS-02"]

    def test_claim_status_objects_are_unchanged(self, tmp_path: Path) -> None:
        """A status field is carried verbatim (the assembler never re-judges)."""
        d = _drafts_dir(tmp_path, "excellence")
        _write(d / "section_spine.json", _excellence_spine(overall_status="assumed"))
        _write(
            d / "B.1.1.draft.json",
            _draft_b11(
                claim_statuses=[
                    {
                        "claim_id": "CS-A",
                        "claim_summary": "host coefficient",
                        "status": "assumed",
                        "source_ref": "working_assumptions.json -> host",
                    }
                ]
            ),
        )
        _write(d / "B.1.2.draft.json", _draft_b12())

        out = json.loads(
            assemble_section(RUN_ID, tmp_path, "excellence").read_text("utf-8")
        )
        assert out["validation_status"]["overall_status"] == "assumed"
        first = out["validation_status"]["claim_statuses"][0]
        assert first["status"] == "assumed"
        assert first["source_ref"] == "working_assumptions.json -> host"

    def test_declaration_carried_from_spine(self, tmp_path: Path) -> None:
        d = _drafts_dir(tmp_path, "excellence")
        _write(
            d / "section_spine.json",
            _excellence_spine(no_unsupported_claims_declaration=False),
        )
        _write(d / "B.1.1.draft.json", _draft_b11())
        _write(d / "B.1.2.draft.json", _draft_b12())
        out = json.loads(
            assemble_section(RUN_ID, tmp_path, "excellence").read_text("utf-8")
        )
        assert out["traceability_footer"]["no_unsupported_claims_declaration"] is False


# ---------------------------------------------------------------------------
# Derived fields (word_count + source_refs union only)
# ---------------------------------------------------------------------------


class TestDerivedFields:
    def test_word_count_is_derived(self, tmp_path: Path) -> None:
        _seed_excellence(tmp_path)
        out = json.loads(
            assemble_section(RUN_ID, tmp_path, "excellence").read_text("utf-8")
        )
        counts = {s["sub_section_id"]: s["word_count"] for s in out["sub_sections"]}
        assert counts == {"B.1.1": 5, "B.1.2": 3}

    def test_source_refs_union_deduped_and_sorted(self, tmp_path: Path) -> None:
        _seed_excellence(tmp_path)
        out = json.loads(
            assemble_section(RUN_ID, tmp_path, "excellence").read_text("utf-8")
        )
        refs = out["traceability_footer"]["primary_sources"]
        # 4 draft refs → 3 unique (objectives.json appears in both drafts),
        # sorted by (tier, source_path).
        assert refs == [
            {"tier": 2, "source_path": "docs/tier2b/scope_requirements.json"},
            {"tier": 3, "source_path": "docs/tier3/objectives.json"},
            {"tier": 4, "source_path": "docs/tier4/wp_structure.json"},
        ]

    def test_page_estimate_carried_when_present(self, tmp_path: Path) -> None:
        d = _drafts_dir(tmp_path, "excellence")
        _write(d / "section_spine.json", _excellence_spine())
        _write(d / "B.1.1.draft.json", _draft_b11(page_estimate=2))
        _write(d / "B.1.2.draft.json", _draft_b12())
        out = json.loads(
            assemble_section(RUN_ID, tmp_path, "excellence").read_text("utf-8")
        )
        b11 = next(s for s in out["sub_sections"] if s["sub_section_id"] == "B.1.1")
        b12 = next(s for s in out["sub_sections"] if s["sub_section_id"] == "B.1.2")
        assert b11["page_estimate"] == 2
        assert "page_estimate" not in b12  # optional: omitted when absent


# ---------------------------------------------------------------------------
# Section-specific passthrough (Impact / Implementation extras)
# ---------------------------------------------------------------------------


class TestExtraFieldsPassthrough:
    def test_impact_extra_fields_carried_at_top_level(self, tmp_path: Path) -> None:
        d = _drafts_dir(tmp_path, "impact")
        _write(
            d / "section_spine.json",
            {
                "schema_id": "orch.tier5.impact_section.v1",
                "run_id": RUN_ID,
                "criterion": "Impact",
                "sub_section_order": ["B.2.1"],
                "overall_status": "confirmed",
                "no_unsupported_claims_declaration": True,
                "extra_fields": {
                    "dec_coverage": {"dissemination": True, "exploitation": True},
                    "impact_pathway_refs": ["IMP-01", "IMP-02"],
                },
            },
        )
        _write(
            d / "B.2.1.draft.json",
            {
                "sub_section_id": "B.2.1",
                "title": "Pathways towards impact",
                "content": "Pathway prose.",
                "claim_statuses": [],
                "source_refs": [{"tier": 2, "source_path": "docs/tier2b/x.json"}],
            },
        )
        out = json.loads(
            assemble_section(RUN_ID, tmp_path, "impact").read_text("utf-8")
        )
        assert out["dec_coverage"] == {"dissemination": True, "exploitation": True}
        assert out["impact_pathway_refs"] == ["IMP-01", "IMP-02"]

    def test_extra_fields_cannot_shadow_core_field(self, tmp_path: Path) -> None:
        d = _drafts_dir(tmp_path, "impact")
        _write(
            d / "section_spine.json",
            {
                "schema_id": "orch.tier5.impact_section.v1",
                "run_id": RUN_ID,
                "criterion": "Impact",
                "sub_section_order": ["B.2.1"],
                "overall_status": "confirmed",
                "no_unsupported_claims_declaration": True,
                "extra_fields": {"validation_status": {"tampered": True}},
            },
        )
        _write(
            d / "B.2.1.draft.json",
            {
                "sub_section_id": "B.2.1",
                "title": "Pathways",
                "content": "Prose.",
                "claim_statuses": [],
                "source_refs": [],
            },
        )
        with pytest.raises(SectionAssemblerError, match="may not shadow"):
            assemble_section(RUN_ID, tmp_path, "impact")


# ---------------------------------------------------------------------------
# Section-specific required fields (§16.4 structural compliance)
# ---------------------------------------------------------------------------


def _impact_draft() -> dict[str, Any]:
    return {
        "sub_section_id": "B.2.1",
        "title": "Pathways",
        "content": "Prose.",
        "claim_statuses": [],
        "source_refs": [],
    }


class TestRequiredExtraFields:
    def test_impact_missing_required_extras_fails(self, tmp_path: Path) -> None:
        """An Impact spine without the schema-required extras fails closed
        rather than writing a non-compliant artifact."""
        d = _drafts_dir(tmp_path, "impact")
        _write(
            d / "section_spine.json",
            {
                "schema_id": "orch.tier5.impact_section.v1",
                "run_id": RUN_ID,
                "criterion": "Impact",
                "sub_section_order": ["B.2.1"],
                "overall_status": "confirmed",
                "no_unsupported_claims_declaration": True,
                # No extra_fields → dec_coverage + impact_pathway_refs missing.
            },
        )
        _write(d / "B.2.1.draft.json", _impact_draft())
        with pytest.raises(SectionAssemblerError, match="schema-required field"):
            assemble_section(RUN_ID, tmp_path, "impact")

    def test_impact_with_required_extras_succeeds(self, tmp_path: Path) -> None:
        d = _drafts_dir(tmp_path, "impact")
        _write(
            d / "section_spine.json",
            {
                "schema_id": "orch.tier5.impact_section.v1",
                "run_id": RUN_ID,
                "criterion": "Impact",
                "sub_section_order": ["B.2.1"],
                "overall_status": "confirmed",
                "no_unsupported_claims_declaration": True,
                "extra_fields": {
                    "impact_pathway_refs": ["IMP-01"],
                    "dec_coverage": {"dissemination_addressed": True},
                },
            },
        )
        _write(d / "B.2.1.draft.json", _impact_draft())
        out = json.loads(
            assemble_section(RUN_ID, tmp_path, "impact").read_text("utf-8")
        )
        assert out["impact_pathway_refs"] == ["IMP-01"]

    def test_implementation_partial_required_extras_fails(
        self, tmp_path: Path
    ) -> None:
        """Only some of the four required Implementation extras present → fail,
        naming the missing ones."""
        d = _drafts_dir(tmp_path, "implementation")
        _write(
            d / "section_spine.json",
            {
                "schema_id": "orch.tier5.implementation_section.v1",
                "run_id": RUN_ID,
                "criterion": "Quality and efficiency of the implementation",
                "sub_section_order": ["B.3.1"],
                "overall_status": "confirmed",
                "no_unsupported_claims_declaration": True,
                "extra_fields": {"wp_table_refs": ["WP1"], "gantt_ref": "gantt.json"},
                # milestone_refs + risk_register_ref missing.
            },
        )
        _write(
            d / "B.3.1.draft.json",
            {
                "sub_section_id": "B.3.1",
                "title": "Work plan",
                "content": "Prose.",
                "claim_statuses": [],
                "source_refs": [],
            },
        )
        with pytest.raises(SectionAssemblerError, match="milestone_refs"):
            assemble_section(RUN_ID, tmp_path, "implementation")

    def test_excellence_needs_no_extras(self, tmp_path: Path) -> None:
        """Excellence has no schema-required extras — assembles with none."""
        _seed_excellence(tmp_path)
        # Reuses the base fixture (no extra_fields) — must succeed.
        out = assemble_section(RUN_ID, tmp_path, "excellence")
        assert out.is_file()


# ---------------------------------------------------------------------------
# Fail-closed behavior
# ---------------------------------------------------------------------------


class TestFailClosed:
    def test_unknown_slug(self, tmp_path: Path) -> None:
        with pytest.raises(SectionAssemblerError, match="Unknown section slug"):
            assemble_section(RUN_ID, tmp_path, "budget")

    def test_missing_drafts_dir(self, tmp_path: Path) -> None:
        with pytest.raises(SectionAssemblerError, match="drafts directory not found"):
            assemble_section(RUN_ID, tmp_path, "excellence")

    def test_missing_spine(self, tmp_path: Path) -> None:
        d = _drafts_dir(tmp_path, "excellence")
        _write(d / "B.1.1.draft.json", _draft_b11())
        with pytest.raises(SectionAssemblerError, match="section spine not found"):
            assemble_section(RUN_ID, tmp_path, "excellence")

    def test_run_id_mismatch_is_stale(self, tmp_path: Path) -> None:
        _seed_excellence(tmp_path)
        with pytest.raises(SectionAssemblerError, match="stale drafts"):
            assemble_section("a-different-run", tmp_path, "excellence")

    def test_schema_id_mismatch(self, tmp_path: Path) -> None:
        d = _drafts_dir(tmp_path, "excellence")
        _write(
            d / "section_spine.json",
            _excellence_spine(schema_id="orch.tier5.impact_section.v1"),
        )
        _write(d / "B.1.1.draft.json", _draft_b11())
        _write(d / "B.1.2.draft.json", _draft_b12())
        with pytest.raises(SectionAssemblerError, match="does not match the expected"):
            assemble_section(RUN_ID, tmp_path, "excellence")

    def test_declared_sub_section_missing_draft(self, tmp_path: Path) -> None:
        d = _drafts_dir(tmp_path, "excellence")
        _write(d / "section_spine.json", _excellence_spine())
        _write(d / "B.1.1.draft.json", _draft_b11())  # B.1.2 missing
        with pytest.raises(SectionAssemblerError, match="no.*draft is present"):
            assemble_section(RUN_ID, tmp_path, "excellence")

    def test_undeclared_draft_on_disk(self, tmp_path: Path) -> None:
        d = _drafts_dir(tmp_path, "excellence")
        _write(d / "section_spine.json", _excellence_spine())
        _write(d / "B.1.1.draft.json", _draft_b11())
        _write(d / "B.1.2.draft.json", _draft_b12())
        _write(d / "B.1.3.draft.json", _draft_b12(sub_section_id="B.1.3"))
        with pytest.raises(SectionAssemblerError, match="not declared in spine"):
            assemble_section(RUN_ID, tmp_path, "excellence")

    def test_duplicate_in_sub_section_order(self, tmp_path: Path) -> None:
        d = _drafts_dir(tmp_path, "excellence")
        _write(
            d / "section_spine.json",
            _excellence_spine(sub_section_order=["B.1.1", "B.1.1"]),
        )
        _write(d / "B.1.1.draft.json", _draft_b11())
        with pytest.raises(SectionAssemblerError, match="contains duplicates"):
            assemble_section(RUN_ID, tmp_path, "excellence")

    def test_bad_page_estimate_type(self, tmp_path: Path) -> None:
        d = _drafts_dir(tmp_path, "excellence")
        _write(d / "section_spine.json", _excellence_spine())
        _write(d / "B.1.1.draft.json", _draft_b11(page_estimate="two"))
        _write(d / "B.1.2.draft.json", _draft_b12())
        with pytest.raises(SectionAssemblerError, match="page_estimate.*integer"):
            assemble_section(RUN_ID, tmp_path, "excellence")


# ---------------------------------------------------------------------------
# Deterministic-component substrate integration
# ---------------------------------------------------------------------------


class TestComponentRegistration:
    @pytest.mark.parametrize(
        "component_id",
        [
            "excellence_section_assembler",
            "impact_section_assembler",
            "implementation_section_assembler",
        ],
    )
    def test_registered(self, component_id: str) -> None:
        assert component_id in COMPONENT_REGISTRY

    def test_invoke_component_success_record(self, tmp_path: Path) -> None:
        _seed_excellence(tmp_path)
        record = invoke_component(
            "excellence_section_assembler", RUN_ID, tmp_path
        )
        assert record.status == "success"
        assert record.outputs_written == [
            f"{PROPOSAL_SECTIONS_REL}/excellence_section.json"
        ]
        assert (tmp_path / PROPOSAL_SECTIONS_REL / "excellence_section.json").is_file()

    def test_invoke_component_failure_record_on_missing_inputs(
        self, tmp_path: Path
    ) -> None:
        record = invoke_component(
            "excellence_section_assembler", RUN_ID, tmp_path
        )
        assert record.status == "failure"
        assert record.failure_reason


class TestSourceRefTierCoercion:
    """The assembler coerces a descriptive string tier ('Tier 2B') to its
    integer form.  The live drafter sometimes emits the string; re-drafting to
    fix it would waste the whole section's drafting quota, so the assembler
    normalises deterministically instead."""

    def test_string_tier_coerced_to_int(self) -> None:
        from runner.section_assembler import _coerce_tier
        assert _coerce_tier("Tier 2B") == 2
        assert _coerce_tier("2B") == 2
        assert _coerce_tier("Tier 2") == 2
        assert _coerce_tier("2") == 2

    def test_integer_tier_unchanged(self) -> None:
        # Byte-equal guarantee: an already-integer tier is identity.
        from runner.section_assembler import _coerce_tier
        for i in (1, 2, 3, 4):
            assert _coerce_tier(i) == i

    def test_uncoercible_tier_is_none(self) -> None:
        from runner.section_assembler import _coerce_tier
        assert _coerce_tier(None) is None
        assert _coerce_tier(True) is None
        assert _coerce_tier("no digits here") is None

    def test_source_ref_key_accepts_string_tier(self) -> None:
        from runner.section_assembler import _source_ref_key
        assert _source_ref_key(
            {"tier": "Tier 2B", "source_path": "docs/x.json"}
        ) == (2, "docs/x.json")

    def test_source_ref_key_rejects_uncoercible_tier(self) -> None:
        from runner.section_assembler import (
            _source_ref_key,
            SectionAssemblerError,
        )
        with pytest.raises(SectionAssemblerError):
            _source_ref_key({"tier": "none", "source_path": "docs/x.json"})
