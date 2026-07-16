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

Scope (tickets 3 + 6)
---------------------
Two extraction slices share one mechanism (read the vault, route by config
binding, extract declared fields verbatim, compute status from
``evidence_strength`` via Appendix B):

* **Tier 3 ``architecture_inputs``** (ticket 3) — ``tier == "tier3"`` bindings
  with an ``artifact_path`` → ``objectives.json`` etc. (:func:`compile_tier3`).
* **Part B ``proposal_section``** (ticket 6, the headline authoring move) —
  ``tier == "tier5"`` ``proposal_section`` bindings → ``{slug}_section.json``,
  one node per sub-section, ``content`` = the node's body prose,
  ``claim_statuses[].status`` computed from ``evidence_strength`` so an
  ``unconfirmed`` node yields an ``unresolved`` claim the drafting gates catch
  (:func:`compile_part_b`).

Against the *current* MSCA vault — methodology-only, with the Tier-3/Part-B
binding nodes (folders 11–18) not yet authored (ticket 8) — **both** slices
compile empty: the Tier-3 diff enumerates the whole hand-lift as an **explained
residual**, and no ``proposal_section`` nodes exist so no section is written.
Each extraction contract is proven on a controlled fixture vault
(``tests/runner/test_graph_compiler.py``, ``test_graph_compiler_part_b.py``).

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
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Optional

import yaml

