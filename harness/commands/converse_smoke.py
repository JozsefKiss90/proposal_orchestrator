"""
The Converse blind pass on the private host: receipt, assess, freeze (ticket AN12).

On the host the operator shows that the bundle carries a working assessor
before the V14 session depends on it. The pass runs on the synthetic dev-graph
world, never on a proposal: its candidate and profile are the ones the blind
lane's offline tests use (``tests/fixtures/dev_graph_synthetic`` and
:func:`write_synthetic_profile`).

Three steps
-----------
``prepare``
    Builds the world under ``--root``, outside the installed bundle, and runs
    the evidence preflight. Then it drafts a readiness receipt from the
    Converse template, filled with what can be measured before the run: the
    request the judge's own builder makes, the preflight's bindings, the
    world's paths. No assessor call is made. Everything only the operator can
    attest stays a ``<placeholder>``, which the receipt reader refuses.
``assess``
    Refuses unless the operator's receipt is green, as V13 requires before a
    private run. Then it runs ``assess`` over ``bedrock-converse``, writing
    the checkpoint the receipt names, and ``freeze`` under the V04 checks: the
    same commands a real run takes. Last, it reads the receipt against the
    blind report.
``check``
    Reads the receipt with :func:`harness.execution_receipt.check` as things
    stand, against the preflight and, once it exists, the report. Green is
    that validator's verdict; this command adds no reading of its own.

The region
----------
The report does not record the region the client targeted. The draft takes
it from ``AWS_REGION`` or ``AWS_DEFAULT_REGION``, the variables the runner's
Converse transport reads, and both ``prepare`` and ``assess`` refuse one
outside ADR-001's two before any call.

Advisory output only.  The harness is never a runtime gate.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Callable, Optional, Sequence

import harness.blind_assessment as blind
import harness.commands.blind_assessment as ba
import harness.grounding_scope as gs
from harness import execution_receipt as er
from harness.record_binding import file_sha256
from runner.anonymisation_rewrite import ALLOWED_REGIONS
from runner.dev_graph import import_document
from runner.original_configuration import THIS_REPOSITORY, inside_this_repository

FIXTURE = THIS_REPOSITORY / "tests" / "fixtures" / "dev_graph_synthetic"
CANDIDATE = Path("docs/tier5_deliverables/candidates/synthetic_candidate.json")
DOCUMENT_ID = "CAND-1"
TEMPLATE = THIS_REPOSITORY / "harness" / "execution_receipt_template_bedrock_converse.json"
BUNDLE_MANIFEST = THIS_REPOSITORY / "bundle_manifest.json"

WORLD_DIR = "world"
BASELINE_DIR = "baseline"
DRAFT_FILE = "receipt_draft.json"
PREPARED_FILE = "prepared.json"
IMPORT_MANIFEST_FILE = "import_manifest.json"
CHECKPOINT_NAME = "an12_converse_smoke.jsonl"

EXIT_GREEN = 0
EXIT_FINDINGS = 1
EXIT_REFUSED = 2


class SmokeRefused(RuntimeError):
    """The pass cannot run as asked. No assessor call was made."""


# --------------------------------------------------------------------------- #
# The synthetic world
# --------------------------------------------------------------------------- #


def _write_json(path: Path, data: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def write_synthetic_profile(root: Path) -> Path:
    """A call-neutral profile whose three criteria map onto the fixture
    candidate's sections S1, S2 and S3."""
    criteria = [
        ("aims", "Aims", "S1", "aims-objectives", "Clarity of the objectives", ["objective"]),
        ("plan", "Plan", "S2", "plan-tasks", "Credibility of the task plan", ["task"]),
        ("outputs", "Outputs", "S3", "outputs-deliverables", "Definition of the deliverables", ["deliverable"]),
    ]
    registry = {
        "instruments": [
            {
                "instrument_type": "SYN-GRAPH",
                "criteria": [
                    {"criterion_id": rid, "evaluator_expectations": [text]}
                    for _c, rid, _s, _k, text, _t in criteria
                ],
            }
        ]
    }
    scorecard = {
        "scorecard_id": "syn_graph_scorecard",
        "provenance": {"version": "0.1"},
        "scoring": {"scale": "0-5", "levels": {"0": "none", "5": "full"}, "overall_threshold": 10, "overall_max": 15},
        "criteria": [
            {
                "id": cid,
                "name": rid,
                "weight_pct": 34 if cid == "aims" else 33,
                "aspects": [{"id": key, "text": text, "option_tag": "Track one", "source_page": 1}],
            }
            for cid, rid, _s, key, text, _t in criteria
        ],
        "excluded_aspects": [],
    }
    rubrics = {
        "rubric_set_id": "syn_graph_rubrics",
        "version": "0.1.0",
        "scorecard_id": "syn_graph_scorecard",
        "scorecard_version": "0.1",
        "rubrics": [
            {
                "expectation_key": key,
                "criterion_id": cid,
                "expectation_text": text,
                "rubric": "Integrity-framed: addressed AND grounded.",
                "evaluation_steps": ["Check the spans.", "Check the claims."],
                "pass_threshold": 0.7,
                "selection_terms": terms,
                "anchor_sub_section_ids": [sid],
            }
            for cid, _rid, sid, key, text, terms in criteria
        ],
    }
    profile = {
        "profile_id": "syn_graph",
        "label": "Synthetic graph-mapped profile",
        "instrument": {
            "registry_instrument_type": "SYN-GRAPH",
            "name": "Synthetic Graph Track",
            "form_name": "Synthetic Graph Assessment Form",
        },
        "option_tag_grammar": {
            "applicable_variant": "Track one",
            "known_variants": ["Track one", "Track two"],
            "variant_prefix": "",
            "all_except_prefix": "all tracks except ",
        },
        "criteria": [
            {"id": cid, "registry_criterion_id": rid, "section_ids": [sid]}
            for cid, rid, sid, _k, _t, _terms in criteria
        ],
        "registry_path": "syn/registry.json",
        "scorecard": {"path": "syn/scorecard.json", "scorecard_id": "syn_graph_scorecard", "version": "0.1"},
        "rubric_set": {"path": "syn/rubrics.json", "rubric_set_id": "syn_graph_rubrics", "version": "0.1.0"},
    }
    _write_json(root / "syn/registry.json", registry)
    _write_json(root / "syn/scorecard.json", scorecard)
    _write_json(root / "syn/rubrics.json", rubrics)
    return _write_json(root / "syn/profile.json", profile)


