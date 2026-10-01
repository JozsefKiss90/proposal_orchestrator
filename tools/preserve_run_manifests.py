"""Copy the run manifests that dispatched Phases 1 to 6 into the durable record.

The ticket 'Runner Phases 1 to 6 on the demo' asks that run manifests with their
reuse decisions be preserved for every run. They are written, but under
``.claude/runs/``, which §9.2 calls runtime execution state and which this
repository gitignores — so a clone has none of them and a cleared cache loses
them. §9.1 puts the durable record in ``docs/``. This tool moves a copy there.

It preserves what the criterion names and nothing else: the run id, the node
states, the per-node failure metadata and the reuse decisions, all out of the
manifest, plus the reuse policy and whatever the surviving run summary still says
about its own dispatch. A run summary is overwritten by each dispatch under the
same run id, so for a run dispatched one phase at a time only the last survives.
That is recorded as a fact about the run rather than quietly presented as the
whole of it.

A run id is used in file names, and nothing validates it: a mis-pasted argument
becomes a directory name. So the output file is named by a slug derived from the
run id, with the true run id recorded inside, and runs whose ids slugify the same
are refused rather than silently merged.

Run it from the repository root::

    py -3.10 -m tools.preserve_run_manifests            # write
    py -3.10 -m tools.preserve_run_manifests --check    # exit 1 if anything differs

Constitutional standing: an authoring tool, not a runtime component. It reads
runtime state and writes Tier 4 records, evaluates no gate and invokes no Claude.
It copies; it never edits a manifest.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from runner.atomic_write import atomic_write_json, canonical_json_bytes  # noqa: E402

SCHEMA_ID = "orch.run_record.preserved.v1"
RUNS_REL = ".claude/runs"
OUTPUT_DIR_REL = "docs/tier4_orchestration_state/run_records"

#: A run qualifies only when its manifest holds a state for every one of these.
#: The ticket's subject is the Phase 1 to 6 sequence, so a run that dispatched
#: two of them is a fragment of other work, not a record this ticket preserves —
#: and some such runs predate this demo world entirely.
QUALIFYING_NODES = (
    "n01_call_analysis",
    "n02_concept_refinement",
    "n03_wp_design",
    "n04_gantt_milestones",
    "n05_impact_architecture",
    "n06_implementation_architecture",
)


class PreservationError(RuntimeError):
    """Two runs cannot be told apart, or a manifest is unreadable."""


def slug(run_id: str) -> str:
    """A file-safe name for *run_id*, which nothing validates upstream."""
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", run_id).strip("-")
    return (cleaned or "unnamed-run")[:80]


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def collect(repo_root: Path) -> list[dict[str, Any]]:
    """One preserved record per qualifying run, ordered by the manifest clock."""
    records: list[dict[str, Any]] = []
    for manifest_path in sorted((repo_root / RUNS_REL).glob("*/run_manifest.json")):
        manifest = _read(manifest_path)
        states = manifest.get("node_states") or {}
        if not all(node in states for node in QUALIFYING_NODES):
            continue

        directory = manifest_path.parent
        summary_path = directory / "run_summary.json"
        policy_path = directory / "reuse_policy.json"
        summary = _read(summary_path) if summary_path.exists() else None

        dispatched = (summary or {}).get("dispatched_nodes") or []
        records.append(
            {
                "schema_id": SCHEMA_ID,
                "run_id": manifest["run_id"],
                "run_id_is_a_uuid": bool(
                    re.fullmatch(
                        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}"
                        r"-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
                        str(manifest["run_id"]),
                    )
                ),
                "copied_from": str(directory.relative_to(repo_root)).replace("\\", "/"),
                "manifest_version": manifest.get("manifest_version"),
                "library_version": manifest.get("library_version"),
                "constitution_version": manifest.get("constitution_version"),
                "created_at": manifest.get("created_at"),
                "node_states": states,
                "node_failure_details": manifest.get("node_failure_details") or {},
                "reuse_decisions": manifest.get("reuse_decisions") or {},
                "reuse_decisions_note": (
                    "Empty is the correct record for a Phases 1 to 6 run, not a "
                    "missing one: the reuse layer covers only the three Phase 8 "
                    "drafting nodes, so no node dispatched here can produce a "
                    "reuse decision."
                ),
                "reuse_policy": _read(policy_path) if policy_path.exists() else None,
                "surviving_run_summary": (
                    None
                    if summary is None
                    else {
                        "overall_status": summary.get("overall_status"),
                        "phase_scope": summary.get("phase_scope"),
                        "dispatched_nodes": dispatched,
                        "started_at": summary.get("started_at"),
                        "completed_at": summary.get("completed_at"),
                        "gate_results_index": summary.get("gate_results_index") or {},
                    }
                ),
                "run_summary_caveat": (
                    "A run summary is rewritten by each dispatch under the same run "
                    "id. This run dispatched "
                    + str(len(states))
                    + " phases, so the summary preserved here describes only its "
                    "last dispatch: " + ", ".join(dispatched or ["none recorded"])
                    + ". The node states and reuse decisions above come from the "
                    "manifest, which is cumulative and loses nothing."
                ),
            }
        )

    records.sort(key=lambda r: (str(r["created_at"]), str(r["run_id"])))

    seen: dict[str, str] = {}
    for record in records:
        name = slug(str(record["run_id"]))
        if name in seen and seen[name] != record["run_id"]:
            raise PreservationError(
                f"two run ids slugify to {name!r}: {seen[name]!r} and "
                f"{record['run_id']!r}. Preserving both would overwrite one."
            )
        seen[name] = record["run_id"]
    return records


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Preserve the run manifests that dispatched Phases 1 to 6 into "
            "docs/, where the durable record lives."
        )
    )
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--check",
        action="store_true",
        help="Write nothing; exit 1 if any preserved record would differ.",
    )
    args = parser.parse_args(argv)

    repo_root = args.repo_root.resolve()
    try:
        records = collect(repo_root)
    except PreservationError as exc:
        print(f"[BLOCKED] {exc}", file=sys.stderr)
        return 2

    if not records:
        print(
            f"[BLOCKED] no run under {RUNS_REL} holds a state for every one of "
            f"{list(QUALIFYING_NODES)}; there is nothing to preserve.",
            file=sys.stderr,
        )
        return 2

    differs = False
    for record in records:
        target = repo_root / OUTPUT_DIR_REL / f"{slug(str(record['run_id']))}.json"
        expected = canonical_json_bytes(record)
        if args.check:
            if not target.exists() or target.read_bytes() != expected:
                print(f"[DIFFERS] {target.name} would change.", file=sys.stderr)
                differs = True
            continue
        atomic_write_json(record, target)
        released = sum(1 for s in record["node_states"].values() if s == "released")
        print(f"Wrote {OUTPUT_DIR_REL}/{target.name}")
        print(f"  run_id {record['run_id']!r}")
        print(
            f"  {released}/{len(record['node_states'])} nodes released, "
            f"{len(record['reuse_decisions'])} reuse decision(s), "
            f"uuid={record['run_id_is_a_uuid']}"
        )

    if args.check:
        if differs:
            return 1
        print(f"[OK] {len(records)} preserved run record(s) unchanged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
