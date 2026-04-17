"""
Agent runtime — orchestration adapter layer.

Loads an agent definition and prompt specification, resolves canonical
inputs, sequences skill invocations through :func:`runner.skill_runtime.run_skill`,
manages context passing and failure handling, determines
``can_evaluate_exit_gate`` from actual disk state, and returns an
:class:`AgentResult`.

Agent ``.md`` files and prompt specs are **specifications, not executable
code**.  Domain reasoning is performed by Claude through ``run_skill()``
calls; this module handles spec loading, input resolution, skill
sequencing, context passing, failure propagation, and gate-readiness
determination.

Authoritative sources:
    runtime_integration_plan.md §6, §7, §8, §10.2, §10.3, §10.4, §11
    runtime_integration_execution_plan.md Step 5
    node_body_contract.md §1–§10
    agent_catalog.yaml (reads_from, writes_to, must_not per agent)

Constitutional authority:
    Subordinate to CLAUDE.md.  This module does not invoke the scheduler,
    does not evaluate gates, and does not compute budget figures.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

import yaml

from runner.node_resolver import NodeResolver, NodeResolverError
from runner.runtime_models import AgentResult, SkillInvocationRecord
from runner.skill_runtime import run_skill

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Repo-relative path to the agent catalog.
AGENT_CATALOG_REL_PATH: str = (
    ".claude/workflows/system_orchestration/agent_catalog.yaml"
)

#: Repo-relative path to the compiled manifest.
MANIFEST_REL_PATH: str = (
    ".claude/workflows/system_orchestration/manifest.compile.yaml"
)

#: Skills whose primary audit target is Tier 5 deliverable artifacts.
#: When invoked in a phase where Tier 5 does not yet exist (e.g. Phase 2),
#: these skills are skipped as "not_applicable" rather than failed with
#: MISSING_INPUT.  In phases where Tier 5 is expected (Phase 8), they
#: execute normally and fail-closed on missing inputs.
_TIER5_AUDIT_SKILLS: frozenset[str] = frozenset({
    "proposal-section-traceability-check",
})

#: Tier 5 deliverable directories that must contain at least one JSON
#: file for a Tier 5 audit skill to be considered applicable.
_TIER5_DELIVERABLE_DIRS: tuple[str, ...] = (
    "docs/tier5_deliverables/proposal_sections",
    "docs/tier5_deliverables/assembled_drafts",
)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class AgentRuntimeError(Exception):
    """Raised for infrastructure failures outside the normal failure protocol.

    Logical failures (missing inputs, skill failures, constitutional halts)
    are returned as ``AgentResult`` with the appropriate fields.
    ``AgentRuntimeError`` is reserved for truly unexpected errors such as
    the agent catalog being unreadable.
    """


# ---------------------------------------------------------------------------
# Agent catalog loader (cached per repo_root)
# ---------------------------------------------------------------------------

_agent_catalog_cache: dict[str, list[dict]] = {}


def _load_agent_catalog(repo_root: Path) -> list[dict]:
    """Load and cache ``agent_catalog.yaml``."""
    key = str(repo_root)
    if key in _agent_catalog_cache:
        return _agent_catalog_cache[key]

    catalog_path = repo_root / AGENT_CATALOG_REL_PATH
    if not catalog_path.exists():
        raise AgentRuntimeError(
            f"Agent catalog not found: {catalog_path}"
        )
    try:
        raw = catalog_path.read_text(encoding="utf-8-sig")
        data = yaml.safe_load(raw)
    except (OSError, yaml.YAMLError) as exc:
        raise AgentRuntimeError(
            f"Cannot load agent catalog {catalog_path}: {exc}"
        ) from exc

    entries = data.get("agent_catalog", [])
    if not isinstance(entries, list):
        raise AgentRuntimeError("agent_catalog is not a list")

    _agent_catalog_cache[key] = entries
    return entries


def _get_agent_entry(agent_id: str, repo_root: Path) -> dict:
    """Return the catalog entry for *agent_id*."""
    for entry in _load_agent_catalog(repo_root):
        if entry.get("id") == agent_id:
            return entry
    raise AgentRuntimeError(
        f"Agent {agent_id!r} not found in agent_catalog.yaml"
    )


# ---------------------------------------------------------------------------
# Manifest artifact registry loader (cached per repo_root)
# ---------------------------------------------------------------------------

_artifact_registry_cache: dict[str, list[dict]] = {}


def _load_artifact_registry(
    repo_root: Path,
    manifest_path: Optional[Path] = None,
) -> list[dict]:
    """Load and cache the artifact_registry from manifest.compile.yaml.

    Parameters
    ----------
    repo_root:
        Repository root.
    manifest_path:
        Explicit path to the compiled manifest.  When provided, this
        takes precedence over the module-level ``MANIFEST_REL_PATH``
        constant.  When ``None``, the default constant is used.

    The cache is keyed by the **resolved** manifest path so that
    different manifests (e.g. production vs. test fixture) used with
    the same ``repo_root`` are cached independently.
    """
    resolved_path = (
        manifest_path if manifest_path is not None
        else repo_root / MANIFEST_REL_PATH
    )
    key = str(resolved_path)
    if key in _artifact_registry_cache:
        return _artifact_registry_cache[key]

    if not resolved_path.exists():
        raise AgentRuntimeError(
            f"Manifest not found: {resolved_path}"
        )
    try:
        raw = resolved_path.read_text(encoding="utf-8-sig")
        data = yaml.safe_load(raw)
    except (OSError, yaml.YAMLError) as exc:
        raise AgentRuntimeError(
            f"Cannot load manifest {resolved_path}: {exc}"
        ) from exc

    registry = data.get("artifact_registry", [])
    if not isinstance(registry, list):
        raise AgentRuntimeError("artifact_registry is not a list")

    _artifact_registry_cache[key] = registry
    return registry


# ---------------------------------------------------------------------------
# Phase A — Spec loading
# ---------------------------------------------------------------------------


def _load_agent_spec(agent_id: str, repo_root: Path) -> str:
    """Load the agent definition Markdown content."""
    path = repo_root / ".claude" / "agents" / f"{agent_id}.md"
    if not path.exists():
        raise AgentRuntimeError(
            f"Agent definition not found: {path}"
        )
    return path.read_text(encoding="utf-8-sig")


def _load_prompt_spec(agent_id: str, repo_root: Path) -> str:
    """Load the agent prompt specification Markdown content."""
    path = (
        repo_root / ".claude" / "agents" / "prompts"
        / f"{agent_id}_prompt_spec.md"
    )
    if not path.exists():
        raise AgentRuntimeError(
            f"Agent prompt spec not found: {path}"
        )
    return path.read_text(encoding="utf-8-sig")


# ---------------------------------------------------------------------------
# Phase B — Canonical input resolution
# ---------------------------------------------------------------------------


def _resolve_agent_inputs(
    reads_from: list[str],
    repo_root: Path,
) -> tuple[dict[str, Any], list[str]]:
    """Resolve canonical inputs from the agent's reads_from paths.

    Returns ``(resolved_inputs, validation_errors)``.
    *resolved_inputs* maps repo-relative paths to parsed content.
    *validation_errors* is empty when all required inputs are valid.
    """
    resolved: dict[str, Any] = {}
    errors: list[str] = []

    for rel_path in reads_from:
        abs_path = repo_root / rel_path
        if abs_path.is_dir():
            if not abs_path.exists():
                errors.append(
                    f"Required input directory missing: {rel_path}"
                )
                continue
            # Collect JSON files from directories
            children = sorted(
                c for c in abs_path.iterdir()
                if c.suffix == ".json" and c.is_file()
            )
            if not children:
                # Directories may be legitimately empty for some agents
                # (e.g. source directories before Phase 1 runs).
                # Record as present-but-empty; not a hard error at agent
                # level — individual skills validate their own inputs.
                pass
            for child in children:
                child_rel = str(child.relative_to(repo_root)).replace(
                    "\\", "/"
                )
                try:
                    resolved[child_rel] = json.loads(
                        child.read_text(encoding="utf-8-sig")
                    )
                except (json.JSONDecodeError, OSError):
                    resolved[child_rel] = None
        elif abs_path.is_file():
            try:
                resolved[rel_path] = json.loads(
                    abs_path.read_text(encoding="utf-8-sig")
                )
            except json.JSONDecodeError:
                # Non-JSON file — store raw text
                resolved[rel_path] = abs_path.read_text(encoding="utf-8-sig")
            except OSError:
                errors.append(f"Cannot read required input: {rel_path}")
        else:
            # File doesn't exist — not necessarily fatal at agent level.
            # Skills validate their own required inputs and return
            # MISSING_INPUT if needed.  The agent only hard-fails here
            # for file-path inputs (not directory-path inputs, which may
            # be populated by earlier skills in the same agent execution).
            if not rel_path.endswith("/"):
                errors.append(f"Required input file missing: {rel_path}")

    return resolved, errors


# ---------------------------------------------------------------------------
# Phase D helpers — Skill sequencing
# ---------------------------------------------------------------------------


def _resolve_skill_sequence(
    agent_id: str,
    skill_ids: list[str],
    prompt_spec: str,
) -> list[str]:
    """Derive the skill invocation order from the prompt spec.

    The manifest skill list (*skill_ids*) is the **authoritative set** of
    skills the agent must invoke.  The prompt spec determines the
    **ordering** within that set.  If the prompt spec mentions skills in a
    particular order, that order is used.  Skills in the manifest set but
    not mentioned in ordering context are appended at the end in manifest
    order.

    This implementation uses a simple heuristic: scan the prompt spec for
    skill-id mentions in document order.  Skill IDs use the format
    ``word-word-word`` (hyphenated lowercase), so substring false positives
    from natural language are avoided for production skill IDs.  This is
    sufficient because prompt specs list skills in their intended execution
    sequence.

    Returns *skill_ids* reordered per the prompt spec, constrained to the
    manifest-declared set.
    """
    if not skill_ids:
        return []

    # Find the position of each skill_id's first mention in the prompt spec.
    # Skill IDs contain hyphens (e.g. "work-package-normalization"), which
    # makes them distinct from natural language words.  A simple str.find()
    # is reliable for production IDs.  For single-character or very short
    # test IDs, use re.search with word boundaries to avoid false matches.
    import re as _re

    ordered: list[tuple[int, str]] = []
    unmentioned: list[str] = []

    for sid in skill_ids:
        if len(sid) <= 3:
            # Short IDs: use word-boundary matching to avoid substring hits
            match = _re.search(r"\b" + _re.escape(sid) + r"\b", prompt_spec)
            pos = match.start() if match else -1
        else:
            pos = prompt_spec.find(sid)
        if pos >= 0:
            ordered.append((pos, sid))
        else:
            unmentioned.append(sid)

    # Sort mentioned skills by position in the prompt spec
    ordered.sort(key=lambda t: t[0])

    # Combine: mentioned-in-order first, then unmentioned in manifest order
    return [sid for _, sid in ordered] + unmentioned


# ---------------------------------------------------------------------------
# Phase E — Gate-readiness determination
# ---------------------------------------------------------------------------


def _get_artifacts_produced_by_node(
    node_id: str,
    repo_root: Path,
    manifest_path: Optional[Path] = None,
) -> list[str]:
    """Return repo-relative artifact paths that *node_id* produces.

    Reads from the manifest artifact_registry's ``produced_by`` field.
    Returns only artifacts with a ``gate_dependency`` or those in Tier 4/5
    (the artifacts that exit-gate predicates evaluate).
    """
    registry = _load_artifact_registry(repo_root, manifest_path=manifest_path)
    paths: list[str] = []
    for entry in registry:
        if not isinstance(entry, dict):
            continue
        produced_by = entry.get("produced_by")
        # produced_by can be a string or a list
        if isinstance(produced_by, str):
            if produced_by != node_id:
                continue
        elif isinstance(produced_by, list):
            if node_id not in produced_by:
                continue
        else:
            continue

        path = entry.get("path", "")
        tier = entry.get("tier", "")

        # Only check artifacts relevant to gate evaluation:
        # - tier4_phase_output artifacts (these have gate_dependency)
        # - tier5_deliverable artifacts
        # - checkpoint artifacts
        # - integration_validation artifacts
        # Skip tier3_updated, tier2b_extracted, tier2a_extracted (these
        # are produced as side effects; gate predicates evaluate the
        # primary phase output, not every extracted file individually).
        if tier in (
            "tier4_phase_output",
            "tier5_deliverable",
            "checkpoint",
            "integration_validation",
        ) or entry.get("gate_dependency"):
            paths.append(path)

    return paths


def _determine_can_evaluate_exit_gate(
    node_id: str,
    repo_root: Path,
    manifest_path: Optional[Path] = None,
) -> bool:
    """Check whether all gate-relevant artifacts for *node_id* exist on disk.

    Inspects actual file-system state — not optimistic assumptions.
    Returns ``True`` only when every artifact path produced by *node_id*
    (that is relevant to gate evaluation) exists and is non-empty.

    For directory paths: the directory must exist and contain at least one
    ``.json`` file.
    For file paths: the file must exist and parse as non-empty JSON.

    .. note::

       This is a **conservative artifact-registry approximation** of
       exit-gate readiness.  It checks that the artifacts the manifest
       declares as produced by *node_id* are present and non-empty on
       disk, but it does **not** evaluate the actual exit-gate predicate
       expressions (which may impose additional semantic constraints such
       as field-level completeness or cross-artifact consistency).

       A ``True`` return means "the gate evaluator has enough material
       on disk to attempt evaluation."  It does **not** mean "the gate
       will pass."  The scheduler's gate evaluator makes the
       authoritative pass/fail determination.
    """
    required_paths = _get_artifacts_produced_by_node(
        node_id, repo_root, manifest_path=manifest_path
    )

    if not required_paths:
        # Node produces no gate-relevant artifacts — this shouldn't
        # happen for production nodes, but defensively return False.
        logger.warning(
            "Node %s has no gate-relevant artifacts in artifact_registry; "
            "returning can_evaluate_exit_gate=False",
            node_id,
        )
        return False

    for rel_path in required_paths:
        abs_path = repo_root / rel_path
        if rel_path.endswith("/") or abs_path.is_dir():
            # Directory artifact — must exist with at least one .json file
            if not abs_path.is_dir():
                logger.debug(
                    "Gate-relevant directory missing: %s", rel_path
                )
                return False
            json_files = [
                f for f in abs_path.iterdir()
                if f.suffix == ".json" and f.is_file()
            ]
            if not json_files:
                logger.debug(
                    "Gate-relevant directory empty: %s", rel_path
                )
                return False
        else:
            # File artifact — must exist and be non-empty JSON
            if not abs_path.is_file():
                logger.debug(
                    "Gate-relevant artifact missing: %s", rel_path
                )
                return False
            try:
                content = abs_path.read_text(encoding="utf-8-sig")
                data = json.loads(content)
                if not data:
                    logger.debug(
                        "Gate-relevant artifact is empty: %s", rel_path
                    )
                    return False
            except (json.JSONDecodeError, OSError):
                logger.debug(
                    "Gate-relevant artifact unreadable/invalid JSON: %s",
                    rel_path,
                )
                return False

    return True


# ---------------------------------------------------------------------------
# Caller context for context-sensitive skills
# ---------------------------------------------------------------------------

#: Skills that require the invoking agent to supply content context, mapped
#: to the Tier 3 source paths that provide that context.  When these skills
#: are invoked, the agent runtime reads the listed paths and passes them as
#: ``caller_context`` to ``run_skill()``.
#:
#: This is the authoritative registry of skill→context-source bindings.
#: Each entry's source paths must fall within the invoking agent's
#: ``reads_from`` scope (agent_catalog.yaml).
_SKILL_CONTEXT_SOURCES: dict[str, tuple[str, ...]] = {
    "topic-scope-check": (
        "docs/tier3_project_instantiation/project_brief/concept_note.md",
        "docs/tier3_project_instantiation/project_brief/strategic_positioning.md",
        "docs/tier3_project_instantiation/project_brief/project_summary.json",
    ),
}


def _build_caller_context(
    skill_id: str,
    resolved_inputs: dict[str, Any],
    repo_root: Path,
) -> dict[str, Any]:
    """Build caller-supplied content context for context-sensitive skills.

    Returns a dict mapping source paths to their content.  Empty dict when
    no context sources are configured or no sources are available for
    *skill_id*.

    Content is taken from *resolved_inputs* first (for JSON files already
    loaded by ``_resolve_agent_inputs``), then read from disk (for non-JSON
    files such as ``.md`` that ``_resolve_agent_inputs`` does not collect).

    **Fail-closed:** returns empty dict when sources are absent.  The
    skill's own input validation (e.g. Step 1.4 of ``topic-scope-check``)
    will produce the appropriate ``MISSING_INPUT`` failure.
    """
    source_paths = _SKILL_CONTEXT_SOURCES.get(skill_id)
    if source_paths is None:
        return {}

    context: dict[str, Any] = {}
    for rel_path in source_paths:
        # Check resolved_inputs first (JSON files already loaded by agent)
        if rel_path in resolved_inputs and resolved_inputs[rel_path] is not None:
            context[rel_path] = resolved_inputs[rel_path]
            continue
        # Read from disk for files not in resolved_inputs (.md files)
        abs_path = repo_root / rel_path
        if abs_path.is_file():
            try:
                raw = abs_path.read_text(encoding="utf-8-sig")
                if rel_path.endswith(".json"):
                    try:
                        context[rel_path] = json.loads(raw)
                    except json.JSONDecodeError:
                        context[rel_path] = raw
                else:
                    context[rel_path] = raw
            except OSError:
                pass  # absent/unreadable — skip; fail-closed downstream

    return context


# ---------------------------------------------------------------------------
# Skill applicability guard
# ---------------------------------------------------------------------------


def _check_skill_applicability(
    skill_id: str,
    repo_root: Path,
) -> tuple[bool, str | None]:
    """Check whether *skill_id* is applicable in the current repo state.

    Returns ``(is_applicable, skip_reason)``.  When ``is_applicable`` is
    ``False``, *skip_reason* explains why the skill should be skipped.

    This is a **narrow** applicability guard for skills that audit Tier 5
    deliverable artifacts (e.g. ``proposal-section-traceability-check``).
    In phases before Tier 5 is populated (Phase 2), these skills are not
    applicable and must be skipped rather than failed with MISSING_INPUT.
    In phases where Tier 5 is expected (Phase 8), the guard passes and
    the skill runs normally — preserving fail-closed behavior.

    The check is based on actual disk state (whether Tier 5 directories
    contain any JSON files), not on phase number.  This ensures the guard
    is phase-sensitive without coupling to manifest constants.
    """
    if skill_id not in _TIER5_AUDIT_SKILLS:
        return True, None

    # Check if any Tier 5 deliverable directory has content
    for dir_path in _TIER5_DELIVERABLE_DIRS:
        abs_dir = repo_root / dir_path
        if abs_dir.is_dir():
            json_files = [
                f for f in abs_dir.iterdir()
                if f.suffix == ".json" and f.is_file()
            ]
            if json_files:
                return True, None  # Tier 5 has content — skill is applicable

    # No Tier 5 content exists — skill is not applicable yet
    return False, (
        f"Skill {skill_id!r} requires Tier 5 deliverable artifacts "
        f"(proposal_sections/ or assembled_drafts/) which do not yet exist; "
        f"skipping as not applicable in current phase"
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_agent(
    agent_id: str,
    node_id: str,
    run_id: str,
    repo_root: Path,
    *,
    manifest_path: Path,
    skill_ids: list[str],
    phase_id: str,
    sub_agent_id: Optional[str] = None,
    pre_gate_agent_id: Optional[str] = None,
) -> AgentResult:
    """Execute an agent's body for a node and return an AgentResult.

    This is an **orchestration adapter**, not a domain reasoner.  It loads
    agent and prompt specifications, sequences skill invocations through
    :func:`runner.skill_runtime.run_skill` (a Claude runtime transport
    adapter), manages context passing between invocations, handles failure
    propagation, and determines ``can_evaluate_exit_gate`` from actual disk
    state.

    Parameters
    ----------
    agent_id:
        Agent identifier matching ``agent_catalog.yaml``.
    node_id:
        Canonical manifest node ID (e.g. ``"n01_call_analysis"``).
    run_id:
        Current run UUID, propagated to every skill invocation.
    repo_root:
        Absolute path to the repository root.
    manifest_path:
        Path to ``manifest.compile.yaml``.
    skill_ids:
        Manifest-declared skill list for this node (authoritative set).
    phase_id:
        Phase identifier from the manifest node registry.
    sub_agent_id:
        Sub-agent for this node (e.g. ``"dependency_mapper"`` for n03),
        or ``None``.
    pre_gate_agent_id:
        Pre-gate agent for this node (e.g.
        ``"budget_interface_coordinator"`` for n07), or ``None``.

    Returns
    -------
    AgentResult
        Always returned — never raises for logical failures.  Only
        :class:`AgentRuntimeError` is raised for infrastructure failures.
        ``failure_origin`` is always ``"agent_body"``.
    """

    all_invocations: list[SkillInvocationRecord] = []
    all_outputs: list[str] = []
    all_validation_reports: list[str] = []
    all_decision_log_writes: list[str] = []

    # ── Phase A: Spec loading ──────────────────────────────────────────

    try:
        _agent_spec = _load_agent_spec(agent_id, repo_root)
    except AgentRuntimeError as exc:
        return AgentResult(
            status="failure",
            can_evaluate_exit_gate=False,
            failure_reason=f"Agent spec loading failed: {exc}",
            failure_category="MISSING_INPUT",
        )

    try:
        prompt_spec = _load_prompt_spec(agent_id, repo_root)
    except AgentRuntimeError as exc:
        return AgentResult(
            status="failure",
            can_evaluate_exit_gate=False,
            failure_reason=f"Prompt spec loading failed: {exc}",
            failure_category="MISSING_INPUT",
        )

    # Load agent catalog entry for reads_from
    try:
        agent_entry = _get_agent_entry(agent_id, repo_root)
    except AgentRuntimeError as exc:
        return AgentResult(
            status="failure",
            can_evaluate_exit_gate=False,
            failure_reason=f"Agent catalog lookup failed: {exc}",
            failure_category="MISSING_INPUT",
        )

    reads_from: list[str] = agent_entry.get("reads_from", [])

    # ── Phase B: Canonical input resolution ────────────────────────────

    resolved_inputs, input_errors = _resolve_agent_inputs(
        reads_from, repo_root
    )
    if input_errors:
        return AgentResult(
            status="failure",
            can_evaluate_exit_gate=False,
            failure_reason=(
                f"Agent {agent_id!r} input validation failed: "
                + "; ".join(input_errors)
            ),
            failure_category="MISSING_INPUT",
        )

    # ── Phase C: Pre-gate agent (n07 special case) ─────────────────────

    if pre_gate_agent_id is not None:
        # Resolve the pre-gate agent's skills from the manifest.
        # The manifest's skill list for this node includes both the
        # pre-gate agent's skills and the primary agent's skills.
        # We need to identify which skills belong to the pre-gate agent
        # by looking at skill_catalog used_by_agents.
        pre_gate_skills = _identify_agent_skills(
            pre_gate_agent_id, skill_ids, repo_root
        )
        primary_skills = [s for s in skill_ids if s not in pre_gate_skills]

        # Execute pre-gate agent's skills first
        for sid in pre_gate_skills:
            result = run_skill(sid, run_id, repo_root, resolved_inputs)
            record = SkillInvocationRecord(
                skill_id=sid,
                status=result.status,
                failure_reason=result.failure_reason,
                failure_category=result.failure_category,
                outputs_written=list(result.outputs_written),
            )
            all_invocations.append(record)

            if result.status == "success":
                all_outputs.extend(result.outputs_written)
                if result.validation_report:
                    all_validation_reports.append(result.validation_report)
                # Make pre-gate outputs available to subsequent skills
                _refresh_inputs_from_outputs(
                    resolved_inputs, result.outputs_written, repo_root
                )
            else:
                if result.failure_category == "CONSTITUTIONAL_HALT":
                    return AgentResult(
                        status="failure",
                        can_evaluate_exit_gate=False,
                        failure_reason=(
                            f"CONSTITUTIONAL_HALT from pre-gate skill "
                            f"{sid!r}: {result.failure_reason}"
                        ),
                        failure_category="CONSTITUTIONAL_HALT",
                        outputs_written=all_outputs,
                        validation_reports=all_validation_reports,
                        decision_log_writes=all_decision_log_writes,
                        invoked_skills=all_invocations,
                    )
                # Non-halt pre-gate failure: log and continue to primary
                # agent — it may still be able to produce required outputs
                # (e.g. the budget response may already exist externally).
                logger.warning(
                    "Pre-gate skill %s failed: %s; continuing to primary agent",
                    sid,
                    result.failure_reason,
                )
    else:
        primary_skills = list(skill_ids)

    # ── Phase D: Skill invocation sequencing ───────────────────────────

    # Determine execution order from the prompt spec
    ordered_skills = _resolve_skill_sequence(
        agent_id, primary_skills, prompt_spec
    )

    # For n03: identify sub-agent skills so they can be invoked at the
    # right point in the sequence.
    sub_agent_skills: list[str] = []
    if sub_agent_id is not None:
        sub_agent_skills = _identify_agent_skills(
            sub_agent_id, primary_skills, repo_root
        )
        # Remove sub-agent skills from ordered_skills — they'll be
        # invoked at the right point based on dependency.
        ordered_skills = [s for s in ordered_skills if s not in sub_agent_skills]

    had_failure = False
    failure_reason_accumulator: str | None = None
    failure_category_accumulator: str | None = None

    for sid in ordered_skills:
        # ── Applicability guard: skip Tier-5 audit skills pre-Tier-5 ──
        applicable, skip_reason = _check_skill_applicability(sid, repo_root)
        if not applicable:
            record = SkillInvocationRecord(
                skill_id=sid,
                status="not_applicable",
                failure_reason=skip_reason,
            )
            all_invocations.append(record)
            logger.info(
                "Skill %s skipped (not applicable): %s", sid, skip_reason
            )
            continue

        # Build caller context for context-sensitive skills (e.g.
        # topic-scope-check needs concept text from the invoking agent).
        caller_context = _build_caller_context(
            sid, resolved_inputs, repo_root
        )

        result = run_skill(
            sid, run_id, repo_root, resolved_inputs,
            caller_context=caller_context or None,
        )
        record = SkillInvocationRecord(
            skill_id=sid,
            status=result.status,
            failure_reason=result.failure_reason,
            failure_category=result.failure_category,
            outputs_written=list(result.outputs_written),
        )
        all_invocations.append(record)

        if result.status == "success":
            all_outputs.extend(result.outputs_written)
            if result.validation_report:
                all_validation_reports.append(result.validation_report)
            # Make this skill's outputs available to subsequent skills
            _refresh_inputs_from_outputs(
                resolved_inputs, result.outputs_written, repo_root
            )

            # n03 sub-agent injection point: after the primary agent's
            # structure-producing skills have run, invoke the sub-agent's
            # skills (e.g. wp-dependency-analysis after work-package-
            # normalization produces wp_structure.json).
            if sub_agent_id is not None and sub_agent_skills:
                # Check if we should inject sub-agent skills now.
                # Heuristic: invoke after the first skill that writes to
                # the same output directory as the sub-agent reads from.
                # For n03, this means after work-package-normalization
                # writes wp_structure.json.
                if _should_invoke_sub_agent(
                    sid, sub_agent_skills, repo_root
                ):
                    for sub_sid in sub_agent_skills:
                        sub_result = run_skill(
                            sub_sid, run_id, repo_root, resolved_inputs
                        )
                        sub_record = SkillInvocationRecord(
                            skill_id=sub_sid,
                            status=sub_result.status,
                            failure_reason=sub_result.failure_reason,
                            failure_category=sub_result.failure_category,
                            outputs_written=list(sub_result.outputs_written),
                        )
                        all_invocations.append(sub_record)

                        if sub_result.status == "success":
                            all_outputs.extend(sub_result.outputs_written)
                            if sub_result.validation_report:
                                all_validation_reports.append(
                                    sub_result.validation_report
                                )
                            _refresh_inputs_from_outputs(
                                resolved_inputs,
                                sub_result.outputs_written,
                                repo_root,
                            )
                        else:
                            if sub_result.failure_category == "CONSTITUTIONAL_HALT":
                                return AgentResult(
                                    status="failure",
                                    can_evaluate_exit_gate=False,
                                    failure_reason=(
                                        f"CONSTITUTIONAL_HALT from sub-agent "
                                        f"skill {sub_sid!r}: "
                                        f"{sub_result.failure_reason}"
                                    ),
                                    failure_category="CONSTITUTIONAL_HALT",
                                    outputs_written=all_outputs,
                                    validation_reports=all_validation_reports,
                                    decision_log_writes=all_decision_log_writes,
                                    invoked_skills=all_invocations,
                                )
                            had_failure = True
                            failure_reason_accumulator = (
                                f"Sub-agent skill {sub_sid!r} failed: "
                                f"{sub_result.failure_reason}"
                            )
                            failure_category_accumulator = "SKILL_FAILURE"

                    # Mark sub-agent skills as consumed
                    sub_agent_skills = []

        else:
            # Skill failure
            if result.failure_category == "CONSTITUTIONAL_HALT":
                # Immediate halt — do not invoke remaining skills
                return AgentResult(
                    status="failure",
                    can_evaluate_exit_gate=False,
                    failure_reason=(
                        f"CONSTITUTIONAL_HALT from skill {sid!r}: "
                        f"{result.failure_reason}"
                    ),
                    failure_category="CONSTITUTIONAL_HALT",
                    outputs_written=all_outputs,
                    validation_reports=all_validation_reports,
                    decision_log_writes=all_decision_log_writes,
                    invoked_skills=all_invocations,
                )

            # Non-halt failure: record and continue.
            # The agent continues invoking remaining skills because:
            # - later skills may still produce their required outputs
            #   from other inputs
            # - can_evaluate_exit_gate is determined from disk state
            #   at the end, not from individual skill success
            had_failure = True
            failure_reason_accumulator = (
                f"Skill {sid!r} failed: {result.failure_reason}"
            )
            failure_category_accumulator = "SKILL_FAILURE"

    # Invoke any remaining sub-agent skills that weren't triggered by
    # the injection heuristic (defensive: ensures they always run).
    if sub_agent_id is not None and sub_agent_skills:
        for sub_sid in sub_agent_skills:
            sub_result = run_skill(
                sub_sid, run_id, repo_root, resolved_inputs
            )
            sub_record = SkillInvocationRecord(
                skill_id=sub_sid,
                status=sub_result.status,
                failure_reason=sub_result.failure_reason,
                failure_category=sub_result.failure_category,
                outputs_written=list(sub_result.outputs_written),
            )
            all_invocations.append(sub_record)

            if sub_result.status == "success":
                all_outputs.extend(sub_result.outputs_written)
                if sub_result.validation_report:
                    all_validation_reports.append(sub_result.validation_report)
                _refresh_inputs_from_outputs(
                    resolved_inputs, sub_result.outputs_written, repo_root
                )
            else:
                if sub_result.failure_category == "CONSTITUTIONAL_HALT":
                    return AgentResult(
                        status="failure",
                        can_evaluate_exit_gate=False,
                        failure_reason=(
                            f"CONSTITUTIONAL_HALT from sub-agent skill "
                            f"{sub_sid!r}: {sub_result.failure_reason}"
                        ),
                        failure_category="CONSTITUTIONAL_HALT",
                        outputs_written=all_outputs,
                        validation_reports=all_validation_reports,
                        decision_log_writes=all_decision_log_writes,
                        invoked_skills=all_invocations,
                    )
                had_failure = True
                failure_reason_accumulator = (
                    f"Sub-agent skill {sub_sid!r} failed: "
                    f"{sub_result.failure_reason}"
                )
                failure_category_accumulator = "SKILL_FAILURE"

    # ── Phase E: Gate-readiness determination ──────────────────────────

    can_evaluate = _determine_can_evaluate_exit_gate(
        node_id, repo_root, manifest_path=manifest_path
    )

    # ── Phase F: Return ────────────────────────────────────────────────
    #
    # Two independent dimensions:
    #   status            — did all skills succeed?
    #   can_evaluate_exit_gate — are gate-relevant artifacts on disk?
    #
    # These are independent signals.  A failure with can_evaluate=True
    # means "some skills failed but enough material landed on disk for
    # the gate evaluator to attempt evaluation."  The failure is still
    # reported; it is the scheduler's responsibility to decide whether
    # to proceed to gate evaluation when status="failure".

    if had_failure:
        return AgentResult(
            status="failure",
            can_evaluate_exit_gate=can_evaluate,
            failure_reason=failure_reason_accumulator,
            failure_category=failure_category_accumulator,
            outputs_written=all_outputs,
            validation_reports=all_validation_reports,
            decision_log_writes=all_decision_log_writes,
            invoked_skills=all_invocations,
        )

    if not can_evaluate:
        # All skills succeeded but gate-relevant artifacts are missing.
        # This indicates a skill produced outputs to unexpected paths
        # or the artifact_registry is misconfigured.
        return AgentResult(
            status="failure",
            can_evaluate_exit_gate=False,
            failure_reason=(
                f"Agent {agent_id!r}: all skills succeeded but gate-"
                f"relevant artifacts are missing from disk for node "
                f"{node_id!r}"
            ),
            failure_category="INCOMPLETE_OUTPUT",
            outputs_written=all_outputs,
            validation_reports=all_validation_reports,
            decision_log_writes=all_decision_log_writes,
            invoked_skills=all_invocations,
        )

    # Happy path: all skills succeeded and gate artifacts are on disk.
    return AgentResult(
        status="success",
        can_evaluate_exit_gate=True,
        outputs_written=all_outputs,
        validation_reports=all_validation_reports,
        decision_log_writes=all_decision_log_writes,
        invoked_skills=all_invocations,
    )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _identify_agent_skills(
    agent_id: str,
    node_skill_ids: list[str],
    repo_root: Path,
) -> list[str]:
    """Identify which skills from *node_skill_ids* belong to *agent_id*.

    Looks up the skill catalog's ``used_by_agents`` field for each skill
    and returns those that list *agent_id*.
    """
    from runner.skill_runtime import _load_skill_catalog

    catalog = _load_skill_catalog(repo_root)
    agent_skills: list[str] = []
    for sid in node_skill_ids:
        for entry in catalog:
            if entry.get("id") == sid:
                used_by = entry.get("used_by_agents", [])
                if agent_id in used_by:
                    agent_skills.append(sid)
                break
    return agent_skills


def _refresh_inputs_from_outputs(
    resolved_inputs: dict[str, Any],
    outputs_written: list[str],
    repo_root: Path,
) -> None:
    """Add newly written artifacts to the resolved inputs dict.

    This enables context passing: a skill's output artifact becomes
    available as input to the next skill in the sequence.
    """
    for rel_path in outputs_written:
        abs_path = repo_root / rel_path
        if abs_path.is_file():
            try:
                resolved_inputs[rel_path] = json.loads(
                    abs_path.read_text(encoding="utf-8-sig")
                )
            except (json.JSONDecodeError, OSError):
                pass  # Skill already validated; skip on re-read error


def _should_invoke_sub_agent(
    just_completed_skill_id: str,
    sub_agent_skills: list[str],
    repo_root: Path,
) -> bool:
    """Determine whether sub-agent skills should be invoked now.

    For n03: the sub-agent (dependency_mapper) should run after
    work-package-normalization has produced wp_structure.json.

    This is a simple heuristic that checks if the just-completed skill
    is ``work-package-normalization`` (the primary structure-producing
    skill for n03).  For other nodes with sub-agents (if any arise in
    the future), this can be extended.
    """
    if just_completed_skill_id == "work-package-normalization":
        return True
    return False