def _region() -> str:
    region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or ""
    if region not in ALLOWED_REGIONS:
        raise SmokeRefused(f"region {region or '(unset)'!r} is outside ADR-001's "
                           f"{list(ALLOWED_REGIONS)}; set AWS_REGION")
    return region


def _single(directory: Path, pattern: str, what: str) -> Path:
    found = sorted(p for p in directory.glob(pattern) if p.is_file())
    if len(found) != 1:
        raise SmokeRefused(f"expected one {what} in {directory}, found {len(found)}")
    return found[0]


# --------------------------------------------------------------------------- #
# prepare: the world, the preflight and the receipt draft, with no model call
# --------------------------------------------------------------------------- #


def _shared(world: Path, profile: Path, manifest: Path) -> list[str]:
    return ["--document", DOCUMENT_ID, "--graph-root", str(world), "--repo-root", str(world),
            "--profile", str(profile), "--transport", ba.TRANSPORT_BEDROCK_CONVERSE,
            "--grounding-scope", gs.SCOPE_CONTENT_FOCUSED, "--import-manifest", str(manifest)]


def _assess_argv(root: Path, prepared: dict[str, Any]) -> list[str]:
    world = root / WORLD_DIR
    return ["assess", *_shared(world, Path(prepared["profile"]), Path(prepared["import_manifest"])),
            "--out-dir", str(world / "reports"), "--preflight", prepared["preflight"],
            "--assessor-model", prepared["assessor_model"],
            "--assessor-version", prepared["assessor_version"]]


