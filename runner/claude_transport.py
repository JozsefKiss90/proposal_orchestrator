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

import json
import os
import signal
import subprocess
import threading
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


class ClaudeCLIRateLimitError(ClaudeTransportError):
    """Raised when the ``claude`` CLI refuses a call due to a usage limit.

    The Claude Code Max subscription enforces a rolling usage cap.  When it is
    reached, ``claude -p`` prints a notice such as
    ``"You've hit your limit · resets 9:20pm (Europe/Budapest)"`` **to stdout**
    (not stderr) and exits non-zero.  Without special handling this surfaces as
    a bare ``"Claude CLI exited with code 1"`` — indistinguishable from a real
    transport fault, and misleading during debugging.

    This is an environmental / account condition, not a defect in the prompt,
    the skill, or the orchestration engine.  The correct recovery is to wait
    for the quota to reset and re-run; the runtime must not retry (§17.5.4).
    Carries the notice line in ``reset_notice`` for surfacing to the operator.
    """

    def __init__(
        self,
        message: str,
        *,
        stderr: str | None = None,
        stdout: str | None = None,
        reset_notice: str | None = None,
    ) -> None:
        super().__init__(message, stderr=stderr, stdout=stdout)
        self.reset_notice = reset_notice


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

#: Output-token ceiling for Claude CLI invocations.
#:
#: Several skills must emit large single-object artifacts — e.g.
#: ``concept-alignment-check`` writes ``scope_coverage`` for every SR-xx and
#: CC-xx element with a 1-3 sentence description each, plus
#: ``topic_mapping_rationale`` for every expected outcome.  Under the CLI's
#: default ceiling such a generation is cut off, and the CLI then returns only
#: the tail of the response, so the captured text begins mid-object.  The
#: artifact is unrecoverable and the schema validator reports every required
#: field as "missing", which points at the wrong fault.
#:
#: Raising the ceiling is a transport-layer change only: it alters no skill
#: semantics, no gate logic, and no artifact schema.  An operator-supplied
#: value in the environment always wins.
_MAX_OUTPUT_TOKENS_DEFAULT: str = "32000"

#: True on Windows (``os.name == "nt"``), False on POSIX.
_IS_WINDOWS: bool = os.name == "nt"

#: Case-insensitive substrings that identify a Claude Code subscription
#: usage-limit refusal in the CLI's output.  The CLI writes this notice to
#: *stdout* and exits non-zero, so a plain "exited with code N" message hides
#: the real cause.  Matching any of these promotes the failure to a distinct,
#: self-identifying ``ClaudeCLIRateLimitError``.  Kept deliberately narrow to
#: avoid misclassifying a model that merely *discusses* rate limits in prose;
#: these phrases are CLI-emitted control notices, not response content.
_RATE_LIMIT_SIGNALS: tuple[str, ...] = (
    "hit your limit",
    "usage limit reached",
    "you've reached your limit",
    "claude usage limit",
)


def _rate_limit_notice(*texts: str | None) -> str | None:
    """Return the first line matching a usage-limit signal, else ``None``.

    Scans each supplied text (stdout, stderr) line by line and returns the
    first line containing any :data:`_RATE_LIMIT_SIGNALS` substring
    (case-insensitively), trimmed.  Used to detect subscription quota
    exhaustion and surface the human-readable reset notice verbatim.
    """
    for text in texts:
        if not text:
            continue
        for line in text.splitlines():
            low = line.lower()
            if any(sig in low for sig in _RATE_LIMIT_SIGNALS):
                return line.strip()
    return None

#: Bound on how long we wait for the process-tree kill (and the post-kill
#: pipe drain) to complete.  A forceful kill of an already-known PID returns
#: near-instantly; this is a safety ceiling, not a tuning knob.
_TREE_KILL_TIMEOUT_SECONDS: int = 10


# ---------------------------------------------------------------------------
# stream-json response reassembly
# ---------------------------------------------------------------------------


