"""
Instrumented transport wrapper — captures per-invocation telemetry.

Wraps ``invoke_claude_text()`` at call sites, preserving return value
and exception semantics exactly.  When benchmarking is disabled
(``get_ledger()`` returns ``None``), falls through to the plain
transport with zero overhead.

Prompt content is NEVER captured — only character counts.

Integration pattern
-------------------
Call-site modules (``skill_runtime.py``, ``semantic_dispatch.py``)
alias this function AS ``invoke_claude_text``:

    from runner.benchmark.transport_hook import instrumented_invoke as invoke_claude_text

This preserves existing test mock targets (``runner.skill_runtime.invoke_claude_text``).
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
