"""
Dev-graph snapshot builder — a rebuildable index over authoritative records.

Reads the Tier 3 records that own project facts, derives typed nodes and
edges from their declared keys and structure, validates the result against
the closed schema, and returns an immutable :class:`Snapshot`. The graph owns
nothing: every node carries the record it indexes and the path it came from,
and a rebuild from the same records yields the same snapshot.

Identity model:

* A node id is the record's own declared key (``partner_id``, ``wp_id``,
  ``task_id`` ...). It is independent of file path and title.
* A node version is the content hash of the record.
* An edge references each endpoint as ``{"id", "version"}``.

Derived relationships (from record structure, no inference):

* ``work_package.lead_partner``             -> ``work_package assigned_to participant``
* ``task.responsible_partner``              -> ``task assigned_to participant``
* ``task.contributing_partners[]``          -> ``participant contributes_to task``
* task membership in a work package         -> ``task contributes_to work_package``
* ``work_package.objectives[]``             -> ``work_package contributes_to objective``
* ``task.dependencies[]``                   -> ``task consumes task``
* deliverable membership in a work package  -> ``work_package produces deliverable``
* ``deliverable.produced_by[]``             -> ``task produces deliverable``
* ``milestone.deliverables[]``              -> ``deliverable validated_by milestone``

Tier 3 declares no edges of its own: the edge set is recomputed on every
build from the fields above, so Tier 3 stays the single writer of each fact.

An empty or absent Tier 3 yields an explicit empty snapshot (``empty=True``),
never an error and never a fabricated node.

Constitutional authority:
    Subordinate to CLAUDE.md. Reads Tier 3, writes nothing, evaluates no
    gate, invents no facts (§13.3).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from runner.dev_graph.identity import content_hash, snapshot_id
from runner.dev_graph.schema import DevGraphError, validate_graph

SCHEMA_ID = "orch.dev_graph.snapshot.v1"

_TIER3 = Path("docs/tier3_project_instantiation")

PARTNERS_REL = _TIER3 / "consortium" / "partners.json"
OBJECTIVES_REL = _TIER3 / "architecture_inputs" / "objectives.json"
WP_SEED_REL = _TIER3 / "architecture_inputs" / "workpackage_seed.json"
MILESTONES_REL = _TIER3 / "architecture_inputs" / "milestones_seed.json"


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Snapshot:
    """An immutable graph snapshot with a content-derived identity."""

    snapshot_id: str
    nodes: tuple[dict[str, Any], ...]
    edges: tuple[dict[str, Any], ...]
    inputs: tuple[str, ...]
    """Repo-relative POSIX paths of every record file read, sorted."""

    @property
    def empty(self) -> bool:
        return not self.nodes

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_id": SCHEMA_ID,
            "snapshot_id": self.snapshot_id,
            "empty": self.empty,
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
            "inputs": list(self.inputs),
            "nodes": list(self.nodes),
            "edges": list(self.edges),
        }

    def to_json_bytes(self) -> bytes:
        """The on-disk serialisation (same options as ``atomic_write_json``)."""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False).encode("utf-8")


# ---------------------------------------------------------------------------
# Record reading
# ---------------------------------------------------------------------------


def _malformed(rel: Path, message: str) -> DevGraphError:
    return DevGraphError("malformed_record", rel.as_posix(), message)


def _read_records(
    repo_root: Path, rel: Path, list_key: str, inputs: list[str]
) -> list[dict[str, Any]]:
    """Read ``{list_key: [...]}`` from *rel*; an absent file yields ``[]``."""
    path = repo_root / rel
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        raise _malformed(rel, f"unreadable JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise _malformed(rel, "expected a JSON object")
    inputs.append(rel.as_posix())
    return list(_objects(data, list_key, rel, rel.name))


def _objects(rec: dict[str, Any], key: str, rel: Path, where: str) -> Iterator[dict[str, Any]]:
    """Yield the objects under ``rec[key]``; absent key yields nothing."""
    value = rec.get(key, [])
    if value is None:
        return
    if not isinstance(value, list):
        raise _malformed(rel, f"{where}.{key} must be a list")
    for i, item in enumerate(value):
        if not isinstance(item, dict):
            raise _malformed(rel, f"{where}.{key}[{i}] is not an object")
        yield item


def _key(rec: dict[str, Any], key: str, rel: Path, where: str) -> str:
    value = rec.get(key)
    if not isinstance(value, str) or not value.strip():
        raise _malformed(rel, f"{where} has no non-empty {key!r} (its declared key)")
    return value


def _ids(rec: dict[str, Any], key: str, rel: Path, where: str) -> list[str]:
    value = rec.get(key, [])
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise _malformed(rel, f"{where}.{key} must be a list of ids")
    return value


def _optional_id(rec: dict[str, Any], key: str) -> str | None:
    value = rec.get(key)
    return value if isinstance(value, str) and value else None


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------


class _Assembler:
    """Collects nodes and edges; validation happens once in :meth:`finish`."""

    def __init__(self) -> None:
        self.nodes: list[dict[str, Any]] = []
        self.edges: list[tuple[str, str, str]] = []
        self._versions: dict[str, str] = {}

    def node(
        self,
        nid: str,
        ntype: str,
        rel: Path,
        content: dict[str, Any],
        *,
        title_key: str = "title",
    ) -> None:
        version = content_hash(content)
        title = content.get(title_key)
        self.nodes.append(
            {
                "id": nid,
                "type": ntype,
                "version": version,
                "title": title if isinstance(title, str) else nid,
                "path": rel.as_posix(),
                "content": content,
            }
        )
        # First declaration wins for the version map; validate_graph reports
        # the duplicate itself.
        self._versions.setdefault(nid, version)

    def edge(self, src: str, predicate: str, dst: str) -> None:
        self.edges.append((src, predicate, dst))

    def finish(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        nodes = sorted(self.nodes, key=lambda n: n["id"])
        edges: list[dict[str, Any]] = [
            {
                "predicate": p,
                "source": {"id": s, "version": self._versions.get(s, "")},
                "target": {"id": t, "version": self._versions.get(t, "")},
            }
            for s, p, t in self.edges
        ]
        validate_graph(nodes, edges)
        edges.sort(key=lambda e: (e["predicate"], e["source"]["id"], e["target"]["id"]))
        return nodes, edges


def _add_partner(g: _Assembler, p: dict[str, Any]) -> None:
    pid = _key(p, "partner_id", PARTNERS_REL, "partner")
    g.node(pid, "participant", PARTNERS_REL, p, title_key="legal_name")


def _add_objective(g: _Assembler, o: dict[str, Any]) -> None:
    oid = _key(o, "objective_id", OBJECTIVES_REL, "objective")
    g.node(oid, "objective", OBJECTIVES_REL, o)


def _add_work_package(g: _Assembler, wp: dict[str, Any]) -> None:
    rel = WP_SEED_REL
    wp_id = _key(wp, "wp_id", rel, "work package")
    g.node(wp_id, "work_package", rel, wp)
    lead = _optional_id(wp, "lead_partner")
    if lead:
        g.edge(wp_id, "assigned_to", lead)
    for obj in _ids(wp, "objectives", rel, wp_id):
        g.edge(wp_id, "contributes_to", obj)

    for t in _objects(wp, "tasks", rel, wp_id):
        tid = _key(t, "task_id", rel, f"task in {wp_id}")
        g.node(tid, "task", rel, t)
        g.edge(tid, "contributes_to", wp_id)
        resp = _optional_id(t, "responsible_partner")
        if resp:
            g.edge(tid, "assigned_to", resp)
        for c in _ids(t, "contributing_partners", rel, tid):
            g.edge(c, "contributes_to", tid)
        for dep in _ids(t, "dependencies", rel, tid):
            g.edge(tid, "consumes", dep)

    for d in _objects(wp, "deliverables", rel, wp_id):
        did = _key(d, "deliverable_id", rel, f"deliverable in {wp_id}")
        g.node(did, "deliverable", rel, d)
        g.edge(wp_id, "produces", did)
        for producer in _ids(d, "produced_by", rel, did):
            g.edge(producer, "produces", did)


def _add_milestone(g: _Assembler, m: dict[str, Any]) -> None:
    mid = _key(m, "milestone_id", MILESTONES_REL, "milestone")
    g.node(mid, "milestone", MILESTONES_REL, m)
    for did in _ids(m, "deliverables", MILESTONES_REL, mid):
        g.edge(did, "validated_by", mid)


def _assemble(repo_root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    inputs: list[str] = []
    g = _Assembler()
    for p in _read_records(repo_root, PARTNERS_REL, "partners", inputs):
        _add_partner(g, p)
    for o in _read_records(repo_root, OBJECTIVES_REL, "objectives", inputs):
        _add_objective(g, o)
    for wp in _read_records(repo_root, WP_SEED_REL, "work_packages", inputs):
        _add_work_package(g, wp)
    for m in _read_records(repo_root, MILESTONES_REL, "milestones", inputs):
        _add_milestone(g, m)
    nodes, edges = g.finish()
    return nodes, edges, sorted(set(inputs))


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def build_snapshot(repo_root: Path) -> Snapshot:
    """Build an immutable graph snapshot from the records under *repo_root*.

    Returns a :class:`Snapshot`, or raises :class:`DevGraphError` naming the
    first invalid node, edge or record. Deterministic: identical record
    content yields byte-identical output and the same ``snapshot_id``.
    """
    nodes, edges, inputs = _assemble(Path(repo_root))
    return Snapshot(
        snapshot_id=snapshot_id(nodes, edges),
        nodes=tuple(nodes),
        edges=tuple(edges),
        inputs=tuple(inputs),
    )
