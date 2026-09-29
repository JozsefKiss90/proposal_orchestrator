"""
Dev-graph bounded evidence packages — task-scoped, policy-bound, immutable.

An operator or agent asks for the evidence around one task (a node id) under
one view and one budget. The builder returns an immutable :class:`Package`:
the included items and a manifest that says what was included and why, what
was excluded and why, what is unresolved, and whether the package is complete.

Selection, in order, all deterministic:

1. **Refuse** a stale snapshot id, a stale policy version, an unknown view, a
   task that is not in the snapshot, or a non-positive budget.
2. **Apply the policy before expansion.** Every node is classified once by
   :meth:`ViewPolicy.refusal`; a refused node is never a step in a traversal,
   and an edge whose predicate the view does not permit is never followed.
   A view that hides superseded versions also refuses every node derived
   from one, with detail ``superseded_version:<snapshot id>``. Which
   snapshots are superseded is a fact of the whole graph, so the builder
   computes it here (:func:`runner.dev_graph.builder.superseded_versions`)
   rather than in the per-node policy lookup.
3. **Expand** from the seed over the permitted graph, breadth first, to the
   view's maximum depth. Each reached node records the edges traversed.
4. **Mark mandatory** the nodes reached from the seed through the mandatory
   predicates only (:data:`MANDATORY_PREDICATES`): the responsible party,
   consumed tasks, constraints, validators, and the passages that address the
   task from elsewhere in the candidate (cross-section dependencies).
   ``addresses`` is followed only towards the node being addressed, and the
   walk steps from a task up to its work package (``contributes_to``, task
   to work package only) so the work package's constraints are reached. A
   mandatory item's recorded path is this walk, not the shortest one.
5. **Fill the budget**: the seed, then mandatory items, then the rest, each
   group in ``(depth, id)`` order. An item that does not fit is excluded with
   reason ``over_budget``; a required one is also listed as unresolved. Any
   over-budget exclusion makes the package ``incomplete``, and so does a
   seed larger than the budget. Nothing is dropped silently, and the seed is
   always in the package.
6. **Record exclusions** for every node adjacent to an included node that is
   not itself included: ``policy_forbidden`` (with the refusal detail) or
   ``not_relevant`` (beyond the depth). Every exclusion names the record
   path the node came from, so an operator can find what was kept out.
7. **List unresolved items** from the whole snapshot: claims whose declared
   status is Unresolved, and two rule-based contradictions (two current
   versions of one document; an approved claim that is Unresolved).

The package hash is the content hash of the items. The package id hashes the
request and the package hash. No wall-clock field anywhere.

Constitutional authority:
    Subordinate to CLAUDE.md. Reads a snapshot in memory, writes only through
    :func:`write_package` under Tier 4 dev_graph/packages, evaluates no gate,
    invokes no Claude, invents no facts (§13.3).
"""

from __future__ import annotations

import json
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from runner.atomic_write import atomic_write_json
from runner.claim_status import worst_status
from runner.dev_graph.builder import (
    Snapshot,
    build_snapshot,
    derived_from_version,
    superseded_versions,
)
from runner.dev_graph.identity import HASH_PREFIX, canonical_json, content_hash
from runner.dev_graph.policies import POLICY_VERSION, VIEW_POLICIES, ViewPolicy
from runner.dev_graph.schema import CURRENT_DOCUMENT_STATES, DevGraphError, edge_label

PACKAGE_SCHEMA_ID = "orch.dev_graph.evidence_package.v1"
MANIFEST_SCHEMA_ID = "orch.dev_graph.package_manifest.v1"

#: Repo-relative directory holding one immutable package per package id.
PACKAGES_REL = "docs/tier4_orchestration_state/dev_graph/packages"
#: Repo-relative operator request the writer component reads.
PACKAGE_REQUEST_REL = "docs/tier4_orchestration_state/dev_graph/package_request.json"

COMPLETENESS: frozenset[str] = frozenset({"complete", "incomplete"})
EXCLUSION_REASONS: frozenset[str] = frozenset({"policy_forbidden", "over_budget", "not_relevant"})
SELECTION_REASONS: frozenset[str] = frozenset({"seed", "mandatory", "expansion"})

#: Predicates whose neighbours are required regardless of ranking: who does
#: the work, what must exist first, what constrains it, what validates it,
#: and which passages address it.
MANDATORY_PREDICATES: frozenset[str] = frozenset(
    {"assigned_to", "consumes", "constrained_by", "validated_by", "addresses"}
)


def _mandatory_step(pred: str, forward: bool, from_type: str) -> bool:
    """Whether one traversal step belongs to the mandatory walk.

    ``addresses`` counts only against its direction (from the addressed node
    to the passage), so a passage never pulls in everything else it names.
    ``contributes_to`` counts only from a task up to its work package, so the
    work package's constraints are required and its siblings are not.
    """
    if pred == "addresses":
        return not forward
    if pred == "contributes_to":
        return forward and from_type == "task"
    return pred in MANDATORY_PREDICATES

