"""
Tests for ``runner.transport.errors`` — error types and HTTP error normalization.

Covers:
    - Error category enum values
    - Exception hierarchy
    - normalize_http_error mapping for all documented status codes
    - Retryability flags
    - Response body truncation
    - Unknown status code handling
"""

from __future__ import annotations

import pytest

from runner.transport.errors import (
    ErrorCategory,
    OpenAICompatAuthError,
    OpenAICompatModelNotFoundError,
    OpenAICompatProviderError,
    OpenAICompatRateLimitError,
    OpenAICompatTransportError,
    normalize_http_error,
)


# ---------------------------------------------------------------------------
# Test: Error categories
# ---------------------------------------------------------------------------


class TestErrorCategories:
    """ErrorCategory enum completeness."""

    def test_all_categories_exist(self):
        expected = {
            "rate_limited", "provider_error", "auth_failure",
            "malformed_request", "model_not_found", "timeout", "unknown",
        }
        assert {c.value for c in ErrorCategory} == expected


# ---------------------------------------------------------------------------
# Test: Exception hierarchy
# ---------------------------------------------------------------------------


class TestExceptionHierarchy:
    """All transport exceptions inherit from OpenAICompatTransportError."""

    def test_auth_error_is_transport_error(self):
        assert issubclass(OpenAICompatAuthError, OpenAICompatTransportError)

    def test_rate_limit_error_is_transport_error(self):
        assert issubclass(OpenAICompatRateLimitError, OpenAICompatTransportError)

    def test_provider_error_is_transport_error(self):
        assert issubclass(OpenAICompatProviderError, OpenAICompatTransportError)

    def test_model_not_found_is_transport_error(self):
        assert issubclass(OpenAICompatModelNotFoundError, OpenAICompatTransportError)

    def test_base_error_carries_metadata(self):
        exc = OpenAICompatTransportError(
            "test",
            status_code=500,
            category=ErrorCategory.PROVIDER_ERROR,
            retryable=True,
            response_body="error detail",
        )
        assert exc.status_code == 500
        assert exc.category == ErrorCategory.PROVIDER_ERROR
        assert exc.retryable is True
        assert exc.response_body == "error detail"


# ---------------------------------------------------------------------------
# Test: HTTP error normalization
# ---------------------------------------------------------------------------


class TestNormalizeHttpError:
    """normalize_http_error maps status codes correctly."""

    @pytest.mark.parametrize(
        "status, expected_cls, expected_category, expected_retryable",
        [
            (400, OpenAICompatTransportError, ErrorCategory.MALFORMED_REQUEST, False),
            (401, OpenAICompatAuthError, ErrorCategory.AUTH_FAILURE, False),
            (403, OpenAICompatAuthError, ErrorCategory.AUTH_FAILURE, False),
            (404, OpenAICompatModelNotFoundError, ErrorCategory.MODEL_NOT_FOUND, False),
            (429, OpenAICompatRateLimitError, ErrorCategory.RATE_LIMITED, True),
            (500, OpenAICompatProviderError, ErrorCategory.PROVIDER_ERROR, True),
            (502, OpenAICompatProviderError, ErrorCategory.PROVIDER_ERROR, True),
            (503, OpenAICompatProviderError, ErrorCategory.PROVIDER_ERROR, True),
        ],
    )
    def test_known_status_codes(self, status, expected_cls, expected_category, expected_retryable):
        exc = normalize_http_error(status, "error body")
        assert isinstance(exc, expected_cls)
        assert exc.category == expected_category
        assert exc.retryable == expected_retryable
        assert exc.status_code == status

    def test_unknown_status_code(self):
        exc = normalize_http_error(418, "I'm a teapot")
        assert isinstance(exc, OpenAICompatTransportError)
        assert exc.category == ErrorCategory.UNKNOWN
        assert exc.retryable is False
        assert exc.status_code == 418

    def test_response_body_truncated(self):
        long_body = "x" * 1000
        exc = normalize_http_error(500, long_body)
        assert len(exc.response_body) == 500

    def test_empty_response_body(self):
        exc = normalize_http_error(403, "")
        assert exc.response_body == ""

    def test_error_message_includes_status(self):
        exc = normalize_http_error(429, "rate limit exceeded")
        assert "429" in str(exc)
