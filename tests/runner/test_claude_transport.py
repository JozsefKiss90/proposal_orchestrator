"""
Unit tests for runner/claude_transport.py — Claude CLI transport adapter.

Tests mock ``subprocess.Popen`` to verify the transport adapter's behavior
without requiring the ``claude`` CLI to be installed.  The transport uses
``Popen`` + ``communicate(timeout=...)`` (rather than ``subprocess.run``) so
that a timed-out call can kill the child's *entire* process tree — see
``test_claude_transport_treekill.py`` for the real-process tree-kill coverage.

Test groups:
  - Successful invocation — stdout returned
  - Non-zero exit code — ClaudeTransportError raised
  - Missing executable — ClaudeCLIUnavailableError raised
  - Timeout — ClaudeCLITimeoutError raised + process tree killed
  - Empty stdout — ClaudeTransportError raised
  - System prompt length fallback — long prompts embedded in user prompt
  - Command construction — correct flags and arguments passed
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from runner.claude_transport import (
    ClaudeCLIRateLimitError,
    ClaudeCLIResolution,
    ClaudeCLITimeoutError,
    ClaudeCLIUnavailableError,
    ClaudeTransportError,
    DEFAULT_TIMEOUT_SECONDS,
    NO_TOOLS,
    _CLI_MAX_OUTPUT_TOKENS_VAR,
    _CLI_PATH_ENV_VAR,
    _MAX_OUTPUT_TOKENS_DEFAULT,
    _MAX_OUTPUT_TOKENS_ENV_VAR,
    _MAX_SYSTEM_PROMPT_CLI_LENGTH,
    invoke_claude_text,
    resolve_claude_cli,
)


@pytest.fixture(autouse=True)
def _unpinned_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    """Neutralise a developer's own CLI pin for every test in this module.

    ``ORCHESTRATOR_CLAUDE_CLI_PATH`` is a machine-local operator setting.  If
    it leaks into the test environment, every command-construction assertion
    below would depend on that machine's install layout.  Tests that exercise
    the pin set it themselves (autouse fixtures run first).
    """
    monkeypatch.delenv(_CLI_PATH_ENV_VAR, raising=False)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

#: Patch target: the transport now spawns via Popen, not subprocess.run.
_POPEN_TARGET = "runner.claude_transport.subprocess.Popen"


def _mock_proc(stdout: str | None = "response", stderr: str = "", returncode: int = 0):
    """Create a mock Popen whose communicate() returns (stdout, stderr)."""
    proc = MagicMock(spec=subprocess.Popen)
    proc.communicate.return_value = (stdout, stderr)
    proc.returncode = returncode
    # poll() reports "exited" so any teardown path is a safe no-op.
    proc.poll.return_value = returncode
    proc.pid = 4242
    # The transport hands the stdin pipe to a writer thread (TR-2); spec'd
    # mocks do not expose instance-only attributes, so set it explicitly.
    proc.stdin = MagicMock()
    return proc


def _timeout_proc(
    timeout_exc: subprocess.TimeoutExpired,
    *,
    drain: tuple[str | None, str | None] = (None, None),
    poll: int | None = 1,
):
    """Mock Popen whose first communicate() times out, second call drains.

    ``poll`` defaults to a non-None value so the real ``_kill_process_tree``
    treats the (fake) process as already exited and never shells out to
    ``taskkill`` against an arbitrary PID during a unit test.
    """
    proc = MagicMock(spec=subprocess.Popen)
    proc.communicate.side_effect = [timeout_exc, drain]
    proc.returncode = None
    proc.poll.return_value = poll
    proc.pid = 4242
    proc.stdin = MagicMock()
    return proc


def _call_kwargs() -> dict:
    """Default kwargs for invoke_claude_text."""
    return {
        "system_prompt": "You are helpful.",
        "user_prompt": "Hello",
        "model": "claude-sonnet-4-6",
        "max_tokens": 4096,
    }


# ---------------------------------------------------------------------------
# Successful invocation
# ---------------------------------------------------------------------------


class TestSuccessPath:
    def test_returns_stdout_text(self) -> None:
        with patch(_POPEN_TARGET, return_value=_mock_proc("Hello world")) as mock_popen:
            result = invoke_claude_text(**_call_kwargs())
        assert result == "Hello world"
        mock_popen.assert_called_once()

    def test_passes_user_prompt_via_stdin(self) -> None:
        proc = _mock_proc("ok")
        # The transport detaches proc.stdin (sets it to None) after handing
        # the pipe to the TR-2 writer thread — capture the pipe first.
        pipe = proc.stdin
        with patch(_POPEN_TARGET, return_value=proc):
            invoke_claude_text(**_call_kwargs())
        # The user prompt is written to the stdin pipe by the TR-2 writer
        # thread (never via communicate(input=...), whose synchronous write
        # would defeat the deadline), and the pipe is closed afterwards.
        stdin_writes = "".join(c.args[0] for c in pipe.write.call_args_list)
        assert stdin_writes == "Hello"
        pipe.close.assert_called_once()
        assert "input" not in (proc.communicate.call_args.kwargs or {})

    def test_uses_text_mode_and_utf8(self) -> None:
        with patch(_POPEN_TARGET, return_value=_mock_proc("ok")) as mock_popen:
            invoke_claude_text(**_call_kwargs())
        kw = mock_popen.call_args.kwargs
        assert kw["text"] is True
        assert kw["encoding"] == "utf-8"

    def test_does_not_use_shell(self) -> None:
        with patch(_POPEN_TARGET, return_value=_mock_proc("ok")) as mock_popen:
            invoke_claude_text(**_call_kwargs())
        assert mock_popen.call_args.kwargs["shell"] is False

    def test_captures_stdout_and_stderr_via_pipes(self) -> None:
        with patch(_POPEN_TARGET, return_value=_mock_proc("ok")) as mock_popen:
            invoke_claude_text(**_call_kwargs())
        kw = mock_popen.call_args.kwargs
        assert kw["stdout"] == subprocess.PIPE
        assert kw["stderr"] == subprocess.PIPE
        assert kw["stdin"] == subprocess.PIPE


# ---------------------------------------------------------------------------
# Command construction
# ---------------------------------------------------------------------------


class TestCommandConstruction:
    def test_command_includes_print_mode(self) -> None:
        with patch(_POPEN_TARGET, return_value=_mock_proc("ok")) as mock_popen:
            invoke_claude_text(**_call_kwargs())
        cmd = mock_popen.call_args.args[0]
        assert "-p" in cmd

    def test_command_includes_model(self) -> None:
        with patch(_POPEN_TARGET, return_value=_mock_proc("ok")) as mock_popen:
            invoke_claude_text(**_call_kwargs())
        cmd = mock_popen.call_args.args[0]
        idx = cmd.index("--model")
        assert cmd[idx + 1] == "claude-sonnet-4-6"

    def test_max_tokens_not_passed_to_cli(self) -> None:
        """max_tokens is accepted for interface compatibility but the claude -p
        CLI does not support a --max-tokens flag.  Output bounding is achieved
        through prompt design (output minimization rules), not transport-level
        token caps.  Verify the flag is NOT added to the command."""
        with patch(_POPEN_TARGET, return_value=_mock_proc("ok")) as mock_popen:
            invoke_claude_text(**_call_kwargs())
        cmd = mock_popen.call_args.args[0]
        assert "--max-tokens" not in cmd

    def test_short_system_prompt_passed_via_flag(self) -> None:
        with patch(_POPEN_TARGET, return_value=_mock_proc("ok")) as mock_popen:
            invoke_claude_text(**_call_kwargs())
        cmd = mock_popen.call_args.args[0]
        idx = cmd.index("--system-prompt")
        assert cmd[idx + 1] == "You are helpful."

    def test_default_timeout_applied(self) -> None:
        proc = _mock_proc("ok")
        with patch(_POPEN_TARGET, return_value=proc):
            invoke_claude_text(**_call_kwargs())
        # The timeout is enforced by communicate(), not by Popen().
        assert proc.communicate.call_args.kwargs["timeout"] == DEFAULT_TIMEOUT_SECONDS

    def test_custom_timeout_applied(self) -> None:
        proc = _mock_proc("ok")
        with patch(_POPEN_TARGET, return_value=proc):
            invoke_claude_text(**_call_kwargs(), timeout_seconds=60)
        assert proc.communicate.call_args.kwargs["timeout"] == 60


# ---------------------------------------------------------------------------
# Tools parameter
# ---------------------------------------------------------------------------


class TestToolsParameter:
    def test_no_tools_flag_when_tools_is_none(self) -> None:
        with patch(_POPEN_TARGET, return_value=_mock_proc("ok")) as mock_popen:
            invoke_claude_text(**_call_kwargs())
        cmd = mock_popen.call_args.args[0]
        assert "--tools" not in cmd

    def test_an_empty_tool_list_disables_every_tool_at_the_argv_level(self) -> None:
        """``tools=[]`` is not ``tools=None``.  Omitting ``--tools`` leaves the
        CLI's built-in set live (measured 2026-10-04: a no-flag call read
        ``./CLAUDE.md``); ``--tools ""`` disables it.  The user's MCP servers
        survive ``--tools ""`` (measured 2026-10-05: the init event still listed
        a filesystem reader), so ``--strict-mcp-config`` is emitted with it."""
        with patch(_POPEN_TARGET, return_value=_mock_proc("ok")) as mock_popen:
            invoke_claude_text(**_call_kwargs(), tools=[])
        cmd = mock_popen.call_args.args[0]
        idx = cmd.index("--tools")
        assert cmd[idx + 1] == ""
        assert "--strict-mcp-config" in cmd

    def test_the_no_tools_marker_is_an_empty_list(self) -> None:
        assert list(NO_TOOLS) == []
        with patch(_POPEN_TARGET, return_value=_mock_proc("ok")) as mock_popen:
            invoke_claude_text(**_call_kwargs(), tools=NO_TOOLS)
        cmd = mock_popen.call_args.args[0]
        assert cmd[cmd.index("--tools") + 1] == ""

    def test_a_named_tool_list_does_not_strip_mcp_servers(self) -> None:
        with patch(_POPEN_TARGET, return_value=_mock_proc("ok")) as mock_popen:
            invoke_claude_text(**_call_kwargs(), tools=["Read"])
        assert "--strict-mcp-config" not in mock_popen.call_args.args[0]

    def test_the_empty_tools_flag_precedes_the_system_prompt_flag(self) -> None:
        """``--tools`` is variadic at the CLI; the next option terminates it.
        The system prompt must therefore follow as an option, never as a
        positional, or it is absorbed into the tool list."""
        with patch(_POPEN_TARGET, return_value=_mock_proc("ok")) as mock_popen:
            invoke_claude_text(**_call_kwargs(), tools=[])
        cmd = mock_popen.call_args.args[0]
        idx = cmd.index("--tools")
        assert cmd[idx + 2].startswith("--")

    def test_single_tool_produces_tools_flag(self) -> None:
        with patch(_POPEN_TARGET, return_value=_mock_proc("ok")) as mock_popen:
            invoke_claude_text(**_call_kwargs(), tools=["Read"])
        cmd = mock_popen.call_args.args[0]
        idx = cmd.index("--tools")
        assert cmd[idx + 1] == "Read"

    def test_multiple_tools_comma_separated(self) -> None:
        with patch(_POPEN_TARGET, return_value=_mock_proc("ok")) as mock_popen:
            invoke_claude_text(**_call_kwargs(), tools=["Read", "Glob"])
        cmd = mock_popen.call_args.args[0]
        idx = cmd.index("--tools")
        assert cmd[idx + 1] == "Read,Glob"

    def test_tools_flag_before_system_prompt(self) -> None:
        with patch(_POPEN_TARGET, return_value=_mock_proc("ok")) as mock_popen:
            invoke_claude_text(**_call_kwargs(), tools=["Read"])
        cmd = mock_popen.call_args.args[0]
        tools_idx = cmd.index("--tools")
        system_idx = cmd.index("--system-prompt")
        assert tools_idx < system_idx


# ---------------------------------------------------------------------------
# Working directory
# ---------------------------------------------------------------------------


class TestWorkingDirectory:
    def test_no_cwd_by_default(self) -> None:
        """Unchanged behaviour: the child inherits the caller's directory."""
        with patch(_POPEN_TARGET, return_value=_mock_proc("ok")) as mock_popen:
            invoke_claude_text(**_call_kwargs())
        assert mock_popen.call_args.kwargs.get("cwd") is None

    def test_cwd_is_handed_to_popen(self, tmp_path: Path) -> None:
        with patch(_POPEN_TARGET, return_value=_mock_proc("ok")) as mock_popen:
            invoke_claude_text(**_call_kwargs(), cwd=tmp_path)
        assert mock_popen.call_args.kwargs["cwd"] == str(tmp_path)

    def test_a_missing_cwd_is_refused_before_spawning(self, tmp_path: Path) -> None:
        with patch(_POPEN_TARGET, return_value=_mock_proc("ok")) as mock_popen:
            with pytest.raises(ClaudeTransportError, match="working directory"):
                invoke_claude_text(**_call_kwargs(), cwd=tmp_path / "absent")
        assert mock_popen.call_count == 0


