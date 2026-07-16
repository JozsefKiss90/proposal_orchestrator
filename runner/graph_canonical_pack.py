"""
Pack-from-graph — canonical reference pack from graph nodes (milestone 2, ticket
7; D13-graph).

The graph-sourced successor to the milestone-1 (ticket-10) Tier-3-sourced
canonical-pack deriver (:mod:`runner.phase8_canonical_pack`).  It produces the
**same** ``orch.phase8.canonical_reference_pack.v1`` artifact — the canonical
reference the Phase-8 preservation gates check Part B prose against — but reads
its confirmed arrays (objectives, outcomes, work packages, deliverables,
partners) from **graph nodes** via the ticket-1 reader instead of from
``docs/**`` JSON.

Why graph-sourced (D13-graph)
-----------------------------
Because pack **and** Part B prose then share the *same* source — the vault
(:mod:`runner.graph_compiler` compiles the prose from ``proposal_section`` nodes;
this derives the pack from the binding nodes).  One source cannot drift from
itself, so the canonical-preservation contradiction detectors
(``runner.predicates.phase8_section_predicates``) pass on the compiled sections
by construction — the drift the milestone-1 deriver had to guard against across
two artifacts is eliminated at the source.

Guarantees (ticket 7)
---------------------

* **Deterministic & non-inferential.**  No Claude, no domain reasoning.  Every
  field is a verbatim copy of a declared node front-matter value; the only
  computed field is the per-entry ``provenance`` — a **pure Appendix-B lookup**
  (:data:`~runner.graph_schema.EVIDENCE_TO_MACHINE_STATUS`) over the node's
  ``evidence_strength``.  Same vault ⇒ byte-identical pack.
* **Provenance-carrying, anti-fabrication.**  Every pack entry carries its
  ``source_node`` and a ``provenance`` derived from that node's
  ``evidence_strength``: ``source_grounded`` → ``confirmed``,
  ``synthesis``/``inference`` → ``inferred``, ``unconfirmed`` → ``unresolved``.
  An ``unconfirmed``/synthesis node therefore can **never** be emitted as a
  ``confirmed`` canonical fact.
* **Declared assumptions quarantined.**  Operator declarations are still read
  from the Tier 3 ``working_assumptions.json`` substrate (ticket 15) — the graph
  does not author operator assumptions — and are passed through **verbatim** into
  a separate ``declared_assumptions`` array tagged ``provenance: "assumed"``,
  never merged into a confirmed array.  The rendering is the **single** shared
  :meth:`runner.working_assumptions.WorkingAssumptions.as_canonical_pack_entries`
  that the Tier-3-sourced deriver also uses, so the two packs cannot drift.

Constitutional authority
------------------------
Subordinate to CLAUDE.md.  A deterministic, Claude-free deriver (§17.5.3 / C2
class) that reads declared vault fields and writes one canonical artifact via
``_atomic_write``; it invents no facts (§13.3) and evaluates no gate (§17.6.2).
Non-destructive by default: it stages under Tier 4 ``graph_compile/`` rather than
over the run's ``canonical_reference_pack.json`` (the ticket-10 cutover chooses
the authoritative source).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Optional

from runner.atomic_write import atomic_write_json
from runner.graph_config import GraphConfigError, load_graph_config
from runner.graph_schema import EVIDENCE_TO_MACHINE_STATUS
from runner.vault_reader import GraphNode, Vault, VaultReadError, read_vault
from runner.working_assumptions import load_working_assumptions

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: The canonical-pack artifact's schema id (shared with the milestone-1 deriver).
SCHEMA_ID: str = "orch.phase8.canonical_reference_pack.v1"

#: The canonical pack's real run path (Tier 4).  This deriver does **not** write
#: here by default — the graph-as-authoritative cutover (open-Q #4) is deferred to
#: ticket 10; until then it stages (below), non-destructively.
CANONICAL_PACK_REL: str = (
    "docs/tier4_orchestration_state/phase_outputs"
    "/phase8_drafting_review/canonical_reference_pack.json"
)

#: Default (non-destructive) staging path, mirroring the docs path under the
#: shared ``graph_compile/staging`` root the ticket-3/6 compiler also stages to.
DEFAULT_STAGING_REL: str = (
    "docs/tier4_orchestration_state/graph_compile/staging/" + CANONICAL_PACK_REL
)


# ---------------------------------------------------------------------------
# Extraction (verbatim copy + pure Appendix-B provenance)
# ---------------------------------------------------------------------------


def _provenance(node: GraphNode) -> str:
    """The per-entry provenance tag: Appendix-B lookup over ``evidence_strength``.

    Pure (a dict lookup, never inference).  ``evidence_strength`` is already
    schema-validated by the reader, so the lookup is total.
    """
    return EVIDENCE_TO_MACHINE_STATUS[node.evidence_strength]


def _copy_fields(node: GraphNode, keys: tuple[str, ...]) -> dict[str, Any]:
    """Copy the present *keys* from a node's front-matter, verbatim (in *keys* order)."""
    entry: dict[str, Any] = {}
    for key in keys:
        if key in node.front_matter:
            entry[key] = node.front_matter[key]
    return entry


