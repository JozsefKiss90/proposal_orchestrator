"""
Claude runtime transport — shared invocation adapter.

Provides a single function, :func:`invoke_claude_text`, that invokes
the local ``claude`` CLI in print mode and returns the response text.
This module is the sole runtime transport boundary for all Claude
invocations in the DAG execution path.

The ``claude`` CLI is authenticated via the user's Claude Code Max
subscription.  No Anthropic API key is required for runtime execution.

Which ``claude`` build gets spawned is pinnable through the
``ORCHESTRATOR_CLAUDE_CLI_PATH`` environment variable; see
:func:`resolve_claude_cli`.  Unpinned, the transport resolves the name on the
OS search path and logs the absolute result once, so the run record always
names the build it used.

This module is transport-only.  It has no knowledge of semantic predicate
schemas, skill result schemas, artifact paths, gate logic, or workflow
structure.  It is subordinate to CLAUDE.md but does not interpret
constitutional rules.

Authoritative source:
    CLAUDE.md §17.5 (Claude Runtime Transport Principle)
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import signal
import subprocess
import threading
import time
from typing import NamedTuple


logger = logging.getLogger(__name__)


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
#: semantics, no gate logic, and no artifact schema.
_MAX_OUTPUT_TOKENS_DEFAULT: str = "32000"

#: Environment variable the orchestrator uses to override the ceiling.
#:
#: Why a dedicated variable instead of honouring an ambient
#: ``CLAUDE_CODE_MAX_OUTPUT_TOKENS``: the transport previously applied its
#: ceiling with ``setdefault``, so any value already present in the
#: operator's shell silently won.  A shell that carries the CLI's
#: interactive default (8192) therefore capped every skill generation at a
#: quarter of the intended ceiling, and the cut surfaced far downstream as
#: an unparseable artifact — run 0395b136 ``concept-alignment-check`` was
#: cut at ~30.7k characters, roughly 8k tokens.  The override must be a
#: deliberate orchestrator setting, not an inherited accident.
_MAX_OUTPUT_TOKENS_ENV_VAR: str = "ORCHESTRATOR_MAX_OUTPUT_TOKENS"

#: The CLI's own ceiling variable, which this transport sets explicitly.
_CLI_MAX_OUTPUT_TOKENS_VAR: str = "CLAUDE_CODE_MAX_OUTPUT_TOKENS"


def _effective_max_output_tokens() -> str:
    """Return the output-token ceiling to hand the CLI.

    ``ORCHESTRATOR_MAX_OUTPUT_TOKENS`` wins when it is set to a positive
    integer; otherwise :data:`_MAX_OUTPUT_TOKENS_DEFAULT` applies.  A
    non-numeric or non-positive override is ignored with a warning rather
    than silently passed through to the CLI, where it would be rejected or
    clamped invisibly.
    """
    raw = (os.environ.get(_MAX_OUTPUT_TOKENS_ENV_VAR) or "").strip()
    if not raw:
        return _MAX_OUTPUT_TOKENS_DEFAULT
    try:
        value = int(raw)
    except ValueError:
        value = 0
    if value <= 0:
        logger.warning(
            "%s=%r is not a positive integer; using the transport default "
            "of %s output tokens.",
            _MAX_OUTPUT_TOKENS_ENV_VAR, raw, _MAX_OUTPUT_TOKENS_DEFAULT,
        )
        return _MAX_OUTPUT_TOKENS_DEFAULT
    return str(value)


#: True on Windows (``os.name == "nt"``), False on POSIX.
_IS_WINDOWS: bool = os.name == "nt"

#: Environment variable that pins the ``claude`` executable to one absolute
#: path.  Set it in ``.env`` (git-ignored, machine-specific).
#:
#: Why this exists: ``Popen(["claude", ...])`` resolves the name through the
#: OS search path, which is **not** the resolution the operator's shell
#: performs.  On the reference Windows machine the two disagreed — Python
#: resolved ``claude.EXE`` (2.1.81) while PowerShell ran ``claude.ps1``
#: (2.1.224) — so the runner silently exercised a different CLI build, with a
#: different MCP surface and a ~3-5x different per-invocation cost, from the
#: one the operator was testing at the prompt.  Pinning makes the choice
#: explicit and auditable instead of an accident of ``PATH`` and ``PATHEXT``
#: ordering.
_CLI_PATH_ENV_VAR: str = "ORCHESTRATOR_CLAUDE_CLI_PATH"

#: The command name looked up on PATH when the pin is unset.
_CLI_COMMAND_NAME: str = "claude"

#: Windows file types that ``CreateProcess`` cannot launch directly, so they
#: can never be a valid pin for a ``shell=False`` spawn.  ``.ps1`` is a
#: PowerShell *script*, not an image: it runs only through ``powershell.exe``.
#: This is the exact shim PowerShell prefers, so it is the most likely wrong
#: value for an operator to copy out of ``Get-Command claude``.
_UNSPAWNABLE_WINDOWS_SUFFIXES: tuple[str, ...] = (".ps1",)

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
# Executable resolution (TR-3)
# ---------------------------------------------------------------------------


class ClaudeCLIResolution(NamedTuple):
    """Which ``claude`` executable this process will spawn, and why.

    ``source`` is one of:

    ``"env"``
        Pinned explicitly through :data:`_CLI_PATH_ENV_VAR`.  Validated: the
        file exists and is directly spawnable.
    ``"path"``
        The pin is unset; resolved by searching the OS path.  ``path`` is
        absolute, so the run record still names the exact build used — but
        the operator's shell may resolve a *different* one.
    ``"unresolved"``
        The pin is unset and no ``claude`` was found on the search path.
        ``path`` is the bare command name; the spawn will fail and surface
        :class:`ClaudeCLIUnavailableError`.
    """

    path: str
    source: str


#: Resolved paths already announced to the log — the resolution is stable for
#: the life of the process, so it is reported once rather than per invocation.
_announced_cli_paths: set[str] = set()
_announce_lock = threading.Lock()


def resolve_claude_cli() -> ClaudeCLIResolution:
    """Resolve the ``claude`` executable to spawn, honouring the pin.

    Resolution order:

    1. :data:`_CLI_PATH_ENV_VAR`, when set to a non-empty value.  Surrounding
       whitespace and quotes are stripped (operators paste Windows paths),
       ``~`` and ``%VARS%``/``$VARS`` are expanded, and a bare command name
       (no path separator) is still resolved against the search path.  The
       result must be an existing file that the OS can spawn directly.
    2. Otherwise the search path, via :func:`shutil.which`.

    **Fail-closed on a bad pin.**  A pin that names a missing or unspawnable
    file raises :class:`ClaudeCLIUnavailableError` rather than falling back to
    the search path.  Silently running a different CLI build than the operator
    pinned is the exact failure this function exists to prevent; a typo must
    stop the run, not quietly restore the ambiguity.

    A *missing* pin is not an error: the transport keeps its historical
    behaviour so CI, POSIX and containers are unaffected.

    Raises
    ------
    ClaudeCLIUnavailableError
        The pin is set but names a missing file, an unspawnable file type, or
        a command name absent from the search path.
    """
    raw = (os.environ.get(_CLI_PATH_ENV_VAR) or "").strip()
    # Operators paste paths straight out of a shell prompt; tolerate quoting.
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in ("'", '"'):
        raw = raw[1:-1].strip()

    if not raw:
        found = shutil.which(_CLI_COMMAND_NAME)
        if found is None:
            # Preserve the historical contract: let the spawn fail and report
            # the "not found on PATH" error from one place.
            return ClaudeCLIResolution(_CLI_COMMAND_NAME, "unresolved")
        return ClaudeCLIResolution(os.path.abspath(found), "path")

    candidate = os.path.expanduser(os.path.expandvars(raw))

    # A bare command name (no separator) is a legitimate pin — "use whatever
    # this name resolves to" — but it must resolve *now*, not at spawn time.
    if os.path.basename(candidate) == candidate:
        found = shutil.which(candidate)
        if found is None:
            raise ClaudeCLIUnavailableError(
                f"{_CLI_PATH_ENV_VAR} is set to {raw!r}, which is a bare "
                "command name that is not on the search path. Set it to the "
                "absolute path of the claude executable, or unset it to let "
                "the transport search the path itself."
            )
        candidate = found

    candidate = os.path.abspath(candidate)

    if not os.path.isfile(candidate):
        raise ClaudeCLIUnavailableError(
            f"{_CLI_PATH_ENV_VAR} is set to {raw!r}, but no file exists at "
            f"{candidate!r}. The transport will not fall back to a path "
            "search: an unpinned run may silently use a different CLI build "
            "than the one you pinned. Correct the value or unset the variable."
        )

    if _IS_WINDOWS:
        suffix = os.path.splitext(candidate)[1].lower()
        if suffix in _UNSPAWNABLE_WINDOWS_SUFFIXES:
            raise ClaudeCLIUnavailableError(
                f"{_CLI_PATH_ENV_VAR} points at {candidate!r}, a {suffix} "
                "file. Windows cannot start a PowerShell script as a process "
                "image, and the transport spawns with shell=False, so this "
                "pin can never run. Pin the .cmd or .exe shim in the same "
                "directory instead (or the CLI's node entry point). "
                "tools/diag_cli_resolution.py lists every candidate on this "
                "machine with its version and whether it is spawnable."
            )

    return ClaudeCLIResolution(candidate, "env")


def _announce_cli_resolution(resolution: ClaudeCLIResolution) -> None:
    """Log the resolved executable once per distinct path, then stay quiet.

    Without this, a run's log records the *flags* of every invocation but not
    which of several installed CLI builds served them — the ambiguity that
    made the 2.1.81 / 2.1.224 split invisible.
    """
    with _announce_lock:
        if resolution.path in _announced_cli_paths:
            return
        _announced_cli_paths.add(resolution.path)

    ceiling = _effective_max_output_tokens()
    if resolution.source == "env":
        logger.info(
            "  claude CLI  pinned=%s  (%s)  max_output_tokens=%s",
            resolution.path, _CLI_PATH_ENV_VAR, ceiling,
        )
    elif resolution.source == "path":
        logger.info(
            "  claude CLI  resolved=%s  max_output_tokens=%s  (path search; "
            "%s unset — your shell may resolve a different build)",
            resolution.path,
            ceiling,
            _CLI_PATH_ENV_VAR,
        )
    else:
        logger.debug(
            "  claude CLI  unresolved: %r is not on the search path",
            _CLI_COMMAND_NAME,
        )


# ---------------------------------------------------------------------------
# stream-json response reassembly
# ---------------------------------------------------------------------------


#: Opening delimiter of a Markdown code fence.  A continuation turn that
#: begins with one is a *restart*, not a seamless token-level continuation:
#: the model re-opened its answer block and re-emitted the structure it was
#: in the middle of when the output-token ceiling cut the previous turn.
_FENCE: str = "```"

#: Maximum characters of a continuation turn's opening line used as the
#: overlap anchor when splicing a restart onto the truncated turn.  Long
#: enough to be unique inside a typical artifact, short enough to survive
#: the model re-indenting the line it restarts on.
_ANCHOR_MAX_CHARS: int = 120

#: Shortest anchor accepted for a splice.  Below this an opening line
#: (``{``, ``[``, ``",``) matches too many positions to identify a unique
#: resume point, and splicing on it would be a guess.
_ANCHOR_MIN_CHARS: int = 4


class AssistantTurn(NamedTuple):
    """One top-level assistant turn captured from stream-json output.

    Attributes
    ----------
    text:
        Concatenated text of the turn's ``text`` content blocks.
    stop_reason:
        The turn's ``message.stop_reason`` verbatim, or ``None`` when the
        CLI did not report one.  ``"max_tokens"`` marks a turn the model
        did not finish — the next turn continues it.
    """

    text: str
    stop_reason: str | None


def _splice_continuation(accumulated: str, continuation: str) -> str | None:
    """Splice a restart-style continuation onto a truncated turn.

    When an output-token cut lands inside a fenced code block, the CLI's
    auto-continuation does not resume at the exact token boundary.  The
    model re-opens a fence and re-emits from the start of whatever element
    it was writing, so the two turns *overlap*::

        turn 1 tail:  ... "coverage_status": "not_applicable",
                          "coverage_description": "CC
        turn 2 head:  ```json
                          "CC-12": {
                            "scope_element_id": "CC-12",
                            ...

    Concatenating them verbatim yields text that is not valid JSON (here a
    raw newline inside a string literal), and the artifact is lost — the
    live defect in run 0395b136 ``concept-alignment-check``.

    The overlap is removed deterministically: the continuation's opening
    line is located in the truncated turn (LAST occurrence — the model
    restarts at the element it was writing, which is the latest one), and
    the truncated turn is cut back to that point before the continuation is
    appended.  Nothing is invented, reordered, or rewritten; the result is
    exactly the text the model emitted, with the re-emitted prefix counted
    once instead of twice.

    Returns ``None`` when the continuation is not a fenced restart or no
    unambiguous anchor is found.  The caller then falls back to the
    verbatim join and the response fails closed downstream (§17.6.5 — no
    silent repair of a response the transport cannot reconstruct honestly).
    """
    body = continuation.lstrip()
    if not body.startswith(_FENCE):
        return None
    newline = body.find("\n")
    if newline == -1:
        return None
    body = body[newline + 1:]

    anchor = body.lstrip().split("\n", 1)[0].strip()[:_ANCHOR_MAX_CHARS]
    if len(anchor) < _ANCHOR_MIN_CHARS:
        return None

    cut = accumulated.rfind(anchor)
    if cut == -1:
        return None

    return accumulated[:cut].rstrip(" \t") + body.lstrip(" \t")


def _join_assistant_turns(turns: list[AssistantTurn]) -> str:
    """Join assistant turns into the complete visible response.

    Consecutive turns are joined with NO separator: a turn split mid-token
    by an output-token cut must rejoin seamlessly, and inserting a newline
    would corrupt a JSON string that continues across the split.

    The one exception is a *restart* continuation — the previous turn
    stopped on ``max_tokens`` and the next turn re-opens a code fence.
    There the two turns overlap, and a verbatim join duplicates the
    re-emitted prefix, producing text that cannot be parsed.  Such a
    boundary is spliced by :func:`_splice_continuation`; when the splice
    finds no unambiguous anchor the verbatim join stands and the caller
    fails closed downstream.
    """
    if not turns:
        return ""

    out = turns[0].text
    for index in range(1, len(turns)):
        previous = turns[index - 1]
        current = turns[index]
        spliced: str | None = None
        if previous.stop_reason == "max_tokens":
            spliced = _splice_continuation(out, current.text)
        if spliced is None:
            out += current.text
        else:
            logger.warning(
                "  transport  stream-json turn %d hit the output-token "
                "ceiling; turn %d restarted a code fence and was spliced "
                "at the overlap (%d re-emitted chars dropped). Raise "
                "CLAUDE_CODE_MAX_OUTPUT_TOKENS to avoid the cut.",
                index, index + 1,
                len(out) + len(current.text) - len(spliced),
            )
            out = spliced
    return out


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
    JSONL event.  This helper collects the text blocks of all *top-level*
    assistant events in emission order together with each turn's
    ``stop_reason``, then hands them to :func:`_join_assistant_turns`, which
    restores the complete visible response regardless of how many turns it
    spanned.  It is a faithful capture of what the model actually emitted —
    no repair, no synthesis, no reordering (§17.6.5 is untouched: a
    genuinely malformed response still fails downstream parsing and is
    reported honestly).

    ``stop_reason`` is carried because it is what distinguishes the two
    kinds of turn boundary.  A turn that ended normally (tool call, then
    more prose) is followed by a seamless continuation.  A turn that ended
    on ``max_tokens`` may be followed by a *restart*: the model re-opens a
    code fence and re-emits the element it was cut inside, so the turns
    overlap and a verbatim join corrupts the payload.  See
    :func:`_splice_continuation`.

    Returns ``None`` when *stdout* contains no recognizable stream-json
    events — the caller then falls back to treating stdout as the response
    verbatim (defensive: also keeps the transport usable against a CLI or
    test double that ignores the output-format flag).  Otherwise returns the
    joined text, possibly empty; the caller fails closed on an empty
    reassembly.
    """
    turns: list[AssistantTurn] = []
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
        stop_reason = message.get("stop_reason")
        if not isinstance(stop_reason, str):
            stop_reason = None
        texts = [
            block.get("text") or ""
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        ]
        if not texts:
            continue
        turns.append(
            AssistantTurn(text="".join(texts), stop_reason=stop_reason)
        )
    if not saw_stream_event:
        return None
    return _join_assistant_turns(turns)


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


def _child_tree_snapshot(root_pid: int) -> str:
    """Best-effort snapshot of *root_pid*'s process tree for hang diagnostics.

    Taken on the timeout path *before* the tree kill, so a recurrence of a
    pre-``main()`` child stall (TR-2) records what the stuck tree looked
    like: a bare direct child means the CLI froze at process start; live
    Node descendants mean it got further.  Must never raise and must stay
    cheap — it runs only on failures.
    """
    try:
        entries: list[tuple[int, int, str]] = []  # (pid, ppid, name)
        if _IS_WINDOWS:
            import ctypes
            import ctypes.wintypes as wt

            TH32CS_SNAPPROCESS = 0x2
            class PROCESSENTRY32(ctypes.Structure):
                _fields_ = [
                    ("dwSize", wt.DWORD),
                    ("cntUsage", wt.DWORD),
                    ("th32ProcessID", wt.DWORD),
                    ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
                    ("th32ModuleID", wt.DWORD),
                    ("cntThreads", wt.DWORD),
                    ("th32ParentProcessID", wt.DWORD),
                    ("pcPriClassBase", ctypes.c_long),
                    ("dwFlags", wt.DWORD),
                    ("szExeFile", ctypes.c_char * 260),
                ]

            k32 = ctypes.windll.kernel32
            snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
            if snap == -1:
                return "<snapshot unavailable>"
            try:
                entry = PROCESSENTRY32()
                entry.dwSize = ctypes.sizeof(PROCESSENTRY32)
                ok = k32.Process32First(snap, ctypes.byref(entry))
                while ok:
                    entries.append((
                        int(entry.th32ProcessID),
                        int(entry.th32ParentProcessID),
                        entry.szExeFile.decode(errors="replace"),
                    ))
                    ok = k32.Process32Next(snap, ctypes.byref(entry))
            finally:
                k32.CloseHandle(snap)
        else:
            out = subprocess.run(
                ["ps", "-Ao", "pid=,ppid=,comm="],
                capture_output=True, text=True, timeout=10,
            ).stdout
            for line in out.splitlines():
                parts = line.split(None, 2)
                if len(parts) == 3:
                    entries.append((int(parts[0]), int(parts[1]), parts[2]))

        # Walk descendants of root_pid (including root itself).
        by_parent: dict[int, list[tuple[int, str]]] = {}
        names: dict[int, str] = {}
        for pid, ppid, name in entries:
            by_parent.setdefault(ppid, []).append((pid, name))
            names[pid] = name
        tree: list[str] = []
        stack = [(root_pid, 0)]
        seen: set[int] = set()
        while stack and len(tree) < 32:
            pid, depth = stack.pop()
            if pid in seen:
                continue
            seen.add(pid)
            name = names.get(pid, "<gone>")
            tree.append(f"{'  ' * depth}pid={pid} {name}")
            for child_pid, _ in by_parent.get(pid, []):
                stack.append((child_pid, depth + 1))
        return "; ".join(tree) if tree else "<no live process tree>"
    except Exception:
        return "<snapshot unavailable>"


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
        The ``claude`` executable is not on PATH, or ``ORCHESTRATOR_CLAUDE_CLI_PATH``
        pins a missing or unspawnable file (see :func:`resolve_claude_cli`).
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
    #
    # cmd[0] is the *resolved* executable (TR-3), not the bare name: the OS
    # path search Popen would perform is not the resolution the operator's
    # shell performs, and the two disagreeing meant the runner silently ran a
    # different CLI build than the one being tested at the prompt.
    _cli = resolve_claude_cli()
    _announce_cli_resolution(_cli)

    cmd: list[str] = [
        _cli.path,
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
    # Assigned, not setdefault: an ambient CLAUDE_CODE_MAX_OUTPUT_TOKENS
    # inherited from the operator's shell used to win silently and cap every
    # generation at whatever that shell happened to carry.  Deliberate
    # overrides go through ORCHESTRATOR_MAX_OUTPUT_TOKENS.
    _env = os.environ.copy()
    _env[_CLI_MAX_OUTPUT_TOKENS_VAR] = _effective_max_output_tokens()

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
            f"The 'claude' CLI executable was not found on PATH ({_cli.path!r}, "
            f"source: {_cli.source}). Ensure Claude Code is installed and "
            f"available, or pin it explicitly with {_CLI_PATH_ENV_VAR}."
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
        # Snapshot the stuck tree BEFORE killing it — on a pre-main child
        # stall (TR-2) this is the only record of what the child looked like.
        _tree_snapshot = _child_tree_snapshot(proc.pid)
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
                "(pre-main startup stall — e.g. an unserviced/frozen "
                "console or a CLI startup deadlock)"
            )
        )
        raise ClaudeCLITimeoutError(
            f"Claude CLI invocation timed out after {timeout_seconds}s"
            f"{_stdin_note}. Child tree at timeout: {_tree_snapshot}",
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
