"""
Unit tests for runner/claude_transport.py — Claude CLI transport adapter.

Tests mock ``subprocess.run`` to verify the transport adapter's behavior
without requiring the ``claude`` CLI to be installed.

Test groups:
  - Successful invocation — stdout returned
  - Non-zero exit code — ClaudeTransportError raised
  - Missing executable — ClaudeCLIUnavailableError raised
  - Timeout — ClaudeCLITimeoutError raised
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

_SUBPROCESS_TARGET = "runner.claude_transport.subprocess.run"


def _mock_completed(stdout: str = "response", stderr: str = "", returncode: int = 0):
    """Create a mock CompletedProcess."""
    cp = MagicMock(spec=subprocess.CompletedProcess)
    cp.stdout = stdout
    cp.stderr = stderr
    cp.returncode = returncode
    return cp


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
        with patch(_SUBPROCESS_TARGET, return_value=_mock_completed("Hello world")) as mock_run:
            result = invoke_claude_text(**_call_kwargs())
        assert result == "Hello world"
        mock_run.assert_called_once()

    def test_passes_user_prompt_via_stdin(self) -> None:
        with patch(_SUBPROCESS_TARGET, return_value=_mock_completed("ok")) as mock_run:
            invoke_claude_text(**_call_kwargs())
        call_kwargs = mock_run.call_args
        assert call_kwargs.kwargs["input"] == "Hello"

    def test_uses_text_mode_and_utf8(self) -> None:
        with patch(_SUBPROCESS_TARGET, return_value=_mock_completed("ok")) as mock_run:
            invoke_claude_text(**_call_kwargs())
        kw = mock_run.call_args.kwargs
        assert kw["text"] is True
        assert kw["encoding"] == "utf-8"

    def test_does_not_use_shell(self) -> None:
        with patch(_SUBPROCESS_TARGET, return_value=_mock_completed("ok")) as mock_run:
            invoke_claude_text(**_call_kwargs())
        assert mock_run.call_args.kwargs["shell"] is False

    def test_captures_stdout_and_stderr(self) -> None:
        with patch(_SUBPROCESS_TARGET, return_value=_mock_completed("ok")) as mock_run:
            invoke_claude_text(**_call_kwargs())
        assert mock_run.call_args.kwargs["capture_output"] is True


# ---------------------------------------------------------------------------
# Command construction
# ---------------------------------------------------------------------------


class TestCommandConstruction:
    def test_command_includes_print_mode(self) -> None:
        with patch(_SUBPROCESS_TARGET, return_value=_mock_completed("ok")) as mock_run:
            invoke_claude_text(**_call_kwargs())
        cmd = mock_run.call_args.args[0]
        assert "-p" in cmd

    def test_command_includes_model(self) -> None:
        with patch(_SUBPROCESS_TARGET, return_value=_mock_completed("ok")) as mock_run:
            invoke_claude_text(**_call_kwargs())
        cmd = mock_run.call_args.args[0]
        idx = cmd.index("--model")
        assert cmd[idx + 1] == "claude-sonnet-4-6"

    def test_command_includes_max_tokens(self) -> None:
        with patch(_SUBPROCESS_TARGET, return_value=_mock_completed("ok")) as mock_run:
            invoke_claude_text(**_call_kwargs())
        cmd = mock_run.call_args.args[0]
        idx = cmd.index("--max-tokens")
        assert cmd[idx + 1] == "4096"

    def test_short_system_prompt_passed_via_flag(self) -> None:
        with patch(_SUBPROCESS_TARGET, return_value=_mock_completed("ok")) as mock_run:
            invoke_claude_text(**_call_kwargs())
        cmd = mock_run.call_args.args[0]
        idx = cmd.index("--system-prompt")
        assert cmd[idx + 1] == "You are helpful."

    def test_default_timeout_applied(self) -> None:
        with patch(_SUBPROCESS_TARGET, return_value=_mock_completed("ok")) as mock_run:
            invoke_claude_text(**_call_kwargs())
        assert mock_run.call_args.kwargs["timeout"] == DEFAULT_TIMEOUT_SECONDS

    def test_custom_timeout_applied(self) -> None:
        with patch(_SUBPROCESS_TARGET, return_value=_mock_completed("ok")) as mock_run:
            invoke_claude_text(**_call_kwargs(), timeout_seconds=60)
        assert mock_run.call_args.kwargs["timeout"] == 60


# ---------------------------------------------------------------------------
# Tools parameter
# ---------------------------------------------------------------------------


class TestToolsParameter:
    def test_no_tools_flag_when_tools_is_none(self) -> None:
        with patch(_SUBPROCESS_TARGET, return_value=_mock_completed("ok")) as mock_run:
            invoke_claude_text(**_call_kwargs())
        cmd = mock_run.call_args.args[0]
        assert "--tools" not in cmd

    def test_no_tools_flag_when_tools_is_empty_list(self) -> None:
        with patch(_SUBPROCESS_TARGET, return_value=_mock_completed("ok")) as mock_run:
            invoke_claude_text(**_call_kwargs(), tools=[])
        cmd = mock_run.call_args.args[0]
        assert "--tools" not in cmd

    def test_single_tool_produces_tools_flag(self) -> None:
        with patch(_SUBPROCESS_TARGET, return_value=_mock_completed("ok")) as mock_run:
            invoke_claude_text(**_call_kwargs(), tools=["Read"])
        cmd = mock_run.call_args.args[0]
        idx = cmd.index("--tools")
        assert cmd[idx + 1] == "Read"

    def test_multiple_tools_comma_separated(self) -> None:
        with patch(_SUBPROCESS_TARGET, return_value=_mock_completed("ok")) as mock_run:
            invoke_claude_text(**_call_kwargs(), tools=["Read", "Glob"])
        cmd = mock_run.call_args.args[0]
        idx = cmd.index("--tools")
        assert cmd[idx + 1] == "Read,Glob"

    def test_tools_flag_before_system_prompt(self) -> None:
        with patch(_SUBPROCESS_TARGET, return_value=_mock_completed("ok")) as mock_run:
            invoke_claude_text(**_call_kwargs(), tools=["Read"])
        cmd = mock_run.call_args.args[0]
        tools_idx = cmd.index("--tools")
        system_idx = cmd.index("--system-prompt")
        assert tools_idx < system_idx


# ---------------------------------------------------------------------------
# System prompt length fallback
# ---------------------------------------------------------------------------


class TestSystemPromptFallback:
    def test_long_system_prompt_embedded_in_user_prompt(self) -> None:
        long_prompt = "x" * (_MAX_SYSTEM_PROMPT_CLI_LENGTH + 1)
        with patch(_SUBPROCESS_TARGET, return_value=_mock_completed("ok")) as mock_run:
            invoke_claude_text(
                system_prompt=long_prompt,
                user_prompt="Hello",
                model="sonnet",
                max_tokens=1024,
            )
        cmd = mock_run.call_args.args[0]
        assert "--system-prompt" not in cmd
        stdin_input = mock_run.call_args.kwargs["input"]
        assert "SYSTEM INSTRUCTIONS" in stdin_input
        assert long_prompt in stdin_input
        assert "Hello" in stdin_input

    def test_exact_threshold_uses_flag(self) -> None:
        exact_prompt = "y" * _MAX_SYSTEM_PROMPT_CLI_LENGTH
        with patch(_SUBPROCESS_TARGET, return_value=_mock_completed("ok")) as mock_run:
            invoke_claude_text(
                system_prompt=exact_prompt,
                user_prompt="Hi",
                model="sonnet",
                max_tokens=1024,
            )
        cmd = mock_run.call_args.args[0]
        assert "--system-prompt" in cmd


# ---------------------------------------------------------------------------
# Non-zero exit code
# ---------------------------------------------------------------------------


class TestNonZeroExitCode:
    def test_raises_transport_error(self) -> None:
        with patch(_SUBPROCESS_TARGET, return_value=_mock_completed("", "error msg", 1)):
            with pytest.raises(ClaudeTransportError, match="exited with code 1"):
                invoke_claude_text(**_call_kwargs())

    def test_includes_stderr_in_message(self) -> None:
        with patch(
            _SUBPROCESS_TARGET,
            return_value=_mock_completed("", "authentication failed", 1),
        ):
            with pytest.raises(ClaudeTransportError, match="authentication failed"):
                invoke_claude_text(**_call_kwargs())

    def test_handles_empty_stderr(self) -> None:
        with patch(_SUBPROCESS_TARGET, return_value=_mock_completed("", "", 2)):
            with pytest.raises(ClaudeTransportError, match="exited with code 2"):
                invoke_claude_text(**_call_kwargs())


# ---------------------------------------------------------------------------
# Missing executable
# ---------------------------------------------------------------------------


class TestMissingExecutable:
    def test_raises_cli_unavailable_error(self) -> None:
        with patch(_SUBPROCESS_TARGET, side_effect=FileNotFoundError("not found")):
            with pytest.raises(ClaudeCLIUnavailableError, match="not found on PATH"):
                invoke_claude_text(**_call_kwargs())

    def test_is_subclass_of_transport_error(self) -> None:
        assert issubclass(ClaudeCLIUnavailableError, ClaudeTransportError)


# ---------------------------------------------------------------------------
# Timeout
# ---------------------------------------------------------------------------


class TestTimeout:
    def test_raises_timeout_error(self) -> None:
        with patch(
            _SUBPROCESS_TARGET,
            side_effect=subprocess.TimeoutExpired(cmd="claude", timeout=60),
        ):
            with pytest.raises(ClaudeCLITimeoutError, match="timed out"):
                invoke_claude_text(**_call_kwargs(), timeout_seconds=60)

    def test_is_subclass_of_transport_error(self) -> None:
        assert issubclass(ClaudeCLITimeoutError, ClaudeTransportError)


# ---------------------------------------------------------------------------
# Empty / whitespace stdout
# ---------------------------------------------------------------------------


class TestEmptyOutput:
    def test_empty_string_raises(self) -> None:
        with patch(_SUBPROCESS_TARGET, return_value=_mock_completed("")):
            with pytest.raises(ClaudeTransportError, match="empty output"):
                invoke_claude_text(**_call_kwargs())

    def test_whitespace_only_raises(self) -> None:
        with patch(_SUBPROCESS_TARGET, return_value=_mock_completed("   \n  ")):
            with pytest.raises(ClaudeTransportError, match="empty output"):
                invoke_claude_text(**_call_kwargs())

    def test_none_stdout_raises(self) -> None:
        cp = _mock_completed("")
        cp.stdout = None
        with patch(_SUBPROCESS_TARGET, return_value=cp):
            with pytest.raises(ClaudeTransportError, match="empty output"):
                invoke_claude_text(**_call_kwargs())

    def test_includes_stderr_hint_when_available(self) -> None:
        with patch(
            _SUBPROCESS_TARGET,
            return_value=_mock_completed("", "some hint"),
        ):
            with pytest.raises(ClaudeTransportError, match="some hint"):
                invoke_claude_text(**_call_kwargs())


# ---------------------------------------------------------------------------
# Unexpected exceptions
# ---------------------------------------------------------------------------


class TestUnexpectedException:
    def test_wraps_in_transport_error(self) -> None:
        with patch(_SUBPROCESS_TARGET, side_effect=OSError("disk full")):
            with pytest.raises(ClaudeTransportError, match="disk full"):
                invoke_claude_text(**_call_kwargs())