# ---------------------------------------------------------------------------
# stream-json reassembly (front-truncation fix)
# ---------------------------------------------------------------------------


def _assistant_event(
    *blocks: dict,
    parent_tool_use_id: str | None = None,
    stop_reason: str | None = None,
) -> dict:
    """Build a stream-json assistant event with the given content blocks.

    ``stop_reason`` mirrors the CLI's ``message.stop_reason``.  It is what
    distinguishes a turn the model finished from one the output-token
    ceiling cut short, and the reassembler joins the two cases differently.
    """
    return {
        "type": "assistant",
        "parent_tool_use_id": parent_tool_use_id,
        "message": {
            "role": "assistant",
            "content": list(blocks),
            "stop_reason": stop_reason,
        },
    }


def _text(text: str) -> dict:
    return {"type": "text", "text": text}


def _stream(*events: dict) -> str:
    """Serialize events to the JSONL shape claude -p --output-format stream-json emits."""
    return "\n".join(json.dumps(e) for e in events)


class TestStreamJsonReassembly:
    _INIT = {"type": "system", "subtype": "init", "session_id": "s1"}
    _RESULT = {"type": "result", "subtype": "success", "result": "tail"}

    def test_command_requests_stream_json_with_verbose(self) -> None:
        with patch(_POPEN_TARGET, return_value=_mock_proc("ok")) as mock_popen:
            invoke_claude_text(**_call_kwargs())
        cmd = mock_popen.call_args.args[0]
        idx = cmd.index("--output-format")
        assert cmd[idx + 1] == "stream-json"
        assert "--verbose" in cmd

    def test_single_assistant_message_text_returned(self) -> None:
        out = _stream(self._INIT, _assistant_event(_text("OK")), self._RESULT)
        with patch(_POPEN_TARGET, return_value=_mock_proc(out)):
            assert invoke_claude_text(**_call_kwargs()) == "OK"

    def test_multi_turn_split_rejoins_seamlessly(self) -> None:
        """A generation cut mid-token across two assistant turns (the run
        e93b54c6 '3.1' failure: the CLI's text mode returned only the tail,
        front-truncating the JSON object) must be reassembled whole, with no
        separator injected inside the split JSON string."""
        front = '{"content": "WP'
        tail = '5 covers communication."}'
        out = _stream(
            self._INIT,
            _assistant_event(_text(front)),
            _assistant_event(_text(tail)),
            {"type": "result", "subtype": "success", "result": tail},
        )
        with patch(_POPEN_TARGET, return_value=_mock_proc(out)):
            result = invoke_claude_text(**_call_kwargs())
        assert result == front + tail
        assert json.loads(result) == {"content": "WP5 covers communication."}

    def test_result_event_text_is_not_duplicated(self) -> None:
        out = _stream(self._INIT, _assistant_event(_text("OK")),
                      {"type": "result", "subtype": "success", "result": "OK"})
        with patch(_POPEN_TARGET, return_value=_mock_proc(out)):
            assert invoke_claude_text(**_call_kwargs()) == "OK"

    def test_tool_use_and_thinking_blocks_skipped(self) -> None:
        out = _stream(
            self._INIT,
            _assistant_event(
                {"type": "thinking", "thinking": "planning..."},
                _text("prose "),
                {"type": "tool_use", "id": "t1", "name": "Read", "input": {}},
            ),
            _assistant_event(_text("answer")),
        )
        with patch(_POPEN_TARGET, return_value=_mock_proc(out)):
            assert invoke_claude_text(**_call_kwargs()) == "prose answer"

    def test_subagent_assistant_messages_skipped(self) -> None:
        out = _stream(
            self._INIT,
            _assistant_event(_text("sub"), parent_tool_use_id="tu_1"),
            _assistant_event(_text("top")),
        )
        with patch(_POPEN_TARGET, return_value=_mock_proc(out)):
            assert invoke_claude_text(**_call_kwargs()) == "top"

    def test_plain_text_stdout_falls_back_verbatim(self) -> None:
        """A CLI (or test double) that ignored the output-format flag still
        works: non-stream stdout is the response, exactly as before."""
        out = "Just a plain\nmulti-line answer with {\"k\": 1} inside."
        with patch(_POPEN_TARGET, return_value=_mock_proc(out)):
            assert invoke_claude_text(**_call_kwargs()) == out

    def test_stream_events_without_assistant_text_fail_closed(self) -> None:
        out = _stream(self._INIT, {"type": "result", "subtype": "error_during_execution"})
        with patch(_POPEN_TARGET, return_value=_mock_proc(out)):
            with pytest.raises(ClaudeTransportError, match="no assistant text"):
                invoke_claude_text(**_call_kwargs())

    def test_malformed_jsonl_lines_are_ignored(self) -> None:
        out = "{not json\n" + _stream(_assistant_event(_text("OK"))) + "\n{also not json"
        with patch(_POPEN_TARGET, return_value=_mock_proc(out)):
            assert invoke_claude_text(**_call_kwargs()) == "OK"


