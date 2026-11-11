"""
One place builds a judge and states its independence (overhaul ticket 03).

Two groups, written in this order:

* **Characterisation**, pinned through the blind-assessment command and the
  grounding freeze before the builders moved: what each route refuses, what it
  wraps the backend in, and the ``assessor_transport`` strings a blind report
  records.  These pass before and after the factory exists.
* **The factory**: a route is named, the environment must agree, the drafter
  model is refused on every route, the judge has no lazy default, and no
  harness module but the factory constructs a judge.

No test here reaches a network or spawns a CLI.
"""
from __future__ import annotations

import ast
import dataclasses
import tempfile
import warnings
from pathlib import Path
from typing import Any

import pytest

import harness.commands.blind_assessment as cmd
import harness.grounding_scope as gs
import runner.transport.bedrock_converse as bc
from harness.commands import _subscription_judge as sj
from harness.judge import (
    Judge,
    JudgeConfig,
    JudgeConfigError,
    JudgeError,
    JudgeIndependenceError,
)
from runner.claude_transport import NO_TOOLS
from runner.paths import find_repo_root

REPO = find_repo_root()

CLAUDE_PIN = "claude-sonnet-5"
CLAUDE_VERSION = "claude-cli-subscription@2026-10-02"
CONVERSE_PIN = "eu.anthropic.claude-sonnet-4-6"
CONVERSE_VERSION = "bedrock-converse-eu-west-1@2026-10-14"
OPENAI_PIN = "llama-3.3-70b-versatile"
OPENAI_VERSION = "groq-llama-3.3-70b@2026-08-03"

#: The pin each route admits, so a test of one property holds the others fixed.
PINS = {
    "openai-compatible": (OPENAI_PIN, OPENAI_VERSION),
    "bedrock-converse": (CONVERSE_PIN, CONVERSE_VERSION),
    "claude-cli": (CLAUDE_PIN, CLAUDE_VERSION),
}

#: The backend name each route's environment resolves to.
ENVIRONMENTS = {
    "openai-compatible": "openai_compatible",
    "bedrock-converse": "bedrock_converse",
    "claude-cli": "claude_cli",
}

_REPLY = '{"passed": true, "score": 0.9, "rationale": "ok"}'


# --------------------------------------------------------------------------- #
# Environments
# --------------------------------------------------------------------------- #