def _reassemble_stream_json(stdout: str) -> str | None:
    """Reassemble the complete assistant-visible text from stream-json output.

    ``claude -p`` in its default text output mode prints only the **final**
    assistant message of the session.  When a generation spans more than one
    assistant turn — an output-token cut that the CLI auto-continues, or a
    tool call issued after the model has begun its answer — the text of every
    earlier turn is silently dropped and the caller receives a
    **front-truncated** response (observed live three times: run 2026-07-14
    concept-alignment-check, run a79ed11e n08a, run e93b54c6 n08c
    sub-section '3.1', whose capture began mid-word at a token boundary).

    With ``--output-format stream-json`` the CLI emits every message as a
    JSONL event.  This helper concatenates the text blocks of all *top-level*
    assistant events in emission order, restoring the complete visible
    response regardless of how many turns it spanned.  It is a faithful
    capture of what the model actually emitted — no repair, no synthesis, no
    reordering (§17.6.5 is untouched: a genuinely malformed response still
    fails downstream parsing and is reported honestly).

    Returns ``None`` when *stdout* contains no recognizable stream-json
    events — the caller then falls back to treating stdout as the response
    verbatim (defensive: also keeps the transport usable against a CLI or
    test double that ignores the output-format flag).  Otherwise returns the
    concatenated text, possibly empty; the caller fails closed on an empty
    reassembly.
    """
    texts: list[str] = []
    saw_stream_event = False
    for line in stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict) or "type" not in event:
            continue
        saw_stream_event = True
        if event.get("type") != "assistant":
            continue
        # Only top-level assistant traffic is the response; a sub-agent's
        # messages (parent_tool_use_id set) belong to its parent tool call.
        if event.get("parent_tool_use_id"):
            continue
        message = event.get("message")
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                texts.append(block.get("text") or "")
    if not saw_stream_event:
        return None
    # Join with NO separator: a turn split mid-token by an output-token cut
    # must rejoin seamlessly — inserting a newline would corrupt a JSON
    # string that continues across the split (the exact defect this helper
    # exists to close).
    return "".join(texts)


# ---------------------------------------------------------------------------
# Process-tree termination (TR-1)
# ---------------------------------------------------------------------------


def _tree_killable_popen_kwargs() -> dict:
    """Platform-specific ``Popen`` kwargs that make the child tree killable.

    On POSIX, ``start_new_session=True`` runs the child in its own session and
    process group (``setsid``), so :func:`_kill_process_tree` can signal the
    whole group — including grandchildren such as the ``claude`` CLI's Node
    child — without ever reaching this process's own group (the test runner).

    On Windows this returns ``CREATE_NO_WINDOW`` (TR-2): the child gets its
    own invisible console instead of attaching to the operator's terminal.
    A child attaching to a *frozen* console (QuickEdit text selection or
    Ctrl+S in the operator's window freezes the console host) blocks before
    ``main()`` and never drains stdin — the observed multi-hour hang.  A
    detached child cannot be frozen by the operator's terminal.  ``taskkill
    /T`` walks the parent/child PID tree from the direct child's PID, so no
    process-group creation flag is required.

    The transport and its regression tests must spawn children through the
    *same* helper so the kill semantics they exercise match production.
    """
    if _IS_WINDOWS:
        return {"creationflags": subprocess.CREATE_NO_WINDOW}
    return {"start_new_session": True}


def _kill_process_tree(proc: subprocess.Popen) -> None:
    """Forcibly terminate *proc* and its entire descendant process tree.

    Python's own timeout handling (``subprocess.run(timeout=...)`` internally,
    or a bare ``proc.kill()``) terminates only the *direct* child.  On both
    platforms that leaves the ``claude`` CLI's Node child tree orphaned and
    running — the ~2h "stalled" hang this fix (TR-1) closes.

    This is a best-effort, exception-swallowing teardown: a failure to kill
    must never mask the timeout error that motivated the kill.  It is a no-op
    if *proc* has already exited (guarding the PID-reuse window: we only kill
    a PID we still hold and have not reaped).
    """
    if proc.poll() is not None:
        return  # already exited — nothing to kill, and its PID may be reused

    if _IS_WINDOWS:
        # /T terminates the process and every descendant; /F forces it.
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                capture_output=True,
                timeout=_TREE_KILL_TIMEOUT_SECONDS,
                shell=False,
            )
            return
        except Exception:
            # Fall through to a direct-child kill as a last resort.
            pass
    else:
        # The child leads its own process group (start_new_session=True);
        # signal the whole group so grandchildren die with it.
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            return
        except (ProcessLookupError, PermissionError, OSError):
            # Process/group already gone, or not permitted — fall through.
            pass

    try:
        proc.kill()
    except Exception:
        pass