# ---------------------------------------------------------------------------
# System prompt length fallback
# ---------------------------------------------------------------------------


class TestSystemPromptFallback:
    def test_long_system_prompt_embedded_in_user_prompt(self) -> None:
        long_prompt = "x" * (_MAX_SYSTEM_PROMPT_CLI_LENGTH + 1)
        proc = _mock_proc("ok")
        pipe = proc.stdin  # captured before the transport detaches it
        with patch(_POPEN_TARGET, return_value=proc) as mock_popen:
            invoke_claude_text(
                system_prompt=long_prompt,
                user_prompt="Hello",
                model="sonnet",
                max_tokens=1024,
            )
        cmd = mock_popen.call_args.args[0]
        assert "--system-prompt" not in cmd
        stdin_input = "".join(c.args[0] for c in pipe.write.call_args_list)
        assert "SYSTEM INSTRUCTIONS" in stdin_input
        assert long_prompt in stdin_input
        assert "Hello" in stdin_input

    def test_exact_threshold_uses_flag(self) -> None:
        exact_prompt = "y" * _MAX_SYSTEM_PROMPT_CLI_LENGTH
        with patch(_POPEN_TARGET, return_value=_mock_proc("ok")) as mock_popen:
            invoke_claude_text(
                system_prompt=exact_prompt,
                user_prompt="Hi",
                model="sonnet",
                max_tokens=1024,
            )
        cmd = mock_popen.call_args.args[0]
        assert "--system-prompt" in cmd


