"""
Phase-8 checkpoint publisher — deterministic node-body component (CHK-1).

This module publishes ``phase8_checkpoint.json`` to Tier 4.  It is a
**deterministic component** (CLAUDE.md §17.5.3 / C2, bound in the manifest per
§16.5 / C3): a pure-Python, Claude-free node-body pass that reads declared input
artifacts and writes a canonical artifact via an atomic write.  It replaces the
retired ``checkpoint-publish`` skill, which was found to be 100% mechanical
(decision_log/chk-1-checkpoint-provenance-quad_2026-07-24.json).

What it does
------------
For node ``n08f_revision`` it confirms the six Phase-8 gate results and writes
an immutable checkpoint asserting that Phase 8 completed with a known validated
state.  The one thing that is *not* a plain equality check is the cross-run
``run_id`` case:

Phase-scoped runs (``--phase 8``) bootstrap phases 1–7 from a prior run's
durable gate evidence, so those gate results legitimately carry a **prior**
``run_id`` (``runner/dag_scheduler.py`` ``bootstrap_phase_prerequisites``).  A
gate whose durable ``run_id`` differs from the current run's is authorized here
by **deterministic set-membership** against the ``accepted_upstream_gates``
record the bootstrap wrote to the run manifest — the same record the
gate-evaluation path already consults (``gate_pass_predicates``
``_check_continuation_acceptance``).  For each authorized cross-run gate the
component records a provenance quad
``{gate_id, original_run_id, evidence_path, input_fingerprint, versions}`` —
every field copied **verbatim** from the durable gate result — into an optional
``inherited_gate_provenance`` array (the ``inherited_artifacts`` idiom).  This
makes the durable checkpoint self-consistent and auditable against durable
Tier-4 evidence without ever validating inheritance against clearable
``.claude/runs/`` state at read time, and without ever falsifying it by
re-stamping.

Determinism guarantee
---------------------
Pure lookup + verbatim copy over durable gate results and the deterministic
``accepted_upstream_gates`` set membership.  No inference, no domain reasoning,
no Claude.  The single non-deterministic field is ``published_at`` — a
publication stamp like ``gate_result.evaluated_at``, excluded from the replay
invariant.  The additive ``inherited_gate_provenance`` array is **omitted when
empty**, so an all-current-run checkpoint is byte-identical to the pre-CHK-1
output.

Fail-closed (§12.4, §13.4)
--------------------------
Any structural fault — a missing/malformed/non-pass/wrong-schema gate result, or
a cross-run gate that is **not** authorized by ``accepted_upstream_gates`` —
raises :class:`CheckpointPublishError`.  The agent runtime surfaces a raised
component fault as ``AGENT_EXECUTION_ERROR`` / ``can_evaluate_exit_gate=False``,
so the exit gate (gate_12) is skipped and n08f blocks ``blocked_at_exit`` — the
fail-closed fires **before** anything is written (no premature-published-
checkpoint hazard).  A checkpoint already published with ``status: "published"``
is immutable: re-publishing raises rather than overwriting.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from runner.atomic_write import atomic_write_json
from runner.gate_result_registry import (
    GATE_RESULT_PATHS,
    GATE_RESULT_SCHEMA_ID,
    GATE_RESULT_VERSION_FIELDS,
)
from runner.run_context import RunContext

log = logging.getLogger(__name__)

#: Schema id of the checkpoint artifact (unchanged v1 — the provenance field is
#: additive, per decision D3).
CHECKPOINT_SCHEMA_ID = "orch.checkpoints.phase8_checkpoint.v1"

#: Canonical repo-relative path of the checkpoint artifact.
CHECKPOINT_REL = (
    "docs/tier4_orchestration_state/checkpoints/phase8_checkpoint.json"
)

_TIER4_ROOT_REL = "docs/tier4_orchestration_state"

#: The six gate results the checkpoint confirms, in canonical order.  In a
#: ``--phase 8`` run these split into gate_09 (phase 7, potentially bootstrapped
#: → prior run_id) and gate_10a/b/c/d + gate_11 (phase 8, current run_id).
CONFIRMED_GATE_IDS: tuple[str, ...] = (
    "gate_09_budget_consistency",
    "gate_10a_excellence_completeness",
    "gate_10b_impact_completeness",
    "gate_10c_implementation_completeness",
    "gate_10d_cross_section_consistency",
    "gate_11_review_closure",
)


class CheckpointPublishError(Exception):
    """Raised when the checkpoint cannot be published — fail-closed (§12.4).

    Surfaced by the deterministic-component wrapper as an
    ``AGENT_EXECUTION_ERROR`` node block; no checkpoint is written.
    """


def _read_json_dict(path: Path) -> dict:
    """Read *path* as a JSON object, raising :class:`CheckpointPublishError`."""
    try:
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        raise CheckpointPublishError(
            f"Gate result at {path} could not be read: {exc}"
        ) from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise CheckpointPublishError(
            f"Gate result at {path} is not valid JSON: {exc}"
        ) from exc
    if not isinstance(data, dict):
        raise CheckpointPublishError(
            f"Gate result at {path} is not a JSON object"
        )
    return data


def _validate_gate_result(gate_id: str, path: Path) -> dict:
    """Read and validate one gate result (presence, schema_id, status=pass)."""
    if not path.is_file():
        raise CheckpointPublishError(
            f"Gate result file {path} not found; all six gate results are "
            f"required for the checkpoint (gate_id={gate_id})"
        )
    data = _read_json_dict(path)
    if data.get("schema_id") != GATE_RESULT_SCHEMA_ID:
        raise CheckpointPublishError(
            f"Gate result at {path} has unexpected schema_id "
            f"{data.get('schema_id')!r} (expected {GATE_RESULT_SCHEMA_ID!r})"
        )
    if data.get("status") != "pass":
        raise CheckpointPublishError(
            f"Gate {gate_id} has status {data.get('status')!r}; all six "
            f"required gates must have status 'pass'"
        )
    return data


def _load_run_context(repo_root: Path, run_id: str) -> Optional[RunContext]:
    """Load the run manifest for *run_id*, or ``None`` if it does not exist."""
    try:
        return RunContext.load(repo_root, run_id)
    except FileNotFoundError:
        return None


def _authorize_and_build_quad(
    gate_id: str,
    gate_result: dict,
    ctx: Optional[RunContext],
) -> dict:
    """Authorize a cross-run gate and build its provenance quad entry.

    Fails closed unless the current run's continuation bootstrap recorded an
    ``accepted_upstream_gates`` entry for *gate_id* whose ``original_run_id``
    matches the durable gate result's ``run_id`` and whose ``status`` is
    ``"pass"``.  All quad fields are copied verbatim from the durable gate
    result (and the authorized evidence path).
    """
    original_run_id = gate_result.get("run_id")
    accepted = ctx.get_accepted_upstream_gate(gate_id) if ctx is not None else None
    if (
        accepted is None
        or accepted.get("original_run_id") != original_run_id
        or accepted.get("status") != "pass"
    ):
        raise CheckpointPublishError(
            f"Gate {gate_id} carries a cross-run run_id {original_run_id!r} "
            f"(current run is different) that is NOT authorized by the run's "
            f"accepted_upstream_gates continuation record. Refusing to publish "
            f"a checkpoint asserting un-declared inherited gate evidence."
        )
    return {
        "gate_id": gate_id,
        "original_run_id": original_run_id,
        "evidence_path": accepted.get("evidence_path"),
        "input_fingerprint": gate_result.get("input_fingerprint"),
        "versions": {k: gate_result.get(k) for k in GATE_RESULT_VERSION_FIELDS},
    }


def _read_optional_json(path: Path) -> Optional[dict]:
    """Read a non-blocking Tier-3 JSON file; return ``None`` on any absence/error."""
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _build_tier3_snapshot(repo_root: Path) -> dict[str, Any]:
    """Snapshot Tier-3 identity (call/topic/partners); absent → null/empty.

    Pure lookup: ``call_id`` and ``topic_id`` from ``selected_call.json``
    (``topic_code`` accepted as the ``topic_id`` source, matching the real call
    binding), ``partner_ids`` from ``partners.json``.  Never blocks — Tier 3
    identity is not gate-relevant here (the reader predicate checks only
    ``gate_results_confirmed`` and the provenance quad).
    """
    call = _read_optional_json(
        repo_root
        / "docs/tier3_project_instantiation/call_binding/selected_call.json"
    )
    partners_doc = _read_optional_json(
        repo_root
        / "docs/tier3_project_instantiation/consortium/partners.json"
    )

    call_id = call.get("call_id") if call else None
    topic_id = (call.get("topic_id") or call.get("topic_code")) if call else None

    partner_ids: list[str] = []
    if partners_doc:
        partners = partners_doc.get("partners", [])
        if isinstance(partners, list):
            for p in partners:
                if isinstance(p, dict) and p.get("partner_id"):
                    partner_ids.append(p["partner_id"])

    return {
        "call_id": call_id,
        "topic_id": topic_id,
        "partner_ids": partner_ids,
    }


def publish_checkpoint(run_id: str, repo_root: Path) -> Path:
    """Publish ``phase8_checkpoint.json``; return its absolute path.

    Parameters
    ----------
    run_id:
        Current DAG-runner run id (the checkpoint's own ``run_id``).
    repo_root:
        Absolute path to the repository root.

    Raises
    ------
    CheckpointPublishError
        On the write-once guard (an already-published checkpoint), any invalid
        gate result, or an unauthorized cross-run gate — all fail-closed.
    """
    repo_root = Path(repo_root)
    checkpoint_path = repo_root / CHECKPOINT_REL

    # 1. Write-once guard — a published checkpoint is immutable (never-overwrite).
    existing = _read_optional_json(checkpoint_path)
    if existing is not None and existing.get("status") == "published":
        raise CheckpointPublishError(
            f"Validated checkpoint already exists at {checkpoint_path} with "
            f"status 'published'; overwrite prohibited (CLAUDE.md §5 Tier 4)."
        )

    # Load the continuation record once (absent for a full non-phase-scoped run,
    # which never has a cross-run gate anyway).
    ctx = _load_run_context(repo_root, run_id)
    tier4_root = repo_root / _TIER4_ROOT_REL

    # 2–4. Validate the six gates; authorize + record any cross-run provenance.
    inherited_provenance: list[dict] = []
    for gate_id in CONFIRMED_GATE_IDS:
        gate_path = tier4_root / GATE_RESULT_PATHS[gate_id]
        gate_result = _validate_gate_result(gate_id, gate_path)
        if gate_result.get("run_id") != run_id:
            inherited_provenance.append(
                _authorize_and_build_quad(gate_id, gate_result, ctx)
            )

    # 5. Tier-3 snapshot (non-blocking).
    tier3_snapshot = _build_tier3_snapshot(repo_root)

    # 6. Assemble and atomically write the checkpoint.
    checkpoint: dict[str, Any] = {
        "schema_id": CHECKPOINT_SCHEMA_ID,
        "run_id": run_id,
        "status": "published",
        "published_at": datetime.now(timezone.utc).isoformat(),
        "gate_results_confirmed": list(CONFIRMED_GATE_IDS),
        "tier3_snapshot": tier3_snapshot,
    }
    # Additive / optional: omitted when empty → byte-identical to the
    # pre-CHK-1 all-current-run checkpoint (decision D3).
    if inherited_provenance:
        checkpoint["inherited_gate_provenance"] = inherited_provenance

    atomic_write_json(checkpoint, checkpoint_path, prefix="checkpoint_")
    log.info(
        "Phase-8 checkpoint published: %s (run_id=%s, inherited=%d)",
        checkpoint_path,
        run_id,
        len(inherited_provenance),
    )
    return checkpoint_path
