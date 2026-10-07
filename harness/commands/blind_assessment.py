#!/usr/bin/env python3
"""
Candidate-bound blind assessment — the harness module command.

Assesses one specified candidate (a directory of section artifacts) against a
pre-evaluation profile with the pinned, non-drafter assessor, without running
the production pipeline, and writes a bound report
(:mod:`harness.blind_assessment`).  A second sub-command re-binds a persisted
report to the candidate on disk and rejects it when the candidate changed.  A
third, ``preflight``, realises the evidence the assessor would read and binds
it by hash before any quota is spent (:mod:`harness.evidence_preflight`).  A
fourth, ``freeze``, checks a written report against the baseline conditions and
copies it, with a freeze record, into a durable baseline directory
(:mod:`harness.blind_baseline`).  A fifth, ``audit``, runs the Claude-free
integrity audit over the parsed table rows and the claim ledger and binds the
result to the frozen baseline when one is given (:mod:`harness.integrity_audit`).
A sixth, ``compare``, resolves the operator's ESR record and dispositions
against the frozen baseline and writes the comparison and the revision
priorities (:mod:`harness.esr_comparison`).

Usage (assessor config auto-loads from ``.env.harness``; run FROM THE REPO ROOT):

    py -3.10 -m harness.commands.blind_assessment preflight --document <id> [--graph-root <repo>] [...]
    py -3.10 -m harness.commands.blind_assessment assess --document <id> --preflight <file> [...]
    py -3.10 -m harness.commands.blind_assessment assess --candidate <dir> --preflight <file>
    py -3.10 -m harness.commands.blind_assessment verify --report <file> --candidate <dir>
    py -3.10 -m harness.commands.blind_assessment freeze --report <file> --candidate <dir> --baseline-dir <dir>
    py -3.10 -m harness.commands.blind_assessment audit --document <id> [--graph-root <repo>] [--baseline-dir <dir>]
    py -3.10 -m harness.commands.blind_assessment compare --baseline-dir <dir> --esr <file> --dispositions <file> --candidate <dir> --register <file> --out-dir <dir>

``preflight`` and ``assess`` share every evidence-selecting flag (``--budget``,
``--span-fraction``, ``--no-claims``, ``--criterion-budget``, ``--transport``,
``--package-budget``, ...).  Run the preflight with the flags you will assess
with: ``assess`` **requires** ``--preflight`` and re-derives the realised pack
set under its own flags; when the candidate, the profile, any parameter or any
pack moved, it refuses (exit 2) naming every field that did, before the
assessor is constructed.  The blind report then carries the preflight's
pack-set hash.

``--document`` names a document snapshot in the dev-graph (a node id or a
document id with one current version).  The evidence is then built by the
dev-graph package builder under the blind pre-evaluation view policy,
checked by the leakage guard, and materialised under ``<out-dir>/candidates/``
before the assessor is even constructed.  A leaked item is a hard failure
(exit 2, nothing written).  ``--intake`` names an ESR intake record; its
availability is stamped on the report and a purpose other than a blind
assessment is refused.

Exit codes.  ``assess``: ``0`` complete assessment written (or report
verified); ``1`` partial assessment written — the candidate lacks
profile-required sections, named in the report (advisory); ``2`` the
assessment could not run or the report or preflight was rejected
(fail-closed; nothing written).  ``preflight``: ``0`` written with no flag;
``1`` written with flags the operator should read (a missing anchor, a
truncated pack, an incomplete package, a leak); ``2`` could not run.
``freeze``: ``0`` frozen; ``2`` refused, naming every failed condition,
nothing written.  ``audit``: ``0`` written with no flag; ``1`` written with
flags the operator should read (a vacuous ledger, a ledger entry contradicting
the import contract, a re-derived baseline, a parse failure); ``2`` could not
run.  Findings never move the exit code: they are the product, not a verdict.

The command lives inside the harness package so the one-way ``harness ->
runner`` import boundary holds.  Advisory artifact; never a runtime gate
(``harness/HARNESS.md``).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Callable, Mapping, Sequence

from harness.blind_assessment import (
    DEFAULT_PACKAGE_BUDGET,
    DEFAULT_PROVENANCE_PATH,
    DEFAULT_REPORTS_DIR,
    SCOPE_PARTIAL,
    BlindAssessmentError,
    BlindEvidence,
    assess_candidate,
    assessor_pin,
    build_blind_evidence,
    candidate_hash,
    load_candidate,
    load_report,
    render_report,
    write_report,
)
from harness.blind_baseline import freeze_baseline, load_frozen_baseline, render_freeze
from harness.integrity_audit import render_audit, run_audit, write_audit
from harness.esr_comparison import (
    EsrComparisonError,
    load_audits,
    load_dispositions,
    load_esr_record,
    load_register,
    render_comparison,
    run_comparison,
    write_comparison,
)
from harness.evidence_pack import (
    DEFAULT_PACK_TOKEN_BUDGET,
    DEFAULT_SPAN_BUDGET_FRACTION,
    MAX_PACK_TOKEN_BUDGET,
    UNCAPPED_DEFAULT_PACK_TOKEN_BUDGET,
    EvidencePackError,
)
from harness.evidence_preflight import (
    PackParams,
    check_preflight,
    file_sha256,
    load_preflight,
    realise_pack_set,
    render_preflight,
    resolve_import_manifest,
    run_preflight,
    write_preflight,
)
from harness.criterion_scoring import DEFAULT_CRITERION_SAMPLES, CriterionScoringError
from harness.expectation_coverage import CoverageError
from harness.expectations import ExpectationError
from harness.judge import Judge, JudgeError
from harness.profile import ProfileError
from harness.routing import DeterministicCoverageError
from harness.rubrics import ProfileBundle, RubricError, load_profile_bundle
from harness.provenance import prompt_hash
from harness.response_cache import (
    CacheBinding,
    ResponseCache,
    ResponseCacheError,
    next_checkpoint_path,
)
from harness.verdict import MIN_MAJORITY_SAMPLES
from runner.dev_graph import DevGraphError, read_esr_intake
from runner.leakage_scan import LeakageError as LeakageScanError

#: How the transport delimits a system prompt too long for the CLI flag
#: (``runner.claude_transport``); a salvaged transcript may carry it.
_EMBEDDED_SYSTEM_MARKER: str = "=== SYSTEM INSTRUCTIONS (embedded due to length) ==="
_EMBEDDED_SYSTEM_END: str = "=== END SYSTEM INSTRUCTIONS ===\n\n"

#: Where a run checkpoints its raw assessor responses when none is named.
#: Runtime state under the repository root, deliberately not --out-dir: a
#: failed run must still leave the report directory empty.
DEFAULT_CHECKPOINT_DIR: str = ".harness/checkpoints"

#: Every fail-closed error the command converts to exit code 2.
_CLI_ERRORS = (
    BlindAssessmentError,
    EsrComparisonError,
    DevGraphError,
    RubricError,
    ProfileError,
    ExpectationError,
    EvidencePackError,
    CoverageError,
    CriterionScoringError,
    DeterministicCoverageError,
    JudgeError,
    LeakageScanError,
    ResponseCacheError,
    OSError,
)


def _env_int(name: str, default: int) -> int:
    v = os.environ.get(name)
    return int(v) if v else default


def _judge_config(args: argparse.Namespace):
    """Resolve the pinned assessor config from the environment and the flags.

    Split out of :func:`_live_judge` because the salvage command needs the pin
    (it goes into the checkpoint binding) and must not build a transport to
    learn it.
    """
    import dataclasses

    from harness.commands._common import load_harness_env
    from harness.judge import JudgeConfig, resolve_judge_config

    load_harness_env()
    if args.assessor_model and args.assessor_version:
        # Both flags given: the pin need not exist in the environment at all.
        return JudgeConfig(model=args.assessor_model, version=args.assessor_version)
    cfg = resolve_judge_config()  # fail-closed if the assessor pin is unset
    if args.assessor_model or args.assessor_version:
        cfg = dataclasses.replace(
            cfg,
            model=args.assessor_model or cfg.model,
            version=args.assessor_version or cfg.version,
        )
    return cfg


def _live_judge(args: argparse.Namespace, repo_root: Path) -> Judge:
    """The live assessor: the ``.env.harness`` pin over the chosen transport.

    Two transports, one pin.  ``openai-compatible`` is the default and the
    independent path: a non-drafter model at a non-Claude endpoint.
    ``claude-cli`` speaks the Max subscription instead, which trades transport
    and vendor independence for needing no API key; the model-level guard and
    the assessor's blindness both survive that trade.  See
    ``harness/commands/_subscription_judge.py`` for what each axis costs.
    """
    cfg = _judge_config(args)
    if args.transport == TRANSPORT_CLAUDE_CLI:
        from harness.commands._subscription_judge import build_subscription_judge

        judge, _backend = build_subscription_judge(
            cfg,
            prov_path=repo_root / args.provenance,
            repo_root=repo_root,
            timeout_seconds=args.cli_timeout,
            max_retries=args.max_retries,
        )
        return judge

    from harness.commands.freeze_grounding_baselines import build_paced_judge

    judge, _wrapper = build_paced_judge(
        cfg,
        tpm=args.tpm,
        rpm=args.rpm,
        max_retries=args.max_retries,
        prov_path=repo_root / args.provenance,
    )
    return judge


#: The independent default: a non-drafter model at a non-Claude endpoint.
TRANSPORT_OPENAI = "openai-compatible"

#: The Max subscription.  No API key, weaker independence (see
#: ``harness/commands/_subscription_judge.py``).
TRANSPORT_CLAUDE_CLI = "claude-cli"


def _add_evidence_args(p: argparse.ArgumentParser) -> None:
    """The flags that decide what evidence the assessor reads.

    Shared verbatim by ``preflight`` and ``assess``: the preflight hash binds
    the realised pack set under these flags, so the two commands must take the
    same ones or the operator could not reproduce the preflight at assess time.
    """
    what = p.add_mutually_exclusive_group(required=True)
    what.add_argument("--candidate", help="directory holding <section_id>.json artifacts")
    what.add_argument("--document",
                      help="dev-graph document snapshot (node id, or a document id with one current version)")
    p.add_argument("--graph-root", default=None,
                   help="repository root holding the dev-graph records (default: --repo-root)")
    p.add_argument("--project", default=None,
                   help="project label for the package request (default: the document id)")
    p.add_argument("--package-budget", type=int, default=DEFAULT_PACKAGE_BUDGET,
                   help="dev-graph package size budget for the document route")
    p.add_argument("--repo-root", default=os.environ.get("HARNESS_REPO_ROOT", "."))
    p.add_argument("--profile", default=None,
                   help="pre-evaluation profile JSON (default: the harness default profile)")
    p.add_argument("--out-dir", default=str(DEFAULT_REPORTS_DIR),
                   help="directory for the new report file (never overwritten)")
    p.add_argument("--budget", type=int, default=None,
                   help=(
                       "evidence-pack token budget per expectation. "
                       f"Default {DEFAULT_PACK_TOKEN_BUDGET} on a "
                       "transport with a token-per-minute ceiling, "
                       f"{UNCAPPED_DEFAULT_PACK_TOKEN_BUDGET} on one "
                       "without. A truncated pack is graded as "
                       "insufficient context, never as a clean pass"
                   ))
    p.add_argument("--span-fraction", type=float, default=DEFAULT_SPAN_BUDGET_FRACTION)
    p.add_argument(
        "--no-claims", action="store_true",
        help=(
            "withhold the claim ledger from every cell's evidence pack: no claim is "
            "loaded, rendered or charged, prose gets the whole budget, and each "
            "cell's grounding reads unassessable (spec decision 6; the blind lane "
            "over an imported proposal passes this)"
        ),
    )
    p.add_argument(
        "--criterion-budget", type=int, default=UNCAPPED_DEFAULT_PACK_TOKEN_BUDGET,
        help=(
            "token budget for one criterion's complete input (section plus declared "
            f"appendix). Default {UNCAPPED_DEFAULT_PACK_TOKEN_BUDGET}, the uncapped "
            "assessor budget; an input that does not fit is reported not scored, "
            "never truncated. Lower it only on a transport with a per-minute ceiling"
        ),
    )
    p.add_argument(
        "--transport",
        choices=[TRANSPORT_OPENAI, TRANSPORT_CLAUDE_CLI],
        default=os.environ.get("HARNESS_ASSESSOR_TRANSPORT", TRANSPORT_OPENAI),
        help=(
            "assessor transport. %(default)s by default: a non-drafter model at "
            "a non-Claude endpoint, which is the independent path. "
            f"'{TRANSPORT_CLAUDE_CLI}' speaks the Max subscription instead and "
            "needs no API key, at the cost of transport and vendor "
            "independence; HARNESS_JUDGE_MODEL must then be a Claude pin and "
            "HARNESS_JUDGE_VERSION should name the transport. The transport also "
            "decides the pack ceiling, so give the preflight the one you will assess with"
        ),
    )
    p.add_argument(
        "--import-manifest", default=None,
        help=(
            "an external import manifest to pin by sha256 beside the pack-set hash "
            "(default: <graph-root>/docs/tier4_orchestration_state/dev_graph/imports/"
            "<document id>.json when it exists)"
        ),
    )


def _parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="harness.commands.blind_assessment",
        description=(
            "Blind pre-evaluation of one candidate against a pre-evaluation "
            "profile. The report is bound to the candidate hash, profile version, "
            "assessor pin and the evidence preflight's pack-set hash. Advisory; "
            "never a runtime gate."
        ),
    )
    sub = ap.add_subparsers(dest="command", required=True)

    p_pre = sub.add_parser(
        "preflight",
        help="realise and report the evidence the assessor would read; bind it by hash; no assessor call",
    )
    _add_evidence_args(p_pre)

    p_assess = sub.add_parser("assess", help="assess one candidate and write a bound report")
    _add_evidence_args(p_assess)
    p_assess.add_argument(
        "--preflight", required=True,
        help=(
            "the evidence preflight report this assessment is bound to (required). "
            "The realised pack set is re-derived under this command's flags and must "
            "match the preflight's hash; a mismatch refuses before any assessor call"
        ),
    )
    p_assess.add_argument("--intake", default=None, help="ESR intake record id to stamp on the report")
    p_assess.add_argument("--provenance", default=str(DEFAULT_PROVENANCE_PATH))
    p_assess.add_argument("--n", type=int, default=MIN_MAJORITY_SAMPLES,
                          help="assessor samples per verdict (majority; N>=3)")
    p_assess.add_argument(
        "--criterion-n", type=int, default=DEFAULT_CRITERION_SAMPLES,
        help=(
            "assessor samples per criterion score (median and spread reported; "
            f"default {DEFAULT_CRITERION_SAMPLES}, minimum {MIN_MAJORITY_SAMPLES}). "
            "The criterion scorer reads each criterion's complete section verbatim "
            "plus its declared appendix rows, never a pack"
        ),
    )
    p_assess.add_argument(
        "--skip-criterion-scores", action="store_true",
        help="run the cells only; write no criterion scores and no total",
    )
    p_assess.add_argument("--tpm", type=int, default=_env_int("HARNESS_TPM_BUDGET", 5500))
    p_assess.add_argument("--rpm", type=int, default=_env_int("HARNESS_RPM_BUDGET", 28))
    p_assess.add_argument("--max-retries", type=int, default=_env_int("HARNESS_MAX_RETRIES", 6))
    p_assess.add_argument(
        "--assessor-model", default=None,
        help=(
            "override the HARNESS_JUDGE_MODEL pin for this run. Needed because "
            "the harness env file is loaded with override=True, so an exported "
            "variable cannot win against it. Must still not be a drafter model"
        ),
    )
    p_assess.add_argument(
        "--assessor-version", default=None,
        help=(
            "override the HARNESS_JUDGE_VERSION pin for this run. The report "
            "records model@version and nothing else about the assessor, so this "
            "tag is where a non-default transport is declared"
        ),
    )
    p_assess.add_argument(
        "--cli-timeout", type=int, default=_env_int("HARNESS_CLI_TIMEOUT", 300),
        help="per-call wall-clock limit for the claude-cli transport, in seconds",
    )
    ckpt = p_assess.add_mutually_exclusive_group()
    ckpt.add_argument(
        "--checkpoint", default=None,
        help=(
            "where to checkpoint every raw assessor response as it arrives "
            f"(default: {DEFAULT_CHECKPOINT_DIR}/checkpoint_<hash12>_<NNNN>.jsonl "
            "under --repo-root; never --out-dir, which holds reports). A run that "
            "fails on its last call can then be resumed instead of redrawn. An "
            "existing file is never appended to: name a new one, or --resume"
        ),
    )
    ckpt.add_argument(
        "--resume", default=None,
        help=(
            "resume an earlier run from its checkpoint: every call the file "
            "already holds is replayed from it and no quota is spent on it; the "
            "run goes live from the first call it does not cover, appending to the "
            "same file. The checkpoint's binding - candidate, profile, assessor "
            "pin, preflight pack set, sample counts - must equal this run's. The "
            "report declares how many of its calls were replayed"
        ),
    )
    ckpt.add_argument(
        "--no-checkpoint", action="store_true",
        help="write no response checkpoint; a failed run is then redrawn in full",
    )

    p_salvage = sub.add_parser(
        "salvage",
        help=(
            "rebuild a response checkpoint from the claude CLI's own session "
            "transcripts, so a run that spent its quota before the checkpoint "
            "existed can be resumed instead of redrawn"
        ),
    )
    _add_evidence_args(p_salvage)
    p_salvage.add_argument("--preflight", required=True,
                           help="the preflight the salvaged run was bound to")
    p_salvage.add_argument(
        "--transcripts", required=True,
        help=(
            "directory of the run's .jsonl session transcripts, one per assessor "
            "call (the CLI writes them under ~/.claude/projects/<working directory>)"
        ),
    )
    p_salvage.add_argument("--checkpoint", required=True,
                           help="the checkpoint file to write; must not exist")
    p_salvage.add_argument("--n", type=int, default=MIN_MAJORITY_SAMPLES,
                           help="the --n the salvaged run used (it binds the checkpoint)")
    p_salvage.add_argument("--criterion-n", type=int, default=DEFAULT_CRITERION_SAMPLES,
                           help="the --criterion-n the salvaged run used (it binds the checkpoint)")
    p_salvage.add_argument("--skip-criterion-scores", action="store_true",
                           help="set it if the salvaged run set it; it binds the checkpoint")
    p_salvage.add_argument("--assessor-model", default=None,
                           help="the assessor model pin the salvaged run used")
    p_salvage.add_argument("--assessor-version", default=None,
                           help="the assessor version pin the salvaged run used")

    p_verify = sub.add_parser("verify", help="re-bind a persisted report to a candidate")
    p_verify.add_argument("--report", required=True)
    p_verify.add_argument("--candidate", required=True)
    p_verify.add_argument("--repo-root", default=os.environ.get("HARNESS_REPO_ROOT", "."))
    p_verify.add_argument("--profile", default=None)

    p_freeze = sub.add_parser(
        "freeze",
        help=(
            "freeze a written report as the blind baseline: check the baseline "
            "conditions, copy the report and write a freeze record into --baseline-dir"
        ),
    )
    p_freeze.add_argument("--report", required=True, help="the blind report to freeze")
    p_freeze.add_argument("--candidate", required=True,
                          help="the materialised candidate directory the report is bound to")
    p_freeze.add_argument(
        "--baseline-dir", required=True,
        help=(
            "directory to hold the frozen copy and its freeze record; must hold no "
            "earlier freeze (a frozen baseline is never replaced). Relative to --repo-root"
        ),
    )
    p_freeze.add_argument("--repo-root", default=os.environ.get("HARNESS_REPO_ROOT", "."))
    p_freeze.add_argument("--profile", default=None)

    p_audit = sub.add_parser(
        "audit",
        help=(
            "integrity audit: five consistency checks over the parsed table rows, the "
            "claim ledger enumerated Unresolved, bound to the frozen baseline; no assessor call"
        ),
    )
    what = p_audit.add_mutually_exclusive_group(required=True)
    what.add_argument("--candidate", help="directory holding <section_id>.json artifacts")
    what.add_argument("--document",
                      help="dev-graph document snapshot (node id, or a document id with one current version)")
    p_audit.add_argument("--graph-root", default=None,
                         help="repository root holding the dev-graph records (default: --repo-root)")
    p_audit.add_argument("--project", default=None,
                         help="project label for the package request (default: the document id)")
    p_audit.add_argument("--package-budget", type=int, default=DEFAULT_PACKAGE_BUDGET,
                         help="dev-graph package size budget for the document route")
    p_audit.add_argument("--repo-root", default=os.environ.get("HARNESS_REPO_ROOT", "."))
    p_audit.add_argument("--profile", default=None,
                         help="pre-evaluation profile JSON (default: the harness default profile)")
    p_audit.add_argument("--out-dir", default=str(DEFAULT_REPORTS_DIR),
                         help="directory for the new audit report (never overwritten)")
    p_audit.add_argument(
        "--baseline-dir", default=None,
        help=(
            "the frozen blind baseline to bind to (relative to --repo-root). The report "
            "states whether its candidate hash and snapshot id equal the baseline's, or "
            "that the baseline was re-derived; without it the report says none was consulted"
        ),
    )

    p_cmp = sub.add_parser(
        "compare",
        help=(
            "ESR comparison: one row per historical observation over the frozen blind "
            "baseline, dispositions declared by the operator and every reference "
            "resolved; criterion scores compared separately; no assessor call"
        ),
    )
    p_cmp.add_argument("--baseline-dir", required=True,
                       help="the frozen blind baseline (relative to --repo-root)")
    p_cmp.add_argument("--esr", required=True, help="the operator-authored ESR record (JSON)")
    p_cmp.add_argument("--dispositions", required=True,
                       help="the operator's dispositions, bound to the baseline report's sha256")
    p_cmp.add_argument("--candidate", required=True,
                       help="the materialised candidate directory the baseline is bound to")
    p_cmp.add_argument("--register", required=True,
                       help="the fidelity register the dispositions' evidence_basis pointers resolve against")
    p_cmp.add_argument("--historical-candidate", default=None,
                       help="an earlier materialised copy, for 'addressed' rows and historical quotes")
    p_cmp.add_argument("--audit", action="append", default=[],
                       help="an integrity-audit report the dispositions cite (repeatable)")
    p_cmp.add_argument("--repo-root", default=os.environ.get("HARNESS_REPO_ROOT", "."))
    p_cmp.add_argument("--profile", default=None)
    p_cmp.add_argument("--out-dir", required=True,
                       help="directory for the comparison and revisions artifacts (never overwritten)")
    return ap


def _pack_params(args: argparse.Namespace) -> PackParams:
    """The evidence-selecting parameters, resolved exactly once for both commands.

    The pack ceiling belongs to the transport, not to the proposal.  A
    per-minute token cap is the OpenAI-compatible provider's; the CLI has
    none, so there the operator's budget alone governs.
    """
    uncapped = args.transport == TRANSPORT_CLAUDE_CLI
    token_budget = args.budget
    if token_budget is None:
        token_budget = UNCAPPED_DEFAULT_PACK_TOKEN_BUDGET if uncapped else DEFAULT_PACK_TOKEN_BUDGET
    return PackParams(
        token_budget=token_budget,
        span_budget_fraction=args.span_fraction,
        max_token_budget=None if uncapped else MAX_PACK_TOKEN_BUDGET,
        include_claims=not args.no_claims,
        criterion_token_budget=args.criterion_budget,
    )


def _build_evidence(
    args: argparse.Namespace, bundle: ProfileBundle, graph_root: Path, out_dir: Path
) -> BlindEvidence | None:
    """The document route's evidence, or ``None`` on the directory route.

    Snapshot, blind-view package, leakage guard, materialisation — all
    before any assessor exists.  A leak stops here.
    """
    if not args.document:
        return None
    return build_blind_evidence(
        graph_root,
        args.document,
        profile_version=bundle.version,
        out_dir=out_dir,
        budget=args.package_budget,
        project=args.project,
    )


def _audit(
    args: argparse.Namespace,
    bundle: ProfileBundle,
    graph_root: Path,
    out_dir: Path,
    repo_root: Path,
    clock: Callable[[], str] | None,
) -> int:
    """The ``audit`` sub-command: parse, check, enumerate, bind, write; then show
    that the snapshot id did not move by rebuilding it after the write."""
    from runner.dev_graph import build_snapshot

    evidence = _build_evidence(args, bundle, graph_root, out_dir)
    candidate_dir = evidence.candidate_dir if evidence is not None else Path(args.candidate)
    candidate = load_candidate(candidate_dir, bundle.profile)
    baseline_dir = None
    if args.baseline_dir:
        baseline_dir = Path(args.baseline_dir)
        if not baseline_dir.is_absolute():
            baseline_dir = repo_root / baseline_dir
    report = run_audit(
        candidate,
        profile_id=bundle.profile_id,
        profile_version=bundle.version,
        candidate_path=_portable(Path(candidate_dir), repo_root),
        evidence=evidence,
        baseline_dir=baseline_dir,
        out_dir=out_dir,
        graph_root=graph_root if evidence is not None else None,
        clock=clock,
    )
    path = write_audit(report, out_dir)
    print(render_audit(report.to_dict()))
    print(f"\naudit -> {path}")
    flags = list(report.flags)
    if evidence is not None:
        after = build_snapshot(graph_root).snapshot_id
        if after == evidence.snapshot_id:
            print(f"snapshot id after the write: {after} (unchanged)")
        else:
            print(f"snapshot id after the write: {after} (MOVED from {evidence.snapshot_id})")
            flags.append("snapshot id moved during the audit")
    return 1 if flags else 0


def _compare(
    args: argparse.Namespace,
    bundle: ProfileBundle,
    repo_root: Path,
    clock: Callable[[], str] | None,
) -> int:
    """The ``compare`` sub-command: load, bind, resolve every declared reference,
    write the comparison and the revision priorities."""
    def _under_root(raw: str) -> Path:
        p = Path(raw)
        return p if p.is_absolute() else repo_root / p

    baseline_dir = _under_root(args.baseline_dir)
    frozen = load_frozen_baseline(baseline_dir)
    esr = load_esr_record(_under_root(args.esr))
    dispositions = load_dispositions(_under_root(args.dispositions))
    candidate_dir = _under_root(args.candidate)
    candidate = load_candidate(candidate_dir, bundle.profile)
    historical = None
    historical_path = None
    if args.historical_candidate:
        historical_dir = _under_root(args.historical_candidate)
        historical = load_candidate(historical_dir, bundle.profile)
        historical_path = _portable(historical_dir, repo_root)
    register = load_register(_under_root(args.register))
    audits = load_audits(args.audit, repo_root=repo_root)
    report = run_comparison(
        frozen=frozen,
        esr=esr,
        dispositions=dispositions,
        candidate=candidate,
        candidate_path=_portable(candidate_dir, repo_root),
        register=register,
        historical_candidate=historical,
        historical_candidate_path=historical_path,
        audits=audits,
        repo_root=repo_root,
        clock=clock,
    )
    out_dir = _under_root(args.out_dir)
    path, revisions = write_comparison(report, out_dir)
    print(render_comparison(report.data))
    print(f"\ncomparison -> {path}")
    print(f"revisions  -> {revisions}")
    return 1 if report.flags else 0


def _portable(path: Path, repo_root: Path) -> str:
    """*path* relative to *repo_root* when it lies under it, else as given."""
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _invocation_record(judge: Judge) -> dict:
    """The backend's account of what its child could reach, if it keeps one.

    The subscription backend does (``invocation_record``); the OpenAI-compatible
    backend has no child process and an injected test backend says nothing.
    """
    backend = getattr(judge, "_backend", None)
    record = getattr(backend, "invocation_record", None)
    return dict(record()) if callable(record) else {}


def _is_transport_failure(exc: BaseException) -> bool:
    """Whether *exc* came from an assessor transport rather than the harness.

    Imported lazily: neither transport is pulled in by importing this command,
    and the ``claude-cli`` one is only ever imported when it is selected.
    """
    try:
        from runner.transport.errors import OpenAICompatTransportError
    except Exception:  # pragma: no cover - the transport package is optional
        OpenAICompatTransportError = ()  # type: ignore[assignment,misc]
    try:
        from runner.claude_transport import ClaudeTransportError
    except Exception:  # pragma: no cover
        ClaudeTransportError = ()  # type: ignore[assignment,misc]
    candidates = tuple(
        t for t in (OpenAICompatTransportError, ClaudeTransportError) if t
    )
    return bool(candidates) and isinstance(exc, candidates)


def _cache_binding(
    args: argparse.Namespace,
    *,
    digest: str,
    pin: str,
    profile_version: str,
    preflight_hash: str,
    params: PackParams,
) -> CacheBinding:
    """The binding a run's checkpoint carries.

    One builder for both commands: a checkpoint salvage writes must equal the
    one the assess run computes, or the resume is refused.  Two copies of this
    expression would be two chances to disagree.
    """
    return CacheBinding(
        candidate_hash=digest,
        profile_version=profile_version,
        assessor_pin=pin,
        preflight_pack_set_hash=preflight_hash,
        include_claims=params.include_claims,
        n=args.n,
        criterion_samples=None if args.skip_criterion_scores else args.criterion_n,
    )


def _open_checkpoint(
    args: argparse.Namespace,
    *,
    repo_root: Path,
    digest: str,
    pin: str,
    profile_version: str,
    preflight_hash: str,
    params: PackParams,
) -> ResponseCache | None:
    """Open this run's response checkpoint, or ``None`` when asked for none.

    The binding is everything that decides which prompts the run issues and
    what the answers mean.  It is written into a new checkpoint and checked
    against a resumed one, so one candidate's responses can never be replayed
    into another candidate's report.

    The default location is :data:`DEFAULT_CHECKPOINT_DIR` under the repository
    root, never ``--out-dir``: a checkpoint is runtime state, and the report
    directory holds reports.  A failed run writes no report and that stays
    true.
    """
    if args.no_checkpoint:
        return None
    binding = _cache_binding(
        args,
        digest=digest,
        pin=pin,
        profile_version=profile_version,
        preflight_hash=preflight_hash,
        params=params,
    )
    if args.resume:
        path = Path(args.resume)
        if not path.is_absolute():
            path = Path(args.repo_root).resolve() / path
        return ResponseCache(path, binding, resume=True)
    if args.checkpoint:
        path = Path(args.checkpoint)
        if not path.is_absolute():
            path = Path(args.repo_root).resolve() / path
    else:
        directory = repo_root / DEFAULT_CHECKPOINT_DIR
        directory.mkdir(parents=True, exist_ok=True)
        path = next_checkpoint_path(directory, digest)
    return ResponseCache(path, binding)


def _report_checkpoint(checkpoint: ResponseCache | None) -> None:
    """Name the checkpoint on a failed run, so the quota already spent is reusable."""
    if checkpoint is None or checkpoint.live + checkpoint.replayed == 0:
        return
    print(
        f"{checkpoint.live + checkpoint.replayed} assessor call(s) are checkpointed at "
        f"{checkpoint.path}\nresume with the same flags plus: --resume {checkpoint.path}",
        file=sys.stderr,
    )


def _read_transcript(path: Path) -> tuple[str, str]:
    """The (user prompt, assistant response) of one ``claude`` CLI session file.

    The CLI writes one JSONL transcript per session under
    ``~/.claude/projects/<slugified working directory>/``.  The assessor child
    runs one session per call in a fresh temp directory, so one file is one
    assessor call.  The response is reassembled from every top-level assistant
    turn by the transport's own joiner, so a generation that spanned turns is
    read exactly as the transport read it.  The system prompt is NOT recorded
    (it went to the CLI as ``--system-prompt``), which is why the caller
    matches on the user prompt and rebuilds the system prompt itself.

    The recorded user prompt has CRLF line endings on Windows: the transport
    writes it to the child's stdin, and the pipe translates.  They are
    translated back, and nothing else is normalised — a match must otherwise
    be byte for byte.
    """
    from runner.claude_transport import AssistantTurn, _join_assistant_turns

    user = ""
    turns: list[AssistantTurn] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, Mapping):
            continue
        if event.get("parentToolUseId") or event.get("parent_tool_use_id"):
            continue
        message = event.get("message")
        if not isinstance(message, Mapping):
            continue
        content = message.get("content")
        text = (
            content
            if isinstance(content, str)
            else "".join(
                b.get("text") or ""
                for b in (content or [])
                if isinstance(b, Mapping) and b.get("type") == "text"
            )
        )
        if event.get("type") == "user" and not user:
            # The prompt reached the child through a pipe, which on Windows
            # translated every newline to CRLF before the CLI recorded it.
            # Undoing that one deterministic transformation is what lets the
            # recorded prompt be compared to the rebuilt one byte for byte;
            # nothing else about the text is touched.
            user = text.replace("\r\n", "\n")
        elif event.get("type") == "assistant":
            stop = message.get("stop_reason")
            turns.append(AssistantTurn(text, stop if isinstance(stop, str) else None))
    return user, _join_assistant_turns(turns)


def _salvage(
    args: argparse.Namespace,
    bundle: ProfileBundle,
    candidate,
    *,
    digest: str,
    preflight_hash: str,
    params: PackParams,
    repo_root: Path,
) -> int:
    """Turn a directory of ``claude`` CLI transcripts into a response checkpoint.

    One-off recovery for a run that spent its quota before the checkpoint
    existed.  Nothing is guessed: each transcript's recorded user prompt must
    equal, byte for byte, a prompt rebuilt here from this profile and this
    candidate.  A transcript that matches nothing is named and left out, which
    costs the resumed run one live call and can never cost it a wrong answer.

    Only the cells are recovered.  A criterion prompt carries the aspect
    findings of the run that drew it, so it cannot be rebuilt from the
    candidate alone; and the criterion system prompt changed when the
    strict-JSON instruction was added, so replaying a criterion response drawn
    before that would let a report claim a score from a prompt that never
    produced it.  Those calls are redrawn.
    """
    from harness.evidence_pack import EvidencePackError
    from harness.rubrics import build_pack_for, build_rubric_prompts
    from runner.json_extract import extract_first_json_object

    transcripts = Path(args.transcripts)
    if not transcripts.is_absolute():
        transcripts = repo_root / transcripts
    if not transcripts.is_dir():
        raise BlindAssessmentError(f"transcript directory not found: {transcripts}")
    files = sorted(transcripts.glob("*.jsonl"), key=lambda p: p.stat().st_mtime)
    if not files:
        raise BlindAssessmentError(f"no .jsonl transcript in {transcripts}")

    # Rebuild every cell prompt this candidate yields, in the order assess
    # issues them.  The index is keyed by the user prompt, which is the only
    # half the transcript records.
    index: dict[str, tuple[str, str]] = {}
    collisions: set[str] = set()
    for rubric in bundle.rubric_set.rubrics:
        for section_id in bundle.profile.section_ids_for(rubric.criterion_id):
            path = candidate.sections.get(section_id)
            if path is None:
                continue
            try:
                pack = build_pack_for(
                    rubric,
                    path,
                    token_budget=params.token_budget,
                    span_budget_fraction=params.span_budget_fraction,
                    max_token_budget=params.max_token_budget,
                    include_claims=params.include_claims,
                )
            except EvidencePackError as exc:
                raise BlindAssessmentError(
                    f"could not rebuild the pack for {rubric.expectation_key}/{section_id}: {exc}"
                ) from exc
            system, user = build_rubric_prompts(rubric, pack)
            if user in index and index[user] != (system, user):
                collisions.add(user)
            index[user] = (system, user)
    if collisions:
        raise BlindAssessmentError(
            f"{len(collisions)} rebuilt cell prompt(s) share a user prompt under two "
            "system prompts; a transcript could not be attributed to one of them."
        )

    pin = f"{(cfg := _judge_config(args)).model}@{cfg.version}"
    binding = _cache_binding(
        args,
        digest=digest,
        pin=pin,
        profile_version=bundle.version,
        preflight_hash=preflight_hash,
        params=params,
    )
    path = Path(args.checkpoint)
    if not path.is_absolute():
        path = repo_root / path
    path.parent.mkdir(parents=True, exist_ok=True)
    cache = ResponseCache(path, binding)

    recovered = malformed = 0
    unmatched: list[tuple[Path, str]] = []
    for f in files:
        user, response = _read_transcript(f)
        hit = index.get(user)
        if hit is None and user.startswith(_EMBEDDED_SYSTEM_MARKER):
            # The transport embeds an over-long system prompt in the user
            # prompt; strip the envelope and try the plain form.
            tail = user.split(_EMBEDDED_SYSTEM_END, 1)
            hit = index.get(tail[1].lstrip("\n")) if len(tail) == 2 else None
        if hit is None or not response.strip():
            unmatched.append((f, user.splitlines()[0] if user else "<no user prompt>"))
            continue
        cache.record(prompt_hash(*hit), response)
        if extract_first_json_object(response) is None:
            # Recorded for the record, never replayed: the run that drew it
            # could not use it either.
            cache.discard_last("recorded response carries no parseable JSON object")
            malformed += 1
        else:
            recovered += 1

    expected = len(index) * args.n
    print(
        f"SALVAGE - {recovered} cell response(s) recovered from {len(files)} transcript(s)\n"
        f"checkpoint: {path}\n"
        f"binding:    candidate {digest[:19]}  profile {bundle.version[:19]}\n"
        f"            assessor {pin}  preflight {preflight_hash[:19]}\n"
        f"            n={args.n} criterion_samples={binding.criterion_samples} "
        f"include_claims={params.include_claims}\n"
        f"cells:      {recovered} of {expected} expected "
        f"({len(index)} prompt(s) x {args.n} sample(s))"
    )
    if malformed:
        print(f"malformed:  {malformed} recorded response(s) will not parse; each is redrawn")
    if unmatched:
        print(
            f"\nNOT RECOVERED - {len(unmatched)} transcript(s) matched no rebuilt cell "
            "prompt. Each costs the resumed run one live call, never a wrong answer.\n"
            "Criterion calls belong here: their prompts carry the drawing run's aspect "
            "findings, and the criterion system prompt has changed since."
        )
        for f, first in unmatched:
            print(f"  {f.name}  {first[:88]}")
    print(f"\nresume with: --resume {path}")
    return 0 if recovered else 1


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
    checkpoint: ResponseCache | None = None
    try:
        bundle = load_profile_bundle(args.profile, repo_root=repo_root)
        if args.command == "verify":
            data = load_report(
                args.report, args.candidate, bundle.profile, profile_version=bundle.version
            )
            print(render_report(data))
            print(f"\nverified: report is bound to the candidate at {args.candidate}")
            return 0
        if args.command == "freeze":
            baseline_dir = Path(args.baseline_dir)
            if not baseline_dir.is_absolute():
                baseline_dir = repo_root / baseline_dir
            frozen = freeze_baseline(
                args.report,
                args.candidate,
                bundle.profile,
                baseline_dir=baseline_dir,
                profile_version=bundle.version,
                repo_root=repo_root,
                clock=clock,
            )
            print(render_freeze(frozen.record))
            print(f"\nfrozen -> {frozen.freeze_path}")
            return 0
        if args.command == "compare":
            return _compare(args, bundle, repo_root, clock)

        out_dir = Path(args.out_dir)
        if not out_dir.is_absolute():
            out_dir = repo_root / out_dir
        graph_root = Path(args.graph_root).resolve() if args.graph_root else repo_root
        if args.command == "audit":
            return _audit(args, bundle, graph_root, out_dir, repo_root, clock)
        params = _pack_params(args)
        evidence = _build_evidence(args, bundle, graph_root, out_dir)

        if args.command == "preflight":
            preflight = run_preflight(
                bundle,
                candidate_dir=None if evidence is not None else args.candidate,
                evidence=evidence,
                params=params,
                graph_root=graph_root if evidence is not None else None,
                repo_root=repo_root,
                import_manifest=args.import_manifest,
                clock=clock,
            )
            path = write_preflight(preflight, out_dir)
            print(render_preflight(preflight.to_dict()))
            print(f"\npreflight -> {path}")
            return 1 if preflight.flags else 0

        # assess: the preflight is re-bound before the assessor exists.  A
        # mismatch names what moved and spends no quota.
        preflight_data = load_preflight(args.preflight)
        candidate = load_candidate(
            evidence.candidate_dir if evidence is not None else args.candidate, bundle.profile
        )
        realised = realise_pack_set(bundle, candidate, params)
        manifest = resolve_import_manifest(
            args.import_manifest, evidence, graph_root if evidence is not None else None
        )
        preflight_hash = check_preflight(
            preflight_data,
            bundle=bundle,
            candidate=candidate,
            realised=realised,
            params=params,
            import_manifest_sha256=file_sha256(manifest[0]) if manifest is not None else None,
            evidence=evidence,
        )
        if args.command == "salvage":
            return _salvage(
                args,
                bundle,
                candidate,
                digest=candidate_hash(candidate),
                preflight_hash=preflight_hash,
                params=params,
                repo_root=repo_root,
            )
        intake = read_esr_intake(graph_root, args.intake) if args.intake else None
        assessor = judge if judge is not None else _live_judge(args, repo_root)
        checkpoint = _open_checkpoint(
            args,
            repo_root=repo_root,
            digest=candidate_hash(candidate),
            pin=assessor_pin(assessor),
            profile_version=bundle.version,
            preflight_hash=preflight_hash,
            params=params,
        )
        if checkpoint is not None:
            assessor.attach_response_cache(checkpoint)
            held = checkpoint.replayable
            print(
                f"    checkpoint {checkpoint.path}"
                + (f" - replaying {held} recorded call(s) before going live" if held else "")
            )
        report = assess_candidate(
            assessor,
            bundle,
            args.candidate,
            evidence=evidence,
            intake=intake,
            token_budget=params.token_budget,
            max_token_budget=params.max_token_budget,
            span_budget_fraction=params.span_budget_fraction,
            n=args.n,
            clock=clock,
            include_claims=params.include_claims,
            criterion_samples=None if args.skip_criterion_scores else args.criterion_n,
            criterion_token_budget=params.criterion_token_budget,
            preflight_hash=preflight_hash,
            preflight_report=Path(args.preflight).as_posix(),
            assessor_transport=args.transport,
            assessor_invocation=_invocation_record(assessor),
        )
        path = write_report(report, out_dir)
        data = report.to_dict()
        print(render_report(data))
        print(f"\nreport -> {path}")
        return 1 if report.scope == SCOPE_PARTIAL else 0
    except _CLI_ERRORS as exc:
        print(f"blind assessment could not run (fail-closed): {exc}", file=sys.stderr)
        _report_checkpoint(checkpoint)
        return 2
    except Exception as exc:
        # A transport failure — a rejected key, an unreachable endpoint, a CLI
        # that will not spawn — is a fail-closed condition like any other, and
        # the operator should read one line rather than a traceback.  Checked
        # lazily so importing this command pulls in neither transport.
        if not _is_transport_failure(exc):
            raise
        print(
            f"the assessor transport failed (fail-closed, nothing written): "
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        _report_checkpoint(checkpoint)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