# ---------------------------------------------------------------------------
# Non-zero exit code
# ---------------------------------------------------------------------------


class TestNonZeroExitCode:
    def test_raises_transport_error(self) -> None:
        with patch(_POPEN_TARGET, return_value=_mock_proc("", "error msg", 1)):
            with pytest.raises(ClaudeTransportError, match="exited with code 1"):
                invoke_claude_text(**_call_kwargs())

    def test_includes_stderr_in_message(self) -> None:
        with patch(
            _POPEN_TARGET,
            return_value=_mock_proc("", "authentication failed", 1),
        ):
            with pytest.raises(ClaudeTransportError, match="authentication failed"):
                invoke_claude_text(**_call_kwargs())

    def test_handles_empty_stderr(self) -> None:
        with patch(_POPEN_TARGET, return_value=_mock_proc("", "", 2)):
            with pytest.raises(ClaudeTransportError, match="exited with code 2"):
                invoke_claude_text(**_call_kwargs())

    def test_stdout_detail_surfaced_when_stderr_empty(self) -> None:
        # A non-zero exit whose diagnostic lands on stdout (stderr empty) must
        # still be visible in the exception message, not a blind exit code.
        with patch(
            _POPEN_TARGET,
            return_value=_mock_proc("Something went wrong on stdout", "", 1),
        ):
            with pytest.raises(
                ClaudeTransportError, match="Something went wrong on stdout"
            ):
                invoke_claude_text(**_call_kwargs())


# ---------------------------------------------------------------------------
# Subscription usage-limit refusal (stdout notice, non-zero exit)
# ---------------------------------------------------------------------------


