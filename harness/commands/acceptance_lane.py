#!/usr/bin/env python3
"""
Run a named acceptance lane and reconcile it against its own declaration.

    py -3.10 -m harness.commands.acceptance_lane

The lane is read from ``harness/acceptance_lanes/``. With one declaration in the
tree it is chosen; with several, ``--lane NAME`` names one and an unqualified
run refuses rather than guessing.

The command exits 0 only when all four of these hold:

* no failure and no setup error;
* every skip the run reported is a declared exclusion;
* every declared exclusion the run was expected to report, it reported;
* every declared exclusion is also named in the exclusion document, and no
  exclusion sits in an area the run depends on;
* the extraction environment is one measured to reproduce the committed import
  artifacts.

The last is fail-closed rather than advisory. A build that cannot reproduce the
candidate derives a different document identity, so a green importer area under
it would certify a replay of something else. ``--allow-unreproducing-build``
runs anyway and stamps the result ``NOT CERTIFIED``, for an engineer measuring a
new build rather than accepting one.

Flags
-----
``--lane NAME``                  which declaration to run.
``--list``                       print the declaration and exit, running nothing.
``--junit PATH``                 where to write the JUnit report (default: a
                                 temporary file, read and then deleted).
``--from-junit PATH``            reconcile a report from an earlier run; runs no
                                 tests, so a recorded result can be re-read.
``--allow-unreproducing-build``  run off a reproducing build, uncertified.
``-k EXPR`` / ``--area NAME``    narrow the run. Both stamp ``PARTIAL``: a
                                 narrowed run is a diagnostic, never an
                                 acceptance result.

What a green lane does not say is printed with every result, and spelled out in
the declaration's own documentation.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from harness import acceptance_lane as lanes
from harness.commands._common import REPO_ROOT
from runner import extraction_environment as extraction


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="harness.commands.acceptance_lane",
        description="run and reconcile a named acceptance lane",
    )
    parser.add_argument("--lane", default=None, help="which declaration to run")
    parser.add_argument("--list", action="store_true", help="print the declaration and exit")
    parser.add_argument("--junit", type=Path, default=None, help="where to write the JUnit report")
    parser.add_argument(
        "--from-junit", type=Path, default=None, help="reconcile an earlier report, running nothing"
    )
    parser.add_argument(
        "--allow-unreproducing-build",
        action="store_true",
        help="run on a build not measured to reproduce the imports; the result is NOT CERTIFIED",
    )
    parser.add_argument("--area", action="append", default=[], help="run one area only (repeatable)")
    parser.add_argument("-k", dest="keyword", default=None, help="pytest -k expression")
    return parser


def _print_declaration(lane: lanes.Lane) -> None:
    print(f"lane: {lane.name}")
    print(f"declared in: {lane.source}")
    print(f"command: {lane.command}")
    print(f"modules: {len(lane.modules())} in {len(lane.areas)} areas")
    print()
    for area in lane.areas:
        print(f"[{area.name}] {lanes.one_line(area.invariant)}")
        for module in area.modules:
            print(f"    {module}")
    print()
    print(f"beyond the audit's focused command: {len(lane.modules_added)} modules")
    for module, why in lane.modules_added.items():
        print(f"    {module}  ({why})")
    print()
    print(f"considered and left out: {len(lane.modules_left_out)} modules")
    for module, why in lane.modules_left_out.items():
        print(f"    {module}  ({why})")
    print()
    print(
        f"declared exclusions: {len(lane.exclusions)} rows, "
        f"{lane.declared_check_count()} checks"
    )
    for exclusion in lane.exclusions:
        print(f"    EXCLUDED  {exclusion.check}")
        print(f"              {exclusion.substrate}: {exclusion.reason}")
        print(f"              replacement: {exclusion.replacement_evidence}")
        print(f"              lifted by: {exclusion.lifted_by}")
    print()
    for claim in lane.not_evidence_of:
        print(f"a green lane is {claim}.")


def _modules(lane: lanes.Lane, areas: list[str]) -> list[str]:
    if not areas:
        return list(lane.modules())
    known = {a.name for a in lane.areas}
    unknown = sorted(set(areas) - known)
    if unknown:
        raise SystemExit(
            f"no such area: {', '.join(unknown)}; declared: {', '.join(sorted(known))}"
        )
    return [m for a in lane.areas if a.name in areas for m in a.modules]


def _run_pytest(modules: list[str], junit: Path, keyword: str | None) -> None:
    command = [
        sys.executable,
        "-m",
        "pytest",
        *modules,
        "-q",
        "-o",
        "addopts=",
        "--tb=short",
        "-rs",
        f"--junitxml={junit}",
    ]
    if keyword:
        command += ["-k", keyword]
    print("$ " + " ".join(command), flush=True)
    subprocess.run(command, cwd=REPO_ROOT, check=False)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    try:
        lane = lanes.load_lane(lanes.resolve_lane_path(args.lane, REPO_ROOT), REPO_ROOT)
    except (FileNotFoundError, ValueError) as problem:
        print(f"REFUSED: {problem}", file=sys.stderr)
        return 2

    if args.list:
        _print_declaration(lane)
        return 0

    missing = lane.modules_missing_from_disk(REPO_ROOT)
    if missing:
        print(f"{lane.source} names modules that are not in the tree:", file=sys.stderr)
        for module in missing:
            print(f"    {module}", file=sys.stderr)
        return 2
    unassigned = lane.unassigned_focused_modules(REPO_ROOT)
    if unassigned:
        print("inside the audit's focused command and outside every area:", file=sys.stderr)
        for module in unassigned:
            print(f"    {module}", file=sys.stderr)
        return 2
    undocumented = lane.exclusions_missing_from_their_document(REPO_ROOT)
    if undocumented:
        print(f"declared here and absent from {lane.exclusion_document}:", file=sys.stderr)
        for check in undocumented:
            print(f"    {check}", file=sys.stderr)
        return 2
    depended_on = lane.exclusions_in_depended_on_areas()
    if depended_on:
        print("excluded, and the run depends on the area it sits in:", file=sys.stderr)
        for check, area in depended_on:
            print(f"    {check}  (area: {area})", file=sys.stderr)
        return 2

    print(extraction.describe_environment())
    cannot = extraction.cannot_reproduce_reason()
    if cannot is not None and not args.allow_unreproducing_build:
        print(f"\nREFUSED: {cannot}", file=sys.stderr)
        print(
            "Install the pinned build, or pass --allow-unreproducing-build to measure one "
            "and take an uncertified result.",
            file=sys.stderr,
        )
        return 2
    print()

    partial = bool(args.area or args.keyword)
    scratch: Path | None = None
    if args.from_junit is not None:
        report = args.from_junit
    elif args.junit is not None:
        report = args.junit
        report.parent.mkdir(parents=True, exist_ok=True)
    else:
        scratch = Path(tempfile.mkdtemp(prefix="acceptance-lane-"))
        report = scratch / "lane.xml"

    try:
        if args.from_junit is None:
            _run_pytest(_modules(lane, args.area), report, args.keyword)
        if not report.is_file():
            print(f"\nno JUnit report at {report}", file=sys.stderr)
            return 2
        outcome = lanes.parse_junit(report.read_text(encoding="utf-8"))
    finally:
        if scratch is not None:
            shutil.rmtree(scratch, ignore_errors=True)

    result = lanes.reconcile(outcome, lane.exclusions)

    print()
    for line in lanes.baseline_reconciliation(lane, outcome):
        print(line)
    print()

    # A narrowed run cannot tell a stale exclusion from one simply out of
    # scope, so that finding is dropped from the typed field rather than
    # filtered out of the rendered text.
    findings = (
        lanes.Reconciliation(
            unexplained_failures=result.unexplained_failures,
            undeclared_skips=result.undeclared_skips,
        )
        if partial
        else result
    )
    for line in findings.lines(lane.exclusion_document):
        print(line)

    if partial:
        print("PARTIAL: a narrowed run is a diagnostic, not an acceptance result.")
    elif findings.green:
        print(
            f"GREEN: {outcome.passed:,} passed, 0 failed, 0 errors, "
            f"{outcome.skipped} declared exclusions."
        )
    else:
        print("NOT GREEN: the findings above are unreconciled.")
    if cannot is not None:
        print(f"NOT CERTIFIED: {cannot}")
    print()
    for claim in lane.not_evidence_of:
        print(f"This result is {claim}.")
    print(f"Exclusions and the work that lifts each: {lane.exclusion_document}")

    if not findings.green:
        return 1
    return 0 if cannot is None else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
