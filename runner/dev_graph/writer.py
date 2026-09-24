"""
Dev-graph snapshot writer — the deterministic component behind the index.

Builds the snapshot and writes it atomically to :data:`SNAPSHOT_REL`. The
snapshot carries no run id and no wall-clock field, so a replay from the
same records is byte-equal. Registered in ``runner.deterministic_components``
as ``dev_graph_snapshot_writer`` (CLAUDE.md §17.5.3): Python owns the write,
nothing here invokes Claude, and a build error propagates so the component
record reports the failure and no partial artifact is left behind.
"""

from __future__ import annotations

from pathlib import Path

from runner.atomic_write import atomic_write_json
from runner.dev_graph.builder import build_snapshot

#: Repo-relative location of the index. Distinct from the compiler's staging
#: path; see the decision log entry on the retained staging path.
SNAPSHOT_REL = "docs/tier4_orchestration_state/dev_graph/snapshot.json"


def write_snapshot(repo_root: Path) -> Path:
    """Build and write the snapshot; return its absolute path."""
    root = Path(repo_root)
    snap = build_snapshot(root)
    target = root / SNAPSHOT_REL
    atomic_write_json(snap.to_dict(), target)
    return target


def run_snapshot_writer(run_id: str, repo_root: Path) -> list[Path]:
    """Component adapter: ``(run_id, repo_root) -> written``. The run id is
    accepted for the contract and does not enter the artifact."""
    del run_id
    return [write_snapshot(repo_root)]
