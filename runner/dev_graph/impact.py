"""
Dev-graph shadow impact planner — what an approved change affects, and why.

The planner takes the snapshot before an approved change, the snapshot after
it, and the durable run records, and returns an advisory plan. Every entry
names one affected thing (a changed record, a passage, a piece of evidence,
an artifact, a check), a reason path, a hit kind and one action from the
closed set :data:`ACTIONS`.

Rules, all deterministic and all lookups over declared data:

* **Origins** are the nodes whose own content changed, was added or was
  removed (:func:`runner.dev_graph.changes.change_set`). A node whose
  version moved only because a nested record changed is not an origin. The
  endpoints of an added or removed edge are origins when neither endpoint
  is one already.
* **Reach** is a breadth-first walk from the origins over the union of the
  before and after edges under the ``change_impact_planning`` view policy:
  its permitted types, permitted traversals, forbidden types and tags, and
  its depth, applied before expansion as the package builder applies them.
  A removed edge is still walked, so the participant who lost a task is
  reached. The walk enters a document
  container (an ``artifact_version`` node) but does not continue out of it
  unless the container is itself an origin: reaching the document means the
  document is affected, and its other passages are not affected through it.
  Every other node expands, so a passage that addresses the changed task's
  work package is reached and listed with that route.
* **Reason path**: ``changed:<origin>``, then the edge labels traversed,
  then ``input_of:<record>`` for a run record. Never empty.
* **Hit**: ``origin``; ``direct`` for an endpoint of an added or removed
  edge; ``transitive`` for anything reached over unchanged edges only;
  ``coverage_unknown`` for a run record whose declared inputs are absent or
  whose declared inputs or dependency edges no longer exist after the
  change.
* **Action**: an origin and any reached passage, evidence or artifact
  version is ``reconsider`` (wording is a human decision). A run record hit
  directly or with unknown coverage is ``rerun``. A run record hit only
  transitively is ``reuse-under-policy``: its result may be retained only
  when an explicit policy says so, never by silence.
* **Newly relevant sources**: a source reached from an origin that no run
  record lists among its inputs or its package is flagged, so a change in
  selection scope is not missed.

The planner refuses a missing or malformed snapshot and malformed run
records. It never narrows: a broken index is a refusal, not a smaller plan.

Shadow mode. The plan is advisory. The planner reads no scheduler state,
writes no reuse metadata, and no runtime layer consumes it. The whole-Tier-3
reuse fingerprint stays the sole authority over what executes.

Constitutional authority:
    Subordinate to CLAUDE.md. Writes only the advisory plan under Tier 4
    dev_graph/impact_plans through :func:`write_impact_plan`. Evaluates no
    gate, invokes no Claude, invents no facts (§13.3).
"""

from __future__ import annotations

import json
import re
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from runner.atomic_write import atomic_write_json
from runner.dev_graph.builder import Snapshot
from runner.dev_graph.changes import (
    change_set,
    label_of,
    load_snapshot,
    read_change_record,
)
from runner.dev_graph.identity import HASH_PREFIX, content_hash
from runner.dev_graph.policies import POLICY_VERSION, VIEW_POLICIES, ViewPolicy
from runner.dev_graph.schema import DevGraphError

PLAN_SCHEMA_ID = "orch.dev_graph.impact_plan.v1"
RUN_RECORDS_SCHEMA_ID = "orch.dev_graph.run_records.v1"

_DEV_GRAPH = "docs/tier4_orchestration_state/dev_graph"
#: One immutable advisory plan per plan id.
IMPACT_PLANS_REL = f"{_DEV_GRAPH}/impact_plans"
#: The operator request the writer component reads: ``{"change_id": ...}``.
IMPACT_REQUEST_REL = f"{_DEV_GRAPH}/impact_request.json"
#: The durable run records: artifacts and checks with their declared inputs.
RUN_RECORDS_REL = f"{_DEV_GRAPH}/run_records.json"

ACTIONS: frozenset[str] = frozenset({"rerun", "reuse-under-policy", "reconsider"})
HITS: frozenset[str] = frozenset({"origin", "direct", "transitive", "coverage_unknown"})
ENTRY_KINDS: frozenset[str] = frozenset({"record", "passage", "evidence", "artifact", "check"})
RECORD_KINDS: frozenset[str] = frozenset({"artifact", "check"})

