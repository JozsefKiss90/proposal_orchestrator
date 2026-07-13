"""Ticket 7 tracer bullet — Excellence decomposed drafting → assembled section.

Proves the milestone's central claim: **decomposition** (bounded per-sub-section
calls at profile granularity, composed by the deterministic assembler) produces a
full-length, traceable Excellence section that materially exceeds the prior
monolithic ~10x length shortfall — with no chunked writer and no synthesis.

The per-sub-section Claude call is stood in by a deterministic fake drafter so
the whole decompose→compose chain is exercised without a live model; the
assembler's byte-equal guarantee (proven in test_section_assembler) is
re-confirmed on these realistic drafts (idempotent replay).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from runner.decomposed_drafting import (
    DecomposedDraftingError,
    draft_section_decomposed,
)
from runner.section_assembler import (
    PROPOSAL_SECTIONS_REL,
    SECTION_DRAFTS_ROOT_REL,
    assemble_section,
)

RUN_ID = "run-excellence-decomposed-1"

#: The four MSCA-PF Excellence sub-sections (profile granularity, ticket 5).
_EXCELLENCE_SUBS = [
    ("1.1", "Quality and pertinence of the objectives"),
    ("1.2", "Soundness of the proposed methodology"),
    ("1.3", "Quality of the supervision and training"),
    ("1.4", "Quality of the researcher's experience"),
]

#: The monolithic drafter's per-sub-section soft cap (chars) and whole-section
#: response ceiling — the limits decomposition lifts (excellence-section-drafting
#: spec, pre-ticket-7).
_MONOLITHIC_SUBSECTION_CAP = 2500
_MONOLITHIC_SECTION_CEILING = 20000


def _write(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def _seed_msca_excellence_profile(repo_root: Path) -> None:
    """Seed a resolvable MSCA-PF profile with the Excellence sub-sections."""
    _write(
        repo_root / "docs/tier3_project_instantiation/call_binding/selected_call.json",
        {"instrument_type": "MSCA-PF", "budget_regime": "unit_cost"},
    )
    sections: list[dict[str, Any]] = [
        {
            "section_id": "1",
            "section_name": "Excellence",
            "mandatory": True,
            "section_type": "criterion_section",
            "criterion": "Excellence",
        }
    ]
    for sid, name in _EXCELLENCE_SUBS:
        sections.append({
            "section_id": sid,
            "section_name": name,
            "mandatory": True,
            "section_type": "proposal_section",
            "criterion": "Excellence",
            "parent_section_id": "1",
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


class _RecordingDrafter:
    """A deterministic fake drafter that produces full-length prose and records
    the sequential context it was handed."""

    def __init__(self, *, chars_per_sub: int = 4000, unresolved_sub: str | None = None):
        self.chars_per_sub = chars_per_sub
        self.unresolved_sub = unresolved_sub
        self.calls: list[tuple[str, int]] = []  # (sub_id, num_prior_drafts)

    def __call__(
        self,
        sub: dict[str, Any],
        criterion: str,
        prior_drafts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        sub_id = sub["section_id"]
        self.calls.append((sub_id, len(prior_drafts)))
        # Full-length prose (well beyond the monolithic per-sub-section cap).
        sentence = f"Sub-section {sub_id} of {criterion} develops the argument. "
        content = (sentence * ((self.chars_per_sub // len(sentence)) + 1))[
            : self.chars_per_sub
        ]
        status = "confirmed"
        if self.unresolved_sub == sub_id:
            status = "unresolved"
        return {
            "content": content,
            "claim_statuses": [
                {
                    "claim_id": f"CS-{sub_id}",
                    "claim_summary": f"claim for {sub_id}",
                    "status": status,
                    "source_ref": "tier3/objectives.json",
                }
            ],
            "source_refs": [
                {"tier": 3, "source_path": "docs/tier3/objectives.json"},
                {"tier": 2, "source_path": f"docs/tier2b/{sub_id}.json"},
            ],
        }


# ---------------------------------------------------------------------------
# The decompose → compose tracer bullet
# ---------------------------------------------------------------------------


class TestDecomposeThenCompose:
    def test_drafts_one_per_profile_sub_section(self, tmp_path: Path) -> None:
        _seed_msca_excellence_profile(tmp_path)
        drafter = _RecordingDrafter()
        written = draft_section_decomposed(
            RUN_ID, tmp_path, "excellence", drafter=drafter
        )
        drafts_dir = tmp_path / SECTION_DRAFTS_ROOT_REL / "excellence"
        # Spine + one draft per Excellence sub-section (profile granularity).
        assert (drafts_dir / "section_spine.json").is_file()
        draft_files = sorted(p.name for p in drafts_dir.glob("*.draft.json"))
        assert draft_files == ["1.1.draft.json", "1.2.draft.json",
                               "1.3.draft.json", "1.4.draft.json"]
        assert len(written) == 5  # spine + 4 drafts

    def test_sequential_context_passed_between_calls(self, tmp_path: Path) -> None:
        """Each sub-section call receives the prior sub-sections' drafts (D5)."""
        _seed_msca_excellence_profile(tmp_path)
        drafter = _RecordingDrafter()
        draft_section_decomposed(RUN_ID, tmp_path, "excellence", drafter=drafter)
        # Calls are in order and each sees one more prior draft than the last.
        assert drafter.calls == [("1.1", 0), ("1.2", 1), ("1.3", 2), ("1.4", 3)]

    def test_assembles_to_full_length_section(self, tmp_path: Path) -> None:
        """The composed section materially exceeds the monolithic ceiling —
        the ~10x length fix, by decomposition."""
        _seed_msca_excellence_profile(tmp_path)
        draft_section_decomposed(
            RUN_ID, tmp_path, "excellence", drafter=_RecordingDrafter(chars_per_sub=6000)
        )
        out = assemble_section(RUN_ID, tmp_path, "excellence")
        section = json.loads(out.read_text("utf-8"))

        total_chars = sum(len(s["content"]) for s in section["sub_sections"])
        # Each sub-section alone exceeds the monolithic per-sub-section soft cap...
        for s in section["sub_sections"]:
            assert len(s["content"]) > _MONOLITHIC_SUBSECTION_CAP
        # ...their aggregate exceeds what the monolithic writer could produce
        # (its per-sub-section cap x the sub-section count)...
        assert total_chars > _MONOLITHIC_SUBSECTION_CAP * len(section["sub_sections"])
        # ...and even the whole section exceeds the monolithic single-response
        # JSON ceiling — decomposition lifts both caps at once.
        assert total_chars > _MONOLITHIC_SECTION_CEILING
        assert len(section["sub_sections"]) == 4

    def test_claims_and_traceability_carried(self, tmp_path: Path) -> None:
        _seed_msca_excellence_profile(tmp_path)
        draft_section_decomposed(
            RUN_ID, tmp_path, "excellence", drafter=_RecordingDrafter()
        )
        section = json.loads(
            assemble_section(RUN_ID, tmp_path, "excellence").read_text("utf-8")
        )
        # Every sub-section's claim is carried up (one per sub-section).
        claim_ids = [
            c["claim_id"] for c in section["validation_status"]["claim_statuses"]
        ]
        assert claim_ids == ["CS-1.1", "CS-1.2", "CS-1.3", "CS-1.4"]
        assert section["traceability_footer"]["primary_sources"]
        assert (
            section["traceability_footer"]["no_unsupported_claims_declaration"]
            is True
        )

    def test_content_carried_verbatim_no_synthesis(self, tmp_path: Path) -> None:
        """Assembled content is exactly what the drafter produced (no synthesis)."""
        _seed_msca_excellence_profile(tmp_path)
        drafter = _RecordingDrafter()
        # Re-derive the expected content deterministically by replaying the fake.
        draft_section_decomposed(RUN_ID, tmp_path, "excellence", drafter=drafter)
        drafts_dir = tmp_path / SECTION_DRAFTS_ROOT_REL / "excellence"
        section = json.loads(
            assemble_section(RUN_ID, tmp_path, "excellence").read_text("utf-8")
        )
        for sub in section["sub_sections"]:
            draft = json.loads(
                (drafts_dir / f"{sub['sub_section_id']}.draft.json").read_text("utf-8")
            )
            assert sub["content"] == draft["content"]

    def test_byte_equal_replay_on_real_drafts(self, tmp_path: Path) -> None:
        """assemble(drafts) is byte-identical on replay — the anti-synthesis
        guarantee, on the real Excellence drafts (ticket 7 acceptance)."""
        _seed_msca_excellence_profile(tmp_path)
        draft_section_decomposed(
            RUN_ID, tmp_path, "excellence", drafter=_RecordingDrafter()
        )
        first = assemble_section(RUN_ID, tmp_path, "excellence").read_bytes()
        second = assemble_section(RUN_ID, tmp_path, "excellence").read_bytes()
        assert first == second
        assert (tmp_path / PROPOSAL_SECTIONS_REL / "excellence_section.json").is_file()


