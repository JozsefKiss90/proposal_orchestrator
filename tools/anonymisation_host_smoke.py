"""The pipeline's smoke run on the private host: A0 to A7 on the synthetic fixture (AN12).

AN12 of ``.scratch/msca-dn-anonymisation/tickets.md``. On the host, the
operator runs this against live Bedrock to show that the bundle carries a
working pipeline before the DN original is touched (AN13). It never reads a
real document: it builds the AN3 synthetic fixture itself, so it takes no
input file.

What it runs
------------
A0 intake, A2 redaction, A3 rewrite, A4 Table 1.4.1 synthesis, both halves of
A5, A6 structural fidelity and A7 acceptance, in the order the AN11 tests
chain them, each into its own directory under ``--root``. The two model
stages (A3, A5's attack) go through the runner's Converse transport, each
under its own token budget, and stop when it is reached.

What it does not do
-------------------
Make the operator's two acts. A6 needs a figure review, and A7 needs a signed
acceptance input. Without them the run stops with ``awaiting_operator`` and
writes a template for each, filled with what was measured and with
``<placeholder>`` values where the operator decides. A template still holding
a placeholder is refused before any stage reads it, so no report is written
from an unmade decision.

Re-running is free: every stage is idempotent, and the model stages replay
their checkpoints. A6 and A7 write into a directory named for the hash of the
operator input they used, so a corrected review never collides with the
report of an earlier one.

The policy
----------
The committed policy leaves the research-group re-identification threshold
Unresolved, and the attack refuses to run under it. The fixture is synthetic,
so the run writes a synthetic successor that sets it, as the AN8b and AN11
tests do, and the status file says so. It is never a policy for AN13.

Known stop
----------
No stage applies an A3 plan yet (AN6, AN11). If the live A3 model proposes an
edit, A7 refuses the plan. That is a correct refusal, recorded in the status
file, not a failure of the bundle.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Sequence

from runner import anonymisation_acceptance as aa
from runner import anonymisation_attack as atk
from runner import anonymisation_fidelity as af
from runner import anonymisation_intake as ai
from runner import anonymisation_leak_scan as ls
from runner import anonymisation_matching as matching
from runner import anonymisation_policy as ap
from runner import anonymisation_redaction as ar
from runner import anonymisation_rewrite as rw
from runner import anonymisation_table as at
from runner.atomic_write import atomic_write_text, canonical_json_bytes
from runner.original_configuration import THIS_REPOSITORY, inside_this_repository
from tests import _anonymisation_fixture as fx

STATUS_SCHEMA = "anonymisation_host_smoke/1"
STATUS_FILE = "smoke_status.json"
FIGURE_TEMPLATE = "operator/figure_review_template.json"
ACCEPTANCE_TEMPLATE = "operator/acceptance_input_template.json"
#: Where the installed bundle's manifest sits (``runner.offline_bundle.MANIFEST_FILE``).
BUNDLE_MANIFEST = THIS_REPOSITORY / "bundle_manifest.json"

EXIT_ACCEPTED = 0
EXIT_STOPPED = 1
EXIT_REFUSED = 2
EXIT_AWAITING = 3

SYNTHETIC_BASIS = ("AN12 synthetic smoke run on the AN3 fixture. The operator has not set this "
                   "threshold; this successor exists only for the fixture and is never used on "
                   "the DN original.")

_PLACEHOLDER = re.compile(r"^<.*>$", re.S)
_STAGE_ERRORS = (ai.IntakeRefused, ar.RedactionRefused, rw.RewriteRefused, at.TableRefused,
                 ls.LeakScanRefused, atk.AttackRefused, af.FidelityRefused, aa.AcceptanceRefused,
                 ap.PolicyRefused, matching.DictionaryRefused, fx.FixtureRefused)


class SmokeRefused(RuntimeError):
    """The smoke run cannot start as asked. Nothing was written."""


class _Awaiting(Exception):
    """An operator input is absent or unfilled; the message says which."""


@dataclass(frozen=True)
class SmokeResult:
    outcome: str
    """``accepted``, ``awaiting_operator``, ``stopped`` or ``refused``."""
    status: Path


def _sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _read(path: Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write(path: Path, record: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(canonical_json_bytes(record).decode("utf-8"), path)
    return path


def _placeholders(value: Any, where: str = "") -> list[str]:
    if isinstance(value, dict):
        return [p for k, v in value.items() for p in _placeholders(v, f"{where}.{k}")]
    if isinstance(value, list):
        return [p for i, v in enumerate(value) for p in _placeholders(v, f"{where}[{i}]")]
    return [where.lstrip(".")] if isinstance(value, str) and _PLACEHOLDER.match(value) else []


def synthetic_policy_record() -> dict[str, Any]:
    """The committed policy with the research-group threshold set for the fixture only."""
    record = copy.deepcopy(ap.load(ap.STARTING_POLICY_PATH).record)
    for target in record["reidentification_threshold"]["targets"]:
        if target["target"] == "research_group":
            target.update(max_correct_guesses=0, declared_status="Assumed", basis=SYNTHETIC_BASIS)
    return record


def bundle_revision() -> Optional[str]:
    """The revision the installed bundle's manifest names, when there is one."""
    try:
        return str(_read(BUNDLE_MANIFEST)["repository_revision"])
    except (OSError, ValueError, KeyError):
        return None