def _draft(root: Path, world: Path, prepared: dict[str, Any], region: str) -> Path:
    """The Converse receipt draft, from the preflight and the request the assessor will send.

    The request is built by the judge's own Converse builder, which makes no
    network call, so the draft records what the run sends rather than what the
    configuration says.
    """
    args = ba._parser().parse_args(_assess_argv(root, prepared))
    judge = ba._live_judge(args, world)
    # The ConverseRetryingBackend wraps the runner's BedrockConverseBackend.
    backend: Any = judge._backend
    request = backend._inner._build_request([{"role": "user", "content": ""}])
    sent = request["inferenceConfig"]
    preflight_path = Path(prepared["preflight"])
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    profile = Path(prepared["profile"])
    doc = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    doc.pop("_what_this_is")
    try:
        revision = json.loads(BUNDLE_MANIFEST.read_text(encoding="utf-8"))["repository_revision"]
    except (OSError, ValueError, KeyError):
        revision = doc["repository_revision"]
    doc.update(receipt_id="an12_converse_smoke", private_clone_root=str(world),
               repository_revision=revision)
    doc["model_identity"]["pin"] = blind.assessor_pin(judge)
    values = {"model": request["modelId"], "temperature": str(sent["temperature"]),
              "max_tokens": str(sent["maxTokens"])}
    for setting in doc["effective_settings"]:
        setting["value"] = values[setting["name"]]
    doc["rendered_request"].update(model_id=request["modelId"], temperature=sent["temperature"],
                                   max_tokens=sent["maxTokens"],
                                   tool_config_present="toolConfig" in request, region=region)
    doc["checkpoint"]["path"] = prepared["checkpoint"]
    manifest = preflight["import_manifest"]
    doc["preflight"] = {
        "report_path": str(preflight_path), "report_sha256": file_sha256(preflight_path),
        "pack_set_hash": preflight["pack_set_hash"], "document_id": preflight["document_id"],
        "profile_id": preflight["profile_id"], "profile_path": str(profile),
        "profile_sha256": file_sha256(profile), "profile_version": preflight["profile_version"],
        "import_manifest_path": manifest["path"], "import_manifest_sha256": manifest["sha256"],
        "grounding_scope": gs.declared_scope_of(preflight),
    }
    return _write_json(root / DRAFT_FILE, doc)


def prepare(root: Path, *, assessor_model: str, assessor_version: str,
            clock: Optional[Callable[[], str]] = None) -> Path:
    """Build the world, run the preflight and draft the receipt. No assessor call. The draft's path."""
    if inside_this_repository(Path(root)):
        raise SmokeRefused(f"{Path(root).name} resolves inside this repository "
                           f"({THIS_REPOSITORY.name}); the pass writes outside it")
    root = Path(root).expanduser().resolve()
    region = _region()
    world = root / WORLD_DIR
    if world.exists():
        raise SmokeRefused(f"{world} exists; a pass builds a fresh world")
    shutil.copytree(FIXTURE, world)
    import_document(world, CANDIDATE)
    profile = write_synthetic_profile(world)
    manifest = _write_json(root / IMPORT_MANIFEST_FILE,
                           {"synthetic": True, "purpose": "AN12 host smoke pass"})
    preflights = world / "reports_preflight"
    code = ba.main(["preflight", *_shared(world, profile, manifest), "--out-dir", str(preflights)],
                   clock=clock)
    if code != 0:
        raise SmokeRefused("the evidence preflight did not pass; see its output above")
    prepared = {
        "assessor_model": assessor_model, "assessor_version": assessor_version,
        "profile": str(profile), "import_manifest": str(manifest),
        "preflight": str(_single(preflights, "preflight_*.json", "preflight report")),
        "checkpoint": str(world / ".harness" / "checkpoints" / CHECKPOINT_NAME),
    }
    _write_json(root / PREPARED_FILE, prepared)
    return _draft(root, world, prepared, region)


# --------------------------------------------------------------------------- #
# assess: a green receipt first, then the pass and the freeze
# --------------------------------------------------------------------------- #


def _report(root: Path) -> Optional[dict[str, Any]]:
    reports = root / WORLD_DIR / "reports"
    if not reports.is_dir() or not any(p.is_file() for p in reports.glob("*.json")):
        return None
    return json.loads(_single(reports, "*.json", "blind report").read_text(encoding="utf-8"))


