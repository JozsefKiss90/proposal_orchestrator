"""
The subscription assessor: a judge backend over the local ``claude`` CLI.

Why this module exists
----------------------
``Judge._get_backend`` refuses the ``claude_cli`` transport, and
``build_paced_judge`` refuses it again — grader–generator independence
(strategy §1).  Both refusals govern the **default-built** backend.  ``Judge``
documents the *injected* backend as the seam for "callers that wire their own
transport", and states that on that path transport independence is the caller's
responsibility.  This module is such a caller.  What follows discharges that
responsibility by stating exactly which axes of independence survive and which
do not.

What independence survives
--------------------------
**Model — preserved.**  ``JudgeConfig`` refuses every model in
``drafter_models()``, which it reads live from ``SKILL_MODEL`` and
``AGENT_MODEL``.  The assessor therefore can never be the model that drafted
the sections under assessment.  :func:`build_subscription_judge` builds through
``JudgeConfig``, so that guard is not bypassed here.

**Context — preserved, and the blind lane rests on it.**  The assessor sees the
rubric prompts over the frozen evidence pack, and nothing else.  Two controls
make that true, and both are tested at the level of the child process rather
than of this module (``tests/harness/test_subscription_judge.py``):

* :class:`ClaudeCLIJudgeBackend` calls ``invoke_claude_text`` with the
  explicit empty tool list (``NO_TOOLS``), which the transport renders as
  ``--tools "" --strict-mcp-config``.  ``tools=None`` is **not** that: it
  omits the flag and leaves the CLI's built-in tools live.  Measured
  2026-10-04, a no-flag assessor asked to read ``./CLAUDE.md`` did so; with
  ``--tools ""`` it answered ``NO_TOOLS``.  Measured 2026-10-05, ``--tools ""``
  alone still listed the operator's MCP servers, a filesystem reader among
  them; ``--strict-mcp-config`` with no ``--mcp-config`` left the tool list
  empty.  (Spec §2.13 and decision 12.)
* The child runs in a fresh, empty **working directory outside the
  repository**.  ``Popen`` otherwise inherits the harness's directory, which
  is the repository root where the historical evaluation lives.

The assessor cannot open the drafting context, the assembled draft or the phase
outputs, because it cannot open anything.  A tool-enabled assessor would not be
blind, and would stop being an assessor without saying so.

What independence does not survive
----------------------------------
**Transport — not preserved.**  The assessor speaks the transport the pipeline
drafts over.

**Vendor and family — not preserved.**  A same-family assessor shares the
drafter's training lineage and stylistic priors.  It is a weaker check on
phrasing, and on claims that a sibling model finds self-evident, than a
different-family assessor is.

A report produced through this backend must say so.  The ``model@version`` pin
is where it says it: set ``HARNESS_JUDGE_VERSION`` to a tag naming the
transport, following the convention the Groq pin already uses
(``llama-3.3-70b-versatile@groq-llama-3.3-70b@2026-08-03``).  The builder
refuses a version tag that does not contain :data:`TRANSPORT_TAG` (spec
decision 10), so a report cannot carry this transport under another name.

Advisory output only.  The harness is never a runtime gate, and this module does
not change that.
"""
from __future__ import annotations

import tempfile
import time
from pathlib import Path
from typing import Any, Callable

from harness.judge import Judge, JudgeConfig, JudgeError
from harness.provenance import ProvenanceLog
from runner.claude_transport import (
    NO_TOOLS,
    ClaudeCLIUnavailableError,
    ClaudeTransportError,
    invoke_claude_text,
)
from runner.paths import find_repo_root

__all__ = [
    "CLAUDE_MODEL_ALIASES",
    "TRANSPORT_TAG",
    "ClaudeCLIJudgeBackend",
    "SubscriptionJudgeError",
    "assessor_working_dir",
    "build_subscription_judge",
    "is_claude_model_pin",
]

#: The short aliases the ``claude`` CLI accepts in place of a full model id.
CLAUDE_MODEL_ALIASES: frozenset[str] = frozenset({"sonnet", "opus", "haiku"})

#: The token a version tag must carry to name this transport.  Matches the
#: command's ``--transport`` choice (``harness.commands.blind_assessment.
#: TRANSPORT_CLAUDE_CLI``); kept as a literal here so this module does not
#: import the command that imports it.
TRANSPORT_TAG: str = "claude-cli"

#: Prefix of the fresh working directory the assessor child runs in.
_WORKING_DIR_PREFIX: str = "blind_assessor_"

