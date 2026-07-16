"""Tests for runner.working_assumptions — the Tier 3 working_assumptions.json
declaration substrate (CLAUDE.md §12.2, ticket 15).

The declaration substrate is the single mechanism that turns an honest block
into a *conscious* green (D11): a human operator declares working assumptions
and both consumers read them from one shared reader — the budget gate's
host-country coefficient (ticket 8) and the claim layer's ``Assumed`` claims
(ticket 9, W1).  This ticket delivers the convention, schema, and reader; the
applier and the W1 predicate remain ticket 9.

Covers:
  - absent / empty file is a **valid** state (the honest block, mode α) — never
    an error,
  - fail-closed on a present-but-malformed file (bad JSON, wrong shape, missing
    required per-entry fields, duplicate keys, bad provenance_class),
  - the per-entry schema (stable key, operator-declared value, attribution,
    timestamp) sufficient for W1 and the budget host lookup,
  - the shared lookups both consumers use (``declared_value`` /
    ``by_checklist_ref``),
  - the declared-assumptions surface that makes a declaration legible as
    **declared**, not confirmed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from runner.working_assumptions import (
    DECLARED_STATUS,
    PROVENANCE_CLASS,
    WORKING_ASSUMPTIONS_REL,
    Declaration,
    WorkingAssumptions,
    WorkingAssumptionsError,
    load_working_assumptions,
)


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------


def _write(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(obj, str):
        path.write_text(obj, encoding="utf-8")
    else:
        path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def _host_declaration(country: str = "BE") -> dict[str, Any]:
    return {
        "key": "host_country",
        "value": country,
        "declared_by": "operator@example.org",
        "declared_on": "2026-07-13T10:00:00Z",
        "rationale": "Host institution located in Belgium.",
        "checklist_ref": "HOST",
    }


def _file(*declarations: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_type": "working_assumptions",
        "provenance_class": PROVENANCE_CLASS,
        "declarations": list(declarations),
    }


def _seed(repo_root: Path, obj: Any) -> Path:
    path = repo_root / WORKING_ASSUMPTIONS_REL
    _write(path, obj)
    return path


# ---------------------------------------------------------------------------
# Absent / empty are valid states — the honest block (α), never an error
# ---------------------------------------------------------------------------


class TestAbsentOrEmptyIsValid:
    def test_absent_file_is_valid_and_empty(self, tmp_path: Path) -> None:
        wa = load_working_assumptions(tmp_path)
        assert wa.present is False
        assert wa.is_empty is True
        assert wa.declarations == ()
        assert wa.declaration("host_country") is None
        assert wa.declared_value("host_country") is None
        assert wa.as_surface() == []

    def test_blank_file_is_valid_and_empty(self, tmp_path: Path) -> None:
        """A file the operator created but left blank is valid (present, empty)."""
        _seed(tmp_path, "   \n  ")
        wa = load_working_assumptions(tmp_path)
        assert wa.present is True
        assert wa.is_empty is True
        assert wa.declared_value("host_country") is None

    def test_empty_object_is_valid_and_empty(self, tmp_path: Path) -> None:
        _seed(tmp_path, {})
        wa = load_working_assumptions(tmp_path)
        assert wa.present is True
        assert wa.is_empty is True

    def test_empty_declarations_array_is_valid_and_empty(self, tmp_path: Path) -> None:
        _seed(tmp_path, {"provenance_class": PROVENANCE_CLASS, "declarations": []})
        wa = load_working_assumptions(tmp_path)
        assert wa.is_empty is True

    def test_empty_declarations_needs_no_provenance_class(self, tmp_path: Path) -> None:
        """No declarations → nothing to govern → provenance_class not required."""
        _seed(tmp_path, {"declarations": []})
        wa = load_working_assumptions(tmp_path)
        assert wa.is_empty is True


# ---------------------------------------------------------------------------
# Valid declarations — the per-entry schema + shared lookups
# ---------------------------------------------------------------------------


class TestValidDeclarations:
    def test_declared_value_lookup(self, tmp_path: Path) -> None:
        _seed(tmp_path, _file(_host_declaration("AT")))
        wa = load_working_assumptions(tmp_path)
        assert wa.present is True
        assert wa.is_empty is False
        assert wa.declared_value("host_country") == "AT"

    def test_declaration_fields_parsed(self, tmp_path: Path) -> None:
        _seed(tmp_path, _file(_host_declaration("BE")))
        wa = load_working_assumptions(tmp_path)
        decl = wa.declaration("host_country")
        assert isinstance(decl, Declaration)
        assert decl.key == "host_country"
        assert decl.value == "BE"
        assert decl.declared_by == "operator@example.org"
        assert decl.declared_on == "2026-07-13T10:00:00Z"
        assert decl.rationale == "Host institution located in Belgium."
        assert decl.checklist_ref == "HOST"

    def test_optional_fields_default_to_none(self, tmp_path: Path) -> None:
        _seed(
            tmp_path,
            _file(
                {
                    "key": "DURATION",
                    "value": 24,
                    "declared_by": "op",
                    "declared_on": "2026-07-13T00:00:00Z",
                }
            ),
        )
        decl = load_working_assumptions(tmp_path).declaration("DURATION")
        assert decl is not None
        assert decl.value == 24
        assert decl.rationale is None
        assert decl.checklist_ref is None

    def test_value_may_be_a_non_string_scalar(self, tmp_path: Path) -> None:
        """The operator-declared value is any JSON scalar (e.g. an int duration)."""
        _seed(
            tmp_path,
            _file(
                {
                    "key": "months",
                    "value": 24,
                    "declared_by": "op",
                    "declared_on": "2026-07-13T00:00:00Z",
                }
            ),
        )
        assert load_working_assumptions(tmp_path).declared_value("months") == 24

    def test_multiple_declarations_indexed_by_key(self, tmp_path: Path) -> None:
        _seed(
            tmp_path,
            _file(
                _host_declaration("BE"),
                {
                    "key": "CS-05",
                    "value": "Fellowship is a 24-month European Fellowship",
                    "declared_by": "op",
                    "declared_on": "2026-07-13T00:00:00Z",
                },
            ),
        )
        wa = load_working_assumptions(tmp_path)
        assert wa.declared_value("host_country") == "BE"
        assert wa.declared_value("CS-05").startswith("Fellowship")
        assert len(wa.declarations) == 2

    def test_by_checklist_ref_groups_declarations(self, tmp_path: Path) -> None:
        """A single host declaration is discoverable by its spine token so the
        applier (ticket 9) can green the HOST claims from the same source that
        the budget reads for the coefficient (D11/D12)."""
        _seed(tmp_path, _file(_host_declaration("BE")))
        wa = load_working_assumptions(tmp_path)
        host = wa.by_checklist_ref("HOST")
        assert len(host) == 1
        assert host[0].key == "host_country"
        assert wa.by_checklist_ref("FELLOW") == ()


# ---------------------------------------------------------------------------
# Surfacing — a green bought by declaration is legible as *declared*
# ---------------------------------------------------------------------------


class TestDeclaredSurface:
    def test_surface_marks_declarations_as_declared_not_confirmed(
        self, tmp_path: Path
    ) -> None:
        _seed(tmp_path, _file(_host_declaration("BE")))
        surface = load_working_assumptions(tmp_path).as_surface()
        assert len(surface) == 1
        entry = surface[0]
        assert entry["key"] == "host_country"
        assert entry["declared_value"] == "BE"
        # Legible as declared: status is Assumed (§12.2), provenance manually_placed.
        assert entry["status"] == DECLARED_STATUS
        assert entry["status"] != "Confirmed"
        assert entry["provenance_class"] == PROVENANCE_CLASS
        assert entry["declared_by"] == "operator@example.org"
        assert entry["declared_on"] == "2026-07-13T10:00:00Z"
        assert entry["checklist_ref"] == "HOST"

    def test_surface_empty_when_no_declarations(self, tmp_path: Path) -> None:
        assert load_working_assumptions(tmp_path).as_surface() == []


class TestCanonicalPackEntries:
    """The shared machine-entry renderer both canonical-pack derivers use."""

    def test_entries_are_quarantined_assumed(self, tmp_path: Path) -> None:
        _seed(tmp_path, _file(_host_declaration("BE")))
        entries = load_working_assumptions(tmp_path).as_canonical_pack_entries()
        assert entries == [
            {
                "key": "host_country",
                "declared_value": "BE",
                "checklist_ref": "HOST",
                # Lowercase machine tag — quarantined out of every confirmed array.
                "provenance": "assumed",
            }
        ]
        # Never a confirmed canonical fact.
        assert entries[0]["provenance"] != "confirmed"

    def test_checklist_ref_omitted_when_absent(self, tmp_path: Path) -> None:
        decl = _host_declaration("BE")
        del decl["checklist_ref"]
        _seed(tmp_path, _file(decl))
        entry = load_working_assumptions(tmp_path).as_canonical_pack_entries()[0]
        assert "checklist_ref" not in entry

    def test_entries_empty_when_no_declarations(self, tmp_path: Path) -> None:
        assert load_working_assumptions(tmp_path).as_canonical_pack_entries() == []


# ---------------------------------------------------------------------------
# Fail-closed on a present-but-malformed file
# ---------------------------------------------------------------------------


class TestFailClosed:
    def test_invalid_json_raises(self, tmp_path: Path) -> None:
        _seed(tmp_path, "{ not valid json ")
        with pytest.raises(WorkingAssumptionsError, match="valid JSON"):
            load_working_assumptions(tmp_path)

    def test_non_object_root_raises(self, tmp_path: Path) -> None:
        _seed(tmp_path, [1, 2, 3])
        with pytest.raises(WorkingAssumptionsError, match="object"):
            load_working_assumptions(tmp_path)

    def test_declarations_not_a_list_raises(self, tmp_path: Path) -> None:
        _seed(
            tmp_path,
            {"provenance_class": PROVENANCE_CLASS, "declarations": {"key": "x"}},
        )
        with pytest.raises(WorkingAssumptionsError, match="array"):
            load_working_assumptions(tmp_path)

    def test_missing_provenance_class_raises_when_declarations_present(
        self, tmp_path: Path
    ) -> None:
        _seed(tmp_path, {"declarations": [_host_declaration("BE")]})
        with pytest.raises(WorkingAssumptionsError, match="provenance_class"):
            load_working_assumptions(tmp_path)

    def test_wrong_provenance_class_raises(self, tmp_path: Path) -> None:
        _seed(
            tmp_path,
            {"provenance_class": "run_produced", "declarations": [_host_declaration()]},
        )
        with pytest.raises(WorkingAssumptionsError, match="manually_placed"):
            load_working_assumptions(tmp_path)

    def test_entry_not_object_raises(self, tmp_path: Path) -> None:
        _seed(tmp_path, _file())  # provenance ok
        _seed(
            tmp_path,
            {"provenance_class": PROVENANCE_CLASS, "declarations": ["not-an-object"]},
        )
        with pytest.raises(WorkingAssumptionsError, match="object"):
            load_working_assumptions(tmp_path)

    @pytest.mark.parametrize("field", ["key", "value", "declared_by", "declared_on"])
    def test_missing_required_field_raises_naming_it(
        self, tmp_path: Path, field: str
    ) -> None:
        entry = _host_declaration("BE")
        del entry[field]
        _seed(tmp_path, _file(entry))
        with pytest.raises(WorkingAssumptionsError, match=field):
            load_working_assumptions(tmp_path)

    def test_null_value_is_not_a_declaration(self, tmp_path: Path) -> None:
        """An explicit null value declares nothing — fail closed, do not treat
        it as a valid declaration (no fabrication, §13.3)."""
        entry = _host_declaration("BE")
        entry["value"] = None
        _seed(tmp_path, _file(entry))
        with pytest.raises(WorkingAssumptionsError, match="value"):
            load_working_assumptions(tmp_path)

    def test_blank_string_value_raises(self, tmp_path: Path) -> None:
        """A blank string value declares nothing — fail closed loudly rather
        than let a consumer silently degrade it to a block (criterion 4)."""
        entry = _host_declaration("BE")
        entry["value"] = "   "
        _seed(tmp_path, _file(entry))
        with pytest.raises(WorkingAssumptionsError, match="value"):
            load_working_assumptions(tmp_path)

    def test_falsy_non_string_value_is_allowed(self, tmp_path: Path) -> None:
        """0 / False are concrete declared values, not 'nothing' — allowed."""
        _seed(
            tmp_path,
            _file(
                {
                    "key": "return_phase_applies",
                    "value": False,
                    "declared_by": "op",
                    "declared_on": "2026-07-13T00:00:00Z",
                }
            ),
        )
        assert load_working_assumptions(tmp_path).declared_value(
            "return_phase_applies"
        ) is False

    def test_blank_key_raises(self, tmp_path: Path) -> None:
        entry = _host_declaration("BE")
        entry["key"] = "   "
        _seed(tmp_path, _file(entry))
        with pytest.raises(WorkingAssumptionsError, match="key"):
            load_working_assumptions(tmp_path)

    def test_duplicate_key_raises(self, tmp_path: Path) -> None:
        _seed(tmp_path, _file(_host_declaration("BE"), _host_declaration("AT")))
        with pytest.raises(WorkingAssumptionsError, match="duplicate"):
            load_working_assumptions(tmp_path)


# ---------------------------------------------------------------------------
# The engine never writes it (read-only substrate)
# ---------------------------------------------------------------------------


class TestReadOnly:
    def test_loading_absent_file_does_not_create_it(self, tmp_path: Path) -> None:
        load_working_assumptions(tmp_path)
        assert not (tmp_path / WORKING_ASSUMPTIONS_REL).exists()

    def test_module_exposes_no_writer(self) -> None:
        """No public symbol writes the file — the substrate is read-only (§9,
        provenance_class manually_placed)."""
        import runner.working_assumptions as mod

        writers = [
            name
            for name in dir(mod)
            if not name.startswith("_")
            and any(v in name.lower() for v in ("write", "save", "persist", "dump"))
        ]
        assert writers == []
