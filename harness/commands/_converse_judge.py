"""
The Converse assessor: a judge backend over the native Bedrock Converse API.

Why this module exists
----------------------
The private host has one model route: ``bedrock-runtime`` through PrivateLink,
spoken by :class:`~runner.transport.bedrock_converse.BedrockConverseBackend`.
The ``openai-compatible`` route cannot reach it, because Converse has no base
URL, and the ``bedrock`` preset targets the ``bedrock-mantle`` proxy, which a
host with no internet route cannot reach (handoff §9, ticket AN1a).

The judge itself is built by :func:`harness.judge_factory.build_judge` on the
``bedrock-converse`` route; this module holds the route's retry wrapper and
error.  The model-level non-drafter guard (:class:`~harness.judge.JudgeConfig`)
applies there as on every route.  On Bedrock the drafter and the assessor share a
provider, so the guard compares the model each id names
(:func:`~harness.judge.canonical_model_id`), not the id string.  A different
Claude model on the shared provider is admissible; the drafter's own model is
refused in every id form the tests list (ticket AN1c, decision record
``harness-an1c-shared-provider-independence_2026-10-15``).

What the request carries
------------------------
The pinned model, temperature 0 and the configured token limit, sent as
``modelId`` and ``inferenceConfig``.  No tool configuration is sent, and no
child process or working directory exists, so the assessor can open nothing.
:class:`ConverseRetryingBackend` records this from every request it passes on,
and the freeze requires that record (ticket AN1b).

The pin names the transport
---------------------------
A report records ``model@version`` and nothing else about the assessor.  The
factory refuses a version tag that does not contain :data:`TRANSPORT_TAG`
(spec decision 10), and it refuses an environment that resolves to any backend
other than ``bedrock_converse`` (the route's row of
:data:`harness.judge_factory.INDEPENDENCE_POLICY`).  Either would let a report
name a transport it did not speak.

Retries, not pacing
-------------------
Bedrock quotas are account-level, not the per-minute free-tier ceiling the
paced wrapper was tuned for.  The backend goes through the same
:class:`~harness.judge_factory.PacedRetryingBackend` the OpenAI-compatible
route uses, with both pacing budgets switched off, so only its retry on
retryable errors (throttling, server errors) remains.

Advisory output only.  The harness is never a runtime gate.
"""
from __future__ import annotations

from typing import Any

from harness.judge_factory import JudgeRouteError, PacedRetryingBackend

__all__ = [
    "TRANSPORT_TAG",
    "ConverseJudgeError",
    "ConverseRetryingBackend",
]

#: The transport name the command flag, the report and the version tag share.
#: ``blind_assessment.TRANSPORT_BEDROCK_CONVERSE`` repeats it rather than
#: importing it, because that command imports this module lazily.
TRANSPORT_TAG: str = "bedrock-converse"

#: The resolved backend this transport requires.
_BACKEND_NAME: str = "bedrock_converse"


class ConverseJudgeError(JudgeRouteError):
    """The Converse assessor was asked for something it cannot be.

    A :class:`~harness.judge.JudgeError` so the commands convert it to their
    fail-closed exit code rather than a traceback.
    """


class ConverseRetryingBackend(PacedRetryingBackend):
    """The retry wrapper, keeping an account of every request it passed on.

    Before each call it builds the request the inner backend will send, with
    the same builder that sends it, and notes whether that request carried a
    ``toolConfig`` and which ``inferenceConfig`` it carried.  The record is
    therefore measured from the requests, not declared from the configuration.
    """

    def __init__(self, inner: Any, **kwargs: Any) -> None:
        super().__init__(inner, **kwargs)
        self._requests = 0
        self._tool_config_sent = False
        self._inference_configs: list[dict[str, Any]] = []

    def __call__(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        # The builder is deterministic and makes no network call.
        request = self._inner._build_request(messages)
        self._requests += 1
        self._tool_config_sent = self._tool_config_sent or "toolConfig" in request
        config = dict(request.get("inferenceConfig") or {})
        if config not in self._inference_configs:
            self._inference_configs.append(config)
        return super().__call__(messages)

    def invocation_record(self) -> dict[str, Any]:
        """What the assessor could reach, for the report and the freeze.

        ``child_process`` is ``False`` by construction: Converse is an API
        call, with no process and no working directory to measure.
        ``inference_config`` is the one configuration every request carried,
        a list when they differed, and ``None`` before the first request.
        With no request sent, as in a run served wholly from a resumed
        checkpoint, ``tool_config_sent`` is measured from a probe request the
        same builder makes, so the claim is never made from silence.
        """
        configs = self._inference_configs
        if self._requests:
            tool_config_sent = self._tool_config_sent
        else:
            probe = self._inner._build_request([{"role": "user", "content": ""}])
            tool_config_sent = "toolConfig" in probe
        return {
            "tool_config_sent": tool_config_sent,
            "child_process": False,
            "requests": self._requests,
            "inference_config": (
                None if not configs else configs[0] if len(configs) == 1 else list(configs)
            ),
        }

