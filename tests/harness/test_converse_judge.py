"""
The Bedrock Converse assessor (ticket AN1a).

The private host reaches one model route: the native Converse API through the
``bedrock-runtime`` PrivateLink endpoint.  These tests drive the real
:class:`~runner.transport.bedrock_converse.BedrockConverseBackend` with only
``boto3.client`` replaced, so the request the judge builds is the request
Converse would receive.

Three groups:

* The judge builds the Converse backend from a resolved ``bedrock_converse``
  configuration, with the pinned model, temperature 0 and the token limit.
* The builder refuses what would misdescribe the report: a version tag that
  does not name the transport, and an environment that resolves to another
  backend.
* ``blind_assessment`` accepts ``bedrock-converse`` and runs a full synthetic
  blind pass over the fake Converse client.

No test here reaches a network.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest

import harness.commands.blind_assessment as cmd
import harness.grounding_scope as gs
import harness.judge as hj
import runner.transport.bedrock_converse as bc
from harness.commands import _converse_judge as cj
from harness.judge import Judge, JudgeConfig
from harness.rubrics import load_profile_bundle
from runner.dev_graph import import_document
from tests.harness._preflight import preflighted
from tests.harness.test_blind_leakage import (
    CANDIDATE,
    ESR_DOC,
    FIXTURE,
    FROZEN,
    RecordingBackend,
    _graph_profile,
)

PIN = "eu.anthropic.claude-sonnet-4-6"
VERSION = f"{cj.TRANSPORT_TAG}-eu-west-1@2026-10-14"


class FakeConverseClient:
    """Stands in for ``boto3.client('bedrock-runtime')``.

    Keeps every request it receives and answers through *inner*, a backend of
    the ``messages -> {"content": ...}`` shape, so the scripted replies of the
    other blind-lane tests serve here unchanged.
    """

    def __init__(self, inner=None) -> None:
        self.inner = inner or RecordingBackend()
        self.requests: list[dict[str, Any]] = []
        self.client_kwargs: dict[str, Any] = {}

    def converse(self, **kwargs: Any) -> dict[str, Any]:
        self.requests.append(kwargs)
        messages = [{"role": "system", "content": b["text"]} for b in kwargs.get("system", [])]
        for m in kwargs["messages"]:
            text = "".join(block.get("text", "") for block in m["content"])
            messages.append({"role": m["role"], "content": text})
        reply = self.inner(messages)["content"]
        return {
            "output": {"message": {"role": "assistant", "content": [{"text": reply}]}},
            "usage": {"inputTokens": 10, "outputTokens": 5, "totalTokens": 15},
        }


@pytest.fixture
def client(monkeypatch) -> FakeConverseClient:
    fake = FakeConverseClient()

    def _factory(service, **kwargs):
        assert service == "bedrock-runtime"
        fake.client_kwargs = kwargs
        return fake

    monkeypatch.setattr(bc.boto3, "client", _factory)
    return fake


@pytest.fixture
def converse_env(monkeypatch) -> None:
    """The environment the private host resolves: Converse, an env model that
    is not the pin, and an EU region."""
    monkeypatch.delenv("ORCHESTRATOR_TRANSPORT_PRESET", raising=False)
    monkeypatch.delenv("ORCHESTRATOR_PRODUCTION_MODE", raising=False)
    monkeypatch.setenv("ORCHESTRATOR_TRANSPORT_BACKEND", "bedrock_converse")
    monkeypatch.setenv("ORCHESTRATOR_TRANSPORT_MODEL", "env-default-model")
    monkeypatch.setenv("AWS_REGION", "eu-west-1")
    # By dotted path: resolved from sys.modules now, so a module another test
    # reloaded is the one patched, and the operator's .env.harness never loads.
    monkeypatch.setattr("harness.commands._common.load_harness_env", lambda: None)


# --------------------------------------------------------------------------- #
# The judge builds the Converse backend
# --------------------------------------------------------------------------- #


class TestTheJudgeBuildsConverse:
    def test_a_resolved_converse_config_builds_the_converse_backend(self, converse_env, client):
        judge = Judge(JudgeConfig(model=PIN, version=VERSION, max_tokens=3072))
        assert judge.raw_invoke("system text", "user text") == '{"passed": true, "score": 0.9, "rationale": "scripted pass"}'
        assert isinstance(judge._backend, bc.BedrockConverseBackend)

    def test_the_request_carries_the_pin_temperature_and_token_limit(self, converse_env, client):
        judge = Judge(JudgeConfig(model=PIN, version=VERSION, max_tokens=3072))
        judge.raw_invoke("system text", "user text")
        (request,) = client.requests
        assert request["modelId"] == PIN
        assert request["inferenceConfig"] == {"maxTokens": 3072, "temperature": 0.0}
        assert request["system"] == [{"text": "system text"}]
        assert request["messages"] == [{"role": "user", "content": [{"text": "user text"}]}]

    def test_the_request_carries_no_tools(self, converse_env, client):
        Judge(JudgeConfig(model=PIN, version=VERSION)).raw_invoke("s", "u")
        (request,) = client.requests
        assert "toolConfig" not in request

    def test_the_client_targets_the_resolved_region(self, converse_env, client):
        Judge(JudgeConfig(model=PIN, version=VERSION)).raw_invoke("s", "u")
        assert client.client_kwargs["region_name"] == "eu-west-1"

    def test_the_converse_route_needs_no_base_url(self, converse_env, client):
        """The gap §9 of the handoff names: the OpenAI-style build raised here."""
        from runner.transport.config import resolve_provider_config

        assert resolve_provider_config().base_url is None
        Judge(JudgeConfig(model=PIN, version=VERSION)).raw_invoke("s", "u")
        assert len(client.requests) == 1


# --------------------------------------------------------------------------- #
# The builder
# --------------------------------------------------------------------------- #


class TestTheBuilder:
    def test_the_builder_wires_the_pin_and_a_provenance_log(self, converse_env, client, tmp_path):
        judge, wrapper = cj.build_converse_judge(
            JudgeConfig(model=PIN, version=VERSION), prov_path=tmp_path / "prov.jsonl", log=lambda _m: None
        )
        judge.raw_invoke("s", "u")
        assert judge.config.model == PIN
        assert judge.provenance_log is not None
        assert client.requests[0]["modelId"] == PIN
        assert wrapper.calls == 1

    def test_a_version_tag_that_does_not_name_the_transport_is_refused(self, converse_env, client, tmp_path):
        cfg = JudgeConfig(model=PIN, version="claude-cli-subscription@2026-10-05")
        with pytest.raises(cj.ConverseJudgeError, match=cj.TRANSPORT_TAG):
            cj.build_converse_judge(cfg, prov_path=tmp_path / "prov.jsonl")

    def test_an_environment_resolving_another_backend_is_refused(self, converse_env, client, monkeypatch, tmp_path):
        """The flag says Converse, the environment says otherwise: the report
        would name a transport it did not speak."""
        monkeypatch.setenv("ORCHESTRATOR_TRANSPORT_BACKEND", "ollama")
        with pytest.raises(cj.ConverseJudgeError, match="ollama"):
            cj.build_converse_judge(JudgeConfig(model=PIN, version=VERSION), prov_path=tmp_path / "prov.jsonl")

    def test_a_retryable_failure_is_retried(self, converse_env, monkeypatch, tmp_path):
        from botocore.exceptions import ClientError

        class _Throttled(FakeConverseClient):
            def converse(self, **kwargs):
                if not self.requests:
                    self.requests.append(kwargs)
                    raise ClientError({"Error": {"Code": "ThrottlingException", "Message": "slow"}}, "Converse")
                return super().converse(**kwargs)

        fake = _Throttled()
        monkeypatch.setattr(bc.boto3, "client", lambda *_a, **_k: fake)
        import harness.commands.freeze_grounding_baselines as fgb

        monkeypatch.setattr(fgb.time, "sleep", lambda _s: None)
        judge, wrapper = cj.build_converse_judge(
            JudgeConfig(model=PIN, version=VERSION), prov_path=tmp_path / "prov.jsonl",
            max_retries=2, log=lambda _m: None,
        )
        assert judge.raw_invoke("s", "u")
        assert len(fake.requests) == 2
        assert wrapper.retries == 1


# --------------------------------------------------------------------------- #
# The command
# --------------------------------------------------------------------------- #


@pytest.fixture
def world(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    shutil.copytree(FIXTURE, root)
    import_document(root, CANDIDATE)
    import_document(root, ESR_DOC, state="submitted")
    return root


class TestTheCommand:
    def test_the_parser_accepts_the_converse_transport(self):
        args = cmd._parser().parse_args(
            ["assess", "--candidate", "x", "--preflight", "x", "--grounding-scope", gs.SCOPE_CONTENT_FOCUSED,
             "--transport", cmd.TRANSPORT_BEDROCK_CONVERSE]
        )
        assert args.transport == cj.TRANSPORT_TAG == "bedrock-converse"

    def test_the_default_transport_is_unchanged(self):
        args = cmd._parser().parse_args(
            ["assess", "--candidate", "x", "--preflight", "x", "--grounding-scope", gs.SCOPE_CONTENT_FOCUSED]
        )
        assert args.transport == cmd.TRANSPORT_OPENAI

    def test_the_converse_transport_is_uncapped(self):
        """Converse carries the same Claude context as the CLI; no per-minute
        provider cap shrinks the pack."""
        args = cmd._parser().parse_args(
            ["assess", "--candidate", "x", "--preflight", "x", "--grounding-scope", gs.SCOPE_CONTENT_FOCUSED,
             "--transport", cmd.TRANSPORT_BEDROCK_CONVERSE]
        )
        params = cmd._pack_params(args)
        assert params.max_token_budget is None

    def test_the_converse_transport_builds_the_converse_judge(self, converse_env, client, monkeypatch, tmp_path):
        monkeypatch.setattr(hj, "resolve_judge_config", lambda: JudgeConfig(model=PIN, version=VERSION))
        args = cmd._parser().parse_args(
            ["assess", "--candidate", "x", "--preflight", "x", "--grounding-scope", gs.SCOPE_CONTENT_FOCUSED,
             "--transport", cmd.TRANSPORT_BEDROCK_CONVERSE]
        )
        judge = cmd._live_judge(args, tmp_path)
        judge.raw_invoke("s", "u")
        assert client.requests[0]["modelId"] == PIN

    def test_a_full_synthetic_blind_pass_runs_over_converse(self, converse_env, client, world):
        bundle = load_profile_bundle(_graph_profile(world), repo_root=world)
        out = world / "reports"
        argv = [
            "assess", "--document", "CAND-1", "--graph-root", str(world), "--out-dir", str(out),
            "--repo-root", str(world), "--profile", str(bundle.profile.source_path),
            "--transport", cmd.TRANSPORT_BEDROCK_CONVERSE, "--grounding-scope", gs.SCOPE_CONTENT_FOCUSED,
            "--assessor-model", PIN, "--assessor-version", VERSION, "--no-checkpoint",
        ]
        code = cmd.main(preflighted(argv, clock=lambda: FROZEN), clock=lambda: FROZEN)
        assert code == 0
        (path,) = [p for p in out.iterdir() if p.is_file()]
        report = json.loads(path.read_text(encoding="utf-8"))
        assert report["assessor_transport"] == "bedrock-converse"
        assert report["assessor_model"] == PIN
        assert report["assessor_version"] == VERSION
        assert report["scope"] == "complete"
        assert report["criterion_scoring"]
        assert client.requests, "the pass never reached the Converse client"
        assert {r["modelId"] for r in client.requests} == {PIN}
        assert all("toolConfig" not in r for r in client.requests)
        assert all(r["inferenceConfig"]["temperature"] == 0.0 for r in client.requests)


# --------------------------------------------------------------------------- #
# The freeze (ticket AN1b)
# --------------------------------------------------------------------------- #


def _converse_pass(world: Path) -> tuple[Path, Any]:
    """A full synthetic blind pass over the fake Converse client: the report
    path and the profile bundle it was assessed under."""
    bundle = load_profile_bundle(_graph_profile(world), repo_root=world)
    out = world / "reports"
    argv = [
        "assess", "--document", "CAND-1", "--graph-root", str(world), "--out-dir", str(out),
        "--repo-root", str(world), "--profile", str(bundle.profile.source_path),
        "--transport", cmd.TRANSPORT_BEDROCK_CONVERSE, "--grounding-scope", gs.SCOPE_CONTENT_FOCUSED,
        "--assessor-model", PIN, "--assessor-version", VERSION, "--no-checkpoint",
    ]
    assert cmd.main(preflighted(argv, clock=lambda: FROZEN), clock=lambda: FROZEN) == 0
    (path,) = [p for p in out.iterdir() if p.is_file()]
    return path, bundle


def _freeze(world: Path, bundle, report: Path, baseline: Path) -> int:
    (candidate,) = (world / "reports" / "candidates").iterdir()
    return cmd.main(
        [
            "freeze", "--report", str(report), "--candidate", str(candidate),
            "--baseline-dir", str(baseline), "--repo-root", str(world),
            "--profile", str(bundle.profile.source_path),
        ],
        clock=lambda: FROZEN,
    )


def _failed(report: dict, bundle, repo_root: Path) -> list[tuple[str, str]]:
    import harness.blind_baseline as bb

    return list(bb.run_baseline_checks(report, bundle, repo_root=repo_root).failures)


class TestTheConverseFreeze:
    def test_the_report_carries_the_measured_invocation_record(self, converse_env, client, world):
        path, _bundle = _converse_pass(world)
        record = json.loads(path.read_text(encoding="utf-8"))["assessor_invocation"]
        assert record["tool_config_sent"] is False
        assert record["child_process"] is False
        assert record["requests"] == len(client.requests) > 0
        assert record["inference_config"] == client.requests[0]["inferenceConfig"]
        assert record["inference_config"]["temperature"] == 0.0

    def test_a_synthetic_converse_pass_freezes_under_the_v04_checks(self, converse_env, client, world):
        import harness.blind_baseline as bb

        path, bundle = _converse_pass(world)
        baseline = world / "baseline"
        assert _freeze(world, bundle, path, baseline) == 0
        record = bb.load_frozen_baseline(baseline).record
        assert record["bindings"]["assessor_transport"] == cj.TRANSPORT_TAG
        assert "invocation_evidence" in record["checks_passed"]
        assert record["checks_not_applicable"] == []
        assert set(record["checks_passed"]) == set(bb.BASELINE_CHECKS)

    def test_the_freeze_record_carries_the_isolation_evidence(self, converse_env, client, world):
        import harness.blind_baseline as bb

        path, bundle = _converse_pass(world)
        baseline = world / "baseline"
        assert _freeze(world, bundle, path, baseline) == 0
        invocation = bb.load_frozen_baseline(baseline).record["bindings"]["assessor_invocation"]
        assert invocation["tool_config_sent"] is False
        assert invocation["child_process"] is False

    def test_the_freeze_table_has_a_converse_entry(self):
        import harness.blind_baseline as bb

        entry = bb.TRANSPORT_ISOLATION_EVIDENCE[cj.TRANSPORT_TAG]
        assert dict(entry) == {"tool_config_sent": False, "child_process": False}

    def test_a_report_whose_request_carried_tools_is_refused(self, converse_env, client, world):
        path, bundle = _converse_pass(world)
        report = json.loads(path.read_text(encoding="utf-8"))
        report["assessor_invocation"]["tool_config_sent"] = True
        ((name, reason),) = _failed(report, bundle, world)
        assert name == "invocation_evidence"
        assert "tool_config_sent" in reason

    def test_a_report_without_the_invocation_record_is_refused(self, converse_env, client, world):
        path, bundle = _converse_pass(world)
        report = json.loads(path.read_text(encoding="utf-8"))
        report["assessor_invocation"] = {}
        ((name, reason),) = _failed(report, bundle, world)
        assert name == "invocation_evidence"
        assert cj.TRANSPORT_TAG in reason

    def test_a_report_claiming_a_transport_with_no_entry_is_refused(self, converse_env, client, world):
        """The mantle preset is not a route the private host has, and the
        freeze has no isolation entry for it."""
        path, bundle = _converse_pass(world)
        report = json.loads(path.read_text(encoding="utf-8"))
        report.update(assessor_transport="bedrock", assessor_version="bedrock-eu-west-1@2026-10-14")
        failures = _failed(report, bundle, world)
        assert ("invocation_evidence" in {name for name, _ in failures})
        assert any("not one this freeze knows" in reason for _, reason in failures)


class TestTheInvocationRecordIsMeasured:
    def test_a_backend_configured_with_tools_reports_them_sent(self, converse_env, client, tmp_path):
        """The record is read off the requests the backend built, not
        declared: a Converse backend given a tool list sends a toolConfig,
        and the record says so."""
        judge, wrapper = cj.build_converse_judge(
            JudgeConfig(model=PIN, version=VERSION), prov_path=tmp_path / "prov.jsonl", log=lambda _m: None
        )
        wrapper._inner._tools = [{"type": "function", "function": {"name": "read_file", "parameters": {}}}]
        judge.raw_invoke("s", "u")
        assert "toolConfig" in client.requests[0]
        assert wrapper.invocation_record()["tool_config_sent"] is True

    def test_no_request_means_no_inference_config(self, converse_env, client, tmp_path):
        _judge, wrapper = cj.build_converse_judge(
            JudgeConfig(model=PIN, version=VERSION), prov_path=tmp_path / "prov.jsonl", log=lambda _m: None
        )
        record = wrapper.invocation_record()
        assert record["requests"] == 0
        assert record["inference_config"] is None
        assert record["tool_config_sent"] is False

    def test_with_no_request_the_builder_is_still_measured(self, converse_env, client, tmp_path):
        """A run served wholly from a checkpoint sends nothing. The record is
        then measured from a probe the same builder makes, never from silence."""
        _judge, wrapper = cj.build_converse_judge(
            JudgeConfig(model=PIN, version=VERSION), prov_path=tmp_path / "prov.jsonl", log=lambda _m: None
        )
        wrapper._inner._tools = [{"type": "function", "function": {"name": "read_file", "parameters": {}}}]
        assert wrapper.invocation_record()["tool_config_sent"] is True
        assert client.requests == []

    def test_an_unmade_claim_does_not_freeze(self, converse_env, client, world):
        path, bundle = _converse_pass(world)
        report = json.loads(path.read_text(encoding="utf-8"))
        report["assessor_invocation"]["tool_config_sent"] = None
        ((name, reason),) = _failed(report, bundle, world)
        assert name == "invocation_evidence"
        assert "tool_config_sent" in reason


# --------------------------------------------------------------------------- #
# The receipt for the pass (ticket AN1b)
# --------------------------------------------------------------------------- #


def _receipt_for(tmp_path: Path, world: Path, report: dict) -> tuple[Path, Any]:
    """A filled Converse receipt for the pass that wrote *report*.

    Every value is read off the pass: its preflight, its profile, and the
    request the fake client received. The receipt lies outside the world, as
    the private one lies outside the clone.
    """
    from harness import execution_receipt as er
    from harness.record_binding import file_sha256

    preflight_path = Path(report["preflight_report"])
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    profile = Path(_graph_profile(world))
    request = report["assessor_invocation"]["inference_config"]
    doc = json.loads(
        (Path(__file__).resolve().parents[2] / "harness" / "execution_receipt_template_bedrock_converse.json")
        .read_text(encoding="utf-8")
    )
    doc.pop("_what_this_is")
    doc.update(
        receipt_id="synthetic_converse_receipt", authored_on="2026-10-14",
        review_state="operator_reviewed", declared_status="Confirmed",
        purpose="the synthetic Converse pass", written_by="tests",
        private_clone_root=str(world), repository_revision="synthetic",
    )
    doc["processing_route"] = {
        "authority": "synthetic rule", "processing": "synthetic prompts",
        "export": "nothing", "verified_on": "2026-10-14", "verified_by": "tests",
    }
    doc["model_identity"]["pin"] = report["assessor_pin"]
    values = {"model": PIN, "temperature": str(request["temperature"]), "max_tokens": str(request["maxTokens"])}
    for setting in doc["effective_settings"]:
        setting["value"] = values[setting["name"]]
    doc["rendered_request"].update(
        model_id=PIN, temperature=request["temperature"], max_tokens=request["maxTokens"],
        region="eu-west-1",
    )
    doc["isolation_check"].update(
        evidence=["tests/harness/test_converse_judge.py::TestTheJudgeBuildsConverse"],
        verified_on="2026-10-14", verified_by="tests",
    )
    doc["checkpoint"]["path"] = str(world / ".harness" / "checkpoints" / "synthetic.jsonl")
    manifest = preflight["import_manifest"]
    doc["preflight"] = {
        "report_path": str(preflight_path), "report_sha256": file_sha256(preflight_path),
        "pack_set_hash": preflight["pack_set_hash"], "document_id": preflight["document_id"],
        "profile_id": preflight["profile_id"], "profile_path": str(profile),
        "profile_sha256": file_sha256(profile), "profile_version": preflight["profile_version"],
        "import_manifest_path": manifest["path"], "import_manifest_sha256": manifest["sha256"],
        "grounding_scope": preflight["grounding_scope"]["declared"],
    }
    path = tmp_path / "private" / "readiness_receipt.json"
    path.parent.mkdir()
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    intended = er.IntendedPair(
        candidate_document_id=preflight["document_id"], profile_id=preflight["profile_id"],
        profile_path=str(profile), profile_sha256=file_sha256(profile),
    )
    return path, intended


@pytest.fixture
def receipt_pass(converse_env, client, world, tmp_path):
    """The Converse pass with a pinned import manifest, its report and its receipt."""
    manifest = tmp_path / "import_manifest.json"
    manifest.write_text('{"synthetic": true}', encoding="utf-8")
    bundle = load_profile_bundle(_graph_profile(world), repo_root=world)
    out = world / "reports"
    argv = [
        "assess", "--document", "CAND-1", "--graph-root", str(world), "--out-dir", str(out),
        "--repo-root", str(world), "--profile", str(bundle.profile.source_path),
        "--transport", cmd.TRANSPORT_BEDROCK_CONVERSE, "--grounding-scope", gs.SCOPE_CONTENT_FOCUSED,
        "--assessor-model", PIN, "--assessor-version", VERSION, "--no-checkpoint",
        "--import-manifest", str(manifest),
    ]
    assert cmd.main(preflighted(argv, clock=lambda: FROZEN), clock=lambda: FROZEN) == 0
    (path,) = [p for p in out.iterdir() if p.is_file()]
    report = json.loads(path.read_text(encoding="utf-8"))
    receipt, intended = _receipt_for(tmp_path, world, report)
    return path, report, receipt, intended, bundle


class TestTheReceiptForTheConversePass:
    def test_the_receipt_validates_against_the_pass_and_its_report(self, receipt_pass):
        from harness import execution_receipt as er

        _path, report, receipt_path, intended, _bundle = receipt_pass
        receipt = er.load_receipt(receipt_path)
        result = er.check(receipt, intended, receipt_dir=receipt_path.parent, report=report)
        assert result.green, result.lines()

    def test_the_same_pass_also_freezes(self, receipt_pass, world):
        path, _report, _receipt, _intended, bundle = receipt_pass
        assert _freeze(world, bundle, path, world / "baseline") == 0

    @pytest.mark.parametrize(
        ("change", "value"),
        [("maxTokens", 8192), ("temperature", 0.7)],
    )
    def test_a_report_that_sent_another_request_is_refused(self, receipt_pass, change, value):
        from harness import execution_receipt as er

        _path, report, receipt_path, intended, _bundle = receipt_pass
        invocation = dict(report["assessor_invocation"])
        invocation["inference_config"] = dict(invocation["inference_config"], **{change: value})
        report = dict(report, assessor_invocation=invocation)
        result = er.check(er.load_receipt(receipt_path), intended, receipt_dir=receipt_path.parent, report=report)
        assert result.request_disagrees_with_the_report
        assert not result.green

    def test_a_report_of_another_model_is_refused(self, receipt_pass):
        from harness import execution_receipt as er

        _path, report, receipt_path, intended, _bundle = receipt_pass
        report = dict(report, assessor_model="another-model")
        result = er.check(er.load_receipt(receipt_path), intended, receipt_dir=receipt_path.parent, report=report)
        assert result.request_disagrees_with_the_report

    def test_a_report_whose_transport_differs_is_refused(self, receipt_pass):
        from harness import execution_receipt as er

        _path, report, receipt_path, intended, _bundle = receipt_pass
        report = dict(report, assessor_transport="claude-cli")
        result = er.check(er.load_receipt(receipt_path), intended, receipt_dir=receipt_path.parent, report=report)
        assert result.transport_disagrees_with_the_report
        assert not result.green


# --------------------------------------------------------------------------- #
# Judge independence on a shared provider (ticket AN1c)
# --------------------------------------------------------------------------- #

#: The drafter model, ``skill_runtime.SKILL_MODEL``, in the forms Bedrock
#: names it: bare, foundation-model id, inference profiles, a dated snapshot,
#: a profile ARN and mixed case.
DRAFTER_ON_BEDROCK = [
    "claude-opus-4-8",
    "anthropic.claude-opus-4-8-v1:0",
    "eu.anthropic.claude-opus-4-8-v1:0",
    "us.anthropic.claude-opus-4-8",
    "global.anthropic.claude-opus-4-8",
    "apac.anthropic.claude-opus-4-8-20260801-v1:0",
    "arn:aws:bedrock:eu-west-1:123456789012:inference-profile/eu.anthropic.claude-opus-4-8-v1:0",
    "EU.Anthropic.Claude-Opus-4-8-V1:0",
    "anthropic.claude-opus-4-8-v1:0:200k",
    "anthropic.claude-opus-4-8:0",
    "eu.anthropic.claude-opus-4-8-v1:0:1m",
    "anthropic/claude-opus-4-8",
    "openrouter/anthropic/claude-opus-4-8",
    "claude-opus-4-8@20260801",
    "claude-opus-4-8[1m]",
    "claude-opus-4-8-latest",
]

#: Other Claude models on the same provider. The last two are near misses of
#: the drafter's id that name a different model.
OTHER_CLAUDE_ON_BEDROCK = [
    PIN,
    "eu.anthropic.claude-haiku-4-5-20251001-v1:0",
    "anthropic.claude-opus-4-1-v1:0",
    "eu.anthropic.claude-opus-4",
    "claude-opus-4-80",
    "claude-opus-4.8",
]


class TestJudgeIndependenceOnASharedProvider:
    @pytest.mark.parametrize("model", DRAFTER_ON_BEDROCK)
    def test_the_drafter_model_in_any_bedrock_form_is_refused(self, model):
        with pytest.raises(hj.JudgeIndependenceError, match="independence"):
            JudgeConfig(model=model, version=VERSION)

    @pytest.mark.parametrize("model", DRAFTER_ON_BEDROCK)
    def test_the_canonical_form_is_the_drafter_model(self, model):
        assert hj.canonical_model_id(model) == "claude-opus-4-8"

    def test_a_drafter_pin_in_the_environment_is_refused(self, converse_env, monkeypatch):
        """The route the command takes: the pin is resolved from the environment."""
        monkeypatch.setenv("HARNESS_JUDGE_MODEL", "eu.anthropic.claude-opus-4-8-v1:0")
        monkeypatch.setenv("HARNESS_JUDGE_VERSION", VERSION)
        with pytest.raises(hj.JudgeIndependenceError):
            hj.resolve_judge_config()

    def test_the_refusal_comes_before_any_request(self, converse_env, client):
        with pytest.raises(hj.JudgeIndependenceError):
            Judge(JudgeConfig(model="eu.anthropic.claude-opus-4-8-v1:0", version=VERSION))
        assert client.requests == []

    def test_a_drafter_named_in_bedrock_form_is_matched_too(self, monkeypatch):
        """Both sides are canonicalised: a runner pinned to a Bedrock id still
        refuses the bare model name."""
        monkeypatch.setattr(hj, "drafter_models", lambda: frozenset({"eu.anthropic.claude-opus-4-8-v1:0"}))
        with pytest.raises(hj.JudgeIndependenceError):
            JudgeConfig(model="claude-opus-4-8", version=VERSION)

    @pytest.mark.parametrize("model", OTHER_CLAUDE_ON_BEDROCK)
    def test_a_different_claude_model_passes_the_guard(self, model):
        assert JudgeConfig(model=model, version=VERSION).model == model

    def test_a_different_claude_model_runs_over_converse(self, converse_env, client, tmp_path):
        judge, _wrapper = cj.build_converse_judge(
            JudgeConfig(model=PIN, version=VERSION), prov_path=tmp_path / "prov.jsonl", log=lambda _m: None
        )
        assert judge.raw_invoke("s", "u")
        assert client.requests[0]["modelId"] == PIN

    @pytest.mark.parametrize(
        "model",
        ["llama-3.3-70b-versatile", "openai/gpt-oss-120b", "meta.llama3-1-70b-instruct-v1:0"],
    )
    def test_a_non_bedrock_or_non_claude_id_is_left_comparable(self, model):
        """Canonicalisation strips only Bedrock's wrapping, so other ids stay distinct."""
        assert hj.canonical_model_id(model) != "claude-opus-4-8"
        assert JudgeConfig(model=model, version=VERSION).model == model