#: Reached node types that become plan entries, and the entry kind each gets.
_REACHED_KINDS: Mapping[str, str] = {
    "passage": "passage",
    "claim": "evidence",
    "commitment": "evidence",
    "artifact_version": "artifact",
}

#: Container types the walk enters but does not continue out of (unless the
#: container is an origin). A document is reached as a whole; its unrelated
#: passages are not reached through it.
_NO_EXPANSION_TYPES: frozenset[str] = frozenset({"artifact_version"})

_PLANNING_VIEW = "change_impact_planning"
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
_SHORT_HEX = 16


@dataclass(frozen=True)
class ImpactPlan:
    """An immutable advisory plan with a content-derived identity."""

    plan_id: str
    change_id: str
    before_snapshot_id: str
    after_snapshot_id: str
    run_records_hash: str
    change_set: dict[str, Any]
    origins: list[str]
    entries: list[dict[str, Any]]
    newly_relevant_sources: list[dict[str, Any]]

    @property
    def nothing_changed(self) -> bool:
        return plan_nothing_changed(self.change_set, self.origins)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_id": PLAN_SCHEMA_ID,
            "plan_id": self.plan_id,
            "advisory": True,
            "mode": "shadow",
            "change_id": self.change_id,
            "before_snapshot_id": self.before_snapshot_id,
            "after_snapshot_id": self.after_snapshot_id,
            "run_records_hash": self.run_records_hash,
            "policy_version": POLICY_VERSION,
            "max_depth": VIEW_POLICIES[_PLANNING_VIEW].max_depth,
            "nothing_changed": self.nothing_changed,
            "change_set": self.change_set,
            "origins": list(self.origins),
            "entries": list(self.entries),
            "newly_relevant_sources": list(self.newly_relevant_sources),
        }


# ---------------------------------------------------------------------------
# Run records (validation is pure; reading is the one file read)
# ---------------------------------------------------------------------------


def _refuse(kind: str, offender: str, message: str) -> DevGraphError:
    return DevGraphError(kind, offender, message)


def _id_list(raw: Any, where: str, key: str) -> list[str] | None:
    if raw is None:
        return None
    if not isinstance(raw, list) or not all(isinstance(v, str) and v for v in raw):
        raise _refuse("malformed_record", where, f"{where}: {key!r} must be a list of ids or null")
    return list(raw)


def normalise_run_records(raw: Any, where: str) -> list[dict[str, Any]]:
    """Validate the run records' own shape and return them canonically.

    Each record: ``record_id`` (plain id), ``kind`` (:data:`RECORD_KINDS`),
    ``path`` (string), ``inputs`` (list of node ids, or null for unknown
    coverage), optional ``dependency_edges`` (edge labels) and optional
    ``package`` (``{"package_id", "included": [ids]}``). Pure.
    """
    if not isinstance(raw, list):
        raise _refuse("malformed_record", where, f"{where}: run records must be a list")
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for i, rec in enumerate(raw):
        if not isinstance(rec, dict):
            raise _refuse("malformed_record", where, f"{where}: records[{i}] is not an object")
        rid = rec.get("record_id")
        if not isinstance(rid, str) or not _ID_RE.match(rid):
            raise _refuse("malformed_record", where, f"{where}: records[{i}] has no plain record_id")
        if rid in seen:
            raise _refuse("malformed_record", rid, f"record_id {rid!r} declared more than once")
        seen.add(rid)
        kind = rec.get("kind")
        if kind not in RECORD_KINDS:
            raise _refuse("malformed_record", rid, f"{rid}: kind {kind!r} is not in {sorted(RECORD_KINDS)}")
        path = rec.get("path", "")
        if not isinstance(path, str):
            raise _refuse("malformed_record", rid, f"{rid}: path must be a string")
        package = rec.get("package")
        included: list[str] = []
        package_id: str | None = None
        if package is not None:
            if not isinstance(package, dict) or not isinstance(package.get("package_id"), str):
                raise _refuse("malformed_record", rid, f"{rid}: package must be an object with a package_id")
            package_id = package["package_id"]
            included = _id_list(package.get("included", []), rid, "package.included") or []
        out.append(
            {
                "record_id": rid,
                "kind": kind,
                "path": path,
                "inputs": _id_list(rec.get("inputs"), rid, "inputs"),
                "dependency_edges": _id_list(rec.get("dependency_edges", []), rid, "dependency_edges") or [],
                "package": None if package_id is None else {"package_id": package_id, "included": included},
            }
        )
    return sorted(out, key=lambda r: r["record_id"])


