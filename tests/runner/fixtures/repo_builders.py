"""
Synthetic repository builders for Step 12 gate fixture tests.

Provides helpers for:
* creating canonical directory structure in tmp_path
* initialising and manipulating RunContext (including reuse-policy approvals)
* writing minimal synthetic gate_rules_library.yaml files
* building predicate and gate-entry dicts

Design note: every helper operates on an absolute repo_root (typically
pytest's tmp_path).  No helper reads or mutates live repository state.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

import yaml

from runner.run_context import RunContext
from runner.versions import CONSTITUTION_VERSION, LIBRARY_VERSION, MANIFEST_VERSION


# ---------------------------------------------------------------------------
# Repository root setup
# ---------------------------------------------------------------------------


def make_repo_root(tmp_path: Path) -> Path:
    """
    Create the canonical directory skeleton expected by gate predicates.

    Returns *tmp_path* after creating all standard sub-directories so that
    dir_non_empty and non_empty_json predicates never fail due to missing
    parent directories.
    """
    dirs = [
        "docs/tier2a_instrument_schemas/application_forms",
        "docs/tier2a_instrument_schemas/evaluation_forms",
        "docs/tier2a_instrument_schemas/extracted",
        "docs/tier2b_topic_and_call_sources/work_programmes",
        "docs/tier2b_topic_and_call_sources/call_extracts",
        "docs/tier2b_topic_and_call_sources/extracted",
        "docs/tier3_project_instantiation/call_binding",
        "docs/tier3_project_instantiation/consortium",
        "docs/tier3_project_instantiation/architecture_inputs",
        "docs/tier3_project_instantiation/project_brief",
        "docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis",
        "docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement",
        "docs/tier4_orchestration_state/phase_outputs/phase3_wp_design",
        "docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones",
        "docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture",
        "docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture",
        "docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate",
        "docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review",
        "docs/tier4_orchestration_state/checkpoints",
        "docs/tier5_deliverables/proposal_sections",
        "docs/tier5_deliverables/assembled_drafts",
        "docs/tier5_deliverables/review_packets",
        "docs/tier5_deliverables/final_exports",
        "docs/integrations/lump_sum_budget_planner/request_templates",
        ".claude/runs",
    ]
    for d in dirs:
        (tmp_path / d).mkdir(parents=True, exist_ok=True)
    return tmp_path


# ---------------------------------------------------------------------------
# Run context helpers
# ---------------------------------------------------------------------------


def make_run_id() -> str:
    """Return a fresh UUID v4 string."""
    return str(uuid.uuid4())


def init_run(repo_root: Path, run_id: str | None = None) -> tuple[RunContext, str]:
    """
    Initialize a RunContext and return ``(ctx, run_id)``.

    When *run_id* is ``None`` a new UUID is generated.  The context is
    immediately persisted to disk.
    """
    if run_id is None:
        run_id = make_run_id()
    ctx = RunContext.initialize(repo_root, run_id)
    return ctx, run_id


def approve_artifact(repo_root: Path, run_id: str, artifact_rel_path: str) -> None:
    """
    Add *artifact_rel_path* to the reuse policy ``approved_artifacts`` list
    for *run_id*.

    The canonical ``artifact_owned_by_run`` predicate reads this list to
    decide whether an artifact with a mismatched run_id is accepted as an
    inherited/reused artifact.
    """
    ctx = RunContext.load(repo_root, run_id)
    # Append directly to the internal reuse policy dict
    ctx._reuse_policy.setdefault("approved_artifacts", []).append(artifact_rel_path)
    ctx.save()


# ---------------------------------------------------------------------------
# JSON write utility
# ---------------------------------------------------------------------------


def write_json(path: Path, data: Any) -> None:
    """Write *data* as JSON to *path*, creating parent directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Gate rules library builder
# ---------------------------------------------------------------------------


def write_library(
    repo_root: Path,
    gates: list[dict],
    lib_name: str = ".test_library.yaml",
) -> Path:
    """
    Write a synthetic ``gate_rules_library.yaml`` and return its path.

    The library uses the production MANIFEST_VERSION, LIBRARY_VERSION, and
    CONSTITUTION_VERSION constants so that ``GateLibrary.load`` accepts it
    without a version-mismatch error.
    """
    lib_data: dict = {
        "library_version": LIBRARY_VERSION,
        "manifest_version": MANIFEST_VERSION,
        "constitution_version": CONSTITUTION_VERSION,
        "gate_rules": gates,
    }
    lib_path = repo_root / lib_name
    lib_path.write_text(yaml.dump(lib_data), encoding="utf-8")
    return lib_path


def write_library_with_version(
    repo_root: Path,
    gates: list[dict],
    *,
    manifest_version: str,
    lib_name: str = ".test_library_ver.yaml",
) -> Path:
    """
    Write a synthetic library with a custom *manifest_version*.

    Used to build version-mismatch test fixtures.
    """
    lib_data: dict = {
        "library_version": LIBRARY_VERSION,
        "manifest_version": manifest_version,
        "constitution_version": CONSTITUTION_VERSION,
        "gate_rules": gates,
    }
    lib_path = repo_root / lib_name
    lib_path.write_text(yaml.dump(lib_data), encoding="utf-8")
    return lib_path


