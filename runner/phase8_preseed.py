"""
Phase 8 manual preseed — copy manually prepared section artifacts into
canonical Tier 5 paths before agent dispatch.

This is NOT reuse.  Preseed mode:
  - does not require .reuse.json metadata
  - does not require input_fingerprint
  - does not require artifact_sha256 for gating
  - does not depend on prior run IDs

Preseed copies a validated JSON artifact from:
    docs/tier4_orchestration_state/preseed/phase8/<section>.json
to:
    docs/tier5_deliverables/proposal_sections/<section>.json

and skips only the primary drafting skill.  Audit skills (traceability-
check, compliance-check), exit gate evaluation, and downstream assembly
all execute normally.

Fail-closed: if a preseed file exists but is invalid (bad JSON, wrong
schema_id, missing required fields), the node is blocked before agent
dispatch.  No silent fallback to LLM drafting.

Constitutional authority:
    Subordinate to CLAUDE.md.  This module does not evaluate gates,
    invoke agents, or modify scheduler state.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from runner.claim_status import STATUS_SEVERITY, worst_status

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Repo-relative preseed source directory.
PRESEED_DIR: str = "docs/tier4_orchestration_state/preseed/phase8"

#: Repo-relative audit output directory.
PRESEED_AUDIT_DIR: str = (
    "docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review"
)

#: Required top-level fields in a preseed artifact.
REQUIRED_FIELDS: tuple[str, ...] = (
    "schema_id",
    "run_id",
    "criterion",
    "sub_sections",
    "validation_status",
    "traceability_footer",
)

#: Node-to-preseed mapping.
PRESEED_NODE_CONFIG: dict[str, dict[str, str]] = {
    "n08a_excellence_drafting": {
        "source_file": "excellence_section.json",
        "target_path": "docs/tier5_deliverables/proposal_sections/excellence_section.json",
        "schema_id": "orch.tier5.excellence_section.v1",
        "skipped_skill": "excellence-section-drafting",
    },
    "n08b_impact_drafting": {
        "source_file": "impact_section.json",
        "target_path": "docs/tier5_deliverables/proposal_sections/impact_section.json",
        "schema_id": "orch.tier5.impact_section.v1",
        "skipped_skill": "impact-section-drafting",
    },
    "n08c_implementation_drafting": {
        "source_file": "implementation_section.json",
        "target_path": "docs/tier5_deliverables/proposal_sections/implementation_section.json",
        "schema_id": "orch.tier5.implementation_section.v1",
        "skipped_skill": "implementation-section-drafting",
    },
}


# ---------------------------------------------------------------------------
# Validation-status consistency
# ---------------------------------------------------------------------------


def _validation_status_inconsistency(data: dict[str, Any]) -> str | None:
    """Return a failure reason iff the roll-up over-states the claims (§12.2).

    A drafted section gets its ``validation_status.overall_status`` derived from
    the per-claim statuses by the drafter and, after any declared flips, by the
    assumption-applier — the worst-wins rule of §12.2.  A **preseeded** section
    bypasses that whole pipeline: the operator hands in a finished artifact, and
    nothing downstream re-derives the roll-up.  ``gate_10a`` reads only the
    roll-up (``no_unresolved_material_claims``) and W1
    (``assumed_claims_are_operator_declared``) inspects only ``assumed`` claims,
    so an ``unresolved`` claim sitting under a ``confirmed`` roll-up is invisible
    to both — a fail-closed honest block silently becomes a green.  Presence
    validation alone cannot catch that; this check does.

    The rule is one-sided by design: the roll-up may be **more** conservative
    than its claims (an operator may declare a section ``assumed`` over
    ``confirmed`` claims — honest under-claiming, §15), but it may never be more
    resolved than its least-resolved claim.

    Returns ``None`` when the artifact is consistent (including when it carries
    no claims), otherwise a ``preseed_*`` reason string.
    """
    validation_status = data.get("validation_status")
    if not isinstance(validation_status, dict):
        return (
            "preseed_validation_status_not_object: 'validation_status' must be "
            f"an object, got {type(validation_status).__name__}"
        )

    overall = validation_status.get("overall_status")
    if not isinstance(overall, str) or overall.lower() not in STATUS_SEVERITY:
        return (
            "preseed_overall_status_invalid: 'validation_status."
            f"overall_status' must be one of {sorted(STATUS_SEVERITY)}, got "
            f"{overall!r}"
        )

    claim_statuses = validation_status.get("claim_statuses", [])
    if not isinstance(claim_statuses, list):
        return (
            "preseed_claim_statuses_not_array: 'validation_status."
            "claim_statuses' must be an array, got "
            f"{type(claim_statuses).__name__}"
        )

    worst = worst_status(
        claim.get("status", "")
        for claim in claim_statuses
        if isinstance(claim, dict)
    )
    if STATUS_SEVERITY[overall.lower()] < STATUS_SEVERITY[worst]:
        return (
            f"preseed_overall_status_overstated: 'validation_status."
            f"overall_status' is {overall!r} but the worst claim status is "
            f"{worst!r} (CLAUDE.md §12.2 worst-wins); the roll-up may be more "
            "conservative than its claims, never more resolved"
        )
    return None


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase8PreseedResult:
    """Outcome of a preseed attempt for a single node."""

    applied: bool
    """True if preseed was successfully applied."""

    reason: str | None = None
    """Explanation (especially on failure or when not applicable)."""

    target_path: str | None = None
    """Repo-relative path where the artifact was written."""

    skipped_skill_id: str | None = None
    """Skill ID that should be skipped in agent dispatch."""

    error: bool = False
    """True if preseed file exists but is invalid (caller should block)."""

    failure_category: str | None = None
    """Failure category when error=True."""


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------


def maybe_apply_phase8_preseed(
    repo_root: Path,
    run_id: str,
    node_id: str,
) -> Phase8PreseedResult:
    """Attempt to apply a manual preseed for a Phase 8 drafting node.

    Parameters
    ----------
    repo_root:
        Repository root.
    run_id:
        Current run UUID.
    node_id:
        Canonical manifest node ID (e.g. ``"n08a_excellence_drafting"``).

    Returns
    -------
    Phase8PreseedResult
        - ``applied=True``: artifact copied, audit written, skill to skip.
        - ``applied=False, error=False``: no preseed file, proceed normally.
        - ``applied=False, error=True``: preseed file invalid, block node.
    """
    config = PRESEED_NODE_CONFIG.get(node_id)
    if config is None:
        return Phase8PreseedResult(
            applied=False,
            reason="node_not_preseed_eligible",
        )

    source_path = repo_root / PRESEED_DIR / config["source_file"]
    if not source_path.is_file():
        return Phase8PreseedResult(
            applied=False,
            reason="preseed_file_not_found",
        )

    # -- Parse JSON --
    try:
        raw = source_path.read_text(encoding="utf-8")
        data: dict[str, Any] = json.loads(raw)
    except (json.JSONDecodeError, OSError) as exc:
        return Phase8PreseedResult(
            applied=False,
            reason=f"preseed_invalid_json: {exc}",
            error=True,
            failure_category="MALFORMED_ARTIFACT",
        )

    if not isinstance(data, dict):
        return Phase8PreseedResult(
            applied=False,
            reason="preseed_root_not_dict",
            error=True,
            failure_category="MALFORMED_ARTIFACT",
        )

    # -- Verify schema_id --
    expected_schema = config["schema_id"]
    actual_schema = data.get("schema_id")
    if actual_schema != expected_schema:
        return Phase8PreseedResult(
            applied=False,
            reason=(
                f"preseed_schema_mismatch: expected {expected_schema!r}, "
                f"got {actual_schema!r}"
            ),
            error=True,
            failure_category="MALFORMED_ARTIFACT",
        )

    # -- Verify required fields --
    missing = [f for f in REQUIRED_FIELDS if f not in data]
    if missing:
        return Phase8PreseedResult(
            applied=False,
            reason=f"preseed_missing_fields: {missing}",
            error=True,
            failure_category="MALFORMED_ARTIFACT",
        )

    # -- Verify the validation_status roll-up is internally consistent --
    consistency_error = _validation_status_inconsistency(data)
    if consistency_error is not None:
        return Phase8PreseedResult(
            applied=False,
            reason=consistency_error,
            error=True,
            failure_category="MALFORMED_ARTIFACT",
        )

    # -- Rewrite run_id --
    original_run_id = data["run_id"]
    data["run_id"] = run_id

    # -- Write artifact to canonical Tier 5 path --
    target_rel = config["target_path"]
    target_abs = repo_root / target_rel
    target_abs.parent.mkdir(parents=True, exist_ok=True)
    target_abs.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # -- Write preseed audit record --
    source_rel = f"{PRESEED_DIR}/{config['source_file']}"
    _write_preseed_audit(
        repo_root=repo_root,
        node_id=node_id,
        source_path=source_rel,
        target_path=target_rel,
        schema_id=expected_schema,
        original_run_id=original_run_id,
        current_run_id=run_id,
        skipped_skill=config["skipped_skill"],
    )

    log.info(
        "  [%s] PRESEED: artifact copied from %s -> %s, "
        "run_id rewritten %s -> %s",
        node_id, source_rel, target_rel, original_run_id, run_id,
    )

    return Phase8PreseedResult(
        applied=True,
        reason="preseed_applied",
        target_path=target_rel,
        skipped_skill_id=config["skipped_skill"],
    )


# ---------------------------------------------------------------------------
# Audit record writer
# ---------------------------------------------------------------------------


def _write_preseed_audit(
    *,
    repo_root: Path,
    node_id: str,
    source_path: str,
    target_path: str,
    schema_id: str,
    original_run_id: str,
    current_run_id: str,
    skipped_skill: str,
) -> Path:
    """Write a preseed audit JSON to the phase8 output directory.

    Returns the absolute path of the written audit file.
    """
    audit = {
        "mode": "manual_preseed",
        "node_id": node_id,
        "source_path": source_path,
        "target_path": target_path,
        "schema_id": schema_id,
        "original_artifact_run_id": original_run_id,
        "current_run_id": current_run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "drafting_skill_skipped": skipped_skill,
    }
    audit_dir = repo_root / PRESEED_AUDIT_DIR
    audit_dir.mkdir(parents=True, exist_ok=True)
    audit_path = audit_dir / f"preseed_{node_id}.json"
    audit_path.write_text(
        json.dumps(audit, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return audit_path