class TestRateLimitRefusal:
    #: The exact notice observed in run 0d041dae's skill_diag stdout.
    _NOTICE = "You've hit your limit · resets 9:20pm (Europe/Budapest)"

    def test_is_subclass_of_transport_error(self) -> None:
        assert issubclass(ClaudeCLIRateLimitError, ClaudeTransportError)

    def test_stdout_limit_notice_raises_rate_limit_error(self) -> None:
        with patch(_POPEN_TARGET, return_value=_mock_proc(self._NOTICE, "", 1)):
            with pytest.raises(ClaudeCLIRateLimitError, match="usage limit reached"):
                invoke_claude_text(**_call_kwargs())

    def test_reset_notice_captured_verbatim(self) -> None:
        with patch(_POPEN_TARGET, return_value=_mock_proc(self._NOTICE, "", 1)):
            try:
                invoke_claude_text(**_call_kwargs())
            except ClaudeCLIRateLimitError as exc:
                assert exc.reset_notice == self._NOTICE
                assert "resets 9:20pm" in str(exc)
            else:
                pytest.fail("expected ClaudeCLIRateLimitError")

    def test_notice_on_stderr_also_detected(self) -> None:
        # Defensive: if a future CLI version routes the notice to stderr, the
        # detection must still fire.
        with patch(
            _POPEN_TARGET,
            return_value=_mock_proc("", "Claude usage limit reached", 1),
        ):
            with pytest.raises(ClaudeCLIRateLimitError):
                invoke_claude_text(**_call_kwargs())

    def test_ordinary_error_is_not_misclassified_as_rate_limit(self) -> None:
        # A generic failure that merely mentions "limit" in an unrelated way
        # must remain a plain ClaudeTransportError, not a rate-limit error.
        with patch(
            _POPEN_TARGET,
            return_value=_mock_proc("", "config value exceeds limit", 1),
        ):
            with pytest.raises(ClaudeTransportError) as ei:
                invoke_claude_text(**_call_kwargs())
        assert not isinstance(ei.value, ClaudeCLIRateLimitError)


# ---------------------------------------------------------------------------
# Missing executable
# ---------------------------------------------------------------------------


class TestMissingExecutable:
    def test_raises_cli_unavailable_error(self) -> None:
        with patch(_POPEN_TARGET, side_effect=FileNotFoundError("not found")):
            with pytest.raises(ClaudeCLIUnavailableError, match="not found on PATH"):
                invoke_claude_text(**_call_kwargs())

    def test_is_subclass_of_transport_error(self) -> None:
        assert issubclass(ClaudeCLIUnavailableError, ClaudeTransportError)


# ---------------------------------------------------------------------------
# Timeout
# ---------------------------------------------------------------------------


class TestTimeout:
    def test_raises_timeout_error(self) -> None:
        proc = _timeout_proc(subprocess.TimeoutExpired(cmd="claude", timeout=60))
        with patch(_POPEN_TARGET, return_value=proc):
            with pytest.raises(ClaudeCLITimeoutError, match="timed out"):
                invoke_claude_text(**_call_kwargs(), timeout_seconds=60)

    def test_is_subclass_of_transport_error(self) -> None:
        assert issubclass(ClaudeCLITimeoutError, ClaudeTransportError)

    def test_timeout_kills_process_tree(self) -> None:
        """The timeout path must terminate the child's whole process tree."""
        proc = _timeout_proc(
            subprocess.TimeoutExpired(cmd="claude", timeout=60), poll=None
        )
        with patch(_POPEN_TARGET, return_value=proc), patch(
            "runner.claude_transport._kill_process_tree"
        ) as mock_kill:
            with pytest.raises(ClaudeCLITimeoutError):
                invoke_claude_text(**_call_kwargs(), timeout_seconds=60)
        mock_kill.assert_called_once_with(proc)

    def test_timeout_preserves_stdout_stderr(self) -> None:
        te = subprocess.TimeoutExpired(cmd=["claude", "-p"], timeout=120)
        te.stdout = "partial output"
        te.stderr = "some warning"
        with patch(_POPEN_TARGET, return_value=_timeout_proc(te)):
            with pytest.raises(ClaudeCLITimeoutError) as exc_info:
                invoke_claude_text(**_call_kwargs(), timeout_seconds=120)
        err = exc_info.value
        assert err.stdout == "partial output"
        assert err.stderr == "some warning"

    def test_timeout_falls_back_to_drained_output(self) -> None:
        """When the TimeoutExpired carries no output, the post-kill drain
        supplies whatever the pipes had buffered."""
        te = subprocess.TimeoutExpired(cmd="claude", timeout=60)  # stdout/stderr None
        proc = _timeout_proc(te, drain=("drained out", "drained err"))
        with patch(_POPEN_TARGET, return_value=proc):
            with pytest.raises(ClaudeCLITimeoutError) as exc_info:
                invoke_claude_text(**_call_kwargs(), timeout_seconds=60)
        err = exc_info.value
        assert err.stdout == "drained out"
        assert err.stderr == "drained err"

    def test_timeout_preserves_command(self) -> None:
        te = subprocess.TimeoutExpired(cmd=["claude", "-p"], timeout=60)
        with patch(_POPEN_TARGET, return_value=_timeout_proc(te)):
            with pytest.raises(ClaudeCLITimeoutError) as exc_info:
                invoke_claude_text(**_call_kwargs(), timeout_seconds=60)
        err = exc_info.value
        assert isinstance(err.command, list)
        # cmd[0] is the *resolved* executable (TR-3), not the bare name — an
        # absolute path when one is found, the bare name only when nothing is
        # on the search path.  Either way it identifies the claude CLI.
        assert os.path.basename(err.command[0]).lower().startswith("claude")

    def test_timeout_has_elapsed_seconds(self) -> None:
        te = subprocess.TimeoutExpired(cmd="claude", timeout=30)
        with patch(_POPEN_TARGET, return_value=_timeout_proc(te)):
            with pytest.raises(ClaudeCLITimeoutError) as exc_info:
                invoke_claude_text(**_call_kwargs(), timeout_seconds=30)
        err = exc_info.value
        assert err.timeout_seconds == 30
        assert isinstance(err.elapsed_seconds, float)
        assert err.elapsed_seconds >= 0

    def test_timeout_none_stdout_stays_none(self) -> None:
        """When nothing is captured, stdout/stderr are None, not ''."""
        te = subprocess.TimeoutExpired(cmd="claude", timeout=60)
        # TimeoutExpired defaults: stdout=None, stderr=None; drain also None.
        with patch(_POPEN_TARGET, return_value=_timeout_proc(te, drain=(None, None))):
            with pytest.raises(ClaudeCLITimeoutError) as exc_info:
                invoke_claude_text(**_call_kwargs(), timeout_seconds=60)
        err = exc_info.value
        assert err.stdout is None
        assert err.stderr is None


