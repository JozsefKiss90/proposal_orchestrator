"""
The one place a harness judge is built, and the table of what independence each route keeps.

A command names a route.  :func:`build_judge` then

1. re-applies the model guard (:class:`~harness.judge.JudgeConfig`: no drafter
   model, in any id form) on every route;
2. applies the route's own row of :data:`INDEPENDENCE_POLICY` (a Claude pin, a
   version tag naming the transport);
3. checks that the transport environment resolves to that route, and refuses
   a mismatch naming both — no route is ever inferred from the environment;
4. builds the backend, wraps it in the route's retry (and, on
   ``openai-compatible``, pacing) wrapper, and wires the provenance log.

It returns the judge and the wrapper, so a command can read the call and
retry counts.  :class:`~harness.judge.Judge` has no default backend of its
own; nothing else in ``harness/`` constructs one (``tests/harness/
test_judge_factory.py`` checks the source).

The route names are the strings a blind report records as
``assessor_transport``.  The route backends that only one route uses live
beside their commands: the Converse retry wrapper in
:mod:`harness.commands._converse_judge`, the ``claude`` CLI backend in
:mod:`harness.commands._subscription_judge`.  ``runner/transport`` is not
changed; the harness only imports it.

Advisory output only.  The harness is never a runtime gate.
"""
from __future__ import annotations

import dataclasses
import re
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from harness.judge import Judge, JudgeConfig, JudgeError, JudgeIndependenceError
from harness.provenance import ProvenanceLog

__all__ = [
    "INDEPENDENCE_POLICY",
    "ROUTE_BEDROCK_CONVERSE",
    "ROUTE_CLAUDE_CLI",
    "ROUTE_OPENAI_COMPATIBLE",
    "JudgeRouteError",
    "PacedRetryingBackend",
    "RoutePolicy",
    "build_judge",
    "route_of_backend",
]

ROUTE_OPENAI_COMPATIBLE = "openai-compatible"
ROUTE_BEDROCK_CONVERSE = "bedrock-converse"
ROUTE_CLAUDE_CLI = "claude-cli"

HOLDS = "holds"
DOES_NOT_HOLD = "does not hold"
NOT_CHECKED = "not checked"


class JudgeRouteError(JudgeError):
    """The route cannot be built as asked: unknown, misconfigured, or not what
    the environment resolves to.  A :class:`~harness.judge.JudgeError`, so the
    commands convert it to their fail-closed exit rather than a traceback."""


# --------------------------------------------------------------------------- #
# The independence policy
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class RoutePolicy:
    """One route's row of :data:`INDEPENDENCE_POLICY`.

    The four ``*_independence`` fields say which kinds of grader–generator
    independence hold on the route (:data:`HOLDS`, :data:`DOES_NOT_HOLD` or
    :data:`NOT_CHECKED`).  The model guard holds on every route.
    """

    route: str
    #: The ``backend_name`` values of ``resolve_provider_config()`` this route
    #: accepts.  Any other value is refused, naming both.
    environment: frozenset[str]
    #: Token- and request-paced as well as retried, when the caller passes
    #: budgets; a caller that passes none (rubric grid, materiality) is unpaced.
    paced: bool
    #: Retries on a retryable transport error when the caller passes none.
    default_max_retries: int
    #: The version tag must contain the route name: a report records
    #: ``model@version`` and nothing else about the assessor.
    version_tag_required: bool
    #: The pin must be one the ``claude`` CLI can resolve.
    claude_pin_required: bool
    #: How the assessor is kept from opening anything.
    tool_isolation: str
    model_independence: str
    transport_independence: str
    vendor_independence: str
    context_independence: str


#: Backend names that speak the OpenAI-compatible HTTP API.
_OPENAI_COMPATIBLE_BACKENDS = frozenset({"openai_compatible", "bedrock", "together_ai", "ollama"})