def read_run_records(repo_root: Path) -> list[dict[str, Any]]:
    """Read and validate :data:`RUN_RECORDS_REL`. A missing file is a refusal:
    without run records the planner cannot say what an artifact depends on."""
    path = Path(repo_root) / RUN_RECORDS_REL
    if not path.is_file():
        raise _refuse("malformed_request", RUN_RECORDS_REL, "run records file not found")
    try:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        raise _refuse("malformed_record", RUN_RECORDS_REL, f"unreadable JSON: {exc}") from exc
    if not isinstance(doc, dict) or doc.get("schema_id") != RUN_RECORDS_SCHEMA_ID:
        raise _refuse("malformed_record", RUN_RECORDS_REL, f"not a {RUN_RECORDS_SCHEMA_ID} document")
    return normalise_run_records(doc.get("records"), RUN_RECORDS_REL)


# ---------------------------------------------------------------------------
# Reach (pure)
# ---------------------------------------------------------------------------


def _adjacency(
    before: Snapshot, after: Snapshot, policy: ViewPolicy, nodes: Mapping[str, dict[str, Any]]
) -> dict[str, list[tuple[str, str]]]:
    """``{node: [(edge label, neighbour)]}`` over the union of both edge sets,
    sorted, with the policy applied before any traversal: an edge whose
    predicate the view does not permit, or whose endpoint the view refuses,
    is never a step."""
    refusals = {nid: policy.refusal(n) for nid, n in nodes.items()}
    adj: dict[str, list[tuple[str, str]]] = {}
    seen: set[str] = set()
    for e in (*before.edges, *after.edges):
        label = label_of(e)
        if label in seen:
            continue
        seen.add(label)
        if e["predicate"] not in policy.permitted_traversals:
            continue
        if refusals[e["source"]["id"]] is not None or refusals[e["target"]["id"]] is not None:
            continue
        adj.setdefault(e["source"]["id"], []).append((label, e["target"]["id"]))
        adj.setdefault(e["target"]["id"], []).append((label, e["source"]["id"]))
    for lst in adj.values():
        lst.sort()
    return adj


def _reach(
    origins: Mapping[str, list[str]],
    adj: Mapping[str, list[tuple[str, str]]],
    max_depth: int,
    no_expansion: frozenset[str],
) -> dict[str, list[str]]:
    """Multi-source breadth-first walk; ``{node: reason path}``, shortest first,
    ties broken by origin id then edge label order. Nodes in *no_expansion*
    are reached but not expanded from unless they are origins."""
    paths: dict[str, list[str]] = {o: list(p) for o, p in sorted(origins.items())}
    queue: deque[tuple[str, int]] = deque((o, 0) for o in sorted(origins))
    while queue:
        node, depth = queue.popleft()
        if depth >= max_depth or (node in no_expansion and node not in origins):
            continue
        for label, other in adj.get(node, []):
            if other in paths:
                continue
            paths[other] = paths[node] + [label]
            queue.append((other, depth + 1))
    return paths


# ---------------------------------------------------------------------------
# Plan identity (shared with the shadow comparison's reader)
# ---------------------------------------------------------------------------

#: The plan fields the plan id hashes, in order. ``nothing_changed``,
#: ``max_depth`` and the change set are derived and stay out of the hash.
PLAN_IDENTITY_FIELDS: tuple[str, ...] = (
    "change_id",
    "before_snapshot_id",
    "after_snapshot_id",
    "run_records_hash",
    "policy_version",
    "entries",
    "newly_relevant_sources",
)


