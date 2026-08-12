"""
evaluate_gate() — gate evaluation entry point (Steps 10 + 11, Approach B).

This module is the public entry point for running a single gate.  It:

1. Loads and validates the gate rules library.
2. Initialises or loads the run context (manifest + reuse policy).
3. Retrieves gate metadata (gate_kind, flags) from the library entry.
4. Resolves predicates via Approach B when the compiled manifest is available:
   reads ``predicate_refs`` from each manifest condition, then resolves each
   predicate_id to its full definition from the library (implementation
   registry).  Falls back to Approach A (library gate entry ``predicates``
   list) when the manifest is absent or the gate has no ``predicate_refs``.
5. Computes per-artifact and combined input fingerprints.
6. Evaluates every deterministic predicate, collecting **all** failures
   (no fast-fail).
7. If any deterministic predicate fails, skips semantic evaluation, sets
   ``skipped_semantic: True``, and writes a failing GateResult.
8. If all deterministic predicates pass, dispatches each semantic predicate
   via ``dispatch_semantic_predicate()`` (Step 11 — Claude API invocation).
   All semantic results are collected; pass/fail/malformed are each handled.
9. Writes a GateResult JSON artifact to the canonical Tier 4 path.
10. Updates node state in the run manifest (``released`` / ``blocked_at_exit``
    / ``blocked_at_entry`` / ``hard_block_upstream``).
11. Applies HARD_BLOCK propagation for ``gate_09_budget_consistency``.
12. Returns the GateResult as a Python dict.

Approach B predicate resolution (step 4):
  manifest.compile.yaml → predicate_refs → library.get_predicate(id)
  The manifest is the **composition source**; the library is the
  **implementation registry**.  See gate_rules_library_plan.md §9.

Semantic predicates are invoked via ``runner.semantic_dispatch.invoke_agent``,
which reads artifact files from disk, constructs system/user prompts embedding
artifact content and the applicable constitutional rule, and invokes the model
named by ``semantic_dispatch.AGENT_MODEL`` through the Claude runtime
transport.  Unknown function names and non-parseable responses produce a
``_dispatch_error`` sentinel that intentionally fails
``validate_semantic_result()``, surfacing as
``failure_reason: "semantic_result_malformed"`` in the GateResult.

See gate_rules_library_plan.md §6 for the full specification.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional, Union

from runner.gate_library import (
    GateLibrary,
    GateLibraryError,
    LIBRARY_REL_PATH,
)
from runner.manifest_reader import ManifestReader, ManifestReaderError
from runner.gate_result_registry import (
    GATE_RESULT_FALLBACK_SUBDIR,
    GATE_RESULT_PATHS,
    GATE_RESULT_SCHEMA_ID,
    TIER4_ROOT_REL,
)
from runner.fingerprints import compute_fingerprints
from runner.paths import find_repo_root, resolve_repo_path
from runner.predicates.scope_coverage_predicates import all_mandatory_scope_covered
from runner.predicates.coverage_predicates import (
    all_impacts_mapped,
    all_management_roles_in_tier3,
    all_partners_in_tier3,
    all_sections_drafted,
    all_sections_have_traceability_footer,
    all_tasks_have_months,
    all_wps_have_deliverable_and_lead,
    instrument_sections_addressed,
    kpis_traceable_to_wps,
    partner_budget_coverage_match,
    wp_budget_coverage_match,
)
from runner.predicates.criterion_predicates import (
    assumed_claims_are_operator_declared,
    cross_section_consistency,
    impact_pathways_covered,
    implementation_coverage_complete,
    no_unresolved_material_claims,
    schema_id_matches,
)
from runner.predicates.phase8_section_predicates import (
    canonical_terms_preserved,
    deliverable_identity_preserved,
    measurable_targets_preserved,
    no_stale_run_id,
    partner_names_preserved,
)
from runner.predicates.cycle_predicates import no_dependency_cycles
from runner.predicates.file_predicates import (
    artifact_owned_by_run,
    dir_non_empty,
    exists,
    non_empty,
    non_empty_json,
)
from runner.predicates.gate_pass_predicates import gate_pass_recorded
from runner.predicates.schema_predicates import (
    all_critical_revisions_resolved,
    budget_gate_confirmation_present,
    checkpoint_published,
    ethics_assessment_explicit,
    findings_categorised_by_severity,
    governance_matrix_present,
    instrument_type_matches_schema,
    interface_contract_conforms,
    json_field_present,
    json_fields_present,
    no_blocking_inconsistencies,
    revision_action_list_present,
    risk_register_populated,
    unit_cost_budget_resolved,
)
from runner.predicates.source_ref_predicates import (
    all_mappings_have_source_refs,
    source_refs_present,
)
from runner.predicates.timeline_predicates import (
    all_milestones_have_criteria,
    critical_path_present,
    dependency_schedule_consistency,
    timeline_within_duration,
    wp_count_within_limit,
)
from runner.predicates.types import PredicateResult
from runner.run_context import RunContext
from runner.semantic_dispatch import dispatch_semantic_predicate, validate_semantic_result
from runner.upstream_inputs import UPSTREAM_REQUIRED_INPUTS
from runner.versions import CONSTITUTION_VERSION, LIBRARY_VERSION, MANIFEST_VERSION

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Mandatory evaluation order for predicate types (gate_rules_library_plan §3).
PREDICATE_TYPE_ORDER: dict[str, int] = {
    "file": 0,
    "gate_pass": 1,
    "schema": 2,
    "source_ref": 3,
    "coverage": 4,
    "cycle": 5,
    "timeline": 6,
    "semantic": 7,
}

#: Types that map to deterministic (non-agent) predicates.
DETERMINISTIC_TYPES: frozenset[str] = frozenset(
    {"file", "gate_pass", "schema", "source_ref", "coverage", "cycle", "timeline"}
)

#: Gate that triggers HARD_BLOCK on budget-received-dir failure.
HARD_BLOCK_GATE: str = "gate_09_budget_consistency"

#: Tier-4 root and fallback gate-result subdir are sourced from
#: ``gate_result_registry`` (the authoritative path module, imported above) so
#: this write-path resolver and the schema_id backfill discovery tool read one
#: source instead of re-hardcoding the literals.  (Other path-computers —
#: ``dag_scheduler`` etc. — still keep local mirrors; converging them is out of
#: scope here.)  ``TIER4_ROOT_REL`` is re-exported via the import;
#: ``_FALLBACK_RESULT_SUB`` keeps its historical local name.
_FALLBACK_RESULT_SUB: str = GATE_RESULT_FALLBACK_SUBDIR

# ---------------------------------------------------------------------------
# Predicate dispatch registry
# ---------------------------------------------------------------------------
#
# Maps every function name string used in gate_rules_library.yaml to the
# corresponding Python callable.  Semantic predicate function names are
# intentionally absent; their absence is detected and handled explicitly.

PREDICATE_REGISTRY: dict[str, Callable[..., PredicateResult]] = {
    # --- file predicates (Step 3 + Step 10) ---
    "exists": exists,
    "non_empty": non_empty,
    "non_empty_json": non_empty_json,
    "dir_non_empty": dir_non_empty,
    "artifact_owned_by_run": artifact_owned_by_run,
    # --- gate-pass predicate (Step 4) ---
    "gate_pass_recorded": gate_pass_recorded,
    # --- schema predicates (Step 5) ---
    "json_field_present": json_field_present,
    "json_fields_present": json_fields_present,
    "instrument_type_matches_schema": instrument_type_matches_schema,
    "interface_contract_conforms": interface_contract_conforms,
    "risk_register_populated": risk_register_populated,
    "ethics_assessment_explicit": ethics_assessment_explicit,
    "governance_matrix_present": governance_matrix_present,
    "no_blocking_inconsistencies": no_blocking_inconsistencies,
    "unit_cost_budget_resolved": unit_cost_budget_resolved,
    "budget_gate_confirmation_present": budget_gate_confirmation_present,
    "findings_categorised_by_severity": findings_categorised_by_severity,
    "revision_action_list_present": revision_action_list_present,
    "all_critical_revisions_resolved": all_critical_revisions_resolved,
    "checkpoint_published": checkpoint_published,
    # --- source-reference predicates (Step 6) ---
    "source_refs_present": source_refs_present,
    "all_mappings_have_source_refs": all_mappings_have_source_refs,
    # --- coverage predicates (Step 7) ---
    "wp_budget_coverage_match": wp_budget_coverage_match,
    "partner_budget_coverage_match": partner_budget_coverage_match,
    "all_impacts_mapped": all_impacts_mapped,
    "kpis_traceable_to_wps": kpis_traceable_to_wps,
    "all_sections_drafted": all_sections_drafted,
    "all_partners_in_tier3": all_partners_in_tier3,
    "all_management_roles_in_tier3": all_management_roles_in_tier3,
    "all_tasks_have_months": all_tasks_have_months,
    "instrument_sections_addressed": instrument_sections_addressed,
    "all_sections_have_traceability_footer": all_sections_have_traceability_footer,
    "all_wps_have_deliverable_and_lead": all_wps_have_deliverable_and_lead,
    # --- scope coverage predicate (Phase 2 gate) ---
    "all_mandatory_scope_covered": all_mandatory_scope_covered,
    # --- cycle predicate (Step 8) ---
    "no_dependency_cycles": no_dependency_cycles,
    # --- timeline predicates (Step 9) ---
    "timeline_within_duration": timeline_within_duration,
    "all_milestones_have_criteria": all_milestones_have_criteria,
    "wp_count_within_limit": wp_count_within_limit,
    "critical_path_present": critical_path_present,
    "dependency_schedule_consistency": dependency_schedule_consistency,
    # --- criterion-aligned predicates (Phase 8 refactor) ---
    "schema_id_matches": schema_id_matches,
    "no_unresolved_material_claims": no_unresolved_material_claims,
    "assumed_claims_are_operator_declared": assumed_claims_are_operator_declared,
    "impact_pathways_covered": impact_pathways_covered,
    "implementation_coverage_complete": implementation_coverage_complete,
    "cross_section_consistency": cross_section_consistency,
    # --- Phase 8 section preflight predicates ---
    "no_stale_run_id": no_stale_run_id,
    "partner_names_preserved": partner_names_preserved,
    "deliverable_identity_preserved": deliverable_identity_preserved,
    "canonical_terms_preserved": canonical_terms_preserved,
    "measurable_targets_preserved": measurable_targets_preserved,
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _substitute_runtime_args(args: dict, run_id: str) -> dict:
    """
    Replace ``${run_id}`` in all string values within *args*.

    Operates recursively on list values.  Other types are passed through
    unchanged.
    """
    result: dict = {}
    for key, value in args.items():
        if isinstance(value, str):
            result[key] = value.replace("${run_id}", run_id)
        elif isinstance(value, list):
            result[key] = [
                item.replace("${run_id}", run_id)
                if isinstance(item, str)
                else item
                for item in value
            ]
        else:
            result[key] = value
    return result


def _extract_node_id(evaluated_at: str) -> str:
    """
    Extract the node identifier from the ``evaluated_at`` field.

    Example: ``"n01 exit"`` → ``"n01"``.
    """
    parts = (evaluated_at or "").strip().split()
    return parts[0] if parts else "unknown"


def _gate_result_path(gate_id: str, repo_root: Path) -> Path:
    """
    Resolve the canonical Tier 4 write path for a gate result.

    Uses :data:`runner.gate_result_registry.GATE_RESULT_PATHS` when the
    gate_id is registered.  Falls back to
    ``docs/tier4_orchestration_state/gate_results/<gate_id>.json`` for
    gate_ids not in the registry (useful in tests).
    """
    tier4_root = repo_root / TIER4_ROOT_REL
    if gate_id in GATE_RESULT_PATHS:
        return tier4_root / GATE_RESULT_PATHS[gate_id]
    return tier4_root / _FALLBACK_RESULT_SUB / f"{gate_id}.json"


def _call_predicate(
    func_name: str,
    raw_args: dict,
    run_id: str,
    repo_root: Path,
    reuse_policy_path: Optional[Path],
) -> PredicateResult:
    """
    Call the predicate function identified by *func_name*.

    Substitutes ``${run_id}`` in args, injects ``repo_root``, and for
    ``artifact_owned_by_run`` also injects ``reuse_policy_path``.

    If *func_name* is not in the registry, returns a failing
    ``PredicateResult`` with ``MALFORMED_ARTIFACT`` so the gate can
    collect the failure rather than crashing.
    """
    from runner.predicates.types import MALFORMED_ARTIFACT

    if func_name not in PREDICATE_REGISTRY:
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=f"Unknown predicate function in library: {func_name!r}",
            details={"function": func_name},
        )

    call_args = _substitute_runtime_args(raw_args or {}, run_id)
    call_args["repo_root"] = repo_root

    # Inject reuse policy path for the ownership predicate
    if func_name == "artifact_owned_by_run" and reuse_policy_path is not None:
        call_args["reuse_policy_path"] = reuse_policy_path

    func = PREDICATE_REGISTRY[func_name]
    try:
        return func(**call_args)
    except TypeError as exc:
        # Argument mismatch: treat as a library authoring error
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=(
                f"Predicate {func_name!r} rejected its argument list: {exc}.  "
                "Check the 'args' entry in gate_rules_library.yaml."
            ),
            details={"function": func_name, "error": str(exc)},
        )


def _is_hard_block_failure(
    gate_id: str,
    gate_entry: dict,
    failed_predicates: list[dict],
) -> bool:
    """
    Return ``True`` when a HARD_BLOCK condition is detected.

    A HARD_BLOCK occurs on ``gate_09_budget_consistency`` when the
    ``hard_block_on_missing_received_dir: true`` flag is set and a
    ``dir_non_empty`` predicate targeting the ``received/`` path fails
    (gate_rules_library_plan.md §6.4).
    """
    if gate_id != HARD_BLOCK_GATE:
        return False
    if not gate_entry.get("hard_block_on_missing_received_dir"):
        return False
    for fp in failed_predicates:
        # Lump-sum branch: the external ``received/`` response is absent.
        if fp.get("function") == "dir_non_empty":
            path_arg = (fp.get("args") or {}).get("path", "")
            if "received" in str(path_arg):
                return True
        # Unit-cost branch (C1): the internal deterministic derivation is
        # unresolved (missing/blocked ``unit_cost_budget.json``), or the
        # instrument budget regime could not be resolved to select a source.
        # Both are an absent/unresolved budget source — the same categorical
        # Phase-8 block as a missing lump-sum response (§8.4).
        if fp.get("function") in (
            "unit_cost_budget_resolved",
            _INSTRUMENT_UNRESOLVED_FUNC,
        ):
            return True
    return False


#: Synthetic predicate ``function`` used to record an instrument-resolution
#: fail-closed on a gate carrying ``applies_when`` predicates.  It is not a
#: real predicate — it is the fail-closed marker the evaluator emits when a
#: gate's applicable-predicate set cannot be selected because the instrument
#: budget regime is unresolvable (§12.4, fail closed).
_INSTRUMENT_UNRESOLVED_FUNC: str = "instrument_budget_regime_resolvable"


def _resolve_budget_regime(repo_root: Path) -> Optional[str]:
    """Resolve the selected call's budget regime, or ``None`` if unresolvable.

    Thin wrapper over :func:`runner.instrument_profile.resolve_instrument_profile`
    that never raises: any failure to resolve the instrument profile (absent
    call binding, unknown instrument, malformed registry) returns ``None`` so
    the caller can fail the gate closed with a clear reason rather than crash.
    """
    try:
        from runner.instrument_profile import resolve_instrument_profile

        return resolve_instrument_profile(repo_root).budget_regime
    except Exception:  # noqa: BLE001 — any resolution failure ⇒ None (fail closed upstream)
        return None


def _partition_predicates_by_instrument(
    all_predicates: list[dict],
    repo_root: Path,
) -> tuple[list[dict], list[dict], Optional[str]]:
    """Filter instrument-conditional predicates by the resolved budget regime.

    A predicate may carry an ``applies_when: {budget_regime: <regime>}`` tag
    (C1): it is evaluated only when the selected call's budget regime matches.
    This is how ``gate_09`` is **instrument-conditional on source** — the
    lump-sum ``received/`` predicates apply only to lump-sum instruments; the
    unit-cost derivation predicates apply only to unit-cost instruments — with
    the lump-sum predicates preserved verbatim (RIA reachable, D1) and no
    instrument literal on the gate path (§2, programme-agnostic).

    Predicates with **no** ``applies_when`` always apply (the common case;
    unchanged behaviour for every existing gate and synthetic-library test).

    Returns
    -------
    (applicable, skipped, resolution_error)
        *applicable* — predicates to evaluate.
        *skipped* — records of predicates skipped as not-applicable for the
        resolved regime (informational; recorded in the gate result).
        *resolution_error* — a human-readable reason when the gate has
        ``applies_when`` predicates but the budget regime is unresolvable, in
        which case the gate must **fail closed** (§12.4); ``None`` otherwise.
    """
    if not any(p.get("applies_when") for p in all_predicates):
        return all_predicates, [], None

    regime = _resolve_budget_regime(repo_root)
    applicable: list[dict] = []
    skipped: list[dict] = []

    for pred in all_predicates:
        applies_when = pred.get("applies_when")
        if not applies_when:
            applicable.append(pred)
            continue
        want_regime = applies_when.get("budget_regime")
        if regime is not None and want_regime == regime:
            applicable.append(pred)
        else:
            skipped.append({
                "predicate_id": pred.get("predicate_id", "<unknown>"),
                "applies_when": applies_when,
                "resolved_budget_regime": regime,
                "reason": (
                    "not applicable for resolved budget_regime"
                    if regime is not None
                    else "budget_regime unresolvable"
                ),
            })

    resolution_error: Optional[str] = None
    if regime is None:
        resolution_error = (
            "gate has instrument-conditional predicates (applies_when) but "
            "the selected call's budget_regime could not be resolved from "
            "selected_call.json / the instrument registries; failing closed "
            "(§12.4) — the budget source cannot be selected."
        )
    return applicable, skipped, resolution_error


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def evaluate_gate(
    gate_id: str,
    run_id: str,
    repo_root: Union[str, Path],
    *,
    library_path: Optional[Path] = None,
    manifest_path: Optional[Path] = None,
) -> dict:
    """
    Evaluate all predicates for *gate_id* and write a GateResult.

    Parameters
    ----------
    gate_id:
        The gate identifier from ``gate_rules_library.yaml``.
    run_id:
        UUID for the current DAG run (established by
        :func:`runner.run_context.RunContext.initialize`).
    repo_root:
        Absolute path to the repository root directory.
    library_path:
        Optional explicit path to the gate rules library YAML.  When
        ``None``, the library is loaded from
        ``repo_root / LIBRARY_REL_PATH``.  Primarily used in tests.
    manifest_path:
        Optional explicit path to ``manifest.compile.yaml``.  When
        ``None``, the manifest is loaded from
        ``repo_root / MANIFEST_REL_PATH`` if it exists.  When the manifest
        is absent or raises :exc:`ManifestReaderError`, predicate
        composition falls back to the library gate entry (Approach A).
        Primarily used in tests.

    Returns
    -------
    dict
        The GateResult as a Python dict (same content as written to Tier 4).

    Notes
    -----
    * **Approach B (default when manifest present):** predicate composition
      is read from ``manifest.compile.yaml`` ``predicate_refs`` lists; each
      predicate ID is resolved to its full definition via
      :meth:`GateLibrary.get_predicate`.
    * **Approach A fallback (manifest absent or gate has no predicate_refs):**
      predicates are taken directly from the library gate entry ``predicates``
      list.
    * All deterministic predicate failures are collected in one pass; no
      fast-fail on first failure.
    * If any deterministic predicate fails, semantic evaluation is skipped
      and ``skipped_semantic`` is set ``True`` in the result.
    * If all deterministic predicates pass, semantic predicates are
      dispatched through :func:`dispatch_semantic_predicate` (the Step 11
      semantic layer).  Malformed semantic results are treated as gate
      failure and recorded as ``semantic_result_malformed``.
    * A gate passes only when all required deterministic **and** semantic
      predicates pass.
    * HARD_BLOCK for ``gate_09_budget_consistency`` is flagged in the
      result and propagated to Phase 8 nodes in the run manifest.
    """
    repo_root = Path(repo_root)
    evaluated_at_str = datetime.now(timezone.utc).isoformat()

    # ------------------------------------------------------------------
    # 1. Load gate rules library
    # ------------------------------------------------------------------
    lib = GateLibrary.load(
        library_path,
        repo_root=repo_root,
        expected_manifest_version=MANIFEST_VERSION,
    )

    # ------------------------------------------------------------------
    # 2. Retrieve gate entry
    # ------------------------------------------------------------------
    gate_entry = lib.get_gate(gate_id)
    gate_kind: str = gate_entry["gate_kind"]
    node_id: str = _extract_node_id(gate_entry.get("evaluated_at", ""))

    # ------------------------------------------------------------------
    # 3. Load (or create) run context
    # ------------------------------------------------------------------
    try:
        run_ctx = RunContext.load(repo_root, run_id)
    except FileNotFoundError:
        run_ctx = RunContext.initialize(repo_root, run_id)

    reuse_policy_path: Path = run_ctx.reuse_policy_path

    # ------------------------------------------------------------------
    # 4. Resolve predicates (Approach B via manifest; fallback to library)
    # ------------------------------------------------------------------
    #
    # Approach B: read predicate_refs from manifest gate conditions, then
    # resolve each predicate_id to its full definition from the library.
    # The manifest is the composition source; the library is the registry.
    #
    # Approach A fallback: the library gate entry's ``predicates`` list is
    # used when the manifest is absent or the gate has no predicate_refs
    # (e.g. tests that do not create a manifest in the synthetic repo root).
    _predicate_refs: Optional[list[str]] = None
    try:
        _manifest_rdr = ManifestReader.load(manifest_path, repo_root=repo_root)
        _predicate_refs = _manifest_rdr.get_predicate_refs(gate_id)
    except ManifestReaderError:
        _predicate_refs = None  # manifest absent or unreadable — use fallback

    if _predicate_refs is not None:
        # Approach B: resolve each predicate_id from the library
        all_predicates: list[dict] = [
            lib.get_predicate(pid) for pid in _predicate_refs
        ]
    else:
        # Approach A fallback: library gate entry provides the predicates list
        all_predicates = gate_entry.get("predicates") or []

    # Instrument-conditional predicate filtering (C1): a predicate carrying
    # ``applies_when: {budget_regime: ...}`` is evaluated only when it matches
    # the selected call's regime.  This is how gate_09 branches on source
    # (lump-sum ``received/`` vs unit-cost internal derivation) with the
    # lump-sum predicates preserved verbatim.  Predicates with no applies_when
    # are unaffected (every other gate, and every synthetic-library test).
    all_predicates, skipped_predicates, applies_when_error = (
        _partition_predicates_by_instrument(all_predicates, repo_root)
    )

    deterministic_preds = [
        p for p in all_predicates if p.get("type") in DETERMINISTIC_TYPES
    ]
    semantic_preds = [
        p for p in all_predicates if p.get("type") == "semantic"
    ]

    # Sort deterministic predicates by the mandatory type order
    deterministic_preds.sort(
        key=lambda p: PREDICATE_TYPE_ORDER.get(p.get("type", ""), 99)
    )

    # ------------------------------------------------------------------
    # 5. Compute input fingerprints
    # ------------------------------------------------------------------
    upstream_paths: list[str] = UPSTREAM_REQUIRED_INPUTS.get(gate_id, [])
    per_artifact_fps, combined_fp = compute_fingerprints(
        upstream_paths, repo_root
    )

    # ------------------------------------------------------------------
    # 6. Evaluate all deterministic predicates (collect-all-failures)
    # ------------------------------------------------------------------
    passed_det_ids: list[str] = []
    failed_det_entries: list[dict] = []

    for pred in deterministic_preds:
        pred_id: str = pred.get("predicate_id", "<unknown>")
        func_name: str = pred.get("function", "")
        raw_args: dict = pred.get("args") or {}
        pred_type: str = pred.get("type", "")

        result: PredicateResult = _call_predicate(
            func_name, raw_args, run_id, repo_root, reuse_policy_path
        )

        if result.passed:
            passed_det_ids.append(pred_id)
        else:
            failed_det_entries.append(
                {
                    "predicate_id": pred_id,
                    "type": pred_type,
                    "function": func_name,
                    "args": _substitute_runtime_args(raw_args, run_id),
                    "failure_category": result.failure_category,
                    "reason": result.reason,
                    "details": result.details,
                    "fail_message": pred.get("fail_message", ""),
                    "prose_condition": pred.get("prose_condition", ""),
                }
            )

    # Instrument-conditional fail-closed: the gate declared ``applies_when``
    # predicates but the budget regime was unresolvable, so the applicable
    # predicate set could not be selected.  Record a deterministic failure so
    # the gate blocks (§12.4) rather than passing on a subset.
    if applies_when_error is not None:
        failed_det_entries.append(
            {
                "predicate_id": "instrument_conditional_gate",
                "type": "schema",
                "function": _INSTRUMENT_UNRESOLVED_FUNC,
                "args": {},
                "failure_category": "MISSING_MANDATORY_INPUT",
                "reason": applies_when_error,
                "details": {},
                "fail_message": applies_when_error,
                "prose_condition": "Instrument budget_regime resolvable",
            }
        )

    # ------------------------------------------------------------------
    # 7. Decide overall status
    # ------------------------------------------------------------------
    deterministic_all_passed = len(failed_det_entries) == 0

    if not deterministic_all_passed:
        # Deterministic failure: semantic evaluation is skipped
        overall_status = "fail"
        skipped_semantic = True
        semantic_section: dict = {"passed": [], "failed": [], "skipped": True}
    elif semantic_preds:
        # ------------------------------------------------------------------
        # Step 11: dispatch and evaluate semantic predicates
        # ------------------------------------------------------------------
        skipped_semantic = False
        passed_sem_ids: list[str] = []
        failed_sem_entries: list[dict] = []

        for sem_pred in semantic_preds:
            raw = dispatch_semantic_predicate(sem_pred, run_id, repo_root)
            is_valid, validation_err = validate_semantic_result(raw)

            if not is_valid:
                # Malformed result or dispatch error — treat as gate failure
                failed_sem_entries.append(
                    {
                        "predicate_id": raw.get(
                            "predicate_id",
                            sem_pred.get("predicate_id", "<unknown>"),
                        ),
                        "function": raw.get(
                            "function",
                            sem_pred.get("function", "<unknown>"),
                        ),
                        "failure_reason": "semantic_result_malformed",
                        "validation_error": validation_err,
                        "_dispatch_error": raw.get("_dispatch_error", False),
                        "_dispatch_error_reason": raw.get(
                            "_dispatch_error_reason", ""
                        ),
                    }
                )
            elif raw["status"] == "pass":
                passed_sem_ids.append(raw["predicate_id"])
            elif raw.get("_dispatch_error"):
                # Dispatch-level failure (transport error, unknown function,
                # malformed response) — surface the real cause distinctly.
                failed_sem_entries.append(
                    {
                        "predicate_id": raw["predicate_id"],
                        "function": raw["function"],
                        "failure_reason": "semantic_dispatch_error",
                        "constitutional_rule": raw.get(
                            "constitutional_rule", ""
                        ),
                        "fail_message": raw.get("fail_message", ""),
                        "artifacts_inspected": raw.get(
                            "artifacts_inspected", []
                        ),
                        "_dispatch_error": True,
                        "_dispatch_error_reason": raw.get(
                            "_dispatch_error_reason", ""
                        ),
                        "_dispatch_error_category": raw.get(
                            "_dispatch_error_category", ""
                        ),
                        "_diagnostic_bundle_path": raw.get(
                            "_diagnostic_bundle_path"
                        ),
                    }
                )
            else:
                # Genuine semantic failure from agent evaluation
                failed_sem_entries.append(
                    {
                        "predicate_id": raw["predicate_id"],
                        "function": raw["function"],
                        "failure_reason": "semantic_fail",
                        "constitutional_rule": raw.get(
                            "constitutional_rule", ""
                        ),
                        "findings": raw.get("findings", []),
                        "fail_message": raw.get("fail_message", ""),
                        "artifacts_inspected": raw.get(
                            "artifacts_inspected", []
                        ),
                    }
                )

        overall_status = "fail" if failed_sem_entries else "pass"
        semantic_section = {
            "passed": passed_sem_ids,
            "failed": failed_sem_entries,
        }
    else:
        # Full deterministic pass, no semantic predicates: gate passes
        overall_status = "pass"
        skipped_semantic = False
        semantic_section = {"passed": [], "failed": []}

    # ------------------------------------------------------------------
    # 8. HARD_BLOCK detection
    # ------------------------------------------------------------------
    hard_block = _is_hard_block_failure(gate_id, gate_entry, failed_det_entries)
    if hard_block:
        run_ctx.mark_hard_block_downstream()

    # ------------------------------------------------------------------
    # 9. Compute canonical result path
    # ------------------------------------------------------------------
    result_path = _gate_result_path(gate_id, repo_root)
    result_path.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 10. Build GateResult dict (§6.2)
    # ------------------------------------------------------------------
    gate_result: dict[str, Any] = {
        # Required by artifact_schema_specification.yaml (gate_result_schema):
        # every gate result file MUST carry this schema_id, and a consumer that
        # finds a different/absent value fails with MALFORMED_ARTIFACT (e.g.
        # checkpoint-publish at n08f).  Historically omitted; added here so the
        # evaluator's output conforms to its own declared schema.  This is the
        # sole gate-result write path in the runtime (§17.6.3).
        "schema_id": GATE_RESULT_SCHEMA_ID,
        "gate_id": gate_id,
        "gate_kind": gate_kind,
        "run_id": run_id,
        "manifest_version": lib.manifest_version,
        "library_version": lib.library_version,
        "constitution_version": lib.constitution_version,
        "input_fingerprint": combined_fp,
        "input_artifact_fingerprints": per_artifact_fps,
        "evaluated_at": evaluated_at_str,
        "repo_root": str(repo_root),
        "status": overall_status,
        "deterministic_predicates": {
            "passed": passed_det_ids,
            "failed": failed_det_entries,
        },
        "semantic_predicates": semantic_section,
        "skipped_semantic": skipped_semantic,
        "report_written_to": str(result_path),
    }

    # Record instrument-conditional predicates skipped as not-applicable for
    # the resolved budget regime (C1) — informational, for auditability.
    if skipped_predicates:
        gate_result["skipped_not_applicable_predicates"] = skipped_predicates

    if hard_block:
        gate_result["hard_block"] = True
        gate_result["hard_block_reason"] = (
            "dir_non_empty check on "
            "docs/integrations/lump_sum_budget_planner/received/ failed.  "
            "No Phase 8 activity may proceed until the budget gate passes.  "
            "All Phase 8 nodes have been frozen with HARD_BLOCK_UPSTREAM status."
        )

    # ------------------------------------------------------------------
    # 11. Write GateResult to Tier 4
    # ------------------------------------------------------------------
    result_path.write_text(
        json.dumps(gate_result, indent=2), encoding="utf-8"
    )

    # ------------------------------------------------------------------
    # 12. Update node state in run manifest
    # ------------------------------------------------------------------
    if overall_status == "fail":
        if gate_kind == "entry":
            run_ctx.set_node_state(node_id, "blocked_at_entry")
        else:
            run_ctx.set_node_state(node_id, "blocked_at_exit")
    elif overall_status == "pass":
        run_ctx.set_node_state(node_id, "released")

    run_ctx.save()

    return gate_result
