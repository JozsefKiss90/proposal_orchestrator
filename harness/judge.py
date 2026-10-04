"""
The independent judge — pinned, non-drafter, over the OpenAI-compatible transport (E1).

The harness's one privileged capability: an LLM-as-judge for the *semantic gap* no
deterministic predicate can reach.  Three guardrails shape it, and this module is
where they are enforced in code, not merely documented:

* **Grader/generator independence.**  The judge must be a *different* model from
  the drafter/in-run reviewer, over a *different* transport.  An in-run reviewer
  that shares the drafter's blind spots cannot be the unbiased grader of its own
  pipeline (strategy §1).  :class:`JudgeConfig` rejects any drafter model, and
  the default backend rejects the ``claude_cli`` transport, so the judge always
  speaks over the OpenAI-compatible path to a non-drafter model.
* **Pin + determinism.**  Model and version are pinned; temperature is 0.  A
  repin re-opens E1.5's advisory-only state, so both are recorded on every
  verdict's provenance.
* **No silent repair.**  A malformed judge response is a failure, not an
  auto-correctable condition (mirrors §17.6.5).  The judge raises rather than
  improvising a verdict.

Every verdict is typed :data:`~harness.verdict.EVIDENCE_TYPE_INFERRED` and, when a
:class:`~harness.provenance.ProvenanceLog` is attached, logged before it is
returned — so "provenance for every verdict" is structural, not a convention.

The judge is injectable: pass a ``backend`` callable (the
:class:`~runner.transport.tool_loop.ToolLoopBackend` shape) and no network or
``httpx`` is touched — the whole substrate is unit-testable offline.

Constitutional authority:
    Subordinate to CLAUDE.md.  Out-of-band QA substrate.  The judge never
    evaluates a gate and its output never fail-closes a run — it advises a human
    decision *about* the pipeline.  See ``harness/HARNESS.md``.
"""

from __future__ import annotations

import dataclasses
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from runner.json_extract import extract_first_json_object
from harness.provenance import ProvenanceLog, ProvenanceRecord, prompt_hash
from harness.verdict import (
    MIN_MAJORITY_SAMPLES,
    MajorityVerdict,
    Verdict,
    majority_vote,
)

__all__ = [
    "DEFAULT_JUDGE_MAX_TOKENS",
    "JudgeError",
    "JudgeConfigError",
    "JudgeIndependenceError",
    "JudgeResponseError",
    "JudgeConfig",
    "JudgeResult",
    "MajorityJudgeResult",
    "Judge",
    "drafter_models",
    "resolve_judge_config",
]

#: Default completion-token budget for a judge verdict (a bounded JSON object).
DEFAULT_JUDGE_MAX_TOKENS: int = 2048

#: Backend callable shape: ``messages -> {"content": str|None, "tool_calls": ...}``.
Backend = Callable[[list[dict[str, Any]]], dict[str, Any]]

#: Clock shape for provenance timestamps (injectable for reproducible tests).
Clock = Callable[[], str]


# --------------------------------------------------------------------------- #
# Errors
# --------------------------------------------------------------------------- #


class JudgeError(Exception):
    """Base class for judge errors."""


class JudgeConfigError(JudgeError):
    """The judge configuration is invalid (unpinned, wrong temperature, …)."""


class JudgeIndependenceError(JudgeError):
    """The judge would not be independent of the drafter (model or transport)."""


class JudgeResponseError(JudgeError):
    """The judge response was missing or malformed and was **not** repaired."""


# --------------------------------------------------------------------------- #
# Drafter models (independence guard)
# --------------------------------------------------------------------------- #


def drafter_models() -> frozenset[str]:
    """Return the models the judge must NOT be — the drafter + in-run reviewer.

    Sourced from the runtime constants (``skill_runtime.SKILL_MODEL`` and
    ``semantic_dispatch.AGENT_MODEL``) so the independence guard tracks whatever
    the pipeline actually drafts/reviews with.  Imported lazily to keep this
    module cheap to import.
    """
    from runner.semantic_dispatch import AGENT_MODEL
    from runner.skill_runtime import SKILL_MODEL

    return frozenset({SKILL_MODEL, AGENT_MODEL})


def _default_clock() -> str:
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------- #
# JudgeConfig
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class JudgeConfig:
    """Pinned judge configuration.

    Attributes
    ----------
    model:
        The judge model identifier.  Must not be a drafter model
        (:func:`drafter_models`).
    version:
        A pinned version tag (non-empty).  Recorded on every provenance record;
        changing it re-opens E1.5's advisory-only state.
    temperature:
        Must be ``0.0`` — the harness pins temp 0 and relies on the N≥3 majority
        scaffold, not sampling temperature, for robustness.
    max_tokens:
        Completion-token budget for the judge's JSON verdict.
    """

    model: str
    version: str
    temperature: float = 0.0
    max_tokens: int = DEFAULT_JUDGE_MAX_TOKENS

    def __post_init__(self) -> None:
        if not str(self.model).strip():
            raise JudgeConfigError("JudgeConfig.model must be a non-empty, pinned identifier.")
        if not str(self.version).strip():
            raise JudgeConfigError(
                "JudgeConfig.version must be a non-empty, pinned version tag — a "
                "repin re-opens the advisory-only state (E1.5)."
            )
        if self.temperature != 0.0:
            raise JudgeConfigError(
                f"JudgeConfig.temperature must be 0.0 (the harness pins temp 0 and "
                f"uses N≥{MIN_MAJORITY_SAMPLES} majority, not temperature, for "
                f"robustness); got {self.temperature!r}."
            )
        drafters = drafter_models()
        if self.model in drafters:
            raise JudgeIndependenceError(
                f"Judge model {self.model!r} is a drafter/in-run model "
                f"({sorted(drafters)}). Grader–generator independence requires a "
                f"different model as judge (strategy §1)."
            )


