"""
Graph→docs compiler — Tier 3 extraction (milestone 2, ticket 3; walking skeleton).

A deterministic, **Step-0-style** pass (modelled on :mod:`runner.call_slicer`) that
reads a per-project vault via the ticket-1 substrate
(:func:`runner.vault_reader.read_vault`) and **extracts** the Tier 3
``architecture_inputs`` JSON the runner and gates already consume — *without*
inventing a single fact.  It is the ``graph_to_docs`` half of the milestone-2
sync split (D6): it owns Tier 3 (+ Part B prose, added in ticket 6).

What this module is
-------------------

* **Generic and config-driven.**  It carries no project nouns.  Every
  project-specific binding — which folders/``node_type``\\ s map to which
  ``artifact_path`` and under which ``collection_key`` — lives in the per-project
  ``graph.config.yaml`` (:mod:`runner.graph_config`), never here.  A second,
  unrelated instance compiles with only its config changed (the D15 agnosticism
  test, exercised in ticket 9).
* **Pure, deterministic, non-inferential.**  No Claude, no domain reasoning.  The
  same vault yields byte-identical output, modulo the ``compiled_at`` timestamp.
  A record's ``validation_status`` is **computed** from ``evidence_strength`` via
  the Appendix-B lookup — never read from the node — so a ``synthesis`` /
  ``inference`` / ``unconfirmed`` node can never land as a ``Confirmed`` Tier 3
  fact.  The compiler authors no prose; it extracts declared fields verbatim.
* **Non-destructive (compile-and-diff).**  Output is written to a **staging**
  location under Tier 4, never over the hand-lift.  A diff report compares the
  compiled artifacts against the existing ticket-14 hand-lift
  (``docs/tier3_.../architecture_inputs/*.json``), which *is* the compiler's
  oracle.  The graph-as-authoritative-source cutover (open-Q #4) is deferred to
  ticket 10; this module never overwrites the hand-lift.
* **Fail closed, never fabricate.**  A node whose self-declared ``tier`` /
  ``artifact_path`` front-matter contradicts the ``graph.config.yaml`` binding
  that routes it, or a config that routes two conflicting ``collection_key``\\ s
  to one artifact, raises :class:`GraphCompileError` **naming the offending
  node/binding**.  It never guesses a missing fact.

Walking-skeleton scope (ticket 3)
---------------------------------
This slice extracts **Tier 3 ``architecture_inputs``** only (``tier == "tier3"``
bindings with an ``artifact_path``).  Part B ``proposal_section`` extraction
(Tier 5) is ticket 6; it reuses this same mechanism.  Against the *current* MSCA
vault — which is methodology-only, with the Tier-3 binding nodes (folders
11–18) not yet authored (ticket 8) — the compiled ``architecture_inputs`` are
empty and the diff report enumerates the whole hand-lift as an **explained
residual** ("binding nodes authored in ticket 8").  The extraction contract
itself is proven on a controlled fixture vault (``tests/runner/test_graph_compiler.py``).

Constitutional authority
-------------------------
Subordinate to CLAUDE.md.  This is a runtime-layer preprocessing pass (§17,
Call-Slicer-class): it makes **no change** to the §17 contracts, the DAG
scheduler, or gate evaluation.  It writes only staging artifacts under Tier 4 and
never mutates a higher tier.  Provenance is carried end-to-end via Appendix B
(``PHASE8_FULLSCALE_AND_OBSIDIAN_GRILL_BRIEF.md``); status vocabulary is
CLAUDE.md §12.2.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Optional

from runner.atomic_write import atomic_write_json
from runner.graph_config import Binding, GraphConfig, GraphConfigError, load_graph_config
from runner.graph_schema import (
    EVIDENCE_TO_STATUS,
    OPTIONAL_BINDING_FIELDS,
    REQUIRED_CORE_FIELDS,
)
from runner.vault_reader import GraphNode, Vault, VaultReadError, read_vault

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Staging root (relative to repo root) for compiled artifacts.  Non-destructive:
#: the compiler writes here, never over the hand-lift.  Under Tier 4 because a
#: compile is orchestration state, not a Tier 3 source of truth.
STAGING_REL: str = "docs/tier4_orchestration_state/graph_compile/staging"

#: The diff report path (relative to repo root).
DIFF_REPORT_REL: str = "docs/tier4_orchestration_state/graph_compile/diff_report.json"

#: The Appendix-B mapping string, recorded in every compiled ``_provenance`` block.
#: Derived from the canonical :data:`~runner.graph_schema.EVIDENCE_TO_STATUS` so it
#: can never record a mapping that has drifted from the schema.
APPENDIX_B_MAPPING: str = "; ".join(
    f"{k}->{v}" for k, v in EVIDENCE_TO_STATUS.items()
)

#: Front-matter keys that are **structural/binding**, never emitted as record
#: content.  ``id``/``title``/``evidence_strength`` are emitted explicitly (in a
#: fixed position); ``validation_status`` is *computed* from ``evidence_strength``
#: and so is reserved — a node may not inject its own status (anti-fabrication).
#: Derived from the schema's field tuples so a future optional binding field is
#: excluded automatically rather than silently leaking into record content.
RESERVED_FM_KEYS: frozenset[str] = (
    frozenset(REQUIRED_CORE_FIELDS)
    | frozenset(OPTIONAL_BINDING_FIELDS)
    | frozenset({"validation_status", "collection_key", "aliases"})
)


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------


class GraphCompileError(Exception):
    """Raised when the graph cannot be compiled to Tier 3 artifacts.

    Covers a node whose self-declared ``tier``/``artifact_path`` contradicts its
    config binding, and a config that routes conflicting ``collection_key``\\ s to
    one artifact.  Config-load and vault-read failures surface as their own
    (:class:`~runner.graph_config.GraphConfigError` /
    :class:`~runner.vault_reader.VaultReadError`) types.  Every message names the
    offending node or binding.
    """


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CompiledArtifact:
    """One compiled Tier 3 artifact (the ``collection_key`` records for one file)."""

    artifact_path: str
    """Canonical ``docs/**`` target (repo-relative, POSIX)."""
    collection_key: str
    """Top-level JSON key the records are collected under."""
    records: tuple[dict[str, Any], ...]
    """Extracted records, in vault (relative-path) order."""
    source_node_ids: tuple[str, ...]
    """The vault node ids the records came from (parallel to ``records``)."""
    staging_path: Path
    """Absolute path the artifact was written to (under :data:`STAGING_REL`)."""


@dataclass(frozen=True)
class Tier3CompileResult:
    """The result of a Tier 3 compile run."""

    project_id: str
    vault_dir: Path
    artifacts: tuple[CompiledArtifact, ...]
    staging_root: Path
    written: tuple[Path, ...]
    """Every file written (artifacts, in artifact order)."""


# ---------------------------------------------------------------------------
# Record extraction
# ---------------------------------------------------------------------------


def extract_record(node: GraphNode) -> dict[str, Any]:
    """Extract one canonical Tier 3 record from a bound *node*, verbatim.

    The record is: ``id`` and ``title`` (from required core), then every
    non-:data:`RESERVED_FM_KEYS` front-matter field **passed through in
    front-matter order**, then the **computed** ``validation_status`` (Appendix-B
    over ``evidence_strength`` — never read from the node) and the carried
    ``evidence_strength``.  No prose is authored and no field is inferred; the
    compiler only relays declared fields and computes the one derived status.
    """
    record: dict[str, Any] = {"id": node.node_id, "title": node.title}
    for key, value in node.front_matter.items():
        if key in RESERVED_FM_KEYS:
            continue
        record[key] = value
    # Computed, never read (anti-fabrication): status is a pure Appendix-B lookup.
    record["validation_status"] = node.status
    record["evidence_strength"] = node.evidence_strength
    return record


def _collection_key_for(binding: Binding) -> str:
    """The collection key for *binding*: the declared one, else the file stem.

    ``artifact_path`` is guaranteed non-``None`` by the caller (only artifact
    bindings reach here).
    """
    if binding.collection_key:
        return binding.collection_key
    stem = PurePosixPath(str(binding.artifact_path)).name
    if stem.endswith(".json"):
        stem = stem[: -len(".json")]
    return stem


# ---------------------------------------------------------------------------
# Binding consistency (fail-closed)
# ---------------------------------------------------------------------------


def _check_node_self_binding(node: GraphNode, binding: Optional[Binding]) -> None:
    """Fail closed if *node* self-declares a ``tier``/``artifact_path`` the config
    *binding* cannot satisfy.

    Self-declaration is additive-optional; but a node that declares a concrete
    ``artifact_path`` (an extraction target) must be routed to exactly that target
    by some binding, and a declared ``tier`` must agree with its binding.  A
    node declaring an ``artifact_path`` that **no** binding routes — or one that
    routes it elsewhere — is a binding the compiler cannot honour, so it fails
    closed naming the node rather than silently dropping the declared intent or
    fabricating a target.  A ``tier``-only declaration (no ``artifact_path``, i.e.
    no extraction requested) is permitted as documentation.
    """
    node_ap = node.artifact_path
    node_tier = node.tier

    if node_ap is not None:
        if binding is None:
            raise GraphCompileError(
                f"{node.rel_path}: node declares artifact_path {node_ap!r} but no "
                f"graph.config.yaml binding routes it there; add a binding or remove "
                f"the declaration — the compiler will not fabricate a target"
            )
        if node_ap != binding.artifact_path:
            raise GraphCompileError(
                f"{node.rel_path}: node declares artifact_path {node_ap!r} but its "
                f"binding routes it to {binding.artifact_path!r}; resolve the "
                f"contradiction — the compiler will not choose for you"
            )

    if node_tier is not None and binding is not None and node_tier != binding.tier:
        raise GraphCompileError(
            f"{node.rel_path}: node declares tier {node_tier!r} but its binding "
            f"routes it to {binding.tier!r} (artifact_path={binding.artifact_path!r}); "
            f"resolve the contradiction — the compiler will not choose for you"
        )


# ---------------------------------------------------------------------------
# Compile
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_artifact_obj(
    artifact_path: str,
    collection_key: str,
    records: list[dict[str, Any]],
    source_node_ids: list[str],
    project_id: str,
    vault_dir_repr: str,
    now: str,
) -> dict[str, Any]:
    """Assemble the ``{_provenance, <collection_key>: [...]}`` staging object."""
    return {
        "_provenance": {
            "record_type": "tier3_graph_compile",
            "generated_by": "runner/graph_compiler.py",
            "artifact": artifact_path,
            "collection_key": collection_key,
            "source_config_project_id": project_id,
            "source_vault": vault_dir_repr,
            "appendix_b_mapping": APPENDIX_B_MAPPING,
            "node_count": len(records),
            "source_node_ids": source_node_ids,
            "non_destructive": (
                "Compile-and-diff staging output (milestone 2, ticket 3). This "
                "does NOT overwrite the Tier 3 hand-lift; the graph-as-authoritative "
                "cutover (open-Q #4) is deferred to ticket 10."
            ),
            "compiled_at": now,
        },
        collection_key: records,
    }


def compile_tier3(
    config_path: Path,
    repo_root: Path,
    staging_root: Optional[Path] = None,
    now: Optional[str] = None,
) -> Tier3CompileResult:
    """Compile Tier 3 ``architecture_inputs`` from a vault to a staging location.

    Reads ``config_path`` and its vault, extracts every node routed by a
    ``tier == "tier3"`` binding that has an ``artifact_path``, and writes one
    staging JSON per distinct artifact.  Non-destructive: nothing under
    ``docs/tier3_.../`` is touched.

    Parameters
    ----------
    config_path:
        The ``graph.config.yaml`` to compile.
    repo_root:
        Repository root; staging paths are resolved beneath it.
    staging_root:
        Override for the staging directory (default: ``repo_root/`` +
        :data:`STAGING_REL`).  Tests use this for isolation.
    now:
        Override for the ``compiled_at`` timestamp (default: current UTC).  Pass a
        fixed value for byte-exact assertions; determinism across real runs holds
        modulo this one field.

    Returns
    -------
    Tier3CompileResult

    Raises
    ------
    GraphConfigError, VaultReadError, GraphCompileError
        On a malformed config, malformed vault, or an internally inconsistent
        node/binding — each naming the offending element.  Fails closed; never
        writes a partial result.
    """
    config = load_graph_config(config_path)
    vault_dir = config.resolve_vault_dir()
    vault = read_vault(vault_dir, config)

    if staging_root is None:
        staging_root = repo_root / STAGING_REL
    ts = now if now is not None else _now_iso()

    # A stable, repo-relative-ish repr of the vault dir for provenance (falls back
    # to the resolved path when it is outside the repo root, e.g. tmp_path tests).
    try:
        vault_dir_repr = vault_dir.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        vault_dir_repr = vault_dir.as_posix()

    # 1. Group Tier-3 artifact bindings by artifact_path, resolving the collection
    #    key and rejecting conflicting keys for one artifact (fail closed).
    collection_by_artifact: dict[str, str] = {}
    for binding in config.bindings:
        if binding.tier != "tier3" or binding.artifact_path is None:
            continue
        key = _collection_key_for(binding)
        existing = collection_by_artifact.get(binding.artifact_path)
        if existing is not None and existing != key:
            raise GraphCompileError(
                f"config routes conflicting collection_key {existing!r} and {key!r} "
                f"to one artifact {binding.artifact_path!r}; a Tier 3 artifact must "
                f"have a single collection key"
            )
        collection_by_artifact[binding.artifact_path] = key

    # 2. Assign each node to its artifact (first-match binding), checking
    #    self-binding consistency, preserving vault (relative-path) order.
    records_by_artifact: dict[str, list[dict[str, Any]]] = {
        ap: [] for ap in collection_by_artifact
    }
    node_ids_by_artifact: dict[str, list[str]] = {
        ap: [] for ap in collection_by_artifact
    }
    for node in vault.nodes:
        binding = vault.binding_for(node)
        # Fail closed on any node that self-declares a binding the config cannot
        # satisfy — checked for every node, not only the ones routed to a Tier-3
        # artifact, so a mis-declared artifact_path anywhere is never silently
        # dropped.
        _check_node_self_binding(node, binding)
        if binding is None or binding.tier != "tier3" or binding.artifact_path is None:
            continue
        ap = binding.artifact_path
        records_by_artifact[ap].append(extract_record(node))
        node_ids_by_artifact[ap].append(node.node_id)

    # 3. Emit one staging artifact per bound artifact_path (sorted for determinism).
    artifacts: list[CompiledArtifact] = []
    written: list[Path] = []
    for artifact_path in sorted(collection_by_artifact):
        collection_key = collection_by_artifact[artifact_path]
        records = records_by_artifact[artifact_path]
        node_ids = node_ids_by_artifact[artifact_path]
        staging_path = staging_root / artifact_path
        obj = _build_artifact_obj(
            artifact_path=artifact_path,
            collection_key=collection_key,
            records=records,
            source_node_ids=node_ids,
            project_id=config.project_id,
            vault_dir_repr=vault_dir_repr,
            now=ts,
        )
        atomic_write_json(obj, staging_path)
        artifacts.append(
            CompiledArtifact(
                artifact_path=artifact_path,
                collection_key=collection_key,
                records=tuple(records),
                source_node_ids=tuple(node_ids),
                staging_path=staging_path,
            )
        )
        written.append(staging_path)

    return Tier3CompileResult(
        project_id=config.project_id,
        vault_dir=vault_dir,
        artifacts=tuple(artifacts),
        staging_root=staging_root,
        written=tuple(written),
    )


# ---------------------------------------------------------------------------
# Diff against the ticket-14 hand-lift (the oracle)
# ---------------------------------------------------------------------------


def _record_identity(record: dict[str, Any]) -> Optional[str]:
    """Best-effort identity of a record: ``id`` then ``milestone_id`` (the hand-lift
    uses ``milestone_id`` for milestones), else ``None``."""
    for key in ("id", "milestone_id"):
        value = record.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _diff_one(
    artifact: CompiledArtifact, hand_lift_obj: Optional[dict[str, Any]]
) -> dict[str, Any]:
    """Diff one compiled artifact against its hand-lift file (by record identity)."""
    compiled_ids = [i for i in (_record_identity(r) for r in artifact.records) if i]
    if hand_lift_obj is None:
        return {
            "artifact": artifact.artifact_path,
            "collection_key": artifact.collection_key,
            "hand_lift_present": False,
            "compiled_count": len(artifact.records),
            "hand_lift_count": 0,
            "only_in_compiled": compiled_ids,
            "only_in_hand_lift": [],
            "in_both": [],
            "status": "no_oracle",
            "explanation": "No hand-lift file to diff against for this artifact.",
        }
    hand_records = hand_lift_obj.get(artifact.collection_key, [])
    hand_ids = [
        i for i in (_record_identity(r) for r in hand_records if isinstance(r, dict)) if i
    ]
    compiled_set, hand_set = set(compiled_ids), set(hand_ids)
    only_hand = sorted(hand_set - compiled_set)
    only_compiled = sorted(compiled_set - hand_set)
    in_both = sorted(compiled_set & hand_set)
    if not only_hand and not only_compiled:
        status = "converged"
        explanation = "Compiled record ids match the hand-lift exactly."
    else:
        status = "residual"
        explanation = (
            "Residual diff: the Tier-3 binding nodes for this artifact are not yet "
            "authored in the vault (ticket 8). The compile mechanism is verified; "
            "convergence lands when ticket 8 authors the binding nodes carrying "
            "these records. The hand-lift is not overwritten (ticket 10 cutover)."
        )
    return {
        "artifact": artifact.artifact_path,
        "collection_key": artifact.collection_key,
        "hand_lift_present": True,
        "compiled_count": len(artifact.records),
        "hand_lift_count": len(hand_ids),
        "only_in_compiled": only_compiled,
        "only_in_hand_lift": only_hand,
        "in_both": in_both,
        "status": status,
        "explanation": explanation,
    }


def diff_against_hand_lift(
    result: Tier3CompileResult, repo_root: Path
) -> dict[str, Any]:
    """Compare a compile *result* against the ticket-14 hand-lift, by record id.

    Non-destructive: reads the hand-lift ``docs/tier3_.../architecture_inputs/*.json``
    for comparison only.  Returns a structured report (also written to
    :data:`DIFF_REPORT_REL` by :func:`compile_and_diff`).
    """
    per_artifact: list[dict[str, Any]] = []
    for artifact in result.artifacts:
        hand_lift_path = repo_root / artifact.artifact_path
        hand_lift_obj: Optional[dict[str, Any]] = None
        if hand_lift_path.is_file():
            try:
                loaded = json.loads(hand_lift_path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    hand_lift_obj = loaded
            except (OSError, json.JSONDecodeError):
                hand_lift_obj = None
        per_artifact.append(_diff_one(artifact, hand_lift_obj))

    residual_total = sum(len(a["only_in_hand_lift"]) for a in per_artifact)
    converged = all(a["status"] == "converged" for a in per_artifact) and bool(
        per_artifact
    )
    return {
        "record_type": "tier3_graph_compile_diff",
        "generated_by": "runner/graph_compiler.py",
        "project_id": result.project_id,
        "oracle": "docs/tier3_project_instantiation/architecture_inputs (ticket-14 hand-lift)",
        "converged": converged,
        "convergence_basis": (
            "record identity (id/milestone_id) — 'converged' means the id-sets "
            "match, not that every field value matches. Field-level convergence "
            "is verified when ticket 8 authors the binding nodes carrying the "
            "record fields (and reconciled at the ticket-10 cutover)."
        ),
        "residual_total": residual_total,
        "artifacts": per_artifact,
        "note": (
            "compile(vault) ≈ hand_lift. Any residual is explained per-artifact: "
            "against the current methodology-only vault the Tier-3 binding nodes "
            "(folders 11–18) are not yet authored (ticket 8), so the compiled "
            "architecture_inputs are empty and the whole hand-lift is residual. "
            "The extraction mechanism is verified on a controlled fixture vault."
        ),
    }


def compile_and_diff(
    config_path: Path,
    repo_root: Path,
    staging_root: Optional[Path] = None,
    now: Optional[str] = None,
) -> tuple[Tier3CompileResult, dict[str, Any]]:
    """Compile Tier 3 to staging and write the diff report; return both.

    Convenience wrapper used by the ``--from-graph`` entry point and the module
    CLI.  Writes the diff report to :data:`DIFF_REPORT_REL` under *repo_root*.
    """
    result = compile_tier3(config_path, repo_root, staging_root=staging_root, now=now)
    report = diff_against_hand_lift(result, repo_root)
    atomic_write_json(report, repo_root / DIFF_REPORT_REL)
    return result, report


# ---------------------------------------------------------------------------
# CLI  (python -m runner.graph_compiler --config <path>)
# ---------------------------------------------------------------------------


def main(argv: Optional[list[str]] = None) -> int:
    """Run compile-and-diff from the command line.

    Exit codes: ``0`` success; ``2`` a fail-closed compile/config/vault error
    (naming the offending element); ``3`` an unexpected error.
    """
    parser = argparse.ArgumentParser(
        prog="python -m runner.graph_compiler",
        description=(
            "Deterministically compile Tier 3 architecture_inputs from a vault to a "
            "non-destructive staging location, and diff against the hand-lift."
        ),
    )
    parser.add_argument("--config", required=True, help="Path to graph.config.yaml.")
    parser.add_argument(
        "--repo-root",
        default=None,
        help="Repository root (default: auto-discovered via find_repo_root).",
    )
    parser.add_argument(
        "--staging-root",
        default=None,
        help=f"Override the staging directory (default: repo_root/{STAGING_REL}).",
    )
    args = parser.parse_args(argv)

    from runner.paths import find_repo_root

    try:
        repo_root = (
            Path(args.repo_root).resolve() if args.repo_root else find_repo_root()
        )
        staging_root = Path(args.staging_root) if args.staging_root else None
        result, report = compile_and_diff(
            Path(args.config), repo_root, staging_root=staging_root
        )
    except (GraphConfigError, VaultReadError, GraphCompileError) as exc:
        print(f"[graph-compile] FAIL-CLOSED: {exc}", file=sys.stderr, flush=True)
        return 2
    except Exception as exc:  # noqa: BLE001 — CLI boundary
        print(f"[graph-compile] ERROR: {exc}", file=sys.stderr, flush=True)
        return 3

    print(
        f"[graph-compile] project={result.project_id} "
        f"artifacts={len(result.artifacts)} "
        f"converged={report['converged']} residual={report['residual_total']}",
        flush=True,
    )
    for entry in report["artifacts"]:
        print(
            f"  {entry['artifact']}: compiled={entry['compiled_count']} "
            f"hand_lift={entry['hand_lift_count']} status={entry['status']}",
            flush=True,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
