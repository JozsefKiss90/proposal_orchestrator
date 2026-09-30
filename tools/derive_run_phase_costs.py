"""Derive per-phase cost and duration for a runner run, from the ledger.

The benchmark layer already writes an invocation ledger, but it cannot say which
phase an invocation belonged to. ``runner/benchmark/transport_hook.py`` never
sets ``node_id``, so every ledger row carries ``node_id: null``, and
``runner/benchmark/analytics.py`` falls back to inferring the node from the run
summary's single dispatched node. The ledger is append-only across dispatches,
and a run summary names only the latest dispatch, so on a run whose phases were
dispatched one at a time under one run id that inference attributes the whole
cumulative ledger to a single phase. ``phase_analytics.json`` is wrong in
exactly that way for the instance-two demo run.

This tool recovers the attribution the ledger does support. Each phase gate
writes its ``evaluated_at`` into ``gate_result.json``, and a phase's invocations
all fall between the previous phase's gate and its own. Partitioning the ledger
on those boundaries gives per-phase invocations, tokens and wall clock without
guessing.

The attribution is **Inferred**, not Confirmed (§12.2). It rests on the ledger
carrying no node_id and on two structural facts, both checked here rather than
assumed: the phase gates' ``evaluated_at`` values ascend with phase number, and
every gate result carries the same run id. Either check failing is a finding to
record, not a reason to widen a window, so both fail closed.

Monetary cost is **Unresolved** and is written as null. ``provider_projection.json``
evaluated zero providers for this run, so no rate exists to price the tokens
against, and §8.3's rule against substituting a figure applies to a cost as much
as to a budget line.

Everything the artifact holds is measured off the ledger and the gate results.
Nothing is typed: no invocation count, no token total, no duration. The artifact
carries no clock, so a second run over the same inputs rewrites the same bytes.

Run it from the repository root::

    py -3.10 -m tools.derive_run_phase_costs            # write
    py -3.10 -m tools.derive_run_phase_costs --check    # exit 1 if anything differs

Constitutional standing: an authoring tool, not a runtime component. It reads
Tier 4 phase outputs and the runtime ledger under ``.claude/``, writes one Tier 4
artifact, evaluates no gate and invokes no Claude. Per §9.2 the ledger is runtime
execution state and not source truth, which is why the durable numbers belong in
``docs/`` where this tool puts them.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from runner.atomic_write import atomic_write_json, canonical_json_bytes  # noqa: E402

SCHEMA_ID = "orch.run_cost.per_phase.v1"

PHASE_OUTPUTS_REL = "docs/tier4_orchestration_state/phase_outputs"
OUTPUT_DIR_REL = "docs/tier4_orchestration_state/run_cost"
LEDGER_REL_TEMPLATE = ".claude/benchmark/{run_id}/invocation_ledger.jsonl"
PROJECTION_REL_TEMPLATE = ".claude/benchmark/{run_id}/provider_projection.json"

#: ``phase_01_gate`` -> 1. The phase gate of a phase directory; ``gate_01_result``
#: and the other named gates are not phase boundaries and are not matched.
_PHASE_GATE_ID = re.compile(r"^phase_(\d{2})_gate$")


class DerivationError(RuntimeError):
    """A structural assumption this derivation depends on does not hold."""


# ── inputs ────────────────────────────────────────────────────────────────────


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value)


def collect_phase_gates(repo_root: Path) -> list[dict[str, Any]]:
    """The phase gates in ascending phase order, with their evaluation times.

    Reads every ``phase*/gate_result.json`` under the phase outputs directory and
    keeps the ones whose ``gate_id`` is a phase gate. Fails closed when the
    evaluation times do not ascend with phase number, because a partition on
    non-monotonic boundaries would silently mix two phases' invocations.
    """
    gates: list[dict[str, Any]] = []
    for path in sorted((repo_root / PHASE_OUTPUTS_REL).glob("phase*/gate_result.json")):
        result = _read_json(path)
        match = _PHASE_GATE_ID.match(str(result.get("gate_id", "")))
        if match is None:
            continue
        gates.append(
            {
                "phase": int(match.group(1)),
                "gate_id": result["gate_id"],
                "gate_status": result["status"],
                "run_id": result["run_id"],
                "evaluated_at": result["evaluated_at"],
                "gate_result_path": str(path.relative_to(repo_root)).replace("\\", "/"),
            }
        )

    if not gates:
        raise DerivationError(
            f"No phase gate result found under {PHASE_OUTPUTS_REL}. "
            "Nothing to partition the ledger on."
        )

    gates.sort(key=lambda g: g["phase"])
    times = [_parse_ts(g["evaluated_at"]) for g in gates]
    for earlier, later, before, after in zip(times, times[1:], gates, gates[1:]):
        if later <= earlier:
            raise DerivationError(
                f"{after['gate_id']} was evaluated at {after['evaluated_at']}, "
                f"not after {before['gate_id']} at {before['evaluated_at']}. "
                "Phase gate times must ascend with phase number for a "
                "timestamp partition to attribute invocations to one phase."
            )
    return gates


def resolve_run_id(gates: list[dict[str, Any]], requested: str | None) -> str:
    """The one run id every phase gate carries, or the requested one.

    Fails closed on a mixed set: a ledger belongs to one run, and partitioning
    one run's ledger on another run's gate times would produce numbers that
    describe neither.
    """
    observed = sorted({g["run_id"] for g in gates})
    if requested is not None:
        if requested not in observed:
            raise DerivationError(
                f"Requested run id {requested!r} appears in no phase gate result. "
                f"The phase gates carry {observed}."
            )
        return requested
    if len(observed) != 1:
        raise DerivationError(
            f"The phase gate results carry {len(observed)} run ids: {observed}. "
            "Pass --run-id to name the run whose ledger should be partitioned."
        )
    return observed[0]


def read_ledger(repo_root: Path, run_id: str) -> list[dict[str, Any]]:
    path = repo_root / LEDGER_REL_TEMPLATE.format(run_id=run_id)
    if not path.exists():
        raise DerivationError(
            f"No invocation ledger at {path}. The benchmark layer writes it per "
            "run; without it there is nothing to measure."
        )
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not rows:
        raise DerivationError(f"The invocation ledger at {path} holds no rows.")
    foreign = sorted({r.get("run_id") for r in rows if r.get("run_id") != run_id})
    if foreign:
        raise DerivationError(
            f"The ledger at {path} holds rows for other runs: {foreign}."
        )
    return rows


def read_monetary_cost(repo_root: Path, run_id: str) -> dict[str, Any]:
    """What the provider projection says a currency cost would rest on.

    Returns the projection's own numbers when it priced any provider, and an
    explicit Unresolved otherwise. It never prices the tokens itself.
    """
    path = repo_root / PROJECTION_REL_TEMPLATE.format(run_id=run_id)
    rel = PROJECTION_REL_TEMPLATE.format(run_id=run_id)
    if not path.exists():
        return {
            "cost_usd": None,
            "status": "Unresolved",
            "reason": f"No provider projection at {rel}.",
        }
    projection = _read_json(path)
    providers = projection.get("providers_evaluated")
    if isinstance(providers, list):
        evaluated = len(providers)
    else:
        evaluated = int(projection.get("total_providers_evaluated") or 0)
    if evaluated == 0:
        return {
            "cost_usd": None,
            "status": "Unresolved",
            "reason": (
                f"{rel} evaluated 0 providers, so no rate exists to price this "
                "run's tokens against. A figure is not substituted (§8.3)."
            ),
            "provider_projection": rel,
        }
    return {
        "cost_usd": projection.get("lowest_projected_cost_usd"),
        "status": "Inferred",
        "reason": (
            f"{rel} priced {evaluated} providers; the figure is the lowest "
            "projected cost it reports, not a billed amount."
        ),
        "provider_projection": rel,
        "provider": projection.get("lowest_projected_cost_provider"),
    }


# ── partition and measurement ─────────────────────────────────────────────────


def partition(
    rows: list[dict[str, Any]], gates: list[dict[str, Any]]
) -> tuple[list[tuple[dict[str, Any], list[dict[str, Any]]]], list[dict[str, Any]]]:
    """Ledger rows grouped by the phase gate that closed their phase.

    A row belongs to the earliest phase whose gate was evaluated at or after the
    row's timestamp. Rows timestamped after the last phase gate are returned
    separately rather than folded into the last phase: they belong to a dispatch
    this derivation cannot see the end of.
    """
    ordered = sorted(rows, key=lambda r: _parse_ts(r["timestamp_utc"]))
    buckets: list[tuple[dict[str, Any], list[dict[str, Any]]]] = [
        (gate, []) for gate in gates
    ]
    unattributed: list[dict[str, Any]] = []
    for row in ordered:
        stamp = _parse_ts(row["timestamp_utc"])
        for gate, bucket in buckets:
            if stamp <= _parse_ts(gate["evaluated_at"]):
                bucket.append(row)
                break
        else:
            unattributed.append(row)
    return buckets, unattributed


def _measure(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Every number here is summed or counted off *rows*."""
    if not rows:
        return {
            "invocations": 0,
            "estimated_input_tokens": 0,
            "estimated_output_tokens": 0,
            "estimated_total_tokens": 0,
            "wall_clock_seconds": 0.0,
            "span_seconds": 0.0,
            "first_invocation_utc": None,
            "last_invocation_utc": None,
            "execution_modes": {},
            "models": [],
            "failed": 0,
            "timed_out": 0,
            "by_skill": {},
        }

    stamps = [_parse_ts(r["timestamp_utc"]) for r in rows]
    inputs = sum(int(r["estimated_input_tokens"]) for r in rows)
    outputs = sum(int(r["estimated_output_tokens"]) for r in rows)

    modes: dict[str, int] = {}
    for row in rows:
        mode = str(row.get("execution_mode"))
        modes[mode] = modes.get(mode, 0) + 1

    by_skill: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = str(row.get("skill_id") or row.get("predicate_id") or "unnamed")
        entry = by_skill.setdefault(
            key,
            {
                "invocations": 0,
                "estimated_input_tokens": 0,
                "estimated_output_tokens": 0,
                "wall_clock_seconds": 0.0,
            },
        )
        entry["invocations"] += 1
        entry["estimated_input_tokens"] += int(row["estimated_input_tokens"])
        entry["estimated_output_tokens"] += int(row["estimated_output_tokens"])
        entry["wall_clock_seconds"] = round(
            entry["wall_clock_seconds"] + float(row["wall_clock_seconds"]), 3
        )

    return {
        "invocations": len(rows),
        "estimated_input_tokens": inputs,
        "estimated_output_tokens": outputs,
        "estimated_total_tokens": inputs + outputs,
        "wall_clock_seconds": round(
            sum(float(r["wall_clock_seconds"]) for r in rows), 3
        ),
        "span_seconds": round((max(stamps) - min(stamps)).total_seconds(), 3),
        "first_invocation_utc": min(stamps).isoformat(),
        "last_invocation_utc": max(stamps).isoformat(),
        "execution_modes": dict(sorted(modes.items())),
        "models": sorted({str(r.get("model")) for r in rows}),
        "failed": sum(1 for r in rows if r.get("response_status") != "success"),
        "timed_out": sum(
            1 for r in rows if str(r.get("error_class") or "").endswith("TimeoutError")
        ),
        "by_skill": {k: by_skill[k] for k in sorted(by_skill)},
    }


