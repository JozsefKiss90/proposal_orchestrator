"""
DAG Scheduler — Step 1: ManifestGraph (graph loading and readiness logic).

This module provides the read-only graph layer that the DAG scheduler uses
to determine node order, incoming gate conditions, and node readiness.

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

Step 1 scope
------------
Implements ``ManifestGraph``, ``IncomingCondition``, and ``DAGSchedulerError``
only.  ``DAGScheduler.run()``, ``_dispatch_node()``, ``_settle_stalled_nodes()``,
``RunSummary``, and the CLI entry point are deferred to Steps 2–5.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

import yaml

from runner.manifest_reader import MANIFEST_REL_PATH
from runner.paths import find_repo_root
from runner.run_context import RunContext

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class DAGSchedulerError(Exception):
    """Raised for manifest structure or graph configuration errors."""


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
