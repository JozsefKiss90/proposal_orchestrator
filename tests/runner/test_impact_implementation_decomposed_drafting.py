"""Ticket 11 tracer bullet — Impact + Implementation decomposed drafting.

Extends the Excellence tracer bullet (ticket 7,
``test_excellence_decomposed_drafting.py``) to the two remaining criterion
sections.  It proves the milestone's central claim holds for all three sections:
**decomposition** (bounded per-sub-section calls at profile granularity, composed
by the deterministic assembler) produces full-length, traceable Impact and
Implementation sections that materially exceed the prior monolithic length
shortfall — with no chunked writer and no synthesis — and that carry the
section-specific ``extra_fields`` their gates require.

It also proves the ticket-11 gate wiring at the predicate level, on the real
assembled sections:

  * Impact-specific check (``impact_pathways_covered`` — pathway + DEC coverage)
    passes on the assembled Impact section.
  * Implementation-specific check (``implementation_coverage_complete`` — WP /
    Gantt / milestone / risk coverage) passes on the assembled Implementation
    section.
  * W1 (``assumed_claims_are_operator_declared``) covers Impact and
    Implementation, demonstrated both ways (β conscious green / α honest block),
    mirroring ticket 9's Excellence demonstration.
  * ``gate_10d`` ``cross_section_consistency`` is green across the three
    assembled sections.

The per-sub-section Claude call is stood in by a deterministic fake drafter so
the whole decompose→compose chain is exercised without a live model; the
assembler's byte-equal guarantee is re-confirmed on these realistic drafts.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from runner.assumption_applier import apply_assumptions
from runner.decomposed_drafting import draft_section_decomposed
from runner.phase8_canonical_pack import (
    CANONICAL_PACK_REL,
    build_phase8_canonical_reference_pack,
)
from runner.predicates import (
    assumed_claims_are_operator_declared,
    canonical_terms_preserved,
    cross_section_consistency,
    deliverable_identity_preserved,
    impact_pathways_covered,
    implementation_coverage_complete,
    measurable_targets_preserved,
    no_unresolved_material_claims,
    partner_names_preserved,
)
from runner.section_assembler import (
    PROPOSAL_SECTIONS_REL,
    SECTION_DRAFTS_ROOT_REL,
    assemble_section,
)
from runner.working_assumptions import WORKING_ASSUMPTIONS_REL

RUN_ID = "run-impact-impl-decomposed-1"

# Profile sub-sections per criterion (profile granularity, ticket 5).  Impact and
# Implementation mirror Excellence's decomposition; the assembler's
# REQUIRED_EXTRA_FIELDS enforce each section's schema-required extras.
_IMPACT_SUBS = [
    ("2.1", "Credibility of the measures to enhance career and skills"),
    ("2.2", "Credibility of the measures to communicate and disseminate"),
]
_IMPLEMENTATION_SUBS = [
    ("3.1", "Coherence and effectiveness of the work plan"),
    ("3.2", "Quality and appropriateness of infrastructure and resources"),
]
_EXCELLENCE_SUBS = [
    ("1.1", "Quality and pertinence of the objectives"),
    ("1.2", "Soundness of the proposed methodology"),
]

# The monolithic drafter's per-sub-section soft cap (chars) and whole-section
# response ceiling — the limits decomposition lifts (impact/implementation
# section-drafting specs, pre-ticket-11: ceilings of ~18-20 KB).
_MONOLITHIC_SUBSECTION_CAP = 2500
_MONOLITHIC_SECTION_CEILING = 20000

# Canonical paths the section-specific predicates cross-check against.
_IMPACT_ARCH_REL = (
    "docs/tier4_orchestration_state/phase_outputs"
    "/phase5_impact_architecture/impact_architecture.json"
)
_WP_STRUCTURE_REL = (
    "docs/tier4_orchestration_state/phase_outputs"
    "/phase3_wp_design/wp_structure.json"
)
_GANTT_REL = (
    "docs/tier4_orchestration_state/phase_outputs"
    "/phase4_gantt_milestones/gantt.json"
)

# Section-specific spine extra_fields (carried verbatim by the assembler; the
# assembler asserts their presence, the gate predicates validate their content).
_IMPACT_EXTRA_FIELDS: dict[str, Any] = {
    "impact_pathway_refs": ["IP-1", "IP-2"],
    "dec_coverage": {
        "dissemination_addressed": True,
        "exploitation_addressed": True,
        "communication_addressed": True,
    },
}
_IMPLEMENTATION_EXTRA_FIELDS: dict[str, Any] = {
    "wp_table_refs": ["WP1", "WP2"],
    "gantt_ref": _GANTT_REL,
    "milestone_refs": ["MS1", "MS2"],
    "risk_register_ref": (
        "docs/tier3_project_instantiation/architecture_inputs/risks.json"
    ),
}


# ---------------------------------------------------------------------------
# Seeding helpers
# ---------------------------------------------------------------------------


def _write(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def _seed_profile(repo_root: Path) -> None:
    """Seed a resolvable MSCA-PF profile with all three criteria's sub-sections."""
    _write(
        repo_root / "docs/tier3_project_instantiation/call_binding/selected_call.json",
        {"instrument_type": "MSCA-PF", "budget_regime": "unit_cost"},
    )

    sections: list[dict[str, Any]] = []
    for parent_id, criterion, subs, sub_type in (
        ("1", "Excellence", _EXCELLENCE_SUBS, "proposal_section"),
        ("2", "Impact", _IMPACT_SUBS, "proposal_section"),
        ("3", "Implementation", _IMPLEMENTATION_SUBS, "implementation_section"),
    ):
        sections.append({
            "section_id": parent_id,
            "section_name": criterion,
            "mandatory": True,
            "section_type": "criterion_section",
            "criterion": criterion,
        })
        for sid, name in subs:
            sections.append({
                "section_id": sid,
                "section_name": name,
                "mandatory": True,
                "section_type": sub_type,
                "criterion": criterion,
                "parent_section_id": parent_id,
                "field_requirements": [f"Describe {name.lower()}."],
            })

    _write(
        repo_root
        / "docs/tier2a_instrument_schemas/extracted/section_schema_registry.json",
        {"instruments": [
            {
                "instrument_type": "MSCA-PF",
                "part_b_page_limit_hard": 10,
                "sections": sections,
            }
        ]},
    )
    _write(
        repo_root
        / "docs/tier2a_instrument_schemas/extracted/instrument_registry.json",
        {"instruments": [
            {
                "instrument_type": "MSCA-PF",
                "budget_regime": "unit_cost",
                "phases_in_scope": [1, 2, 3, 4, 5, 6, 7, 8],
            }
        ]},
    )