def _set_environment(monkeypatch, backend: str) -> None:
    """Point the transport environment at *backend*, and keep ``.env.harness`` out."""
    for name in ("ORCHESTRATOR_TRANSPORT_PRESET", "ORCHESTRATOR_PRODUCTION_MODE"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("ORCHESTRATOR_TRANSPORT_BACKEND", backend)
    monkeypatch.setenv("ORCHESTRATOR_TRANSPORT_MODEL", "env-default-model")
    monkeypatch.setenv("ORCHESTRATOR_TRANSPORT_ENDPOINT", "https://example.test/v1")
    monkeypatch.setenv("ORCHESTRATOR_TRANSPORT_API_KEY", "test-key")
    monkeypatch.setenv("AWS_REGION", "eu-west-1")
    monkeypatch.setattr("harness.commands._common.load_harness_env", lambda: None)


class _FakeConverseClient:
    """``boto3.client('bedrock-runtime')``: keeps requests, throttles the first *throttle*."""

    def __init__(self, throttle: int = 0) -> None:
        self.requests: list[dict[str, Any]] = []
        self.throttle = throttle

    def converse(self, **kwargs: Any) -> dict[str, Any]:
        self.requests.append(kwargs)
        if len(self.requests) <= self.throttle:
            from botocore.exceptions import ClientError

            raise ClientError({"Error": {"Code": "ThrottlingException", "Message": "slow"}}, "Converse")
        return {
            "output": {"message": {"role": "assistant", "content": [{"text": _REPLY}]}},
            "usage": {"inputTokens": 10, "outputTokens": 5, "totalTokens": 15},
        }


@pytest.fixture
def converse_client(monkeypatch) -> _FakeConverseClient:
    fake = _FakeConverseClient()
    monkeypatch.setattr(bc.boto3, "client", lambda *_a, **_k: fake)
    return fake


@pytest.fixture
def cli_calls(monkeypatch) -> list[dict]:
    seen: list[dict] = []

    def fake(**kwargs):
        seen.append(kwargs)
        return _REPLY

    monkeypatch.setattr(sj, "invoke_claude_text", fake)
    return seen


@pytest.fixture
def sleeps(monkeypatch) -> list[float]:
    """Every ``time.sleep`` the wrappers ask for, recorded instead of slept."""
    import time

    seen: list[float] = []
    monkeypatch.setattr(time, "sleep", lambda s: seen.append(s))
    return seen


def _assess_args(transport: str | None, *extra: str):
    argv = ["assess", "--candidate", "x", "--preflight", "x", "--grounding-scope", gs.SCOPE_CONTENT_FOCUSED]
    if transport is not None:
        argv += ["--transport", transport]
        model, version = PINS[transport]
        argv += ["--assessor-model", model, "--assessor-version", version]
    return cmd._parser().parse_args(argv + list(extra))


# --------------------------------------------------------------------------- #
# Characterisation: claude-cli
# --------------------------------------------------------------------------- #


class TestTheClaudeCliRouteIsUnchanged:
    def test_a_non_claude_pin_is_refused(self, monkeypatch, tmp_path):
        _set_environment(monkeypatch, "claude_cli")
        args = _assess_args("claude-cli", "--assessor-model", OPENAI_PIN)
        with pytest.raises(JudgeError, match="cannot resolve"):
            cmd._live_judge(args, tmp_path)

    def test_a_version_without_the_transport_tag_is_refused(self, monkeypatch, tmp_path):
        _set_environment(monkeypatch, "claude_cli")
        args = _assess_args("claude-cli", "--assessor-version", "subscription@2026-10-02")
        with pytest.raises(JudgeError, match="claude-cli"):
            cmd._live_judge(args, tmp_path)

    def test_a_working_directory_inside_the_repository_is_refused(self, monkeypatch, tmp_path):
        _set_environment(monkeypatch, "claude_cli")
        repo = tmp_path / "repo"
        inside = repo / "tmp"
        inside.mkdir(parents=True)
        monkeypatch.setattr(tempfile, "tempdir", str(inside))
        with pytest.raises(JudgeError, match="inside the repository"):
            cmd._live_judge(_assess_args("claude-cli"), repo)

    def test_the_empty_tool_list_is_passed_outside_the_repository(self, monkeypatch, tmp_path, cli_calls):
        _set_environment(monkeypatch, "claude_cli")
        repo = tmp_path / "repo"
        repo.mkdir()
        judge = cmd._live_judge(_assess_args("claude-cli", "--max-retries", "3"), repo)
        judge._send("s", "u")
        (call,) = cli_calls
        assert call["tools"] is NO_TOOLS
        assert not Path(call["cwd"]).resolve().is_relative_to(repo.resolve())
        assert judge._backend.max_retries == 3
        assert judge.provenance_log is not None


# --------------------------------------------------------------------------- #
# Characterisation: bedrock-converse
# --------------------------------------------------------------------------- #


class TestTheConverseRouteIsUnchanged:
    def test_a_version_without_the_transport_tag_is_refused(self, monkeypatch, tmp_path, converse_client):
        _set_environment(monkeypatch, "bedrock_converse")
        args = _assess_args("bedrock-converse", "--assessor-version", "eu-west-1@2026-10-14")
        with pytest.raises(JudgeError, match="bedrock-converse"):
            cmd._live_judge(args, tmp_path)
        assert converse_client.requests == []

    def test_retry_applies_without_pacing(self, monkeypatch, tmp_path, converse_client, sleeps):
        _set_environment(monkeypatch, "bedrock_converse")
        converse_client.throttle = 1
        judge = cmd._live_judge(_assess_args("bedrock-converse", "--max-retries", "3"), tmp_path)
        wrapper = judge._backend
        assert wrapper._tpm == float("inf")
        assert wrapper._min_interval == 0.0
        assert wrapper._max_retries == 3
        assert judge._send("s", "u") == _REPLY
        assert len(converse_client.requests) == 2
        assert wrapper.retries == 1
        # One backoff for the throttled call; no pacing wait before either call.
        assert sleeps == [8.0]
        assert converse_client.requests[0]["modelId"] == CONVERSE_PIN


# --------------------------------------------------------------------------- #
# Characterisation: openai-compatible
# --------------------------------------------------------------------------- #


def _assert_paced(wrapper, *, tpm: int, rpm: int, max_retries: int) -> None:
    assert wrapper._tpm == float(tpm)
    assert wrapper._min_interval == pytest.approx(60.0 / rpm)
    assert wrapper._max_retries == max_retries
    assert wrapper._base == 8.0
    assert wrapper._max == 90.0


class TestTheOpenAICompatibleRouteIsUnchanged:
    def test_the_blind_assessment_default_paces_and_retries(self, monkeypatch, tmp_path):
        _set_environment(monkeypatch, "openai_compatible")
        args = _assess_args("openai-compatible", "--tpm", "4000", "--rpm", "20", "--max-retries", "4")
        judge = cmd._live_judge(args, tmp_path)
        _assert_paced(judge._backend, tpm=4000, rpm=20, max_retries=4)
        assert judge._backend._inner.model == OPENAI_PIN
        assert judge.provenance_log is not None

    def test_the_grounding_freeze_paces_with_its_defaults(self, monkeypatch, tmp_path):
        import harness.commands.freeze_grounding_baselines as fgb

        _set_environment(monkeypatch, "openai_compatible")
        for name in ("HARNESS_TPM_BUDGET", "HARNESS_RPM_BUDGET", "HARNESS_MAX_RETRIES"):
            monkeypatch.delenv(name, raising=False)
        monkeypatch.setenv("HARNESS_JUDGE_MODEL", OPENAI_PIN)
        monkeypatch.setenv("HARNESS_JUDGE_VERSION", OPENAI_VERSION)
        monkeypatch.setattr(fgb, "load_harness_env", lambda: None)
        built: list[Judge] = []
        original = Judge.__init__

        def spy(self, *a, **k):
            original(self, *a, **k)
            built.append(self)

        monkeypatch.setattr(Judge, "__init__", spy)
        sections = tmp_path / "sections"
        sections.mkdir()
        out = tmp_path / "out"
        rc = fgb.main(["--repo-root", str(tmp_path), "--sections", str(sections), "--out", str(out)])
        assert rc == 2  # no sections: the judge was built, nothing was frozen
        (judge,) = built
        _assert_paced(judge._backend, tpm=5500, rpm=28, max_retries=6)
        assert judge.provenance_log.path == out / "provenance_grounding_freeze.jsonl"


# --------------------------------------------------------------------------- #
# Characterisation: the strings a blind report records
# --------------------------------------------------------------------------- #


class TestTheReportedTransportStringsAreUnchanged:
    @pytest.mark.parametrize(
        "flag, recorded",
        [
            (None, "openai-compatible"),
            ("openai-compatible", "openai-compatible"),
            ("claude-cli", "claude-cli"),
            ("bedrock-converse", "bedrock-converse"),
        ],
    )
    def test_the_command_records_the_same_string(self, monkeypatch, flag, recorded):
        monkeypatch.delenv("HARNESS_ASSESSOR_TRANSPORT", raising=False)
        assert cmd._transport(_assess_args(flag)) == recorded

    def test_the_constants_are_the_recorded_strings(self):
        assert (cmd.TRANSPORT_OPENAI, cmd.TRANSPORT_CLAUDE_CLI, cmd.TRANSPORT_BEDROCK_CONVERSE) == (
            "openai-compatible",
            "claude-cli",
            "bedrock-converse",
        )


# --------------------------------------------------------------------------- #
# The factory
# --------------------------------------------------------------------------- #


def _forged_config(model: str, version: str) -> JudgeConfig:
    """A config that skipped its own guard, to prove the factory re-applies it."""
    cfg = object.__new__(JudgeConfig)
    for name, value in (("model", model), ("version", version), ("temperature", 0.0), ("max_tokens", 2048)):
        object.__setattr__(cfg, name, value)
    return cfg


def _build(route: str, cfg: JudgeConfig, tmp_path: Path):
    from harness.judge_factory import build_judge

    kwargs: dict[str, Any] = {"prov_path": tmp_path / "prov.jsonl", "log": lambda _m: None}
    if route == "claude-cli":
        kwargs["repo_root"] = tmp_path / "repo"
        kwargs["repo_root"].mkdir(exist_ok=True)
    return build_judge(route, cfg, **kwargs)


class TestTheEnvironmentMustAgree:
    def test_a_converse_environment_refuses_the_openai_compatible_route(
        self, monkeypatch, tmp_path, converse_client
    ):
        """The misroute: today an OpenAI-compatible backend is built here."""
        _set_environment(monkeypatch, "bedrock_converse")
        with pytest.raises(JudgeError) as info:
            _build("openai-compatible", JudgeConfig(model=OPENAI_PIN, version=OPENAI_VERSION), tmp_path)
        assert "openai-compatible" in str(info.value)
        assert "bedrock_converse" in str(info.value)
        assert converse_client.requests == []

    @pytest.mark.parametrize(
        "route, environment",
        [(r, e) for r in ENVIRONMENTS for e in ENVIRONMENTS.values() if ENVIRONMENTS[r] != e],
    )
    def test_every_mismatched_pair_is_refused_naming_both(
        self, monkeypatch, tmp_path, converse_client, cli_calls, route, environment
    ):
        _set_environment(monkeypatch, environment)
        model, version = PINS[route]
        with pytest.raises(JudgeError) as info:
            _build(route, JudgeConfig(model=model, version=version), tmp_path)
        assert route in str(info.value)
        assert environment in str(info.value)
        assert converse_client.requests == [] and cli_calls == []

    @pytest.mark.parametrize("route", list(ENVIRONMENTS))
    def test_an_agreeing_environment_builds_the_route(
        self, monkeypatch, tmp_path, converse_client, cli_calls, route
    ):
        _set_environment(monkeypatch, ENVIRONMENTS[route])
        model, version = PINS[route]
        judge, wrapper = _build(route, JudgeConfig(model=model, version=version), tmp_path)
        assert judge._backend is wrapper
        assert judge.config.model == model
        assert judge.provenance_log is not None

    def test_an_unknown_route_is_refused(self, tmp_path):
        with pytest.raises(JudgeError, match="no-such-route"):
            _build("no-such-route", JudgeConfig(model=OPENAI_PIN, version=OPENAI_VERSION), tmp_path)


class TestTheDrafterIsRefusedOnEveryRoute:
    @pytest.mark.parametrize("route", list(ENVIRONMENTS))
    def test_a_drafter_model_is_refused(self, monkeypatch, tmp_path, converse_client, cli_calls, route):
        from runner.skill_runtime import SKILL_MODEL

        _set_environment(monkeypatch, ENVIRONMENTS[route])
        _model, version = PINS[route]
        with pytest.raises(JudgeIndependenceError):
            _build(route, _forged_config(SKILL_MODEL, version), tmp_path)
        assert converse_client.requests == [] and cli_calls == []


class TestTheJudgeHasNoLazyDefault:
    def test_a_judge_without_a_backend_raises(self):
        cfg = JudgeConfig(model=OPENAI_PIN, version=OPENAI_VERSION)
        with pytest.raises((TypeError, JudgeConfigError)):
            Judge(cfg)  # type: ignore[call-arg]
        with pytest.raises(JudgeConfigError, match="backend"):
            Judge(cfg, backend=None)  # type: ignore[arg-type]


#: Calls that put a production backend behind a judge.  Only the factory makes them.
_CONSTRUCTORS = frozenset(
    {
        "Judge",
        "build_openai_backend",
        "build_converse_backend",
        "BedrockConverseBackend",
        "OpenAICompatBackend",
        "ClaudeCLIJudgeBackend",
        "PacedRetryingBackend",
        "ConverseRetryingBackend",
    }
)


def _called_names(source: str) -> set[str]:
    names: set[str] = set()
    with warnings.catch_warnings():  # a docstring's stray escape is not this test's concern
        warnings.simplefilter("ignore", SyntaxWarning)
        warnings.simplefilter("ignore", DeprecationWarning)
        tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                names.add(func.id)
            elif isinstance(func, ast.Attribute):
                names.add(func.attr)
    return names


class TestOnlyTheFactoryConstructsAJudge:
    def test_no_other_harness_module_constructs_a_judge_or_a_production_backend(self):
        offenders = []
        for path in sorted((REPO / "harness").rglob("*.py")):
            if path.name == "judge_factory.py":
                continue
            found = _called_names(path.read_text(encoding="utf-8")) & _CONSTRUCTORS
            if found:
                offenders.append(f"{path.relative_to(REPO).as_posix()}: {sorted(found)}")
        assert offenders == []

    def test_the_factory_is_where_the_construction_lives(self):
        source = (REPO / "harness" / "judge_factory.py").read_text(encoding="utf-8")
        assert {"Judge", "PacedRetryingBackend"} <= _called_names(source)


class TestThePolicyTableIsTheOneTheDocsRead:
    def test_every_route_has_one_row(self):
        from harness.judge_factory import INDEPENDENCE_POLICY

        assert set(INDEPENDENCE_POLICY) == set(ENVIRONMENTS)
        for route, row in INDEPENDENCE_POLICY.items():
            assert row.route == route
            assert dataclasses.is_dataclass(row)

    def test_the_rows_state_what_each_route_requires(self):
        from harness.judge_factory import INDEPENDENCE_POLICY as P

        assert P["openai-compatible"].paced and not P["bedrock-converse"].paced
        assert not P["claude-cli"].paced
        assert not P["openai-compatible"].version_tag_required
        assert P["bedrock-converse"].version_tag_required and P["claude-cli"].version_tag_required
        assert P["claude-cli"].claude_pin_required
        assert not P["openai-compatible"].claude_pin_required

    def test_harness_md_points_at_the_table(self):
        text = (REPO / "harness" / "HARNESS.md").read_text(encoding="utf-8")
        assert "judge_factory.INDEPENDENCE_POLICY" in text
