"""
Instrumented transport wrapper — captures per-invocation telemetry.

Provides two instrumentation layers:

1. ``instrumented_invoke()`` — wraps ``invoke_claude_text()`` (Claude CLI
   transport) at call sites.

2. ``InstrumentedBackend`` — wraps any ``ToolLoopBackend``-conforming
   callable (OpenAI-compatible, Bedrock Converse, etc.) to capture
   per-round telemetry through ``run_tool_loop()`` and direct calls.

When benchmarking is disabled (``get_ledger()`` returns ``None``), both
layers fall through with zero overhead.

Prompt content is NEVER captured — only character counts.

Integration pattern
-------------------
Call-site modules (``skill_runtime.py``, ``semantic_dispatch.py``)
alias ``instrumented_invoke`` AS ``invoke_claude_text`` for the Claude
CLI path, and wrap non-Claude backends with ``InstrumentedBackend``:

    from runner.benchmark.transport_hook import instrumented_invoke as invoke_claude_text
    from runner.benchmark.transport_hook import InstrumentedBackend

Extra ``_bench_*`` kwargs are silently accepted by ``MagicMock`` in tests.
The underlying transport is called via late-bound module lookup so that
mocking ``runner.claude_transport.invoke_claude_text`` also works.
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone

import runner.claude_transport as _transport_module
from runner.benchmark.context import get_ledger
from runner.benchmark.models import BenchmarkInvocationRecord
from runner.benchmark.token_estimator import estimate_tokens

logger = logging.getLogger(__name__)


def instrumented_invoke(
    *,
    system_prompt: str,
    user_prompt: str,
    model: str,
    max_tokens: int,
    timeout_seconds: int = 300,
    tools: list[str] | None = None,
    # Benchmark metadata (not passed to transport).
    # Accepted via **_bench_kwargs so that MagicMock test patches
    # (which don't know about these params) continue to work when
    # this function is aliased as invoke_claude_text.
    _bench_run_id: str = "",
    _bench_skill_id: str | None = None,
    _bench_node_id: str | None = None,
    _bench_predicate_id: str | None = None,
    _bench_invocation_type: str = "unknown",
) -> str:
    """Instrumented wrapper around ``invoke_claude_text()``.

    Captures telemetry when a benchmark ledger is active.
    Falls through to plain ``invoke_claude_text()`` when benchmarking
    is off.

    All transport parameters are forwarded exactly.  Return value and
    exceptions are preserved exactly.

    Uses late-bound module lookup (``_transport_module.invoke_claude_text``)
    so that both ``runner.claude_transport.invoke_claude_text`` and
    call-site-level mocks work correctly in tests.
    """
    ledger = get_ledger()

    # Late-bound transport function lookup — ensures mocking at the
    # runner.claude_transport module level works correctly.
    _invoke = _transport_module.invoke_claude_text

    if ledger is None:
        # Benchmarking disabled - zero overhead path
        return _invoke(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=model,
            max_tokens=max_tokens,
            timeout_seconds=timeout_seconds,
            tools=tools,
        )

    # Benchmarking enabled - capture telemetry
    invocation_id = uuid.uuid4().hex
    t0 = time.monotonic()
    ts = datetime.now(timezone.utc).isoformat()

    sys_chars = len(system_prompt)
    user_chars = len(user_prompt)

    execution_mode = "tapm" if tools else "cli-prompt"

    response_text: str | None = None
    response_status = "success"
    error_class: str | None = None
    error_message: str | None = None

    try:
        response_text = _invoke(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=model,
            max_tokens=max_tokens,
            timeout_seconds=timeout_seconds,
            tools=tools,
        )
        response_status = "success"
        return response_text
    except Exception as exc:
        error_class = type(exc).__name__
        error_message = str(exc)[:500]
        if "timeout" in error_class.lower() or "timeout" in error_message.lower():
            response_status = "timeout"
        else:
            response_status = "error"
        raise
    finally:
        t1 = time.monotonic()
        wall_seconds = t1 - t0
        resp_chars = len(response_text) if response_text is not None else None

        input_chars = sys_chars + user_chars
        estimated_in = estimate_tokens(input_chars, model)
        estimated_out = estimate_tokens(resp_chars, model) if resp_chars else 0

        try:
            record = BenchmarkInvocationRecord(
                invocation_id=invocation_id,
                run_id=_bench_run_id,
                node_id=_bench_node_id,
                skill_id=_bench_skill_id,
                predicate_id=_bench_predicate_id,
                invocation_type=_bench_invocation_type,
                execution_mode=execution_mode,
                model=model,
                timeout_seconds=timeout_seconds,
                tools_enabled=list(tools) if tools else [],
                system_prompt_chars=sys_chars,
                user_prompt_chars=user_chars,
                response_chars=resp_chars,
                response_status=response_status,
                wall_clock_start=t0,
                wall_clock_end=t1,
                wall_clock_seconds=round(wall_seconds, 4),
                timestamp_utc=ts,
                estimated_input_tokens=estimated_in,
                estimated_output_tokens=estimated_out,
                error_class=error_class,
                error_message=error_message,
            )
            ledger.append(record)
        except Exception:
            logger.debug(
                "Benchmark record creation/append failed (non-blocking)",
                exc_info=True,
            )


# ---------------------------------------------------------------------------
# InstrumentedBackend — ToolLoopBackend wrapper for non-Claude transports
# ---------------------------------------------------------------------------


class InstrumentedBackend:
    """Benchmark-instrumented wrapper around a ``ToolLoopBackend`` callable.

    Wraps any backend conforming to the ``ToolLoopBackend`` protocol
    (OpenAI-compatible, Bedrock Converse, FakeBackend, etc.) and records
    a :class:`BenchmarkInvocationRecord` for every ``__call__``.

    When benchmarking is disabled (``get_ledger()`` returns ``None``),
    delegates directly with zero overhead.

    The wrapper preserves the backend's return value and exception
    semantics exactly.  It also proxies ``last_usage``, ``model``, and
    ``url`` properties so callers that inspect the backend continue to
    work.

    Parameters
    ----------
    backend:
        The underlying ``ToolLoopBackend``-conforming callable.
    model:
        Model identifier for the benchmark record.
    timeout_seconds:
        Timeout used for the backend (for the benchmark record).
    tool_names:
        Tool names enabled on the backend (e.g. ``["Read", "Glob"]``).
    bench_run_id:
        Run UUID for the benchmark record.
    bench_skill_id:
        Skill ID (``None`` for semantic predicates).
    bench_node_id:
        Node ID (``None`` for semantic predicates).
    bench_predicate_id:
        Predicate ID (``None`` for skills).
    bench_invocation_type:
        Invocation classification string.
    """

    def __init__(
        self,
        backend: object,
        *,
        model: str = "",
        timeout_seconds: int = 300,
        tool_names: list[str] | None = None,
        bench_run_id: str = "",
        bench_skill_id: str | None = None,
        bench_node_id: str | None = None,
        bench_predicate_id: str | None = None,
        bench_invocation_type: str = "unknown",
    ) -> None:
        self._backend = backend
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._tool_names = tool_names or []
        self._bench_run_id = bench_run_id
        self._bench_skill_id = bench_skill_id
        self._bench_node_id = bench_node_id
        self._bench_predicate_id = bench_predicate_id
        self._bench_invocation_type = bench_invocation_type
        self._round = 0

    def __call__(self, messages: list[dict]) -> dict:
        """Invoke the backend and record telemetry if benchmarking is active."""
        ledger = get_ledger()

        if ledger is None:
            return self._backend(messages)  # type: ignore[operator]

        self._round += 1
        invocation_id = uuid.uuid4().hex
        t0 = time.monotonic()
        ts = datetime.now(timezone.utc).isoformat()

        # Measure input size from messages (char counts only).
        sys_chars = 0
        user_chars = 0
        for msg in messages:
            content = msg.get("content") or ""
            content_len = len(content) if isinstance(content, str) else 0
            if msg.get("role") == "system":
                sys_chars += content_len
            else:
                user_chars += content_len

        execution_mode = "openai_compat_tapm" if self._tool_names else "openai_compat"

        response_status = "success"
        error_class: str | None = None
        error_message: str | None = None
        resp_chars: int | None = None

        try:
            result = self._backend(messages)  # type: ignore[operator]
            content = result.get("content") or ""
            resp_chars = len(content) if isinstance(content, str) else 0
            return result
        except Exception as exc:
            error_class = type(exc).__name__
            error_message = str(exc)[:500]
            if "timeout" in error_class.lower() or "timeout" in error_message.lower():
                response_status = "timeout"
            else:
                response_status = "error"
            raise
        finally:
            t1 = time.monotonic()
            wall_seconds = t1 - t0

            # Prefer actual token counts from the backend when available.
            actual_usage = getattr(self._backend, "last_usage", None)
            if isinstance(actual_usage, dict) and actual_usage.get("prompt_tokens"):
                estimated_in = actual_usage.get("prompt_tokens", 0)
                estimated_out = actual_usage.get("completion_tokens", 0)
            else:
                input_chars = sys_chars + user_chars
                estimated_in = estimate_tokens(input_chars, self._model)
                estimated_out = (
                    estimate_tokens(resp_chars, self._model) if resp_chars else 0
                )

            try:
                record = BenchmarkInvocationRecord(
                    invocation_id=invocation_id,
                    run_id=self._bench_run_id,
                    node_id=self._bench_node_id,
                    skill_id=self._bench_skill_id,
                    predicate_id=self._bench_predicate_id,
                    invocation_type=self._bench_invocation_type,
                    execution_mode=execution_mode,
                    model=self._model,
                    timeout_seconds=self._timeout_seconds,
                    tools_enabled=list(self._tool_names),
                    system_prompt_chars=sys_chars,
                    user_prompt_chars=user_chars,
                    response_chars=resp_chars,
                    response_status=response_status,
                    wall_clock_start=t0,
                    wall_clock_end=t1,
                    wall_clock_seconds=round(wall_seconds, 4),
                    timestamp_utc=ts,
                    estimated_input_tokens=estimated_in,
                    estimated_output_tokens=estimated_out,
                    error_class=error_class,
                    error_message=error_message,
                )
                ledger.append(record)
            except Exception:
                logger.debug(
                    "Benchmark record creation/append failed (non-blocking)",
                    exc_info=True,
                )

    # -- Property proxies for callers that inspect the backend --------

    @property
    def last_usage(self) -> dict | None:
        """Proxy ``last_usage`` from the underlying backend."""
        return getattr(self._backend, "last_usage", None)

    @property
    def model(self) -> str:
        """Proxy ``model`` from the underlying backend."""
        return getattr(self._backend, "model", self._model)

    @property
    def url(self) -> str | None:
        """Proxy ``url`` from the underlying backend."""
        return getattr(self._backend, "url", None)