#: Default retries on a transport failure.  The assessor writes nothing until
#: every cell is graded, so one dropped subprocess would otherwise discard the
#: whole run.
DEFAULT_MAX_RETRIES: int = 2

#: Seconds to wait before the first retry; doubled on each subsequent one.
DEFAULT_RETRY_DELAY: float = 5.0


class SubscriptionJudgeError(JudgeError):
    """The subscription assessor was asked for something it cannot be.

    A :class:`~harness.judge.JudgeError` so the commands convert it to their
    fail-closed exit code rather than a traceback.
    """


def is_claude_model_pin(model: str) -> bool:
    """Return whether *model* is something the ``claude`` CLI can resolve.

    A guard against pointing the subscription transport at the Groq pin left in
    ``.env.harness``: the CLI would fail per call, 18 times, with an error about
    an unknown model rather than about a mismatched pin.
    """
    name = str(model).strip().lower()
    return name.startswith("claude") or name in CLAUDE_MODEL_ALIASES


def _resolve_repo_root(repo_root: Path | None) -> Path:
    return (repo_root if repo_root is not None else find_repo_root()).resolve()


def _check_working_dir(working_dir: Path, repo_root: Path) -> Path:
    """Return *working_dir* resolved, or raise when the child could see the repository."""
    resolved = Path(working_dir).resolve()
    if not resolved.is_dir():
        raise SubscriptionJudgeError(
            f"the assessor working directory does not exist: {resolved}"
        )
    if resolved.is_relative_to(repo_root):
        raise SubscriptionJudgeError(
            f"the assessor working directory {resolved} lies inside the repository "
            f"{repo_root}; the child must run where the repository is not reachable "
            "by path (spec decision 12)."
        )
    return resolved


def assessor_working_dir(repo_root: Path | None = None) -> Path:
    """Create and return a fresh, empty directory outside the repository.

    The system temporary directory is used; it is refused if it turns out to
    lie inside *repo_root* (an operator with ``TMPDIR`` pointed into the
    checkout), because the control would then be a name only.
    """
    root = _resolve_repo_root(repo_root)
    created = Path(tempfile.mkdtemp(prefix=_WORKING_DIR_PREFIX))
    return _check_working_dir(created, root)


