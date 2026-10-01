"""The RIA registry must bind each Part B sub-section to its criterion.

Phase 8 drafts one criterion at a time.  ``draft_section_decomposed`` resolves
*which* sub-sections a slug drafts by matching the instrument profile's
drafting sub-sections against a criterion label, so a registry entry that
omits ``criterion`` yields an empty set and the node fails closed before any
drafting call.  That is what ``n08a`` did on the first dispatch of this
instantiation:

    DecomposedDraftingError: instrument profile 'RIA' has no drafting
    sub-sections for criterion 'Excellence' (slug 'excellence')

The MSCA-PF entry in the same registry carries ``criterion`` on its criterion
sections and on every drafting sub-section.  The RIA entry carried it nowhere.
These tests hold the RIA entry to that contract, and pin the join the engine
actually performs rather than the field's presence alone.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from runner.decomposed_drafting import (  # noqa: E402
    SLUG_CRITERION,
    _resolve_drafting_sub_sections,
)
from runner.instrument_profile import resolve_instrument_profile  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
REGISTRY_REL = "docs/tier2a_instrument_schemas/extracted/section_schema_registry.json"

#: The ``section_type`` values the profile treats as drafted prose.
DRAFTING_TYPES = ("proposal_section", "implementation_section")


def _instrument(instrument_type: str) -> dict:
    registry = json.loads((REPO / REGISTRY_REL).read_text(encoding="utf-8-sig"))
    for entry in registry["instruments"]:
        if entry.get("instrument_type") == instrument_type:
            return entry
    pytest.fail(f"the registry declares no {instrument_type} instrument")


def _sections(instrument_type: str) -> list[dict]:
    return [s for s in _instrument(instrument_type)["sections"] if isinstance(s, dict)]


def _by_type(instrument_type: str, *types: str) -> list[dict]:
    return [s for s in _sections(instrument_type) if s.get("section_type") in types]


class TestTheRIAEntryBindsEverySubSectionToACriterion:
    """A drafting sub-section with no criterion is invisible to Phase 8."""

    def test_every_drafting_sub_section_declares_a_criterion(self):
        missing = [
            s.get("section_id")
            for s in _by_type("RIA", *DRAFTING_TYPES)
            if not str(s.get("criterion") or "").strip()
        ]
        assert missing == [], (
            "these RIA drafting sub-sections declare no criterion, so the slug "
            f"that should draft them resolves to nothing: {missing}"
        )

    def test_every_criterion_section_declares_a_criterion(self):
        missing = [
            s.get("section_id")
            for s in _by_type("RIA", "criterion_section")
            if not str(s.get("criterion") or "").strip()
        ]
        assert missing == [], missing

    def test_the_labels_are_the_vocabulary_the_engine_joins_on(self):
        """No label may be spelled in a way no slug asks for."""
        declared = {
            str(s["criterion"])
            for s in _by_type("RIA", "criterion_section", *DRAFTING_TYPES)
            if s.get("criterion")
        }
        assert declared == set(SLUG_CRITERION.values()), (
            "the RIA criterion labels and the Phase 8 slug map disagree: "
            f"registry={sorted(declared)} engine={sorted(SLUG_CRITERION.values())}"
        )

    def test_the_label_is_the_registrys_token_not_the_form_heading(self):
        """Two of the three labels are the form's heading; the third is not.

        For Excellence and Impact the form heading and the engine token
        coincide, so they prove nothing about the convention.  Criterion 3 is
        where they part, and the token is grounded in the MSCA-PF entry of the
        same registry — an origin this ticket did not author — rather than in
        a string chosen here.
        """
        msca = {
            str(s.get("section_name", "")).strip().lower(): str(s.get("criterion"))
            for s in _by_type("MSCA-PF", "criterion_section")
        }
        ria = {
            str(s.get("section_name", "")).strip().lower(): str(s.get("criterion"))
            for s in _by_type("RIA", "criterion_section")
        }
        heading = "quality and efficiency of the implementation"
        assert heading in msca, "the MSCA-PF entry no longer anchors this token"
        assert heading in ria, "the RIA entry lost its criterion-3 heading"
        assert ria[heading] == msca[heading], (
            "the two instruments spell the same criterion differently, so one "
            "of them cannot be drafted by the shared slug map"
        )
        assert ria[heading] != heading, (
            "criterion 3's token is expected to differ from its heading; if the "
            "registry convention changed, this test is the thing to revisit"
        )

    def test_each_sub_section_carries_its_parent_criterion(self):
        """The binding follows the form's own nesting, not a typed list."""
        parents = {
            str(s["section_id"]): str(s["criterion"])
            for s in _by_type("RIA", "criterion_section")
            if s.get("criterion")
        }
        mismatched = []
        for sub in _by_type("RIA", *DRAFTING_TYPES):
            sub_id = str(sub.get("section_id", ""))
            parent_id = sub_id.rsplit(".", 1)[0]
            if parent_id not in parents:
                mismatched.append(f"{sub_id}: no criterion section {parent_id!r}")
            elif str(sub.get("criterion")) != parents[parent_id]:
                mismatched.append(
                    f"{sub_id}: criterion {sub.get('criterion')!r} but its parent "
                    f"{parent_id} declares {parents[parent_id]!r}"
                )
        assert mismatched == [], mismatched


class TestEachPhase8SlugResolvesItsSubSections:
    """The join the dispatch performs, at the function that raised."""

    @pytest.mark.parametrize(
        "slug,parent_id",
        [("excellence", "B.1"), ("impact", "B.2"), ("implementation", "B.3")],
    )
    def test_the_slug_resolves_the_sub_sections_under_its_criterion(
        self, slug, parent_id
    ):
        resolved = _resolve_drafting_sub_sections(
            REPO, slug, SLUG_CRITERION[slug]
        )
        assert resolved, f"{slug} resolves no sub-section"
        ids = [str(s["section_id"]) for s in resolved]
        assert ids == sorted(ids), f"{slug} sub-sections are not ordered: {ids}"
        strays = [i for i in ids if not i.startswith(f"{parent_id}.")]
        assert strays == [], f"{slug} drew in sub-sections outside {parent_id}: {strays}"

    def test_the_three_slugs_between_them_cover_every_drafting_sub_section(self):
        """A sub-section no slug claims would never be drafted at all."""
        covered = {
            str(s["section_id"])
            for slug in SLUG_CRITERION
            for s in _resolve_drafting_sub_sections(REPO, slug, SLUG_CRITERION[slug])
        }
        declared = {
            str(s["section_id"])
            for s in resolve_instrument_profile(REPO).drafting_sub_sections
        }
        assert covered == declared, (
            "these drafting sub-sections are claimed by no Phase 8 slug: "
            f"{sorted(declared - covered)}"
        )
