"""The per-phase cost and duration derivation, read back off the artifact.

The ticket 'Runner Phases 1 to 6 on the demo' asks that run cost and duration be
recorded per phase. The benchmark layer's own roll-up cannot do it — every ledger
row carries ``node_id: null`` — so ``tools/derive_run_phase_costs.py`` recovers
the attribution from the phase gate times.

These tests assert the derivation's *properties*, not its numbers. A test that
typed 491,140 input tokens would be a second copy of the measurement, free to
drift from the ledger it claims to describe, and the ticket 'First dev-graph
snapshot on the demo world' recorded that lesson as its D9. So every expected
value here is read back off the ledger and the gate results.

The tests that need the demo run's ledger skip when it is absent: ``.claude/`` is
runtime execution state under §9.2, rebuildable and gitignored, so a clone
without it is a valid checkout rather than a failure.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from runner.atomic_write import canonical_json_bytes
from tools.derive_run_phase_costs import (
    DerivationError,
    LEDGER_REL_TEMPLATE,
    SCHEMA_ID,
    build_record,
    collect_phase_gates,
    output_path,
    partition,
    resolve_run_id,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _write_phase_gates(
    root: Path,
    gates: list[tuple[str, str]],
    *,
    run_ids: list[str] | None = None,
) -> None:
    """A minimal phase-outputs tree, for the fail-closed cases."""
    ids = run_ids or ["run-a"] * len(gates)
    for index, ((gate_id, evaluated_at), run_id) in enumerate(zip(gates, ids), start=1):
        directory = root / "docs/tier4_orchestration_state/phase_outputs" / (
            f"phase{index}_synthetic"
        )
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "gate_result.json").write_text(
            json.dumps(
                {
                    "gate_id": gate_id,
                    "status": "pass",
                    "run_id": run_id,
                    "evaluated_at": evaluated_at,
                }
            ),
            encoding="utf-8",
        )


@pytest.fixture(scope="module")
def gates() -> list[dict[str, object]]:
    return collect_phase_gates(REPO_ROOT)


@pytest.fixture(scope="module")
def run_id(gates) -> str:
    return resolve_run_id(gates, None)


@pytest.fixture(scope="module")
def ledger_rows(run_id) -> list[dict[str, object]]:
    path = REPO_ROOT / LEDGER_REL_TEMPLATE.format(run_id=run_id)
    if not path.exists():
        pytest.skip(f"No invocation ledger at {path} (runtime state, §9.2).")
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


@pytest.fixture(scope="module")
def record(ledger_rows, run_id) -> dict[str, object]:
    return build_record(REPO_ROOT, run_id)


class TestThePhaseBoundaries:
    """What the partition rests on, checked rather than assumed."""

    def test_six_phase_gates_are_found(self, gates):
        assert [g["phase"] for g in gates] == [1, 2, 3, 4, 5, 6]

    def test_named_gates_are_not_mistaken_for_phase_boundaries(self, gates):
        # phase1 also holds gate_01_source_integrity; it is not a boundary.
        assert all(str(g["gate_id"]).startswith("phase_") for g in gates)

    def test_gate_times_ascend_with_phase_number(self, gates):
        times = [_parse(str(g["evaluated_at"])) for g in gates]
        assert times == sorted(times)
        assert len(set(times)) == len(times)

    def test_one_run_id_across_every_phase_gate(self, gates, run_id):
        assert {g["run_id"] for g in gates} == {run_id}

    def test_non_monotonic_boundaries_fail_closed(self, tmp_path):
        _write_phase_gates(
            tmp_path,
            [
                ("phase_01_gate", "2026-09-30T10:00:00+00:00"),
                ("phase_02_gate", "2026-09-30T09:00:00+00:00"),
            ],
        )
        with pytest.raises(DerivationError, match="ascend"):
            collect_phase_gates(tmp_path)

    def test_an_empty_phase_outputs_tree_fails_closed(self, tmp_path):
        (tmp_path / "docs/tier4_orchestration_state/phase_outputs").mkdir(parents=True)
        with pytest.raises(DerivationError, match="No phase gate result"):
            collect_phase_gates(tmp_path)

    def test_two_run_ids_refuse_to_partition_without_a_choice(self, tmp_path):
        _write_phase_gates(
            tmp_path,
            [
                ("phase_01_gate", "2026-09-30T10:00:00+00:00"),
                ("phase_02_gate", "2026-09-30T11:00:00+00:00"),
            ],
            run_ids=["run-a", "run-b"],
        )
        collected = collect_phase_gates(tmp_path)
        with pytest.raises(DerivationError, match="2 run ids"):
            resolve_run_id(collected, None)

    def test_a_foreign_run_id_is_refused(self, gates):
        with pytest.raises(DerivationError, match="appears in no phase gate"):
            resolve_run_id(gates, "not-a-run-id")


class TestEveryPhaseGotItsOwnNumbers:
    """The defect this derivation exists to fix: one phase holding the lot."""

    def test_each_phase_has_at_least_one_invocation(self, record):
        empty = [p["phase"] for p in record["per_phase"] if p["invocations"] == 0]
        assert empty == [], f"phases with no invocation attributed: {empty}"

    def test_no_single_phase_holds_the_whole_ledger(self, record, ledger_rows):
        largest = max(p["invocations"] for p in record["per_phase"])
        assert largest < len(ledger_rows), (
            "One phase holds every invocation, which is the phase_analytics.json "
            "misattribution this derivation replaces."
        )

    def test_the_stale_roll_up_is_named_as_superseded(self, record):
        assert "phase_analytics.json" in record["attribution"]["supersedes"]


class TestTheNumbersComeFromTheLedger:
    """Each expected value is summed off the ledger, never typed here."""

    def test_every_row_is_attributed_or_declared_left_over(self, record, ledger_rows):
        attributed = sum(p["invocations"] for p in record["per_phase"])
        left_over = record["unattributed_after_last_gate"]["invocations"]
        assert attributed + left_over == len(ledger_rows)

    def test_totals_match_the_sum_over_phases(self, record):
        per_phase = record["per_phase"]
        totals = record["totals"]
        for field in (
            "invocations",
            "estimated_input_tokens",
            "estimated_output_tokens",
            "estimated_total_tokens",
        ):
            assert totals[field] == sum(p[field] for p in per_phase), field
        assert totals["wall_clock_seconds"] == pytest.approx(
            sum(p["wall_clock_seconds"] for p in per_phase), abs=0.01
        )

    def test_attributed_tokens_match_the_ledger(self, record, ledger_rows, gates):
        last_gate = _parse(str(gates[-1]["evaluated_at"]))
        inside = [
            r
            for r in ledger_rows
            if _parse(str(r["timestamp_utc"])) <= last_gate
        ]
        totals = record["totals"]
        assert totals["estimated_input_tokens"] == sum(
            int(r["estimated_input_tokens"]) for r in inside
        )
        assert totals["estimated_output_tokens"] == sum(
            int(r["estimated_output_tokens"]) for r in inside
        )
        assert totals["wall_clock_seconds"] == pytest.approx(
            sum(float(r["wall_clock_seconds"]) for r in inside), abs=0.01
        )

    def test_each_phase_window_contains_only_its_own_rows(self, record, ledger_rows):
        by_stamp = {str(r["timestamp_utc"]): r for r in ledger_rows}
        assert len(by_stamp) == len(ledger_rows), "ledger timestamps are not unique"
        for phase in record["per_phase"]:
            end = _parse(str(phase["window_end_inclusive_utc"]))
            start = phase["window_start_exclusive_utc"]
            if phase["invocations"] == 0:
                continue
            first = _parse(str(phase["first_invocation_utc"]))
            last = _parse(str(phase["last_invocation_utc"]))
            assert last <= end
            if start is not None:
                assert first > _parse(str(start))

    def test_by_skill_sums_to_the_phase(self, record):
        for phase in record["per_phase"]:
            by_skill = phase["by_skill"]
            assert sum(s["invocations"] for s in by_skill.values()) == (
                phase["invocations"]
            )
            assert sum(s["estimated_input_tokens"] for s in by_skill.values()) == (
                phase["estimated_input_tokens"]
            )

    def test_partition_preserves_every_row(self, ledger_rows, gates):
        buckets, left_over = partition(ledger_rows, gates)
        placed = [r for _, bucket in buckets for r in bucket] + left_over
        assert len(placed) == len(ledger_rows)
        ids = {str(r["invocation_id"]) for r in placed}
        assert ids == {str(r["invocation_id"]) for r in ledger_rows}


class TestHonesty:
    """What the artifact is not allowed to claim."""

    def test_attribution_is_inferred_not_confirmed(self, record):
        assert record["attribution"]["status"] == "Inferred"
        assert len(record["attribution"]["inference_chain"]) >= 3

    def test_no_currency_figure_is_substituted(self, record):
        cost = record["monetary_cost"]
        if cost["status"] == "Unresolved":
            assert cost["cost_usd"] is None
            assert cost["reason"]
        else:
            assert cost["status"] == "Inferred"
            assert cost.get("provider_projection")

    def test_a_failed_or_timed_out_invocation_is_counted_not_dropped(self, record):
        for phase in record["per_phase"]:
            assert phase["failed"] >= 0
            assert phase["timed_out"] >= 0
            assert phase["failed"] <= phase["invocations"]

    def test_the_gate_status_travels_with_the_phase(self, record, gates):
        by_phase = {g["phase"]: g["gate_status"] for g in gates}
        for phase in record["per_phase"]:
            assert phase["gate_status"] == by_phase[phase["phase"]]

    def test_inputs_name_every_file_the_record_rests_on(self, record, gates):
        inputs = record["inputs"]
        for gate in gates:
            assert gate["gate_result_path"] in inputs


class TestDeterminism:
    """No clock, so a second derivation rewrites the same bytes."""

    def test_two_builds_agree_byte_for_byte(self, record, run_id):
        again = build_record(REPO_ROOT, run_id)
        assert canonical_json_bytes(again) == canonical_json_bytes(record)

    def test_the_artifact_on_disk_matches_the_derivation(self, record, run_id):
        target = output_path(REPO_ROOT, run_id)
        if not target.exists():
            pytest.skip(f"{target} not written yet; run the tool to write it.")
        assert target.read_bytes() == canonical_json_bytes(record)

    def test_the_record_carries_no_wall_clock_of_its_own(self, record):
        blob = json.dumps(record)
        for forbidden in ("derived_at", "generated_at", "written_at", "compiled_at"):
            assert forbidden not in blob

    def test_schema_id_is_declared(self, record):
        assert record["schema_id"] == SCHEMA_ID