def build_record(repo_root: Path, requested_run_id: str | None = None) -> dict[str, Any]:
    """The per-phase cost and duration record, derived end to end."""
    gates = collect_phase_gates(repo_root)
    run_id = resolve_run_id(gates, requested_run_id)
    gates = [g for g in gates if g["run_id"] == run_id]
    rows = read_ledger(repo_root, run_id)
    buckets, unattributed = partition(rows, gates)

    per_phase = []
    window_start: str | None = None
    for gate, bucket in buckets:
        per_phase.append(
            {
                "phase": gate["phase"],
                "gate_id": gate["gate_id"],
                "gate_status": gate["gate_status"],
                "gate_result_path": gate["gate_result_path"],
                "window_start_exclusive_utc": window_start,
                "window_end_inclusive_utc": gate["evaluated_at"],
                **_measure(bucket),
            }
        )
        window_start = gate["evaluated_at"]

    attributed = [row for _, bucket in buckets for row in bucket]
    totals = _measure(attributed)
    totals.pop("by_skill")

    return {
        "schema_id": SCHEMA_ID,
        "run_id": run_id,
        "phases_covered": [g["phase"] for g in gates],
        "attribution": {
            "status": "Inferred",
            "method": (
                "Each ledger row is attributed to the earliest phase whose gate "
                "was evaluated at or after the row's timestamp."
            ),
            "inference_chain": [
                "Every ledger row carries node_id: null, because "
                "runner/benchmark/transport_hook.py does not set it.",
                "A phase's invocations therefore cannot be read off the row; "
                "they have to be bounded in time.",
                "A phase is dispatched after the previous phase's gate is "
                "evaluated, and its own gate is evaluated after its last "
                "invocation, so the two gate times bound it.",
                "The phase gates' evaluated_at values are checked to ascend "
                "with phase number, and every gate result is checked to carry "
                "this run id. Either check failing aborts the derivation.",
            ],
            "why_not_confirmed": (
                "No artifact records which phase an invocation belonged to. The "
                "attribution is sound but reconstructed, so it is Inferred "
                "under §12.2 and not Confirmed."
            ),
            "supersedes": (
                f".claude/benchmark/{run_id}/phase_analytics.json, which "
                "attributes this run's whole cumulative ledger to one phase."
            ),
        },
        "monetary_cost": read_monetary_cost(repo_root, run_id),
        "inputs": [
            LEDGER_REL_TEMPLATE.format(run_id=run_id),
            PROJECTION_REL_TEMPLATE.format(run_id=run_id),
            *[g["gate_result_path"] for g in gates],
        ],
        "per_phase": per_phase,
        "totals": totals,
        "unattributed_after_last_gate": _measure(unattributed),
        "note": (
            "Token counts are the benchmark layer's own estimates, not a "
            "provider's billed usage. wall_clock_seconds sums the invocations; "
            "span_seconds measures first to last invocation in the window and "
            "so includes the gaps between them."
        ),
    }