_CHARS_PER_TOKEN = 4
_SHORT_HEX = 16


def estimate_cost(content: Any) -> int:
    """Deterministic size estimate of *content*: ``ceil(len(canonical)/4)``, min 1."""
    n = len(canonical_json(content))
    return max(1, (n + _CHARS_PER_TOKEN - 1) // _CHARS_PER_TOKEN)


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Package:
    """An immutable evidence package: the items and their manifest."""

    manifest: dict[str, Any]
    items: tuple[dict[str, Any], ...]

    @property
    def package_id(self) -> str:
        return self.manifest["package_id"]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_id": PACKAGE_SCHEMA_ID,
            "package_id": self.package_id,
            "package_hash": self.manifest["package_hash"],
            "items": list(self.items),
        }

    def to_json_bytes(self) -> bytes:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False).encode("utf-8")


# ---------------------------------------------------------------------------
# Request validation
# ---------------------------------------------------------------------------


def _refuse(kind: str, offender: str, message: str) -> DevGraphError:
    return DevGraphError(kind, offender, message)


def _check_request(
    snapshot: Snapshot,
    task: Any,
    view: Any,
    budget: Any,
    policy_version: Any,
    expected_snapshot_id: Any,
    project: Any,
    profile_version: Any,
) -> ViewPolicy:
    if view not in VIEW_POLICIES:
        raise _refuse("unknown_view", str(view), f"view {view!r} is not in {sorted(VIEW_POLICIES)}")
    if policy_version != POLICY_VERSION:
        raise _refuse(
            "stale_policy",
            str(policy_version),
            f"requested policy version {policy_version!r} is not the current {POLICY_VERSION}",
        )
    if expected_snapshot_id != snapshot.snapshot_id:
        raise _refuse(
            "stale_snapshot",
            str(expected_snapshot_id),
            f"requested snapshot {expected_snapshot_id!r} does not match the current build "
            f"{snapshot.snapshot_id}",
        )
    if isinstance(budget, bool) or not isinstance(budget, int) or budget <= 0:
        raise _refuse("malformed_request", "budget", f"budget must be a positive integer, got {budget!r}")
    if not isinstance(task, str) or not task:
        raise _refuse("malformed_request", "task", "task must be a non-empty node id")
    if not any(n["id"] == task for n in snapshot.nodes):
        raise _refuse("malformed_request", task, f"task {task!r} is not a node of the snapshot")
    for name, value in (("project", project), ("profile_version", profile_version)):
        if not isinstance(value, str) or not value:
            raise _refuse("malformed_request", name, f"{name} must be a non-empty string")
    return VIEW_POLICIES[view]


# ---------------------------------------------------------------------------
# Expansion (pure)
# ---------------------------------------------------------------------------


def _expand(
    seed: str,
    adjacency: Mapping[str, list[tuple[str, str, str, bool]]],
    max_depth: int,
    *,
    mandatory_only: bool = False,
) -> dict[str, list[str]]:
    """Breadth-first over *adjacency* from *seed*; returns ``{id: path}``.

    *adjacency* maps a node to ``(predicate, neighbour, label, mandatory)``
    tuples in sorted order, *mandatory* being true when the step belongs to
    the mandatory walk (:func:`_mandatory_step`). With *mandatory_only* the
    walk follows those steps only.
    """
    paths: dict[str, list[str]] = {seed: []}
    queue: deque[tuple[str, int]] = deque([(seed, 0)])
    while queue:
        node, depth = queue.popleft()
        if depth >= max_depth:
            continue
        for pred, other, label, mandatory in adjacency.get(node, []):
            if mandatory_only and not mandatory:
                continue
            if other in paths:
                continue
            paths[other] = paths[node] + [label]
            queue.append((other, depth + 1))
    return paths


def _item_span(node: dict[str, Any]) -> dict[str, int] | None:
    content = node["content"]
    if node["type"] == "passage" and isinstance(content.get("span"), dict):
        return dict(content["span"])
    if node["type"] == "source_span":
        return {"start": content["start"], "end": content["end"]}
    return None


# ---------------------------------------------------------------------------
# Unresolved items (pure, whole snapshot)
# ---------------------------------------------------------------------------


