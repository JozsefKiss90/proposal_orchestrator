"""
Error types and HTTP error normalization for OpenAI-compatible backends.

Maps provider HTTP error codes to structured transport exceptions with
orchestrator-aligned failure categories.  These categories correspond
to the SkillResult failure taxonomy defined in CLAUDE.md Section 17.4.1.

Constitutional authority:
    Subordinate to CLAUDE.md.  This module defines transport-layer
    error types only.  It does not evaluate gates, invoke agents,
    write canonical artifacts, or modify scheduler state.
"""

from __future__ import annotations

from enum import Enum


# ---------------------------------------------------------------------------
# Error categories
# ---------------------------------------------------------------------------


class ErrorCategory(str, Enum):
    """Failure categories aligned with the orchestrator's SkillResult taxonomy.

    These map to CLAUDE.md Section 17.4.1 failure categories and to the
    Bedrock error taxonomy in the Phase E implementation brief.
    """

    RATE_LIMITED = "rate_limited"
    """HTTP 429 / ThrottlingException.  Retryable."""

    PROVIDER_ERROR = "provider_error"
    """HTTP 500/503 / ServiceUnavailable / InternalFailure.  Retryable."""

    AUTH_FAILURE = "auth_failure"
    """HTTP 401/403 / AccessDeniedException / InvalidClientTokenId.  Non-retryable."""

    MALFORMED_REQUEST = "malformed_request"
    """HTTP 400 / ValidationError.  Non-retryable."""

    MODEL_NOT_FOUND = "model_not_found"
    """HTTP 404 / ResourceNotFound.  Non-retryable."""

    TIMEOUT = "timeout"
    """Connection or read timeout.  Retryable per policy."""

    UNKNOWN = "unknown"
    """Unclassified error."""


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------


class OpenAICompatTransportError(Exception):
    """Base exception for OpenAI-compatible transport failures.

    Parallel to ``ClaudeTransportError`` in ``runner.claude_transport``.
    Carries structured metadata for diagnostic reporting.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        retryable: bool = False,
        response_body: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.category = category
        self.retryable = retryable
        self.response_body = response_body


class OpenAICompatAuthError(OpenAICompatTransportError):
    """Credential or permission failure (HTTP 401/403)."""


class OpenAICompatRateLimitError(OpenAICompatTransportError):
    """Rate limit exceeded (HTTP 429 / ThrottlingException)."""


class OpenAICompatProviderError(OpenAICompatTransportError):
    """Provider-side error (HTTP 500/503)."""


class OpenAICompatTimeoutError(OpenAICompatTransportError):
    """Request timed out."""


class OpenAICompatModelNotFoundError(OpenAICompatTransportError):
    """Model not available (HTTP 404 / ResourceNotFound)."""


# ---------------------------------------------------------------------------
# HTTP error normalization
# ---------------------------------------------------------------------------

#: Mapping from HTTP status codes to (exception class, category, retryable).
_STATUS_MAP: dict[int, tuple[type[OpenAICompatTransportError], ErrorCategory, bool]] = {
    400: (OpenAICompatTransportError, ErrorCategory.MALFORMED_REQUEST, False),
    401: (OpenAICompatAuthError, ErrorCategory.AUTH_FAILURE, False),
    403: (OpenAICompatAuthError, ErrorCategory.AUTH_FAILURE, False),
    404: (OpenAICompatModelNotFoundError, ErrorCategory.MODEL_NOT_FOUND, False),
    429: (OpenAICompatRateLimitError, ErrorCategory.RATE_LIMITED, True),
    500: (OpenAICompatProviderError, ErrorCategory.PROVIDER_ERROR, True),
    502: (OpenAICompatProviderError, ErrorCategory.PROVIDER_ERROR, True),
    503: (OpenAICompatProviderError, ErrorCategory.PROVIDER_ERROR, True),
}


def normalize_http_error(
    status_code: int,
    response_body: str = "",
) -> OpenAICompatTransportError:
    """Map an HTTP status code to a typed transport exception.

    Parameters
    ----------
    status_code:
        The HTTP response status code.
    response_body:
        The response body text (truncated for diagnostics).

    Returns
    -------
    OpenAICompatTransportError
        A typed exception with category and retryability metadata.
    """
    body_snippet = response_body[:500] if response_body else ""

    if status_code in _STATUS_MAP:
        exc_cls, category, retryable = _STATUS_MAP[status_code]
        return exc_cls(
            f"HTTP {status_code}: {body_snippet}",
            status_code=status_code,
            category=category,
            retryable=retryable,
            response_body=body_snippet,
        )

    # Default: non-retryable unknown error
    return OpenAICompatTransportError(
        f"HTTP {status_code}: {body_snippet}",
        status_code=status_code,
        category=ErrorCategory.UNKNOWN,
        retryable=False,
        response_body=body_snippet,
    )