def check_receipt(root: Path, receipt_path: Path) -> er.ReceiptCheck:
    """The receipt validator's verdict on *receipt_path* for the pass under *root*.

    Before the pass it reads the receipt against the preflight; once the blind
    report exists it also reads it against the report.
    """
    root = Path(root).resolve()
    receipt_path = er.receipt_path_outside(Path(receipt_path), THIS_REPOSITORY)
    receipt = er.load_receipt(receipt_path)
    prepared = json.loads((root / PREPARED_FILE).read_text(encoding="utf-8"))
    preflight = json.loads(Path(prepared["preflight"]).read_text(encoding="utf-8"))
    profile = Path(prepared["profile"])
    intended = er.IntendedPair(
        candidate_document_id=preflight["document_id"], profile_id=preflight["profile_id"],
        profile_path=str(profile), profile_sha256=file_sha256(profile),
    )
    return er.check(receipt, intended, receipt_dir=receipt_path.parent, report=_report(root))


def assess(root: Path, receipt_path: Path, *,
           clock: Optional[Callable[[], str]] = None) -> er.ReceiptCheck:
    """Refuse unless the receipt is green; then assess, freeze and read it against the report."""
    root = Path(root).resolve()
    _region()
    if _report(root) is not None:
        raise SmokeRefused("this root already holds a blind report; prepare a fresh root")
    before = check_receipt(root, receipt_path)
    if not before.green:
        raise SmokeRefused("the receipt is not green before the pass:\n  "
                           + "\n  ".join(before.lines()))
    prepared = json.loads((root / PREPARED_FILE).read_text(encoding="utf-8"))
    world = root / WORLD_DIR
    code = ba.main([*_assess_argv(root, prepared), "--checkpoint", prepared["checkpoint"]],
                   clock=clock)
    if code != 0:
        raise SmokeRefused(f"the assessment exited {code}; see its output above")
    report_path = _single(world / "reports", "*.json", "blind report")
    candidates = sorted((world / "reports" / "candidates").iterdir())
    if len(candidates) != 1:
        raise SmokeRefused(f"expected one materialised candidate, found {len(candidates)}")
    code = ba.main(["freeze", "--report", str(report_path), "--candidate", str(candidates[0]),
                    "--baseline-dir", str(root / BASELINE_DIR), "--repo-root", str(world),
                    "--profile", prepared["profile"]], clock=clock)
    if code != 0:
        raise SmokeRefused(f"the freeze exited {code}; see its output above")
    return check_receipt(root, receipt_path)


# --------------------------------------------------------------------------- #
# Command line
# --------------------------------------------------------------------------- #


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m harness.commands.converse_smoke",
        description="A synthetic blind pass over Bedrock Converse, with its receipt (AN12).",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare", help="build the world, run the preflight, draft the receipt")
    p.add_argument("--root", type=Path, required=True,
                   help="a private directory outside the installed bundle")
    p.add_argument("--assessor-model", required=True)
    p.add_argument("--assessor-version", required=True,
                   help="a version tag naming bedrock-converse")
    a = sub.add_parser("assess", help="validate the receipt, then assess and freeze")
    a.add_argument("--root", type=Path, required=True)
    a.add_argument("--receipt", type=Path, required=True)
    c = sub.add_parser("check", help="read the receipt against the pass, as it stands")
    c.add_argument("--root", type=Path, required=True)
    c.add_argument("--receipt", type=Path, required=True)
    return parser


def main(argv: Optional[Sequence[str]] = None, *,
         clock: Optional[Callable[[], str]] = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "prepare":
            draft = prepare(args.root, assessor_model=args.assessor_model,
                            assessor_version=args.assessor_version, clock=clock)
            print(f"receipt draft: {draft}")
            print("Fill every <placeholder> into a copy, then run 'assess --receipt <copy>'.")
            return EXIT_GREEN
        if args.command == "assess":
            result = assess(args.root, args.receipt, clock=clock)
            print(f"frozen into {Path(args.root).resolve() / BASELINE_DIR}")
        else:
            result = check_receipt(args.root, args.receipt)
    except (SmokeRefused, er.ReceiptError, OSError, KeyError, ValueError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return EXIT_REFUSED
    for line in result.lines():
        print(line)
    print("receipt green" if result.green else f"{result.findings_total} finding(s)")
    return EXIT_GREEN if result.green else EXIT_FINDINGS


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
