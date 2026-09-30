"""Build the first dev-graph snapshot on the instance-two demo world.

Writes the snapshot over the populated Tier 3 records, then one bounded
evidence package per view policy for each of :data:`SEED_TASKS`, under
:data:`runner.dev_graph.DEFAULT_PACKAGE_BUDGET`. Everything it writes is
derived: nothing here types a node, an edge, a count or a package id by hand.

The run summary also records, per package, the smallest budget at which the
mandatory set fits and the smallest at which the package is complete. Both are
bisected against the builder, so "this package is incomplete" comes with the
measurement of how far short the budget fell rather than an estimate of it.

The three seed tasks are chosen by a stated structural rule, not by taste, so
a reader can check the choice against the records:

* ``T3.1`` — the task the most other tasks consume, the densest seed in the
  work plan;
* ``T4.1`` — the demonstration task that both consumes upstream work and is
  consumed downstream, so its mandatory walk crosses work-package boundaries
  in both directions;
* ``T1.1`` — a coordination task, the sparse end of the same range.

:func:`main` is idempotent: a second run over unchanged records rewrites the
same bytes at the same paths, because the snapshot id and every package id are
content-derived and no artifact carries a clock. ``--check`` writes nothing and
exits 1 if any artifact would change.

Run it from the repository root::

    py -3.10 -m tools.build_demo_dev_graph            # write
    py -3.10 -m tools.build_demo_dev_graph --check    # exit 1 if anything differs

Constitutional standing: an authoring tool, not a runtime component. It reads
Tier 3, writes Tier 4 dev-graph artifacts, evaluates no gate and invokes no
Claude. A :class:`DevGraphError` propagates: a fail-closed build is a finding
to fix at its source record, never a reason to loosen the builder.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Callable, Optional, Sequence

from runner.atomic_write import atomic_write_json, canonical_json_bytes
from runner.dev_graph import (
    DEFAULT_PACKAGE_BUDGET,
    POLICY_VERSION,
    SNAPSHOT_REL,
    VIEW_POLICIES,
    Package,
    Snapshot,
    build_package,
    build_snapshot,
    package_dir,
)
from runner.paths import find_repo_root

#: The demo project id carried in every package request.
PROJECT = "DEMO-BIODIV-2027"

#: The instrument profile the packages are requested under. Instance two is an
#: RIA; the packages are not bound to a profile artifact, so the value names
#: the instrument and nothing more.
PROFILE_VERSION = "ria-2026-2027"

#: The three seed tasks, in the order the module docstring states.
SEED_TASKS: tuple[str, ...] = ("T3.1", "T4.1", "T1.1")

#: Where the run summary lands: the counts later scenarios compare against.
SUMMARY_REL = "docs/tier4_orchestration_state/dev_graph/demo_snapshot_summary.json"

#: Schema id of that summary.
SUMMARY_SCHEMA_ID = "orch.dev_graph.demo_snapshot_summary.v1"

#: Upper bound of the budget bisection. Well above the whole snapshot, so a
#: package that does not fit below it does not fit at all.
MAX_PROBED_BUDGET = 1_000_000


def _requests() -> list[tuple[str, str]]:
    """Every ``(task, view)`` pair, in a stated order."""
    return [(task, view) for task in SEED_TASKS for view in sorted(VIEW_POLICIES)]


def _package(snapshot: Snapshot, task: str, view: str, budget: int = DEFAULT_PACKAGE_BUDGET) -> Package:
    return build_package(
        snapshot,
        task=task,
        view=view,
        budget=budget,
        policy_version=POLICY_VERSION,
        expected_snapshot_id=snapshot.snapshot_id,
        project=PROJECT,
        profile_version=PROFILE_VERSION,
    )


def count_by(items: Any, key: str) -> dict[str, int]:
    """How many of *items* carry each value of *key*, in key order."""
    counts: dict[str, int] = {}
    for item in items:
        counts[item[key]] = counts.get(item[key], 0) + 1
    return dict(sorted(counts.items()))


def _minimum_budget(
    snapshot: Snapshot, task: str, view: str, fits: Callable[[Package], bool]
) -> int:
    """The smallest budget at which *fits* holds for this package.

    Bisection over the budget, which is sound because the selection order is
    fixed and an item that fits at one budget fits at every larger one. The
    number answers the question the incompleteness raises — how far short is
    the default — with a measurement rather than an estimate.
    """
    lo, hi = 1, MAX_PROBED_BUDGET
    while lo < hi:
        mid = (lo + hi) // 2
        if fits(_package(snapshot, task, view, budget=mid)):
            hi = mid
        else:
            lo = mid + 1
    return lo


def _mandatory_fits(pkg: Package) -> bool:
    return not any(u["kind"] == "required_over_budget" for u in pkg.manifest["unresolved"])


def _complete(pkg: Package) -> bool:
    return pkg.manifest["completeness"] == "complete"


def _package_row(repo_root: Path, task: str, view: str, pkg: Package) -> dict[str, Any]:
    """One row of the summary: what the manifest reports, derived from it."""
    manifest = pkg.manifest
    over_budget = [e for e in manifest["exclusions"] if e["reason"] == "over_budget"]
    policy_forbidden = [e for e in manifest["exclusions"] if e["reason"] == "policy_forbidden"]
    not_confirmed = [
        {"id": u["id"], "type": u["type"], "declared_status": u["declared_status"]}
        for u in manifest["unresolved"]
        if u["kind"] == "declared_status"
    ]
    return {
        "task": task,
        "view": view,
        "package_id": manifest["package_id"],
        "package_hash": manifest["package_hash"],
        "path": package_dir(repo_root, manifest["package_id"]).relative_to(repo_root).as_posix(),
        "completeness": manifest["completeness"],
        "worst_declared_status": manifest["worst_declared_status"],
        "included_count": len(manifest["included"]),
        "mandatory_count": len(manifest["mandatory_dependencies"]),
        "exclusion_count": len(manifest["exclusions"]),
        # The manifest is the authority on why each item was dropped; the
        # summary carries the ids so a later scenario can diff them without
        # opening eighteen manifests.
        "over_budget_count": len(over_budget),
        "over_budget_required_count": sum(1 for e in over_budget if e["required"]),
        "over_budget_ids": [e["id"] for e in over_budget],
        "first_item_that_did_not_fit": over_budget[0]["id"] if over_budget else None,
        # What the view kept out, as distinct from what the budget kept out.
        # Derived here because a count typed into prose drifts from the
        # artifacts; this one is read back by the ticket's tests.
        "exclusions_by_reason": count_by(manifest["exclusions"], "reason"),
        "policy_forbidden_count": len(policy_forbidden),
        "policy_forbidden": [
            {"id": e["id"], "type": e["type"], "detail": e["detail"]} for e in policy_forbidden
        ],
        "not_confirmed": not_confirmed,
    }


def _totals(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    """Sum the per-package ``{reason: count}`` maps under *key*, in key order."""
    totals: dict[str, int] = {}
    for row in rows:
        for reason, count in row[key].items():
            totals[reason] = totals.get(reason, 0) + count
    return dict(sorted(totals.items()))


def build(repo_root: Path) -> dict[Path, Any]:
    """Every artifact this tool writes, as ``{absolute path: JSON document}``."""
    snapshot = build_snapshot(repo_root)
    artifacts: dict[Path, Any] = {repo_root / SNAPSHOT_REL: snapshot.to_dict()}

    rows: list[dict[str, Any]] = []
    for task, view in _requests():
        pkg = _package(snapshot, task, view)
        base = package_dir(repo_root, pkg.manifest["package_id"])
        artifacts[base / "manifest.json"] = pkg.manifest
        artifacts[base / "package.json"] = pkg.to_dict()
        row = _package_row(repo_root, task, view, pkg)
        row["minimum_budget_for_mandatory"] = _minimum_budget(
            snapshot, task, view, _mandatory_fits
        )
        row["minimum_budget_for_completeness"] = _minimum_budget(snapshot, task, view, _complete)
        rows.append(row)

    artifacts[repo_root / SUMMARY_REL] = {
        "schema_id": SUMMARY_SCHEMA_ID,
        "project": PROJECT,
        "profile_version": PROFILE_VERSION,
        "snapshot_id": snapshot.snapshot_id,
        "policy_version": POLICY_VERSION,
        "budget": DEFAULT_PACKAGE_BUDGET,
        "inputs": list(snapshot.inputs),
        "node_count": len(snapshot.nodes),
        "edge_count": len(snapshot.edges),
        "nodes_by_type": count_by(snapshot.nodes, "type"),
        "edges_by_predicate": count_by(snapshot.edges, "predicate"),
        "seed_tasks": list(SEED_TASKS),
        "views": sorted(VIEW_POLICIES),
        "exclusions_by_reason_total": _totals(rows, "exclusions_by_reason"),
        "packages_with_a_policy_exclusion": sorted(
            (r["task"], r["view"]) for r in rows if r["policy_forbidden_count"]
        ),
        "packages": rows,
    }
    return artifacts




def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="write nothing; exit 1 if anything differs")
    args = ap.parse_args(argv)

    repo_root = find_repo_root()
    artifacts = build(repo_root)

    if args.check:
        differing = [
            path
            for path, doc in sorted(artifacts.items())
            if not path.is_file() or path.read_bytes() != canonical_json_bytes(doc)
        ]
        for path in differing:
            print(f"differs: {path.relative_to(repo_root).as_posix()}", file=sys.stderr)
        print(f"{len(artifacts) - len(differing)}/{len(artifacts)} artifacts up to date")
        return 1 if differing else 0

    for path, doc in sorted(artifacts.items()):
        atomic_write_json(doc, path)
    summary = artifacts[repo_root / SUMMARY_REL]
    print(f"snapshot {summary['snapshot_id']}")
    print(f"{summary['node_count']} nodes, {summary['edge_count']} edges")
    print(f"{len(summary['packages'])} packages written under budget {summary['budget']}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
