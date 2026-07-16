"""
Docs→graph projector — the ``docs_to_graph`` half of the milestone-2 sync split
(ticket 4, D6).

Where the graph→docs compiler (:mod:`runner.graph_compiler`) reads the vault and
writes canonical ``docs/**`` artifacts, this projector runs the other direction:
it reads durable **Tier 4** phase/gate state and mirrors it back into the vault as
``phase_gate_state`` nodes, so the Obsidian dashboards reflect run state.  It is a
**derived, downstream-read-only mirror** — it never feeds gate evaluation.

The two directions are non-overlapping by construction (D6):

* ``graph_to_docs`` (compiler) owns **Tier 3 + Part B prose** — it *writes*
  ``docs/**`` and *reads* the bound vault source folders.
* ``docs_to_graph`` (projector) owns **Tier 4 state + the gate mirror** — it
  *writes* only its owned vault folder (``18_phase_gate_state``) and *reads*
  ``docs/tier4_.../phase_outputs``.  It writes **no** ``docs/**`` path.

No ``docs/**`` path and no vault folder is written by both directions.
:func:`check_no_overlap` enforces this against a project's ``graph.config.yaml``
and is exercised in the tests; :func:`compute_sync_partition` exposes the two
write/read-sets for auditing.

Guarantees (ticket 4):

* **Deterministic & idempotent.**  A mirror node is a pure function of the durable
  gate-result artifact it reflects — no fresh timestamp, no domain reasoning.
  Re-running on unchanged Tier 4 rewrites byte-identical nodes and removes
  nothing.  Same state ⇒ same nodes.
* **Scoped writes.**  The projector writes and prunes **only** ``PGS-*.md`` nodes
  inside its owned folder; it never mutates ``graph_to_docs``-owned content
  (methodology nodes, ``proposal_section``/``objective``/… binding nodes).
* **No gate-evaluation effect.**  The mirror lives in the vault, which the gate
  evaluator does not read; every mirror node is marked ``derived`` and
  ``read_only``.  Projecting cannot change a gate outcome or input freshness.

Constitutional authority:
    Subordinate to CLAUDE.md.  The mirror is Tier-4-derived runtime state (§9.2),
    not source truth; it is downstream-read-only and makes no gate/DAG change.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Optional

import yaml

from runner.atomic_write import atomic_write_text
from runner.graph_config import GraphConfig, GraphConfigError, load_graph_config

# ---------------------------------------------------------------------------
# Constants — the docs_to_graph ownership boundary
# ---------------------------------------------------------------------------

#: Tier-4 phase outputs directory the projector reads (repo-relative).
PHASE_OUTPUTS_REL: str = "docs/tier4_orchestration_state/phase_outputs"

#: The single vault folder the projector owns and writes into.  Its whole
#: write-set is ``PGS-*.md`` nodes here; nothing else in the vault is touched.
PROJECTOR_OWNED_FOLDER: str = "18_phase_gate_state"

#: The node_type the projector emits (a Tier-4 mirror target, never extracted by
#: the compiler — see :func:`check_no_overlap`).
PROJECTOR_NODE_TYPE: str = "phase_gate_state"

#: Basename/id prefix for every mirror node the projector owns.
MIRROR_ID_PREFIX: str = "PGS-"


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class GraphProjectionError(Exception):
    """Raised when Tier-4 state cannot be projected (e.g. an unreadable vault dir)."""


class SyncOverlapError(Exception):
    """Raised when a config would let ``graph_to_docs`` and ``docs_to_graph`` write
    the same ``docs/**`` path or graph node — a D6 no-overlap violation."""


# ---------------------------------------------------------------------------
# GateState — one mirrored Tier-4 gate result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GateState:
    """A durable Tier-4 gate result, distilled for mirroring."""

    gate_id: str
    gate_kind: str
    status: str
    run_id: str
    evaluated_at: str
    phase: Optional[int]
    source_artifact: str
    deterministic_passed: int
    deterministic_failed: int
    semantic_passed: int
    semantic_failed: int

    @property
    def mirror_id(self) -> str:
        return f"{MIRROR_ID_PREFIX}{self.gate_id}"


# ---------------------------------------------------------------------------
# Reading Tier-4 gate state
# ---------------------------------------------------------------------------


def _phase_from_path(rel_path: str) -> Optional[int]:
    """Derive the phase number from a ``phase_outputs/phaseN_.../...`` path."""
    for part in PurePosixPath(rel_path).parts:
        if part.startswith("phase") and len(part) > 5 and part[5].isdigit():
            digits = ""
            for ch in part[5:]:
                if ch.isdigit():
                    digits += ch
                else:
                    break
            if digits:
                return int(digits)
    return None


def _predicate_counts(block: Any) -> tuple[int, int]:
    """(#passed, #failed) from a ``{"passed": [...], "failed": [...]}`` block."""
    if not isinstance(block, dict):
        return (0, 0)
    passed = block.get("passed") or []
    failed = block.get("failed") or []
    return (
        len(passed) if isinstance(passed, list) else 0,
        len(failed) if isinstance(failed, list) else 0,
    )


def read_tier4_gate_states(repo_root: Path) -> tuple[GateState, ...]:
    """Scan Tier-4 phase outputs for gate-result artifacts, deterministically.

    A gate-result file is any ``*.json`` under
    ``docs/tier4_orchestration_state/phase_outputs`` carrying both a ``gate_id``
    and a ``status`` (phase summaries and other artifacts lack these and are
    skipped).  Files are scanned in sorted path order; a duplicate ``gate_id``
    keeps the first (sorted) occurrence.  Returns states ordered by
    ``(phase, gate_id)``.
    """
    outputs_dir = repo_root / PHASE_OUTPUTS_REL
    if not outputs_dir.is_dir():
        return ()

    by_gate_id: dict[str, GateState] = {}
    json_files = sorted(
        (p for p in outputs_dir.rglob("*.json") if p.is_file()),
        key=lambda p: p.relative_to(repo_root).as_posix(),
    )
    for path in json_files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        gate_id = data.get("gate_id")
        status = data.get("status")
        if not isinstance(gate_id, str) or not isinstance(status, str):
            continue  # not a gate-result artifact
        if gate_id in by_gate_id:
            continue  # first sorted occurrence wins (deterministic)
        rel = path.relative_to(repo_root).as_posix()
        det_p, det_f = _predicate_counts(data.get("deterministic_predicates"))
        sem_p, sem_f = _predicate_counts(data.get("semantic_predicates"))
        by_gate_id[gate_id] = GateState(
            gate_id=gate_id,
            gate_kind=str(data.get("gate_kind", "")),
            status=status,
            run_id=str(data.get("run_id", "")),
            evaluated_at=str(data.get("evaluated_at", "")),
            phase=_phase_from_path(rel),
            source_artifact=rel,
            deterministic_passed=det_p,
            deterministic_failed=det_f,
            semantic_passed=sem_p,
            semantic_failed=sem_f,
        )
    return tuple(
        sorted(by_gate_id.values(), key=lambda g: (g.phase if g.phase is not None else 0, g.gate_id))
    )


# ---------------------------------------------------------------------------
# Rendering a mirror node
# ---------------------------------------------------------------------------


def _render_mirror_node(gs: GateState) -> str:
    """Render a ``phase_gate_state`` mirror node as deterministic markdown.

    Front-matter carries the mirrored gate fields plus ``derived: true`` /
    ``read_only: true`` (this is Tier-4-derived, downstream-read-only state) and
    ``sync_direction: docs_to_graph`` (the D6 ownership tag).  No fresh timestamp
    is written — only the source's own ``evaluated_at`` is mirrored — so the node
    is byte-stable for unchanged Tier-4 state.
    """
    front_matter: dict[str, Any] = {
        "id": gs.mirror_id,
        "title": f"Phase-gate mirror: {gs.gate_id}",
        "node_type": PROJECTOR_NODE_TYPE,
        # Mirrors a durable Tier-4 run fact grounded in the gate-result artifact.
        "evidence_strength": "source_grounded",
        "tier": "tier4",
        "phase": gs.phase,
        "gate_id": gs.gate_id,
        "gate_kind": gs.gate_kind,
        "gate_status": gs.status,
        "run_id": gs.run_id,
        "evaluated_at": gs.evaluated_at,
        "deterministic_predicates_passed": gs.deterministic_passed,
        "deterministic_predicates_failed": gs.deterministic_failed,
        "semantic_predicates_passed": gs.semantic_passed,
        "semantic_predicates_failed": gs.semantic_failed,
        "source_artifact": gs.source_artifact,
        "sync_direction": "docs_to_graph",
        "derived": True,
        "read_only": True,
        "tags": ["phase-gate-mirror", "docs-to-graph"],
    }
    fm_text = yaml.safe_dump(front_matter, sort_keys=False, allow_unicode=True)
    phase_label = f"phase {gs.phase}" if gs.phase is not None else "unphased"
    body = (
        f"# Phase-gate mirror: {gs.gate_id}\n\n"
        f"> [!info] Derived, read-only mirror (docs→graph projection, D6)\n"
        f"> This node mirrors durable Tier-4 gate state and is regenerated by "
        f"`runner/graph_projector.py`. It is **not** authored content and does "
        f"**not** feed gate evaluation. Edit the run, not this node.\n\n"
        f"- **Gate:** `{gs.gate_id}` ({gs.gate_kind or 'gate'}, {phase_label})\n"
        f"- **Status:** **{gs.status}**\n"
        f"- **Run:** `{gs.run_id or '—'}`\n"
        f"- **Evaluated at:** {gs.evaluated_at or '—'}\n"
        f"- **Deterministic predicates:** {gs.deterministic_passed} passed / "
        f"{gs.deterministic_failed} failed\n"
        f"- **Semantic predicates:** {gs.semantic_passed} passed / "
        f"{gs.semantic_failed} failed\n"
        f"- **Source:** `{gs.source_artifact}`\n"
    )
    return f"---\n{fm_text}---\n\n{body}"


# ---------------------------------------------------------------------------
# Projection result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProjectionResult:
    """The outcome of a projection run."""

    target_dir: Path
    written: tuple[Path, ...]
    removed: tuple[Path, ...]
    gate_states: tuple[GateState, ...]


def project(
    repo_root: Path,
    vault_dir: Path,
    target_folder: str = PROJECTOR_OWNED_FOLDER,
) -> ProjectionResult:
    """Mirror durable Tier-4 gate state into the vault's owned folder.

    Reads gate results via :func:`read_tier4_gate_states`, renders one
    ``phase_gate_state`` node per gate into ``vault_dir/target_folder``, and
    prunes any stale ``PGS-*.md`` there that no longer corresponds to a gate.
    Writes/prunes **only** ``PGS-*.md`` files in ``target_folder`` — never any
    other folder and never any ``docs/**`` path.

    Idempotent: re-running on unchanged Tier-4 rewrites byte-identical content
    and removes nothing.

    Raises
    ------
    GraphProjectionError
        If *vault_dir* does not exist.
    """
    vault_dir = Path(vault_dir)
    if not vault_dir.is_dir():
        raise GraphProjectionError(f"Vault directory not found: {vault_dir}")

    gate_states = read_tier4_gate_states(repo_root)
    target_dir = vault_dir / target_folder
    target_dir.mkdir(parents=True, exist_ok=True)

    desired: dict[str, str] = {
        f"{gs.mirror_id}.md": _render_mirror_node(gs) for gs in gate_states
    }

    written: list[Path] = []
    for filename in sorted(desired):
        path = target_dir / filename
        content = desired[filename]
        # write-if-changed keeps re-runs idempotent without churning mtimes
        if not path.is_file() or path.read_text(encoding="utf-8") != content:
            atomic_write_text(content, path)
        written.append(path)

    # Prune stale mirror nodes (ours only: PGS-*.md) not in the desired set.
    removed: list[Path] = []
    for existing in sorted(target_dir.glob(f"{MIRROR_ID_PREFIX}*.md")):
        if existing.name not in desired:
            existing.unlink()
            removed.append(existing)

    return ProjectionResult(
        target_dir=target_dir,
        written=tuple(written),
        removed=tuple(removed),
        gate_states=gate_states,
    )


# ---------------------------------------------------------------------------
# D6 no-overlap invariant
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SyncPartition:
    """The two sync directions' write/read-sets, for auditing the D6 partition."""

    graph_to_docs_writes_docs: tuple[str, ...]
    """``docs/**`` artifact paths the compiler writes (tier3 + tier5 bindings)."""
    graph_to_docs_reads_graph: tuple[tuple[Optional[str], Optional[str]], ...]
    """``(folder, node_type)`` selectors the compiler extracts from."""
    docs_to_graph_writes_graph: tuple[tuple[str, str], ...]
    """``(folder, node_type)`` the projector writes (its owned mirror)."""
    docs_to_graph_writes_docs: tuple[str, ...]
    """``docs/**`` paths the projector writes — **always empty** by design."""


def compute_sync_partition(
    config: GraphConfig, target_folder: str = PROJECTOR_OWNED_FOLDER
) -> SyncPartition:
    """Derive the D6 write/read partition from a project's ``graph.config.yaml``."""
    writes_docs: list[str] = []
    reads_graph: list[tuple[Optional[str], Optional[str]]] = []
    for binding in config.bindings:
        if binding.artifact_path is not None:
            writes_docs.append(binding.artifact_path)
            reads_graph.append((binding.match_folder, binding.match_node_type))
    return SyncPartition(
        graph_to_docs_writes_docs=tuple(sorted(set(writes_docs))),
        graph_to_docs_reads_graph=tuple(sorted(set(reads_graph), key=lambda t: (t[0] or "", t[1] or ""))),
        docs_to_graph_writes_graph=((target_folder, PROJECTOR_NODE_TYPE),),
        docs_to_graph_writes_docs=(),
    )


def check_no_overlap(
    config: GraphConfig, target_folder: str = PROJECTOR_OWNED_FOLDER
) -> None:
    """Enforce the D6 no-overlap invariant, failing closed on any violation.

    Raises :class:`SyncOverlapError` if either direction could write what the
    other owns:

    * the projector must write **no** ``docs/**`` path (it owns only the vault
      mirror), and
    * no ``graph_to_docs`` artifact binding may select the projector's owned
      ``phase_gate_state`` mirror (folder ``target_folder`` / node_type
      ``phase_gate_state``) — otherwise the compiler would extract the projected
      mirror into a ``docs/**`` artifact, and both directions would touch it.
    """
    partition = compute_sync_partition(config, target_folder=target_folder)

    if partition.docs_to_graph_writes_docs:
        raise SyncOverlapError(
            "docs_to_graph (projector) must not write any docs/** path; it owns "
            f"only the vault mirror {target_folder}/ (phase_gate_state)"
        )

    for binding in config.bindings:
        if binding.artifact_path is None:
            continue  # source-only bindings extract nothing
        if binding.matches(target_folder, PROJECTOR_NODE_TYPE):
            raise SyncOverlapError(
                f"graph_to_docs binding (folder={binding.match_folder!r}, "
                f"node_type={binding.match_node_type!r}, "
                f"artifact_path={binding.artifact_path!r}) would extract the "
                f"docs_to_graph-owned phase_gate_state mirror in {target_folder}/ "
                f"into a docs/** artifact — the two sync directions overlap (D6). "
                f"Keep the {target_folder}/ (phase_gate_state) binding source-only "
                f"(no artifact_path)."
            )


# ---------------------------------------------------------------------------
# CLI  (python -m runner.graph_projector --config <path>)
# ---------------------------------------------------------------------------


def main(argv: Optional[list[str]] = None) -> int:
    """Project Tier-4 gate state into a config's vault from the command line.

    Enforces the D6 no-overlap invariant before writing.  Exit codes: ``0``
    success; ``2`` a fail-closed error (bad config, overlap, missing vault);
    ``3`` an unexpected error.
    """
    parser = argparse.ArgumentParser(
        prog="python -m runner.graph_projector",
        description=(
            "Mirror durable Tier-4 phase/gate state into a per-project vault as "
            "read-only phase_gate_state nodes (docs→graph projection, D6)."
        ),
    )
    parser.add_argument("--config", required=True, help="Path to graph.config.yaml.")
    parser.add_argument(
        "--repo-root",
        default=None,
        help="Repository root (default: auto-discovered via find_repo_root).",
    )
    args = parser.parse_args(argv)

    from runner.paths import find_repo_root

    try:
        repo_root = (
            Path(args.repo_root).resolve() if args.repo_root else find_repo_root()
        )
        config = load_graph_config(Path(args.config))
        check_no_overlap(config)  # fail closed before writing anything
        result = project(repo_root, config.resolve_vault_dir())
    except (GraphConfigError, SyncOverlapError, GraphProjectionError) as exc:
        print(f"[graph-project] FAIL-CLOSED: {exc}", file=sys.stderr, flush=True)
        return 2
    except Exception as exc:  # noqa: BLE001 — CLI boundary
        print(f"[graph-project] ERROR: {exc}", file=sys.stderr, flush=True)
        return 3

    print(
        f"[graph-project] project={config.project_id} "
        f"mirrored={len(result.written)} pruned={len(result.removed)} "
        f"target={result.target_dir}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
