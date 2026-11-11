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
  auto-correctable condition (mirrors §17.6.5).  :meth:`Judge.ask`, the one
  call path, discards it and draws again over the identical prompt within a
  bounded budget, records every discarded draw, and then raises rather than
  improvising a value.  Re-asking is not repairing.

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
import hashlib
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Generic, Protocol, TypeVar

from runner.json_extract import extract_first_json_object
from runner.model_ids import canonical_model_id
from harness.provenance import ProvenanceLog, ProvenanceRecord, prompt_hash
from harness.response_cache import ResponseCache
from harness.verdict import (
    MIN_MAJORITY_SAMPLES,
    MajorityVerdict,
    Verdict,
    majority_vote,
)

__all__ = [
    "DEFAULT_JUDGE_MAX_TOKENS",
    "DEFAULT_MAX_REDRAWS",
    "JudgeError",
    "JudgeConfigError",
    "JudgeIndependenceError",
    "JudgeResponseError",
    "JudgeConfig",
    "Judged",
    "DiscardedDraw",
    "JudgeAnswer",
    "JudgeResult",
    "MajorityJudgeResult",
    "Judge",
    "build_judge_backend",
    "canonical_model_id",
    "drafter_models",
    "parse_verdict",
    "resolve_judge_config",
]

#: Default completion-token budget for a judge verdict (a bounded JSON object).
DEFAULT_JUDGE_MAX_TOKENS: int = 2048

#: Extra draws the judge allows one ask whose response will not parse: three
#: draws in all.  One stray character in an otherwise sound answer is worth a
#: second ask (a trailing comma cost a 45-call run at call 44 on 2026-10-06);
#: a judge that cannot produce the schema three times running is not having an
#: accident, and the ask then fails closed with the parser's message.
DEFAULT_MAX_REDRAWS: int = 2

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


def _production_mode() -> bool:
    """``ORCHESTRATOR_PRODUCTION_MODE`` is ``true`` (case-insensitive).

    The same rule as ``runner.transport.config.is_production_mode``, read here
    without importing that module, whose import loads ``.env``.
    """
    return os.environ.get("ORCHESTRATOR_PRODUCTION_MODE", "").lower() == "true"


def drafter_models() -> frozenset[str]:
    """Return the models the judge must NOT be — the drafter + in-run reviewer.

    Sourced from the runtime constants (``skill_runtime.SKILL_MODEL`` and
    ``semantic_dispatch.AGENT_MODEL``) so the independence guard tracks whatever
    the pipeline actually drafts/reviews with.  Imported lazily to keep this
    module cheap to import.

    Under ``ORCHESTRATOR_PRODUCTION_MODE=true`` (the private host, started
    through ``runner.host_env``) the pipeline drafts through the transport
    with ``ORCHESTRATOR_TRANSPORT_MODEL`` from the runtime secret, so that
    model is a drafter too (AN1c; decision records
    ``aws-redeployment-od7-model-set_2026-10-21`` OD7-assessor and
    ``aws-redeployment-r9e-eu-region_2026-10-27``).  Outside production mode
    the variable is not read: on the workstation ``.env.harness`` puts the
    *judge's* model there, and counting it would make every workstation judge
    fail its own independence check.
    """
    from runner.semantic_dispatch import AGENT_MODEL
    from runner.skill_runtime import SKILL_MODEL

    models = {SKILL_MODEL, AGENT_MODEL}
    if _production_mode():
        transport_model = os.environ.get("ORCHESTRATOR_TRANSPORT_MODEL", "").strip()
        if transport_model:
            models.add(transport_model)
    return frozenset(models)


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
        The judge model identifier.  Must not name a drafter model
        (:func:`drafter_models`) in any form, compared by
        :func:`canonical_model_id`.
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
        # By the model named, not the string: on Bedrock one model has several
        # ids, and the drafter and the assessor share the provider (AN1c).
        if canonical_model_id(self.model) in {canonical_model_id(d) for d in drafters}:
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
# Backend construction
# --------------------------------------------------------------------------- #


def build_judge_backend(provider: Any, config: JudgeConfig) -> Backend:
    """Build the real judge backend for a resolved provider configuration.

    The judge model is pinned authoritatively from *config*, whatever model
    the environment names.  Temperature and the token limit come from *config*
    too.  A ``bedrock_converse`` provider builds the native Converse backend,
    which needs no base URL (AN1a); every other non-CLI provider builds the
    OpenAI-compatible HTTP backend, as before.

    Raises
    ------
    JudgeIndependenceError
        If *provider* is the ``claude_cli`` drafter transport.
    """
    from runner.transport.config import build_converse_backend, build_openai_backend

    if provider.backend_name == "claude_cli":
        raise JudgeIndependenceError(
            "The independent judge requires a non-drafter API transport "
            "(OpenAI-compatible or Bedrock Converse), but the resolved backend "
            "is 'claude_cli' (the drafter transport). "
            "Set ORCHESTRATOR_TRANSPORT_PRESET / ORCHESTRATOR_TRANSPORT_BACKEND "
            "to a non-Claude backend for grader–generator independence."
        )
    provider = dataclasses.replace(provider, model=config.model)
    build = (
        build_converse_backend
        if provider.backend_name == "bedrock_converse"
        else build_openai_backend
    )
    return build(provider, temperature=config.temperature, max_tokens=config.max_tokens)


