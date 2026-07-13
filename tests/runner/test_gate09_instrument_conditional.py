"""Instrument-conditional gate_09 (C1, ticket 8).

gate_09 branches on the selected call's budget regime: lump-sum instruments
validate the external ``received/`` response; unit-cost instruments validate
the internal deterministic derivation (``unit_cost_budget.json``).  The
selection is driven by ``applies_when: {budget_regime: ...}`` predicate tags
resolved by the gate evaluator, with the lump-sum predicates preserved
verbatim and the categorical HARD_BLOCK on Phase 8 preserved (§8.4).

These tests exercise the evaluator's applies_when filter with synthetic gates
that mirror the production gate_09 shape.
"""

from __future__ import annotations

import json
from pathlib import Path

from runner.gate_evaluator import evaluate_gate
from runner.run_context import RunContext, PHASE_8_NODE_IDS

from tests.runner.fixtures.repo_builders import (
    gate_entry,
    init_run,
    make_repo_root,
    pred_dir_non_empty,
    pred_non_empty_json,
    write_json,
    write_library,
)

_UNIT_COST_BUDGET_REL = (
    "docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/"
    "unit_cost_budget.json"
)
_RECEIVED_REL = "docs/integrations/lump_sum_budget_planner/received"
_VALIDATION_REL = "docs/integrations/lump_sum_budget_planner/validation"


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _pred(pred_dict: dict, *, budget_regime: str) -> dict:
    """Tag a predicate dict with an applies_when budget_regime."""
    pred_dict["applies_when"] = {"budget_regime": budget_regime}
    return pred_dict


def _pred_unit_cost_resolved(pred_id: str, path: str) -> dict:
    return {
        "predicate_id": pred_id,
        "type": "schema",
        "function": "unit_cost_budget_resolved",
        "args": {"path": path},
        "applies_when": {"budget_regime": "unit_cost"},
        "fail_message": f"{pred_id} failed",
        "prose_condition": f"{pred_id} condition",
    }


def _gate09_library(repo_root: Path) -> Path:
    """A synthetic gate_09 mirroring the production instrument-conditional set."""
    preds = [
        # lump-sum branch
        _pred(
            pred_dir_non_empty("g08_p02", f"{_RECEIVED_REL}/"),
            budget_regime="lump_sum",
        ),
        _pred(
            pred_dir_non_empty("g08_p03", f"{_VALIDATION_REL}/"),
            budget_regime="lump_sum",
        ),
        # unit-cost branch
        _pred(
            pred_non_empty_json("g08_uc01", _UNIT_COST_BUDGET_REL),
            budget_regime="unit_cost",
        ),
        _pred_unit_cost_resolved("g08_uc03", _UNIT_COST_BUDGET_REL),
    ]
    return write_library(
        repo_root,
        [
            gate_entry(
                "gate_09_budget_consistency",
                "exit",
                "n07_budget_gate",
                preds,
                mandatory=True,
                bypass_prohibited=True,
                hard_block_on_missing_received_dir=True,
            )
        ],
    )


def _seed_instrument(repo_root: Path, instrument_type: str, budget_regime: str) -> None:
    """Seed a resolvable instrument profile (selected_call + both registries)."""
    write_json(
        repo_root / "docs/tier3_project_instantiation/call_binding/selected_call.json",
        {"instrument_type": instrument_type, "budget_regime": budget_regime},
    )
    write_json(
        repo_root
        / "docs/tier2a_instrument_schemas/extracted/section_schema_registry.json",
        {
            "instruments": [
                {
                    "instrument_type": instrument_type,
                    "part_b_page_limit_hard": 10,
                    "sections": [
                        {
                            "section_id": "1",
                            "section_name": "Excellence",
                            "mandatory": True,
                            "section_type": "criterion_section",
                        }
                    ],
                }
            ]
        },
    )
    write_json(
        repo_root
        / "docs/tier2a_instrument_schemas/extracted/instrument_registry.json",
        {
            "instruments": [
                {
                    "instrument_type": instrument_type,
                    "budget_regime": budget_regime,
                    "phases_in_scope": [1, 2, 3, 4, 5, 6, 7, 8],
                }
            ]
        },
    )


def _write_unit_cost_budget(repo_root: Path, run_id: str, *, resolved: bool) -> None:
    if resolved:
        artifact = {
            "schema_id": "orch.phase7.unit_cost_budget.v1",
            "run_id": run_id,
            "gate_pass_declaration": "pass",
            "unresolved_components": [],
            "total_eur": 209040.0,
        }
    else:
        artifact = {
            "schema_id": "orch.phase7.unit_cost_budget.v1",
            "run_id": run_id,
            "gate_pass_declaration": "fail",
            "unresolved_components": ["host_coefficient_unresolved"],
            "total_eur": None,
            "blocking_inconsistencies": [
                {
                    "inconsistency_id": "host_coefficient_unresolved",
                    "description": "host country unresolved",
                    "severity": "blocking",
                    "resolution": "unresolved",
                }
            ],
        }
    write_json(repo_root / _UNIT_COST_BUDGET_REL, artifact)


# ---------------------------------------------------------------------------
# Unit-cost branch
# ---------------------------------------------------------------------------