def _unresolved_items(snapshot: Snapshot) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    current_by_doc: dict[str, list[str]] = {}
    for n in snapshot.nodes:
        c = n["content"]
        if n["type"] == "claim":
            if c.get("declared_status") == "Unresolved":
                out.append(
                    {
                        "kind": "unresolved_claim",
                        "id": n["id"],
                        "declared_status": "Unresolved",
                        "approval": c.get("approval"),
                    }
                )
                if c.get("approval") == "approved":
                    out.append(
                        {
                            "kind": "contradiction",
                            "rule": "approved_but_unresolved",
                            "ids": [n["id"]],
                        }
                    )
        elif n["type"] == "artifact_version" and c.get("state") in CURRENT_DOCUMENT_STATES:
            doc = c.get("document_id")
            if isinstance(doc, str):
                current_by_doc.setdefault(doc, []).append(n["id"])
    for doc, ids in sorted(current_by_doc.items()):
        if len(ids) > 1:
            out.append(
                {
                    "kind": "contradiction",
                    "rule": "two_current_versions",
                    "document_id": doc,
                    "ids": sorted(ids),
                }
            )
    return out


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def build_package(
    snapshot: Snapshot,
    *,
    task: str,
    view: str,
    budget: int,
    policy_version: str,
    expected_snapshot_id: str,
    project: str,
    profile_version: str,
) -> Package:
    """Build the evidence package for *task* under *view* and *budget*.

    Raises :class:`DevGraphError` with kind ``stale_snapshot``,
    ``stale_policy``, ``unknown_view``, ``policy_forbidden`` (the task itself
    is not visible under the view) or ``malformed_request``. Deterministic:
    identical inputs yield an identical manifest and package hash.
    """
    policy = _check_request(
        snapshot, task, view, budget, policy_version, expected_snapshot_id, project, profile_version
    )
    nodes = {n["id"]: n for n in snapshot.nodes}
    refusals = {nid: policy.refusal(n) for nid, n in nodes.items()}
    if policy.hide_superseded_versions:
        stale = superseded_versions(snapshot)
        for nid, n in nodes.items():
            origin = derived_from_version(n)
            if refusals[nid] is None and origin in stale:
                refusals[nid] = f"superseded_version:{origin}"
    if refusals[task] is not None:
        raise _refuse(
            "policy_forbidden", task, f"task {task!r} is not visible under view {view!r}: {refusals[task]}"
        )

    # Adjacency over every edge (for exclusion records) and over the permitted
    # graph only (for expansion). Policy is applied here, before any traversal.
    all_adj: dict[str, list[tuple[str, str, str, bool]]] = {}
    permitted_adj: dict[str, list[tuple[str, str, str, bool]]] = {}
    for e in snapshot.edges:
        s, p, t = e["source"]["id"], e["predicate"], e["target"]["id"]
        label = edge_label(s, p, t)
        for a, b, forward in ((s, t, True), (t, s, False)):
            step = (p, b, label, _mandatory_step(p, forward, nodes[a]["type"]))
            all_adj.setdefault(a, []).append(step)
            if p in policy.permitted_traversals and refusals[a] is None and refusals[b] is None:
                permitted_adj.setdefault(a, []).append(step)
    for adj in (all_adj, permitted_adj):
        for lst in adj.values():
            lst.sort()

    reached = _expand(task, permitted_adj, policy.max_depth)
    mandatory = _expand(task, permitted_adj, policy.max_depth, mandatory_only=True)
    mandatory.pop(task)
    # One path per node: the mandatory walk for a required item, the
    # shortest permitted walk otherwise.
    paths = {**reached, **mandatory}

    # Ranking: seed, then mandatory, then expansion; (depth, id) within a group.
    def _rank(ids: list[str]) -> list[str]:
        return sorted(ids, key=lambda i: (len(paths[i]), i))

    ordered: list[tuple[str, str]] = [(task, "seed")]
    ordered += [(i, "mandatory") for i in _rank(list(mandatory))]
    ordered += [(i, "expansion") for i in _rank([i for i in reached if i != task and i not in mandatory])]

    included: list[dict[str, Any]] = []
    items: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    spent = 0
    for nid, reason in ordered:
        node = nodes[nid]
        cost = estimate_cost(node["content"])
        if reason != "seed" and spent + cost > budget:
            exclusions.append(
                {
                    "id": nid,
                    "type": node["type"],
                    "version": node["version"],
                    "path": node["path"],
                    "reason": "over_budget",
                    "required": reason == "mandatory",
                    "detail": f"cost {cost} exceeds remaining budget {budget - spent}",
                }
            )
            if reason == "mandatory":
                unresolved.append({"kind": "required_over_budget", "id": nid, "cost": cost})
            continue
        if reason == "seed" and cost > budget:
            unresolved.append({"kind": "seed_over_budget", "id": nid, "cost": cost})
        spent += cost
        item: dict[str, Any] = {
            "id": nid,
            "type": node["type"],
            "version": node["version"],
            "reason": reason,
            "path": list(paths[nid]),
            "depth": len(paths[nid]),
            "cost": cost,
        }
        span = _item_span(node)
        if span is not None:
            item["span"] = span
        if node["type"] == "claim":
            item["declared_status"] = node["content"].get("declared_status")
        included.append(item)
        items.append(
            {"id": nid, "type": node["type"], "version": node["version"], "content": node["content"]}
        )

    included_ids = {i["id"] for i in included}
    seen_excluded = {e["id"] for e in exclusions}
    for nid in sorted(included_ids):
        for pred, other, _label, _mandatory in all_adj.get(nid, []):
            if other in included_ids or other in seen_excluded:
                continue
            refusal = refusals[other]
            if refusal is not None:
                reason, detail = "policy_forbidden", refusal
            elif pred not in policy.permitted_traversals:
                reason, detail = "policy_forbidden", f"traversal_not_permitted:{pred}"
            else:
                reason, detail = "not_relevant", "beyond_max_depth"
            exclusions.append(
                {
                    "id": other,
                    "type": nodes[other]["type"],
                    "version": nodes[other]["version"],
                    "path": nodes[other]["path"],
                    "reason": reason,
                    "required": False,
                    "detail": detail,
                }
            )
            seen_excluded.add(other)
    exclusions.sort(key=lambda e: (e["reason"], e["id"]))

    unresolved += _unresolved_items(snapshot)
    unresolved.sort(key=lambda u: (u["kind"], u.get("id", ""), json.dumps(u.get("ids", []))))

    package_hash = content_hash(items)
    request = {
        "project": project,
        "task": task,
        "view": view,
        "profile_version": profile_version,
        "snapshot_id": snapshot.snapshot_id,
        "policy_version": POLICY_VERSION,
        "budget": budget,
    }
    manifest: dict[str, Any] = {
        "schema_id": MANIFEST_SCHEMA_ID,
        "package_id": content_hash({**request, "package_hash": package_hash}),
        **request,
        "included": included,
        "mandatory_dependencies": [
            {"id": i, "type": nodes[i]["type"], "version": nodes[i]["version"], "path": list(mandatory[i])}
            for i in _rank(list(mandatory))
        ],
        "exclusions": exclusions,
        "unresolved": unresolved,
        # worst_status returns the runtime's lowercase form; the manifest
        # keeps the §12.2 title-case spelling the claims themselves carry.
        "worst_declared_status": worst_status(
            i["declared_status"] for i in included if i["type"] == "claim"
        ).capitalize(),
        "completeness": (
            "incomplete"
            if any(e["reason"] == "over_budget" for e in exclusions)
            or any(u["kind"] == "seed_over_budget" for u in unresolved)
            else "complete"
        ),
        "package_hash": package_hash,
    }
    return Package(manifest=manifest, items=tuple(items))


