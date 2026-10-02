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
rubric prompts over the frozen evidence pack, and nothing else.
:class:`ClaudeCLIJudgeBackend` calls ``invoke_claude_text`` with ``tools=None``,
so the CLI runs in pure print mode with no ``Read`` and no ``Glob``.  The
assessor cannot open the drafting context, the assembled draft or the phase
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
(``llama-3.3-70b-versatile@groq-llama-3.3-70b@2026-08-03``).

Advisory output only.  The harness is never a runtime gate, and this module does
not change that.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable

from harness.judge import Judge, JudgeConfig, JudgeError
from harness.provenance import ProvenanceLog
from runner.claude_transport import (
    ClaudeCLIUnavailableError,
    ClaudeTransportError,
    invoke_claude_text,
)

__all__ = [
    "CLAUDE_MODEL_ALIASES",
    "ClaudeCLIJudgeBackend",
    "SubscriptionJudgeError",
    "build_subscription_judge",
    "is_claude_model_pin",
]

#: The short aliases the ``claude`` CLI accepts in place of a full model id.
CLAUDE_MODEL_ALIASES: frozenset[str] = frozenset({"sonnet", "opus", "haiku"})

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


class ClaudeCLIJudgeBackend:
    """A :class:`~runner.transport.tool_loop.ToolLoopBackend` over ``claude -p``.

    Conforms to the backend protocol the judge calls: ``(messages) -> {"content":
    str, "tool_calls": None}``.  Every invocation is tool-free print mode, which
    is what keeps the assessor blind (see the module docstring).

    Parameters
    ----------
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
        timeout_seconds: int = 300,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delay: float = DEFAULT_RETRY_DELAY,
        log: Callable[[str], None] = print,
    ) -> None:
        self.model = model
        self.max_tokens = max_tokens
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._log = log
        #: Counters for the run summary.
        self.calls = 0
        self.retries = 0

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
                    # No tools.  This is what keeps the assessor blind.
                    tools=None,
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

    Raises
    ------
    SubscriptionJudgeError
        If the pinned model is not one the ``claude`` CLI can resolve.  The
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
    backend = ClaudeCLIJudgeBackend(
        model=cfg.model,
        max_tokens=cfg.max_tokens,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
        log=log,
    )
    judge = Judge(cfg, backend=backend, provenance_log=ProvenanceLog(prov_path))
    return judge, backend