#: The independence policy, one row per route.  ``harness/HARNESS.md`` and the
#: subscription module's account of "what independence survives" read it.
INDEPENDENCE_POLICY: Mapping[str, RoutePolicy] = {
    ROUTE_OPENAI_COMPATIBLE: RoutePolicy(
        route=ROUTE_OPENAI_COMPATIBLE,
        environment=_OPENAI_COMPATIBLE_BACKENDS,
        paced=True,
        default_max_retries=6,
        version_tag_required=False,
        claude_pin_required=False,
        tool_isolation="the request carries no tool schemas",
        model_independence=HOLDS,
        transport_independence=HOLDS,
        vendor_independence=NOT_CHECKED,
        context_independence=HOLDS,
    ),
    ROUTE_BEDROCK_CONVERSE: RoutePolicy(
        route=ROUTE_BEDROCK_CONVERSE,
        environment=frozenset({"bedrock_converse"}),
        paced=False,
        default_max_retries=6,
        version_tag_required=True,
        claude_pin_required=False,
        tool_isolation="no request carries a toolConfig (measured by the retry wrapper)",
        model_independence=HOLDS,
        transport_independence=DOES_NOT_HOLD,
        vendor_independence=DOES_NOT_HOLD,
        context_independence=HOLDS,
    ),
    ROUTE_CLAUDE_CLI: RoutePolicy(
        route=ROUTE_CLAUDE_CLI,
        environment=frozenset({"claude_cli"}),
        paced=False,
        default_max_retries=2,
        version_tag_required=True,
        claude_pin_required=True,
        tool_isolation=(
            "the explicit empty tool list (--tools \"\" --strict-mcp-config) and a "
            "fresh working directory outside the repository"
        ),
        model_independence=HOLDS,
        transport_independence=DOES_NOT_HOLD,
        vendor_independence=DOES_NOT_HOLD,
        context_independence=HOLDS,
    ),
}


def route_of_backend(backend_name: str) -> str:
    """The route a resolved transport ``backend_name`` belongs to."""
    for policy in INDEPENDENCE_POLICY.values():
        if backend_name in policy.environment:
            return policy.route
    return f"no route ({backend_name!r} is not a judge backend)"


# --------------------------------------------------------------------------- #
# The paced, retrying wrapper
# --------------------------------------------------------------------------- #

#: Cold-start token estimate before any real usage is observed. Faithfulness
#: calls carry a source excerpt, so they are not tiny — bias high to be safe.
_COLD_ESTIMATE_TOKENS = 3000

#: Parse a provider "please try again in 8.5s" hint out of a 429 body, if present.
_RETRY_AFTER_RE = re.compile(r"try again in\s*([0-9.]+)\s*s", re.IGNORECASE)


class PacedRetryingBackend:
    """Backend wrapper: token-accurate pacing + retry on retryable errors.

    Conforms to the ``ToolLoopBackend`` shape (``messages -> {"content", ...}``)
    and delegates to *inner*.  It is the single point every judge call passes
    through, which is the only place per-call pacing is reachable — E2's
    per-claim loop is internal to ``evaluate_status_aware_faithfulness`` and
    cannot be paced from outside.  With an infinite token budget and no request
    floor it only retries, which is how the Converse route uses it.
    """

    def __init__(
        self,
        inner,
        *,
        tpm_budget,
        rpm_budget,
        max_retries,
        base_delay=8.0,
        max_delay=90.0,
        log=print,
    ) -> None:
        self._inner = inner
        self._tpm = float(tpm_budget)
        self._min_interval = 60.0 / float(rpm_budget) if rpm_budget else 0.0
        self._max_retries = int(max_retries)
        self._base = float(base_delay)
        self._max = float(max_delay)
        self._log = log
        self._window: deque = deque()   # (monotonic_ts, total_tokens) within the last 60s
        self._recent: deque = deque(maxlen=8)
        self._last_ts = 0.0
        # counters for the run summary
        self.calls = 0
        self.retries = 0
        self.total_tokens = 0

    # -- token-aware pacing --------------------------------------------- #
    def _evict(self, now: float) -> None:
        while self._window and now - self._window[0][0] >= 60.0:
            self._window.popleft()

    def _tokens_in_window(self) -> int:
        return sum(t for _, t in self._window)

    def _estimate_next(self) -> int:
        return max(self._recent) if self._recent else _COLD_ESTIMATE_TOKENS

    def _pace(self) -> None:
        # (1) RPM floor — cheap request spacing.
        if self._min_interval:
            gap = self._min_interval - (time.monotonic() - self._last_ts)
            if gap > 0:
                time.sleep(gap)
        # (2) TPM sliding window — wait until the projected next call fits the budget.
        while self._window:
            now = time.monotonic()
            self._evict(now)
            if not self._window:
                break
            if self._tokens_in_window() + self._estimate_next() <= self._tpm:
                break
            sleep_for = 60.0 - (now - self._window[0][0]) + 0.1
            self._log(
                f"    pacing: {self._tokens_in_window()} tok in the 60s window; "
                f"waiting {sleep_for:.1f}s for TPM headroom"
            )
            time.sleep(max(sleep_for, 0.1))

    # -- backend protocol ----------------------------------------------- #
    def __call__(self, messages):
        # Imported here: the transport package loads ``.env`` on import.
        from runner.transport.errors import OpenAICompatTransportError

        delay = self._base
        for attempt in range(self._max_retries + 1):
            self._pace()
            try:
                result = self._inner(messages)
            except OpenAICompatTransportError as exc:
                # Use the transport's OWN retryability flag (verified: 429/5xx/
                # timeout => retryable=True; 400/401/403/404 => False).
                if not getattr(exc, "retryable", False) or attempt >= self._max_retries:
                    raise
                self.retries += 1
                wait = self._retry_after(exc, delay)
                self._log(
                    f"    {getattr(exc.category, 'value', 'error')} "
                    f"(attempt {attempt + 1}/{self._max_retries}) — waiting {wait:.0f}s then retrying"
                )
                time.sleep(wait)
                delay = min(delay * 2, self._max)
                continue
            # success — record REAL usage so pacing tracks actual tokens.
            self._last_ts = time.monotonic()
            usage = getattr(self._inner, "last_usage", None)
            tok = (
                int(usage["total_tokens"])
                if usage and usage.get("total_tokens")
                else self._estimate_next()
            )
            self._window.append((self._last_ts, tok))
            self._recent.append(tok)
            self.calls += 1
            self.total_tokens += tok
            return result
        raise RuntimeError("unreachable: retry loop exited without returning or raising")

    def _retry_after(self, exc, fallback: float) -> float:
        body = getattr(exc, "response_body", "") or ""
        m = _RETRY_AFTER_RE.search(body)
        if m:
            try:
                return min(max(float(m.group(1)) + 0.5, 1.0), self._max)
            except ValueError:
                pass
        return fallback


