"""Derive the dev-graph run records the shadow impact planner reads.

``runner/dev_graph/impact.py`` refuses without
``docs/tier4_orchestration_state/dev_graph/run_records.json``: without a record
of what an artifact was produced from, the planner cannot say what a change
affects, and it will not narrow a plan to cover for a missing index. The
artifact schema specification places that file by hand. Hand-typing it would
type a node list the artifacts already carry, which the ticket 'First dev-graph
snapshot on the demo world' recorded as its D9 lesson: derive a document's
counts, never type them.

Two rules, both narrow and both declared in the artifact:

**An artifact declares the node ids its own text names.** One record per Tier 5
proposal section, with ``inputs`` set to the snapshot node ids that appear in the
section, matched on a word boundary so ``D3.2`` is not found inside ``D3.21``. A
section that names no node declares ``null`` — unknown coverage — rather than an
empty list: an empty list would assert that the section rests on no project fact,
which the scan cannot show.

**A check declares unknown coverage.** One record per gate result, with
``inputs: null``, because no gate result in this repository names a graph node.
The planner reads that as ``rerun``, which is the conservative reading and the
only honest one. The premise is checked by test, not assumed.

No record declares a ``package``. The evidence packages this world holds are
per-task integrity views, not the view a section was drafted from, so citing one
would misdescribe the artifact's provenance.

Run it from the repository root::

    py -3.10 -m tools.derive_dev_graph_run_records            # write
    py -3.10 -m tools.derive_dev_graph_run_records --check    # exit 1 if anything differs

Constitutional standing: an authoring tool, not a runtime component. It reads
the snapshot, Tier 5 sections and Tier 4 gate results, writes one Tier 4
artifact, evaluates no gate and invokes no Claude. It derives; it invents no
dependency (§13.3).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any, Iterable

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from runner.atomic_write import atomic_write_json, canonical_json_bytes  # noqa: E402
from runner.dev_graph.builder import build_snapshot  # noqa: E402
from runner.dev_graph.impact import (  # noqa: E402
    RUN_RECORDS_REL,
    RUN_RECORDS_SCHEMA_ID,
    normalise_run_records,
)

#: Where the Tier 5 proposal sections live. One artifact record each.
SECTION_DIR_REL = "docs/tier5_deliverables/proposal_sections"

#: Where the gate results live. One check record each.
GATE_RESULT_GLOBS: tuple[str, ...] = (
    "docs/tier4_orchestration_state/phase_outputs/*/gate_result.json",
    "docs/tier4_orchestration_state/phase_outputs/*/gate_*_result.json",
)

DERIVATION_RULE = (
    "An artifact's inputs are the snapshot node ids its own text names, matched "
    "on a word boundary so a shorter id is never found inside a longer one. "
    "Nothing is inferred from the artifact's subject or its section."
)
UNKNOWN_COVERAGE_RULE = (
    "A record whose inputs could not be derived declares null, which the planner "
    "reads as unknown coverage and reports as rerun. An empty list would assert "
    "that the record rests on no project fact; the scan cannot show that."
)
PACKAGE_RULE = (
    "No record declares a package. The evidence packages this world holds are "
    "per-task integrity views, not the view a section was drafted from."
)

_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


def named_node_ids(text: str, node_ids: Iterable[str]) -> list[str]:
    """The node ids *text* names, sorted and deduplicated.

    An id matches only on a word boundary of its own: the character before
    and after must not continue an identifier, so ``D3.2`` is not found
    inside ``D3.21`` and ``P01`` is not found inside ``P011``.
    """
    found = [
        node_id
        for node_id in set(node_ids)
        if re.search(
            r"(?<![A-Za-z0-9_.#-])" + re.escape(node_id) + r"(?![A-Za-z0-9_.-])", text
        )
    ]
    return sorted(found)


def record_id_for(path: Path) -> str:
    """``<parent directory>.<file stem>``.

    Seven phase directories each hold a file named ``gate_result.json``, so a
    stem alone is not an identity. The parent directory is what distinguishes
    them, and naming it keeps the id readable and derived from the path.
    """
    return f"{path.parent.name}.{path.stem}"


def _record(path: Path, repo_root: Path, kind: str, node_ids: set[str]) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8-sig")
    named = named_node_ids(text, node_ids) if kind == "artifact" else []
    return {
        "record_id": record_id_for(path),
        "kind": kind,
        "path": path.relative_to(repo_root).as_posix(),
        "inputs": named or None,
        "dependency_edges": [],
    }


def derive_run_records(repo_root: Path | str) -> list[dict[str, Any]]:
    """The run records for the world at *repo_root*, sorted by record id.

    Deterministic: the same files yield the same records. A world with no
    section and no gate result yields none, which the planner refuses — a
    refusal is the correct output for a world it cannot plan over.
    """
    root = Path(repo_root)
    node_ids = {n["id"] for n in build_snapshot(root).nodes}
    records: list[dict[str, Any]] = [
        _record(p, root, "artifact", node_ids)
        for p in sorted((root / SECTION_DIR_REL).glob("*.json"))
    ]
    gates = sorted({p for pattern in GATE_RESULT_GLOBS for p in root.glob(pattern)})
    records += [_record(p, root, "check", node_ids) for p in gates]
    bad = next((r for r in records if not _ID_RE.match(r["record_id"])), None)
    if bad is not None:
        raise ValueError(
            f"record id {bad['record_id']!r} from {bad['path']} is not a plain identifier"
        )
    return normalise_run_records(records, "derived") if records else []


def build_document(repo_root: Path | str) -> dict[str, Any]:
    """The artifact: the records, and the rules that produced them."""
    return {
        "schema_id": RUN_RECORDS_SCHEMA_ID,
        "derivation_rule": DERIVATION_RULE,
        "unknown_coverage_rule": UNKNOWN_COVERAGE_RULE,
        "package_rule": PACKAGE_RULE,
        "derived_by": "tools/derive_dev_graph_run_records.py",
        "records": derive_run_records(repo_root),
    }


def output_path(repo_root: Path | str) -> Path:
    return Path(repo_root) / RUN_RECORDS_REL


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="compare with the written artifact and exit 1 on any difference",
    )
    parser.add_argument("--repo-root", default=None, help="defaults to this file's repository")
    args = parser.parse_args(argv)

    root = Path(args.repo_root) if args.repo_root else Path(__file__).resolve().parents[1]
    document = build_document(root)
    target = output_path(root)
    expected = canonical_json_bytes(document)

    if args.check:
        if not target.is_file():
            print(f"MISSING {RUN_RECORDS_REL}")
            return 1
        if target.read_bytes() != expected:
            print(f"DIFFERS {RUN_RECORDS_REL}")
            return 1
        print(f"OK {RUN_RECORDS_REL} ({len(document['records'])} records)")
        return 0

    atomic_write_json(document, target)
    artifacts = sum(1 for r in document["records"] if r["kind"] == "artifact")
    checks = sum(1 for r in document["records"] if r["kind"] == "check")
    print(f"WROTE {RUN_RECORDS_REL}: {artifacts} artifact records, {checks} check records")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