def _tag(entry: dict[str, Any], node: GraphNode) -> dict[str, Any]:
    """Attach provenance to a lifted *entry* (in place): the source node id, its
    raw ``evidence_strength``, and the Appendix-B ``provenance`` projection.

    Carrying **both** the raw ``evidence_strength`` and its derived ``provenance``
    is deliberate — ticket 7 asks each entry to carry "source node +
    ``evidence_strength``", and a downstream consumer can audit the projection
    rather than trust it.
    """
    entry["provenance"] = _provenance(node)
    entry["evidence_strength"] = node.evidence_strength
    entry["source_node"] = node.node_id
    return entry


def _bound_extraction_nodes(vault: Vault, node_type: str) -> list[GraphNode]:
    """Nodes of *node_type* routed by a config binding **with an artifact_path**.

    The pack is derived only from **bound** nodes — a node whose
    ``graph.config.yaml`` binding names a concrete ``artifact_path`` extraction
    target — exactly as the compiler folder-scopes Tier 3 (ticket 3): this
    excludes the methodology-graph nodes that *share* a binding node type
    (e.g. the reference vault's ``partner`` role nodes in an **unbound**
    ``08_partners`` folder) so they can never masquerade as consortium canonical
    facts.  Returns nodes in vault (relative-path) order for determinism.
    """
    out: list[GraphNode] = []
    for node in vault.nodes:
        if node.node_type != node_type:
            continue
        binding = vault.binding_for(node)
        if binding is None or binding.artifact_path is None:
            continue
        out.append(node)
    return out


def _extract_objectives(vault: Vault) -> list[dict[str, Any]]:
    """Objectives from bound ``objective`` nodes.  ``id``/``title`` from core;
    ``measurable_target``/``responsible_partner``/``contributing_partners`` passed
    through when declared."""
    out: list[dict[str, Any]] = []
    for node in _bound_extraction_nodes(vault, "objective"):
        entry: dict[str, Any] = {"id": node.node_id, "title": node.title}
        entry.update(
            _copy_fields(
                node, ("measurable_target", "responsible_partner", "contributing_partners")
            )
        )
        out.append(_tag(entry, node))
    return out


def _extract_outcomes(vault: Vault) -> list[dict[str, Any]]:
    """Outcomes from bound ``outcome`` nodes, carrying their ``linked_*`` cross-refs."""
    out: list[dict[str, Any]] = []
    for node in _bound_extraction_nodes(vault, "outcome"):
        entry: dict[str, Any] = {"id": node.node_id, "title": node.title}
        entry.update(
            _copy_fields(
                node, ("linked_objectives", "linked_wp_ids", "linked_deliverable_ids")
            )
        )
        out.append(_tag(entry, node))
    return out