def plan_identity(doc: Mapping[str, Any]) -> str:
    """The content-derived plan id of a plan document (or of the fields a
    plan is built from). The one definition, so a stored plan is checked
    against its id by the same rule that minted it."""
    return content_hash({k: doc.get(k) for k in PLAN_IDENTITY_FIELDS})


def plan_nothing_changed(change_set: Mapping[str, Any], origins: list[str]) -> bool:
    """Whether a change set with these origins is empty."""
    edges = change_set.get("edges", {})
    return not origins and not edges.get("added") and not edges.get("removed")


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def _check_snapshot(snap: Any, which: str) -> Snapshot:
    if not isinstance(snap, Snapshot):
        raise _refuse("malformed_snapshot", which, f"{which} snapshot is not a Snapshot ({type(snap).__name__})")
    if snap.snapshot_id != Snapshot.from_graph(list(snap.nodes), list(snap.edges), snap.inputs).snapshot_id:
        raise _refuse("malformed_snapshot", which, f"{which} snapshot id does not match its content")
    return snap


def plan_impact(
    before: Snapshot,
    after: Snapshot,
    run_records: list[dict[str, Any]],
    *,
    change_id: str,
) -> ImpactPlan:
    """The advisory plan for the change from *before* to *after*.

    Raises :class:`DevGraphError` with kind ``malformed_snapshot`` when either
    snapshot is not a valid :class:`Snapshot`, ``malformed_record`` when the
    run records are malformed, ``malformed_request`` on a bad change id.
    Deterministic: identical inputs yield an identical plan and plan id.
    """
    before = _check_snapshot(before, "before")
    after = _check_snapshot(after, "after")
    if not isinstance(change_id, str) or not _ID_RE.match(change_id):
        raise _refuse("malformed_request", str(change_id), "change_id is not a plain identifier")
    records = normalise_run_records(run_records, "run_records")

    cs = change_set(before, after)
    b_nodes = {n["id"]: n for n in before.nodes}
    a_nodes = {n["id"]: n for n in after.nodes}
    nodes = {**b_nodes, **a_nodes}

    origins: dict[str, list[str]] = {}
    for nid in cs["nodes"]["added"] + cs["nodes"]["removed"]:
        origins[nid] = [f"changed:{nid}"]
    for c in cs["nodes"]["changed"]:
        if c["kind"] == "direct":
            origins[c["id"]] = [f"changed:{c['id']}"]
    changed_edges = cs["edges"]["added"] + cs["edges"]["removed"]
    edge_endpoints: set[str] = set()
    for e in changed_edges:
        ends = (e["source"], e["target"])
        edge_endpoints.update(ends)
        if not any(x in origins for x in ends):
            for x in ends:
                origins.setdefault(x, [f"changed:{e['label']}"])

    policy = VIEW_POLICIES[_PLANNING_VIEW]
    no_expansion = frozenset(nid for nid, n in nodes.items() if n["type"] in _NO_EXPANSION_TYPES)
    reached = _reach(origins, _adjacency(before, after, policy, nodes), policy.max_depth, no_expansion)
    # Nodes the change touched itself: an origin, or an endpoint of a changed edge.
    touched = set(origins) | edge_endpoints

    def _hit(nid: str) -> str:
        if nid in origins:
            return "origin"
        return "direct" if nid in touched else "transitive"

    entries: list[dict[str, Any]] = []
    for nid, path in reached.items():
        node = nodes[nid]
        if nid in origins:
            kind = "record"
        else:
            kind = _REACHED_KINDS.get(node["type"], "")
            if not kind:
                continue
        entries.append(
            {
                "kind": kind,
                "id": nid,
                "type": node["type"],
                "version": node["version"],
                "hit": _hit(nid),
                "action": "reconsider",
                "reason_path": list(path),
                "detail": "removed" if nid in cs["nodes"]["removed"] else "",
            }
        )

    after_labels = {label_of(e) for e in after.edges}
    known_sources: set[str] = set()
    for rec in records:
        rid = rec["record_id"]
        known_sources.update(rec["inputs"] or [])
        if rec["package"]:
            known_sources.update(rec["package"]["included"])
        unknown: list[str] = []
        if rec["inputs"] is None:
            unknown.append("no declared inputs")
        else:
            unknown += [f"input {i} absent from the after snapshot" for i in rec["inputs"] if i not in a_nodes]
        unknown += [f"dependency edge {d} absent from the after snapshot" for d in rec["dependency_edges"] if d not in after_labels]
        if unknown:
            entries.append(
                {
                    "kind": rec["kind"],
                    "id": rid,
                    "path": rec["path"],
                    "hit": "coverage_unknown",
                    "action": "rerun",
                    "reason_path": [f"coverage_unknown:{rid}"],
                    "detail": "; ".join(unknown),
                }
            )
            continue
        hits = [i for i in rec["inputs"] or [] if i in reached]
        if not hits:
            continue
        hit = "direct" if any(i in touched for i in hits) else "transitive"
        candidates = [i for i in hits if i in touched] if hit == "direct" else hits
        via = min(candidates, key=lambda i: (len(reached[i]), i))
        entries.append(
            {
                "kind": rec["kind"],
                "id": rid,
                "path": rec["path"],
                "hit": hit,
                "action": "rerun" if hit == "direct" else "reuse-under-policy",
                "reason_path": list(reached[via]) + [f"input_of:{rid}"],
                "detail": "inputs hit: " + ", ".join(sorted(hits)),
            }
        )

    newly_relevant = [
        {"id": nid, "version": nodes[nid]["version"], "reason_path": list(path)}
        for nid, path in reached.items()
        if nodes[nid]["type"] == "source" and nid not in known_sources
    ]
    newly_relevant.sort(key=lambda s: s["id"])
    entries.sort(key=lambda e: (e["kind"], e["id"]))

    run_records_hash = content_hash(records)
    plan_id = plan_identity(
        {
            "change_id": change_id,
            "before_snapshot_id": before.snapshot_id,
            "after_snapshot_id": after.snapshot_id,
            "run_records_hash": run_records_hash,
            "policy_version": POLICY_VERSION,
            "entries": entries,
            "newly_relevant_sources": newly_relevant,
        }
    )
    return ImpactPlan(
        plan_id=plan_id,
        change_id=change_id,
        before_snapshot_id=before.snapshot_id,
        after_snapshot_id=after.snapshot_id,
        run_records_hash=run_records_hash,
        change_set=cs,
        origins=sorted(origins),
        entries=entries,
        newly_relevant_sources=newly_relevant,
    )


