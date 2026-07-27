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

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from runner.claude_transport import (
    ClaudeCLITimeoutError,
    ClaudeCLIUnavailableError,
    ClaudeTransportError,
    DEFAULT_TIMEOUT_SECONDS,
    _MAX_SYSTEM_PROMPT_CLI_LENGTH,
    invoke_claude_text,
)


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
        with patch(_POPEN_TARGET, return_value=proc):
            invoke_claude_text(**_call_kwargs())
        # The user prompt is sent through communicate(input=...), not Popen.
        assert proc.communicate.call_args.kwargs["input"] == "Hello"

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

    def test_no_tools_flag_when_tools_is_empty_list(self) -> None:
        with patch(_POPEN_TARGET, return_value=_mock_proc("ok")) as mock_popen:
            invoke_claude_text(**_call_kwargs(), tools=[])
        cmd = mock_popen.call_args.args[0]
        assert "--tools" not in cmd

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
# System prompt length fallback
# ---------------------------------------------------------------------------


class TestSystemPromptFallback:
    def test_long_system_prompt_embedded_in_user_prompt(self) -> None:
        long_prompt = "x" * (_MAX_SYSTEM_PROMPT_CLI_LENGTH + 1)
        proc = _mock_proc("ok")
        with patch(_POPEN_TARGET, return_value=proc) as mock_popen:
            invoke_claude_text(
                system_prompt=long_prompt,
                user_prompt="Hello",
                model="sonnet",
                max_tokens=1024,
            )
        cmd = mock_popen.call_args.args[0]
        assert "--system-prompt" not in cmd
        stdin_input = proc.communicate.call_args.kwargs["input"]
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
        assert err.command[0] == "claude"

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
        with patch(_POPEN_TARGET, return_value=proc):
            with pytest.raises(ClaudeTransportError, match="pipe broke"):
                invoke_claude_text(**_call_kwargs())