def _extract_wps_and_deliverables(
    vault: Vault,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Work packages from bound ``work_package`` nodes, and their **nested** deliverables.

    ``wp_id`` is the declared front-matter value (falling back to the node id).
    Deliverables are the entries of the node's ``deliverables`` front-matter list
    (mirroring the milestone-1 ``wp_structure.json`` shape); each is tagged with
    its parent WP node's provenance and ``source_node`` — a deliverable is not its
    own node here, so it inherits its WP node's provenance honestly.
    """
    wps: list[dict[str, Any]] = []
    deliverables: list[dict[str, Any]] = []
    for node in _bound_extraction_nodes(vault, "work_package"):
        wp_id = node.front_matter.get("wp_id") or node.node_id
        wp_entry: dict[str, Any] = {"wp_id": wp_id, "title": node.title}
        wp_entry.update(_copy_fields(node, ("lead_partner",)))
        wps.append(_tag(wp_entry, node))

        raw_deliverables = node.front_matter.get("deliverables")
        if not isinstance(raw_deliverables, list):
            continue
        for deliv in raw_deliverables:
            if not isinstance(deliv, dict):
                continue
            d_entry: dict[str, Any] = {}
            for key in ("deliverable_id", "title", "due_month", "type"):
                if key in deliv:
                    d_entry[key] = deliv[key]
            d_entry["parent_wp"] = wp_id
            if d_entry.get("deliverable_id"):
                deliverables.append(_tag(d_entry, node))
    return wps, deliverables


def _extract_partners(vault: Vault) -> list[dict[str, Any]]:
    """Partners from bound ``partner`` nodes, preserving name/country/role verbatim.

    Bound-only (see :func:`_bound_extraction_nodes`): the reference vault's
    methodology ``partner`` role nodes live in an unbound folder and are excluded
    — a consortium partner is one the config explicitly binds to a partners
    artifact.
    """
    out: list[dict[str, Any]] = []
    for node in _bound_extraction_nodes(vault, "partner"):
        entry = _copy_fields(node, ("short_name", "legal_name", "country", "role"))
        if entry.get("short_name") or entry.get("legal_name"):
            out.append(_tag(entry, node))
    return out


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------


def build_canonical_pack_from_graph(
    config_path: Path,
    repo_root: Path,
    run_id: Optional[str] = None,
    out_path: Optional[Path] = None,
) -> tuple[Path, dict[str, Any]]:
    """Derive the canonical reference pack from a vault; return ``(path, pack)``.

    Reads ``config_path`` and its vault, extracts the confirmed arrays from graph
    nodes and the declared assumptions from ``working_assumptions.json``, and
    atomically writes the ``orch.phase8.canonical_reference_pack.v1`` artifact.

    Parameters
    ----------
    config_path:
        The ``graph.config.yaml`` whose vault to derive from.
    repo_root:
        Repository root — used to resolve ``working_assumptions.json`` and the
        default staging output path.
    run_id:
        The pack's ``run_id`` (defaults to the config's ``project_id`` so the
        output is byte-stable for an unchanged graph).
    out_path:
        Where to write (defaults to the non-destructive staging path
        :data:`DEFAULT_STAGING_REL` under *repo_root*; ticket 10 may point this at
        the real :data:`CANONICAL_PACK_REL`).

    Raises
    ------
    GraphConfigError, VaultReadError, WorkingAssumptionsError
        On a malformed config/vault or a present-but-malformed
        ``working_assumptions.json`` — each fails closed, naming the offending
        element; the deriver never fabricates a missing fact.

    .. note::
       **Ticket-10 cutover pre-condition.**  Against today's methodology-only
       vault (and any pre-authoring vault) the confirmed arrays are legitimately
       empty, so this deriver writes an empty pack — safe while it stages a
       *preview*.  The milestone-1 sibling
       (:func:`runner.phase8_canonical_pack.build_phase8_canonical_reference_pack`)
       fails closed on an empty required array precisely because the Phase-8
       preservation predicates *vacuously pass* on an empty pack (§12.4).  Before
       ticket 10 repoints ``out_path`` at :data:`CANONICAL_PACK_REL` (the pack a
       real run's gates read), that same non-empty backstop must be restored here
       — otherwise an empty graph would silently satisfy every preservation gate.
    """
    config = load_graph_config(config_path)
    vault = read_vault(config.resolve_vault_dir(), config)
    rid = run_id if run_id is not None else config.project_id

    wps, deliverables = _extract_wps_and_deliverables(vault)
    pack: dict[str, Any] = {
        "schema_id": SCHEMA_ID,
        "run_id": rid,
        "objectives": _extract_objectives(vault),
        "outcomes": _extract_outcomes(vault),
        "wps": wps,
        "deliverables": deliverables,
        "partners": _extract_partners(vault),
        # Operator declarations stay operator-sourced (the graph does not author
        # assumptions) — rendered by the shared quarantine renderer both derivers
        # use, so a declared value can never masquerade as a confirmed fact and
        # the two packs cannot drift.  Fail-closed on a malformed file; absent ⇒ [].
        "declared_assumptions": load_working_assumptions(repo_root).as_canonical_pack_entries(),
        "aliases": [],
    }

    target = out_path if out_path is not None else repo_root / DEFAULT_STAGING_REL
    atomic_write_json(pack, target, prefix="graph_canonical_pack_")
    return target, pack


# ---------------------------------------------------------------------------
# CLI  (python -m runner.graph_canonical_pack --config <path>)
# ---------------------------------------------------------------------------


def main(argv: Optional[list[str]] = None) -> int:
    """Derive the canonical pack from a vault from the command line.

    Exit codes: ``0`` success; ``2`` a fail-closed config/vault/assumptions error
    (naming the offending element); ``3`` an unexpected error.
    """
    parser = argparse.ArgumentParser(
        prog="python -m runner.graph_canonical_pack",
        description=(
            "Deterministically derive the Phase-8 canonical reference pack from a "
            "per-project vault (graph nodes) to a non-destructive staging location."
        ),
    )
    parser.add_argument("--config", required=True, help="Path to graph.config.yaml.")
    parser.add_argument(
        "--repo-root",
        default=None,
        help="Repository root (default: auto-discovered via find_repo_root).",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Pack run_id (default: the config's project_id).",
    )
    parser.add_argument(
        "--out",
        default=None,
        help=f"Output path (default: repo_root/{DEFAULT_STAGING_REL}).",
    )
    args = parser.parse_args(argv)

    from runner.paths import find_repo_root
    from runner.working_assumptions import WorkingAssumptionsError

    try:
        repo_root = (
            Path(args.repo_root).resolve() if args.repo_root else find_repo_root()
        )
        out_path = Path(args.out) if args.out else None
        target, pack = build_canonical_pack_from_graph(
            Path(args.config), repo_root, run_id=args.run_id, out_path=out_path
        )
    except (GraphConfigError, VaultReadError, WorkingAssumptionsError) as exc:
        print(f"[graph-pack] FAIL-CLOSED: {exc}", file=sys.stderr, flush=True)
        return 2
    except Exception as exc:  # noqa: BLE001 — CLI boundary
        print(f"[graph-pack] ERROR: {exc}", file=sys.stderr, flush=True)
        return 3

    print(
        f"[graph-pack] run_id={pack['run_id']} "
        f"objectives={len(pack['objectives'])} outcomes={len(pack['outcomes'])} "
        f"wps={len(pack['wps'])} deliverables={len(pack['deliverables'])} "
        f"partners={len(pack['partners'])} "
        f"declared_assumptions={len(pack['declared_assumptions'])} -> {target}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