class TestUnitCostBranch:
    def test_pass_when_derivation_resolved(self, tmp_path: Path) -> None:
        """Unit-cost instrument + resolved derivation → gate passes; the
        lump-sum received/ predicates are skipped as not-applicable."""
        repo_root = make_repo_root(tmp_path)
        _, run_id = init_run(repo_root)
        _seed_instrument(repo_root, "MSCA-PF", "unit_cost")
        _write_unit_cost_budget(repo_root, run_id, resolved=True)

        # Deliberately DO NOT create received/ or validation/ content — those
        # lump-sum predicates must be skipped, not failed.
        lib = _gate09_library(repo_root)
        result = evaluate_gate(
            "gate_09_budget_consistency", run_id, repo_root, library_path=lib
        )

        assert result["status"] == "pass", result
        assert result.get("hard_block") is not True
        # The lump-sum predicates were recorded as skipped-not-applicable.
        skipped_ids = {
            s["predicate_id"]
            for s in result.get("skipped_not_applicable_predicates", [])
        }
        assert {"g08_p02", "g08_p03"} <= skipped_ids

    def test_block_when_derivation_unresolved_hard_blocks_phase8(
        self, tmp_path: Path
    ) -> None:
        """Unit-cost instrument + blocked derivation → gate fails, HARD_BLOCK
        freezes Phase 8 (categorical block preserved, §8.4)."""
        repo_root = make_repo_root(tmp_path)
        _, run_id = init_run(repo_root)
        _seed_instrument(repo_root, "MSCA-PF", "unit_cost")
        _write_unit_cost_budget(repo_root, run_id, resolved=False)

        lib = _gate09_library(repo_root)
        result = evaluate_gate(
            "gate_09_budget_consistency", run_id, repo_root, library_path=lib
        )

        assert result["status"] == "fail"
        assert result.get("hard_block") is True
        ctx = RunContext.load(repo_root, run_id)
        for node_id in PHASE_8_NODE_IDS:
            assert ctx.get_node_state(node_id) == "hard_block_upstream"

    def test_block_when_derivation_missing(self, tmp_path: Path) -> None:
        """Unit-cost instrument + no derivation artifact → gate fails + block."""
        repo_root = make_repo_root(tmp_path)
        _, run_id = init_run(repo_root)
        _seed_instrument(repo_root, "MSCA-PF", "unit_cost")
        # No unit_cost_budget.json written.
        lib = _gate09_library(repo_root)
        result = evaluate_gate(
            "gate_09_budget_consistency", run_id, repo_root, library_path=lib
        )
        assert result["status"] == "fail"


# ---------------------------------------------------------------------------
# Lump-sum branch (preserved verbatim)
# ---------------------------------------------------------------------------


class TestLumpSumBranch:
    def test_pass_when_received_present(self, tmp_path: Path) -> None:
        """Lump-sum instrument + received/validation present → gate passes; the
        unit-cost derivation predicates are skipped."""
        repo_root = make_repo_root(tmp_path)
        _, run_id = init_run(repo_root)
        _seed_instrument(repo_root, "RIA", "lump_sum")
        write_json(repo_root / _RECEIVED_REL / "response.json", {"response_id": "r1"})
        write_json(repo_root / _VALIDATION_REL / "val.json", {"valid": True})

        lib = _gate09_library(repo_root)
        result = evaluate_gate(
            "gate_09_budget_consistency", run_id, repo_root, library_path=lib
        )

        assert result["status"] == "pass", result
        skipped_ids = {
            s["predicate_id"]
            for s in result.get("skipped_not_applicable_predicates", [])
        }
        assert {"g08_uc01", "g08_uc03"} <= skipped_ids

    def test_block_when_received_missing_hard_blocks(self, tmp_path: Path) -> None:
        """Lump-sum instrument + missing received/ → fail + HARD_BLOCK (the
        existing lump-sum behaviour, unchanged)."""
        repo_root = make_repo_root(tmp_path)
        _, run_id = init_run(repo_root)
        _seed_instrument(repo_root, "RIA", "lump_sum")
        # received/ exists (from make_repo_root? no) — ensure absent/empty.
        lib = _gate09_library(repo_root)
        result = evaluate_gate(
            "gate_09_budget_consistency", run_id, repo_root, library_path=lib
        )
        assert result["status"] == "fail"
        assert result.get("hard_block") is True


# ---------------------------------------------------------------------------
# Fail-closed when instrument unresolvable
# ---------------------------------------------------------------------------


class TestInstrumentUnresolvable:
    def test_fail_closed_and_hard_block(self, tmp_path: Path) -> None:
        """A gate with applies_when predicates but no resolvable instrument
        profile fails closed (§12.4) and HARD_BLOCKs Phase 8."""
        repo_root = make_repo_root(tmp_path)
        _, run_id = init_run(repo_root)
        # No selected_call.json / registries seeded → regime unresolvable.
        lib = _gate09_library(repo_root)
        result = evaluate_gate(
            "gate_09_budget_consistency", run_id, repo_root, library_path=lib
        )

        assert result["status"] == "fail"
        assert result.get("hard_block") is True
        # The fail-closed marker is recorded as a failed deterministic predicate.
        failed_fns = {
            f["function"] for f in result["deterministic_predicates"]["failed"]
        }
        assert "instrument_budget_regime_resolvable" in failed_fns
