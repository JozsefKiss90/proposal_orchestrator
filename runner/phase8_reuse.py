"""
Phase 8 section artifact reuse — minimal, safe reuse layer.

Avoids rerunning expensive Phase 8 section drafting (n08a/n08b/n08c) when
a previously produced section artifact is still valid, input-equivalent,
and gate-approved.

Scope: n08a_excellence_drafting, n08b_impact_drafting, n08c_implementation_drafting.
NOT: n08d_assembly, n08e_evaluator_review, n08f_revision.

Fail-closed: any parse error, missing field, hash mismatch, or missing
gate result falls back to normal execution.  No artifact is ever reused
without passing all eligibility checks.

Constitutional authority:
    Subordinate to CLAUDE.md.  This module does not evaluate gates,
    invoke agents, or modify scheduler state.  It provides pure
    functions for fingerprinting, eligibility checking, and metadata I/O.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Policy version stamp for forward compatibility.
REUSE_POLICY_VERSION: str = "phase8.section.v2"

#: Repo-relative directory for reuse metadata.
REUSE_METADATA_DIR: str = "docs/tier4_orchestration_state/reuse/phase8"

#: Node-specific drafting skills to skip during reuse.
#: Only the expensive drafting skill is skipped; audit skills
#: (traceability-check, compliance-check) always execute.
REUSE_SKIP_SKILLS: dict[str, str] = {
    "n08a_excellence_drafting": "excellence-section-drafting",
    "n08b_impact_drafting": "impact-section-drafting",
    "n08c_implementation_drafting": "implementation-section-drafting",
}

#: Nodes eligible for reuse, mapped to their canonical artifact and gate.
REUSE_ELIGIBLE_NODES: dict[str, dict[str, str]] = {
    "n08a_excellence_drafting": {
        "artifact_path": "docs/tier5_deliverables/proposal_sections/excellence_section.json",
        "schema_id": "orch.tier5.excellence_section.v1",
        "gate_id": "gate_10a_excellence_completeness",
    },
    "n08b_impact_drafting": {
        "artifact_path": "docs/tier5_deliverables/proposal_sections/impact_section.json",
        "schema_id": "orch.tier5.impact_section.v1",
        "gate_id": "gate_10b_impact_completeness",
    },
    "n08c_implementation_drafting": {
        "artifact_path": "docs/tier5_deliverables/proposal_sections/implementation_section.json",
        "schema_id": "orch.tier5.implementation_section.v1",
        "gate_id": "gate_10c_implementation_completeness",
    },
}

#: Node-specific minimum fingerprint input directories.
#: All files under these paths are included in the hash.
FINGERPRINT_INPUTS: dict[str, list[str]] = {
    "n08a_excellence_drafting": [
        "docs/tier2a_instrument_schemas/extracted/",
        "docs/tier2b_topic_and_call_sources/extracted/",
        "docs/tier3_project_instantiation/",
        "docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/",
        "docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/",
        "docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/",
        "docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/",
    ],
    "n08b_impact_drafting": [
        "docs/tier2a_instrument_schemas/extracted/",
        "docs/tier2b_topic_and_call_sources/extracted/",
        "docs/tier3_project_instantiation/",
        "docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/",
        "docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/",
        "docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/",
    ],
    "n08c_implementation_drafting": [
        "docs/tier2a_instrument_schemas/extracted/",
        "docs/tier2b_topic_and_call_sources/extracted/",
        "docs/tier3_project_instantiation/",
        "docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/",
        "docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/",
        "docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/",
        "docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/",
    ],
}

#: Paths to exclude from fingerprinting (transient/diagnostic files).
_FINGERPRINT_EXCLUDE_SUFFIXES: tuple[str, ...] = (
    ".reuse.json",
    "_response.txt",
    "_parsed.txt",
    "_phase_e.txt",
    "_transport_diag.json",
    "_system_prompt.txt",
    "_user_prompt.txt",
    "_stdout.txt",
    "_stderr.txt",
)

_FINGERPRINT_EXCLUDE_NAMES: frozenset[str] = frozenset({
    "gate_result.json",
    "gate_10a_result.json",
    "gate_10b_result.json",
    "gate_10c_result.json",
    "gate_10d_result.json",
    "gate_11_result.json",
    "gate_12_result.json",
    "run_manifest.json",
    "run_summary.json",
    "reuse_policy.json",
    "gate_01_result.json",
})

#: Tier 4 gate result registry path prefix (from gate_result_registry.py).
_TIER4_ROOT_REL: str = "docs/tier4_orchestration_state"


# ---------------------------------------------------------------------------
# ReuseDecision
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReuseDecision:
    """Outcome of a reuse eligibility check."""

    reusable: bool
    """True if the artifact can be reused and agent body skipped."""

    reason: str
    """Human-readable explanation of the decision."""

    source_run_id: str | None = None
    """Run ID from the reuse metadata (only set when reusable=True)."""

    artifact_path: str | None = None
    """Canonical artifact path (only set when reusable=True)."""

    input_fingerprint: str | None = None
    """Current input fingerprint (always set when computed)."""

    gate_id: str | None = None
    """Gate ID for the section (only set when reusable=True)."""


# ---------------------------------------------------------------------------
# Input fingerprinting
# ---------------------------------------------------------------------------


def _collect_fingerprint_files(
    paths: list[str],
    repo_root: Path,
) -> list[tuple[str, Path]]:
    """Collect (repo_relative, abs_path) pairs from declared input paths.

    Recursively includes files under directories. Excludes transient files.
    Sorts lexicographically by repo-relative path for determinism.
    """
    entries: list[tuple[str, Path]] = []
    for rel_path in paths:
        abs_path = repo_root / rel_path
        if abs_path.is_file():
            name = abs_path.name
            if name in _FINGERPRINT_EXCLUDE_NAMES:
                continue
            if any(name.endswith(s) for s in _FINGERPRINT_EXCLUDE_SUFFIXES):
                continue
            # Normalize to forward slashes
            norm_rel = rel_path.replace("\\", "/")
            entries.append((norm_rel, abs_path))
        elif abs_path.is_dir():
            for child in abs_path.rglob("*"):
                if not child.is_file():
                    continue
                cname = child.name
                if cname in _FINGERPRINT_EXCLUDE_NAMES:
                    continue
                if any(cname.endswith(s) for s in _FINGERPRINT_EXCLUDE_SUFFIXES):
                    continue
                child_rel = str(child.relative_to(repo_root)).replace("\\", "/")
                entries.append((child_rel, child))
    # Sort lexicographically by repo-relative path for determinism
    entries.sort(key=lambda t: t[0])
    return entries


def compute_input_fingerprint(node_id: str, repo_root: Path) -> str | None:
    """Compute a deterministic SHA-256 fingerprint of all inputs for *node_id*.

    Returns the hex digest, or None if the node is not fingerprint-eligible.
    The hash includes repo-relative path + file content for each input file,
    sorted lexicographically by path.
    """
    input_paths = FINGERPRINT_INPUTS.get(node_id)
    if input_paths is None:
        return None

    entries = _collect_fingerprint_files(input_paths, repo_root)
    h = hashlib.sha256()
    for rel_path, abs_path in entries:
        h.update(rel_path.encode("utf-8"))
        h.update(b"\x00")
        try:
            h.update(abs_path.read_bytes())
        except OSError:
            h.update(b"\x01")  # mark unreadable
        h.update(b"\x00")
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Artifact hashing
# ---------------------------------------------------------------------------


def artifact_sha256(path: Path) -> str | None:
    """Compute SHA-256 of artifact file content. Returns None on error."""
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def read_artifact_run_id(path: Path) -> str | None:
    """Read the top-level ``run_id`` from a JSON artifact.

    Returns the run_id string, or ``None`` if the file is missing,
    malformed, not a dict, or lacks a string ``run_id`` field.
    Fail-closed: any error returns ``None``.
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            rid = data.get("run_id")
            return rid if isinstance(rid, str) else None
        return None
    except (json.JSONDecodeError, OSError):
        return None


