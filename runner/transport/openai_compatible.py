"""
OpenAI-compatible HTTP backend for non-Claude LLM providers.

Implements the :class:`~runner.transport.tool_loop.ToolLoopBackend`
protocol by sending ``POST /chat/completions`` requests to any
OpenAI-compatible endpoint.

Used by AWS Bedrock (bedrock-mantle), Together AI, Ollama, and any
other provider exposing the OpenAI Chat Completions API.

This is a transport adapter.  It contains HTTP client logic, error
normalization, and response extraction.  It does not perform domain
reasoning, evaluate gates, write canonical artifacts, or modify
scheduler state.

Requires ``httpx`` (``pip install httpx``).

Constitutional authority:
    Subordinate to CLAUDE.md.  Transport-layer only.

Authoritative sources:
    - docs/backend/phase_e_bedrock_implementation_brief.md
    - docs/backend/phase_e_bedrock_validation_report.md
    - docs/internal_llm_migration_plan.md Section 5.4
"""

from __future__ import annotations

import logging
from typing import Any

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore[assignment]

from runner.transport.errors import (
    ErrorCategory,
    OpenAICompatProviderError,
    OpenAICompatTimeoutError,
    OpenAICompatTransportError,
    normalize_http_error,
)

logger = logging.getLogger(__name__)


class OpenAICompatBackend:
    """Backend for OpenAI-compatible Chat Completions API endpoints.

    Conforms to the :class:`~runner.transport.tool_loop.ToolLoopBackend`
    protocol: callable with ``(messages) -> {"content": ..., "tool_calls": ...}``.

    Bedrock, Together AI, and Ollama are all configuration variants of
    this single backend class.  No provider-specific subclass is needed.

    Parameters
    ----------
    base_url:
        The base URL of the OpenAI-compatible endpoint.
        Examples:
        - ``https://bedrock-mantle.eu-west-1.api.aws/v1``
        - ``https://api.together.ai/v1``
        - ``http://localhost:11434/v1``
    api_key:
        Bearer token for authentication.  ``None`` for unauthenticated
        endpoints (e.g. local Ollama).  Never logged.
    model:
        Model identifier for the ``model`` field in requests.
        Examples: ``anthropic.claude-sonnet-4-20250514-v1:0``,
        ``meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo``.
    temperature:
        Sampling temperature.  Default ``0.0`` for deterministic output.
    max_tokens:
        Maximum completion tokens.  Default ``4096``.
    tools:
        Optional list of OpenAI-format tool schemas to include in every
        request.  When provided, tool calling is enabled.
    timeout_seconds:
        Total request timeout in seconds.  Default ``300``.
    top_p:
        Nucleus sampling parameter.  ``None`` to omit.
    """

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str | None = None,
        model: str,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        tools: list[dict[str, Any]] | None = None,
        timeout_seconds: int = 300,
        top_p: float | None = None,
    ) -> None:
        if httpx is None:
            raise ImportError(
                "httpx is required for OpenAICompatBackend. "
                "Install it with: pip install httpx"
            )

        self._url: str = base_url.rstrip("/") + "/chat/completions"
        self._model: str = model
        self._temperature: float = temperature
        self._max_tokens: int = max_tokens
        self._tools: list[dict[str, Any]] = tools or []
        self._top_p: float | None = top_p
        self._last_usage: dict[str, int] | None = None

        self._headers: dict[str, str] = {
            "Content-Type": "application/json",
        }
        if api_key:
            self._headers["Authorization"] = f"Bearer {api_key}"

        self._timeout = httpx.Timeout(
            connect=30.0,
            read=float(timeout_seconds),
            write=30.0,
            pool=30.0,
        )

    # -- ToolLoopBackend protocol ------------------------------------------

    def __call__(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        """Send a Chat Completions request and return a ToolLoopBackend-compatible response.

        Parameters
        ----------
        messages:
            OpenAI-format message list (system, user, assistant, tool roles).

        Returns
        -------
        dict
            ``{"content": str | None, "tool_calls": list | None}``
        """
        payload = self._build_payload(messages)
        data = self._post(payload)
        return self._parse_response(data)

    # -- Public properties -------------------------------------------------

    @property
    def last_usage(self) -> dict[str, int] | None:
        """Token usage from the most recent request, if available.

        Returns ``None`` if the provider did not include a ``usage`` object
        in the response (e.g. streaming without ``stream_options``).
        """
        return self._last_usage

    @property
    def model(self) -> str:
        """The configured model identifier."""
        return self._model

    @property
    def url(self) -> str:
        """The full Chat Completions endpoint URL."""
        return self._url

    # -- Internal helpers --------------------------------------------------

    def _build_payload(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        """Construct the Chat Completions request payload."""
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
        }
        if self._tools:
            payload["tools"] = self._tools
        if self._top_p is not None:
            payload["top_p"] = self._top_p
        return payload

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Send the HTTP POST and return parsed JSON.

        Raises
        ------
        OpenAICompatTimeoutError
            On connection or read timeout.
        OpenAICompatProviderError
            On connection failure.
        OpenAICompatTransportError (subclass)
            On HTTP error status codes (normalized via ``errors.normalize_http_error``).
        """
        try:
            response = httpx.post(
                self._url,
                headers=self._headers,
                json=payload,
                timeout=self._timeout,
            )
        except httpx.TimeoutException as exc:
            raise OpenAICompatTimeoutError(
                f"Request timed out: {exc}",
                category=ErrorCategory.TIMEOUT,
                retryable=True,
            ) from exc
        except httpx.ConnectError as exc:
            raise OpenAICompatProviderError(
                f"Connection failed: {exc}",
                category=ErrorCategory.PROVIDER_ERROR,
                retryable=True,
            ) from exc
        except httpx.HTTPError as exc:
            raise OpenAICompatTransportError(
                f"HTTP error: {exc}",
                category=ErrorCategory.UNKNOWN,
                retryable=False,
            ) from exc

        if response.status_code != 200:
            raise normalize_http_error(response.status_code, response.text)

        try:
            return response.json()
        except Exception as exc:
            raise OpenAICompatTransportError(
                f"Failed to parse JSON response: {exc}",
                status_code=response.status_code,
                category=ErrorCategory.UNKNOWN,
            ) from exc

    def _parse_response(self, data: dict[str, Any]) -> dict[str, Any]:
        """Extract ToolLoopBackend-compatible fields from Chat Completions response.

        Captures ``usage`` from the response for benchmark accounting.
        """
        try:
            choice = data["choices"][0]
            message = choice["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise OpenAICompatTransportError(
                f"Malformed response: missing choices[0].message: {exc}",
                category=ErrorCategory.UNKNOWN,
            ) from exc

        # Capture usage for benchmark accounting.
        # Non-streaming usage is confirmed for all providers.
        # Streaming usage on bedrock-mantle is UNVERIFIED —
        # if absent, this is None (not an error).
        self._last_usage = data.get("usage")

        return {
            "content": message.get("content"),
            "tool_calls": message.get("tool_calls"),
        }