from runner.atomic_write import atomic_write_json
from runner.graph_config import Binding, GraphConfig, GraphConfigError, load_graph_config
from runner.graph_schema import (
    EVIDENCE_TO_MACHINE_STATUS,
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
# Part B (Tier 5 proposal_section) constants  — ticket 6
# ---------------------------------------------------------------------------

#: The diff/summary report path for a Part B compile (repo-relative).
PART_B_REPORT_REL: str = "docs/tier4_orchestration_state/graph_compile/part_b_report.json"

#: **Appendix-B mapping to the LOWERCASE Tier-5 section claim-status vocabulary**
#: (``artifact_schema_specification.yaml`` →
#: ``validation_status.claim_statuses[].status`` enum
#: ``[confirmed, inferred, assumed, unresolved]``).  Derived from the canonical
#: :data:`~runner.graph_schema.EVIDENCE_TO_STATUS` so it can never drift from the
#: §12.2 mapping — it *is* that mapping, lowercased to the section vocabulary.
#: ``unconfirmed`` → ``unresolved`` (never ``confirmed``): an ``unconfirmed`` node
#: yields a claim the drafting gates correctly block (ticket 6 / Appendix B).
#: Aliased to the shared :data:`~runner.graph_schema.EVIDENCE_TO_MACHINE_STATUS`
#: so the section compiler and the pack deriver (ticket 7) can never disagree.
EVIDENCE_TO_CLAIM_STATUS: dict[str, str] = EVIDENCE_TO_MACHINE_STATUS

#: Severity order over section claim statuses, worst last.  ``overall_status`` is
#: the highest-risk status across a section's claims — the retained schema's own
#: definition ("A section with any Unresolved claim must have overall_status:
#: unresolved") — computed as a pure ``max`` over this order, not by inference.
_CLAIM_STATUS_SEVERITY: dict[str, int] = {
    "confirmed": 0,
    "inferred": 1,
    "assumed": 2,
    "unresolved": 3,
}

#: The retained Tier-5 section-schema spec (a Tier-2A-class artifact-schema
#: authority).  Read to learn which section-specific top-level fields each
#: criterion *requires* (impact → ``impact_pathway_refs`` / ``dec_coverage``;
#: implementation → ``wp_table_refs`` / ``gantt_ref`` / ``milestone_refs`` /
#: ``risk_register_ref``).  Sourcing the required set **from the schema** — never
#: hard-coding it — keeps the compiler generic (a second instance's own schema
#: drives its own required fields, D15) and honest (the schema is the structural
#: authority, §5/§2A).  Absent/unparseable ⇒ permissive (no required extras), so
#: a throwaway second instance still compiles.
SECTION_SCHEMA_SPEC_REL: str = (
    ".claude/workflows/system_orchestration/artifact_schema_specification.yaml"
)

#: Universal section top-level fields present on every criterion — subtracted
#: when deriving the per-section *required extra* fields from the schema.
_SECTION_CORE_TOP_LEVEL: frozenset[str] = frozenset(
    {
        "schema_id",
        "run_id",
        "artifact_status",
        "criterion",
        "sub_sections",
        "validation_status",
        "traceability_footer",
    }
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


@dataclass(frozen=True)
class CompiledSection:
    """One compiled Part B section (the JSON for one ``{slug}_section.json``)."""

    slug: str
    """Section slug (``excellence`` / ``impact`` / ``implementation``) — drives the
    filename and ``schema_id``.  Declared by the nodes, never hard-coded here."""
    criterion: str
    """The evaluation-criterion display string carried into the section JSON."""
    artifact_path: str
    """Canonical ``docs/**`` target (repo-relative, POSIX)."""
    section: dict[str, Any]
    """The assembled section object, exactly as written."""
    source_node_ids: tuple[str, ...]
    """The proposal_section node ids extracted, in sub-section order."""
    staging_path: Path
    """Absolute path the section was written to (under ``staging_root``, whose
    default is :data:`STAGING_REL`)."""


@dataclass(frozen=True)
class PartBCompileResult:
    """The result of a Part B (Tier 5 ``proposal_section``) compile run."""

    project_id: str
    run_id: str
    vault_dir: Path
    sections: tuple[CompiledSection, ...]
    staging_root: Path
    written: tuple[Path, ...]
    compiled_at: str


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
# Part B — Tier 5 ``proposal_section`` extraction  (ticket 6)
# ---------------------------------------------------------------------------
#
# The headline authoring move: compile full Part B prose authored in the graph
# (one ``proposal_section`` node per sub-section) into the ``{slug}_section.json``
# the retained Tier 5 schema and the Phase-8 gates consume.  This reuses the same
# mechanism as the Tier-3 slice above — read the vault, route by config binding,
# extract declared fields verbatim, compute status from ``evidence_strength`` via
# Appendix B — never authoring a word.  Non-destructive: it stages under Tier 4,
# never over the real ``docs/tier5_.../proposal_sections/`` (ticket-10 cutover).


def _require_section_str(node: GraphNode, field: str) -> str:
    """Return a required non-blank string front-matter *field* of a section node.

    Fails closed (naming the node and field) — a ``proposal_section`` node that
    omits its ``section_slug`` / ``criterion`` / ``sub_section_id`` cannot be
    routed or shaped, so the compiler refuses it rather than guessing.
    """
    value = node.front_matter.get(field)
    if not isinstance(value, str) or not value.strip():
        raise GraphCompileError(
            f"{node.rel_path}: proposal_section node is missing required string "
            f"field {field!r} (needed to compile it into a Tier 5 section)"
        )
    return value.strip()


def extract_sub_section(node: GraphNode) -> dict[str, Any]:
    """Extract one ``sub_sections[]`` entry from a ``proposal_section`` *node*.

    ``content`` is the node's **body prose**, verbatim except for trimming the
    surrounding blank lines the front-matter split leaves (a deterministic
    normalisation, never a rewrite).  ``word_count`` is the only *derived* field
    (whitespace token count — the same rule as the milestone-1 section
    assembler).  The additive-optional D4 graph-provenance fields ``page_estimate``
    and ``source_nodes`` are carried **verbatim** when present.  No prose is
    authored and no field is inferred.
    """
    sub_id = _require_section_str(node, "sub_section_id")
    content = node.body.strip()
    if not content:
        raise GraphCompileError(
            f"{node.rel_path}: proposal_section body is empty; the retained Tier 5 "
            f"schema requires non-empty sub-section content — the compiler will not "
            f"author prose for it"
        )
    entry: dict[str, Any] = {
        "sub_section_id": sub_id,
        "title": node.title,
        "content": content,
        "word_count": len(content.split()),
    }
    page_estimate = node.front_matter.get("page_estimate")
    if page_estimate is not None:
        if isinstance(page_estimate, bool) or not isinstance(page_estimate, int):
            raise GraphCompileError(
                f"{node.rel_path}: page_estimate must be an integer when present "
                f"(got {page_estimate!r})"
            )
        entry["page_estimate"] = page_estimate
    source_nodes = node.front_matter.get("source_nodes")
    if source_nodes is not None:
        if not isinstance(source_nodes, list) or not all(
            isinstance(x, str) for x in source_nodes
        ):
            raise GraphCompileError(
                f"{node.rel_path}: source_nodes must be a list of strings when "
                f"present (got {source_nodes!r})"
            )
        entry["source_nodes"] = list(source_nodes)
    return entry


def _section_claim(node: GraphNode) -> dict[str, Any]:
    """One ``validation_status.claim_statuses[]`` entry from a section *node*.

    ``status`` is **computed** from ``evidence_strength`` via the Appendix-B
    lowercase lookup — never read from the node — so an ``unconfirmed`` node
    yields an ``unresolved`` claim the drafting gates correctly catch, and a
    ``synthesis``/``inference`` node can never land as a ``confirmed`` claim.
    """
    return {
        "claim_id": node.node_id,
        "claim_summary": node.title,
        "status": EVIDENCE_TO_CLAIM_STATUS[node.evidence_strength],
    }


def _derive_overall_status(statuses: list[str]) -> str:
    """The highest-risk status across a section's claims (schema definition).

    A pure ``max`` over :data:`_CLAIM_STATUS_SEVERITY` — not inference.  The empty
    case is unreachable in practice (a section always has ≥1 node → ≥1 claim), but
    its total default is the **fail-safe** ``unresolved``, not the optimistic
    ``confirmed`` — an anti-fabrication system prefers a blocking status over a
    green one when it has nothing to go on (§12.4 / §13.8).
    """
    if not statuses:
        return "unresolved"
    return max(statuses, key=lambda s: _CLAIM_STATUS_SEVERITY[s])


def _partb_out_dir(artifact_path: str) -> str:
    """The output *directory* for a tier5 ``proposal_section`` binding.

    The binding's ``artifact_path`` is normally a directory
    (``docs/tier5_.../proposal_sections``); a trailing ``.json`` file target is
    reduced to its parent so the per-slug ``{slug}_section.json`` files land
    beside it.
    """
    ap = artifact_path.rstrip("/")
    if ap.endswith(".json"):
        return PurePosixPath(ap).parent.as_posix()
    return ap


def _union_section_source_refs(nodes: list[GraphNode]) -> list[dict[str, Any]]:
    """Union the ``source_refs`` declared across a section's *nodes*, deduped+sorted.

    Each entry is a ``{"tier": <1-4>, "source_path": <str>}`` — the Tier 1-4
    provenance the retained schema's ``traceability_footer.primary_sources``
    requires.  De-duplicated by ``(tier, source_path)`` and sorted so the bytes
    are stable regardless of node order (mirrors the assembler's union).  Fails
    closed when **no** node declares a source: the schema requires a non-empty
    ``primary_sources`` and the compiler will not invent one.
    """
    seen: dict[tuple[int, str], dict[str, Any]] = {}
    for node in nodes:
        refs = node.front_matter.get("source_refs")
        if refs is None:
            continue
        if not isinstance(refs, list):
            raise GraphCompileError(
                f"{node.rel_path}: source_refs must be a list when present"
            )
        for ref in refs:
            if not isinstance(ref, dict):
                raise GraphCompileError(
                    f"{node.rel_path}: each source_refs entry must be a mapping "
                    f"(got {type(ref).__name__})"
                )
            tier = ref.get("tier")
            source_path = ref.get("source_path")
            if isinstance(tier, bool) or not isinstance(tier, int) or not 1 <= tier <= 4:
                raise GraphCompileError(
                    f"{node.rel_path}: source_refs.tier must be an int 1-4 "
                    f"(got {tier!r})"
                )
            if not isinstance(source_path, str) or not source_path.strip():
                raise GraphCompileError(
                    f"{node.rel_path}: source_refs.source_path must be a non-empty "
                    f"string (got {source_path!r})"
                )
            seen[(tier, source_path)] = {"tier": tier, "source_path": source_path}
    if not seen:
        listed = ", ".join(n.rel_path for n in nodes)
        raise GraphCompileError(
            f"section has no traceability source_refs on any bound node ({listed}); "
            f"the retained Tier 5 schema requires a non-empty "
            f"traceability_footer.primary_sources — declare source_refs; the "
            f"compiler will not invent a source"
        )
    return [seen[key] for key in sorted(seen)]


def _merge_section_extra_fields(nodes: list[GraphNode], slug: str) -> dict[str, Any]:
    """Merge the ``section_extra_fields`` declared across a section's *nodes*.

    Section-specific top-level fields the gates require (``impact_pathway_refs`` /
    ``dec_coverage`` for Impact; ``wp_table_refs`` / ``gantt_ref`` /
    ``milestone_refs`` / ``risk_register_ref`` for Implementation) are authored in
    a bound node's ``section_extra_fields`` and passed through **verbatim** — the
    compiler never invents them.  Fails closed if two nodes declare the same key
    with conflicting values (the compiler will not choose).
    """
    merged: dict[str, Any] = {}
    origin: dict[str, str] = {}
    for node in nodes:
        extra = node.front_matter.get("section_extra_fields")
        if extra is None:
            continue
        if not isinstance(extra, dict):
            raise GraphCompileError(
                f"{node.rel_path}: section_extra_fields must be a mapping when "
                f"present (got {type(extra).__name__})"
            )
        for key, value in extra.items():
            if key in merged and merged[key] != value:
                raise GraphCompileError(
                    f"section {slug!r}: conflicting section_extra_fields[{key!r}] "
                    f"declared by {origin[key]} and {node.rel_path}; the compiler "
                    f"will not choose for you"
                )
            merged[key] = value
            origin[key] = node.rel_path
    return merged


def _load_required_section_fields(repo_root: Path) -> dict[str, frozenset[str]]:
    """Derive ``{slug: required-extra-field set}`` from the retained section schema.

    Reads :data:`SECTION_SCHEMA_SPEC_REL` and, in **any** top-level mapping
    container (the real spec nests them under ``tier5_deliverable_schemas``; a
    fixture may use another key — the loader does not assume the container name),
    finds every ``*_section`` entry whose ``schema_id_value`` is an
    ``orch.tier5.<slug>_section.v1``.  For each, returns its ``required: true``
    top-level fields minus the universal core (:data:`_SECTION_CORE_TOP_LEVEL`),
    keyed by ``<slug>`` so it matches the node-declared ``section_slug``.
    Permissive on any read/parse failure — a throwaway second instance without
    this spec still compiles (D15).
    """
    spec_path = repo_root / SECTION_SCHEMA_SPEC_REL
    try:
        raw = yaml.safe_load(spec_path.read_text(encoding="utf-8-sig"))
    except (OSError, yaml.YAMLError):
        return {}
    if not isinstance(raw, dict):
        return {}
    out: dict[str, frozenset[str]] = {}
    # Scan every top-level mapping container for section-schema entries — the
    # container key is not assumed (real: tier5_deliverable_schemas).
    for container in raw.values():
        if not isinstance(container, dict):
            continue
        for name, spec in container.items():
            if not (isinstance(name, str) and name.endswith("_section")):
                continue
            if not isinstance(spec, dict):
                continue
            match = re.match(
                r"orch\.tier5\.(.+)_section\.v1", str(spec.get("schema_id_value", ""))
            )
            if match is None:
                continue  # only Tier 5 section schemas drive Part B required fields
            slug = match.group(1)
            fields = spec.get("fields")
            if not isinstance(fields, dict):
                continue
            out[slug] = frozenset(
                key
                for key, field_spec in fields.items()
                if isinstance(field_spec, dict)
                and field_spec.get("required") is True
                and key not in _SECTION_CORE_TOP_LEVEL
            )
    return out


def _validate_compiled_section(
    section: dict[str, Any], slug: str, required_extra: frozenset[str]
) -> None:
    """Assert a compiled *section* is structurally compliant with the retained schema.

    A belt-and-suspenders check that the object the compiler is about to write
    carries every field the retained Tier 5 section schema marks required — the
    universal core plus this section's ``required_extra`` — with a well-formed
    ``sub_sections`` and non-empty ``traceability_footer.primary_sources``.
    Raises :class:`GraphCompileError` naming the missing field rather than emit a
    schema-non-compliant artifact.
    """
    for field in ("schema_id", "run_id", "criterion", "sub_sections",
                  "validation_status", "traceability_footer"):
        if field not in section:
            raise GraphCompileError(f"section {slug!r}: missing required field {field!r}")
    missing_extra = sorted(required_extra - set(section))
    if missing_extra:
        raise GraphCompileError(
            f"section {slug!r} is missing schema-required field(s) {missing_extra}; "
            f"declare them via 'section_extra_fields' on a bound proposal_section "
            f"node — the compiler will not invent them"
        )
    if not section["sub_sections"]:
        raise GraphCompileError(f"section {slug!r}: sub_sections is empty")
    for sub in section["sub_sections"]:
        for field in ("sub_section_id", "title", "content", "word_count"):
            if field not in sub:
                raise GraphCompileError(
                    f"section {slug!r}: a sub_section is missing {field!r}"
                )
    overall = section["validation_status"].get("overall_status")
    if overall not in _CLAIM_STATUS_SEVERITY:
        raise GraphCompileError(
            f"section {slug!r}: overall_status {overall!r} is not one of "
            f"{sorted(_CLAIM_STATUS_SEVERITY)}"
        )
    if not section["traceability_footer"].get("primary_sources"):
        raise GraphCompileError(
            f"section {slug!r}: traceability_footer.primary_sources is empty"
        )


def compile_part_b(
    config_path: Path,
    repo_root: Path,
    staging_root: Optional[Path] = None,
    now: Optional[str] = None,
    run_id: Optional[str] = None,
) -> PartBCompileResult:
    """Compile Part B ``proposal_section`` nodes into Tier 5 section artifacts.

    Reads ``config_path`` and its vault, collects every node routed by a
    ``tier == "tier5"`` binding with an ``artifact_path``, groups them by their
    declared ``section_slug``, and writes one ``{slug}_section.json`` per group to
    a **staging** location (never over the real ``docs/tier5_.../`` — non-
    destructive, the ticket-10 cutover is deferred).  ``content`` is each node's
    body prose verbatim; ``claim_statuses[].status`` is computed from
    ``evidence_strength`` via Appendix B.

    Parameters mirror :func:`compile_tier3`; ``run_id`` defaults to the config's
    ``project_id`` so output is byte-stable for an unchanged graph.

    Raises
    ------
    GraphConfigError, VaultReadError, GraphCompileError
        On a malformed config/vault, a tier5 binding matching a non-
        ``proposal_section`` node, a section node missing a required field,
        conflicting ``criterion`` / ``section_extra_fields`` across a section, an
        absent required section field, or an empty traceability set — each naming
        the offending element.  Fails closed; never writes a partial result.
    """
    config = load_graph_config(config_path)
    vault_dir = config.resolve_vault_dir()
    vault = read_vault(vault_dir, config)

    if staging_root is None:
        staging_root = repo_root / STAGING_REL
    ts = now if now is not None else _now_iso()
    rid = run_id if run_id is not None else config.project_id
    required_fields = _load_required_section_fields(repo_root)

    # 1. Collect Part B nodes (tier5 binding + artifact_path), grouped by slug,
    #    in vault (relative-path) order.  Fail closed on a self-binding
    #    contradiction or a non-proposal_section node routed to a section artifact.
    groups: dict[str, list[GraphNode]] = {}
    out_dir_for_slug: dict[str, str] = {}
    for node in vault.nodes:
        binding = vault.binding_for(node)
        _check_node_self_binding(node, binding)
        if binding is None or binding.tier != "tier5" or binding.artifact_path is None:
            continue
        if node.node_type != "proposal_section":
            raise GraphCompileError(
                f"{node.rel_path}: a tier5 artifact binding "
                f"(artifact_path={binding.artifact_path!r}) matched a "
                f"{node.node_type!r} node; only proposal_section nodes extract to a "
                f"Part B section artifact"
            )
        slug = _require_section_str(node, "section_slug")
        groups.setdefault(slug, []).append(node)
        out_dir = _partb_out_dir(binding.artifact_path)
        prev = out_dir_for_slug.get(slug)
        if prev is not None and prev != out_dir:
            raise GraphCompileError(
                f"section {slug!r} is routed to two output directories "
                f"({prev!r} and {out_dir!r}); one section has one output location"
            )
        out_dir_for_slug[slug] = out_dir

    # 2. Build + write one section per slug (slugs sorted for determinism).
    sections: list[CompiledSection] = []
    written: list[Path] = []
    for slug in sorted(groups):
        nodes = groups[slug]  # already in vault order (vault.nodes is sorted)
        # Typo guard: when the retained schema is available, a declared
        # section_slug must name a real section in it — otherwise a typo'd
        # `section_slug: excellance` would silently emit a non-canonical
        # excellance_section.json with zero required-field enforcement.  Permissive
        # when no schema is present (a throwaway second instance, D15).
        if required_fields and slug not in required_fields:
            raise GraphCompileError(
                f"section_slug {slug!r} is not a section in the retained Tier 5 "
                f"schema (known: {sorted(required_fields)}); a proposal_section node "
                f"declares an unknown section — fix the section_slug (a typo emits a "
                f"non-canonical, unenforced section file)"
            )
        criteria = {_require_section_str(node, "criterion") for node in nodes}
        if len(criteria) != 1:
            raise GraphCompileError(
                f"proposal_section nodes for section {slug!r} declare conflicting "
                f"criterion values {sorted(criteria)}; one section has one criterion"
            )
        criterion = next(iter(criteria))

        sub_sections = [extract_sub_section(node) for node in nodes]
        sub_ids = [s["sub_section_id"] for s in sub_sections]
        duplicates = sorted({sid for sid in sub_ids if sub_ids.count(sid) > 1})
        if duplicates:
            raise GraphCompileError(
                f"section {slug!r}: duplicate sub_section_id(s) {duplicates} across "
                f"its proposal_section nodes; each sub-section id must be unique "
                f"within a section"
            )
        claim_statuses = [_section_claim(node) for node in nodes]
        overall_status = _derive_overall_status([c["status"] for c in claim_statuses])
        primary_sources = _union_section_source_refs(nodes)
        extra_fields = _merge_section_extra_fields(nodes, slug)

        section: dict[str, Any] = {
            "schema_id": f"orch.tier5.{slug}_section.v1",
            "run_id": rid,
            "criterion": criterion,
            "sub_sections": sub_sections,
        }
        # Section-specific extras (verbatim, sorted for byte-stability), placed
        # before validation_status/traceability_footer as the assembler does.
        for key in sorted(extra_fields):
            section[key] = extra_fields[key]
        section["validation_status"] = {
            "overall_status": overall_status,
            "claim_statuses": claim_statuses,
        }
        section["traceability_footer"] = {
            "primary_sources": primary_sources,
            "no_unsupported_claims_declaration": all(
                c["status"] in ("confirmed", "inferred") for c in claim_statuses
            ),
        }

        _validate_compiled_section(section, slug, required_fields.get(slug, frozenset()))

        artifact_rel = f"{out_dir_for_slug[slug]}/{slug}_section.json"
        staging_path = staging_root / artifact_rel
        atomic_write_json(section, staging_path)
        sections.append(
            CompiledSection(
                slug=slug,
                criterion=criterion,
                artifact_path=artifact_rel,
                section=section,
                source_node_ids=tuple(node.node_id for node in nodes),
                staging_path=staging_path,
            )
        )
        written.append(staging_path)

    return PartBCompileResult(
        project_id=config.project_id,
        run_id=rid,
        vault_dir=vault_dir,
        sections=tuple(sections),
        staging_root=staging_root,
        written=tuple(written),
        compiled_at=ts,
    )


def part_b_report(result: PartBCompileResult) -> dict[str, Any]:
    """A structured summary of a Part B compile (written to :data:`PART_B_REPORT_REL`)."""
    return {
        "record_type": "part_b_graph_compile",
        "generated_by": "runner/graph_compiler.py",
        "project_id": result.project_id,
        "run_id": result.run_id,
        "appendix_b_mapping": "; ".join(
            f"{k}->{v}" for k, v in EVIDENCE_TO_CLAIM_STATUS.items()
        ),
        "non_destructive": (
            "Compile-and-stage output (milestone 2, ticket 6). This does NOT "
            "overwrite the Tier 5 proposal_sections; the graph-as-authoritative "
            "cutover (open-Q #4) is deferred to ticket 10."
        ),
        "section_count": len(result.sections),
        "compiled_at": result.compiled_at,
        "sections": [
            {
                "slug": s.slug,
                "criterion": s.criterion,
                "artifact": s.artifact_path,
                "sub_section_count": len(s.section["sub_sections"]),
                "overall_status": s.section["validation_status"]["overall_status"],
                "source_node_ids": list(s.source_node_ids),
            }
            for s in result.sections
        ],
    }


def compile_part_b_and_report(
    config_path: Path,
    repo_root: Path,
    staging_root: Optional[Path] = None,
    now: Optional[str] = None,
    run_id: Optional[str] = None,
) -> tuple[PartBCompileResult, dict[str, Any]]:
    """Compile Part B to staging and write the summary report; return both."""
    result = compile_part_b(
        config_path, repo_root, staging_root=staging_root, now=now, run_id=run_id
    )
    report = part_b_report(result)
    atomic_write_json(report, repo_root / PART_B_REPORT_REL)
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
        part_b_result, part_b = compile_part_b_and_report(
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
        f"converged={report['converged']} residual={report['residual_total']} "
        f"part_b_sections={part_b['section_count']}",
        flush=True,
    )
    for entry in report["artifacts"]:
        print(
            f"  {entry['artifact']}: compiled={entry['compiled_count']} "
            f"hand_lift={entry['hand_lift_count']} status={entry['status']}",
            flush=True,
        )
    for entry in part_b["sections"]:
        print(
            f"  {entry['artifact']}: sub_sections={entry['sub_section_count']} "
            f"criterion={entry['criterion']!r} overall={entry['overall_status']}",
            flush=True,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
