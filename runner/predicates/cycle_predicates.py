"""
Step 8 — Cycle predicate.

Implements the single cycle-detection predicate defined in
gate_rules_library_plan.md §4.5:

    no_dependency_cycles(wp_path, *, repo_root=None)

This predicate reads the ``dependency_map`` field from the Phase 3 canonical
artifact ``wp_structure.json`` and verifies that the directed graph it
represents is acyclic.

---------------------------------------------------------------------------
Dependency-map contract (from artifact_schema_specification.yaml §1.3)
---------------------------------------------------------------------------

The ``dependency_map`` field is a JSON object with two required sub-fields:

    {
        "nodes": ["WP1", "WP2", "T1.1", ...],   // array of string identifiers
        "edges": [
            {"from": "WP1", "to": "WP2", "edge_type": "finish_to_start"},
            ...
        ]
    }

``nodes``:  Required array of string identifiers.  May be empty (→ vacuous
            pass, no edges can exist).  Each entry must be a string.

``edges``:  Required array.  May be empty (→ vacuous pass).  Each entry
            must be a dict with at least a string ``from`` field and a
            string ``to`` field.  The ``edge_type`` field is required by
            the schema but is not load-bearing for cycle detection; it is
            validated only to reject clearly malformed entries (i.e. entries
            that are not dicts at all).

Semantics of an edge (source → target): the source node must complete
before the target node begins (finish-to-start is the dominant type).
Cycle detection is direction-agnostic in terms of the failure condition:
any cycle in the directed graph constitutes a blocking gate failure.

---------------------------------------------------------------------------
Cycle-detection algorithm: Kahn's algorithm (topological sort, BFS)
---------------------------------------------------------------------------

Kahn's algorithm was chosen because:
1. It is deterministic and well-understood.
2. It naturally produces a set of "remaining nodes" (those that could not
   be processed) as a diagnostic when a cycle is present — these nodes
   are all members of cyclic components, giving the operator a concrete
   starting point for inspection.
3. It does not require recursive DFS and has no stack-depth issues for
   large graphs.

Algorithm:
1. Build an adjacency list and an in-degree map from the edge list.
2. Seed a queue with all nodes whose in-degree is 0.
3. Repeatedly dequeue a node, "remove" its outgoing edges by decrementing
   the in-degree of each successor, and enqueue any successor whose
   in-degree drops to 0.
4. If all nodes are processed, the graph is acyclic.
5. If any nodes remain unprocessed, they form one or more cyclic components;
   return them as diagnostic information.

---------------------------------------------------------------------------
Failure-category mapping
---------------------------------------------------------------------------

gate_rules_library_plan.md §3 defines the expected mapping:

    MISSING_MANDATORY_INPUT     — wp_path does not exist on disk
    MALFORMED_ARTIFACT          — file present but not valid JSON, or
                                  ``dependency_map`` is absent/unsupported
    CROSS_ARTIFACT_INCONSISTENCY — graph is readable but contains a cycle

``POLICY_VIOLATION`` is not used for cycle presence; the plan classifies
cycle failures as cross-artifact inconsistency.
"""

from __future__ import annotations

import json
from collections import deque
from pathlib import Path
from typing import Any, Optional

from runner.predicates.types import (
    CROSS_ARTIFACT_INCONSISTENCY,
    MALFORMED_ARTIFACT,
    MISSING_MANDATORY_INPUT,
    PredicateResult,
)

try:
    from runner.paths import resolve_repo_path
except ImportError:  # pragma: no cover — only missing in isolated test envs
    def resolve_repo_path(path: str, repo_root: Optional[str]) -> Path:  # type: ignore[misc]
        return Path(path)


# ---------------------------------------------------------------------------
# Public predicate
# ---------------------------------------------------------------------------


