"""
Benchmark analytics engine — pure aggregation from Phase A ledger records.

Transforms a list of invocation record dicts (deserialized from
``invocation_ledger.jsonl``) into structured analytics artifacts:

- **Phase analytics**: per-phase and per-node aggregation
- **Token economics**: token distribution by type, skill, predicate

No side effects, no I/O, no external dependencies beyond ``timing.py``.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from runner.benchmark.timing import build_timing_profile


# ---------------------------------------------------------------------------
# Phase analytics
# ---------------------------------------------------------------------------

def build_phase_analytics(
    records: list[dict],
    *,
    run_id: str = "",
    phase_scope: int | None = None,
    run_summary: dict | None = None,
    phase_a_summary: dict | None = None,
) -> dict[str, Any]:
    """Build phase-level analytics from invocation record dicts.

    Parameters
    ----------
    records
        Deserialized invocation records (each a dict from JSONL).
    run_id
        The run identifier.
    phase_scope
        The phase number this run was scoped to, if any.
    run_summary
        Optional ``run_summary.json`` dict for phase/node inference.
    phase_a_summary
        Optional Phase A ``run_benchmark_summary.json`` dict.
    """
    # Enrich records with inferred phase and node_id
    enriched = [
        _enrich_record(r, run_summary=run_summary, phase_a_summary=phase_a_summary)
        for r in records
    ]

    phases_observed = sorted({r["_phase"] for r in enriched if r["_phase"] is not None})
    nodes_observed = sorted({r.get("node_id") for r in enriched if r.get("node_id")})

    # Per-phase aggregation
    by_phase: dict[int, list[dict]] = defaultdict(list)
    for r in enriched:
        p = r["_phase"]
        if p is not None:
            by_phase[p].append(r)

    phase_details: dict[str, Any] = {}
    for phase_num in sorted(by_phase.keys()):
        phase_recs = by_phase[phase_num]
        phase_details[str(phase_num)] = _aggregate_phase(phase_recs)

    # Per-node aggregation
    by_node: dict[str, list[dict]] = defaultdict(list)
    for r in enriched:
        nid = r.get("node_id")
        if nid:
            by_node[nid].append(r)

    node_details: dict[str, Any] = {}
    for nid in sorted(by_node.keys()):
        node_recs = by_node[nid]
        node_details[nid] = _aggregate_phase(node_recs)

    total_wc = None
    if phase_a_summary:
        total_wc = phase_a_summary.get("total_wall_clock_seconds")

    return {
        "benchmark_schema_version": "1.0.0",
        "run_id": run_id,
        "phase_scope": phase_scope,
        "phases_observed": phases_observed,
        "nodes_observed": nodes_observed,
        "total_invocations": len(records),
        "per_phase": phase_details,
        "per_node": node_details,
    }


# ---------------------------------------------------------------------------
# Token economics
# ---------------------------------------------------------------------------

def build_token_economics(
    records: list[dict],
    *,
    run_id: str = "",
    run_summary: dict | None = None,
    phase_a_summary: dict | None = None,
) -> dict[str, Any]:
    """Build token economics from invocation record dicts.

    Parameters
    ----------
    records
        Deserialized invocation records (each a dict from JSONL).
    run_id
        The run identifier.
    run_summary
        Optional ``run_summary.json`` dict for phase inference.
    phase_a_summary
        Optional Phase A ``run_benchmark_summary.json`` dict.
    """
    total_in = sum(r.get("estimated_input_tokens", 0) for r in records)
    total_out = sum(r.get("estimated_output_tokens", 0) for r in records)
    total_all = total_in + total_out

    # By invocation type
    by_type: dict[str, dict[str, int]] = defaultdict(lambda: {"input": 0, "output": 0})
    for r in records:
        t = r.get("invocation_type", "unknown")
        by_type[t]["input"] += r.get("estimated_input_tokens", 0)
        by_type[t]["output"] += r.get("estimated_output_tokens", 0)

    tokens_by_type = {
        k: {
            "estimated_input_tokens": v["input"],
            "estimated_output_tokens": v["output"],
            "estimated_total_tokens": v["input"] + v["output"],
        }
        for k, v in sorted(by_type.items())
    }

    # By skill id
    by_skill: dict[str, dict[str, int]] = defaultdict(lambda: {"input": 0, "output": 0})
    for r in records:
        sid = r.get("skill_id")
        if sid:
            by_skill[sid]["input"] += r.get("estimated_input_tokens", 0)
            by_skill[sid]["output"] += r.get("estimated_output_tokens", 0)

    tokens_by_skill = {
        k: {
            "estimated_input_tokens": v["input"],
            "estimated_output_tokens": v["output"],
            "estimated_total_tokens": v["input"] + v["output"],
        }
        for k, v in sorted(by_skill.items())
    }

    # By semantic predicate id
    by_pred: dict[str, dict[str, int]] = defaultdict(lambda: {"input": 0, "output": 0})
    for r in records:
        pid = r.get("predicate_id")
        if pid:
            by_pred[pid]["input"] += r.get("estimated_input_tokens", 0)
            by_pred[pid]["output"] += r.get("estimated_output_tokens", 0)

    tokens_by_predicate = {
        k: {
            "estimated_input_tokens": v["input"],
            "estimated_output_tokens": v["output"],
            "estimated_total_tokens": v["input"] + v["output"],
        }
        for k, v in sorted(by_pred.items())
    }

    # Largest invocation by estimated total tokens
    largest_by_tokens = _find_largest(records, "estimated_total_tokens")
    largest_by_prompt = _find_largest(records, "prompt_chars")

    # TAPM vs cli-prompt totals
    tapm_in = sum(
        r.get("estimated_input_tokens", 0)
        for r in records if r.get("execution_mode") == "tapm"
    )
    tapm_out = sum(
        r.get("estimated_output_tokens", 0)
        for r in records if r.get("execution_mode") == "tapm"
    )
    cli_in = sum(
        r.get("estimated_input_tokens", 0)
        for r in records if r.get("execution_mode") == "cli-prompt"
    )
    cli_out = sum(
        r.get("estimated_output_tokens", 0)
        for r in records if r.get("execution_mode") == "cli-prompt"
    )

    # Semantic predicate token total
    sem_pred_total = sum(
        r.get("estimated_input_tokens", 0) + r.get("estimated_output_tokens", 0)
        for r in records if r.get("invocation_type") == "semantic_predicate"
    )

    # Phase 8 vs Phases 1-7
    enriched = [
        _enrich_record(r, run_summary=run_summary, phase_a_summary=phase_a_summary)
        for r in records
    ]
    phase8_total = sum(
        r.get("estimated_input_tokens", 0) + r.get("estimated_output_tokens", 0)
        for r in enriched if r.get("_phase") == 8
    )
    phases_1_7_total = sum(
        r.get("estimated_input_tokens", 0) + r.get("estimated_output_tokens", 0)
        for r in enriched if r.get("_phase") is not None and 1 <= r["_phase"] <= 7
    )

    return {
        "run_id": run_id,
        "total_estimated_input_tokens": total_in,
        "total_estimated_output_tokens": total_out,
        "total_estimated_tokens": total_all,
        "tokens_by_invocation_type": tokens_by_type,
        "tokens_by_skill_id": tokens_by_skill,
        "tokens_by_semantic_predicate_id": tokens_by_predicate,
        "largest_invocation_by_estimated_total_tokens": largest_by_tokens,
        "largest_invocation_by_prompt_chars": largest_by_prompt,
        "tapm_vs_cli_prompt": {
            "tapm": {
                "estimated_input_tokens": tapm_in,
                "estimated_output_tokens": tapm_out,
                "estimated_total_tokens": tapm_in + tapm_out,
            },
            "cli_prompt": {
                "estimated_input_tokens": cli_in,
                "estimated_output_tokens": cli_out,
                "estimated_total_tokens": cli_in + cli_out,
            },
        },
        "phase_8_estimated_total_tokens": phase8_total,
        "phases_1_7_estimated_total_tokens": phases_1_7_total,
        "semantic_predicate_estimated_total_tokens": sem_pred_total,
        "warning": "All token values are estimates based on character-to-token ratios. They are not billing-grade.",
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

# Node-id prefix to phase number mapping
_NODE_PHASE_MAP: dict[str, int] = {
    "n01": 1, "n02": 2, "n03": 3, "n04": 4,
    "n05": 5, "n06": 6, "n07": 7,
    "n08a": 8, "n08b": 8, "n08c": 8, "n08d": 8, "n08e": 8, "n08f": 8,
}


def _infer_phase_from_node_id(node_id: str | None) -> int | None:
    """Infer phase number from node_id prefix."""
    if not node_id:
        return None
    for prefix, phase in _NODE_PHASE_MAP.items():
        if node_id.startswith(prefix):
            return phase
    return None


def _resolve_single_node(
    run_summary: dict | None,
    phase_a_summary: dict | None,
) -> str | None:
    """Identify an unambiguous single node from available summaries.

    Returns a node_id only when exactly one node can be determined.
    Precedence:
    B. run_summary.phase_scope_nodes has exactly one entry
    C. run_summary.dispatched_nodes has exactly one entry
    D. phase_a_summary.node_records has exactly one dispatched entry
    """
    try:
        if run_summary:
            # B: phase_scope_nodes
            psn = run_summary.get("phase_scope_nodes")
            if isinstance(psn, list) and len(psn) == 1 and isinstance(psn[0], str):
                return psn[0]
            # C: dispatched_nodes
            dn = run_summary.get("dispatched_nodes")
            if isinstance(dn, list) and len(dn) == 1 and isinstance(dn[0], str):
                return dn[0]
        if phase_a_summary:
            # D: node_records with dispatched=true
            nr = phase_a_summary.get("node_records")
            if isinstance(nr, list):
                dispatched = [
                    e["node_id"]
                    for e in nr
                    if isinstance(e, dict)
                    and e.get("dispatched") is True
                    and isinstance(e.get("node_id"), str)
                ]
                if len(dispatched) == 1:
                    return dispatched[0]
    except Exception:
        pass
    return None


def _enrich_record(
    record: dict,
    *,
    run_summary: dict | None = None,
    phase_a_summary: dict | None = None,
) -> dict:
    """Return a copy of *record* with ``_phase`` and possibly ``node_id`` enriched.

    Inference precedence
    --------------------
    A. record.node_id exists -> phase from node_id prefix; keep node_id.
    B. node_id missing, run_summary.phase_scope_nodes has exactly 1 node
       -> assign that node_id; phase = phase_scope.
    C. node_id missing, run_summary.dispatched_nodes has exactly 1 node
       -> assign that node_id; phase from node_id or phase_scope.
    D. node_id missing, phase_a_summary.node_records has exactly 1
       dispatched node -> assign that node_id; phase from node_id.
    E. Multiple nodes possible -> do not guess node_id.  Phase may still
       be inferred from run_summary.phase_scope if unambiguous.
    """
    enriched = dict(record)
    node_id = record.get("node_id")

    # A: record already has node_id
    if node_id:
        enriched["_phase"] = _infer_phase_from_node_id(node_id)
        return enriched

    # B/C/D: try to resolve a single unambiguous node
    inferred_node = _resolve_single_node(run_summary, phase_a_summary)

    if inferred_node:
        enriched["node_id"] = inferred_node
        phase = _infer_phase_from_node_id(inferred_node)
        if phase is None and run_summary:
            ps = run_summary.get("phase_scope")
            if isinstance(ps, int):
                phase = ps
        enriched["_phase"] = phase
        return enriched

    # E: cannot determine node, but phase_scope may still be unambiguous
    phase = None
    if run_summary:
        ps = run_summary.get("phase_scope")
        if isinstance(ps, int):
            phase = ps
    enriched["_phase"] = phase
    return enriched


def _aggregate_phase(records: list[dict]) -> dict[str, Any]:
    """Aggregate statistics for a group of records (phase or node)."""
    invocations = len(records)
    est_in = sum(r.get("estimated_input_tokens", 0) for r in records)
    est_out = sum(r.get("estimated_output_tokens", 0) for r in records)
    est_total = est_in + est_out

    durations = [
        r["wall_clock_seconds"]
        for r in records
        if isinstance(r.get("wall_clock_seconds"), (int, float))
    ]
    wc_seconds = round(sum(durations), 4) if durations else None

    tapm_count = sum(1 for r in records if r.get("execution_mode") == "tapm")
    cli_count = sum(1 for r in records if r.get("execution_mode") == "cli-prompt")

    sem_pred_count = sum(
        1 for r in records if r.get("invocation_type") == "semantic_predicate"
    )
    failed_count = sum(
        1 for r in records
        if r.get("response_status") in ("error", "timeout")
    )
    timeout_count = sum(
        1 for r in records if r.get("response_status") == "timeout"
    )

    return {
        "invocations": invocations,
        "estimated_input_tokens": est_in,
        "estimated_output_tokens": est_out,
        "estimated_total_tokens": est_total,
        "wall_clock_seconds": wc_seconds,
        "tapm_count": tapm_count,
        "cli_prompt_count": cli_count,
        "semantic_predicate_count": sem_pred_count,
        "failed_count": failed_count,
        "timeout_count": timeout_count,
    }


def _find_largest(
    records: list[dict],
    key: str,
) -> dict[str, Any] | None:
    """Find the record with the largest value for *key*.

    For ``"estimated_total_tokens"``, computes input + output.
    For ``"prompt_chars"``, computes system_prompt_chars + user_prompt_chars.
    """
    if not records:
        return None

    best_val = -1
    best_rec: dict | None = None

    for r in records:
        if key == "estimated_total_tokens":
            val = r.get("estimated_input_tokens", 0) + r.get("estimated_output_tokens", 0)
        elif key == "prompt_chars":
            val = r.get("system_prompt_chars", 0) + r.get("user_prompt_chars", 0)
        else:
            val = r.get(key, 0)

        if val > best_val:
            best_val = val
            best_rec = r

    if best_rec is None:
        return None

    return {
        "invocation_id": best_rec.get("invocation_id"),
        "skill_id": best_rec.get("skill_id"),
        "predicate_id": best_rec.get("predicate_id"),
        "invocation_type": best_rec.get("invocation_type"),
        "value": best_val,
    }