class _Run:
    def __init__(self, root: Path, header: dict[str, Any]) -> None:
        self.root = root
        self.header = header
        self.stages: list[dict[str, Any]] = []

    def stage(self, name: str, status: str, **facts: Any) -> None:
        self.stages.append({"stage": name, "status": status, **facts})

    def finish(self, outcome: str, **extra: Any) -> SmokeResult:
        path = _write(self.root / STATUS_FILE, {
            "schema": STATUS_SCHEMA, **self.header, "outcome": outcome,
            "stages": self.stages, **extra,
        })
        return SmokeResult(outcome, path)


def _figure_template(root: Path, unreviewed: Path, derivative_sha256: str) -> Path:
    report = _read(unreviewed)
    pages = sorted(f["page"] for f in report["figures"] if f.get("code") == "figure_not_looked_at")
    return _write(root / FIGURE_TEMPLATE, {
        "schema": af.REVIEW_SCHEMA,
        "record_type": af.REVIEW_RECORD_TYPE,
        "derivative_sha256": derivative_sha256,
        "pages": [{"page": page, "verdict": "<preserved, masked, redrawn or lost>",
                   "basis": "<how the page was looked at, such as operator_visual_comparison>",
                   "reviewed_by": "<who looked>", "reviewed_on": "<YYYY-MM-DD>", "note": ""}
                  for page in pages],
    })


def _acceptance_template(root: Path, derivative_sha256: str, revision: Optional[str]) -> Path:
    return _write(root / ACCEPTANCE_TEMPLATE, {
        "schema": aa.INPUT_SCHEMA,
        "record_type": aa.INPUT_RECORD_TYPE,
        "derivative_sha256": derivative_sha256,
        "decision": "accept",
        "attestations": {name: False for name in aa.ATTESTATIONS},
        "signed_by": "<who signs>",
        "signed_on": "<YYYY-MM-DD>",
        "pipeline_revision": revision or "<the 40-hex revision bundle_manifest.json names>",
        "export_rule": {"rule_id": "<the private environment's rule, or a note that this "
                                   "synthetic derivative is not exported>",
                        "issued_by": "<who issued it>", "read_on": "<YYYY-MM-DD>"},
    })


def _operator_input(path: Optional[Path], what: str) -> tuple[Path, str]:
    """The operator's file and its hash. :class:`_Awaiting` says why it cannot be used yet."""
    if path is None:
        raise _Awaiting(f"no {what} given")
    try:
        holes = _placeholders(_read(path))
    except (OSError, ValueError) as exc:
        raise _Awaiting(f"the {what} cannot be read: {exc}") from exc
    if holes:
        raise _Awaiting(f"the {what} still holds a placeholder at {', '.join(holes[:5])}")
    return Path(path), _sha(path)