def resolve_judge_config() -> JudgeConfig:
    """Resolve a :class:`JudgeConfig` from the environment.

    Reads ``HARNESS_JUDGE_MODEL`` and ``HARNESS_JUDGE_VERSION`` (both required)
    and the optional ``HARNESS_JUDGE_MAX_TOKENS``.  Temperature is always 0.

    Raises
    ------
    JudgeConfigError
        If the required environment variables are absent.
    """
    model = os.environ.get("HARNESS_JUDGE_MODEL")
    version = os.environ.get("HARNESS_JUDGE_VERSION")
    if not model or not version:
        raise JudgeConfigError(
            "HARNESS_JUDGE_MODEL and HARNESS_JUDGE_VERSION must both be set to "
            "pin the independent judge (model + version). Point them at a "
            "non-drafter model reachable over the OpenAI-compatible transport."
        )
    max_tokens_raw = os.environ.get("HARNESS_JUDGE_MAX_TOKENS")
    max_tokens = int(max_tokens_raw) if max_tokens_raw else DEFAULT_JUDGE_MAX_TOKENS
    return JudgeConfig(model=model, version=version, max_tokens=max_tokens)


# --------------------------------------------------------------------------- #
# Result bundles
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class JudgeResult:
    """A single verdict plus its provenance and the raw response text."""

    verdict: Verdict
    provenance: ProvenanceRecord
    raw_response: str


@dataclass(frozen=True)
class MajorityJudgeResult:
    """An N≥3 majority verdict plus every member verdict and its provenance."""

    majority: MajorityVerdict
    verdicts: tuple[Verdict, ...]
    provenance: tuple[ProvenanceRecord, ...]
    raw_responses: tuple[str, ...]


# --------------------------------------------------------------------------- #
# Response parsing (no silent repair)
# --------------------------------------------------------------------------- #


def _verdict_from_payload(payload: dict, *, metric: str, property_key: str) -> Verdict:
    """Build a :class:`Verdict` from the default ``{passed, score, rationale}`` schema.

    Requires at least one of ``passed`` / ``score`` (a verdict with neither is
    not a judgment).  Raises :class:`JudgeResponseError` — never repairs.
    """
    passed = payload.get("passed")
    score = payload.get("score")
    rationale = payload.get("rationale", "")

    if passed is not None and not isinstance(passed, bool):
        raise JudgeResponseError(f"'passed' must be a boolean; got {passed!r}.")
    if score is not None:
        if not isinstance(score, (int, float)) or isinstance(score, bool):
            raise JudgeResponseError(f"'score' must be a number; got {score!r}.")
        score = float(score)
    if passed is None and score is None:
        raise JudgeResponseError(
            "Judge response carried neither 'passed' nor 'score' — not a verdict."
        )
    try:
        return Verdict(
            metric=metric,
            property_key=property_key,
            passed=passed,
            score=score,
            rationale=str(rationale),
        )
    except ValueError as exc:  # e.g. score out of [0,1]
        raise JudgeResponseError(str(exc)) from exc


# --------------------------------------------------------------------------- #
# Judge
# --------------------------------------------------------------------------- #