# --------------------------------------------------------------------------- #
# Result bundles
# --------------------------------------------------------------------------- #


class Judged(Protocol):
    """What a parsed value reports about itself for its provenance record.

    :class:`~harness.verdict.Verdict` satisfies it as it stands; a caller whose
    value has another shape (a 0-5 criterion sample, a decomposition) wraps it
    in a small type that says what its record should carry.  The judge reads
    these three attributes and writes the record itself.
    """

    @property
    def score(self) -> float | None: ...

    @property
    def passed(self) -> bool | None: ...

    @property
    def rationale(self) -> str: ...


ParsedT = TypeVar("ParsedT", bound=Judged)

#: Parser shape: ``raw response -> parsed value``.  Raises
#: :class:`JudgeResponseError` for a malformed response, which is the only
#: signal the judge redraws on.
Parser = Callable[[str], ParsedT]


@dataclass(frozen=True)
class DiscardedDraw:
    """One draw whose response would not parse, and was drawn again.

    Kept so that a redraw never hides: every result names each draw that was
    thrown away, why (the parser's own message), and the sha256 and length of
    the text that was thrown.  ``replayed`` is ``True`` when the thrown draw
    was served from a resumed checkpoint rather than drawn live; it is
    serialized only when ``True``, so a live draw keeps its shape.
    """

    sample_index: int | None
    attempt: int
    reason: str
    response_sha256: str
    response_chars: int
    replayed: bool = False

    def to_dict(self) -> dict[str, Any]:
        record: dict[str, Any] = {
            "sample_index": self.sample_index,
            "attempt": self.attempt,
            "reason": self.reason,
            "response_sha256": self.response_sha256,
            "response_chars": self.response_chars,
        }
        if self.replayed:
            record["replayed"] = True
        return record


@dataclass(frozen=True)
class JudgeAnswer(Generic[ParsedT]):
    """What :meth:`Judge.ask` returns: the parsed value, its record, its discards."""

    value: ParsedT
    provenance: ProvenanceRecord
    raw_response: str
    discarded_draws: tuple[DiscardedDraw, ...] = ()


@dataclass(frozen=True)
class JudgeResult:
    """A single verdict plus its provenance and the raw response text."""

    verdict: Verdict
    provenance: ProvenanceRecord
    raw_response: str
    discarded_draws: tuple[DiscardedDraw, ...] = ()


@dataclass(frozen=True)
class MajorityJudgeResult:
    """An N≥3 majority verdict plus every member verdict and its provenance."""

    majority: MajorityVerdict
    verdicts: tuple[Verdict, ...]
    provenance: tuple[ProvenanceRecord, ...]
    raw_responses: tuple[str, ...]
    discarded_draws: tuple[DiscardedDraw, ...] = ()


# --------------------------------------------------------------------------- #
# Response parsing (no silent repair)
# --------------------------------------------------------------------------- #