# ---------------------------------------------------------------------------
# Empty / whitespace stdout
# ---------------------------------------------------------------------------


class TestEmptyOutput:
    def test_empty_string_raises(self) -> None:
        with patch(_POPEN_TARGET, return_value=_mock_proc("")):
            with pytest.raises(ClaudeTransportError, match="empty output"):
                invoke_claude_text(**_call_kwargs())

    def test_whitespace_only_raises(self) -> None:
        with patch(_POPEN_TARGET, return_value=_mock_proc("   \n  ")):
            with pytest.raises(ClaudeTransportError, match="empty output"):
                invoke_claude_text(**_call_kwargs())

    def test_none_stdout_raises(self) -> None:
        with patch(_POPEN_TARGET, return_value=_mock_proc(None)):
            with pytest.raises(ClaudeTransportError, match="empty output"):
                invoke_claude_text(**_call_kwargs())

    def test_includes_stderr_hint_when_available(self) -> None:
        with patch(
            _POPEN_TARGET,
            return_value=_mock_proc("", "some hint"),
        ):
            with pytest.raises(ClaudeTransportError, match="some hint"):
                invoke_claude_text(**_call_kwargs())


# ---------------------------------------------------------------------------
# Unexpected exceptions
# ---------------------------------------------------------------------------


class TestUnexpectedException:
    def test_wraps_spawn_failure_in_transport_error(self) -> None:
        with patch(_POPEN_TARGET, side_effect=OSError("disk full")):
            with pytest.raises(ClaudeTransportError, match="disk full"):
                invoke_claude_text(**_call_kwargs())

    def test_wraps_communicate_failure_in_transport_error(self) -> None:
        proc = MagicMock(spec=subprocess.Popen)
        proc.communicate.side_effect = OSError("pipe broke")
        proc.poll.return_value = 1  # already exited -> tree kill is a no-op
        proc.pid = 4242
        proc.stdin = MagicMock()
        with patch(_POPEN_TARGET, return_value=proc):
            with pytest.raises(ClaudeTransportError, match="pipe broke"):
                invoke_claude_text(**_call_kwargs())


# ---------------------------------------------------------------------------
# Executable resolution / CLI pin (TR-3)
# ---------------------------------------------------------------------------