# ---------------------------------------------------------------------------
# Predicate dict builders
# ---------------------------------------------------------------------------


def pred(
    pred_id: str,
    type_: str,
    function_: str,
    *,
    fail_message: str = "",
    prose_condition: str = "",
    **args: Any,
) -> dict:
    """Return a minimal predicate entry dict."""
    return {
        "predicate_id": pred_id,
        "type": type_,
        "function": function_,
        "args": args,
        "fail_message": fail_message or f"{pred_id} failed",
        "prose_condition": prose_condition or f"{pred_id} condition",
    }


def pred_non_empty_json(pred_id: str, path: str) -> dict:
    """Shorthand: ``non_empty_json`` predicate."""
    return pred(pred_id, "file", "non_empty_json", path=path)


def pred_dir_non_empty(pred_id: str, path: str) -> dict:
    """Shorthand: ``dir_non_empty`` predicate."""
    return pred(pred_id, "file", "dir_non_empty", path=path)


def pred_owned_by_run(pred_id: str, path: str) -> dict:
    """Shorthand: ``artifact_owned_by_run`` predicate with ``${run_id}``."""
    return pred(pred_id, "file", "artifact_owned_by_run", path=path, run_id="${run_id}")


def pred_gate_pass(pred_id: str, gate_id: str) -> dict:
    """Shorthand: ``gate_pass_recorded`` predicate for *gate_id*."""
    return pred(
        pred_id,
        "gate_pass",
        "gate_pass_recorded",
        gate_id=gate_id,
        run_id="${run_id}",
        tier4_root="docs/tier4_orchestration_state",
    )


def pred_json_field(pred_id: str, path: str, field: str) -> dict:
    """Shorthand: ``json_field_present`` schema predicate."""
    return pred(pred_id, "schema", "json_field_present", path=path, field=field)


def pred_json_fields(pred_id: str, path: str, fields: list[str]) -> dict:
    """Shorthand: ``json_fields_present`` schema predicate."""
    return {
        "predicate_id": pred_id,
        "type": "schema",
        "function": "json_fields_present",
        "args": {"path": path, "fields": fields},
        "fail_message": f"{pred_id} failed",
        "prose_condition": f"{pred_id} condition",
    }


def pred_source_refs(pred_id: str, path: str) -> dict:
    """Shorthand: ``source_refs_present`` predicate."""
    return pred(pred_id, "source_ref", "source_refs_present", path=path)


def pred_all_mappings_source_refs(pred_id: str, path: str) -> dict:
    """Shorthand: ``all_mappings_have_source_refs`` predicate."""
    return pred(pred_id, "source_ref", "all_mappings_have_source_refs", path=path)


def pred_timeline_within_duration(pred_id: str, gantt_path: str, call_path: str) -> dict:
    """Shorthand: ``timeline_within_duration`` predicate."""
    return pred(
        pred_id,
        "timeline",
        "timeline_within_duration",
        gantt_path=gantt_path,
        call_path=call_path,
    )


def pred_all_tasks_months(pred_id: str, gantt_path: str, wp_path: str) -> dict:
    """Shorthand: ``all_tasks_have_months`` coverage predicate."""
    return pred(
        pred_id,
        "coverage",
        "all_tasks_have_months",
        gantt_path=gantt_path,
        wp_path=wp_path,
    )


def pred_management_roles_in_tier3(pred_id: str, impl_path: str, partners_path: str) -> dict:
    """Shorthand: ``all_management_roles_in_tier3`` coverage predicate."""
    return pred(
        pred_id,
        "coverage",
        "all_management_roles_in_tier3",
        impl_path=impl_path,
        partners_path=partners_path,
    )


def pred_all_sections_drafted(pred_id: str, sections_path: str, schema_path: str) -> dict:
    """Shorthand: ``all_sections_drafted`` coverage predicate."""
    return pred(
        pred_id,
        "coverage",
        "all_sections_drafted",
        sections_path=sections_path,
        schema_path=schema_path,
    )


def pred_revision_actions_present(pred_id: str, path: str) -> dict:
    """Shorthand: ``revision_action_list_present`` schema predicate."""
    return pred(pred_id, "schema", "revision_action_list_present", path=path)


def pred_findings_by_severity(pred_id: str, path: str) -> dict:
    """Shorthand: ``findings_categorised_by_severity`` schema predicate."""
    return pred(pred_id, "schema", "findings_categorised_by_severity", path=path)


def pred_semantic(pred_id: str, function_: str, **args: str) -> dict:
    """Shorthand: semantic predicate dict."""
    return pred(pred_id, "semantic", function_, **args)


# ---------------------------------------------------------------------------
# Gate entry builder
# ---------------------------------------------------------------------------


def gate_entry(
    gate_id: str,
    gate_kind: str,
    node: str,
    predicates: list[dict],
    **extras: Any,
) -> dict:
    """
    Return a gate rules library entry dict.

    *node* is the DAG node ID (e.g. ``"n01"``).  ``evaluated_at`` is
    constructed as ``"<node> <gate_kind>"``.
    """
    entry: dict = {
        "gate_id": gate_id,
        "gate_kind": gate_kind,
        "evaluated_at": f"{node} {gate_kind}",
        "mandatory": False,
        "bypass_prohibited": False,
        "predicates": predicates,
    }
    entry.update(extras)
    return entry