def run(root: Path, *, a3_backend: Any, a5_backend: Any, a3_model: str, a5_model: str,
        max_output_tokens: int, a3_token_budget: int, a5_token_budget: int,
        figure_review: Optional[Path] = None, acceptance_input: Optional[Path] = None,
        pipeline_revision: Optional[str] = None) -> SmokeResult:
    """Run A0 to A7 on the synthetic fixture under *root*, as far as the operator's acts allow."""
    if inside_this_repository(Path(root)):
        raise SmokeRefused(f"{Path(root).name} resolves inside this repository "
                           f"({THIS_REPOSITORY.name}); the smoke run writes outside it")
    root = Path(root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    policy_path = _write(root / "policy" / "policy.json", synthetic_policy_record())
    policy = ap.load(policy_path)
    dictionary = fx.write_dictionary(root / "private")
    dictionary_sha = ap.policy_sha256(fx.DICTIONARY)
    built = fx.build(root / "fixture")
    common: dict[str, Any] = dict(policy=policy, policy_sha256=policy.sha256)
    entries: dict[str, Any] = dict(dictionary=dictionary, dictionary_sha256=dictionary_sha)
    out = _Run(root, {
        "fixture": {"pdf_sha256": _sha(built.pdf), "builder": "tests/_anonymisation_fixture.py"},
        "policy": {"sha256": policy.sha256, "synthetic_successor": True, "basis": SYNTHETIC_BASIS},
        "dictionary_sha256": dictionary_sha,
        "models": {"a3": a3_model, "a5": a5_model},
        "max_output_tokens": max_output_tokens,
    })
    stage = "A0"
    try:
        intake = ai.intake(pdf=built.pdf, expected_sha256=_sha(built.pdf), out_dir=root / "a0")
        out.stage("A0", "complete", route=intake.route)

        stage = "A2"
        redacted = ar.redact(pdf=built.pdf, intake_record=intake.intake_record, **common,
                             **entries, out_dir=root / "a2")
        out.stage("A2", "complete", derivative_sha256=redacted.derivative_sha256)

        stage = "A3"
        found = rw.passages(redacted.derivative)
        flags = rw.candidate_flags(found, rw.load_pinned_dictionary(dictionary, policy,
                                                                       dictionary_sha))
        rewritten = rw.rewrite(derivative=redacted.derivative, redaction_log=redacted.edit_log,
                               **common, **entries, flags=flags, backend=a3_backend,
                               model_id=a3_model, max_output_tokens=max_output_tokens,
                               token_budget=a3_token_budget, out_dir=root / "a3")
        out.stage("A3", rewritten.status, flagged_passages=len(flags),
                  tokens_used=rewritten.tokens_used, token_budget=a3_token_budget,
                  calls_made=rewritten.calls_made,
                  from_checkpoint=rewritten.passages_from_checkpoint,
                  pending=rewritten.passages_pending)
        if rewritten.status != "complete":
            return out.finish("stopped")

        stage = "A4"
        synthesised = at.synthesise(
            derivative=redacted.derivative, redaction_log=redacted.edit_log,
            intake_record=intake.intake_record, **common, **entries,
            spec=fx.write_table_spec(root / "private"),
            spec_sha256=ap.policy_sha256(fx.TABLE_SPEC), out_dir=root / "a4")
        derivative, derivative_sha = synthesised.derivative, synthesised.derivative_sha256
        out.stage("A4", "complete", derivative_sha256=derivative_sha)

        stage = "A5_scan"
        scan = ls.leak_scan(derivative=derivative, **common, **entries, out_dir=root / "a5_scan")
        out.stage("A5_scan", "complete", passed=scan.passed, counts=scan.counts)

        stage = "A5_attack"
        attacked = atk.attack(
            derivative=derivative, derivative_sha256=derivative_sha, **common, **entries,
            backend=a5_backend, model_id=a5_model, a3_model_id=a3_model,
            a3_input=redacted.derivative, a3_input_sha256=redacted.derivative_sha256,
            max_output_tokens=max_output_tokens, token_budget=a5_token_budget,
            out_dir=root / "a5_attack")
        out.stage("A5_attack", attacked.status, verdict=attacked.verdict,
                  tokens_used=attacked.tokens_used, token_budget=a5_token_budget,
                  calls_made=attacked.calls_made,
                  from_checkpoint=attacked.windows_from_checkpoint,
                  pending=attacked.windows_pending)
        if attacked.status != "complete":
            return out.finish("stopped")

        stage = "A6"
        logs = [redacted.edit_log, synthesised.log]
        try:
            review, review_sha = _operator_input(figure_review, "figure review")
        except _Awaiting as why:
            unreviewed = af.fidelity(derivative=derivative, derivative_sha256=derivative_sha,
                                     intake_record=intake.intake_record, **common,
                                     stage_logs=logs, figure_review=None,
                                     out_dir=root / "a6_unreviewed")
            template = _figure_template(root, unreviewed.report, derivative_sha)
            out.stage("A6", "awaiting_operator", detail=str(why), template=str(template))
            return out.finish("awaiting_operator", awaiting=["figure_review"])
        fidelity = af.fidelity(derivative=derivative, derivative_sha256=derivative_sha,
                               intake_record=intake.intake_record, **common, stage_logs=logs,
                               figure_review=review, out_dir=root / "a6" / review_sha[:12])
        out.stage("A6", "complete", passed=fidelity.passed, counts=fidelity.counts,
                  figure_review_sha256=review_sha)

        stage = "A7"
        try:
            operator, operator_sha = _operator_input(acceptance_input, "acceptance input")
        except _Awaiting as why:
            revision = pipeline_revision or bundle_revision()
            template = _acceptance_template(root, derivative_sha, revision)
            out.stage("A7", "awaiting_operator", detail=str(why), template=str(template))
            return out.finish("awaiting_operator", awaiting=["acceptance_input"])
        if not (rewritten.plan and attacked.report and attacked.details):
            raise RuntimeError("a complete A3 run or attack wrote no record; this is a bug")
        accepted = aa.accept(
            derivative=derivative, derivative_sha256=derivative_sha, **common, **entries,
            stage_logs=logs, table_row_map=synthesised.row_map, rewrite_plan=rewritten.plan,
            structural_fidelity=fidelity.report, leak_scan=scan.report,
            reidentification_report=attacked.report, reidentification_details=attacked.details,
            operator_input=operator, out_dir=root / "a7" / operator_sha[:12])
        out.stage("A7", "complete", public_record=str(accepted.public_record),
                  acceptance_input_sha256=operator_sha)
        return out.finish("accepted")
    except _STAGE_ERRORS as exc:
        out.stage(stage, "refused", detail=str(exc))
        return out.finish("refused")


# --------------------------------------------------------------------------- #
# Command line
# --------------------------------------------------------------------------- #


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m tools.anonymisation_host_smoke",
        description="Run A0 to A7 on the synthetic fixture over Bedrock Converse (AN12).",
    )
    parser.add_argument("--root", type=Path, required=True,
                        help="a private directory outside the installed bundle")
    parser.add_argument("--region", required=True, help=f"one of {list(rw.ALLOWED_REGIONS)}")
    parser.add_argument("--a3-model", required=True, help="the pinned A3 model id")
    parser.add_argument("--a5-model", required=True, help="the pinned A5 model id, not A3's")
    parser.add_argument("--max-output-tokens", type=int, required=True)
    parser.add_argument("--a3-token-budget", type=int, required=True)
    parser.add_argument("--a5-token-budget", type=int, required=True)
    parser.add_argument("--figure-review", type=Path, default=None)
    parser.add_argument("--acceptance-input", type=Path, default=None)
    parser.add_argument("--pipeline-revision", default=None,
                        help="default: the revision the installed bundle manifest names")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parser().parse_args(argv)
    try:
        a3 = rw.build_converse_backend(model_id=args.a3_model, region=args.region,
                                       max_output_tokens=args.max_output_tokens)
        a5 = atk.build_converse_backend(model_id=args.a5_model, region=args.region,
                                        max_output_tokens=args.max_output_tokens)
        result = run(args.root, a3_backend=a3, a5_backend=a5, a3_model=args.a3_model,
                     a5_model=args.a5_model, max_output_tokens=args.max_output_tokens,
                     a3_token_budget=args.a3_token_budget, a5_token_budget=args.a5_token_budget,
                     figure_review=args.figure_review, acceptance_input=args.acceptance_input,
                     pipeline_revision=args.pipeline_revision)
    except (SmokeRefused, rw.RewriteRefused, atk.AttackRefused) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return EXIT_REFUSED
    status = _read(result.status)
    for entry in status["stages"]:
        facts = ", ".join(f"{k}={v}" for k, v in entry.items() if k not in ("stage", "status")
                          and not isinstance(v, dict))
        print(f"{entry['stage']:<10} {entry['status']:<24} {facts}")
    print(f"outcome: {result.outcome} ({result.status})")
    return {"accepted": EXIT_ACCEPTED, "awaiting_operator": EXIT_AWAITING,
            "stopped": EXIT_STOPPED}.get(result.outcome, EXIT_REFUSED)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