# ── entry point ───────────────────────────────────────────────────────────────


def output_path(repo_root: Path, run_id: str) -> Path:
    return repo_root / OUTPUT_DIR_REL / f"{run_id}.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Derive per-phase cost and duration for a runner run by "
            "partitioning its invocation ledger on the phase gate times."
        )
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root (default: the root this tool lives in).",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Run to derive. Default: the one run id every phase gate carries.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Write nothing; exit 1 if the artifact on disk would change.",
    )
    args = parser.parse_args(argv)

    repo_root = args.repo_root.resolve()
    try:
        record = build_record(repo_root, args.run_id)
    except DerivationError as exc:
        print(f"[BLOCKED] {exc}", file=sys.stderr)
        return 2

    target = output_path(repo_root, record["run_id"])
    expected = canonical_json_bytes(record)

    if args.check:
        if not target.exists():
            print(f"[DIFFERS] {target} does not exist.", file=sys.stderr)
            return 1
        if target.read_bytes() != expected:
            print(f"[DIFFERS] {target} would change.", file=sys.stderr)
            return 1
        print(f"[OK] {target.relative_to(repo_root)} is unchanged.")
        return 0

    atomic_write_json(record, target)

    rel = str(target.relative_to(repo_root)).replace("\\", "/")
    print(f"Wrote {rel}")
    print(f"  run {record['run_id']}")
    header = (
        f"  {'phase':>5}  {'inv':>4}  {'in tok':>9}  {'out tok':>8}  "
        f"{'wall s':>9}  {'span s':>9}"
    )
    print(header)
    for phase in record["per_phase"]:
        print(
            f"  {phase['phase']:>5}  {phase['invocations']:>4}  "
            f"{phase['estimated_input_tokens']:>9,}  "
            f"{phase['estimated_output_tokens']:>8,}  "
            f"{phase['wall_clock_seconds']:>9,.1f}  "
            f"{phase['span_seconds']:>9,.1f}"
        )
    totals = record["totals"]
    print(
        f"  {'total':>5}  {totals['invocations']:>4}  "
        f"{totals['estimated_input_tokens']:>9,}  "
        f"{totals['estimated_output_tokens']:>8,}  "
        f"{totals['wall_clock_seconds']:>9,.1f}  "
        f"{totals['span_seconds']:>9,.1f}"
    )
    left_over = record["unattributed_after_last_gate"]["invocations"]
    if left_over:
        print(f"  {left_over} invocation(s) fall after the last phase gate.")
    cost = record["monetary_cost"]
    print(f"  cost_usd: {cost['cost_usd']} ({cost['status']}) — {cost['reason']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