def no_dependency_cycles(
    wp_path: str,
    *,
    repo_root: Optional[str] = None,
) -> PredicateResult:
    """
    Verify that the ``dependency_map`` in the Phase 3 WP structure artifact
    represents a directed acyclic graph (DAG).

    Parameters
    ----------
    wp_path:
        Absolute (or repo-relative) path to the canonical Phase 3 artifact
        ``wp_structure.json``.  Must be a file path, not a directory.
    repo_root:
        Optional repository root used by ``resolve_repo_path``.  When
        ``None``, path resolution falls back to the caller's working directory
        (consistent with all other predicate modules in this package).

    Returns
    -------
    PredicateResult
        ``passed=True`` when the file exists, parses as a valid JSON object,
        contains a structurally usable ``dependency_map``, and the directed
        graph defined by that map is acyclic.

        ``passed=False`` with:
        - ``MISSING_MANDATORY_INPUT`` when the file does not exist.
        - ``MALFORMED_ARTIFACT`` when the file exists but cannot be parsed,
          is not a JSON object, or ``dependency_map`` is absent, null, not
          a dict, or contains entries that are not interpretable as directed
          edges (see §Dependency-map contract above).
        - ``CROSS_ARTIFACT_INCONSISTENCY`` when the graph is structurally
          valid but contains one or more directed cycles.
    """
    resolved = resolve_repo_path(wp_path, repo_root)

    # ------------------------------------------------------------------
    # Guard 1: file must exist
    # ------------------------------------------------------------------
    if not resolved.exists():
        return PredicateResult(
            passed=False,
            failure_category=MISSING_MANDATORY_INPUT,
            reason=f"wp_structure.json not found: {resolved}",
            details={"path": str(resolved)},
        )

    # ------------------------------------------------------------------
    # Guard 2: must parse as a JSON object
    # ------------------------------------------------------------------
    try:
        with resolved.open("r", encoding="utf-8") as fh:
            artifact: Any = json.load(fh)
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=f"wp_structure.json is not valid JSON: {exc}",
            details={"path": str(resolved), "error": str(exc)},
        )

    if not isinstance(artifact, dict):
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=(
                "wp_structure.json top-level value must be a JSON object "
                f"(dict); got {type(artifact).__name__}"
            ),
            details={"path": str(resolved), "actual_type": type(artifact).__name__},
        )

    # ------------------------------------------------------------------
    # Guard 3: dependency_map must be present and be a dict
    # ------------------------------------------------------------------
    if "dependency_map" not in artifact:
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=(
                "wp_structure.json is missing the required top-level field "
                "'dependency_map' (artifact_schema_specification.yaml §1.3)"
            ),
            details={"path": str(resolved)},
        )

    dep_map: Any = artifact["dependency_map"]

    if dep_map is None or not isinstance(dep_map, dict):
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=(
                "'dependency_map' must be a JSON object (dict) with 'nodes' "
                "and 'edges' arrays; got "
                f"{type(dep_map).__name__ if dep_map is not None else 'null'}"
            ),
            details={
                "path": str(resolved),
                "actual_type": type(dep_map).__name__ if dep_map is not None else "null",
            },
        )

    # ------------------------------------------------------------------
    # Guard 4: dependency_map.nodes must be a list of strings
    # ------------------------------------------------------------------
    nodes_raw: Any = dep_map.get("nodes")
    if nodes_raw is None or not isinstance(nodes_raw, list):
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=(
                "'dependency_map.nodes' must be an array of string identifiers; "
                f"got {type(nodes_raw).__name__ if nodes_raw is not None else 'null'}"
            ),
            details={"path": str(resolved)},
        )

    for i, node in enumerate(nodes_raw):
        if not isinstance(node, str):
            return PredicateResult(
                passed=False,
                failure_category=MALFORMED_ARTIFACT,
                reason=(
                    f"'dependency_map.nodes[{i}]' must be a string identifier; "
                    f"got {type(node).__name__}: {node!r}"
                ),
                details={"path": str(resolved), "bad_node_index": i, "bad_node_value": node},
            )

    # ------------------------------------------------------------------
    # Guard 5: dependency_map.edges must be a list of dicts with from/to
    # ------------------------------------------------------------------
    edges_raw: Any = dep_map.get("edges")
    if edges_raw is None or not isinstance(edges_raw, list):
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=(
                "'dependency_map.edges' must be an array of edge objects; "
                f"got {type(edges_raw).__name__ if edges_raw is not None else 'null'}"
            ),
            details={"path": str(resolved)},
        )

    for i, edge in enumerate(edges_raw):
        if not isinstance(edge, dict):
            return PredicateResult(
                passed=False,
                failure_category=MALFORMED_ARTIFACT,
                reason=(
                    f"'dependency_map.edges[{i}]' must be a dict with 'from' "
                    f"and 'to' string fields; got {type(edge).__name__}: {edge!r}"
                ),
                details={"path": str(resolved), "bad_edge_index": i},
            )
        for required_field in ("from", "to"):
            val = edge.get(required_field)
            if not isinstance(val, str):
                return PredicateResult(
                    passed=False,
                    failure_category=MALFORMED_ARTIFACT,
                    reason=(
                        f"'dependency_map.edges[{i}].{required_field}' must be "
                        f"a non-null string; got "
                        f"{type(val).__name__ if val is not None else 'null'}: {val!r}"
                    ),
                    details={
                        "path": str(resolved),
                        "bad_edge_index": i,
                        "bad_field": required_field,
                    },
                )

    # ------------------------------------------------------------------
    # Vacuous pass: empty node or edge sets cannot contain a cycle
    # ------------------------------------------------------------------
    nodes: set[str] = set(nodes_raw)
    edges: list[tuple[str, str]] = [(e["from"], e["to"]) for e in edges_raw]

    if not nodes or not edges:
        return PredicateResult(
            passed=True,
            details={
                "path": str(resolved),
                "node_count": len(nodes),
                "edge_count": len(edges),
            },
        )

    # ------------------------------------------------------------------
    # Cycle detection: Kahn's algorithm (topological sort, BFS)
    # ------------------------------------------------------------------
    # Build adjacency list (successors) and in-degree map over the union
    # of declared nodes and any implicitly referenced nodes from edges.
    all_nodes: set[str] = nodes | {src for src, _ in edges} | {dst for _, dst in edges}

    in_degree: dict[str, int] = {n: 0 for n in all_nodes}
    successors: dict[str, list[str]] = {n: [] for n in all_nodes}

    for src, dst in edges:
        successors[src].append(dst)
        in_degree[dst] += 1

    queue: deque[str] = deque(n for n in all_nodes if in_degree[n] == 0)
    processed_count: int = 0

    while queue:
        node = queue.popleft()
        processed_count += 1
        for succ in successors[node]:
            in_degree[succ] -= 1
            if in_degree[succ] == 0:
                queue.append(succ)

    if processed_count == len(all_nodes):
        # All nodes processed → graph is acyclic
        return PredicateResult(
            passed=True,
            details={
                "path": str(resolved),
                "node_count": len(all_nodes),
                "edge_count": len(edges),
            },
        )

    # ------------------------------------------------------------------
    # Cycle present: collect unprocessed nodes for diagnostics
    # ------------------------------------------------------------------
    cycle_nodes: list[str] = sorted(
        n for n in all_nodes if in_degree[n] > 0
    )

    return PredicateResult(
        passed=False,
        failure_category=CROSS_ARTIFACT_INCONSISTENCY,
        reason=(
            f"dependency_map contains a directed cycle.  "
            f"{len(cycle_nodes)} node(s) could not be topologically sorted: "
            f"{cycle_nodes}.  Inspect these nodes and their outgoing edges in "
            f"dependency_map to identify and break the cycle."
        ),
        details={
            "path": str(resolved),
            "node_count": len(all_nodes),
            "edge_count": len(edges),
            "cycle_nodes": cycle_nodes,
            "processed_count": processed_count,
            "remaining_count": len(all_nodes) - processed_count,
        },
    )