# ---------------------------------------------------------------------------
# The registered writer
# ---------------------------------------------------------------------------


def read_impact_request(repo_root: Path) -> str:
    """The change id named by :data:`IMPACT_REQUEST_REL`."""
    path = Path(repo_root) / IMPACT_REQUEST_REL
    if not path.is_file():
        raise _refuse("malformed_request", IMPACT_REQUEST_REL, "impact request file not found")
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        raise _refuse("malformed_request", IMPACT_REQUEST_REL, f"unreadable JSON: {exc}") from exc
    if not isinstance(raw, dict) or not isinstance(raw.get("change_id"), str):
        raise _refuse("malformed_request", IMPACT_REQUEST_REL, "expected an object with a change_id")
    return raw["change_id"]


def write_impact_plan(repo_root: Path) -> list[Path]:
    """Plan the change named by the request and write the advisory plan.

    Returns the one absolute path written. The plan directory is named by
    the first sixteen hex characters of the plan id (as the package writer
    names its directories), so the same change over the same records lands
    on the same path with the same bytes. Refuses before writing anything when a
    snapshot is missing or malformed.
    """
    root = Path(repo_root)
    change = read_change_record(root, read_impact_request(root))
    before = load_snapshot(root, change.before_snapshot_id)
    after = load_snapshot(root, change.after_snapshot_id)
    plan = plan_impact(before, after, read_run_records(root), change_id=change.change_id)
    target = root / IMPACT_PLANS_REL / plan.plan_id[len(HASH_PREFIX):][:_SHORT_HEX] / "plan.json"
    atomic_write_json(plan.to_dict(), target)
    return [target]


def run_impact_plan_writer(run_id: str, repo_root: Path) -> list[Path]:
    """Component adapter: ``(run_id, repo_root) -> written``. The run id does
    not enter the artifact."""
    del run_id
    return write_impact_plan(repo_root)
