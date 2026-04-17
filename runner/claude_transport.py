"""
Claude runtime transport — shared invocation adapter.

Provides a single function, :func:`invoke_claude_text`, that invokes
the local ``claude`` CLI in print mode and returns the response text.
This module is the sole runtime transport boundary for all Claude
invocations in the DAG execution path.

The ``claude`` CLI is authenticated via the user's Claude Code Max
subscription.  No Anthropic API key is required for runtime execution.

This module is transport-only.  It has no knowledge of semantic predicate
schemas, skill result schemas, artifact paths, gate logic, or workflow
structure.  It is subordinate to CLAUDE.md but does not interpret
constitutional rules.

Authoritative source:
    CLAUDE.md §17.5 (Claude Runtime Transport Principle)
"""

from __future__ import annotations

import subprocess
import time


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ClaudeTransportError(Exception):
    """Base exception for Claude CLI transport failures.

    Raised when the ``claude`` CLI returns a non-zero exit code,
    produces unusable output, or encounters an unexpected runtime error.

    Carries optional structured ``stderr`` and ``stdout`` fields so that
    callers can write rich diagnostic bundles without re-parsing exception
    messages.
    """

    def __init__(
        self,
        message: str,
        *,
        stderr: str | None = None,
        stdout: str | None = None,
    ) -> None:
        super().__init__(message)
        self.stderr = stderr
        self.stdout = stdout


class ClaudeCLIUnavailableError(ClaudeTransportError):
    """Raised when the ``claude`` executable cannot be found."""


class ClaudeCLITimeoutError(ClaudeTransportError):
    """Raised when a ``claude`` CLI invocation exceeds the timeout.

    Carries structured diagnostic fields so that callers can write rich
    timeout diagnostic bundles without re-parsing exception messages.
    """

    def __init__(
        self,
        message: str,
        *,
        stdout: str | None = None,
        stderr: str | None = None,
        command: list[str] | None = None,
        timeout_seconds: int | None = None,
        elapsed_seconds: float | None = None,
    ) -> None:
        super().__init__(message, stderr=stderr, stdout=stdout)
        self.command = command
        self.timeout_seconds = timeout_seconds
        self.elapsed_seconds = elapsed_seconds


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Default timeout for Claude CLI invocations (seconds).
#: Skill invocations may produce large responses; 5 minutes is generous.
DEFAULT_TIMEOUT_SECONDS: int = 300

#: Maximum safe length for the --system-prompt CLI argument (characters).
#: On Windows, CreateProcess limits the command line to ~32,767 chars.
#: We use a conservative threshold to leave room for other arguments.
_MAX_SYSTEM_PROMPT_CLI_LENGTH: int = 24_000


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def invoke_claude_text(
    *,
    system_prompt: str,
    user_prompt: str,
    model: str,
    max_tokens: int,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    tools: list[str] | None = None,
) -> str:
    """Invoke the local ``claude`` CLI in print mode and return response text.

    Parameters
    ----------
    system_prompt:
        System prompt text.  Passed via ``--system-prompt`` CLI flag when
        short enough; embedded in the user prompt with clear delimitation
        when the flag would exceed safe OS command-line limits.
    user_prompt:
        User prompt text.  Always passed via stdin.
    model:
        Model identifier (e.g. ``"claude-sonnet-4-6"`` or ``"sonnet"``).
    max_tokens:
        Maximum tokens for the response.
    timeout_seconds:
        Maximum wall-clock seconds to wait for the CLI to complete.
    tools:
        Optional list of tool names to make available to Claude during
        execution (e.g. ``["Read", "Glob"]``).  When provided with a
        non-empty list, appends ``--tools <comma-joined>`` to the CLI
        command.  When ``None`` (default) or empty, no ``--tools`` flag
        is added and Claude operates in pure print mode.

    Returns
    -------
    str
        The raw response text from Claude (stdout).

    Raises
    ------
    ClaudeCLIUnavailableError
        The ``claude`` executable is not on PATH.
    ClaudeCLITimeoutError
        The invocation exceeded *timeout_seconds*.
    ClaudeTransportError
        Non-zero exit code, empty stdout, or other transport failure.
    """
    # Build the command
    cmd: list[str] = [
        "claude",
        "-p",
        "--model", model
    ]

    # Append --tools flag when tools are specified.
    if tools:
        cmd.extend(["--tools", ",".join(tools)])

    # Determine how to pass the system prompt.
    # When the system prompt fits within safe OS command-line limits, pass
    # it via --system-prompt.  When it exceeds the threshold, embed it in
    # the user prompt with clear delimitation as a fallback.
    effective_user_prompt = user_prompt
    if len(system_prompt) <= _MAX_SYSTEM_PROMPT_CLI_LENGTH:
        cmd.extend(["--system-prompt", system_prompt])
    else:
        effective_user_prompt = (
            "=== SYSTEM INSTRUCTIONS (embedded due to length) ===\n"
            + system_prompt
            + "\n=== END SYSTEM INSTRUCTIONS ===\n\n"
            + user_prompt
        )

    _t0 = time.monotonic()
    try:
        completed = subprocess.run(
            cmd,
            input=effective_user_prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout_seconds,
            shell=False,
        )
    except FileNotFoundError:
        raise ClaudeCLIUnavailableError(
            "The 'claude' CLI executable was not found on PATH. "
            "Ensure Claude Code is installed and available."
        )
    except subprocess.TimeoutExpired as exc:
        _elapsed = time.monotonic() - _t0
        raise ClaudeCLITimeoutError(
            f"Claude CLI invocation timed out after {timeout_seconds}s",
            stdout=exc.stdout if isinstance(exc.stdout, str) else None,
            stderr=exc.stderr if isinstance(exc.stderr, str) else None,
            command=cmd,
            timeout_seconds=timeout_seconds,
            elapsed_seconds=round(_elapsed, 3),
        )
    except Exception as exc:
        raise ClaudeTransportError(
            f"Claude CLI invocation failed: {type(exc).__name__}: {exc}"
        ) from exc

    if completed.returncode != 0:
        stderr_snippet = (completed.stderr or "").strip()[:500]
        raise ClaudeTransportError(
            f"Claude CLI exited with code {completed.returncode}"
            + (f": {stderr_snippet}" if stderr_snippet else ""),
            stderr=completed.stderr,
            stdout=completed.stdout,
        )

    stdout = completed.stdout
    if not stdout or not stdout.strip():
        raise ClaudeTransportError(
            "Claude CLI returned empty output"
            + (
                f" (stderr: {(completed.stderr or '').strip()[:300]})"
                if completed.stderr
                else ""
            ),
            stderr=completed.stderr,
            stdout=completed.stdout,
        )

    return stdout
