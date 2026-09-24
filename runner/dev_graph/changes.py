"""
Dev-graph approved change recording — a new record version, the old one kept.

An operator records an approved new version of one Tier 3 source record. The
function builds the snapshot before the change, archives the current record
content, applies the new content, builds the snapshot after the change, and
writes one immutable change record carrying both snapshot ids, both record
versions and the change set. Both snapshots are stored content-addressed, so
the planner can read them later without rebuilding.

What "kept" means here:

* The old record content is archived under :data:`RECORD_VERSIONS_REL` by its
  content hash and is retrievable through :func:`read_record_version`.
* The before snapshot is stored under :data:`SNAPSHOTS_REL` by its id.
* Tier 3 stays the single writer of the fact: the new content lands at the
  record's own path and the next build reads it there. The archive is a copy
  for retrieval, never a second authority.

The change set is a pure diff of the two snapshots. Nodes are compared by id
and version; a node whose own content is unchanged and whose version moved
only because a nested record changed (a work package holding a changed task)
is reported as ``contained``, not ``direct``. A direct change also lists the
top-level fields that differ. Edges are compared by label, so a removed link
is a change in its own right.

Fail-closed: an unknown record path, a malformed change id, an existing
change id, or a new record the builder rejects all refuse. When the after
build fails the record file is restored byte for byte and nothing is written.

Constitutional authority:
    Subordinate to CLAUDE.md. Writes the operator-approved content to its
    Tier 3 path and its archive and change record under Tier 4 dev_graph.
    Evaluates no gate, invokes no Claude, invents no facts (§13.3).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from runner.atomic_write import atomic_write_json
from runner.dev_graph.builder import (
    MILESTONES_REL,
    OBJECTIVES_REL,
    PARTNERS_REL,
    SOURCES_REL,
    WP_SEED_REL,
    Snapshot,
    build_snapshot,
)
from runner.dev_graph.identity import HASH_PREFIX, content_hash
from runner.dev_graph.schema import DevGraphError, edge_label

CHANGE_SCHEMA_ID = "orch.dev_graph.change_record.v1"
RECORD_VERSION_SCHEMA_ID = "orch.dev_graph.record_version.v1"

_DEV_GRAPH = "docs/tier4_orchestration_state/dev_graph"
#: One immutable change record per change id.
CHANGES_REL = f"{_DEV_GRAPH}/changes"
#: Content-addressed archive of record versions the operator replaced.
RECORD_VERSIONS_REL = f"{_DEV_GRAPH}/record_versions"
#: Content-addressed store of snapshots, one file per snapshot id.
SNAPSHOTS_REL = f"{_DEV_GRAPH}/snapshots"

#: The Tier 3 records the builder indexes: the only paths a change may name.
RECORD_PATHS: frozenset[str] = frozenset(
    p.as_posix() for p in (PARTNERS_REL, OBJECTIVES_REL, WP_SEED_REL, MILESTONES_REL, SOURCES_REL)
)

#: How a changed node changed: its own content (``direct``) or only a record
#: nested inside it (``contained``).
CHANGE_KINDS: frozenset[str] = frozenset({"direct", "contained"})

_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


@dataclass(frozen=True)
class ChangeRecord:
    """The durable outcome of one approved change."""

    change_id: str
    record_path: str
    before_snapshot_id: str
    after_snapshot_id: str
    before_record_version: str
    after_record_version: str
    change_set: dict[str, Any]
    path: str
    """Repo-relative POSIX path of the change record."""


# ---------------------------------------------------------------------------
# Snapshot store
# ---------------------------------------------------------------------------


def _hex(hashed: str) -> str:
    return hashed[len(HASH_PREFIX):]


def snapshot_path(repo_root: Path, snapshot_id: str) -> Path:
    return Path(repo_root) / SNAPSHOTS_REL / f"{_hex(snapshot_id)}.json"


def store_snapshot(repo_root: Path, snapshot: Snapshot) -> Path:
    """Write *snapshot* under its id; a stored snapshot is never rewritten."""
    target = snapshot_path(repo_root, snapshot.snapshot_id)
    if not target.is_file():
        atomic_write_json(snapshot.to_dict(), target)
    return target


def load_snapshot(repo_root: Path, snapshot_id: str) -> Snapshot:
    """Read the stored snapshot *snapshot_id*, or refuse.

    Raises :class:`DevGraphError` with kind ``missing_snapshot`` when no
    file is stored under that id and ``malformed_snapshot`` when the file
    does not validate or its content does not hash to that id.
    """
    if not isinstance(snapshot_id, str) or not snapshot_id.startswith(HASH_PREFIX):
        raise DevGraphError("malformed_snapshot", str(snapshot_id), "snapshot id is not a sha256: hash")
    path = snapshot_path(repo_root, snapshot_id)
    rel = path.relative_to(repo_root).as_posix()
    if not path.is_file():
        raise DevGraphError("missing_snapshot", rel, f"no stored snapshot for {snapshot_id}")
    try:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        raise DevGraphError("malformed_snapshot", rel, f"unreadable JSON: {exc}") from exc
    snap = Snapshot.from_dict(doc, rel)
    if snap.snapshot_id != snapshot_id:
        raise DevGraphError(
            "malformed_snapshot", rel, f"file is stored under {snapshot_id} but hashes to {snap.snapshot_id}"
        )
    return snap


# ---------------------------------------------------------------------------
# Record archive
# ---------------------------------------------------------------------------


def _record_version_path(repo_root: Path, version: str) -> Path:
    return Path(repo_root) / RECORD_VERSIONS_REL / f"{_hex(version)}.json"


def _archive_record(repo_root: Path, record_rel: str, content: Any) -> str:
    version = content_hash(content)
    target = _record_version_path(repo_root, version)
    if not target.is_file():
        atomic_write_json(
            {
                "schema_id": RECORD_VERSION_SCHEMA_ID,
                "path": record_rel,
                "content_version": version,
                "content": content,
            },
            target,
        )
    return version


def read_record_version(repo_root: Path, version: str) -> Any:
    """The archived content of a record version, or refuse (``missing_snapshot``
    is for snapshots; a missing archive is ``malformed_request``)."""
    path = _record_version_path(repo_root, version)
    rel = path.relative_to(repo_root).as_posix()
    if not path.is_file():
        raise DevGraphError("malformed_request", rel, f"no archived record version {version}")
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    if doc.get("schema_id") != RECORD_VERSION_SCHEMA_ID or content_hash(doc.get("content")) != version:
        raise DevGraphError("malformed_record", rel, "archived record does not hash to its version")
    return doc["content"]


# ---------------------------------------------------------------------------
# Change set (pure)
# ---------------------------------------------------------------------------


def _own_content(node: dict[str, Any]) -> dict[str, Any]:
    """A node's content without the nested records it contains.

    A list of objects inside a record (a work package's tasks) is indexed as
    nodes of its own; a change there is the nested node's change.
    """
    return {
        k: v
        for k, v in node["content"].items()
        if not (isinstance(v, list) and v and all(isinstance(i, dict) for i in v))
    }


def label_of(e: dict[str, Any]) -> str:
    """The label ``<source> -<predicate>-> <target>`` of a snapshot edge."""
    return edge_label(e["source"]["id"], e["predicate"], e["target"]["id"])


def _edge_entry(e: dict[str, Any]) -> dict[str, Any]:
    return {
        "label": label_of(e),
        "predicate": e["predicate"],
        "source": e["source"]["id"],
        "target": e["target"]["id"],
    }


def change_set(before: Snapshot, after: Snapshot) -> dict[str, Any]:
    """The pure diff of two snapshots: nodes by id and version, edges by label.

    ``nodes.added`` and ``nodes.removed`` items carry ``id`` and ``type``;
    ``nodes.changed`` items add both versions, the kind and the changed fields.
    """
    b_nodes = {n["id"]: n for n in before.nodes}
    a_nodes = {n["id"]: n for n in after.nodes}
    changed: list[dict[str, Any]] = []
    for nid in sorted(b_nodes.keys() & a_nodes.keys()):
        b, a = b_nodes[nid], a_nodes[nid]
        if b["version"] == a["version"]:
            continue
        own_b, own_a = _own_content(b), _own_content(a)
        changed.append(
            {
                "id": nid,
                "type": a["type"],
                "before_version": b["version"],
                "after_version": a["version"],
                "kind": "contained" if own_b == own_a else "direct",
                # The top-level keys of the node's own content that differ:
                # the revision contract checker classifies a direct change by
                # field. Empty for a contained change.
                "changed_fields": sorted(
                    k for k in own_b.keys() | own_a.keys() if own_b.get(k) != own_a.get(k)
                ),
            }
        )
    b_edges = {label_of(e): e for e in before.edges}
    a_edges = {label_of(e): e for e in after.edges}
    return {
        "nodes": {
            "added": [{"id": i, "type": a_nodes[i]["type"]} for i in sorted(a_nodes.keys() - b_nodes.keys())],
            "removed": [{"id": i, "type": b_nodes[i]["type"]} for i in sorted(b_nodes.keys() - a_nodes.keys())],
            "changed": changed,
        },
        "edges": {
            "added": [_edge_entry(a_edges[k]) for k in sorted(a_edges.keys() - b_edges.keys())],
            "removed": [_edge_entry(b_edges[k]) for k in sorted(b_edges.keys() - a_edges.keys())],
        },
    }


# ---------------------------------------------------------------------------
# The one write
# ---------------------------------------------------------------------------


def _refuse(kind: str, offender: str, message: str) -> DevGraphError:
    return DevGraphError(kind, offender, message)


def record_change(
    repo_root: Path,
    record_rel: Path | str,
    new_content: Any,
    *,
    change_id: str,
) -> ChangeRecord:
    """Record *new_content* as the approved version of the record at *record_rel*.

    Builds the before snapshot, archives the current content, writes the new
    content, builds the after snapshot, and writes the change record. Raises
    :class:`DevGraphError` on an unknown record path or malformed change id
    (``malformed_request``), an existing change id (``immutable_record``), or
    a new version the builder rejects (the builder's own kind; the record file
    is restored first).
    """
    root = Path(repo_root)
    rel = Path(record_rel).as_posix()
    if rel not in RECORD_PATHS:
        raise _refuse("malformed_request", rel, f"record path is not one of {sorted(RECORD_PATHS)}")
    if not isinstance(change_id, str) or not _ID_RE.match(change_id):
        raise _refuse("malformed_request", str(change_id), "change_id is not a plain identifier")
    change_rel = Path(CHANGES_REL) / f"{change_id}.json"
    if (root / change_rel).exists():
        raise _refuse("immutable_record", change_rel.as_posix(), f"change {change_id} is already recorded")
    if not isinstance(new_content, dict):
        raise _refuse("malformed_request", rel, "new record content must be a JSON object")

    record_path = root / rel
    old_bytes = record_path.read_bytes() if record_path.is_file() else None
    old_content = json.loads(old_bytes.decode("utf-8-sig")) if old_bytes is not None else None

    before = build_snapshot(root)
    atomic_write_json(new_content, record_path)
    try:
        after = build_snapshot(root)
    except DevGraphError:
        if old_bytes is None:
            record_path.unlink()
        else:
            record_path.write_bytes(old_bytes)
        raise
    # Nothing under Tier 4 is written until the new version builds.
    store_snapshot(root, before)
    store_snapshot(root, after)
    before_version = _archive_record(root, rel, old_content)
    after_version = _archive_record(root, rel, new_content)

    cs = change_set(before, after)
    record: dict[str, Any] = {
        "schema_id": CHANGE_SCHEMA_ID,
        "change_id": change_id,
        "approval": "approved",
        "record_path": rel,
        "before": {"snapshot_id": before.snapshot_id, "record_version": before_version},
        "after": {"snapshot_id": after.snapshot_id, "record_version": after_version},
        "change_set": cs,
    }
    atomic_write_json(record, root / change_rel)
    return ChangeRecord(
        change_id=change_id,
        record_path=rel,
        before_snapshot_id=before.snapshot_id,
        after_snapshot_id=after.snapshot_id,
        before_record_version=before_version,
        after_record_version=after_version,
        change_set=cs,
        path=change_rel.as_posix(),
    )


def read_change_record(repo_root: Path, change_id: str) -> ChangeRecord:
    """The recorded change *change_id*, or refuse (``malformed_request``)."""
    root = Path(repo_root)
    if not isinstance(change_id, str) or not _ID_RE.match(change_id):
        raise _refuse("malformed_request", str(change_id), "change_id is not a plain identifier")
    change_rel = Path(CHANGES_REL) / f"{change_id}.json"
    path = root / change_rel
    if not path.is_file():
        raise _refuse("malformed_request", change_rel.as_posix(), f"no change record {change_id}")
    try:
        rec = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        raise _refuse("malformed_record", change_rel.as_posix(), f"unreadable JSON: {exc}") from exc
    try:
        cs: dict[str, Any] = rec["change_set"]
        if rec["schema_id"] != CHANGE_SCHEMA_ID or not isinstance(cs, dict):
            raise KeyError("schema_id")
        return ChangeRecord(
            change_id=rec["change_id"],
            record_path=rec["record_path"],
            before_snapshot_id=rec["before"]["snapshot_id"],
            after_snapshot_id=rec["after"]["snapshot_id"],
            before_record_version=rec["before"]["record_version"],
            after_record_version=rec["after"]["record_version"],
            change_set=cs,
            path=change_rel.as_posix(),
        )
    except (KeyError, TypeError) as exc:
        raise _refuse("malformed_record", change_rel.as_posix(), f"not a {CHANGE_SCHEMA_ID} record: {exc}") from exc