# --------------------------------------------------------------------------- #
# The factory
# --------------------------------------------------------------------------- #


def _route_error(route: str) -> type[JudgeRouteError]:
    """The error a route raises: its module's own subclass, so a caller that
    catches ``ConverseJudgeError`` or ``SubscriptionJudgeError`` still does."""
    if route == ROUTE_BEDROCK_CONVERSE:
        from harness.commands._converse_judge import ConverseJudgeError

        return ConverseJudgeError
    if route == ROUTE_CLAUDE_CLI:
        from harness.commands._subscription_judge import SubscriptionJudgeError

        return SubscriptionJudgeError
    return JudgeRouteError


def _check_pin(policy: RoutePolicy, config: JudgeConfig, error: type[JudgeRouteError]) -> None:
    if policy.claude_pin_required:
        from harness.commands._subscription_judge import is_claude_model_pin

        if not is_claude_model_pin(config.model):
            raise error(
                f"HARNESS_JUDGE_MODEL is {config.model!r}, which the 'claude' CLI "
                f"cannot resolve. The subscription assessor needs a Claude pin "
                f"(e.g. 'claude-sonnet-5'); the Groq pin belongs to the "
                f"OpenAI-compatible transport."
            )
    if policy.version_tag_required and policy.route not in str(config.version):
        raise error(
            f"HARNESS_JUDGE_VERSION is {config.version!r}, which does not name this "
            f"transport. The report records model@version and nothing else about "
            f"the assessor, so the tag must contain {policy.route!r} (e.g. "
            f"'{policy.route}-<detail>@<date>'); pass --assessor-version."
        )


def _resolve_environment(policy: RoutePolicy, error: type[JudgeRouteError]) -> Any:
    """The resolved provider, when the environment agrees with the route."""
    from runner.transport import config as transport_config

    # The transport refuses a misconfiguration with a plain ValueError (no Region
    # in production mode, a backend production mode does not allow, no model).
    try:
        provider = transport_config.resolve_provider_config()
    except ValueError as exc:
        raise error(f"the {policy.route} configuration is refused: {exc}") from exc
    backend = provider.backend_name
    if backend in policy.environment:
        return provider
    message = (
        f"the {policy.route!r} route was asked for, but the transport environment "
        f"resolves to {backend!r} ({route_of_backend(backend)}). No route is "
        f"inferred: set ORCHESTRATOR_TRANSPORT_PRESET / ORCHESTRATOR_TRANSPORT_BACKEND "
        f"to one of {sorted(policy.environment)}, or ask for the route the "
        f"environment names, so the report names the transport it spoke."
    )
    if backend == "claude_cli":
        # The drafter transport behind an API route: an independence refusal.
        raise JudgeIndependenceError(
            f"{message} The independent judge requires a non-drafter API transport "
            f"(OpenAI-compatible or Bedrock Converse) for grader–generator independence."
        )
    raise error(message)


