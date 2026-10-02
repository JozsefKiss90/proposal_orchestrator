"""
The subscription assessor — the judge backend over the local ``claude`` CLI.

Each test pins one property of the trade this backend makes.  Two of them are
load-bearing and would be silent if they broke:

* the assessor is handed **no tools**, which is the whole of its blindness;
* the **model** guard still refuses the drafter, because the transport guard no
  longer applies on the injected path.

No test here reaches a network or spawns a CLI; the transport is replaced.
"""
from __future__ import annotations

import pytest

from harness.commands import _subscription_judge as sj
from harness.judge import JudgeConfig, JudgeIndependenceError
from runner.claude_transport import (
    ClaudeCLIUnavailableError,
    ClaudeTransportError,
)

PIN = "claude-sonnet-5"
VERSION = "claude-cli-subscription@2026-10-02"


@pytest.fixture
def calls(monkeypatch):
    """Capture every transport invocation instead of spawning the CLI."""
    seen: list[dict] = []

    def fake(**kwargs):
        seen.append(kwargs)
        return '{"passed": true, "rationale": "ok"}'

    monkeypatch.setattr(sj, "invoke_claude_text", fake)
    return seen


def _backend(**kwargs) -> sj.ClaudeCLIJudgeBackend:
    kwargs.setdefault("model", PIN)
    kwargs.setdefault("max_tokens", 2048)
    kwargs.setdefault("log", lambda _msg: None)
    return sj.ClaudeCLIJudgeBackend(**kwargs)


_MESSAGES = [
    {"role": "system", "content": "grade this"},
    {"role": "user", "content": "the evidence pack"},
]


# --------------------------------------------------------------------------- #
# Blindness — the property the whole lane rests on
# --------------------------------------------------------------------------- #


class TestTheAssessorIsBlind:
    def test_the_transport_is_given_no_tools(self, calls):
        """With ``Read`` or ``Glob`` the assessor could open the drafting
        context on disk, and would stop being a blind assessor without
        announcing it."""
        _backend()(_MESSAGES)
        assert calls[0]["tools"] is None

    def test_the_prompts_are_the_only_thing_that_reaches_it(self, calls):
        _backend()(_MESSAGES)
        assert calls[0]["system_prompt"] == "grade this"
        assert calls[0]["user_prompt"] == "the evidence pack"

    def test_several_messages_of_a_role_are_joined_in_order(self, calls):
        _backend()(
            [
                {"role": "system", "content": "first"},
                {"role": "system", "content": "second"},
                {"role": "user", "content": "pack"},
            ]
        )
        assert calls[0]["system_prompt"] == "first\n\nsecond"

    def test_an_empty_user_prompt_is_refused(self, calls):
        with pytest.raises(sj.SubscriptionJudgeError):
            _backend()([{"role": "system", "content": "grade this"}])
        assert calls == []


# --------------------------------------------------------------------------- #
# The backend protocol
# --------------------------------------------------------------------------- #


class TestTheBackendProtocol:
    def test_it_returns_the_shape_the_judge_reads(self, calls):
        result = _backend()(_MESSAGES)
        assert result["content"] == '{"passed": true, "rationale": "ok"}'
        assert result["tool_calls"] is None

    def test_the_pinned_model_is_what_the_transport_is_asked_for(self, calls):
        _backend(model="claude-sonnet-5")(_MESSAGES)
        assert calls[0]["model"] == "claude-sonnet-5"

    def test_it_counts_its_calls(self, calls):
        backend = _backend()
        backend(_MESSAGES)
        backend(_MESSAGES)
        assert backend.calls == 2


# --------------------------------------------------------------------------- #
# Retries
# --------------------------------------------------------------------------- #


class TestRetries:
    def test_a_transport_failure_is_retried(self, monkeypatch):
        attempts: list[int] = []

        def flaky(**kwargs):
            attempts.append(1)
            if len(attempts) < 2:
                raise ClaudeTransportError("the CLI exited non-zero")
            return "{}"

        monkeypatch.setattr(sj, "invoke_claude_text", flaky)
        monkeypatch.setattr(sj.time, "sleep", lambda _s: None)
        backend = _backend()
        assert backend(_MESSAGES)["content"] == "{}"
        assert len(attempts) == 2
        assert backend.retries == 1

    def test_it_gives_up_after_the_retry_budget(self, monkeypatch):
        def always(**kwargs):
            raise ClaudeTransportError("still down")

        monkeypatch.setattr(sj, "invoke_claude_text", always)
        monkeypatch.setattr(sj.time, "sleep", lambda _s: None)
        with pytest.raises(ClaudeTransportError):
            _backend(max_retries=1)(_MESSAGES)

    def test_a_missing_cli_is_not_retried(self, monkeypatch):
        """Waiting five seconds does not put the executable back on PATH."""
        attempts: list[int] = []

        def absent(**kwargs):
            attempts.append(1)
            raise ClaudeCLIUnavailableError("claude is not on PATH")

        monkeypatch.setattr(sj, "invoke_claude_text", absent)
        monkeypatch.setattr(sj.time, "sleep", lambda _s: None)
        with pytest.raises(ClaudeCLIUnavailableError):
            _backend()(_MESSAGES)
        assert len(attempts) == 1


# --------------------------------------------------------------------------- #
# Independence — what the injected path keeps and what it drops
# --------------------------------------------------------------------------- #


