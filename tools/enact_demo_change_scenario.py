"""Enact one of the demo's change scenarios on the world itself.

Subticket B of the ticket 'Change scenarios and shadow comparison' asks that
one scenario leave the sandbox: the change is recorded against ``docs/`` so
the Tier 3 record gains a new version and the prior version stays intact, the
snapshot id moves, and the new id is pinned in the scenario record. This tool
is that step. It takes a scenario from the catalogue in
``tools/run_demo_change_scenarios.py`` and hands it to
:func:`runner.dev_graph.scenarios.enact_scenario`, which rehearses every arm in
a sandbox, refuses unless each is a change the revision contract accepts, and
only then records the arms through the change recorder: prior version
archived, both snapshots stored, change record written, advisory plan written
at its canonical path, enactment record written once beside the scenario.

The enactment leaves three things for other tools, and this one prints them:

* ``py -3.10 -m tools.build_demo_dev_graph`` rewrites the snapshot artifacts
  and the packages over the moved snapshot;
* ``py -3.10 -m tools.run_demo_change_scenarios`` rewrites the scenario
  records, replaying the enacted scenario from its archived versions;
* the Tier 3 freeze record names the changed artifacts by fingerprint and is
  superseded by a new decision log entry, which is an operator decision.

The rerun is the operator's act and costs quota. Once a run is dispatched
under a plain run id, ``--record-rerun --run-id <id>`` compares each enacted
arm's advisory with the reuse decisions that run recorded and writes the
result under ``reruns/<run id>.json`` beside the enactment, listing every
``planner_narrower`` row for investigation. One record per run id: a run that
could only be refused stays recorded and the next run is recorded beside it.
Note that until the scheduler persists a ``not_reused``
decision (subticket D), a rerun over changed Tier 3 records no decision at
all: every Phase 8 fingerprint covers the whole of Tier 3, so every drafting
node redrafts, and the comparison refuses with ``no_reuse_decision``.

Run it from the repository root::

    py -3.10 -m tools.enact_demo_change_scenario --scenario deliverable_month_moves
    py -3.10 -m tools.enact_demo_change_scenario --scenario deliverable_month_moves \\
        --record-rerun --run-id <plain run id> [--investigation "<reason>"]

Constitutional standing: an authoring tool, not a runtime component. It writes
one Tier 3 record per arm through the change recorder and Tier 4 dev-graph
artifacts; it evaluates no gate (§17.6.2), invokes no Claude and dispatches no
phase. The Tier 3 write is an operator act under the manual's freeze rule and
is made only on operator instruction.
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from runner.dev_graph.scenarios import (  # noqa: E402
    Scenario,
    enact_scenario,
    read_enactment,
    record_rerun,
)
from runner.dev_graph.schema import DevGraphError  # noqa: E402
from runner.run_context import RUN_ID_RULE, is_plain_run_id  # noqa: E402
from tools.run_demo_change_scenarios import SCENARIOS  # noqa: E402

FOLLOW_UPS = (
    "py -3.10 -m tools.build_demo_dev_graph",
    "py -3.10 -m tools.run_demo_change_scenarios",
    "supersede the live Tier 3 freeze record with a new decision log entry",
)


def catalogue_scenario(scenario_id: str) -> Scenario:
    """The catalogue entry *scenario_id*, or refuse (``malformed_request``)."""
    found = next((s for s in SCENARIOS if s.scenario_id == scenario_id), None)
    if found is None:
        raise DevGraphError(
            "malformed_request",
            scenario_id,
            f"no scenario {scenario_id!r} in the catalogue; "
            f"one of {sorted(s.scenario_id for s in SCENARIOS)}",
        )
    return found


def enact(repo_root: Path, scenario_id: str) -> int:
    scenario = catalogue_scenario(scenario_id)
    sandbox = Path(tempfile.mkdtemp(prefix="enact-"))
    try:
        enactment = enact_scenario(repo_root, scenario, sandbox_dir=sandbox)
    finally:
        shutil.rmtree(sandbox, ignore_errors=True)
    print(f"ENACTED {scenario_id}: {enactment.path}")
    print(f"  before {enactment.before_snapshot_id}")
    print(f"  after  {enactment.after_snapshot_id}")
    for arm in enactment.arms:
        asks = ", ".join(f"{n}={v}" for n, v in arm["scheduler_verdicts"].items())
        print(f"  {arm['arm_id']}: {arm['change_record']} | plan {arm['plan']} | advisory asks {asks}")
    print("follow-ups:")
    for step in FOLLOW_UPS:
        print(f"  {step}")
    return 0


def rerun(repo_root: Path, scenario_id: str, run_id: str, investigation: str | None) -> int:
    if not is_plain_run_id(run_id):
        print(f"--run-id {run_id!r} is not a plain identifier: {RUN_ID_RULE}", file=sys.stderr)
        return 2
    if read_enactment(repo_root, scenario_id) is None:
        print(f"{scenario_id} is not enacted; enact it first", file=sys.stderr)
        return 2
    rel = record_rerun(repo_root, scenario_id, run_id, investigation=investigation)
    print(f"RECORDED rerun of {scenario_id} against {run_id}: {rel}")
    print("follow-up: py -3.10 -m tools.run_demo_change_scenarios")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--scenario", required=True, help="a scenario id from the catalogue")
    parser.add_argument("--repo-root", default=None, help="defaults to this file's repository")
    parser.add_argument(
        "--record-rerun",
        action="store_true",
        help="compare the enacted arms with the reuse decisions of --run-id instead of enacting",
    )
    parser.add_argument("--run-id", default=None, help=f"the dispatched run; {RUN_ID_RULE}")
    parser.add_argument(
        "--investigation",
        default=None,
        help="with --record-rerun: the recorded reason for any planner_narrower row",
    )
    args = parser.parse_args(argv)
    root = Path(args.repo_root) if args.repo_root else Path(__file__).resolve().parents[1]

    try:
        if args.record_rerun:
            if args.run_id is None:
                parser.error("--record-rerun needs --run-id")
            return rerun(root, args.scenario, args.run_id, args.investigation)
        if args.run_id is not None or args.investigation is not None:
            parser.error("--run-id and --investigation go with --record-rerun")
        return enact(root, args.scenario)
    except DevGraphError as exc:
        print(f"REFUSED {exc.kind}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
