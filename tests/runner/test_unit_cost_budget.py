"""Tests for runner.unit_cost_budget — the deterministic unit-cost budget
deriver (CLAUDE.md §8.1 / C1, ticket 8).

Covers:
  - the byte-equal replay check ``unit_cost_budget(months, rates, host_coeff)
    == figure`` that makes the derivation the anti-fabrication guarantee for
    unit-cost instruments (the milestone CI home, mirroring the assembler),
  - the informative blocked assessment: host-independent lines computed while
    the host-dependent living allowance is Unresolved (D12),
  - honest blocking on unresolved months / host (no fabrication, §8.3/§13.3),
  - fail-closed on a malformed rate table,
  - registration + invocation through the deterministic-component substrate.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from runner.deterministic_components import COMPONENT_REGISTRY, invoke_component
from runner.working_assumptions import WorkingAssumptionsError
from runner.unit_cost_budget import (
    OUTPUT_REL,
    SCHEMA_ID,
    SELECTED_CALL_REL,
    UNIT_COST_RATES_REL,
    UnitCostBudgetError,
    compute_unit_cost_budget,
    derive_unit_cost_budget,
)

RUN_ID = "run-unit-cost-1"


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------


def _rates() -> dict[str, Any]:
    """A minimal-but-faithful subset of unit_cost_rates.json."""
    return {
        "schema_id": "orch.tier2b.unit_cost_rates.v1",
        "instrument_type": "MSCA-PF",
        "researcher_unit_contributions": {
            "living_allowance": {
                "amount_eur_per_month": 6350,
                "host_dependent": True,
                "status": "Confirmed",
            },
            "mobility_allowance": {
                "amount_eur_per_month": 710,
                "host_dependent": False,
                "status": "Confirmed",
            },
            "family_allowance": {
                "amount_eur_per_month": 660,
                "host_dependent": False,
                "status": "Confirmed",
            },
        },
        "institutional_unit_contributions": {
            "research_training_networking": {
                "amount_eur_per_month": 1000,
                "status": "Confirmed",
            },
            "management_and_indirect": {
                "amount_eur_per_month": 650,
                "status": "Confirmed",
            },
        },
        "country_correction_coefficient": {
            "applies_to": "living_allowance",
            "unit": "percent",
            "coefficients_percent": {
                "BE": 100.0,
                "AT": 109.4,
            },
        },
    }


def _write(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def _seed(
    repo_root: Path,
    *,
    project_duration_months: int | None = None,
    host_country: str | None = None,
) -> None:
    _write(repo_root / UNIT_COST_RATES_REL, _rates())
    call: dict[str, Any] = {
        "call_id": "HORIZON-MSCA-2026-PF-01",
        "instrument_type": "MSCA-PF",
        "budget_regime": "unit_cost",
        "max_project_duration_months": 36,
    }
    if project_duration_months is not None:
        call["project_duration_months"] = project_duration_months
    if host_country is not None:
        call["host_country"] = host_country
    _write(repo_root / SELECTED_CALL_REL, call)


# ---------------------------------------------------------------------------
# Byte-equal replay — "unit_cost_budget(months, rates, host_coeff) == figure"
# ---------------------------------------------------------------------------


class TestByteEqualFigure:
    def test_figure_matches_expected_for_confirmed_host(self) -> None:
        """The derived figure is the fixed arithmetic on published rates —
        the determinism that stands in for externalisation (C1)."""
        figure = compute_unit_cost_budget(24, _rates(), 100.0)
        assert figure == {
            "line_items": [
                {
                    "line_id": "living_allowance",
                    "host_dependent": True,
                    "base_monthly_rate_eur": 6350,
                    "coefficient_percent": 100.0,
                    "monthly_rate_eur": 6350.0,
                    "months": 24,
                    "amount_eur": 152400.0,
                    "status": "Confirmed",
                },
                {
                    "line_id": "mobility_allowance",
                    "host_dependent": False,
                    "monthly_rate_eur": 710,
                    "months": 24,
                    "amount_eur": 17040.0,
                    "status": "Confirmed",
                },
                {
                    "line_id": "research_training_networking",
                    "host_dependent": False,
                    "monthly_rate_eur": 1000,
                    "months": 24,
                    "amount_eur": 24000.0,
                    "status": "Confirmed",
                },
                {
                    "line_id": "management_and_indirect",
                    "host_dependent": False,
                    "monthly_rate_eur": 650,
                    "months": 24,
                    "amount_eur": 15600.0,
                    "status": "Confirmed",
                },
            ],
            "total_eur": 209040.0,
            "unresolved_components": [],
        }

    def test_replay_is_byte_equal(self) -> None:
        """Same inputs → byte-identical JSON (the replay guarantee)."""
        a = json.dumps(compute_unit_cost_budget(18, _rates(), 109.4), sort_keys=True)
        b = json.dumps(compute_unit_cost_budget(18, _rates(), 109.4), sort_keys=True)
        assert a == b

    def test_coefficient_scales_living_allowance(self) -> None:
        """AT (109.4%) scales only the living allowance; others unchanged."""
        figure = compute_unit_cost_budget(12, _rates(), 109.4)
        living = figure["line_items"][0]
        assert living["monthly_rate_eur"] == round(6350 * 109.4 / 100, 2)
        assert living["amount_eur"] == round(round(6350 * 109.4 / 100, 2) * 12, 2)
        mobility = figure["line_items"][1]
        assert mobility["amount_eur"] == 710 * 12

    def test_include_family_adds_a_line(self) -> None:
        figure = compute_unit_cost_budget(24, _rates(), 100.0, include_family=True)
        ids = [li["line_id"] for li in figure["line_items"]]
        assert "family_allowance" in ids
        family = next(li for li in figure["line_items"] if li["line_id"] == "family_allowance")
        assert family["amount_eur"] == 660 * 24


# ---------------------------------------------------------------------------
# Informative blocked figure — host unresolved
# ---------------------------------------------------------------------------


class TestHostUnresolvedFigure:
    def test_host_independent_lines_computed_living_unresolved(self) -> None:
        """host_coeff=None → living Unresolved, host-independent lines still
        computed, total None (the informative blocked assessment, D12)."""
        figure = compute_unit_cost_budget(24, _rates(), None)
        living = figure["line_items"][0]
        assert living["line_id"] == "living_allowance"
        assert living["status"] == "Unresolved"
        assert living["amount_eur"] is None
        # Host-independent lines are fully computed.
        mobility = figure["line_items"][1]
        assert mobility["status"] == "Confirmed"
        assert mobility["amount_eur"] == 17040.0
        assert figure["total_eur"] is None
        assert figure["unresolved_components"] == ["living_allowance"]


# ---------------------------------------------------------------------------
# Fail-closed on malformed rate table / bad months
# ---------------------------------------------------------------------------


class TestFailClosedCore:
    def test_non_positive_months(self) -> None:
        with pytest.raises(UnitCostBudgetError, match="positive integer"):
            compute_unit_cost_budget(0, _rates(), 100.0)

    def test_missing_rate_group(self) -> None:
        bad = _rates()
        del bad["researcher_unit_contributions"]
        with pytest.raises(UnitCostBudgetError, match="researcher_unit_contributions"):
            compute_unit_cost_budget(24, bad, 100.0)

    def test_non_numeric_rate(self) -> None:
        bad = _rates()
        bad["researcher_unit_contributions"]["mobility_allowance"][
            "amount_eur_per_month"
        ] = "710"
        with pytest.raises(UnitCostBudgetError, match="not a number"):
            compute_unit_cost_budget(24, bad, 100.0)

    def test_missing_family_rate_ok_when_not_included(self) -> None:
        """A rate table lacking the conditional family_allowance must not fail a
        budget that does not emit that line (include_family=False)."""
        no_family = _rates()
        del no_family["researcher_unit_contributions"]["family_allowance"]
        figure = compute_unit_cost_budget(24, no_family, 100.0)  # default: no family
        assert figure["total_eur"] == 209040.0
        # ...but it IS required when the line is emitted.
        with pytest.raises(UnitCostBudgetError, match="family_allowance"):
            compute_unit_cost_budget(24, no_family, 100.0, include_family=True)


# ---------------------------------------------------------------------------
# Component wrapper — derive_unit_cost_budget
# ---------------------------------------------------------------------------


class TestComponentGreen:
    def test_all_resolved_writes_pass_assessment(self, tmp_path: Path) -> None:
        _seed(tmp_path, project_duration_months=24, host_country="BE")
        out = derive_unit_cost_budget(RUN_ID, tmp_path)
        assert out == tmp_path / OUTPUT_REL
        data = json.loads(out.read_text("utf-8"))
        assert data["schema_id"] == SCHEMA_ID
        assert data["run_id"] == RUN_ID
        assert data["gate_pass_declaration"] == "pass"
        assert data["total_eur"] == 209040.0
        assert data["unresolved_components"] == []
        assert data["blocking_inconsistencies"] == []
        assert data["derivation"]["host_country_coefficient_percent"] == 100.0

    def test_declared_host_flips_to_assumed(self, tmp_path: Path) -> None:
        """A host declared in working_assumptions.json (via the shared ticket-15
        substrate) greens as Assumed."""
        _seed(tmp_path, project_duration_months=24)
        _write(
            tmp_path / "docs/tier3_project_instantiation/working_assumptions.json",
            {
                "record_type": "working_assumptions",
                "provenance_class": "manually_placed",
                "declarations": [
                    {
                        "key": "host_country",
                        "value": "AT",
                        "declared_by": "operator@example.org",
                        "declared_on": "2026-07-13T10:00:00Z",
                        "checklist_ref": "HOST",
                    }
                ],
            },
        )
        out = derive_unit_cost_budget(RUN_ID, tmp_path)
        data = json.loads(out.read_text("utf-8"))
        assert data["gate_pass_declaration"] == "pass"
        assert data["derivation"]["host_country_status"] == "Assumed"
        assert data["derivation"]["host_country"] == "AT"

    def test_declared_duration_flips_months_to_assumed(
        self, tmp_path: Path
    ) -> None:
        """A project duration declared in working_assumptions.json greens the
        months line as Assumed — D11/D12 symmetry with the host coefficient
        (ticket 13): the fellowship duration is a deliberately-Unresolved spine
        fact, so declaring it (not confirming it into the call binding) is the
        honest β path."""
        _seed(tmp_path, host_country="BE")  # confirmed host, NO confirmed duration
        _write(
            tmp_path / "docs/tier3_project_instantiation/working_assumptions.json",
            {
                "record_type": "working_assumptions",
                "provenance_class": "manually_placed",
                "declarations": [
                    {
                        "key": "project_duration_months",
                        "value": 24,
                        "declared_by": "operator@example.org",
                        "declared_on": "2026-07-13T10:00:00Z",
                        "checklist_ref": "DURATION",
                    }
                ],
            },
        )
        out = derive_unit_cost_budget(RUN_ID, tmp_path)
        data = json.loads(out.read_text("utf-8"))
        assert data["gate_pass_declaration"] == "pass"
        assert data["derivation"]["confirmed_months"] == 24
        assert data["derivation"]["confirmed_months_status"] == "Assumed"

    def test_declared_duration_via_duration_token(self, tmp_path: Path) -> None:
        """The DURATION checklist token is accepted as the declaration key too
        (matches working_assumptions.example.json)."""
        _seed(tmp_path, host_country="BE")
        _write(
            tmp_path / "docs/tier3_project_instantiation/working_assumptions.json",
            {
                "record_type": "working_assumptions",
                "provenance_class": "manually_placed",
                "declarations": [
                    {
                        "key": "DURATION",
                        "value": 24,
                        "declared_by": "operator@example.org",
                        "declared_on": "2026-07-13T10:00:00Z",
                        "checklist_ref": "DURATION",
                    }
                ],
            },
        )
        out = derive_unit_cost_budget(RUN_ID, tmp_path)
        data = json.loads(out.read_text("utf-8"))
        assert data["gate_pass_declaration"] == "pass"
        assert data["derivation"]["confirmed_months"] == 24
        assert data["derivation"]["confirmed_months_status"] == "Assumed"


class TestComponentBlocked:
    def test_unresolved_host_blocks_with_lines_computed(self, tmp_path: Path) -> None:
        """Host unresolved → fail assessment; host-independent lines computed
        (rides free under the block, D12); living Unresolved."""
        _seed(tmp_path, project_duration_months=24)  # no host
        out = derive_unit_cost_budget(RUN_ID, tmp_path)
        data = json.loads(out.read_text("utf-8"))
        assert data["gate_pass_declaration"] == "fail"
        assert "host_coefficient_unresolved" in data["unresolved_components"]
        # Host-independent lines are present and computed.
        mobility = next(
            li for li in data["line_items"] if li["line_id"] == "mobility_allowance"
        )
        assert mobility["amount_eur"] == 17040.0
        living = next(
            li for li in data["line_items"] if li["line_id"] == "living_allowance"
        )
        assert living["status"] == "Unresolved"
        assert data["total_eur"] is None
        assert any(
            b["resolution"] == "unresolved" for b in data["blocking_inconsistencies"]
        )

    def test_unresolved_months_blocks(self, tmp_path: Path) -> None:
        """No confirmed project duration → months Unresolved → block (the
        call-level max is not used as a project fact, §13.3)."""
        _seed(tmp_path, host_country="BE")  # no project_duration_months
        out = derive_unit_cost_budget(RUN_ID, tmp_path)
        data = json.loads(out.read_text("utf-8"))
        assert data["gate_pass_declaration"] == "fail"
        assert "confirmed_months_unresolved" in data["unresolved_components"]
        assert data["derivation"]["confirmed_months"] is None

    def test_unlisted_country_is_unresolved(self, tmp_path: Path) -> None:
        _seed(tmp_path, project_duration_months=24, host_country="ZZ")
        out = derive_unit_cost_budget(RUN_ID, tmp_path)
        data = json.loads(out.read_text("utf-8"))
        assert data["gate_pass_declaration"] == "fail"
        assert data["derivation"]["host_country_status"] == "Unresolved"


class TestInstrumentGuard:
    def test_lump_sum_instrument_is_skipped(self, tmp_path: Path) -> None:
        """A lump-sum call (no unit_cost_rates.json) is skipped cleanly —
        returns None, writes nothing — so the lump-sum branch is unaffected."""
        _write(
            tmp_path / SELECTED_CALL_REL,
            {"instrument_type": "RIA", "budget_regime": "lump_sum"},
        )
        # No unit_cost_rates.json seeded — must not raise.
        out = derive_unit_cost_budget(RUN_ID, tmp_path)
        assert out is None
        assert not (tmp_path / OUTPUT_REL).exists()

    def test_lump_sum_invoke_component_records_no_outputs(
        self, tmp_path: Path
    ) -> None:
        _write(
            tmp_path / SELECTED_CALL_REL,
            {"instrument_type": "RIA", "budget_regime": "lump_sum"},
        )
        record = invoke_component("unit_cost_budget_deriver", RUN_ID, tmp_path)
        assert record.status == "success"
        assert record.outputs_written == []


class TestComponentFailClosed:
    def test_missing_rates_raises(self, tmp_path: Path) -> None:
        # selected_call present but no rate table.
        _write(
            tmp_path / SELECTED_CALL_REL,
            {"instrument_type": "MSCA-PF", "budget_regime": "unit_cost"},
        )
        with pytest.raises(UnitCostBudgetError, match="unit_cost_rates.json not found"):
            derive_unit_cost_budget(RUN_ID, tmp_path)

    def test_malformed_working_assumptions_surfaces_loudly(
        self, tmp_path: Path
    ) -> None:
        """A present-but-malformed declaration file raises via the shared reader
        (ticket 15) rather than being silently swallowed into a block — an
        operator declaration that did not parse must be legible."""
        _seed(tmp_path, project_duration_months=24)
        _write(
            tmp_path / "docs/tier3_project_instantiation/working_assumptions.json",
            {
                "provenance_class": "manually_placed",
                "declarations": [{"key": "host_country"}],  # missing value/attribution
            },
        )
        with pytest.raises(WorkingAssumptionsError):
            derive_unit_cost_budget(RUN_ID, tmp_path)


# ---------------------------------------------------------------------------
# Deterministic-component substrate integration
# ---------------------------------------------------------------------------


class TestComponentRegistration:
    def test_registered(self) -> None:
        assert "unit_cost_budget_deriver" in COMPONENT_REGISTRY

    def test_invoke_component_success_record(self, tmp_path: Path) -> None:
        _seed(tmp_path, project_duration_months=24, host_country="BE")
        record = invoke_component("unit_cost_budget_deriver", RUN_ID, tmp_path)
        assert record.status == "success"
        assert record.outputs_written == [OUTPUT_REL]
        assert (tmp_path / OUTPUT_REL).is_file()

    def test_invoke_component_failure_record_on_missing_rates(
        self, tmp_path: Path
    ) -> None:
        record = invoke_component("unit_cost_budget_deriver", RUN_ID, tmp_path)
        assert record.status == "failure"
        assert record.failure_reason