class TestWhatIndependenceSurvives:
    def test_the_drafter_model_is_still_refused(self):
        """The transport guard does not apply on the injected path, so this is
        the only guard left between the assessor and the model that drafted the
        sections under assessment."""
        from runner.skill_runtime import SKILL_MODEL

        with pytest.raises(JudgeIndependenceError):
            JudgeConfig(model=SKILL_MODEL, version=VERSION)

    def test_a_non_claude_pin_is_refused_by_the_builder(self, tmp_path):
        """The Groq pin left in ``.env.harness`` must not reach the CLI, where
        it would fail once per cell with an unknown-model error."""
        cfg = JudgeConfig(model="llama-3.3-70b-versatile", version=VERSION)
        with pytest.raises(sj.SubscriptionJudgeError, match="cannot resolve"):
            sj.build_subscription_judge(cfg, prov_path=tmp_path / "prov.jsonl")

    def test_the_builder_wires_the_pin_and_a_provenance_log(self, tmp_path):
        cfg = JudgeConfig(model=PIN, version=VERSION)
        judge, backend = sj.build_subscription_judge(
            cfg, prov_path=tmp_path / "prov.jsonl", log=lambda _m: None
        )
        assert judge.config.model == PIN
        assert judge.provenance_log is not None
        assert isinstance(backend, sj.ClaudeCLIJudgeBackend)
        assert backend.model == PIN

    def test_the_pin_records_the_transport(self, tmp_path):
        """The report carries ``model@version`` and nothing else about the
        assessor, so the version tag is where the transport is declared."""
        from harness.blind_assessment import assessor_pin

        cfg = JudgeConfig(model=PIN, version=VERSION)
        judge, _ = sj.build_subscription_judge(
            cfg, prov_path=tmp_path / "prov.jsonl", log=lambda _m: None
        )
        assert assessor_pin(judge) == f"{PIN}@{VERSION}"
        assert "cli" in assessor_pin(judge)


class TestModelPinGuard:
    @pytest.mark.parametrize("name", ["claude-sonnet-5", "claude-opus-4-8", "sonnet", " Opus "])
    def test_accepts_what_the_cli_resolves(self, name):
        assert sj.is_claude_model_pin(name)

    @pytest.mark.parametrize("name", ["llama-3.3-70b-versatile", "gpt-4o", ""])
    def test_rejects_what_it_does_not(self, name):
        assert not sj.is_claude_model_pin(name)


# --------------------------------------------------------------------------- #
# The command wiring
# --------------------------------------------------------------------------- #


class TestCommandWiring:
    def test_the_default_transport_is_still_the_independent_one(self):
        from harness.commands.blind_assessment import TRANSPORT_OPENAI, _parser

        args = _parser().parse_args(["assess", "--candidate", "x"])
        assert args.transport == TRANSPORT_OPENAI

    def test_the_pin_flags_beat_the_harness_env_file(self, monkeypatch, tmp_path):
        """``load_harness_env`` loads with ``override=True``, so an exported
        variable cannot win against the file.  The flags are the only way to run
        one assessment on a different pin without editing the file that holds
        the other transport's key."""
        import harness.judge as hj
        from harness.commands import _common, blind_assessment as cmd

        monkeypatch.setattr(
            _common, "load_harness_env",
            lambda: monkeypatch.setenv("HARNESS_JUDGE_MODEL", "llama-3.3-70b-versatile"),
        )
        monkeypatch.setenv("HARNESS_JUDGE_VERSION", "groq-pin@2026-08-03")
        args = cmd._parser().parse_args(
            [
                "assess", "--candidate", "x",
                "--transport", cmd.TRANSPORT_CLAUDE_CLI,
                "--assessor-model", PIN,
                "--assessor-version", VERSION,
            ]
        )
        judge = cmd._live_judge(args, tmp_path)
        assert judge.config.model == PIN
        assert judge.config.version == VERSION
        assert hj.os.environ["HARNESS_JUDGE_MODEL"] == "llama-3.3-70b-versatile"

    def test_an_overridden_pin_still_cannot_be_the_drafter(self, monkeypatch, tmp_path):
        """The flag is a pin override, not a guard bypass."""
        from runner.skill_runtime import SKILL_MODEL
        from harness.commands import _common, blind_assessment as cmd

        monkeypatch.setattr(_common, "load_harness_env", lambda: None)
        args = cmd._parser().parse_args(
            [
                "assess", "--candidate", "x",
                "--transport", cmd.TRANSPORT_CLAUDE_CLI,
                "--assessor-model", SKILL_MODEL,
                "--assessor-version", VERSION,
            ]
        )
        with pytest.raises(JudgeIndependenceError):
            cmd._live_judge(args, tmp_path)

    def test_the_uncapped_budget_is_chosen_for_this_transport(self):
        from harness.evidence_pack import (
            DEFAULT_PACK_TOKEN_BUDGET,
            UNCAPPED_DEFAULT_PACK_TOKEN_BUDGET,
        )
        from harness.commands import blind_assessment as cmd

        assert UNCAPPED_DEFAULT_PACK_TOKEN_BUDGET > DEFAULT_PACK_TOKEN_BUDGET
        # Resolved from the transport after parsing, so the flag default is None.
        args = cmd._parser().parse_args(
            ["assess", "--candidate", "x", "--transport", cmd.TRANSPORT_CLAUDE_CLI]
        )
        assert args.budget is None

    def test_the_subscription_transport_builds_the_subscription_judge(
        self, monkeypatch, tmp_path
    ):
        import harness.judge as hj
        from harness.commands import _common, blind_assessment as ba

        monkeypatch.setattr(_common, "load_harness_env", lambda: None)
        monkeypatch.setattr(
            hj, "resolve_judge_config", lambda: JudgeConfig(model=PIN, version=VERSION)
        )
        args = ba._parser().parse_args(
            ["assess", "--candidate", "x", "--transport", ba.TRANSPORT_CLAUDE_CLI]
        )
        judge = ba._live_judge(args, tmp_path)
        assert isinstance(judge._backend, sj.ClaudeCLIJudgeBackend)
        assert judge.config.model == PIN