# ---------------------------------------------------------------------------
# The registered writer
# ---------------------------------------------------------------------------

_REQUEST_KEYS = ("task", "view", "budget", "project", "profile_version", "policy_version", "snapshot_id")


def read_package_request(repo_root: Path) -> dict[str, Any]:
    """Read and shape-check the operator request at :data:`PACKAGE_REQUEST_REL`."""
    path = Path(repo_root) / PACKAGE_REQUEST_REL
    if not path.is_file():
        raise _refuse("malformed_request", PACKAGE_REQUEST_REL, "package request file not found")
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        raise _refuse("malformed_request", PACKAGE_REQUEST_REL, f"unreadable JSON: {exc}") from exc
    if not isinstance(raw, dict):
        raise _refuse("malformed_request", PACKAGE_REQUEST_REL, "expected a JSON object")
    missing = [k for k in _REQUEST_KEYS if k not in raw]
    if missing:
        raise _refuse("malformed_request", PACKAGE_REQUEST_REL, f"missing keys {missing}")
    return {k: raw[k] for k in _REQUEST_KEYS}


def write_package(repo_root: Path) -> list[Path]:
    """Build the snapshot and the requested package; write manifest and package.

    Returns the two absolute paths written. The package directory is named by
    the package id, so the same request over the same records lands on the
    same path with the same bytes.
    """
    root = Path(repo_root)
    req = read_package_request(root)
    snapshot = build_snapshot(root)
    pkg = build_package(
        snapshot,
        task=req["task"],
        view=req["view"],
        budget=req["budget"],
        policy_version=req["policy_version"],
        expected_snapshot_id=req["snapshot_id"],
        project=req["project"],
        profile_version=req["profile_version"],
    )
    base = root / PACKAGES_REL / pkg.package_id[len(HASH_PREFIX):][:_SHORT_HEX]
    manifest_path = base / "manifest.json"
    package_path = base / "package.json"
    atomic_write_json(pkg.manifest, manifest_path)
    atomic_write_json(pkg.to_dict(), package_path)
    return [manifest_path, package_path]


def run_package_manifest_writer(run_id: str, repo_root: Path) -> list[Path]:
    """Component adapter: ``(run_id, repo_root) -> written``. The run id does
    not enter the artifacts."""
    del run_id
    return write_package(repo_root)
