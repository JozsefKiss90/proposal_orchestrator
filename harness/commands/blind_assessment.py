#!/usr/bin/env python3
"""
Candidate-bound blind assessment — the harness module command.

Assesses one specified candidate (a directory of section artifacts) against a
pre-evaluation profile with the pinned, non-drafter assessor, without running
the production pipeline, and writes a bound report
(:mod:`harness.blind_assessment`).  A second sub-command re-binds a persisted
report to the candidate on disk and rejects it when the candidate changed.

Usage (assessor config auto-loads from ``.env.harness``; run FROM THE REPO ROOT):

    py -3.10 -m harness.commands.blind_assessment assess --candidate <dir>
    py -3.10 -m harness.commands.blind_assessment assess --document <id> [--graph-root <repo>] [--intake <id>]
    py -3.10 -m harness.commands.blind_assessment verify --report <file> --candidate <dir>

``--document`` names a document snapshot in the dev-graph (a node id or a
document id with one current version).  The evidence is then built by the
dev-graph package builder under the blind pre-evaluation view policy,
checked by the leakage guard, and materialised under ``<out-dir>/candidates/``
before the assessor is even constructed.  A leaked item is a hard failure
(exit 2, nothing written).  ``--intake`` names an ESR intake record; its
availability is stamped on the report and a purpose other than a blind
assessment is refused.

Exit codes: ``0`` complete assessment written (or report verified); ``1``
partial assessment written — the candidate lacks profile-required sections,
named in the report (advisory); ``2`` the assessment could not run or the
report was rejected (fail-closed; nothing written).

The command lives inside the harness package so the one-way ``harness ->
runner`` import boundary holds.  Advisory artifact; never a runtime gate
(``harness/HARNESS.md``).
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Callable, Sequence

from harness.blind_assessment import (
    DEFAULT_PACKAGE_BUDGET,
    DEFAULT_PROVENANCE_PATH,
    DEFAULT_REPORTS_DIR,
    SCOPE_PARTIAL,
    BlindAssessmentError,
    assess_candidate,
    build_blind_evidence,
    load_report,
    render_report,
    write_report,
)
from harness.evidence_pack import (
    DEFAULT_PACK_TOKEN_BUDGET,
    DEFAULT_SPAN_BUDGET_FRACTION,
    EvidencePackError,
)
from harness.expectation_coverage import CoverageError
from harness.expectations import ExpectationError
from harness.judge import Judge, JudgeError
from harness.profile import ProfileError
from harness.routing import DeterministicCoverageError
from harness.rubrics import RubricError, load_profile_bundle
from harness.verdict import MIN_MAJORITY_SAMPLES
from runner.dev_graph import DevGraphError, read_esr_intake

#: Every fail-closed error the command converts to exit code 2.
_CLI_ERRORS = (
    BlindAssessmentError,
    DevGraphError,
    RubricError,
    ProfileError,
    ExpectationError,
    EvidencePackError,
    CoverageError,
    DeterministicCoverageError,
    JudgeError,
    OSError,
)


def _env_int(name: str, default: int) -> int:
    v = os.environ.get(name)
    return int(v) if v else default


def _live_judge(args: argparse.Namespace, repo_root: Path) -> Judge:
    """The live assessor: ``.env.harness`` pin + the paced/retrying backend."""
    from harness.commands._common import load_harness_env
    from harness.commands.freeze_grounding_baselines import build_paced_judge
    from harness.judge import resolve_judge_config

    load_harness_env()
    cfg = resolve_judge_config()  # fail-closed if the assessor pin is unset
    judge, _wrapper = build_paced_judge(
        cfg,
        tpm=args.tpm,
        rpm=args.rpm,
        max_retries=args.max_retries,
        prov_path=repo_root / args.provenance,
    )
    return judge


def _parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="harness.commands.blind_assessment",
        description=(
            "Blind pre-evaluation of one candidate against a pre-evaluation "
            "profile. The report is bound to the candidate hash, profile version "
            "and assessor pin. Advisory; never a runtime gate."
        ),
    )
    sub = ap.add_subparsers(dest="command", required=True)

    p_assess = sub.add_parser("assess", help="assess one candidate and write a bound report")
    what = p_assess.add_mutually_exclusive_group(required=True)
    what.add_argument("--candidate", help="directory holding <section_id>.json artifacts")
    what.add_argument("--document",
                      help="dev-graph document snapshot (node id, or a document id with one current version)")
    p_assess.add_argument("--graph-root", default=None,
                          help="repository root holding the dev-graph records (default: --repo-root)")
    p_assess.add_argument("--intake", default=None, help="ESR intake record id to stamp on the report")
    p_assess.add_argument("--project", default=None,
                          help="project label for the package request (default: the document id)")
    p_assess.add_argument("--package-budget", type=int, default=DEFAULT_PACKAGE_BUDGET,
                          help="dev-graph package size budget for the document route")
    p_assess.add_argument("--repo-root", default=os.environ.get("HARNESS_REPO_ROOT", "."))
    p_assess.add_argument("--profile", default=None,
                          help="pre-evaluation profile JSON (default: the harness default profile)")
    p_assess.add_argument("--out-dir", default=str(DEFAULT_REPORTS_DIR),
                          help="directory for the new report file (never overwritten)")
    p_assess.add_argument("--provenance", default=str(DEFAULT_PROVENANCE_PATH))
    p_assess.add_argument("--budget", type=int, default=DEFAULT_PACK_TOKEN_BUDGET,
                          help="evidence-pack token budget per expectation")
    p_assess.add_argument("--span-fraction", type=float, default=DEFAULT_SPAN_BUDGET_FRACTION)
    p_assess.add_argument("--n", type=int, default=MIN_MAJORITY_SAMPLES,
                          help="assessor samples per verdict (majority; N>=3)")
    p_assess.add_argument("--tpm", type=int, default=_env_int("HARNESS_TPM_BUDGET", 5500))
    p_assess.add_argument("--rpm", type=int, default=_env_int("HARNESS_RPM_BUDGET", 28))
    p_assess.add_argument("--max-retries", type=int, default=_env_int("HARNESS_MAX_RETRIES", 6))

    p_verify = sub.add_parser("verify", help="re-bind a persisted report to a candidate")
    p_verify.add_argument("--report", required=True)
    p_verify.add_argument("--candidate", required=True)
    p_verify.add_argument("--repo-root", default=os.environ.get("HARNESS_REPO_ROOT", "."))
    p_verify.add_argument("--profile", default=None)
    return ap


def main(
    argv: Sequence[str] | None = None,
    *,
    judge: Judge | None = None,
    clock: Callable[[], str] | None = None,
) -> int:
    """Run the command.  *judge* and *clock* are injectable for offline tests;
    the live path builds the paced assessor from ``.env.harness``."""
    args = _parser().parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    try:
        bundle = load_profile_bundle(args.profile, repo_root=repo_root)
        if args.command == "verify":
            data = load_report(
                args.report, args.candidate, bundle.profile, profile_version=bundle.version
            )
            print(render_report(data))
            print(f"\nverified: report is bound to the candidate at {args.candidate}")
            return 0

        out_dir = Path(args.out_dir)
        if not out_dir.is_absolute():
            out_dir = repo_root / out_dir
        graph_root = Path(args.graph_root).resolve() if args.graph_root else repo_root
        intake = read_esr_intake(graph_root, args.intake) if args.intake else None
        evidence = None
        if args.document:
            # Snapshot, blind-view package, leakage guard, materialisation —
            # all before the assessor exists.  A leak stops here.
            evidence = build_blind_evidence(
                graph_root,
                args.document,
                profile_version=bundle.version,
                out_dir=out_dir,
                budget=args.package_budget,
                project=args.project,
            )
        assessor = judge if judge is not None else _live_judge(args, repo_root)
        report = assess_candidate(
            assessor,
            bundle,
            args.candidate,
            evidence=evidence,
            intake=intake,
            token_budget=args.budget,
            span_budget_fraction=args.span_fraction,
            n=args.n,
            clock=clock,
        )
        path = write_report(report, out_dir)
        data = report.to_dict()
        print(render_report(data))
        print(f"\nreport -> {path}")
        return 1 if report.scope == SCOPE_PARTIAL else 0
    except _CLI_ERRORS as exc:
        print(f"blind assessment could not run (fail-closed): {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