class TestCliPathResolution:
    """The pin decides which installed CLI build the runner spawns.

    Regression target: ``Popen(["claude", ...])`` resolved a *different*
    executable than the operator's shell did (2.1.81 vs 2.1.224 on the
    reference machine), so the runner was never exercising the CLI under
    test.  These tests lock the resolution rules, not the CLI's behaviour.
    """

    # -- unpinned -----------------------------------------------------------

    def test_unset_pin_uses_absolute_path_search_result(self) -> None:
        with patch(
            "runner.claude_transport.shutil.which",
            return_value=os.path.join(os.sep, "usr", "local", "bin", "claude"),
        ):
            assert resolve_claude_cli() == ClaudeCLIResolution(
                os.path.join(os.sep, "usr", "local", "bin", "claude"), "path"
            )

    def test_unset_pin_with_nothing_on_path_falls_back_to_bare_name(self) -> None:
        """Historical contract: the spawn fails and reports it from one place."""
        with patch("runner.claude_transport.shutil.which", return_value=None):
            assert resolve_claude_cli() == ClaudeCLIResolution("claude", "unresolved")

    def test_unresolved_name_still_raises_cli_unavailable(self) -> None:
        with patch("runner.claude_transport.shutil.which", return_value=None):
            with patch(_POPEN_TARGET, side_effect=FileNotFoundError("nope")):
                with pytest.raises(
                    ClaudeCLIUnavailableError, match=_CLI_PATH_ENV_VAR
                ):
                    invoke_claude_text(**_call_kwargs())

    # -- pinned -------------------------------------------------------------

    def test_pin_wins_over_path_search(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        pinned = tmp_path / "claude.exe"
        pinned.write_text("stub")
        monkeypatch.setenv(_CLI_PATH_ENV_VAR, str(pinned))
        with patch(
            "runner.claude_transport.shutil.which", return_value="/somewhere/else/claude"
        ):
            resolution = resolve_claude_cli()
        assert resolution == ClaudeCLIResolution(str(pinned), "env")

    def test_pinned_path_becomes_argv0(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        pinned = tmp_path / "claude.exe"
        pinned.write_text("stub")
        monkeypatch.setenv(_CLI_PATH_ENV_VAR, str(pinned))
        with patch(_POPEN_TARGET, return_value=_mock_proc("ok")) as mock_popen:
            invoke_claude_text(**_call_kwargs())
        assert mock_popen.call_args.args[0][0] == str(pinned)

    def test_pin_tolerates_quotes_and_whitespace(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Operators paste paths straight out of a shell prompt."""
        pinned = tmp_path / "claude.exe"
        pinned.write_text("stub")
        monkeypatch.setenv(_CLI_PATH_ENV_VAR, f'  "{pinned}"  ')
        assert resolve_claude_cli().path == str(pinned)

    def test_pin_expands_user_and_env_vars(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        pinned = tmp_path / "claude.exe"
        pinned.write_text("stub")
        monkeypatch.setenv("PIN_TEST_HOME", str(tmp_path))
        monkeypatch.setenv(
            _CLI_PATH_ENV_VAR, os.path.join("$PIN_TEST_HOME", "claude.exe")
        )
        assert resolve_claude_cli().path == str(pinned)

    def test_bare_command_name_pin_is_resolved_on_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        target = tmp_path / "claude-nightly"
        target.write_text("stub")
        monkeypatch.setenv(_CLI_PATH_ENV_VAR, "claude-nightly")
        with patch("runner.claude_transport.shutil.which", return_value=str(target)):
            assert resolve_claude_cli() == ClaudeCLIResolution(str(target), "env")

    # -- fail-closed --------------------------------------------------------

    def test_missing_pinned_file_fails_closed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A typo must stop the run, never silently fall back to a search."""
        monkeypatch.setenv(_CLI_PATH_ENV_VAR, str(tmp_path / "does_not_exist.exe"))
        with patch(
            "runner.claude_transport.shutil.which", return_value="/usr/bin/claude"
        ):
            with pytest.raises(ClaudeCLIUnavailableError, match="no file exists"):
                resolve_claude_cli()

    def test_missing_pinned_file_never_spawns(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(_CLI_PATH_ENV_VAR, str(tmp_path / "does_not_exist.exe"))
        with patch(_POPEN_TARGET) as mock_popen:
            with pytest.raises(ClaudeCLIUnavailableError):
                invoke_claude_text(**_call_kwargs())
        mock_popen.assert_not_called()

    def test_directory_pin_fails_closed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(_CLI_PATH_ENV_VAR, str(tmp_path))
        with pytest.raises(ClaudeCLIUnavailableError, match="no file exists"):
            resolve_claude_cli()

    def test_unresolvable_bare_name_pin_fails_closed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(_CLI_PATH_ENV_VAR, "claude-nightly")
        with patch("runner.claude_transport.shutil.which", return_value=None):
            with pytest.raises(ClaudeCLIUnavailableError, match="bare command name"):
                resolve_claude_cli()

    def test_windows_ps1_pin_is_rejected(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`Get-Command claude` reports the .ps1 shim — the one value that
        can never work with shell=False, so it must fail loudly at resolution
        rather than as an opaque WinError at spawn time."""
        pinned = tmp_path / "claude.ps1"
        pinned.write_text("# shim")
        monkeypatch.setenv(_CLI_PATH_ENV_VAR, str(pinned))
        with patch("runner.claude_transport._IS_WINDOWS", True):
            with pytest.raises(ClaudeCLIUnavailableError, match="PowerShell script"):
                resolve_claude_cli()

    def test_posix_does_not_reject_ps1_suffix(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The .ps1 guard is a Windows spawn rule, not a naming policy."""
        pinned = tmp_path / "claude.ps1"
        pinned.write_text("# shim")
        monkeypatch.setenv(_CLI_PATH_ENV_VAR, str(pinned))
        with patch("runner.claude_transport._IS_WINDOWS", False):
            assert resolve_claude_cli().source == "env"

    # -- empty / whitespace-only pin ---------------------------------------

    def test_whitespace_only_pin_is_treated_as_unset(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(_CLI_PATH_ENV_VAR, "   ")
        with patch(
            "runner.claude_transport.shutil.which", return_value="/usr/bin/claude"
        ):
            assert resolve_claude_cli().source == "path"


# ---------------------------------------------------------------------------
# Continuation restart splice (run 0395b136 concept-alignment-check)
# ---------------------------------------------------------------------------


class TestContinuationRestartSplice:
    """An output-token cut inside a fenced code block is not resumed at the
    token boundary: the CLI's auto-continuation re-opens a fence and the
    model re-emits the element it was cut inside, so the two turns overlap.

    Joining them verbatim is what broke run 0395b136 — turn 1 ended at
    ``"coverage_description": "CC`` and turn 2 began ```` ```json ```` +
    ``"CC-12": {``, putting a raw newline inside a JSON string.  The whole
    38k-character artifact was lost, the skill failed with a bare "non-JSON
    response", and the node reported the *downstream* skill's missing input
    as the fault.
    """

    _INIT = {"type": "system", "subtype": "init", "session_id": "s1"}

    def test_fenced_restart_is_spliced_at_the_overlap(self) -> None:
        cut = (
            '```json\n{\n  "scope_coverage": {\n'
            '    "CC-11": {"coverage_status": "covered"},\n'
            '    "CC-12": {\n      "scope_element_id": "CC-12",\n'
            '      "coverage_description": "CC'
        )
        restart = (
            '```json\n    "CC-12": {\n      "scope_element_id": "CC-12",\n'
            '      "coverage_description": "CC-12 specifies admissibility."\n'
            '    }\n  }\n}\n```'
        )
        out = _stream(
            self._INIT,
            _assistant_event(_text(cut), stop_reason="max_tokens"),
            _assistant_event(_text(restart), stop_reason="end_turn"),
        )
        with patch(_POPEN_TARGET, return_value=_mock_proc(out)):
            result = invoke_claude_text(**_call_kwargs())

        body = result.strip().split("\n", 1)[1].rsplit("```", 1)[0]
        parsed = json.loads(body)
        assert set(parsed["scope_coverage"]) == {"CC-11", "CC-12"}
        assert (
            parsed["scope_coverage"]["CC-12"]["coverage_description"]
            == "CC-12 specifies admissibility."
        )
        # The re-emitted prefix is counted once, not twice.
        assert result.count('"scope_element_id": "CC-12"') == 1

    def test_seamless_token_split_still_joins_verbatim(self) -> None:
        """A cut that the model *does* resume at the token boundary must
        keep the existing behaviour: no separator, no splice."""
        out = _stream(
            self._INIT,
            _assistant_event(_text('{"content": "WP'), stop_reason="max_tokens"),
            _assistant_event(_text('5 covers comms."}'), stop_reason="end_turn"),
        )
        with patch(_POPEN_TARGET, return_value=_mock_proc(out)):
            result = invoke_claude_text(**_call_kwargs())
        assert json.loads(result) == {"content": "WP5 covers comms."}

    def test_fenced_turn_after_a_completed_turn_is_not_spliced(self) -> None:
        """Only a ``max_tokens`` boundary can be a restart.  A turn that
        ended normally and is followed by a fenced block is ordinary
        multi-turn output and must be joined verbatim."""
        out = _stream(
            self._INIT,
            _assistant_event(_text("Here is the answer.\n"), stop_reason="tool_use"),
            _assistant_event(_text('```json\n{"k": 1}\n```'), stop_reason="end_turn"),
        )
        with patch(_POPEN_TARGET, return_value=_mock_proc(out)):
            result = invoke_claude_text(**_call_kwargs())
        assert result == 'Here is the answer.\n```json\n{"k": 1}\n```'

    def test_restart_without_an_anchor_falls_back_to_verbatim_join(self) -> None:
        """No unambiguous resume point means no splice.  The transport must
        not guess: the verbatim join stands and the response fails closed in
        the caller's parser (§17.6.5)."""
        out = _stream(
            self._INIT,
            _assistant_event(_text('{"x": "aaa'), stop_reason="max_tokens"),
            _assistant_event(
                _text('```json\n"never-seen-key": 1\n```'), stop_reason="end_turn"
            ),
        )
        with patch(_POPEN_TARGET, return_value=_mock_proc(out)):
            result = invoke_claude_text(**_call_kwargs())
        assert result == '{"x": "aaa```json\n"never-seen-key": 1\n```'

    def test_missing_stop_reason_is_treated_as_a_finished_turn(self) -> None:
        """A CLI build that omits stop_reason must not trigger a splice."""
        out = _stream(
            self._INIT,
            _assistant_event(_text("head ")),
            _assistant_event(_text("```json\nhead {}\n```")),
        )
        with patch(_POPEN_TARGET, return_value=_mock_proc(out)):
            result = invoke_claude_text(**_call_kwargs())
        assert result == "head ```json\nhead {}\n```"


# ---------------------------------------------------------------------------
# Output-token ceiling
# ---------------------------------------------------------------------------


class TestOutputTokenCeiling:
    """The ceiling is *assigned*, never defaulted.

    It used to be applied with ``setdefault``, so a CLAUDE_CODE_MAX_OUTPUT_
    TOKENS inherited from the operator's shell silently won and capped every
    skill generation at whatever that shell carried — the cut that produced
    the run 0395b136 restart.  Overrides must be deliberate.
    """

    def _spawn_env(self, monkeypatch: pytest.MonkeyPatch) -> dict:
        with patch(_POPEN_TARGET, return_value=_mock_proc("ok")) as mock_popen:
            invoke_claude_text(**_call_kwargs())
        return mock_popen.call_args.kwargs["env"]

    def test_default_ceiling_applied(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv(_MAX_OUTPUT_TOKENS_ENV_VAR, raising=False)
        monkeypatch.delenv(_CLI_MAX_OUTPUT_TOKENS_VAR, raising=False)
        env = self._spawn_env(monkeypatch)
        assert env[_CLI_MAX_OUTPUT_TOKENS_VAR] == _MAX_OUTPUT_TOKENS_DEFAULT

    def test_ambient_cli_variable_does_not_win(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv(_MAX_OUTPUT_TOKENS_ENV_VAR, raising=False)
        monkeypatch.setenv(_CLI_MAX_OUTPUT_TOKENS_VAR, "8192")
        env = self._spawn_env(monkeypatch)
        assert env[_CLI_MAX_OUTPUT_TOKENS_VAR] == _MAX_OUTPUT_TOKENS_DEFAULT

    def test_orchestrator_override_wins(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(_MAX_OUTPUT_TOKENS_ENV_VAR, "48000")
        env = self._spawn_env(monkeypatch)
        assert env[_CLI_MAX_OUTPUT_TOKENS_VAR] == "48000"

    @pytest.mark.parametrize("bad", ["nonsense", "0", "-1", "  "])
    def test_invalid_override_falls_back_to_default(
        self, monkeypatch: pytest.MonkeyPatch, bad: str
    ) -> None:
        monkeypatch.setenv(_MAX_OUTPUT_TOKENS_ENV_VAR, bad)
        env = self._spawn_env(monkeypatch)
        assert env[_CLI_MAX_OUTPUT_TOKENS_VAR] == _MAX_OUTPUT_TOKENS_DEFAULT

