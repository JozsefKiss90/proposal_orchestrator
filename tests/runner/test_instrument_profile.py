"""Tests for runner.instrument_profile — the per-instrument profile resolver.

Covers ticket-2 acceptance:
  - resolve from selected_call's instrument_type → sub-section set, hard page
    limit, budget regime, phases in scope
  - the instrument registry is populated for RIA; the resolver returns the
    correct RIA profile (against the real registries)
  - the page limit and section structure are READ (not assumed)
  - fail-closed (no silent default) when instrument_type is absent or unknown
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from runner.paths import find_repo_root
from runner.instrument_profile import (
    InstrumentProfile,
    InstrumentProfileError,
    resolve_instrument_profile,
    resolve_instrument_type,
    SECTION_SCHEMA_REGISTRY_REL,
    INSTRUMENT_REGISTRY_REL,
    SELECTED_CALL_REL,
)


# ---------------------------------------------------------------------------
# tmp-repo fixtures for fail-closed behavior
# ---------------------------------------------------------------------------

_RIA_SECTION_ENTRY = {
    "instrument_type": "RIA",
    "part_b_page_limit_hard": 40,
    "sections": [
        {"section_id": "A.1", "section_name": "General", "mandatory": True,
         "section_type": "cover_page"},
        {"section_id": "B.1", "section_name": "Excellence", "mandatory": True,
         "section_type": "proposal_section"},
        {"section_id": "B.1.1", "section_name": "Objectives", "mandatory": True,
         "section_type": "proposal_section"},
        {"section_id": "B.2.3", "section_name": "Summary", "mandatory": False,
         "section_type": "proposal_section"},
        {"section_id": "B.3.1", "section_name": "Work plan", "mandatory": True,
         "section_type": "implementation_section"},
    ],
}

_RIA_INSTRUMENT_ENTRY = {
    "instrument_type": "RIA",
    "budget_regime": "lump_sum",
    "phases_in_scope": [1, 2, 3, 4, 5, 6, 7, 8],
}


def _write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _write_repo(
    tmp: Path,
    *,
    section=_RIA_SECTION_ENTRY,
    instrument=_RIA_INSTRUMENT_ENTRY,
    call={"instrument_type": "RIA"},
    section_data=None,
    instrument_data=None,
) -> None:
    """Materialize a minimal repo skeleton for the resolver."""
    if section_data is not None:
        _write(tmp / SECTION_SCHEMA_REGISTRY_REL, section_data)
    elif section is not None:
        _write(tmp / SECTION_SCHEMA_REGISTRY_REL, {"instruments": [section]})
    if instrument_data is not None:
        _write(tmp / INSTRUMENT_REGISTRY_REL, instrument_data)
    elif instrument is not None:
        _write(tmp / INSTRUMENT_REGISTRY_REL, {"instruments": [instrument]})
    if call is not None:
        _write(tmp / SELECTED_CALL_REL, call)


# ---------------------------------------------------------------------------
# Real-registry integration — the resolver returns the correct RIA profile
# ---------------------------------------------------------------------------


class TestRealRIAProfile:
    """Against the real Tier 2A registries populated for RIA (ticket 2)."""

    @pytest.fixture(scope="class")
    def profile(self) -> InstrumentProfile:
        return resolve_instrument_profile(find_repo_root(), instrument_type="RIA")

    def test_instrument_type(self, profile: InstrumentProfile) -> None:
        assert profile.instrument_type == "RIA"

    def test_hard_page_limit_read_from_form(self, profile: InstrumentProfile) -> None:
        # 40 is the value stated in af_he-ria-ia_en.pdf Part B p.3 — read, not assumed.
        assert profile.hard_page_limit == 40

    def test_budget_regime_is_lump_sum(self, profile: InstrumentProfile) -> None:
        assert profile.budget_regime == "lump_sum"

    def test_phases_in_scope_full_sequence(self, profile: InstrumentProfile) -> None:
        assert profile.phases_in_scope == [1, 2, 3, 4, 5, 6, 7, 8]

    def test_sub_section_set_present(self, profile: InstrumentProfile) -> None:
        ids = [s["section_id"] for s in profile.sub_sections]
        # The Excellence / Impact / Implementation triptych sub-sections.
        for sid in ("B.1", "B.1.1", "B.1.2", "B.2", "B.2.1", "B.3", "B.3.1"):
            assert sid in ids

    def test_drafting_sub_sections_are_prose(self, profile: InstrumentProfile) -> None:
        for s in profile.drafting_sub_sections:
            assert s["section_type"] in (
                "proposal_section", "implementation_section"
            )
        # cover_page / annexe sections are excluded from the drafting set.
        assert not any(
            s["section_type"] == "cover_page"
            for s in profile.drafting_sub_sections
        )

    def test_real_registries_have_ria_not_msca(self) -> None:
        # Tier 2A extracted carries RIA (ticket 2); MSCA-PF is added by ticket 5.
        profile = resolve_instrument_profile(find_repo_root(), instrument_type="RIA")
        assert profile.instrument_type == "RIA"


# ---------------------------------------------------------------------------
# tmp-repo happy path
# ---------------------------------------------------------------------------


class TestResolveHappyPath:
    def test_full_profile(self, tmp_path: Path) -> None:
        _write_repo(tmp_path)
        profile = resolve_instrument_profile(tmp_path)
        assert profile.instrument_type == "RIA"
        assert profile.hard_page_limit == 40
        assert profile.budget_regime == "lump_sum"
        assert profile.phases_in_scope == [1, 2, 3, 4, 5, 6, 7, 8]
        assert profile.mandatory_sub_section_ids == [
            "A.1", "B.1", "B.1.1", "B.3.1"
        ]
        # Optional B.2.3 Summary is excluded from mandatory ids.
        assert "B.2.3" not in profile.mandatory_sub_section_ids

    def test_explicit_instrument_type_overrides_call(self, tmp_path: Path) -> None:
        # A call naming a different type is ignored when type is passed.
        _write_repo(tmp_path, call={"instrument_type": "SOMETHING_ELSE"})
        profile = resolve_instrument_profile(tmp_path, instrument_type="RIA")
        assert profile.instrument_type == "RIA"

    def test_resolves_from_selected_call_when_type_omitted(self, tmp_path: Path) -> None:
        # With no instrument_type argument, it is read from selected_call.json.
        _write_repo(tmp_path, call={"instrument_type": "RIA"})
        profile = resolve_instrument_profile(tmp_path)
        assert profile.instrument_type == "RIA"
        assert profile.budget_regime == "lump_sum"

    def test_resolve_instrument_type_reads_call(self, tmp_path: Path) -> None:
        _write_repo(tmp_path, call={"instrument_type": "RIA"})
        assert resolve_instrument_type(tmp_path) == "RIA"


# ---------------------------------------------------------------------------
# Fail-closed behavior (no silent default)
# ---------------------------------------------------------------------------


class TestFailClosed:
    def test_absent_instrument_type_field(self, tmp_path: Path) -> None:
        _write_repo(tmp_path, call={"call_id": "X"})  # no instrument_type
        with pytest.raises(InstrumentProfileError, match="instrument_type"):
            resolve_instrument_profile(tmp_path)

    def test_blank_instrument_type(self, tmp_path: Path) -> None:
        _write_repo(tmp_path, call={"instrument_type": "   "})
        with pytest.raises(InstrumentProfileError):
            resolve_instrument_profile(tmp_path)

    def test_missing_selected_call(self, tmp_path: Path) -> None:
        _write_repo(tmp_path, call=None)
        with pytest.raises(InstrumentProfileError, match="selected_call.json"):
            resolve_instrument_profile(tmp_path)

    def test_unknown_instrument_type(self, tmp_path: Path) -> None:
        _write_repo(tmp_path)
        with pytest.raises(InstrumentProfileError, match="not found"):
            resolve_instrument_profile(tmp_path, instrument_type="ERC-ADG")

    def test_empty_instrument_registry_skeleton(self, tmp_path: Path) -> None:
        _write_repo(tmp_path, instrument_data={})  # unpopulated {}
        with pytest.raises(InstrumentProfileError):
            resolve_instrument_profile(tmp_path, instrument_type="RIA")

    def test_missing_page_limit(self, tmp_path: Path) -> None:
        entry = dict(_RIA_SECTION_ENTRY)
        entry.pop("part_b_page_limit_hard")
        _write_repo(tmp_path, section=entry)
        with pytest.raises(InstrumentProfileError, match="part_b_page_limit_hard"):
            resolve_instrument_profile(tmp_path, instrument_type="RIA")

    def test_invalid_budget_regime(self, tmp_path: Path) -> None:
        entry = dict(_RIA_INSTRUMENT_ENTRY)
        entry["budget_regime"] = "bananas"
        _write_repo(tmp_path, instrument=entry)
        with pytest.raises(InstrumentProfileError, match="budget_regime"):
            resolve_instrument_profile(tmp_path, instrument_type="RIA")

    def test_invalid_phases_in_scope(self, tmp_path: Path) -> None:
        entry = dict(_RIA_INSTRUMENT_ENTRY)
        entry["phases_in_scope"] = "all"
        _write_repo(tmp_path, instrument=entry)
        with pytest.raises(InstrumentProfileError, match="phases_in_scope"):
            resolve_instrument_profile(tmp_path, instrument_type="RIA")

    def test_real_registries_do_not_yet_have_msca(self) -> None:
        # MSCA-PF is added by ticket 5; until then the resolver fails closed.
        with pytest.raises(InstrumentProfileError):
            resolve_instrument_profile(find_repo_root(), instrument_type="MSCA-PF")