class ClaudeCLIJudgeBackend:
    """A :class:`~runner.transport.tool_loop.ToolLoopBackend` over ``claude -p``.

    Conforms to the backend protocol the judge calls: ``(messages) -> {"content":
    str, "tool_calls": None}``.  Every invocation is tool-free print mode in a
    working directory outside the repository, which is what keeps the assessor
    blind (see the module docstring).

    Parameters
    ----------
    working_dir:
        The directory the ``claude`` child runs in.  Must exist and must lie
        outside *repo_root*; :func:`assessor_working_dir` makes one.
    repo_root:
        The repository the child must not reach.  Default: the root found from
        the current directory.
    model:
        The assessor model.  A full id or a CLI alias.  Pinned by
        :class:`JudgeConfig`, never read from the environment here.
    max_tokens:
        Carried for interface parity.  ``claude -p`` exposes no token cap, so
        the transport documents this as unenforced; the rubric prompts bound
        the response by asking for one JSON object.
    timeout_seconds:
        Per-call wall-clock limit handed to the transport.
    max_retries:
        Retries on :class:`ClaudeTransportError` (timeouts included).  Two
        failures are never retried: a malformed *response*, because the judge
        raises on that and silently resampling a bad verdict would corrupt the
        majority vote; and :class:`ClaudeCLIUnavailableError`, because a CLI
        that is absent from PATH will still be absent in five seconds.
    log:
        Progress sink.  The operator watches 18 subprocesses; silence reads as
        a hang.
    """

    def __init__(
        self,
        *,
        model: str,
        max_tokens: int,
        working_dir: Path,
        repo_root: Path | None = None,
        timeout_seconds: int = 300,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delay: float = DEFAULT_RETRY_DELAY,
        log: Callable[[str], None] = print,
    ) -> None:
        self.repo_root = _resolve_repo_root(repo_root)
        self.working_dir = _check_working_dir(working_dir, self.repo_root)
        self.model = model
        self.max_tokens = max_tokens
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._log = log
        #: Counters for the run summary.
        self.calls = 0
        self.retries = 0

    def invocation_record(self) -> dict[str, Any]:
        """What the child process could reach, for a report or a log line."""
        return {
            "tools": "",
            "strict_mcp_config": True,
            "working_directory": str(self.working_dir),
            "working_directory_outside_repository": not self.working_dir.is_relative_to(
                self.repo_root
            ),
        }

    @staticmethod
    def _join(messages: list[dict[str, Any]], role: str) -> str:
        return "\n\n".join(
            str(m.get("content") or "")
            for m in messages
            if m.get("role") == role and m.get("content")
        )

    def __call__(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        system_prompt = self._join(messages, "system")
        user_prompt = self._join(messages, "user")
        if not user_prompt.strip():
            raise SubscriptionJudgeError(
                "the assessor was handed no user prompt; the rubric prompt "
                "builder is the only thing that should call this backend."
            )

        delay = self.retry_delay
        for attempt in range(self.max_retries + 1):
            try:
                text = invoke_claude_text(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    model=self.model,
                    max_tokens=self.max_tokens,
                    timeout_seconds=self.timeout_seconds,
                    # The explicit empty list, never None: None omits --tools and
                    # leaves the built-in set live.  Rendered by the transport as
                    # --tools "" --strict-mcp-config.  With the working directory
                    # outside the repository, this is what keeps the assessor blind.
                    tools=NO_TOOLS,
                    cwd=self.working_dir,
                )
            except ClaudeCLIUnavailableError:
                # Not retryable: the CLI is not on PATH, or the pinned path is
                # unspawnable.  Waiting changes neither.
                raise
            except ClaudeTransportError as exc:
                if attempt >= self.max_retries:
                    raise
                self.retries += 1
                self._log(
                    f"    transport failure ({type(exc).__name__}, attempt "
                    f"{attempt + 1}/{self.max_retries}) — waiting {delay:.0f}s "
                    f"then retrying"
                )
                time.sleep(delay)
                delay *= 2
                continue
            self.calls += 1
            self._log(f"    assessor call {self.calls} returned {len(text)} chars")
            return {"content": text, "tool_calls": None}
        raise SubscriptionJudgeError(
            "unreachable: the retry loop exited without returning or raising"
        )


def build_subscription_judge(
    cfg: JudgeConfig,
    *,
    prov_path: Path,
    repo_root: Path | None = None,
    working_dir: Path | None = None,
    timeout_seconds: int = 300,
    max_retries: int = DEFAULT_MAX_RETRIES,
    log: Callable[[str], None] = print,
) -> tuple[Judge, ClaudeCLIJudgeBackend]:
    """Build a judge that speaks the Max subscription, with its pin recorded.

    Mirrors :func:`~harness.commands.freeze_grounding_baselines.build_paced_judge`
    in shape and return value, and differs in exactly one way: the backend is
    the ``claude`` CLI rather than an OpenAI-compatible endpoint.  No pacing
    wrapper — there is no TPM or RPM cap to pace against, and the calls are
    sequential subprocesses.

    *working_dir* defaults to a fresh directory from :func:`assessor_working_dir`.

    Raises
    ------
    SubscriptionJudgeError
        If the pinned model is not one the ``claude`` CLI can resolve; if the
        version tag does not name this transport (:data:`TRANSPORT_TAG`); or if
        the working directory is missing or lies inside the repository.  The
        drafter-model guard is :class:`JudgeConfig`'s and has already run by the
        time *cfg* exists.
    """
    if not is_claude_model_pin(cfg.model):
        raise SubscriptionJudgeError(
            f"HARNESS_JUDGE_MODEL is {cfg.model!r}, which the 'claude' CLI "
            f"cannot resolve. The subscription assessor needs a Claude pin "
            f"(e.g. 'claude-sonnet-5'); the Groq pin belongs to the "
            f"OpenAI-compatible transport."
        )
    if TRANSPORT_TAG not in str(cfg.version):
        raise SubscriptionJudgeError(
            f"HARNESS_JUDGE_VERSION is {cfg.version!r}, which does not name this "
            f"transport. The report records model@version and nothing else about "
            f"the assessor, so the tag must contain {TRANSPORT_TAG!r} (e.g. "
            f"'claude-cli-subscription@2026-10-05'); pass --assessor-version."
        )
    root = _resolve_repo_root(repo_root)
    backend = ClaudeCLIJudgeBackend(
        model=cfg.model,
        max_tokens=cfg.max_tokens,
        working_dir=working_dir if working_dir is not None else assessor_working_dir(root),
        repo_root=root,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
        log=log,
    )
    log(
        f"    assessor child: tools disabled (--tools \"\" --strict-mcp-config), "
        f"working directory {backend.working_dir}"
    )
    judge = Judge(cfg, backend=backend, provenance_log=ProvenanceLog(prov_path))
    return judge, backend