def _api_backend(provider: Any, config: JudgeConfig, error: type[JudgeRouteError]) -> Any:
    """The transport's backend for *provider*, pinned to the judge's model.

    The judge model, temperature and token limit come from *config*, whatever
    model the environment names.
    """
    from runner.transport import config as transport_config

    provider = dataclasses.replace(provider, model=config.model)
    build = (
        transport_config.build_converse_backend
        if provider.backend_name == "bedrock_converse"
        else transport_config.build_openai_backend
    )
    try:
        return build(provider, temperature=config.temperature, max_tokens=config.max_tokens)
    except (ValueError, ImportError) as exc:
        raise error(f"the {route_of_backend(provider.backend_name)} backend cannot be built: {exc}") from exc


def build_judge(
    route: str,
    config: JudgeConfig,
    *,
    prov_path: Path | None = None,
    tpm: float | None = None,
    rpm: float | None = None,
    max_retries: int | None = None,
    repo_root: Path | None = None,
    working_dir: Path | None = None,
    timeout_seconds: int = 300,
    log: Callable[[str], None] = print,
) -> tuple[Judge, Any]:
    """Build the judge for *route*, after the checks of its policy row.

    Parameters
    ----------
    route:
        One of :data:`INDEPENDENCE_POLICY`'s keys.
    config:
        The pinned judge configuration.  Its model guard is applied again here.
    prov_path:
        The provenance log the judge appends every record to.  ``None`` attaches
        none, for a caller that writes the records itself.
    tpm, rpm:
        The pacing budgets of a paced route (tokens and requests per minute).
        ``None`` paces nothing on that axis.  Refused on a route that is not paced.
    max_retries:
        Retries on a retryable transport error; the route's default when ``None``.
    repo_root, working_dir, timeout_seconds:
        ``claude-cli`` only: the repository the child must not reach, the
        directory it runs in (default: a fresh one outside *repo_root*), and the
        per-call limit.

    Returns
    -------
    (Judge, wrapper)
        The judge and the backend it calls, whose counters a command reports.

    Raises
    ------
    JudgeIndependenceError
        If the model is a drafter model, or an API route meets the drafter's
        ``claude_cli`` environment.
    JudgeRouteError
        If the route is unknown, its pin or version tag is refused, the
        environment resolves to another route, or the backend cannot be built.
    """
    policy = INDEPENDENCE_POLICY.get(route)
    if policy is None:
        raise JudgeRouteError(f"unknown judge route {route!r}; routes: {sorted(INDEPENDENCE_POLICY)}")
    error = _route_error(route)
    # The model guard, on every route: a config cannot skip its own check here.
    config = JudgeConfig(
        model=config.model,
        version=config.version,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
    )
    if not policy.paced and (tpm is not None or rpm is not None):
        raise error(f"the {route!r} route is not paced; pacing budgets do not apply to it.")
    _check_pin(policy, config, error)
    provider = _resolve_environment(policy, error)
    retries = policy.default_max_retries if max_retries is None else max_retries

    if route == ROUTE_CLAUDE_CLI:
        from harness.commands._subscription_judge import ClaudeCLIJudgeBackend, assessor_working_dir
        from runner.paths import find_repo_root

        root = (repo_root if repo_root is not None else find_repo_root()).resolve()
        wrapper: Any = ClaudeCLIJudgeBackend(
            model=config.model,
            max_tokens=config.max_tokens,
            working_dir=working_dir if working_dir is not None else assessor_working_dir(root),
            repo_root=root,
            timeout_seconds=timeout_seconds,
            max_retries=retries,
            log=log,
        )
        log(
            f"    assessor child: tools disabled (--tools \"\" --strict-mcp-config), "
            f"working directory {wrapper.working_dir}"
        )
    elif route == ROUTE_BEDROCK_CONVERSE:
        from harness.commands._converse_judge import ConverseRetryingBackend

        # Retries, not pacing: an infinite token budget and no request floor.
        wrapper = ConverseRetryingBackend(
            _api_backend(provider, config, error),
            tpm_budget=float("inf"), rpm_budget=0, max_retries=retries, log=log,
        )
    else:
        wrapper = PacedRetryingBackend(
            _api_backend(provider, config, error),
            tpm_budget=float("inf") if tpm is None else tpm,
            rpm_budget=rpm or 0,
            max_retries=retries,
            log=log,
        )
    provenance = ProvenanceLog(prov_path) if prov_path is not None else None
    return Judge(config, backend=wrapper, provenance_log=provenance), wrapper