def _drain_after_kill(
    proc: subprocess.Popen,
) -> tuple[str | None, str | None]:
    """Drain and reap *proc* after a tree kill; return any buffered output.

    Once the tree is dead the pipes hit EOF, so this returns promptly.  It is
    called only from failure paths and must never raise: a drain failure must
    not mask the timeout/transport error being surfaced.
    """
    try:
        return proc.communicate(timeout=_TREE_KILL_TIMEOUT_SECONDS)
    except Exception:
        return None, None


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
        Model identifier: either a full id or a short alias
        (e.g. ``"claude-sonnet-4-6"`` or ``"sonnet"``).  The transport is
        model-agnostic; callers supply the model.
    max_tokens:
        Accepted for interface compatibility but **not currently enforced**
        by the ``claude -p`` CLI transport.  The ``claude`` CLI does not
        expose a ``--max-tokens`` flag; response length is determined by
        the model's own completion behavior.  Callers should not rely on
        this parameter to bound output size.  Output bounding is achieved
        through prompt design (output minimization rules in skill specs),
        not through transport-level token caps.
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
        The complete assistant response text, reassembled from the CLI's
        stream-json events across ALL assistant turns of the session (a
        generation split across turns — output-token cut with auto-continue,
        or a mid-answer tool call — is captured whole, not tail-only).  When
        stdout carries no stream-json events, the raw stdout is returned
        verbatim.

    Raises
    ------
    ClaudeCLIUnavailableError
        The ``claude`` executable is not on PATH.
    ClaudeCLITimeoutError
        The invocation exceeded *timeout_seconds*.
    ClaudeTransportError
        Non-zero exit code, empty stdout, or other transport failure.
    """
    # Build the command.  stream-json output (which requires --verbose in
    # print mode) lets the transport reassemble the FULL assistant response
    # from every turn of the session; the default text mode prints only the
    # final assistant message, which front-truncates any generation that
    # spans turns (see _reassemble_stream_json).
    cmd: list[str] = [
        "claude",
        "-p",
        "--model", model,
        "--output-format", "stream-json",
        "--verbose",
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

    # Raise the CLI's output-token ceiling so that large single-object
    # artifacts are not cut off mid-generation (see _MAX_OUTPUT_TOKENS_DEFAULT).
    # An operator-supplied value always takes precedence.
    _env = os.environ.copy()
    _env.setdefault("CLAUDE_CODE_MAX_OUTPUT_TOKENS", _MAX_OUTPUT_TOKENS_DEFAULT)

    # Use Popen (not subprocess.run) so that on timeout we still hold a handle
    # to the child and can kill its *entire* process tree.  subprocess.run's
    # internal timeout path kills only the direct child, orphaning the claude
    # CLI's Node grandchild (TR-1).  Popen.communicate(timeout=...) does not
    # auto-kill on timeout, which is exactly what lets us tree-kill ourselves.
    _t0 = time.monotonic()
    try:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            shell=False,
            env=_env,
            **_tree_killable_popen_kwargs(),
        )
    except FileNotFoundError:
        raise ClaudeCLIUnavailableError(
            "The 'claude' CLI executable was not found on PATH. "
            "Ensure Claude Code is installed and available."
        )
    except Exception as exc:
        # Spawn failed for some other reason (e.g. OSError); preserve the
        # original contract of wrapping unexpected failures.
        raise ClaudeTransportError(
            f"Claude CLI invocation failed: {type(exc).__name__}: {exc}"
        ) from exc

    # TR-2: write stdin from a daemon thread so the deadline below is
    # unconditional.  ``communicate(input=...)`` writes stdin synchronously
    # on the calling thread *before* any deadline check (CPython Windows
    # ``_communicate``); a child that stalls before reading input (e.g.
    # startup blocked by a frozen console) never drains the pipe, the write
    # blocks forever, and ``TimeoutExpired`` becomes structurally
    # unreachable.
    _stdin_done = threading.Event()
    _stdin_pipe = proc.stdin

    def _feed_stdin() -> None:
        try:
            _stdin_pipe.write(effective_user_prompt)
            _stdin_pipe.close()
            _stdin_done.set()
        except OSError:
            # Child exited or was tree-killed before draining stdin; the
            # main thread surfaces the real error.
            pass

    _writer = threading.Thread(
        target=_feed_stdin, name="claude-stdin-writer", daemon=True
    )
    _writer.start()
    # communicate() must not close or flush the pipe the writer thread owns.
    proc.stdin = None

    try:
        stdout, stderr = proc.communicate(timeout=timeout_seconds)
        _writer.join(timeout=5)
    except subprocess.TimeoutExpired as exc:
        _elapsed = time.monotonic() - _t0
        # Kill the whole tree (the direct child *and* its Node descendants),
        # then drain any buffered output so the child is reaped and no pipe
        # readers are left dangling.
        _kill_process_tree(proc)
        _drained_out, _drained_err = _drain_after_kill(proc)
        _to_out = exc.stdout if isinstance(exc.stdout, str) else _drained_out
        _to_err = exc.stderr if isinstance(exc.stderr, str) else _drained_err
        _stdin_note = (
            ""
            if _stdin_done.is_set()
            else (
                ". The user prompt was never fully written to the CLI's "
                "stdin: the child stalled before reading its input pipe "
                "(e.g. startup blocked by a frozen console — QuickEdit text "
                "selection or Ctrl+S in the operator's terminal)"
            )
        )
        raise ClaudeCLITimeoutError(
            f"Claude CLI invocation timed out after {timeout_seconds}s"
            f"{_stdin_note}",
            stdout=_to_out if isinstance(_to_out, str) else None,
            stderr=_to_err if isinstance(_to_err, str) else None,
            command=cmd,
            timeout_seconds=timeout_seconds,
            elapsed_seconds=round(_elapsed, 3),
        )
    except Exception as exc:
        # Any other communication failure: make sure we don't leak the child
        # (or its tree) before surfacing the error.
        _kill_process_tree(proc)
        _drain_after_kill(proc)
        raise ClaudeTransportError(
            f"Claude CLI invocation failed: {type(exc).__name__}: {exc}"
        ) from exc

    returncode = proc.returncode
    if returncode != 0:
        # A subscription usage-limit refusal is written to *stdout* and exits
        # non-zero.  Detect it first so it surfaces as a distinct, actionable
        # error instead of a bare "exited with code N" (the notice is not on
        # stderr, so the generic path below would hide it).
        _notice = _rate_limit_notice(stdout, stderr)
        if _notice is not None:
            raise ClaudeCLIRateLimitError(
                "Claude CLI refused the call: Claude Code subscription usage "
                f"limit reached ({_notice}). This is an account/quota condition, "
                "not a prompt or engine defect; wait for the reset and re-run.",
                stderr=stderr,
                stdout=stdout,
                reset_notice=_notice,
            )
        # Generic non-zero exit.  stderr is preferred for the message, but when
        # it is empty the CLI often writes its diagnostic to stdout — include a
        # stdout snippet so the failure is not blind in the run manifest.
        stderr_snippet = (stderr or "").strip()[:500]
        stdout_snippet = (stdout or "").strip()[:500]
        detail = stderr_snippet or stdout_snippet
        raise ClaudeTransportError(
            f"Claude CLI exited with code {returncode}"
            + (f": {detail}" if detail else ""),
            stderr=stderr,
            stdout=stdout,
        )

    if not stdout or not stdout.strip():
        raise ClaudeTransportError(
            "Claude CLI returned empty output"
            + (
                f" (stderr: {(stderr or '').strip()[:300]})"
                if stderr
                else ""
            ),
            stderr=stderr,
            stdout=stdout,
        )

    reassembled = _reassemble_stream_json(stdout)
    if reassembled is None:
        # Not stream-json output (a CLI or test double that ignored the
        # flag): the raw stdout IS the response, exactly as before.
        return stdout
    if not reassembled.strip():
        raise ClaudeTransportError(
            "Claude CLI stream-json output contained no assistant text"
            + (
                f" (stderr: {(stderr or '').strip()[:300]})"
                if stderr
                else ""
            ),
            stderr=stderr,
            stdout=stdout,
        )
    return reassembled
