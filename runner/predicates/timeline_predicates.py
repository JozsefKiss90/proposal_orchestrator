"""
Step 9 — Timeline predicates.

Implements the four scheduling-consistency predicates defined in
gate_rules_library_plan.md §4.6 and §4.7:

    timeline_within_duration(gantt_path, call_path, *, repo_root=None)
    all_milestones_have_criteria(gantt_path, *, repo_root=None)
    wp_count_within_limit(wp_path, schema_path, *, repo_root=None)
    critical_path_present(gantt_path, *, repo_root=None)

All four are deterministic arithmetic / structural checks over parsed artifacts.
They do not validate dependency-ordering correctness (Step 8) or invoke agents
(Step 11).  They do not emit GateResult artifacts (Step 10).

---------------------------------------------------------------------------
Artifact structural assumptions
---------------------------------------------------------------------------

gantt.json (canonical Phase 4 output)
--------------------------------------
Source: artifact_schema_specification.yaml §1.4

    {
        "tasks": [
            {"task_id": "T1.1", "wp_id": "WP1", "start_month": 1,
             "end_month": 6, "responsible_partner": "P1"},
            ...
        ],
        "milestones": [
            {"milestone_id": "MS1", "title": "...", "due_month": 6,
             "verifiable_criterion": "...", "responsible_wp": "WP1"},
            ...
        ],
        "critical_path": ["T1.1", "T2.3", "MS2", ...]
    }

``tasks``:          Required array.  Each entry must be a dict with string
                    ``task_id``, string ``wp_id``, integer ``start_month``,
                    integer ``end_month``, string ``responsible_partner``.
                    ``end_month`` is the field checked against project duration.

``milestones``:     Required array.  Each entry must be a dict with at minimum:
                    - ``due_month``: integer, non-null
                    - ``verifiable_criterion``: string, non-null and non-blank

``critical_path``:  Required array of strings (task_ids and/or milestone_ids).
                    Must be non-empty for ``critical_path_present`` to pass.
                    The schema defines this as an array.  ``critical_path_present``
                    also accepts non-empty strings, non-empty objects in case a
                    producing agent writes an alternative representation, but the
                    canonical form is an array per the schema.

selected_call.json (Tier 3 call binding artifact)
--------------------------------------------------
Source: artifact_schema_specification.yaml §5.x (tier3_instantiation_schemas)

    {
        "project_duration_months": 36,
        ...
    }

``project_duration_months``:  Required integer.  Maximum project duration as
                               specified in the call.  All task ``end_month``
                               values in gantt.json must be ≤ this value for
                               ``timeline_within_duration`` to pass.
                               A non-positive value is treated as malformed.

wp_structure.json (canonical Phase 3 output)
--------------------------------------------
Source: artifact_schema_specification.yaml §1.3

    {
        "work_packages": [
            {"wp_id": "WP1", ...},
            {"wp_id": "WP2", ...},
            ...
        ],
        ...
    }

``work_packages``:  Required array.  Length = number of WPs in the Phase 3 output.

section_schema_registry.json (Tier 2A extracted)
-------------------------------------------------
Source: artifact_schema_specification.yaml §8

The registry format is ambiguous in the current repository (two co-existing
representations observed in different predicate modules):

Form A — object with instrument-type keys (assumed by schema_predicates.py Step 5):
    {
        "RIA": {"max_work_packages": 8, "sections": [...], ...},
        "IA":  {"max_work_packages": 10, ...},
        ...
    }

Form B — object with top-level ``instruments`` array (per artifact_schema_specification.yaml §8):
    {
        "instruments": [
            {"instrument_type": "RIA", "max_work_packages": 8, "sections": [...], ...},
            ...
        ]
    }

Both forms are supported.  ``max_work_packages`` is extracted from whichever
form is present.  Since the predicate signature ``wp_count_within_limit(wp_path,
schema_path)`` does not receive an instrument_type argument, the following
resolution rule is applied:

1.  Collect all ``max_work_packages`` integer values found across all
    instrument entries in the registry.
2.  If no values are found → fail with MALFORMED_ARTIFACT (missing constraint).
3.  If one or more values are found → use the **minimum** (most conservative /
    strictest constraint).  This is the narrowest correct interpretation: if the
    active instrument cannot be determined from the predicate's inputs alone, the
    strictest available constraint is applied to avoid false passes.

This interpretation is documented here and encoded in the tests.  When the
full runner (Step 10) resolves instrument_type from the gate context and passes
a pre-filtered registry, this predicate will naturally produce the correct result
because only one instrument entry will be present.

---------------------------------------------------------------------------
Failure-category mapping (Step 9)
---------------------------------------------------------------------------

gate_rules_library_plan.md §3 defines the mapping for timeline predicates:

    MISSING_MANDATORY_INPUT     — required artifact file does not exist
    MALFORMED_ARTIFACT          — file present but not valid JSON, or required
                                  fields absent/wrong type
    CROSS_ARTIFACT_INCONSISTENCY — scheduling constraint violated: task ends
                                   after duration, milestone missing criterion,
                                   critical_path absent
    POLICY_VIOLATION            — wp_count_within_limit only: WP count exceeds
                                   the instrument's structural rule (structurally
                                   valid content violating an instrument limit,
                                   not a cross-artifact data inconsistency)

``STALE_UPSTREAM_MISMATCH`` is not used in Step 9.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List, Optional, Union

from runner.predicates.types import (
    CROSS_ARTIFACT_INCONSISTENCY,
    MALFORMED_ARTIFACT,
    MISSING_MANDATORY_INPUT,
    POLICY_VIOLATION,
    PredicateResult,
)

try:
    from runner.paths import resolve_repo_path
except ImportError:  # pragma: no cover — only missing in isolated test envs
    def resolve_repo_path(path: Any, repo_root: Optional[str]) -> Path:  # type: ignore[misc]
        return Path(path)

PathLike = Union[str, Path]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _read_json_object(
    resolved: Path,
) -> tuple[Optional[dict], Optional[PredicateResult]]:
    """Read *resolved* as a JSON object (dict).  Return (dict, None) or (None, err)."""
    if not resolved.exists():
        return None, PredicateResult(
            passed=False,
            failure_category=MISSING_MANDATORY_INPUT,
            reason=f"Required file not found: {resolved}",
            details={"path": str(resolved)},
        )
    if resolved.is_dir():
        return None, PredicateResult(
            passed=False,
            failure_category=MISSING_MANDATORY_INPUT,
            reason=(
                f"Expected a JSON file but found a directory: {resolved}.  "
                "This predicate requires a canonical artifact file path."
            ),
            details={"path": str(resolved), "is_dir": True},
        )
    try:
        text = resolved.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        return None, PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=f"File is not valid UTF-8: {exc}",
            details={"path": str(resolved), "encoding_error": str(exc)},
        )
    if not text.strip():
        return None, PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=f"File is empty: {resolved}",
            details={"path": str(resolved)},
        )
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        return None, PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=f"Invalid JSON in {resolved}: {exc}",
            details={"path": str(resolved), "json_error": str(exc)},
        )
    if not isinstance(parsed, dict):
        return None, PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=(
                f"Expected a JSON object in {resolved}, "
                f"got {type(parsed).__name__}."
            ),
            details={"path": str(resolved), "parsed_type": type(parsed).__name__},
        )
    return parsed, None


def _extract_max_wp_values(registry: dict) -> List[int]:
    """
    Extract all ``max_work_packages`` integer values from the section schema
    registry, supporting both known formats (see module docstring).

    Returns a list of non-negative integers found.  Empty list means no
    ``max_work_packages`` constraint is present anywhere in the registry.
    """
    found: List[int] = []

    # Form B: top-level ``instruments`` array
    instruments_raw = registry.get("instruments")
    if isinstance(instruments_raw, list):
        for entry in instruments_raw:
            if isinstance(entry, dict):
                mwp = entry.get("max_work_packages")
                if isinstance(mwp, int) and not isinstance(mwp, bool):
                    found.append(mwp)
        return found

    # Form A: top-level keys are instrument-type strings, values are dicts
    for value in registry.values():
        if isinstance(value, dict):
            mwp = value.get("max_work_packages")
            if isinstance(mwp, int) and not isinstance(mwp, bool):
                found.append(mwp)

    return found


# ---------------------------------------------------------------------------
# Public predicates
# ---------------------------------------------------------------------------


def timeline_within_duration(
    gantt_path: PathLike,
    call_path: PathLike,
    *,
    repo_root: Optional[str] = None,
) -> PredicateResult:
    """
    Verify that every task end month in the Gantt output is within the project
    duration specified in ``selected_call.json``.

    Parameters
    ----------
    gantt_path:
        Path to the canonical Phase 4 artifact ``gantt.json``.
    call_path:
        Path to the Tier 3 call binding artifact ``selected_call.json``.
    repo_root:
        Optional repository root for path resolution.

    Returns
    -------
    PredicateResult
        Passes when all task ``end_month`` values are ≤ ``project_duration_months``.
        Fails with:
        - MISSING_MANDATORY_INPUT if either file is absent.
        - MALFORMED_ARTIFACT if either file cannot be parsed, ``project_duration_months``
          is missing/non-integer/non-positive, or any task entry is malformed.
        - CROSS_ARTIFACT_INCONSISTENCY if any task ends after the allowed duration.
    """
    gantt_resolved = resolve_repo_path(gantt_path, repo_root)
    call_resolved = resolve_repo_path(call_path, repo_root)

    gantt, err = _read_json_object(gantt_resolved)
    if err:
        return err

    call_data, err = _read_json_object(call_resolved)
    if err:
        return err

    # --- Read duration ---
    duration_raw = call_data.get("project_duration_months")
    if duration_raw is None:
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=(
                "selected_call.json is missing required field "
                "'project_duration_months' "
                "(artifact_schema_specification.yaml tier3_instantiation_schemas)"
            ),
            details={"path": str(call_resolved)},
        )
    if not isinstance(duration_raw, int) or isinstance(duration_raw, bool):
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=(
                f"'project_duration_months' must be an integer; "
                f"got {type(duration_raw).__name__}: {duration_raw!r}"
            ),
            details={
                "path": str(call_resolved),
                "actual_type": type(duration_raw).__name__,
                "actual_value": duration_raw,
            },
        )
    if duration_raw <= 0:
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=(
                f"'project_duration_months' must be a positive integer; "
                f"got {duration_raw}"
            ),
            details={"path": str(call_resolved), "actual_value": duration_raw},
        )

    # --- Read tasks ---
    tasks_raw = gantt.get("tasks")
    if tasks_raw is None or not isinstance(tasks_raw, list):
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=(
                "gantt.json is missing required field 'tasks' or it is not an array "
                "(artifact_schema_specification.yaml §1.4)"
            ),
            details={"path": str(gantt_resolved)},
        )

    # --- Check each task's end_month ---
    over_duration: list[dict] = []
    for i, task in enumerate(tasks_raw):
        if not isinstance(task, dict):
            return PredicateResult(
                passed=False,
                failure_category=MALFORMED_ARTIFACT,
                reason=(
                    f"gantt.json tasks[{i}] must be a dict; "
                    f"got {type(task).__name__}: {task!r}"
                ),
                details={"path": str(gantt_resolved), "bad_task_index": i},
            )
        end_raw = task.get("end_month")
        if end_raw is None:
            return PredicateResult(
                passed=False,
                failure_category=MALFORMED_ARTIFACT,
                reason=(
                    f"gantt.json tasks[{i}] (task_id={task.get('task_id')!r}) "
                    f"is missing required field 'end_month'"
                ),
                details={
                    "path": str(gantt_resolved),
                    "bad_task_index": i,
                    "task_id": task.get("task_id"),
                },
            )
        if not isinstance(end_raw, int) or isinstance(end_raw, bool):
            return PredicateResult(
                passed=False,
                failure_category=MALFORMED_ARTIFACT,
                reason=(
                    f"gantt.json tasks[{i}] (task_id={task.get('task_id')!r}) "
                    f"'end_month' must be an integer; "
                    f"got {type(end_raw).__name__}: {end_raw!r}"
                ),
                details={
                    "path": str(gantt_resolved),
                    "bad_task_index": i,
                    "task_id": task.get("task_id"),
                    "actual_type": type(end_raw).__name__,
                },
            )
        if end_raw > duration_raw:
            over_duration.append(
                {
                    "task_id": task.get("task_id"),
                    "end_month": end_raw,
                    "allowed_duration": duration_raw,
                }
            )

    if over_duration:
        task_ids = [e.get("task_id") for e in over_duration]
        return PredicateResult(
            passed=False,
            failure_category=CROSS_ARTIFACT_INCONSISTENCY,
            reason=(
                f"{len(over_duration)} task(s) have end_month exceeding "
                f"project_duration_months ({duration_raw}): {task_ids}.  "
                "Adjust the Gantt schedule or the call duration binding."
            ),
            details={
                "gantt_path": str(gantt_resolved),
                "call_path": str(call_resolved),
                "project_duration_months": duration_raw,
                "over_duration_tasks": over_duration,
                "over_duration_count": len(over_duration),
            },
        )

    return PredicateResult(
        passed=True,
        details={
            "gantt_path": str(gantt_resolved),
            "call_path": str(call_resolved),
            "project_duration_months": duration_raw,
            "task_count": len(tasks_raw),
        },
    )


def all_milestones_have_criteria(
    gantt_path: PathLike,
    *,
    repo_root: Optional[str] = None,
) -> PredicateResult:
    """
    Verify that every milestone in ``gantt.json`` has a non-empty
    ``verifiable_criterion`` and a non-null ``due_month``.

    Parameters
    ----------
    gantt_path:
        Path to the canonical Phase 4 artifact ``gantt.json``.
    repo_root:
        Optional repository root for path resolution.

    Returns
    -------
    PredicateResult
        Passes when all milestones are complete.
        Fails with:
        - MISSING_MANDATORY_INPUT if the file is absent.
        - MALFORMED_ARTIFACT if the file cannot be parsed or ``milestones``
          is absent or not a list.
        - CROSS_ARTIFACT_INCONSISTENCY if any milestone is missing its
          criterion or due month (these are planning incompleteness failures,
          not structural parse failures).

    Non-empty criterion definition
    --------------------------------
    ``verifiable_criterion`` is considered non-empty when it is a string that
    contains at least one non-whitespace character.  Null and blank/whitespace-
    only strings both fail.
    """
    resolved = resolve_repo_path(gantt_path, repo_root)

    gantt, err = _read_json_object(resolved)
    if err:
        return err

    milestones_raw = gantt.get("milestones")
    if milestones_raw is None:
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=(
                "gantt.json is missing required field 'milestones' "
                "(artifact_schema_specification.yaml §1.4)"
            ),
            details={"path": str(resolved)},
        )
    if not isinstance(milestones_raw, list):
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=(
                f"gantt.json 'milestones' must be an array; "
                f"got {type(milestones_raw).__name__}"
            ),
            details={"path": str(resolved), "actual_type": type(milestones_raw).__name__},
        )

    incomplete: list[dict] = []
    for i, ms in enumerate(milestones_raw):
        if not isinstance(ms, dict):
            return PredicateResult(
                passed=False,
                failure_category=MALFORMED_ARTIFACT,
                reason=(
                    f"gantt.json milestones[{i}] must be a dict; "
                    f"got {type(ms).__name__}"
                ),
                details={"path": str(resolved), "bad_milestone_index": i},
            )
        ms_id = ms.get("milestone_id", f"<index {i}>")

        # Check verifiable_criterion
        criterion = ms.get("verifiable_criterion")
        criterion_ok = isinstance(criterion, str) and criterion.strip() != ""
        if criterion is None or not criterion_ok:
            incomplete.append(
                {
                    "milestone_id": ms_id,
                    "problem": "verifiable_criterion is null or blank",
                    "value": criterion,
                }
            )
            continue  # don't double-count; move to next milestone

        # Check due_month
        due = ms.get("due_month")
        if due is None:
            incomplete.append(
                {"milestone_id": ms_id, "problem": "due_month is null or absent"}
            )

    if incomplete:
        ids = [e.get("milestone_id") for e in incomplete]
        return PredicateResult(
            passed=False,
            failure_category=CROSS_ARTIFACT_INCONSISTENCY,
            reason=(
                f"{len(incomplete)} milestone(s) are missing verifiable_criterion "
                f"or due_month: {ids}.  Every milestone must have a concrete, "
                "externally-verifiable achievement criterion and a scheduled month."
            ),
            details={
                "path": str(resolved),
                "incomplete_milestones": incomplete,
                "incomplete_count": len(incomplete),
            },
        )

    return PredicateResult(
        passed=True,
        details={"path": str(resolved), "milestone_count": len(milestones_raw)},
    )


def wp_count_within_limit(
    wp_path: PathLike,
    schema_path: PathLike,
    *,
    repo_root: Optional[str] = None,
) -> PredicateResult:
    """
    Verify that the number of work packages in Phase 3 does not exceed the
    maximum defined in the section schema registry.

    Parameters
    ----------
    wp_path:
        Path to the canonical Phase 3 artifact ``wp_structure.json``.
    schema_path:
        Path to ``docs/tier2a_instrument_schemas/extracted/section_schema_registry.json``.
    repo_root:
        Optional repository root for path resolution.

    Returns
    -------
    PredicateResult
        Passes when WP count ≤ max_work_packages.
        Fails with:
        - MISSING_MANDATORY_INPUT if either file is absent.
        - MALFORMED_ARTIFACT if either file cannot be parsed, ``work_packages``
          is not a list, or no ``max_work_packages`` constraint is found in the
          registry.
        - POLICY_VIOLATION if the WP count exceeds the instrument limit.
          Rationale: the artifact is structurally valid but violates an
          instrument-level structural rule from Tier 2A.  This is a policy
          constraint, not a cross-artifact data inconsistency.

    Registry format and instrument selection
    -----------------------------------------
    See module docstring.  Both Form A (object with instrument-type keys) and
    Form B (object with ``instruments`` array) are supported.  When the registry
    contains multiple instrument entries, the **minimum** max_work_packages
    found is used as the binding constraint (most conservative interpretation).
    This ensures the predicate never produces a false pass when the active
    instrument cannot be determined from the available inputs alone.
    """
    wp_resolved = resolve_repo_path(wp_path, repo_root)
    schema_resolved = resolve_repo_path(schema_path, repo_root)

    wp_data, err = _read_json_object(wp_resolved)
    if err:
        return err

    schema_data, err = _read_json_object(schema_resolved)
    if err:
        return err

    # --- Count work packages ---
    wps_raw = wp_data.get("work_packages")
    if wps_raw is None or not isinstance(wps_raw, list):
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=(
                "wp_structure.json is missing required field 'work_packages' "
                "or it is not an array (artifact_schema_specification.yaml §1.3)"
            ),
            details={"path": str(wp_resolved)},
        )
    wp_count = len(wps_raw)

    # --- Extract max_work_packages from registry ---
    max_values = _extract_max_wp_values(schema_data)
    if not max_values:
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=(
                "section_schema_registry.json contains no 'max_work_packages' "
                "constraint in any instrument entry.  The registry must define "
                "this limit for wp_count_within_limit to evaluate."
            ),
            details={"path": str(schema_resolved)},
        )

    max_wps = min(max_values)  # most conservative: minimum across all instruments

    if wp_count > max_wps:
        return PredicateResult(
            passed=False,
            failure_category=POLICY_VIOLATION,
            reason=(
                f"WP count ({wp_count}) exceeds the maximum allowed by the "
                f"section schema registry ({max_wps}).  Reduce the number of "
                "work packages to comply with the instrument's structural limit."
            ),
            details={
                "wp_path": str(wp_resolved),
                "schema_path": str(schema_resolved),
                "wp_count": wp_count,
                "max_work_packages": max_wps,
                "all_registry_limits": max_values,
            },
        )

    return PredicateResult(
        passed=True,
        details={
            "wp_path": str(wp_resolved),
            "schema_path": str(schema_resolved),
            "wp_count": wp_count,
            "max_work_packages": max_wps,
        },
    )


def critical_path_present(
    gantt_path: PathLike,
    *,
    repo_root: Optional[str] = None,
) -> PredicateResult:
    """
    Verify that ``gantt.json`` contains a non-empty ``critical_path`` field.

    This is a presence / completeness check only.  The predicate does not
    recompute or validate the mathematical correctness of the critical path.

    Parameters
    ----------
    gantt_path:
        Path to the canonical Phase 4 artifact ``gantt.json``.
    repo_root:
        Optional repository root for path resolution.

    Returns
    -------
    PredicateResult
        Passes when ``critical_path`` is non-empty.
        Fails with:
        - MISSING_MANDATORY_INPUT if the file is absent.
        - MALFORMED_ARTIFACT if the file cannot be parsed.
        - CROSS_ARTIFACT_INCONSISTENCY if ``critical_path`` is absent or empty.
          Rationale: the Gantt output is planning-incomplete relative to the
          required structure; this constitutes an inconsistency between the
          declared plan (which implies a schedulable structure) and the absence
          of critical-path information.

    Non-empty definition
    ---------------------
    The canonical form of ``critical_path`` is an array of strings
    (artifact_schema_specification.yaml §1.4).  The following are all considered
    empty and will fail:

    - ``null``
    - ``""`` (empty string)
    - ``[]`` (empty list)
    - ``{}`` (empty dict)

    Non-null strings, non-empty lists, and non-empty dicts all pass.
    """
    resolved = resolve_repo_path(gantt_path, repo_root)

    gantt, err = _read_json_object(resolved)
    if err:
        return err

    if "critical_path" not in gantt:
        return PredicateResult(
            passed=False,
            failure_category=CROSS_ARTIFACT_INCONSISTENCY,
            reason=(
                "gantt.json is missing the required 'critical_path' field.  "
                "The Gantt output must include a non-empty critical path for "
                "the phase gate to pass (artifact_schema_specification.yaml §1.4)."
            ),
            details={"path": str(resolved)},
        )

    cp = gantt["critical_path"]

    # Null
    if cp is None:
        return PredicateResult(
            passed=False,
            failure_category=CROSS_ARTIFACT_INCONSISTENCY,
            reason="gantt.json 'critical_path' is null; it must be a non-empty value.",
            details={"path": str(resolved), "critical_path_value": None},
        )

    # Empty string
    if isinstance(cp, str) and cp.strip() == "":
        return PredicateResult(
            passed=False,
            failure_category=CROSS_ARTIFACT_INCONSISTENCY,
            reason=(
                "gantt.json 'critical_path' is an empty string; "
                "it must be a non-empty value."
            ),
            details={"path": str(resolved), "critical_path_value": cp},
        )

    # Empty list
    if isinstance(cp, list) and len(cp) == 0:
        return PredicateResult(
            passed=False,
            failure_category=CROSS_ARTIFACT_INCONSISTENCY,
            reason=(
                "gantt.json 'critical_path' is an empty list; "
                "it must contain at least one entry."
            ),
            details={"path": str(resolved), "critical_path_value": []},
        )

    # Empty dict
    if isinstance(cp, dict) and len(cp) == 0:
        return PredicateResult(
            passed=False,
            failure_category=CROSS_ARTIFACT_INCONSISTENCY,
            reason=(
                "gantt.json 'critical_path' is an empty object; "
                "it must contain at least one entry."
            ),
            details={"path": str(resolved), "critical_path_value": {}},
        )

    # Non-empty: pass
    cp_len: Optional[int] = None
    if isinstance(cp, (list, dict)):
        cp_len = len(cp)

    return PredicateResult(
        passed=True,
        details={
            "path": str(resolved),
            "critical_path_type": type(cp).__name__,
            **({"critical_path_length": cp_len} if cp_len is not None else {}),
        },
    )
