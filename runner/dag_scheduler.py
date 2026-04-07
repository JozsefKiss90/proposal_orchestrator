"""
DAG Scheduler — Steps 1–4: ManifestGraph, DAGScheduler core loop,
stall detection / abort, and RunSummary persistence.

Node ID convention
------------------
All node IDs in this module are **canonical manifest node IDs** as defined
in ``manifest.compile.yaml`` ``node_registry`` (e.g. ``n01_call_analysis``,
``n08a_section_drafting``).  Short-form IDs (e.g. ``n01``, ``n08a``) are
never used.  The same canonical IDs are used by:

* ``RunContext.set_node_state`` / ``get_node_state``
* ``PHASE_8_NODE_IDS`` in ``runner.run_context``
* Gate-to-node extraction in ``runner.gate_evaluator._extract_node_id``
  (which reads ``evaluated_at`` from the gate library; the library entries
  now use canonical IDs in ``evaluated_at`` after the Step 1 reconciliation)

See dag_scheduler_plan.md §2 for the full node-state and readiness invariants.

Step 1 scope (ManifestGraph)
----------------------------
``ManifestGraph``, ``IncomingCondition``, and ``DAGSchedulerError``.

Step 2 scope (DAGScheduler core loop)
--------------------------------------
``DAGScheduler.__init__``, ``run()``, and ``_dispatch_node()``.

``_dispatch_node()`` drives gate evaluation via ``evaluate_gate()``.
``evaluate_gate()`` loads a fresh ``RunContext`` from disk, updates node
state, and saves.  After each ``evaluate_gate()`` call ``_dispatch_node``
reloads ``self.ctx`` from disk so that subsequent readiness checks see the
updated state.  Where ``evaluate_gate()`` is mocked in tests, the scheduler
explicitly enforces the intended terminal state so that the two code-paths
produce identical observable behaviour.

Step 3 scope (stall detection and run-abort)
--------------------------------------------
``_settle_stalled_nodes()`` and ``RunAbortedError``.

After the dispatch loop exits, any node still ``pending`` is permanently
stalled.  ``run()`` raises ``RunAbortedError`` when any pending nodes remain.

Step 4 scope (RunSummary persistence)
--------------------------------------
``RunSummary`` — a typed dataclass that captures the full run outcome.

``RunSummary.build()`` derives the summary from ``RunContext``,
``ManifestGraph``, scheduler bookkeeping (dispatched nodes, evaluated gates,
timestamps), and the stall report from ``_settle_stalled_nodes()``.

``RunSummary.write()`` persists ``run_summary.json`` to
``.claude/runs/<run_id>/`` **before** ``run()`` returns or raises.  This
replaces the Step 3 "exception carries result dict" pattern:
``RunAbortedError`` now carries the ``RunSummary`` object on ``.summary``
and exposes a backward-compatible ``.result`` dict via ``summary.to_dict()``.

``run()`` returns ``RunSummary`` (not a plain dict).  ``RunSummary`` supports
dict-style ``[key]`` and ``in`` access via ``__getitem__`` / ``__contains__``
so that existing Step 2/3 tests that index the return value continue to work
unchanged.

Deferred to Step 5:
``runner/__main__.py``, node body execution, parallelism.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Union

import yaml

from runner.gate_evaluator import evaluate_gate
from runner.gate_result_registry import GATE_RESULT_PATHS
from runner.manifest_reader import MANIFEST_REL_PATH
from runner.paths import find_repo_root
from runner.run_context import RunContext
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

    Extra implementation fields (not in plan schema)
    -------------------------------------------------
    dispatched_nodes:
        Ordered list of node IDs dispatched during the run.

    Backward-compatible access
    --------------------------
    ``summary["key"]`` and ``"key" in summary`` are supported via
    ``__getitem__`` / ``__contains__`` (both delegate to ``to_dict()``).
    ``to_dict()`` also includes derived compat fields: ``released_nodes``,
    ``blocked_nodes``, ``pending_nodes``, ``stalled``, ``aborted``,
    ``stall_report``.
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
    # Extra implementation field
    dispatched_nodes: list[str]

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
        # overall_status (dag_scheduler_plan.md §4, RunSummary schema)
        # ------------------------------------------------------------------
        if pending:
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
            dispatched_nodes=list(dispatched_nodes),
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
            # --- Extra implementation field ---
            "dispatched_nodes": list(self.dispatched_nodes),
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
            "dispatched_nodes": self.dispatched_nodes,
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
        This is the authoritative payload for Step 4 onwards.
    result:
        ``summary.to_dict()`` — retained for backward compatibility with
        callers and tests that previously accessed ``exc.result["key"]``.
        Both attributes are always consistent.
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
        # 2. Build exit-gate → node reverse lookup
        #    Used to resolve additional_condition sources correctly.
        # ------------------------------------------------------------------
        exit_gate_to_node: dict[str, str] = {}
        for nid, node in self._nodes.items():
            eg = node.get("exit_gate")
            if eg:
                exit_gate_to_node[eg] = nid

        # ------------------------------------------------------------------
        # 3. Process edges, build incoming-conditions index
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

    Step 2 scope
    ------------
    Implements ``__init__``, ``run()``, and ``_dispatch_node()``.

    Step 3 scope
    ------------
    Implements ``_settle_stalled_nodes()`` and ``RunAbortedError`` raising
    in ``run()``.

    Step 4 scope
    ------------
    ``run()`` builds and writes a :class:`RunSummary` before returning or
    raising.  Returns a ``RunSummary`` (not a plain dict).  ``RunAbortedError``
    now carries ``.summary`` (the authoritative payload) and a backward-
    compatible ``.result`` dict.
    """

    def __init__(
        self,
        graph: ManifestGraph,
        ctx: RunContext,
        repo_root: Union[str, Path],
        library_path: Optional[Path] = None,
        manifest_path: Optional[Path] = None,
    ) -> None:
        self.graph: ManifestGraph = graph
        self.ctx: RunContext = ctx
        self.repo_root: Path = Path(repo_root)
        self.library_path: Optional[Path] = library_path
        self.manifest_path: Optional[Path] = manifest_path
        #: Accumulates every gate ID passed to evaluate_gate() during run().
        #: Populated by _dispatch_node() and consumed by RunSummary.build().
        self._evaluated_gates: list[str] = []

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(self) -> RunSummary:
        """
        Execute all nodes in dependency order until no node is ready.

        Each iteration recomputes the ready set from the current
        ``RunContext`` state.  Nodes are dispatched in manifest registry
        order within each iteration.  The loop stops when:

        * all nodes are settled (released / blocked / hard_blocked), or
        * no further node becomes ready (upstream failure stall).

        After the loop, :meth:`_settle_stalled_nodes` is called, a
        :class:`RunSummary` is built, and ``run_summary.json`` is written
        to ``.claude/runs/<run_id>/`` before this method returns or raises.

        Returns
        -------
        RunSummary
            Summary of the completed run.  Supports ``summary["key"]`` and
            ``"key" in summary`` for backward compatibility with tests that
            previously indexed the plain result dict.

        Raises
        ------
        RunAbortedError
            When any nodes remain ``pending`` after the loop exits.
            ``run_summary.json`` is written **before** raising.  The
            exception carries ``.summary`` (the :class:`RunSummary`) and a
            backward-compatible ``.result`` dict (``summary.to_dict()``).
        DAGSchedulerError
            If a dispatched node has no exit gate defined.
        """
        started_at: str = datetime.now(timezone.utc).isoformat()
        dispatched: list[str] = []

        while True:
            ready = [
                nid
                for nid in self.graph.node_ids()
                if self.graph.is_ready(nid, self.ctx)
            ]
            if not ready:
                break
            for nid in ready:
                # Re-check: an earlier dispatch in this batch may have
                # frozen this node (e.g. gate_09 HARD_BLOCK).
                if not self.graph.is_ready(nid, self.ctx):
                    continue
                self._dispatch_node(nid)
                dispatched.append(nid)
                # _dispatch_node reloads self.ctx; subsequent is_ready()
                # calls use the updated state directly.

        # ------------------------------------------------------------------
        # Step 3: stall detection
        # ------------------------------------------------------------------
        stall_report = self._settle_stalled_nodes()

        # ------------------------------------------------------------------
        # Step 4: build RunSummary and write to disk
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
        )
        summary.write(self.ctx.run_dir)

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

    def _settle_stalled_nodes(self) -> list[dict]:
        """
        Identify nodes that are permanently stalled after the dispatch loop.

        A node is stalled when its state is still ``"pending"`` after the
        loop exits.  This means at least one required upstream source node
        never reached ``"released"`` state, so the ready condition (§2.2 of
        the plan) can never be satisfied.

        This method is **read-only**: it does not mutate any node state and
        does not introduce new state strings.  Hard-blocked nodes
        (``"hard_block_upstream"``) are already settled and are excluded.

        Returns
        -------
        list[dict]
            One dict per stalled node (in manifest registry order), each with:

            ``node_id``
                Canonical manifest node ID of the stalled node.
            ``unsatisfied_conditions``
                List of dicts — one per :class:`IncomingCondition` whose
                source is not ``"released"`` — each containing:

                * ``gate_id`` — the gate that was never satisfied
                * ``source_node_id`` — the upstream node that should have
                  been released
                * ``source_node_state`` — its actual current state

            An entry node (no incoming edges) that somehow remains pending
            will appear with an empty ``unsatisfied_conditions`` list; this
            indicates a scheduler invariant violation and must not occur in
            normal operation.
        """
        report: list[dict] = []
        for node_id in self.graph.node_ids():
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

    def _dispatch_node(self, node_id: str) -> dict:
        """
        Evaluate the entry and exit gates for *node_id*.

        Execution contract
        ------------------
        1. Transition node state to ``"running"`` and persist.
        2. If the node has an entry gate, evaluate it.  On failure,
           ensure state is ``"blocked_at_entry"`` and return.
        3. Evaluate the exit gate.
        4. On exit-gate pass, ensure state is ``"released"``.
        5. On exit-gate failure:
           - If the gate is ``gate_09_budget_consistency``, call
             ``ctx.mark_hard_block_downstream()`` and persist so that Phase 8
             nodes are frozen even when ``evaluate_gate()`` is mocked.
           - Ensure state is ``"blocked_at_exit"``.
        6. Return the last gate result dict.

        ``evaluate_gate()`` internally loads a fresh ``RunContext``, writes
        node state, and saves.  After each call this method reloads
        ``self.ctx`` from disk so the in-memory state stays authoritative.
        When ``evaluate_gate()`` is mocked (tests), the explicit state
        enforcement in steps 4–5 guarantees identical observable behaviour.

        Parameters
        ----------
        node_id:
            Canonical manifest node ID to dispatch.

        Returns
        -------
        dict
            The gate result dict from the last ``evaluate_gate()`` call.

        Raises
        ------
        DAGSchedulerError
            If *node_id* has no exit gate (all production nodes must have one).
        """
        # 1. Mark running
        self.ctx.set_node_state(node_id, "running")
        self.ctx.save()

        # 2. Entry gate (optional — only n01_call_analysis has one currently)
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

            if entry_result.get("status") != "pass":
                # Enforce blocked_at_entry in case evaluate_gate() was mocked.
                if self.ctx.get_node_state(node_id) != "blocked_at_entry":
                    self.ctx.set_node_state(node_id, "blocked_at_entry")
                    self.ctx.save()
                return entry_result

        # 3. Exit gate (mandatory for all production nodes)
        exit_gate_id = self.graph.exit_gate(node_id)
        if exit_gate_id is None:
            raise DAGSchedulerError(
                f"Node {node_id!r} has no exit_gate defined in the manifest.  "
                "All production nodes must have an exit gate."
            )

        exit_result = evaluate_gate(
            exit_gate_id,
            self.ctx.run_id,
            self.repo_root,
            library_path=self.library_path,
            manifest_path=self.manifest_path,
        )
        self._evaluated_gates.append(exit_gate_id)
        self._reload_ctx()

        if exit_result.get("status") == "pass":
            # 4. Enforce released.
            if self.ctx.get_node_state(node_id) != "released":
                self.ctx.set_node_state(node_id, "released")
                self.ctx.save()
        else:
            # 5. Exit gate failed.
            if exit_gate_id == _HARD_BLOCK_GATE:
                # Freeze Phase 8 nodes.  This is idempotent if evaluate_gate()
                # already called it; it is essential when evaluate_gate() is mocked.
                self.ctx.mark_hard_block_downstream()
                self.ctx.save()

            # Enforce blocked_at_exit.
            if self.ctx.get_node_state(node_id) != "blocked_at_exit":
                self.ctx.set_node_state(node_id, "blocked_at_exit")
                self.ctx.save()

        return exit_result

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
