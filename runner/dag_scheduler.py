"""
DAG Scheduler — stable runtime contract for the Horizon Europe Proposal
Orchestration System.

Public API
----------
ManifestGraph       Read-only in-memory graph built from manifest.compile.yaml.
DAGScheduler        Synchronous gate-evaluation loop over the manifest DAG.
RunSummary          Typed dataclass capturing the full run outcome.
RunAbortedError     Raised when a run cannot complete; carries ``.summary``.
RUN_SUMMARY_FILENAME  Filename of the per-run summary artifact (``run_summary.json``).

Node ID convention
------------------
All node IDs are **canonical manifest node IDs** as defined in
``manifest.compile.yaml`` ``node_registry`` (e.g. ``n01_call_analysis``,
``n08a_section_drafting``).  Short-form IDs (e.g. ``n01``, ``n08a``) are
never used.

Node state machine
------------------
States are defined in ``runner.run_context``.  Valid terminal states:

``released``
    Exit gate passed; downstream edges unblocked.
``blocked_at_entry``
    Entry gate failed; node body not executed.
``blocked_at_exit``
    Exit gate failed; node body ran but gate did not pass.
``hard_block_upstream``
    Frozen by HARD_BLOCK propagation when ``gate_09_budget_consistency`` fails.

Non-terminal states (scheduler-internal):

``pending``
    Not yet dispatched.
``running``
    Gate evaluation in progress.
``deterministic_pass_semantic_pending``
    Deterministic predicates passed; semantic evaluation outstanding.

See ``dag_scheduler_plan.md`` §2 for readiness invariants.

Run outcome contract
--------------------
``DAGScheduler.run()`` returns a :class:`RunSummary` when the run completes
(``overall_status`` is ``"pass"``, ``"partial_pass"``, or ``"fail"``).
It raises :class:`RunAbortedError` (carrying ``.summary``) when pending nodes
remain after the dispatch loop exits.  ``run_summary.json`` is written to
``.claude/runs/<run_id>/`` **before** the method returns or raises.

Phase-scoped continuation
-------------------------
:func:`bootstrap_phase_prerequisites` seeds upstream prerequisite nodes as
``released`` from durable Tier 4 gate result artifacts, enabling
phase-by-phase execution with new ``--run-id`` values per invocation.
This is a **bootstrap/seed step** invoked before dispatch, not rerun or
resume logic.  ``ManifestGraph.is_ready()`` continues to rely on current
``RunContext`` node states; the bootstrap ensures those states are correctly
initialized from prior evidence.

Scope boundaries
----------------
This module implements gate-evaluation dispatch with integrated node body
execution via the agent runtime.  The following are intentionally out of scope:

- Direct skill invocation (the scheduler calls ``run_agent()``, never ``run_skill()``)
- Parallel dispatch
- Full rerun / resume logic (phase-scoped continuation bootstrap is in scope)
- Semantic agent orchestration beyond calling ``evaluate_gate()``
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Union

import yaml

log = logging.getLogger("runner.scheduler")

from runner.agent_runtime import run_agent
from runner.call_slicer import CallSlicerError, generate_call_slice
from runner.gate_evaluator import evaluate_gate
from runner.gate_result_registry import GATE_RESULT_PATHS
from runner.manifest_reader import MANIFEST_REL_PATH
from runner.node_resolver import NodeResolver
from runner.paths import find_repo_root
from runner.phase8_reuse import (
    REUSE_ELIGIBLE_NODES,
    REUSE_SKIP_SKILLS,
    ReuseDecision,
    artifact_sha256,
    compute_input_fingerprint,
    read_artifact_run_id,
    validate_reuse_candidate,
    write_reuse_metadata,
)
from runner.predicates.gate_pass_predicates import is_gate_fresh
from runner.run_context import RunContext
from runner.runtime_models import AgentResult, NodeExecutionResult
from runner.versions import CONSTITUTION_VERSION, LIBRARY_VERSION, MANIFEST_VERSION

# ---------------------------------------------------------------------------
# Module constants
# ---------------------------------------------------------------------------

#: The gate whose failure triggers Phase 8 HARD_BLOCK propagation.
_HARD_BLOCK_GATE: str = "gate_09_budget_consistency"

#: Tier-4 root relative to repo root (mirrors gate_evaluator.TIER4_ROOT_REL).
_TIER4_ROOT_REL: str = "docs/tier4_orchestration_state"

#: Sub-path under Tier 4 used for gate IDs not in GATE_RESULT_PATHS.
_FALLBACK_GATE_RESULT_SUB: str = "gate_results"

#: Filename of the run summary artifact written by RunSummary.write().
RUN_SUMMARY_FILENAME: str = "run_summary.json"


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _gate_result_repo_path(gate_id: str) -> str:
    """
    Return the repo-relative canonical path for a gate result JSON file.

    Uses :data:`runner.gate_result_registry.GATE_RESULT_PATHS` for
    registered gate IDs; falls back to
    ``docs/tier4_orchestration_state/gate_results/<gate_id>.json``.
    """
    if gate_id in GATE_RESULT_PATHS:
        return f"{_TIER4_ROOT_REL}/{GATE_RESULT_PATHS[gate_id]}"
    return f"{_TIER4_ROOT_REL}/{_FALLBACK_GATE_RESULT_SUB}/{gate_id}.json"


# ---------------------------------------------------------------------------
# Phase-scoped continuation bootstrap
# ---------------------------------------------------------------------------


def _collect_upstream_nodes(
    graph: "ManifestGraph",
    target_nodes: set[str],
    upstream: set[str],
) -> None:
    """Recursively collect all transitive upstream node IDs for *target_nodes*.

    Traces incoming conditions in the ``ManifestGraph`` and accumulates
    every source node that must be ``released`` before *target_nodes* can
    become ready.  Already-visited nodes (present in *upstream*) are not
    re-traversed, so the function terminates on acyclic graphs.
    """
    for node_id in target_nodes:
        for cond in graph.incoming_conditions(node_id):
            src = cond.source_node_id
            if src not in upstream:
                upstream.add(src)
                _collect_upstream_nodes(graph, {src}, upstream)


def bootstrap_phase_prerequisites(
    ctx: RunContext,
    graph: "ManifestGraph",
    repo_root: Path,
    phase: int,
) -> list[str]:
    """Seed upstream prerequisite nodes as ``released`` from durable evidence.

    For phase-scoped execution (``--phase N``), upstream nodes outside the
    requested phase start as ``pending`` in a fresh ``RunContext``.  This
    function inspects canonical Tier 4 gate result artifacts to determine
    which upstream nodes have previously passed their exit gates, and seeds
    them as ``released`` in the current ``RunContext``.

    Evidence requirement
    --------------------
    A node is bootstrapped to ``released`` only when its canonical exit-gate
    result artifact exists in Tier 4 **and** contains ``"status": "pass"``.
    No completion is inferred from the mere existence of phase output files
    or any other heuristic.

    Fail-closed
    -----------
    If evidence is absent, ambiguous, corrupt, or shows a non-pass status,
    the node remains ``pending``.

    Parameters
    ----------
    ctx:
        ``RunContext`` for the current run.  Modified in-place and saved
        when at least one node is bootstrapped.
    graph:
        ``ManifestGraph`` for the DAG.
    repo_root:
        Absolute path to the repository root.
    phase:
        Phase number being executed.

    Returns
    -------
    list[str]
        Node IDs bootstrapped to ``released``, in manifest registry order.
    """
    phase_nodes = set(graph.nodes_for_phase(phase))
    if not phase_nodes:
        return []

    # Collect all transitive upstream nodes required by the target phase.
    upstream_needed: set[str] = set()
    _collect_upstream_nodes(graph, phase_nodes, upstream_needed)
    upstream_needed -= phase_nodes  # Don't bootstrap the target phase itself.

    bootstrapped: list[str] = []
    for node_id in graph.node_ids():  # preserve manifest registry order
        if node_id not in upstream_needed:
            continue
        if ctx.get_node_state(node_id) != "pending":
            continue  # already has a state (loaded from existing run)

        exit_gate_id = graph.exit_gate(node_id)
        if exit_gate_id is None:
            continue  # no exit gate — cannot verify completion

        # Check canonical gate result artifact in Tier 4.
        gate_result_rel = _gate_result_repo_path(exit_gate_id)
        gate_result_abs = repo_root / gate_result_rel
        if not gate_result_abs.exists():
            continue  # no evidence — remain pending

        try:
            result_data = json.loads(
                gate_result_abs.read_text(encoding="utf-8")
            )
            if result_data.get("status") != "pass":
                continue  # non-pass status — remain pending

            # Freshness check: reject stale upstream gates before
            # accepting them.  This enforces the invariant that a
            # node never executes with stale upstream gates — the
            # same freshness check that exit-gate evaluation applies
            # via gate_pass_recorded step 9.
            fresh, stale_reason, stale_inputs = is_gate_fresh(
                exit_gate_id, result_data, repo_root
            )
            if not fresh:
                log.info(
                    "  [BOOTSTRAP] Rejecting upstream gate %s "
                    "(stale inputs detected): %s  "
                    "evaluated_at=%s  stale_inputs=%s",
                    exit_gate_id,
                    stale_reason,
                    result_data.get("evaluated_at", "unknown"),
                    stale_inputs,
                )
                continue  # stale evidence — remain pending

            ctx.set_node_state(node_id, "released")
            bootstrapped.append(node_id)
            # Record accepted upstream gate evidence so that
            # downstream gate_pass_recorded predicates can verify
            # the run_id mismatch was explicitly accepted by this
            # run's continuation bootstrap.
            ctx.record_accepted_upstream_gate(
                gate_id=exit_gate_id,
                original_run_id=result_data.get("run_id", "unknown"),
                evidence_path=gate_result_rel,
            )
            log.info(
                "  Bootstrap: %s -> released (evidence: %s, "
                "original_run_id: %s)",
                node_id,
                gate_result_rel,
                result_data.get("run_id", "unknown"),
            )
        except (json.JSONDecodeError, OSError, TypeError):
            continue  # corrupt or unreadable evidence — remain pending

    if bootstrapped:
        ctx.save()

    return bootstrapped


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class DAGSchedulerError(Exception):
    """Raised for manifest structure or graph configuration errors."""


# ---------------------------------------------------------------------------
# RunSummary
# ---------------------------------------------------------------------------


@dataclass
class RunSummary:
    """
    Durable summary of a completed or aborted DAG run.

    Written to ``.claude/runs/<run_id>/run_summary.json`` at the end of
    every ``run()`` call, whether the run succeeded, partially passed,
    failed, or aborted.

    Attributes (plan schema)
    ------------------------
    run_id:
        UUID of the run.
    manifest_version, library_version, constitution_version:
        Version strings from ``runner.versions``.
    started_at, completed_at:
        UTC ISO-8601 timestamps for when ``run()`` entered the dispatch
        loop and when the summary was built.
    overall_status:
        One of ``"pass"``, ``"partial_pass"``, ``"fail"``, ``"aborted"``.
    terminal_nodes_reached:
        Node IDs whose final state is ``"released"`` **and** which are
        marked ``terminal: true`` in the manifest.
    stalled_nodes:
        Stall-detail dicts from ``_settle_stalled_nodes()`` — one entry per
        node that remained ``pending`` after the dispatch loop.
    hard_blocked_nodes:
        Node IDs in ``"hard_block_upstream"`` state.
    node_states:
        Full ``{node_id: state}`` map for every node in the graph, in
        manifest registry order.
    gate_results_index:
        ``{gate_id: repo_relative_path}`` for every gate evaluated during
        the run.
    node_failure_details:
        ``{node_id: {failure_origin, exit_gate_evaluated, ...}}`` for nodes
        not in ``released`` or ``pending`` state.  See §9.3 of
        ``runtime_integration_plan.md``.

    Extra implementation fields (not in plan schema)
    -------------------------------------------------
    dispatched_nodes:
        Ordered list of node IDs dispatched during the run.

    Stable compatibility surface
    ----------------------------
    ``summary["key"]`` and ``"key" in summary`` are **stable public API**
    via ``__getitem__`` / ``__contains__`` (both delegate to ``to_dict()``).

    ``to_dict()`` includes the plan-schema fields (written to
    ``run_summary.json``) **plus** the following named aliases that are
    **stable public contract** and will not be removed:

    =====================  ================================================
    Alias                  Derived from
    =====================  ================================================
    ``released_nodes``     nodes in ``"released"`` state
    ``blocked_nodes``      nodes in ``"blocked_at_entry"`` or ``"blocked_at_exit"``
    ``pending_nodes``      nodes in ``"pending"`` state
    ``stall_report``       alias for ``stalled_nodes`` (stall-detail dicts)
    ``stalled``            ``True`` when ``overall_status == "aborted"``
    ``aborted``            same as ``stalled``
    =====================  ================================================

    These aliases are **not** written to ``run_summary.json``; they exist
    only for in-process consumers.
    """

    # Plan schema fields
    run_id: str
    manifest_version: str
    library_version: str
    constitution_version: str
    started_at: str
    completed_at: str
    overall_status: str
    terminal_nodes_reached: list[str]
    stalled_nodes: list[dict]
    hard_blocked_nodes: list[str]
    node_states: dict[str, str]
    gate_results_index: dict[str, str]
    node_failure_details: dict[str, dict]
    # Extra implementation fields
    dispatched_nodes: list[str]
    phase_scope: int | None = None
    phase_scope_nodes: list[str] = field(default_factory=list)
    reuse_decisions: dict[str, dict] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def build(
        cls,
        *,
        ctx: RunContext,
        graph: ManifestGraph,
        dispatched_nodes: list[str],
        evaluated_gates: list[str],
        stalled_nodes: list[dict],
        started_at: str,
        completed_at: str,
        phase_scope: int | None = None,
        phase_scope_nodes: list[str] | None = None,
        reuse_decisions: dict[str, dict] | None = None,
    ) -> RunSummary:
        """
        Derive a ``RunSummary`` from scheduler state after ``run()`` exits.

        Parameters
        ----------
        ctx:
            The (most recently reloaded) ``RunContext`` for the run.
        graph:
            The ``ManifestGraph`` for this run.
        dispatched_nodes:
            Ordered list of node IDs dispatched during the run (from the
            scheduler's internal tracking).
        evaluated_gates:
            Ordered list of gate IDs passed to ``evaluate_gate()`` during
            the run, in evaluation order.  Used to build
            ``gate_results_index``.
        stalled_nodes:
            Output of ``_settle_stalled_nodes()`` — stall-detail dicts.
        started_at:
            UTC ISO-8601 timestamp recorded at the start of ``run()``.
        completed_at:
            UTC ISO-8601 timestamp recorded just before building the summary.

        Returns
        -------
        RunSummary
            Fully populated summary ready to write to disk.
        """
        all_node_ids = graph.node_ids()

        # Full node-state map in manifest registry order.
        node_states: dict[str, str] = {
            nid: ctx.get_node_state(nid) for nid in all_node_ids
        }

        # Derived state lists.
        pending = [n for n, s in node_states.items() if s == "pending"]
        hard_blocked = [
            n for n, s in node_states.items() if s == "hard_block_upstream"
        ]
        terminal_nodes = [n for n in all_node_ids if graph.is_terminal(n)]
        terminal_reached = [
            n for n in terminal_nodes if node_states.get(n) == "released"
        ]

        # ------------------------------------------------------------------
        # overall_status
        # ------------------------------------------------------------------
        _phase_nodes = phase_scope_nodes or []

        if phase_scope is not None and _phase_nodes:
            # Phase-scoped: status is based on the phase's own nodes only.
            phase_st = {n: node_states.get(n, "pending") for n in _phase_nodes}
            p_pending = [n for n, s in phase_st.items() if s == "pending"]
            p_released = [n for n, s in phase_st.items() if s == "released"]
            if p_pending:
                overall_status = "aborted"
            elif len(p_released) == len(_phase_nodes):
                overall_status = "pass"
            elif p_released:
                overall_status = "partial_pass"
            else:
                overall_status = "fail"
        elif pending:
            overall_status = "aborted"
        elif not terminal_nodes:
            # No terminal nodes defined — check for any blocking failures.
            blocked_states = {"blocked_at_entry", "blocked_at_exit", "hard_block_upstream"}
            has_failures = any(s in blocked_states for s in node_states.values())
            overall_status = "fail" if has_failures else "pass"
        elif len(terminal_reached) == len(terminal_nodes):
            overall_status = "pass"
        elif terminal_reached:
            overall_status = "partial_pass"
        else:
            overall_status = "fail"

        # ------------------------------------------------------------------
        # gate_results_index: map each evaluated gate_id to its canonical path
        # ------------------------------------------------------------------
        # Preserve evaluation order; deduplicate while keeping first occurrence.
        seen: set[str] = set()
        gate_results_index: dict[str, str] = {}
        for gid in evaluated_gates:
            if gid not in seen:
                gate_results_index[gid] = _gate_result_repo_path(gid)
                seen.add(gid)

        # ------------------------------------------------------------------
        # node_failure_details (§9.3 of runtime_integration_plan.md)
        # ------------------------------------------------------------------
        # Populated only for nodes not in "released" or "pending" state.
        # Manifest registry order is preserved via all_node_ids iteration.
        node_failure_details: dict[str, dict] = {}
        for nid in all_node_ids:
            st = node_states[nid]
            if st in ("released", "pending"):
                continue
            if st == "hard_block_upstream":
                # Frozen by propagation — not a local failure.
                node_failure_details[nid] = {
                    "failure_origin": None,
                    "exit_gate_evaluated": False,
                    "failure_reason": None,
                    "failure_category": None,
                }
            elif st in ("blocked_at_entry", "blocked_at_exit"):
                stored = ctx.get_node_failure_details(nid)
                if stored is not None:
                    node_failure_details[nid] = dict(stored)
                else:
                    # Conservative fallback when metadata was not persisted
                    # (e.g. gate evaluator set state before Step 6 extension).
                    if st == "blocked_at_entry":
                        node_failure_details[nid] = {
                            "failure_origin": "entry_gate",
                            "exit_gate_evaluated": False,
                            "failure_reason": None,
                            "failure_category": None,
                        }
                    else:
                        node_failure_details[nid] = {
                            "failure_origin": None,
                            "exit_gate_evaluated": False,
                            "failure_reason": None,
                            "failure_category": None,
                        }
            elif st == "deterministic_pass_semantic_pending":
                # Runner-internal transitional state — not a failure.
                # Include with null origin for completeness (node is neither
                # released nor truly failed; semantic evaluation is pending).
                node_failure_details[nid] = {
                    "failure_origin": None,
                    "exit_gate_evaluated": False,
                    "failure_reason": None,
                    "failure_category": None,
                }

        return cls(
            run_id=ctx.run_id,
            manifest_version=MANIFEST_VERSION,
            library_version=LIBRARY_VERSION,
            constitution_version=CONSTITUTION_VERSION,
            started_at=started_at,
            completed_at=completed_at,
            overall_status=overall_status,
            terminal_nodes_reached=terminal_reached,
            stalled_nodes=stalled_nodes,
            hard_blocked_nodes=hard_blocked,
            node_states=node_states,
            gate_results_index=gate_results_index,
            node_failure_details=node_failure_details,
            dispatched_nodes=list(dispatched_nodes),
            phase_scope=phase_scope,
            phase_scope_nodes=list(_phase_nodes),
            reuse_decisions=reuse_decisions or {},
        )

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """
        Return a dict representation of this summary.

        Includes all plan-schema fields, the extra ``dispatched_nodes``
        field, and several backward-compatible derived fields so that
        callers that previously indexed a plain ``result`` dict continue
        to work without modification.

        Backward-compat fields (derived; not written as separate plan-schema
        keys, but included for callers that still reference them):

        * ``released_nodes`` — nodes in ``"released"`` state (graph order).
        * ``blocked_nodes`` — nodes in ``"blocked_at_entry"`` or
          ``"blocked_at_exit"`` (graph order).
        * ``pending_nodes`` — nodes in ``"pending"`` state (graph order).
        * ``stalled`` — ``True`` when ``overall_status == "aborted"``.
        * ``aborted`` — same as ``stalled``.
        * ``stall_report`` — alias for ``stalled_nodes``.
        """
        _blocked_states = ("blocked_at_entry", "blocked_at_exit")
        is_aborted = self.overall_status == "aborted"
        return {
            # --- Plan schema ---
            "run_id": self.run_id,
            "manifest_version": self.manifest_version,
            "library_version": self.library_version,
            "constitution_version": self.constitution_version,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "overall_status": self.overall_status,
            "terminal_nodes_reached": list(self.terminal_nodes_reached),
            "stalled_nodes": list(self.stalled_nodes),
            "hard_blocked_nodes": list(self.hard_blocked_nodes),
            "node_states": dict(self.node_states),
            "gate_results_index": dict(self.gate_results_index),
            "node_failure_details": dict(self.node_failure_details),
            # --- Extra implementation fields ---
            "dispatched_nodes": list(self.dispatched_nodes),
            "phase_scope": self.phase_scope,
            "phase_scope_nodes": list(self.phase_scope_nodes),
            "reuse_decisions": dict(self.reuse_decisions),
            # --- Backward-compat derived fields ---
            "released_nodes": [
                n for n, s in self.node_states.items() if s == "released"
            ],
            "blocked_nodes": [
                n for n, s in self.node_states.items() if s in _blocked_states
            ],
            "pending_nodes": [
                n for n, s in self.node_states.items() if s == "pending"
            ],
            "stalled": is_aborted,
            "aborted": is_aborted,
            "stall_report": list(self.stalled_nodes),  # alias
        }

    def write(self, run_dir: Path) -> Path:
        """
        Write ``run_summary.json`` to *run_dir* and return its path.

        Creates *run_dir* if it does not exist.  Only plan-schema fields and
        ``dispatched_nodes`` are written (backward-compat derived fields are
        omitted from the JSON file to keep it clean).
        """
        path = run_dir / RUN_SUMMARY_FILENAME
        path.parent.mkdir(parents=True, exist_ok=True)
        # Write only the plan-schema + implementation fields, not the
        # backward-compat aliases that exist only for in-process access.
        schema_dict = {
            "run_id": self.run_id,
            "manifest_version": self.manifest_version,
            "library_version": self.library_version,
            "constitution_version": self.constitution_version,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "overall_status": self.overall_status,
            "terminal_nodes_reached": self.terminal_nodes_reached,
            "stalled_nodes": self.stalled_nodes,
            "hard_blocked_nodes": self.hard_blocked_nodes,
            "node_states": self.node_states,
            "gate_results_index": self.gate_results_index,
            "node_failure_details": self.node_failure_details,
            "dispatched_nodes": self.dispatched_nodes,
            "phase_scope": self.phase_scope,
            "phase_scope_nodes": self.phase_scope_nodes,
            "reuse_decisions": self.reuse_decisions,
        }
        path.write_text(json.dumps(schema_dict, indent=2), encoding="utf-8")
        return path

    # ------------------------------------------------------------------
    # Dict-compatible access (backward compat for Step 2/3 tests)
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Convenience properties (derived from node_states)
    # ------------------------------------------------------------------

    @property
    def pending_nodes(self) -> list[str]:
        """Node IDs in ``"pending"`` state (graph order)."""
        return [n for n, s in self.node_states.items() if s == "pending"]

    # ------------------------------------------------------------------
    # Dict-compatible access (backward compat for Step 2/3 tests)
    # ------------------------------------------------------------------

    def __getitem__(self, key: str) -> Any:
        """Enable ``summary["key"]`` access by delegating to ``to_dict()``."""
        return self.to_dict()[key]

    def __contains__(self, key: object) -> bool:
        """Enable ``"key" in summary`` by delegating to ``to_dict()``."""
        return key in self.to_dict()


# ---------------------------------------------------------------------------
# Exceptions (continued — RunAbortedError references RunSummary)
# ---------------------------------------------------------------------------


class RunAbortedError(DAGSchedulerError):
    """Raised when run() detects that no progress is possible and at least
    one non-terminal node is unsettled (remains ``pending``).

    ``run_summary.json`` is written to disk **before** this exception is
    raised so that the run outcome is durable even in the aborted case.

    Attributes
    ----------
    summary:
        The :class:`RunSummary` built at the end of the aborted run.
        This is the authoritative source for all run outcome data.
    result:
        ``summary.to_dict()`` — **stable compatibility surface** retained
        for callers that previously indexed the plain result dict via
        ``exc.result["key"]``.  Always exactly equal to
        ``exc.summary.to_dict()``.
    """

    def __init__(self, message: str, summary: RunSummary) -> None:
        super().__init__(message)
        self.summary = summary
        self.result: dict = summary.to_dict()  # backward compat


# ---------------------------------------------------------------------------
# IncomingCondition
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IncomingCondition:
    """
    A single gate condition on an incoming edge to a node.

    Attributes
    ----------
    gate_id:
        The gate that must have passed on the source node.
    source_node_id:
        The canonical node ID whose ``released`` state satisfies this
        condition (i.e. the node whose exit gate IS ``gate_id``).
    """

    gate_id: str
    source_node_id: str


# ---------------------------------------------------------------------------
# ManifestGraph
# ---------------------------------------------------------------------------


class ManifestGraph:
    """
    Read-only in-memory graph of the compiled manifest.

    Built from ``manifest.compile.yaml`` at scheduler startup.  Provides
    structural queries only; it does not duplicate ``RunContext`` state.

    Use :meth:`load` to construct.

    Invariants
    ----------
    * All node IDs are the canonical ``node_id`` values from the manifest
      ``node_registry`` (e.g. ``n01_call_analysis``, ``n08a_section_drafting``).
    * ``node_ids()`` returns IDs in registry insertion order.
    * ``incoming_conditions(n)`` returns one ``IncomingCondition`` per
      incoming edge to ``n``, plus one per ``additional_condition`` present
      on those edges.
    * For an ``additional_condition`` gate, the ``source_node_id`` is
      resolved by looking up which node has that gate as its ``exit_gate``
      in the node registry.  If no such node exists the edge's ``from_node``
      is used as a fallback.
    """

    def __init__(
        self,
        node_registry: list[dict],
        edge_registry: list[dict],
    ) -> None:
        """
        Validate and index the parsed registry lists.

        Parameters
        ----------
        node_registry:
            List of node-definition dicts from the manifest.
        edge_registry:
            List of edge-definition dicts from the manifest.

        Raises
        ------
        DAGSchedulerError
            Duplicate node IDs, missing ``node_id`` field, edge referencing
            an unknown node, or edge missing ``from_node``/``to_node``.
        """
        self._nodes: dict[str, dict] = {}
        self._node_order: list[str] = []
        self._incoming: dict[str, list[IncomingCondition]] = defaultdict(list)
        self._phase_map: dict[int, list[str]] = defaultdict(list)

        # ------------------------------------------------------------------
        # 1. Index nodes (validates duplicates)
        # ------------------------------------------------------------------
        for node in node_registry:
            if not isinstance(node, dict):
                raise DAGSchedulerError(
                    f"node_registry entry is not a dict: {node!r}"
                )
            nid = node.get("node_id")
            if not nid:
                raise DAGSchedulerError(
                    f"node_registry entry missing 'node_id': {node!r}"
                )
            if nid in self._nodes:
                raise DAGSchedulerError(
                    f"Duplicate node_id in node_registry: {nid!r}"
                )
            self._nodes[nid] = node
            self._node_order.append(nid)

        # ------------------------------------------------------------------
        # 2. Index phase_number → node_ids
        # ------------------------------------------------------------------
        for nid, node in self._nodes.items():
            pn = node.get("phase_number")
            if pn is not None:
                self._phase_map[int(pn)].append(nid)

        # ------------------------------------------------------------------
        # 3. Build exit-gate → node reverse lookup
        #    Used to resolve additional_condition sources correctly.
        # ------------------------------------------------------------------
        exit_gate_to_node: dict[str, str] = {}
        for nid, node in self._nodes.items():
            eg = node.get("exit_gate")
            if eg:
                exit_gate_to_node[eg] = nid

        # ------------------------------------------------------------------
        # 4. Process edges, build incoming-conditions index
        # ------------------------------------------------------------------
        for edge in edge_registry:
            if not isinstance(edge, dict):
                raise DAGSchedulerError(
                    f"edge_registry entry is not a dict: {edge!r}"
                )
            eid = edge.get("edge_id", "<unknown>")
            from_node: Optional[str] = edge.get("from_node")
            to_node: Optional[str] = edge.get("to_node")
            gate_cond: Optional[str] = edge.get("gate_condition")

            if not from_node:
                raise DAGSchedulerError(
                    f"Edge {eid!r} is missing 'from_node'"
                )
            if not to_node:
                raise DAGSchedulerError(
                    f"Edge {eid!r} is missing 'to_node'"
                )
            if from_node not in self._nodes:
                raise DAGSchedulerError(
                    f"Edge {eid!r} references unknown from_node: {from_node!r}"
                )
            if to_node not in self._nodes:
                raise DAGSchedulerError(
                    f"Edge {eid!r} references unknown to_node: {to_node!r}"
                )

            # Primary condition: source is the edge's from_node
            if gate_cond:
                self._incoming[to_node].append(
                    IncomingCondition(
                        gate_id=gate_cond,
                        source_node_id=from_node,
                    )
                )

            # Additional condition: resolve source via exit-gate lookup;
            # fall back to from_node only if no node claims that gate.
            additional: Optional[str] = edge.get("additional_condition")
            if additional:
                add_source = exit_gate_to_node.get(additional, from_node)
                self._incoming[to_node].append(
                    IncomingCondition(
                        gate_id=additional,
                        source_node_id=add_source,
                    )
                )

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def load(
        cls,
        manifest_path: Optional[Union[str, Path]] = None,
        *,
        repo_root: Optional[Union[str, Path]] = None,
    ) -> "ManifestGraph":
        """
        Load and parse the compiled manifest, returning a ``ManifestGraph``.

        Parameters
        ----------
        manifest_path:
            Explicit path to ``manifest.compile.yaml``.  When ``None``,
            resolves to ``repo_root / MANIFEST_REL_PATH``.
        repo_root:
            Repository root.  Used only when *manifest_path* is ``None``.
            When both are ``None``, the root is auto-discovered via
            :func:`runner.paths.find_repo_root`.

        Raises
        ------
        DAGSchedulerError
            File not found, invalid YAML, missing ``node_registry`` or
            ``edge_registry``, non-list registries, duplicate node IDs,
            or edges referencing unknown nodes.
        """
        if manifest_path is None:
            if repo_root is None:
                repo_root = find_repo_root()
            manifest_path = Path(repo_root) / MANIFEST_REL_PATH
        else:
            manifest_path = Path(manifest_path)

        if not manifest_path.exists():
            raise DAGSchedulerError(
                f"Compiled manifest not found: {manifest_path}"
            )

        try:
            raw = manifest_path.read_text(encoding="utf-8-sig")
        except OSError as exc:
            raise DAGSchedulerError(
                f"Cannot read manifest {manifest_path}: {exc}"
            ) from exc

        try:
            data = yaml.safe_load(raw)
        except yaml.YAMLError as exc:
            raise DAGSchedulerError(
                f"Invalid YAML in manifest {manifest_path}: {exc}"
            ) from exc

        if not isinstance(data, dict):
            raise DAGSchedulerError(
                f"Manifest root must be a YAML mapping; got {type(data).__name__}"
            )

        node_registry = data.get("node_registry")
        if node_registry is None:
            raise DAGSchedulerError(
                "Manifest missing required top-level key 'node_registry'"
            )
        if not isinstance(node_registry, list):
            raise DAGSchedulerError(
                "'node_registry' must be a YAML sequence (list)"
            )

        edge_registry = data.get("edge_registry")
        if edge_registry is None:
            raise DAGSchedulerError(
                "Manifest missing required top-level key 'edge_registry'"
            )
        if not isinstance(edge_registry, list):
            raise DAGSchedulerError(
                "'edge_registry' must be a YAML sequence (list)"
            )

        return cls(node_registry, edge_registry)

    # ------------------------------------------------------------------
    # Structural queries
    # ------------------------------------------------------------------

    def node_ids(self) -> list[str]:
        """Return all node IDs in manifest registry insertion order."""
        return list(self._node_order)

    def entry_gate(self, node_id: str) -> Optional[str]:
        """
        Return the entry gate ID for *node_id*, or ``None`` if none defined.

        Raises
        ------
        DAGSchedulerError
            If *node_id* is not in the graph.
        """
        self._require_known(node_id)
        return self._nodes[node_id].get("entry_gate") or None

    def exit_gate(self, node_id: str) -> Optional[str]:
        """
        Return the exit gate ID for *node_id*, or ``None`` if none defined.

        Raises
        ------
        DAGSchedulerError
            If *node_id* is not in the graph.
        """
        self._require_known(node_id)
        return self._nodes[node_id].get("exit_gate") or None

    def is_terminal(self, node_id: str) -> bool:
        """
        Return ``True`` if *node_id* is marked ``terminal: true`` in the manifest.

        Raises
        ------
        DAGSchedulerError
            If *node_id* is not in the graph.
        """
        self._require_known(node_id)
        return bool(self._nodes[node_id].get("terminal", False))

    def incoming_conditions(self, node_id: str) -> list[IncomingCondition]:
        """
        Return all incoming gate conditions for *node_id*.

        Each incoming edge contributes one ``IncomingCondition`` for its
        primary ``gate_condition`` and an additional one for each
        ``additional_condition`` present on that edge.

        Returns an empty list for nodes with no incoming edges (i.e. entry
        nodes, which are ready immediately).

        Raises
        ------
        DAGSchedulerError
            If *node_id* is not in the graph.
        """
        self._require_known(node_id)
        return list(self._incoming.get(node_id, []))

    def is_ready(self, node_id: str, ctx: RunContext) -> bool:
        """
        Return ``True`` when *node_id* is ready to execute per §2.2 of the plan.

        Ready conditions (all must hold):

        1. Node state in ``RunContext`` is ``"pending"``.
        2. Every source node required by each incoming condition is
           in state ``"released"`` in ``RunContext``.

        A node with no incoming conditions (entry node) is ready as soon as
        its state is ``"pending"``.

        Parameters
        ----------
        node_id:
            The canonical manifest node ID to check.
        ctx:
            The live ``RunContext`` for this run.

        Raises
        ------
        DAGSchedulerError
            If *node_id* is not in the graph.
        """
        self._require_known(node_id)
        if ctx.get_node_state(node_id) != "pending":
            return False
        for cond in self._incoming.get(node_id, []):
            if ctx.get_node_state(cond.source_node_id) != "released":
                return False
        return True

    # ------------------------------------------------------------------
    # Phase queries
    # ------------------------------------------------------------------

    def nodes_for_phase(self, phase_number: int) -> list[str]:
        """Return node IDs belonging to *phase_number*, in manifest order.

        Returns an empty list when no nodes carry that ``phase_number``.
        """
        return list(self._phase_map.get(phase_number, []))

    def phase_numbers(self) -> list[int]:
        """Return sorted list of all distinct ``phase_number`` values."""
        return sorted(self._phase_map.keys())

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _require_known(self, node_id: str) -> None:
        """Raise ``DAGSchedulerError`` if *node_id* is not in the graph."""
        if node_id not in self._nodes:
            raise DAGSchedulerError(
                f"Unknown node_id: {node_id!r}.  "
                f"Known nodes: {sorted(self._nodes)!r}"
            )


# ---------------------------------------------------------------------------
# DAGScheduler — Step 2: core dispatch loop
# ---------------------------------------------------------------------------


class DAGScheduler:
    """
    Synchronous single-threaded DAG scheduler.

    Drives gate evaluation across all nodes in the manifest in dependency
    order, propagates gate failures, and enforces the HARD_BLOCK freeze rule
    for Phase 8 nodes when ``gate_09_budget_consistency`` fails.

    Parameters
    ----------
    graph:
        Loaded ``ManifestGraph`` for this run.
    ctx:
        Initialised ``RunContext`` for this run.  The scheduler reloads the
        context from disk after every ``evaluate_gate()`` call so that the
        in-memory state stays consistent with what the gate evaluator wrote.
    repo_root:
        Absolute path to the repository root.
    library_path:
        Optional explicit path to the gate rules library YAML.  Forwarded to
        ``evaluate_gate()`` unchanged.
    manifest_path:
        Optional explicit path to ``manifest.compile.yaml``.  Forwarded to
        ``evaluate_gate()`` unchanged.

    Usage
    -----
    ::

        graph = ManifestGraph.load(repo_root=repo_root)
        ctx   = RunContext.initialize(repo_root, run_id)
        sched = DAGScheduler(graph, ctx, repo_root)
        result = sched.run()

    Run outcome
    -----------
    ``run()`` builds and writes a :class:`RunSummary` before returning or
    raising.  Returns ``RunSummary`` when the run completes.  Raises
    :class:`RunAbortedError` (carrying ``.summary``) when pending nodes
    remain after the dispatch loop exits.  ``run_summary.json`` is always
    written, including on abort.
    """

    def __init__(
        self,
        graph: ManifestGraph,
        ctx: RunContext,
        repo_root: Union[str, Path],
        library_path: Optional[Path] = None,
        manifest_path: Optional[Path] = None,
        phase: Optional[int] = None,
    ) -> None:
        self.graph: ManifestGraph = graph
        self.ctx: RunContext = ctx
        self.repo_root: Path = Path(repo_root)
        self.library_path: Optional[Path] = library_path
        self.manifest_path: Optional[Path] = manifest_path
        #: Phase scope: when set, only nodes with this phase_number are dispatched.
        self._phase_scope: Optional[int] = phase
        #: Accumulates every gate ID passed to evaluate_gate() during run().
        #: Populated by _dispatch_node() and consumed by RunSummary.build().
        self._evaluated_gates: list[str] = []
        #: Reuse decisions made during the run (auditable).
        self._reuse_decisions: dict[str, dict] = {}

        #: Node resolver for agent_id / skill_ids / phase_id lookups.
        #: Constructed once on first access via :attr:`_node_resolver`
        #: (lazy to avoid requiring the manifest file at construction
        #: time in test harnesses that don't provide it).
        self.__node_resolver: Optional[NodeResolver] = None

    @property
    def _node_resolver(self) -> NodeResolver:
        """Return the cached ``NodeResolver``, constructing it on first access."""
        if self.__node_resolver is None:
            self.__node_resolver = NodeResolver(
                manifest_path=self.manifest_path,
                repo_root=self.repo_root,
            )
        return self.__node_resolver

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(self) -> RunSummary:
        """
        Execute nodes in dependency order until no node is ready.

        When ``phase`` was passed to the constructor, only nodes belonging
        to that phase are eligible for dispatch.  All prerequisite checks
        (dependency state, incoming conditions, entry gates, artifacts)
        still use the full DAG — the phase filter restricts *which* nodes
        may be dispatched, not *which rules apply*.

        Each iteration recomputes the ready set from the current
        ``RunContext`` state.  Nodes are dispatched in manifest registry
        order within each iteration.  The loop stops when:

        * all in-scope nodes are settled (released / blocked / hard_blocked), or
        * no further in-scope node becomes ready (upstream failure stall).

        After the loop, :meth:`_settle_stalled_nodes` is called, a
        :class:`RunSummary` is built, and ``run_summary.json`` is written
        to ``.claude/runs/<run_id>/`` before this method returns or raises.

        Returns
        -------
        RunSummary
            Summary of the completed run.

        Raises
        ------
        RunAbortedError
            When in-scope nodes remain ``pending`` after the loop exits.
        DAGSchedulerError
            If the requested phase has no nodes, or a dispatched node has
            no exit gate defined.
        """
        started_at: str = datetime.now(timezone.utc).isoformat()
        dispatched: list[str] = []

        # ------------------------------------------------------------------
        # Step 0: Call slicing (deterministic input bounding)
        # ------------------------------------------------------------------
        try:
            call_slice_path = generate_call_slice(self.repo_root)
            log.info("Call slice generated: %s", call_slice_path)
        except CallSlicerError as exc:
            log.warning("Call slicer skipped (non-blocking): %s", exc)

        # ------------------------------------------------------------------
        # Phase scope resolution
        # ------------------------------------------------------------------
        scope_node_ids: set[str] | None = None
        if self._phase_scope is not None:
            phase_nodes = self.graph.nodes_for_phase(self._phase_scope)
            if not phase_nodes:
                raise DAGSchedulerError(
                    f"No nodes found for phase {self._phase_scope}.  "
                    f"Known phases: {self.graph.phase_numbers()!r}"
                )
            scope_node_ids = set(phase_nodes)
            log.info(
                "Phase-scoped execution: phase=%d  nodes=%s",
                self._phase_scope,
                phase_nodes,
            )
        else:
            log.info("Full DAG execution mode")

        # ------------------------------------------------------------------
        # Dispatch loop
        # ------------------------------------------------------------------
        while True:
            ready = [
                nid
                for nid in self.graph.node_ids()
                if self.graph.is_ready(nid, self.ctx)
                and (scope_node_ids is None or nid in scope_node_ids)
            ]
            if not ready:
                # Log why no nodes are ready when in phase-scoped mode.
                if scope_node_ids is not None:
                    for nid in scope_node_ids:
                        state = self.ctx.get_node_state(nid)
                        if state == "pending":
                            unmet = []
                            for cond in self.graph.incoming_conditions(nid):
                                src_st = self.ctx.get_node_state(
                                    cond.source_node_id
                                )
                                if src_st != "released":
                                    unmet.append(
                                        f"{cond.source_node_id}={src_st}"
                                        f" (requires {cond.gate_id})"
                                    )
                            if unmet:
                                log.info(
                                    "  [%s] blocked by unmet upstream: %s",
                                    nid,
                                    "; ".join(unmet),
                                )
                break

            for nid in ready:
                # Re-check: an earlier dispatch in this batch may have
                # frozen this node (e.g. gate_09 HARD_BLOCK).
                if not self.graph.is_ready(nid, self.ctx):
                    log.info("  [%s] skipped (no longer ready)", nid)
                    continue
                if scope_node_ids is not None and nid not in scope_node_ids:
                    continue
                log.info("  Dispatching: %s", nid)
                self._dispatch_node(nid)
                dispatched.append(nid)
                # _dispatch_node reloads self.ctx; subsequent is_ready()
                # calls use the updated state directly.

        # ------------------------------------------------------------------
        # Stall detection (scoped when phase filter is active)
        # ------------------------------------------------------------------
        stall_report = self._settle_stalled_nodes(
            scope_node_ids=scope_node_ids
        )

        # ------------------------------------------------------------------
        # Build RunSummary and write to disk
        # ------------------------------------------------------------------
        completed_at: str = datetime.now(timezone.utc).isoformat()

        summary = RunSummary.build(
            ctx=self.ctx,
            graph=self.graph,
            dispatched_nodes=dispatched,
            evaluated_gates=self._evaluated_gates,
            stalled_nodes=stall_report,
            started_at=started_at,
            completed_at=completed_at,
            phase_scope=self._phase_scope,
            phase_scope_nodes=sorted(scope_node_ids) if scope_node_ids else [],
            reuse_decisions=self._reuse_decisions,
        )
        summary.write(self.ctx.run_dir)

        log.info(
            "Run complete: overall_status=%s  dispatched=%d  stalled=%d",
            summary.overall_status,
            len(dispatched),
            len(stall_report),
        )

        if summary.overall_status == "aborted":
            stalled_ids = [e["node_id"] for e in stall_report]
            raise RunAbortedError(
                f"Run {self.ctx.run_id!r} aborted: "
                f"{len(summary.pending_nodes)} node(s) remain pending with "
                f"no further progress possible.  "
                f"Stalled nodes: {stalled_ids!r}",
                summary,
            )

        return summary

    # ------------------------------------------------------------------
    # Stall detection
    # ------------------------------------------------------------------

    def _settle_stalled_nodes(
        self,
        *,
        scope_node_ids: set[str] | None = None,
    ) -> list[dict]:
        """
        Identify nodes that are permanently stalled after the dispatch loop.

        A node is stalled when its state is still ``"pending"`` after the
        loop exits.  This means at least one required upstream source node
        never reached ``"released"`` state, so the ready condition (§2.2 of
        the plan) can never be satisfied.

        Parameters
        ----------
        scope_node_ids:
            When provided, only nodes in this set are checked.  Nodes
            outside the set are ignored even if they are ``"pending"``.
            Used by phase-scoped execution to restrict stall detection to
            the requested phase.

        Returns
        -------
        list[dict]
            One dict per stalled node (in manifest registry order).
        """
        report: list[dict] = []
        for node_id in self.graph.node_ids():
            if scope_node_ids is not None and node_id not in scope_node_ids:
                continue
            if self.ctx.get_node_state(node_id) != "pending":
                continue
            unsatisfied: list[dict] = []
            for cond in self.graph.incoming_conditions(node_id):
                src_state = self.ctx.get_node_state(cond.source_node_id)
                if src_state != "released":
                    unsatisfied.append(
                        {
                            "gate_id": cond.gate_id,
                            "source_node_id": cond.source_node_id,
                            "source_node_state": src_state,
                        }
                    )
            report.append(
                {
                    "node_id": node_id,
                    "unsatisfied_conditions": unsatisfied,
                }
            )
        return report

    # ------------------------------------------------------------------
    # Node dispatch
    # ------------------------------------------------------------------

    def _dispatch_node(self, node_id: str) -> NodeExecutionResult:
        """
        Execute node body and evaluate gates for *node_id*.

        Execution contract (runtime_integration_plan.md §9.2)
        -----------------------------------------------------
        1. Set state → ``"running"``.  Persist.
        2. Evaluate entry gate (if present).  On failure →
           ``"blocked_at_entry"``; return immediately.
        3. Execute node body via ``run_agent()``.  On failure or
           ``can_evaluate_exit_gate == False`` → ``"blocked_at_exit"``
           with ``failure_origin="agent_body"``; skip exit gate; return.
        4. Evaluate exit gate.  On pass → ``"released"``.
           On failure → ``"blocked_at_exit"`` with
           ``failure_origin="exit_gate"``.
        5. Return :class:`NodeExecutionResult`.

        ``evaluate_gate()`` internally loads a fresh ``RunContext``, writes
        node state, and saves.  After each call this method reloads
        ``self.ctx`` from disk so the in-memory state stays authoritative.
        The explicit state enforcement guarantees that node state in
        ``RunContext`` is always consistent with the gate/agent result,
        regardless of how ``evaluate_gate()`` is implemented.

        Parameters
        ----------
        node_id:
            Canonical manifest node ID to dispatch.

        Returns
        -------
        NodeExecutionResult
            Full composite result of the dispatch.

        Raises
        ------
        DAGSchedulerError
            If *node_id* has no exit gate (all production nodes must have one).
        """
        # ── Step 1: Mark running ──────────────────────────────────────
        log.info("  [%s] state -> running", node_id)
        self.ctx.set_node_state(node_id, "running")
        self.ctx.save()

        # ── Step 2: Entry gate (optional) ─────────────────────────────
        entry_gate_id = self.graph.entry_gate(node_id)
        if entry_gate_id is not None:
            entry_result = evaluate_gate(
                entry_gate_id,
                self.ctx.run_id,
                self.repo_root,
                library_path=self.library_path,
                manifest_path=self.manifest_path,
            )
            self._evaluated_gates.append(entry_gate_id)
            self._reload_ctx()

            entry_status = entry_result.get("status", "unknown")
            log.info(
                "  [%s] entry gate %s -> %s", node_id, entry_gate_id, entry_status
            )

            if entry_status != "pass":
                # Enforce blocked_at_entry and persist failure metadata
                # (idempotent if evaluate_gate() already set the state).
                self.ctx.set_node_state(
                    node_id,
                    "blocked_at_entry",
                    failure_origin="entry_gate",
                    exit_gate_evaluated=False,
                )
                self.ctx.save()
                return NodeExecutionResult(
                    node_id=node_id,
                    final_state="blocked_at_entry",
                    exit_gate_evaluated=False,
                    failure_origin="entry_gate",
                    gate_result=entry_result,
                    agent_result=None,
                )

        # ── Validate exit gate exists (before agent invocation) ───────
        exit_gate_id = self.graph.exit_gate(node_id)
        if exit_gate_id is None:
            raise DAGSchedulerError(
                f"Node {node_id!r} has no exit_gate defined in the manifest.  "
                "All production nodes must have an exit gate."
            )

        # ── Step 2.5: Phase 8 reuse check (n08a/n08b/n08c only) ──────
        #
        # If the node is a Phase 8 section drafting node and a valid
        # reuse candidate exists, skip the expensive drafting skill
        # but still run audit skills (traceability-check, compliance-
        # check) so that gate predicates have current-run evidence.
        # The exit gate is always re-evaluated in the current run.
        _reuse_skip_skills: list[str] | None = None
        if node_id in REUSE_ELIGIBLE_NODES:
            fp = compute_input_fingerprint(node_id, self.repo_root)
            decision = validate_reuse_candidate(
                node_id, self.repo_root, current_fingerprint=fp,
            )
            if decision.reusable:
                log.info(
                    "  [%s] REUSE: drafting skipped, audit skills executing "
                    "(source_run=%s, fingerprint=%s..)",
                    node_id,
                    decision.source_run_id,
                    (decision.input_fingerprint or "")[:12],
                )
                reuse_dec = {
                    "status": "reused",
                    "mode": "drafting_skipped_audit_executed",
                    "source_run_id": decision.source_run_id,
                    "artifact_run_id": decision.source_run_id,
                    "artifact_path": decision.artifact_path,
                    "input_fingerprint": decision.input_fingerprint,
                    "gate_id": decision.gate_id,
                }
                self._reuse_decisions[node_id] = reuse_dec
                # Persist to RunContext so gate predicates can verify
                self.ctx.record_reuse_decision(node_id, reuse_dec)
                self.ctx.save()
                # Skip only the drafting skill; audit skills still run.
                drafting_skill = REUSE_SKIP_SKILLS.get(node_id)
                if drafting_skill:
                    _reuse_skip_skills = [drafting_skill]
            else:
                log.info(
                    "  [%s] REUSE: not reusable (%s)",
                    node_id, decision.reason,
                )
                self._reuse_decisions[node_id] = {
                    "status": "not_reused",
                    "reason": decision.reason,
                }

        # ── Step 3: Node body execution via agent runtime ─────────────
        resolver = self._node_resolver
        agent_id = resolver.resolve_agent_id(node_id)
        sub_agent_id = resolver.resolve_sub_agent_id(node_id)
        pre_gate_agent_id = resolver.resolve_pre_gate_agent_id(node_id)
        skill_ids = resolver.resolve_skill_ids(node_id)
        phase_id = resolver.resolve_phase_id(node_id)

        log.info("  [%s] agent dispatch: agent=%s", node_id, agent_id)
        agent_result = run_agent(
            agent_id,
            node_id,
            self.ctx.run_id,
            self.repo_root,
            manifest_path=self.manifest_path,
            skill_ids=skill_ids,
            phase_id=phase_id,
            sub_agent_id=sub_agent_id,
            pre_gate_agent_id=pre_gate_agent_id,
            skip_skills=_reuse_skip_skills,
        )
        log.info(
            "  [%s] agent result: status=%s  can_evaluate_exit=%s",
            node_id,
            agent_result.status,
            agent_result.can_evaluate_exit_gate,
        )

        # Agent-body failure OR can_evaluate_exit_gate == False:
        # skip exit gate unconditionally (§9.2 step 3, §10.4).
        if (
            agent_result.status == "failure"
            or not agent_result.can_evaluate_exit_gate
        ):
            self.ctx.set_node_state(
                node_id,
                "blocked_at_exit",
                failure_origin="agent_body",
                exit_gate_evaluated=False,
                failure_reason=agent_result.failure_reason,
                failure_category=agent_result.failure_category,
            )

            # HARD_BLOCK: if this is the budget gate node, freeze Phase 8.
            if exit_gate_id == _HARD_BLOCK_GATE:
                self.ctx.mark_hard_block_downstream()

            self.ctx.save()
            log.info(
                "  [%s] state -> blocked_at_exit (agent_body failure)",
                node_id,
            )

            return NodeExecutionResult(
                node_id=node_id,
                final_state="blocked_at_exit",
                exit_gate_evaluated=False,
                failure_origin="agent_body",
                gate_result=None,
                agent_result=agent_result,
                failure_reason=agent_result.failure_reason,
                failure_category=agent_result.failure_category,
            )

        # ── Step 4: Exit gate evaluation ──────────────────────────────
        exit_result = evaluate_gate(
            exit_gate_id,
            self.ctx.run_id,
            self.repo_root,
            library_path=self.library_path,
            manifest_path=self.manifest_path,
        )
        self._evaluated_gates.append(exit_gate_id)
        self._reload_ctx()

        exit_status = exit_result.get("status", "unknown")
        log.info(
            "  [%s] exit gate %s -> %s", node_id, exit_gate_id, exit_status
        )

        if exit_status == "pass":
            # Enforce released and persist metadata (idempotent if
            # evaluate_gate() already set the state).
            self.ctx.set_node_state(
                node_id,
                "released",
                failure_origin=None,
                exit_gate_evaluated=True,
            )
            self.ctx.save()
            log.info("  [%s] state -> released", node_id)

            # ── Write reuse metadata for Phase 8 section nodes ────
            # Only after gate pass — never before, never on failure.
            if node_id in REUSE_ELIGIBLE_NODES:
                try:
                    _cfg = REUSE_ELIGIBLE_NODES[node_id]
                    _fp = compute_input_fingerprint(node_id, self.repo_root)
                    _art_path = self.repo_root / _cfg["artifact_path"]
                    _art_hash = artifact_sha256(_art_path)
                    _art_run_id = read_artifact_run_id(_art_path)
                    if _fp is not None and _art_hash is not None:
                        write_reuse_metadata(
                            node_id=node_id,
                            repo_root=self.repo_root,
                            source_run_id=_art_run_id or self.ctx.run_id,
                            artifact_path=_cfg["artifact_path"],
                            schema_id=_cfg["schema_id"],
                            gate_id=_cfg["gate_id"],
                            input_fingerprint=_fp,
                            artifact_hash=_art_hash,
                            artifact_run_id=_art_run_id or self.ctx.run_id,
                            last_validated_run_id=self.ctx.run_id,
                        )
                        log.info(
                            "  [%s] reuse metadata written (fp=%s..)",
                            node_id, _fp[:12],
                        )
                except Exception:
                    # Best-effort: failure to write reuse metadata must
                    # not block the run.  Next run will just re-execute.
                    log.warning(
                        "  [%s] reuse metadata write failed (non-blocking)",
                        node_id,
                        exc_info=True,
                    )

            return NodeExecutionResult(
                node_id=node_id,
                final_state="released",
                exit_gate_evaluated=True,
                failure_origin=None,
                gate_result=exit_result,
                agent_result=agent_result,
            )
        else:
            # Exit gate failed.
            if exit_gate_id == _HARD_BLOCK_GATE:
                # Freeze Phase 8 nodes.
                self.ctx.mark_hard_block_downstream()

            # Enforce blocked_at_exit.
            self.ctx.set_node_state(
                node_id,
                "blocked_at_exit",
                failure_origin="exit_gate",
                exit_gate_evaluated=True,
                failure_reason=exit_result.get("reason"),
                failure_category=exit_result.get("failure_category"),
            )
            self.ctx.save()
            log.info(
                "  [%s] state -> blocked_at_exit (exit_gate failure)", node_id
            )

            return NodeExecutionResult(
                node_id=node_id,
                final_state="blocked_at_exit",
                exit_gate_evaluated=True,
                failure_origin="exit_gate",
                gate_result=exit_result,
                agent_result=agent_result,
                failure_reason=exit_result.get("reason"),
                failure_category=exit_result.get("failure_category"),
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _reload_ctx(self) -> None:
        """
        Reload ``self.ctx`` from disk.

        Called after every ``evaluate_gate()`` invocation so that subsequent
        ``get_node_state()`` and ``is_ready()`` calls see the state that
        ``evaluate_gate()`` persisted.
        """
        self.ctx = RunContext.load(self.repo_root, self.ctx.run_id)