class Judge:
    """A pinned, non-drafter judge over the OpenAI-compatible transport.

    Parameters
    ----------
    config:
        A validated :class:`JudgeConfig` (pinned model+version, temp 0).
    backend:
        Optional injected backend callable (the
        :class:`~runner.transport.tool_loop.ToolLoopBackend` shape).  When
        supplied, no network or ``httpx`` is touched — the path used by tests
        and by callers that wire their own transport.  When ``None``, a real
        OpenAI-compatible backend is built lazily from
        ``resolve_provider_config()`` on first use, and a ``claude_cli`` transport
        is rejected for independence.  Note: the *transport*-independence check
        (non-``claude_cli``) applies only to the default-built backend — the
        judge cannot introspect an arbitrary injected callable's transport, so
        on the injected path transport independence is the caller's
        responsibility.  The *model*-level non-drafter guard
        (:class:`JudgeConfig`) always applies regardless of backend.
    provenance_log:
        Optional :class:`~harness.provenance.ProvenanceLog`.  When present, every
        verdict's provenance is appended before the result is returned.
    clock:
        Optional callable returning an ISO-8601 timestamp for provenance
        (injectable for reproducible tests).
    """

    def __init__(
        self,
        config: JudgeConfig,
        *,
        backend: Backend | None = None,
        provenance_log: ProvenanceLog | None = None,
        clock: Clock | None = None,
    ) -> None:
        self.config = config
        self._backend = backend
        self._provenance_log = provenance_log
        self._clock = clock or _default_clock

    @property
    def clock(self) -> Clock:
        """The timestamp source provenance records carry (read-only).

        Exposed for the same reason as :attr:`provenance_log`: a caller that
        drives :meth:`raw_invoke` for a verdict the default schema cannot carry
        (a 0-5 criterion score, say) hand-builds its provenance with the same
        clock the judge would have used, so its trail stays comparable.
        """
        return self._clock

    @property
    def provenance_log(self) -> ProvenanceLog | None:
        """The attached provenance log, if any (read-only).

        ``evaluate()`` appends to it automatically.  Exposed so callers that
        drive :meth:`raw_invoke` for a *generative* judge task (e.g. E3's
        decomposition) can hand-build their provenance into the **same** trail
        instead of silently producing none.
        """
        return self._provenance_log

    # -- transport -------------------------------------------------------- #

    def _get_backend(self) -> Backend:
        """Return the backend, building a real one from env config on first use."""
        if self._backend is not None:
            return self._backend

        from runner.transport.config import build_openai_backend, resolve_provider_config

        provider = resolve_provider_config()
        if provider.backend_name == "claude_cli":
            raise JudgeIndependenceError(
                "The independent judge requires an OpenAI-compatible transport, "
                "but the resolved backend is 'claude_cli' (the drafter transport). "
                "Set ORCHESTRATOR_TRANSPORT_PRESET / ORCHESTRATOR_TRANSPORT_BACKEND "
                "to a non-Claude backend for grader–generator independence."
            )
        # Pin the judge model authoritatively, independent of the env model.
        provider = dataclasses.replace(provider, model=self.config.model)
        self._backend = build_openai_backend(
            provider,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )
        return self._backend

    def raw_invoke(self, system_prompt: str, user_prompt: str) -> str:
        """Send one chat request and return the raw content string.

        Raises :class:`JudgeResponseError` if the backend returns no content.
        """
        backend = self._get_backend()
        result = backend(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
        )
        content = result.get("content") if isinstance(result, dict) else None
        if not content or not str(content).strip():
            raise JudgeResponseError("Judge backend returned empty content.")
        return str(content)

    # -- verdicts --------------------------------------------------------- #

    def evaluate(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        metric: str,
        property_key: str,
        sample_index: int | None = None,
    ) -> JudgeResult:
        """Produce one :class:`Verdict` (+ provenance) for a semantic property.

        The judge is expected to return a JSON object of the default schema
        ``{"passed": bool?, "score": number?, "rationale": str}`` (a metric may
        instruct a richer schema in *system_prompt*; only these keys are read).
        A malformed or empty response raises :class:`JudgeResponseError`.
        """
        raw = self.raw_invoke(system_prompt, user_prompt)
        payload = extract_first_json_object(raw)
        if payload is None:
            raise JudgeResponseError(
                f"Judge returned no parseable JSON object for {metric!r}/"
                f"{property_key!r}: {raw[:200]!r}"
            )
        verdict = _verdict_from_payload(payload, metric=metric, property_key=property_key)
        if sample_index is not None:
            verdict = dataclasses.replace(verdict, sample_index=sample_index)

        record = ProvenanceRecord.from_verdict(
            verdict,
            judge_model=self.config.model,
            judge_version=self.config.version,
            prompt_hash=prompt_hash(system_prompt, user_prompt),
            timestamp=self._clock(),
        )
        if self._provenance_log is not None:
            self._provenance_log.append(record)
        return JudgeResult(verdict=verdict, provenance=record, raw_response=raw)

    def evaluate_majority(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        metric: str,
        property_key: str,
        n: int = MIN_MAJORITY_SAMPLES,
    ) -> MajorityJudgeResult:
        """Run the judge ``n`` (≥3) times and combine via majority vote.

        The scaffold the guardrails mandate wherever a score will inform a
        decision.  Every sample's provenance is captured (and logged if a log is
        attached); the combined :class:`MajorityVerdict` is still ``Inferred``.
        """
        if n < MIN_MAJORITY_SAMPLES:
            raise ValueError(
                f"evaluate_majority requires n≥{MIN_MAJORITY_SAMPLES}; got {n}."
            )
        verdicts: list[Verdict] = []
        provenance: list[ProvenanceRecord] = []
        raws: list[str] = []
        for i in range(n):
            res = self.evaluate(
                system_prompt,
                user_prompt,
                metric=metric,
                property_key=property_key,
                sample_index=i,
            )
            verdicts.append(res.verdict)
            provenance.append(res.provenance)
            raws.append(res.raw_response)
        return MajorityJudgeResult(
            majority=majority_vote(verdicts),
            verdicts=tuple(verdicts),
            provenance=tuple(provenance),
            raw_responses=tuple(raws),
        )