# ---------------------------------------------------------------------------
# Reuse metadata I/O
# ---------------------------------------------------------------------------


def _reuse_metadata_path(node_id: str, repo_root: Path) -> Path:
    """Return the canonical path for a node's reuse metadata file."""
    return repo_root / REUSE_METADATA_DIR / f"{node_id}.reuse.json"


def load_reuse_metadata(node_id: str, repo_root: Path) -> dict | None:
    """Load reuse metadata for *node_id*. Returns None if absent or invalid."""
    path = _reuse_metadata_path(node_id, repo_root)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return None
        return data
    except (json.JSONDecodeError, OSError):
        return None


def write_reuse_metadata(
    *,
    node_id: str,
    repo_root: Path,
    source_run_id: str,
    artifact_path: str,
    schema_id: str,
    gate_id: str,
    input_fingerprint: str,
    artifact_hash: str,
    artifact_run_id: str | None = None,
    last_validated_run_id: str | None = None,
) -> Path:
    """Write reuse metadata for a section node after successful gate pass.

    Parameters
    ----------
    source_run_id:
        Backward-compatible parameter.  Should be set to the artifact's
        actual ``run_id`` (the producing run).  Preserved as alias for
        ``artifact_run_id``.
    artifact_run_id:
        The ``run_id`` embedded in the artifact JSON — the run that
        originally produced the artifact.  When ``None``, falls back to
        *source_run_id*.
    last_validated_run_id:
        The run that most recently validated this artifact through a
        gate pass.  When ``None``, falls back to *source_run_id*.

    Returns the path of the written metadata file.
    """
    _artifact_run_id = artifact_run_id if artifact_run_id is not None else source_run_id
    _last_validated_run_id = (
        last_validated_run_id if last_validated_run_id is not None else source_run_id
    )
    metadata = {
        "node_id": node_id,
        "artifact_path": artifact_path,
        "schema_id": schema_id,
        "artifact_run_id": _artifact_run_id,
        "last_validated_run_id": _last_validated_run_id,
        "source_run_id": _artifact_run_id,  # backward compat alias = artifact origin
        "gate_id": gate_id,
        "gate_status": "pass",
        "input_fingerprint": input_fingerprint,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "artifact_sha256": artifact_hash,
        "reuse_policy_version": REUSE_POLICY_VERSION,
    }
    path = _reuse_metadata_path(node_id, repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Reuse eligibility validation
# ---------------------------------------------------------------------------


def _load_gate_result(gate_id: str, repo_root: Path) -> dict | None:
    """Load a gate result from its canonical Tier 4 path."""
    from runner.gate_result_registry import GATE_RESULT_PATHS

    rel = GATE_RESULT_PATHS.get(gate_id)
    if rel is None:
        return None
    abs_path = repo_root / _TIER4_ROOT_REL / rel
    if not abs_path.is_file():
        return None
    try:
        data = json.loads(abs_path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (json.JSONDecodeError, OSError):
        return None


def validate_reuse_candidate(
    node_id: str,
    repo_root: Path,
    current_fingerprint: str | None = None,
) -> ReuseDecision:
    """Check whether a section node's previous artifact can be reused.

    Checks all eligibility conditions fail-closed. Returns a ReuseDecision
    with reusable=True only when every condition passes.
    """
    # 1. Node must be eligible
    node_config = REUSE_ELIGIBLE_NODES.get(node_id)
    if node_config is None:
        return ReuseDecision(
            reusable=False, reason="not_eligible_node",
            input_fingerprint=current_fingerprint,
        )

    artifact_rel = node_config["artifact_path"]
    expected_schema = node_config["schema_id"]
    gate_id = node_config["gate_id"]

    # 2. Artifact must exist at exact canonical path
    artifact_abs = repo_root / artifact_rel
    if not artifact_abs.is_file():
        return ReuseDecision(
            reusable=False, reason="missing_artifact",
            input_fingerprint=current_fingerprint,
        )

    # 3. Artifact must be valid JSON with correct schema_id
    try:
        artifact_data = json.loads(artifact_abs.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return ReuseDecision(
            reusable=False, reason="invalid_artifact_json",
            input_fingerprint=current_fingerprint,
        )

    if not isinstance(artifact_data, dict):
        return ReuseDecision(
            reusable=False, reason="artifact_not_dict",
            input_fingerprint=current_fingerprint,
        )

    if artifact_data.get("schema_id") != expected_schema:
        return ReuseDecision(
            reusable=False, reason="schema_mismatch",
            input_fingerprint=current_fingerprint,
        )

    # 4. validation_status.overall_status must not be "unresolved"
    vs = artifact_data.get("validation_status")
    if not isinstance(vs, dict):
        return ReuseDecision(
            reusable=False, reason="missing_validation_status",
            input_fingerprint=current_fingerprint,
        )
    if vs.get("overall_status") == "unresolved":
        return ReuseDecision(
            reusable=False, reason="unresolved_validation_status",
            input_fingerprint=current_fingerprint,
        )

    # 5. traceability_footer.no_unsupported_claims_declaration must be true
    tf = artifact_data.get("traceability_footer")
    if not isinstance(tf, dict):
        return ReuseDecision(
            reusable=False, reason="missing_traceability_footer",
            input_fingerprint=current_fingerprint,
        )
    if tf.get("no_unsupported_claims_declaration") is not True:
        return ReuseDecision(
            reusable=False, reason="unsupported_claims",
            input_fingerprint=current_fingerprint,
        )

    # 6. artifact_status must not be failed/stale/draft_invalid/blocked
    art_status = artifact_data.get("artifact_status")
    if art_status in ("failed", "stale", "draft_invalid", "blocked"):
        return ReuseDecision(
            reusable=False, reason="artifact_status_invalid",
            input_fingerprint=current_fingerprint,
        )

    # 7. Previous gate result must exist and be pass
    gate_result = _load_gate_result(gate_id, repo_root)
    if gate_result is None:
        return ReuseDecision(
            reusable=False, reason="missing_gate_result",
            input_fingerprint=current_fingerprint,
        )
    if gate_result.get("status") != "pass":
        return ReuseDecision(
            reusable=False, reason="previous_gate_not_passed",
            input_fingerprint=current_fingerprint,
        )

    # 8. Reuse metadata must exist and be valid
    metadata = load_reuse_metadata(node_id, repo_root)
    if metadata is None:
        return ReuseDecision(
            reusable=False, reason="missing_metadata",
            input_fingerprint=current_fingerprint,
        )

    # Validate metadata fields
    for required_key in (
        "node_id", "artifact_path", "schema_id", "source_run_id",
        "gate_id", "gate_status", "input_fingerprint", "artifact_sha256",
    ):
        if required_key not in metadata:
            return ReuseDecision(
                reusable=False, reason=f"metadata_missing_{required_key}",
                input_fingerprint=current_fingerprint,
            )

    if metadata["gate_status"] != "pass":
        return ReuseDecision(
            reusable=False, reason="metadata_gate_not_pass",
            input_fingerprint=current_fingerprint,
        )

    if metadata["artifact_path"] != artifact_rel:
        return ReuseDecision(
            reusable=False, reason="metadata_artifact_path_mismatch",
            input_fingerprint=current_fingerprint,
        )

    # 9. Artifact content hash must match metadata
    current_hash = artifact_sha256(artifact_abs)
    if current_hash is None or current_hash != metadata["artifact_sha256"]:
        return ReuseDecision(
            reusable=False, reason="artifact_hash_mismatch",
            input_fingerprint=current_fingerprint,
        )

    # 10. Input fingerprint must match
    if current_fingerprint is None:
        current_fingerprint = compute_input_fingerprint(node_id, repo_root)
    if current_fingerprint is None:
        return ReuseDecision(
            reusable=False, reason="fingerprint_computation_failed",
            input_fingerprint=current_fingerprint,
        )
    if current_fingerprint != metadata["input_fingerprint"]:
        return ReuseDecision(
            reusable=False, reason="fingerprint_mismatch",
            input_fingerprint=current_fingerprint,
        )

    # All checks passed.
    # Prefer artifact_run_id (v2+) over source_run_id (v1 compat).
    _meta_art_rid = metadata.get("artifact_run_id") or metadata["source_run_id"]
    return ReuseDecision(
        reusable=True,
        reason="all_checks_passed",
        source_run_id=_meta_art_rid,
        artifact_path=artifact_rel,
        input_fingerprint=current_fingerprint,
        gate_id=gate_id,
    )


# ---------------------------------------------------------------------------
# Reuse ownership validation (gate predicate support)
# ---------------------------------------------------------------------------

#: Directory for current-run validation reports.
_VALIDATION_REPORTS_DIR: str = "docs/tier4_orchestration_state/validation_reports"

#: Audit skills that must have produced current-run evidence.
_REQUIRED_AUDIT_SKILLS: tuple[str, ...] = (
    "proposal-section-traceability-check",
    "constitutional-compliance-check",
)

#: Mapping of artifact paths to their expected node_id for reverse lookup.
_ARTIFACT_PATH_TO_NODE: dict[str, str] = {
    v["artifact_path"]: k for k, v in REUSE_ELIGIBLE_NODES.items()
}


def _run_id_prefix(run_id: str) -> str:
    """Return first 8 chars of run_id (UUID first segment)."""
    return run_id.split("-")[0] if "-" in run_id else run_id[:8]


def _audit_report_exists(skill_id: str, run_id: str, repo_root: Path) -> bool:
    """Check if a current-run audit report exists and is parseable JSON."""
    prefix = _run_id_prefix(run_id)
    report_path = repo_root / _VALIDATION_REPORTS_DIR / f"{skill_id}_{prefix}.json"
    if not report_path.is_file():
        return False
    try:
        data = json.loads(report_path.read_text(encoding="utf-8"))
        return isinstance(data, dict) and data.get("skill_id") == skill_id
    except (json.JSONDecodeError, OSError):
        return False


def is_reuse_owned_artifact_valid(
    node_id: str,
    artifact_path: str,
    artifact: dict,
    current_run_id: str,
    repo_root: Path,
) -> tuple[bool, str]:
    """Validate that a reused Phase 8 section artifact passes ownership.

    This is called by ``artifact_owned_by_run`` when the artifact's run_id
    does not match the current run and the artifact path belongs to a
    reuse-eligible Phase 8 section node.

    Returns (True, reason) on success or (False, reason) on failure.
    All checks are fail-closed: any missing data causes rejection.

    Acceptance conditions (all must hold):
      1. Node is reuse-eligible (n08a/n08b/n08c only)
      2. Current run has a persisted reuse decision with status="reused"
      3. Decision mode is "drafting_skipped_audit_executed"
      4. Decision artifact_run_id matches artifact.run_id
      5. Decision artifact_path matches the canonical artifact path
      6. Reuse metadata file exists on disk
      7. (removed — superseded by conditions 8+9)
      8. Metadata artifact_sha256 matches current file hash
      9. Metadata input_fingerprint matches current computed fingerprint
     10. Current-run audit reports exist for both required audit skills
     11. Artifact structural validation passes (schema_id, validation_status,
         traceability_footer)
    """
    artifact_run_id = artifact.get("run_id")

    # Condition 1: node must be reuse-eligible
    node_config = REUSE_ELIGIBLE_NODES.get(node_id)
    if node_config is None:
        return False, "node_not_reuse_eligible"

    # Verify artifact_path matches canonical path for the node
    if artifact_path != node_config["artifact_path"]:
        return False, "artifact_path_not_canonical"

    # Conditions 2-5: check persisted reuse decision from RunContext
    from runner.run_context import RunContext, RUNS_DIR_REL

    run_manifest_path = (
        repo_root / RUNS_DIR_REL / current_run_id / "run_manifest.json"
    )
    if not run_manifest_path.is_file():
        return False, "run_manifest_not_found"

    try:
        manifest = json.loads(run_manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False, "run_manifest_unreadable"

    decisions = manifest.get("reuse_decisions")
    if not isinstance(decisions, dict):
        return False, "no_reuse_decisions_in_manifest"

    decision = decisions.get(node_id)
    if not isinstance(decision, dict):
        return False, "no_reuse_decision_for_node"

    # Condition 2
    if decision.get("status") != "reused":
        return False, "reuse_decision_status_not_reused"

    # Condition 3
    if decision.get("mode") != "drafting_skipped_audit_executed":
        return False, "reuse_decision_mode_wrong"

    # Condition 4: prefer artifact_run_id (v2+), fall back to source_run_id (v1)
    decision_art_rid = decision.get("artifact_run_id") or decision.get("source_run_id")
    if decision_art_rid != artifact_run_id:
        return False, "reuse_decision_source_run_id_mismatch"

    # Condition 5
    if decision.get("artifact_path") != artifact_path:
        return False, "reuse_decision_artifact_path_mismatch"

    # Conditions 6-9: check reuse metadata file on disk
    metadata = load_reuse_metadata(node_id, repo_root)
    if metadata is None:
        return False, "reuse_metadata_missing"

    # Condition 7 (removed): metadata artifact_run_id vs artifact.run_id.
    # This check is superseded by conditions 8+9 (SHA-256 hash + input
    # fingerprint), which are strictly stronger integrity proofs.  v1
    # metadata may have a stale source_run_id (set to validating run
    # instead of artifact origin); conditions 8+9 catch any real change.

    # Condition 8
    artifact_abs = repo_root / artifact_path
    current_hash = artifact_sha256(artifact_abs)
    if current_hash is None or current_hash != metadata.get("artifact_sha256"):
        return False, "artifact_hash_mismatch"

    # Condition 9
    current_fp = compute_input_fingerprint(node_id, repo_root)
    if current_fp is None or current_fp != metadata.get("input_fingerprint"):
        return False, "input_fingerprint_mismatch"

    # Condition 10: current-run audit reports exist
    for skill_id in _REQUIRED_AUDIT_SKILLS:
        if not _audit_report_exists(skill_id, current_run_id, repo_root):
            return False, f"missing_audit_report_{skill_id}"

    # Condition 11: artifact structural validation
    expected_schema = node_config["schema_id"]
    if artifact.get("schema_id") != expected_schema:
        return False, "schema_id_mismatch"

    vs = artifact.get("validation_status")
    if not isinstance(vs, dict):
        return False, "missing_validation_status"
    if vs.get("overall_status") == "unresolved":
        return False, "validation_status_unresolved"

    # Check for assumed/unresolved claims
    claim_statuses = vs.get("claim_statuses", [])
    for cs in claim_statuses:
        if isinstance(cs, dict) and cs.get("status") in ("assumed", "unresolved"):
            return False, f"claim_status_{cs.get('status')}"

    tf = artifact.get("traceability_footer")
    if not isinstance(tf, dict):
        return False, "missing_traceability_footer"
    if tf.get("no_unsupported_claims_declaration") is not True:
        return False, "unsupported_claims_declaration_false"

    return True, "all_reuse_ownership_conditions_met"
