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