def _seed_impact_architecture(repo_root: Path) -> None:
    """Seed the Phase-5 impact architecture with the two covered pathways."""
    _write(
        repo_root / _IMPACT_ARCH_REL,
        {"impact_pathways": [{"pathway_id": "IP-1"}, {"pathway_id": "IP-2"}]},
    )


def _seed_wp_structure(repo_root: Path) -> None:
    """Seed the Phase-3 WP structure with the two covered work packages."""
    _write(
        repo_root / _WP_STRUCTURE_REL,
        {"work_packages": [{"wp_id": "WP1"}, {"wp_id": "WP2"}]},
    )


def _declare(repo_root: Path, key: str, value: Any) -> None:
    _write(
        repo_root / WORKING_ASSUMPTIONS_REL,
        {
            "provenance_class": "manually_placed",
            "declarations": [
                {
                    "key": key,
                    "value": value,
                    "declared_by": "operator",
                    "declared_on": "2026-07-14",
                }
            ],
        },
    )


class _FakeDrafter:
    """A deterministic fake drafter that produces full-length prose, records the
    sequential context it was handed, and can inject a chosen claim status on a
    single *target* sub-section (all others draft a ``confirmed`` claim).

    ``mention`` strings are appended to every sub-section's content so a test can
    force canonical identifiers (e.g. objective IDs) to appear for the
    cross-section coverage checks.
    """

    def __init__(
        self,
        *,
        chars_per_sub: int = 4000,
        claim_prefix: str = "CS",
        mention: list[str] | None = None,
        special_sub: str | None = None,
        special_status: str = "confirmed",
        special_summary: str | None = None,
    ) -> None:
        self.chars_per_sub = chars_per_sub
        self.claim_prefix = claim_prefix
        self.mention = mention or []
        self.special_sub = special_sub
        self.special_status = special_status
        self.special_summary = special_summary
        self.calls: list[tuple[str, int]] = []  # (sub_id, num_prior_drafts)

    def __call__(
        self,
        sub: dict[str, Any],
        criterion: str,
        prior_drafts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        sub_id = sub["section_id"]
        self.calls.append((sub_id, len(prior_drafts)))
        sentence = f"Sub-section {sub_id} of {criterion} develops the argument in full. "
        content = (sentence * ((self.chars_per_sub // len(sentence)) + 1))[
            : self.chars_per_sub
        ]
        if self.mention:
            content = content + " " + " ".join(self.mention)
        # Only the target sub-section carries the special status; every other
        # sub-section is confirmed, so the section's worst-status is driven by
        # the single claim under test (mirrors the Excellence tracer bullet).
        if self.special_sub is not None and sub_id == self.special_sub:
            status = self.special_status
            summary = (
                self.special_summary
                if self.special_summary is not None
                else f"claim for {sub_id}"
            )
        else:
            status = "confirmed"
            summary = f"claim for {sub_id}"
        return {
            "content": content,
            "claim_statuses": [
                {
                    "claim_id": f"{self.claim_prefix}-{sub_id}",
                    "claim_summary": summary,
                    "status": status,
                    "source_ref": "tier3/architecture_inputs.json",
                }
            ],
            "source_refs": [
                {"tier": 3, "source_path": "docs/tier3/architecture_inputs.json"},
                {"tier": 2, "source_path": f"docs/tier2b/{sub_id}.json"},
            ],
        }


def _draft_and_assemble(
    repo_root: Path,
    slug: str,
    drafter: _FakeDrafter,
    extra_fields: dict[str, Any] | None,
) -> dict[str, Any]:
    """Run the decompose→compose chain for *slug* and return the section JSON."""
    draft_section_decomposed(
        RUN_ID, repo_root, slug, drafter=drafter, extra_fields=extra_fields
    )
    out = assemble_section(RUN_ID, repo_root, slug)
    return json.loads(out.read_text("utf-8"))


# ===========================================================================
# Impact: decompose → compose
# ===========================================================================


class TestImpactDecomposeThenCompose:
    def test_drafts_one_per_profile_sub_section(self, tmp_path: Path) -> None:
        _seed_profile(tmp_path)
        drafter = _FakeDrafter(claim_prefix="CI")
        draft_section_decomposed(
            RUN_ID, tmp_path, "impact",
            drafter=drafter, extra_fields=_IMPACT_EXTRA_FIELDS,
        )
        drafts_dir = tmp_path / SECTION_DRAFTS_ROOT_REL / "impact"
        assert (drafts_dir / "section_spine.json").is_file()
        draft_files = sorted(p.name for p in drafts_dir.glob("*.draft.json"))
        assert draft_files == ["2.1.draft.json", "2.2.draft.json"]

    def test_sequential_context_passed_between_calls(self, tmp_path: Path) -> None:
        _seed_profile(tmp_path)
        drafter = _FakeDrafter(claim_prefix="CI")
        draft_section_decomposed(
            RUN_ID, tmp_path, "impact",
            drafter=drafter, extra_fields=_IMPACT_EXTRA_FIELDS,
        )
        assert drafter.calls == [("2.1", 0), ("2.2", 1)]

    def test_assembles_to_full_length_section(self, tmp_path: Path) -> None:
        """The composed section materially exceeds the monolithic ceiling."""
        _seed_profile(tmp_path)
        section = _draft_and_assemble(
            tmp_path, "impact",
            _FakeDrafter(chars_per_sub=11000, claim_prefix="CI"),
            _IMPACT_EXTRA_FIELDS,
        )
        total_chars = sum(len(s["content"]) for s in section["sub_sections"])
        for s in section["sub_sections"]:
            assert len(s["content"]) > _MONOLITHIC_SUBSECTION_CAP
        assert total_chars > _MONOLITHIC_SECTION_CEILING
        assert len(section["sub_sections"]) == 2

    def test_extra_fields_and_traceability_carried(self, tmp_path: Path) -> None:
        _seed_profile(tmp_path)
        section = _draft_and_assemble(
            tmp_path, "impact", _FakeDrafter(claim_prefix="CI"),
            _IMPACT_EXTRA_FIELDS,
        )
        # Section-specific extras reached the artifact verbatim via the spine.
        assert section["impact_pathway_refs"] == ["IP-1", "IP-2"]
        assert section["dec_coverage"]["dissemination_addressed"] is True
        # Claims carried up, one per sub-section.
        claim_ids = [
            c["claim_id"] for c in section["validation_status"]["claim_statuses"]
        ]
        assert claim_ids == ["CI-2.1", "CI-2.2"]
        assert section["traceability_footer"]["primary_sources"]

    def test_byte_equal_replay_on_real_drafts(self, tmp_path: Path) -> None:
        _seed_profile(tmp_path)
        draft_section_decomposed(
            RUN_ID, tmp_path, "impact",
            drafter=_FakeDrafter(claim_prefix="CI"),
            extra_fields=_IMPACT_EXTRA_FIELDS,
        )
        first = assemble_section(RUN_ID, tmp_path, "impact").read_bytes()
        second = assemble_section(RUN_ID, tmp_path, "impact").read_bytes()
        assert first == second

    def test_impact_specific_check_passes(self, tmp_path: Path) -> None:
        """impact_pathways_covered (DEC + pathway coverage) passes on the
        assembled Impact section — ticket 11 item 3."""
        _seed_profile(tmp_path)
        _seed_impact_architecture(tmp_path)
        _draft_and_assemble(
            tmp_path, "impact", _FakeDrafter(claim_prefix="CI"),
            _IMPACT_EXTRA_FIELDS,
        )
        result = impact_pathways_covered(
            f"{PROPOSAL_SECTIONS_REL}/impact_section.json",
            _IMPACT_ARCH_REL,
            repo_root=tmp_path,
        )
        assert result.passed


# ===========================================================================
# Implementation: decompose → compose
# ===========================================================================


class TestImplementationDecomposeThenCompose:
    def test_drafts_one_per_profile_sub_section(self, tmp_path: Path) -> None:
        _seed_profile(tmp_path)
        drafter = _FakeDrafter(claim_prefix="CM")
        draft_section_decomposed(
            RUN_ID, tmp_path, "implementation",
            drafter=drafter, extra_fields=_IMPLEMENTATION_EXTRA_FIELDS,
        )
        drafts_dir = tmp_path / SECTION_DRAFTS_ROOT_REL / "implementation"
        assert (drafts_dir / "section_spine.json").is_file()
        draft_files = sorted(p.name for p in drafts_dir.glob("*.draft.json"))
        assert draft_files == ["3.1.draft.json", "3.2.draft.json"]

    def test_sequential_context_passed_between_calls(self, tmp_path: Path) -> None:
        _seed_profile(tmp_path)
        drafter = _FakeDrafter(claim_prefix="CM")
        draft_section_decomposed(
            RUN_ID, tmp_path, "implementation",
            drafter=drafter, extra_fields=_IMPLEMENTATION_EXTRA_FIELDS,
        )
        assert drafter.calls == [("3.1", 0), ("3.2", 1)]

    def test_assembles_to_full_length_section(self, tmp_path: Path) -> None:
        _seed_profile(tmp_path)
        section = _draft_and_assemble(
            tmp_path, "implementation",
            _FakeDrafter(chars_per_sub=11000, claim_prefix="CM"),
            _IMPLEMENTATION_EXTRA_FIELDS,
        )
        total_chars = sum(len(s["content"]) for s in section["sub_sections"])
        for s in section["sub_sections"]:
            assert len(s["content"]) > _MONOLITHIC_SUBSECTION_CAP
        assert total_chars > _MONOLITHIC_SECTION_CEILING
        assert len(section["sub_sections"]) == 2

    def test_extra_fields_and_traceability_carried(self, tmp_path: Path) -> None:
        _seed_profile(tmp_path)
        section = _draft_and_assemble(
            tmp_path, "implementation", _FakeDrafter(claim_prefix="CM"),
            _IMPLEMENTATION_EXTRA_FIELDS,
        )
        assert section["wp_table_refs"] == ["WP1", "WP2"]
        assert section["gantt_ref"] == _GANTT_REL
        assert section["milestone_refs"] == ["MS1", "MS2"]
        assert section["risk_register_ref"]
        claim_ids = [
            c["claim_id"] for c in section["validation_status"]["claim_statuses"]
        ]
        assert claim_ids == ["CM-3.1", "CM-3.2"]

    def test_byte_equal_replay_on_real_drafts(self, tmp_path: Path) -> None:
        _seed_profile(tmp_path)
        draft_section_decomposed(
            RUN_ID, tmp_path, "implementation",
            drafter=_FakeDrafter(claim_prefix="CM"),
            extra_fields=_IMPLEMENTATION_EXTRA_FIELDS,
        )
        first = assemble_section(RUN_ID, tmp_path, "implementation").read_bytes()
        second = assemble_section(RUN_ID, tmp_path, "implementation").read_bytes()
        assert first == second

    def test_implementation_specific_check_passes(self, tmp_path: Path) -> None:
        """implementation_coverage_complete (WP/Gantt/milestone/risk coverage)
        passes on the assembled Implementation section — ticket 11 item 3."""
        _seed_profile(tmp_path)
        _seed_wp_structure(tmp_path)
        _draft_and_assemble(
            tmp_path, "implementation", _FakeDrafter(claim_prefix="CM"),
            _IMPLEMENTATION_EXTRA_FIELDS,
        )
        result = implementation_coverage_complete(
            f"{PROPOSAL_SECTIONS_REL}/implementation_section.json",
            _WP_STRUCTURE_REL,
            _GANTT_REL,
            repo_root=tmp_path,
        )
        assert result.passed


# ===========================================================================
# W1 across Impact + Implementation (ticket 11 item 2, both ways)
# ===========================================================================


@pytest.mark.parametrize(
    "slug, claim_prefix, extra_fields",
    [
        ("impact", "CI", _IMPACT_EXTRA_FIELDS),
        ("implementation", "CM", _IMPLEMENTATION_EXTRA_FIELDS),
    ],
)
class TestW1AcrossImpactImplementation:
    """W1 covers all three sections; proven both ways on Impact and
    Implementation, mirroring ticket 9's Excellence demonstration."""

    def _section_rel(self, slug: str) -> str:
        return f"{PROPOSAL_SECTIONS_REL}/{slug}_section.json"

    def _target_sub(self, slug: str) -> str:
        return "2.1" if slug == "impact" else "3.1"

    def test_beta_declaration_greens_the_section(
        self, tmp_path: Path, slug: str, claim_prefix: str,
        extra_fields: dict[str, Any],
    ) -> None:
        """With a declaration, the unresolved claim greens as assumed and both
        the unresolved-check and W1 pass — a conscious green (β)."""
        _seed_profile(tmp_path)
        # One sub-section drafts an unresolved claim; the rest are confirmed.
        target = self._target_sub(slug)
        drafter = _FakeDrafter(
            claim_prefix=claim_prefix,
            special_sub=target,
            special_status="unresolved",
            special_summary="Host institution — UNCONFIRMED",
        )
        draft_section_decomposed(
            RUN_ID, tmp_path, slug, drafter=drafter, extra_fields=extra_fields,
        )
        # Operator declares the value → applier flips unresolved → assumed.
        _declare(
            tmp_path, f"{claim_prefix}-{target}",
            "University of Example (operator-declared)",
        )
        apply_assumptions(RUN_ID, tmp_path, slug)
        assemble_section(RUN_ID, tmp_path, slug)

        section_rel = self._section_rel(slug)
        unresolved = no_unresolved_material_claims(section_rel, repo_root=tmp_path)
        w1 = assumed_claims_are_operator_declared(section_rel, repo_root=tmp_path)
        assert unresolved.passed  # overall_status flipped away from unresolved
        assert w1.passed          # the assumed claim is operator-declared

    def test_alpha_no_declaration_blocks_honestly(
        self, tmp_path: Path, slug: str, claim_prefix: str,
        extra_fields: dict[str, Any],
    ) -> None:
        """Without a declaration, the claim stays unresolved: blocked by the
        unresolved-check (α honest block); W1 is vacuous."""
        _seed_profile(tmp_path)
        drafter = _FakeDrafter(
            claim_prefix=claim_prefix,
            special_sub=self._target_sub(slug),
            special_status="unresolved",
            special_summary="Host institution — UNCONFIRMED",
        )
        draft_section_decomposed(
            RUN_ID, tmp_path, slug, drafter=drafter, extra_fields=extra_fields,
        )
        written = apply_assumptions(RUN_ID, tmp_path, slug)
        assert written == []  # applier is a pure no-op in α
        assemble_section(RUN_ID, tmp_path, slug)

        section_rel = self._section_rel(slug)
        unresolved = no_unresolved_material_claims(section_rel, repo_root=tmp_path)
        w1 = assumed_claims_are_operator_declared(section_rel, repo_root=tmp_path)
        assert not unresolved.passed             # honest block on the gap
        assert unresolved.failure_category == "POLICY_VIOLATION"
        assert w1.passed                          # no assumed claim ⇒ W1 inert

    def test_assumed_without_declaration_blocked_by_w1(
        self, tmp_path: Path, slug: str, claim_prefix: str,
        extra_fields: dict[str, Any],
    ) -> None:
        """An 'assumed' claim with no backing declaration fails W1 — the
        anti-fabrication guarantee, on Impact/Implementation (§13.3)."""
        _seed_profile(tmp_path)
        drafter = _FakeDrafter(
            claim_prefix=claim_prefix,
            special_sub=self._target_sub(slug),
            special_status="assumed",
            special_summary="fabricated assumed value",
        )
        draft_section_decomposed(
            RUN_ID, tmp_path, slug, drafter=drafter, extra_fields=extra_fields,
        )
        assemble_section(RUN_ID, tmp_path, slug)  # no declaration authored
        w1 = assumed_claims_are_operator_declared(
            self._section_rel(slug), repo_root=tmp_path
        )
        assert not w1.passed
        assert w1.failure_category == "POLICY_VIOLATION"


# ===========================================================================
# gate_10d cross-section consistency across the three assembled sections
# ===========================================================================


class TestGate10dGreenAcrossThreeSections:
    def _assemble_all_three(self, repo_root: Path) -> None:
        """Draft + assemble all three criterion sections from decomposed drafts."""
        _draft_and_assemble(
            repo_root, "excellence",
            _FakeDrafter(claim_prefix="CE", mention=["OBJ-1", "OBJ-2"]),
            None,
        )
        _draft_and_assemble(
            repo_root, "impact", _FakeDrafter(claim_prefix="CI"),
            _IMPACT_EXTRA_FIELDS,
        )
        _draft_and_assemble(
            repo_root, "implementation", _FakeDrafter(claim_prefix="CM"),
            _IMPLEMENTATION_EXTRA_FIELDS,
        )

    def _write_assembled_part_b(self, repo_root: Path) -> Path:
        """Compose a minimal assembled Part B draft over the three sections."""
        assembled_rel = (
            "docs/tier5_deliverables/assembled_drafts/part_b_assembled_draft.json"
        )
        _write(
            repo_root / assembled_rel,
            {
                "schema_id": "orch.tier5.part_b_assembled_draft.v1",
                "run_id": RUN_ID,
                "sections": [
                    {"criterion": "Excellence"},
                    {"criterion": "Impact"},
                    {"criterion": "Implementation"},
                ],
                "consistency_log": [],
            },
        )
        return repo_root / assembled_rel

    def test_cross_section_consistency_green(self, tmp_path: Path) -> None:
        """gate_10d's cross_section_consistency is green across the three
        decomposed → assembled sections — ticket 11 item 4."""
        _seed_profile(tmp_path)
        # Tier 3 objectives the Excellence section enumerates (real cross-check).
        _write(
            tmp_path / "docs/tier3_project_instantiation/architecture_inputs/objectives.json",
            {"objectives": [
                {"id": "OBJ-1", "title": "First objective"},
                {"id": "OBJ-2", "title": "Second objective"},
            ]},
        )
        self._assemble_all_three(tmp_path)
        assembled = self._write_assembled_part_b(tmp_path)

        result = cross_section_consistency(
            str(assembled),
            PROPOSAL_SECTIONS_REL,
            "docs/tier3_project_instantiation",
            repo_root=tmp_path,
        )
        assert result.passed, result.reason

    def test_flagged_inconsistency_blocks(self, tmp_path: Path) -> None:
        """A flagged consistency_log entry blocks gate_10d (guards the green)."""
        _seed_profile(tmp_path)
        self._assemble_all_three(tmp_path)
        assembled_rel = (
            "docs/tier5_deliverables/assembled_drafts/part_b_assembled_draft.json"
        )
        _write(
            tmp_path / assembled_rel,
            {
                "schema_id": "orch.tier5.part_b_assembled_draft.v1",
                "run_id": RUN_ID,
                "sections": [
                    {"criterion": "Excellence"},
                    {"criterion": "Impact"},
                    {"criterion": "Implementation"},
                ],
                "consistency_log": [
                    {"check_id": "cc-01", "status": "inconsistency_flagged"}
                ],
            },
        )
        result = cross_section_consistency(
            str(tmp_path / assembled_rel),
            PROPOSAL_SECTIONS_REL,
            "docs/tier3_project_instantiation",
            repo_root=tmp_path,
        )
        assert not result.passed
        assert result.failure_category == "CROSS_ARTIFACT_INCONSISTENCY"


# ===========================================================================
# Canonical pack covers all three sections (ticket 11 item 2, pack half)
# ===========================================================================


@pytest.mark.parametrize(
    "slug, claim_prefix, extra_fields",
    [
        ("impact", "CI", _IMPACT_EXTRA_FIELDS),
        ("implementation", "CM", _IMPLEMENTATION_EXTRA_FIELDS),
    ],
)
class TestCanonicalPackCoversImpactImplementation:
    """The section-agnostic canonical-pack deriver (ticket 10) regenerates the
    reference pack from Tier 3/4, and the canonical-preservation gates pass
    against it for the assembled Impact and Implementation sections — ticket
    10's Excellence acceptance ("preservation gates still pass against the
    regenerated pack") extended to the two remaining sections (item 2)."""

    def _seed_pack_sources(self, repo_root: Path) -> None:
        """Seed the confirmed Tier 3/4 the deriver requires (non-empty
        objectives / outcomes / wps / deliverables per its fail-closed
        backstop)."""
        _write(
            repo_root
            / "docs/tier3_project_instantiation/architecture_inputs/objectives.json",
            {"objectives": [
                {"id": "OBJ-1", "title": "First objective"},
                {"id": "OBJ-2", "title": "Second objective"},
            ]},
        )
        _write(
            repo_root
            / "docs/tier3_project_instantiation/architecture_inputs/outcomes.json",
            {"outcomes": [
                {"id": "OUT-1", "title": "First outcome",
                 "linked_objectives": ["OBJ-1"]},
            ]},
        )
        _write(
            repo_root / _WP_STRUCTURE_REL,
            {"work_packages": [
                {
                    "wp_id": "WP1",
                    "title": "First work package",
                    "lead_partner": "HOST",
                    "deliverables": [
                        {"deliverable_id": "D1.1", "title": "First deliverable",
                         "due_month": 6, "type": "report"},
                    ],
                },
                {
                    "wp_id": "WP2",
                    "title": "Second work package",
                    "lead_partner": "HOST",
                    "deliverables": [
                        {"deliverable_id": "D2.1", "title": "Second deliverable",
                         "due_month": 12, "type": "report"},
                    ],
                },
            ]},
        )

    def test_preservation_gates_pass_on_assembled_section(
        self, tmp_path: Path, slug: str, claim_prefix: str,
        extra_fields: dict[str, Any],
    ) -> None:
        _seed_profile(tmp_path)
        self._seed_pack_sources(tmp_path)

        # The same deriver that serves Excellence regenerates the pack — one
        # section-agnostic artifact, provenance-tagged (ticket 10).
        pack_path = build_phase8_canonical_reference_pack(tmp_path, RUN_ID)
        assert pack_path.is_file()

        _draft_and_assemble(
            tmp_path, slug, _FakeDrafter(claim_prefix=claim_prefix), extra_fields,
        )
        section_rel = f"{PROPOSAL_SECTIONS_REL}/{slug}_section.json"

        # The four canonical-preservation predicates (g09{b,c}_p08–p10/p11) are
        # the contradiction detectors the pack backs; each must pass on the
        # assembled section against the regenerated pack.
        for predicate in (
            partner_names_preserved,
            deliverable_identity_preserved,
            canonical_terms_preserved,
            measurable_targets_preserved,
        ):
            result = predicate(
                section_rel, CANONICAL_PACK_REL, repo_root=tmp_path
            )
            assert result.passed, f"{predicate.__name__}: {result.reason}"