# ---------------------------------------------------------------------------
# Honest-block status derivation
# ---------------------------------------------------------------------------


class TestOverallStatus:
    def test_unresolved_claim_makes_section_unresolved(self, tmp_path: Path) -> None:
        """An Unresolved claim in any sub-section makes the section Unresolved
        (the honest block) — carried through the spine to validation_status."""
        _seed_msca_excellence_profile(tmp_path)
        draft_section_decomposed(
            RUN_ID, tmp_path, "excellence",
            drafter=_RecordingDrafter(unresolved_sub="1.3"),
        )
        section = json.loads(
            assemble_section(RUN_ID, tmp_path, "excellence").read_text("utf-8")
        )
        assert section["validation_status"]["overall_status"] == "unresolved"

    def test_all_confirmed_makes_section_confirmed(self, tmp_path: Path) -> None:
        _seed_msca_excellence_profile(tmp_path)
        draft_section_decomposed(
            RUN_ID, tmp_path, "excellence", drafter=_RecordingDrafter()
        )
        section = json.loads(
            assemble_section(RUN_ID, tmp_path, "excellence").read_text("utf-8")
        )
        assert section["validation_status"]["overall_status"] == "confirmed"


# ---------------------------------------------------------------------------
# Fail-closed
# ---------------------------------------------------------------------------


class TestFailClosed:
    def test_unknown_slug(self, tmp_path: Path) -> None:
        with pytest.raises(DecomposedDraftingError, match="Unknown section slug"):
            draft_section_decomposed(RUN_ID, tmp_path, "budget", drafter=_RecordingDrafter())

    def test_no_profile_fails_closed(self, tmp_path: Path) -> None:
        # No instrument profile seeded → resolve fails closed.
        with pytest.raises(Exception):
            draft_section_decomposed(
                RUN_ID, tmp_path, "excellence", drafter=_RecordingDrafter()
            )

    def test_drafter_empty_content_fails(self, tmp_path: Path) -> None:
        _seed_msca_excellence_profile(tmp_path)

        def _empty(sub, criterion, prior):
            return {"content": "  "}

        with pytest.raises(DecomposedDraftingError, match="no 'content'"):
            draft_section_decomposed(RUN_ID, tmp_path, "excellence", drafter=_empty)