def parse_verdict(raw: str, *, metric: str, property_key: str) -> Verdict:
    """Parse one response of the default ``{passed, score, rationale}`` schema.

    The verdict parser every cell uses, and the one the salvage command judges
    transcripts with.  Raises :class:`JudgeResponseError` — never repairs.
    """
    payload = extract_first_json_object(raw)
    if payload is None:
        raise JudgeResponseError(
            f"Judge returned no parseable JSON object for {metric!r}/{property_key!r}: "
            f"{raw[:200]!r}"
        )
    return _verdict_from_payload(payload, metric=metric, property_key=property_key)


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
        backend is built lazily from ``resolve_provider_config()`` on first use
        (:func:`build_judge_backend`): native Converse for ``bedrock_converse``,
        OpenAI-compatible otherwise, and a ``claude_cli`` transport is rejected
        for independence.  Note: the *transport*-independence check
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
    response_cache:
        Optional :class:`~harness.response_cache.ResponseCache`.  When present,
        every raw response is checkpointed as it arrives, and a cache opened in
        resume mode serves the calls it already holds instead of spawning them
        again.  A long run then survives a failure in its last call.
    max_redraws:
        Extra draws one ask may take when its response will not parse
        (default :data:`DEFAULT_MAX_REDRAWS`).  The same for every ask.
    """

    def __init__(
        self,
        config: JudgeConfig,
        *,
        backend: Backend | None = None,
        provenance_log: ProvenanceLog | None = None,
        clock: Clock | None = None,
        response_cache: ResponseCache | None = None,
        max_redraws: int = DEFAULT_MAX_REDRAWS,
    ) -> None:
        if isinstance(max_redraws, bool) or not isinstance(max_redraws, int) or max_redraws < 0:
            raise JudgeConfigError(f"max_redraws must be a non-negative int; got {max_redraws!r}.")
        self.config = config
        self._backend = backend
        self._provenance_log = provenance_log
        self._clock = clock or _default_clock
        self._response_cache = response_cache
        self.max_redraws = max_redraws

    @property
    def clock(self) -> Clock:
        """The timestamp source every provenance record carries (read-only)."""
        return self._clock

    @property
    def response_cache(self) -> ResponseCache | None:
        """The attached response checkpoint, if any (read-only).

        Every draw this judge makes goes out through :meth:`ask`, so the cache
        attached here covers the whole run: the cells, the criterion samples
        and anything else a caller drives.
        """
        return self._response_cache

    def attach_response_cache(self, cache: ResponseCache) -> None:
        """Attach a checkpoint to a judge built elsewhere.

        The live assessors are built by their own builders
        (``build_paced_judge``, ``build_subscription_judge``), so a command
        that wants a checkpoint attaches it after the fact.  A second cache is
        refused: two caches would each hold half a run and neither would
        replay it.
        """
        if self._response_cache is not None:
            raise JudgeError(
                f"this judge already writes to checkpoint "
                f"{self._response_cache.path}; a second one would split the run."
            )
        self._response_cache = cache

    @property
    def provenance_log(self) -> ProvenanceLog | None:
        """The attached provenance log, if any (read-only).

        :meth:`ask` appends every record to it.  Exposed so graders can refuse
        a judge that would leave no durable trail.
        """
        return self._provenance_log

    # -- transport -------------------------------------------------------- #

    def _get_backend(self) -> Backend:
        """Return the backend, building a real one from env config on first use."""
        if self._backend is not None:
            return self._backend

        from runner.transport.config import resolve_provider_config

        self._backend = build_judge_backend(resolve_provider_config(), self.config)
        return self._backend

    def _send(self, system_prompt: str, user_prompt: str) -> str:
        """Send one chat request and return the raw content string (private).

        Raises :class:`JudgeResponseError` if the backend returns no content.

        Only :meth:`ask` calls this.  It is where the response checkpoint
        lives (:mod:`harness.response_cache`): with a cache attached in resume
        mode, a call the checkpoint covers is served from it and no subprocess
        is spawned; otherwise the live response is checkpointed verbatim
        before it is returned to the parser.  Replay is byte-faithful: the
        same response text, through the same parsers, never a repaired or
        regenerated one.
        """
        cache = self._response_cache
        key = prompt_hash(system_prompt, user_prompt) if cache is not None else ""
        if cache is not None:
            replayed = cache.take(key)
            if replayed is not None:
                return replayed
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
        if cache is not None:
            cache.record(key, str(content))
        return str(content)

    def _discard_last_response(self, reason: str) -> None:
        """Tell the checkpoint that the last response was unusable, if one is attached.

        The cache sits below the parsers and cannot tell a good response from a
        bad one; this is how it is told.  A discarded response stays in the
        file but is never replayed, so a resumed run redraws that call instead
        of failing on the same bytes again.
        """
        if self._response_cache is not None:
            self._response_cache.discard_last(reason)

    @property
    def last_call_replayed(self) -> bool:
        """Whether the last draw was served from the checkpoint.

        A replayed response already has the live record of the run that drew
        it, so its new record is marked replayed rather than counted as a
        second draw.
        """
        return self._response_cache is not None and self._response_cache.last_was_replay

    # -- the one call path ------------------------------------------------ #

    def ask(
        self,
        system_prompt: str,
        user_prompt: str,
        parser: Parser[ParsedT],
        *,
        metric: str,
        property_key: str,
        sample_index: int | None = None,
        provenance_log: ProvenanceLog | None = None,
    ) -> JudgeAnswer[ParsedT]:
        """Draw one response, parse it strictly, and return the value with its record.

        The only way a draw goes out.  In order:

        1. The checkpoint serves the call, or it is drawn live and recorded.
        2. *parser* reads the raw text.  Only :class:`JudgeResponseError`
           means "malformed": the draw is discarded from the checkpoint,
           recorded as a :class:`DiscardedDraw`, and drawn again over the
           identical prompt, up to :attr:`max_redraws` times.  A replayed draw
           that fails uses budget too and is marked ``replayed``.  Any other
           exception passes straight through, with no redraw and no discard.
        3. Once the budget is spent the ask fails closed with the parser's
           last message and the draw count.  Nothing is repaired.
        4. The judge writes the provenance record from what the value reports
           about itself (:class:`Judged`) into *provenance_log* when one is
           given, else into the attached log, and returns the value, its
           record and its discarded draws.
        """
        discarded: list[DiscardedDraw] = []
        for attempt in range(self.max_redraws + 1):
            raw = self._send(system_prompt, user_prompt)
            replayed = self.last_call_replayed
            try:
                value = parser(raw)
            except JudgeResponseError as exc:
                self._discard_last_response(str(exc))
                if attempt >= self.max_redraws:
                    where = f"{metric}/{property_key}" + (
                        f" sample {sample_index}" if sample_index is not None else ""
                    )
                    raise JudgeResponseError(
                        f"{exc} ({where}: {attempt + 1} draw(s) over an identical "
                        f"prompt, every one malformed; nothing was repaired)"
                    ) from exc
                discarded.append(
                    DiscardedDraw(
                        sample_index=sample_index,
                        attempt=attempt,
                        reason=str(exc),
                        response_sha256=hashlib.sha256(raw.encode("utf-8")).hexdigest(),
                        response_chars=len(raw),
                        replayed=replayed,
                    )
                )
                continue
            record = ProvenanceRecord(
                judge_model=self.config.model,
                judge_version=self.config.version,
                prompt_hash=prompt_hash(system_prompt, user_prompt),
                score=value.score,
                rationale=value.rationale,
                metric=metric,
                property_key=property_key,
                passed=value.passed,
                sample_index=sample_index,
                timestamp=self._clock(),
                replayed=replayed,
            )
            log = provenance_log if provenance_log is not None else self._provenance_log
            if log is not None:
                log.append(record)
            return JudgeAnswer(
                value=value,
                provenance=record,
                raw_response=raw,
                discarded_draws=tuple(discarded),
            )
        raise JudgeError(  # pragma: no cover - the loop returns or raises
            "unreachable: the redraw loop exited without a value"
        )

    # -- verdict presets -------------------------------------------------- #

    def evaluate(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        metric: str,
        property_key: str,
        sample_index: int | None = None,
    ) -> JudgeResult:
        """Produce one :class:`Verdict` (+ provenance): :meth:`ask` with :func:`parse_verdict`.

        The judge is expected to return a JSON object of the default schema
        ``{"passed": bool?, "score": number?, "rationale": str}`` (a metric may
        instruct a richer schema in *system_prompt*; only these keys are read).
        A malformed response is redrawn within the budget, then raises
        :class:`JudgeResponseError`.
        """

        def parse(raw: str) -> Verdict:
            verdict = parse_verdict(raw, metric=metric, property_key=property_key)
            if sample_index is not None:
                verdict = dataclasses.replace(verdict, sample_index=sample_index)
            return verdict

        answer = self.ask(
            system_prompt,
            user_prompt,
            parse,
            metric=metric,
            property_key=property_key,
            sample_index=sample_index,
        )
        return JudgeResult(
            verdict=answer.value,
            provenance=answer.provenance,
            raw_response=answer.raw_response,
            discarded_draws=answer.discarded_draws,
        )

    def evaluate_majority(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        metric: str,
        property_key: str,
        n: int = MIN_MAJORITY_SAMPLES,
    ) -> MajorityJudgeResult:
        """Run :meth:`evaluate` ``n`` (≥3) times and combine via majority vote.

        The scaffold the guardrails mandate wherever a score will inform a
        decision.  A redraw replaces its malformed sample, so the vote always
        has ``n`` members.  Every sample's provenance is captured (and logged
        if a log is attached); the combined :class:`MajorityVerdict` is still
        ``Inferred``.
        """
        if n < MIN_MAJORITY_SAMPLES:
            raise ValueError(
                f"evaluate_majority requires n≥{MIN_MAJORITY_SAMPLES}; got {n}."
            )
        results = [
            self.evaluate(
                system_prompt,
                user_prompt,
                metric=metric,
                property_key=property_key,
                sample_index=i,
            )
            for i in range(n)
        ]
        verdicts = [r.verdict for r in results]
        return MajorityJudgeResult(
            majority=majority_vote(verdicts),
            verdicts=tuple(verdicts),
            provenance=tuple(r.provenance for r in results),
            raw_responses=tuple(r.raw_response for r in results),
            discarded_draws=tuple(d for r in results for d in r.discarded_draws),
        )
