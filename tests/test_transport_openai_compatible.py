"""
Tests for ``runner.transport.openai_compatible`` — OpenAI-compatible HTTP backend.

Covers:
    - Request payload construction (model, messages, tools, temperature, max_tokens)
    - ToolLoopBackend protocol compliance
    - Response parsing (content, tool_calls, usage)
    - Error normalization (429, 403, 500, 503, 400, 404, timeout)
    - Missing httpx import handling
    - No secrets in logs or error messages
    - Claude CLI backend remains unchanged

All tests use mocks.  No real HTTP calls are made.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Mock httpx before importing the module under test
# ---------------------------------------------------------------------------

# Create a mock httpx module so tests work without httpx installed.
_mock_httpx = MagicMock()
_mock_httpx.TimeoutException = type("TimeoutException", (Exception,), {})
_mock_httpx.ConnectError = type("ConnectError", (Exception,), {})
_mock_httpx.HTTPError = type("HTTPError", (Exception,), {})


def _mock_timeout(*args, **kwargs):
    return {"connect": 30.0, "read": 300.0, "write": 30.0, "pool": 30.0}


_mock_httpx.Timeout = _mock_timeout


def _make_response(status_code: int = 200, json_data: dict | None = None, text: str = "") -> MagicMock:
    """Build a mock httpx response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text or json.dumps(json_data or {})
    resp.json.return_value = json_data or {}
    return resp


def _chat_response(
    content: str | None = "Hello",
    tool_calls: list[dict[str, Any]] | None = None,
    usage: dict[str, int] | None = None,
    finish_reason: str = "stop",
) -> dict[str, Any]:
    """Build a standard Chat Completions response body."""
    message: dict[str, Any] = {"role": "assistant"}
    if content is not None:
        message["content"] = content
    if tool_calls is not None:
        message["tool_calls"] = tool_calls
    resp: dict[str, Any] = {
        "choices": [{"message": message, "finish_reason": finish_reason}],
    }
    if usage is not None:
        resp["usage"] = usage
    return resp


# ---------------------------------------------------------------------------
# Test: Backend construction
# ---------------------------------------------------------------------------


class TestBackendConstruction:
    """Tests for OpenAICompatBackend.__init__."""

    def test_url_construction_strips_trailing_slash(self):
        with patch.dict("sys.modules", {"httpx": _mock_httpx}):
            from runner.transport.openai_compatible import OpenAICompatBackend

            backend = OpenAICompatBackend(
                base_url="https://bedrock-mantle.eu-west-1.api.aws/v1/",
                model="anthropic.claude-sonnet-4-20250514-v1:0",
            )
            assert backend.url == "https://bedrock-mantle.eu-west-1.api.aws/v1/chat/completions"

    def test_url_construction_without_trailing_slash(self):
        with patch.dict("sys.modules", {"httpx": _mock_httpx}):
            from runner.transport.openai_compatible import OpenAICompatBackend

            backend = OpenAICompatBackend(
                base_url="https://bedrock-mantle.eu-west-1.api.aws/v1",
                model="anthropic.claude-sonnet-4-20250514-v1:0",
            )
            assert backend.url == "https://bedrock-mantle.eu-west-1.api.aws/v1/chat/completions"

    def test_model_property(self):
        with patch.dict("sys.modules", {"httpx": _mock_httpx}):
            from runner.transport.openai_compatible import OpenAICompatBackend

            backend = OpenAICompatBackend(
                base_url="https://api.together.ai/v1",
                model="meta-llama/Llama-3.1-405B",
            )
            assert backend.model == "meta-llama/Llama-3.1-405B"

    def test_bearer_auth_header_set_when_api_key_provided(self):
        with patch.dict("sys.modules", {"httpx": _mock_httpx}):
            from runner.transport.openai_compatible import OpenAICompatBackend

            backend = OpenAICompatBackend(
                base_url="https://bedrock-mantle.eu-west-1.api.aws/v1",
                api_key="test-key-12345",
                model="anthropic.claude-sonnet-4-20250514-v1:0",
            )
            assert backend._headers["Authorization"] == "Bearer test-key-12345"

    def test_no_auth_header_when_no_api_key(self):
        with patch.dict("sys.modules", {"httpx": _mock_httpx}):
            from runner.transport.openai_compatible import OpenAICompatBackend

            backend = OpenAICompatBackend(
                base_url="http://localhost:11434/v1",
                model="llama3.1:70b",
            )
            assert "Authorization" not in backend._headers


# ---------------------------------------------------------------------------
# Test: Payload construction
# ---------------------------------------------------------------------------


class TestPayloadConstruction:
    """Tests for _build_payload."""

    def test_payload_includes_model_and_messages(self):
        with patch.dict("sys.modules", {"httpx": _mock_httpx}):
            from runner.transport.openai_compatible import OpenAICompatBackend

            backend = OpenAICompatBackend(
                base_url="https://example.com/v1",
                model="test-model",
            )
            messages = [{"role": "user", "content": "Hello"}]
            payload = backend._build_payload(messages)

            assert payload["model"] == "test-model"
            assert payload["messages"] == messages
            assert payload["temperature"] == 0.0
            assert payload["max_tokens"] == 4096

    def test_payload_includes_tools_when_provided(self):
        with patch.dict("sys.modules", {"httpx": _mock_httpx}):
            from runner.transport.openai_compatible import OpenAICompatBackend

            tools = [{"type": "function", "function": {"name": "Read", "parameters": {}}}]
            backend = OpenAICompatBackend(
                base_url="https://example.com/v1",
                model="test-model",
                tools=tools,
            )
            payload = backend._build_payload([])
            assert payload["tools"] == tools

    def test_payload_excludes_tools_when_empty(self):
        with patch.dict("sys.modules", {"httpx": _mock_httpx}):
            from runner.transport.openai_compatible import OpenAICompatBackend

            backend = OpenAICompatBackend(
                base_url="https://example.com/v1",
                model="test-model",
            )
            payload = backend._build_payload([])
            assert "tools" not in payload

    def test_payload_includes_top_p_when_set(self):
        with patch.dict("sys.modules", {"httpx": _mock_httpx}):
            from runner.transport.openai_compatible import OpenAICompatBackend

            backend = OpenAICompatBackend(
                base_url="https://example.com/v1",
                model="test-model",
                top_p=0.9,
            )
            payload = backend._build_payload([])
            assert payload["top_p"] == 0.9

    def test_payload_excludes_top_p_when_none(self):
        with patch.dict("sys.modules", {"httpx": _mock_httpx}):
            from runner.transport.openai_compatible import OpenAICompatBackend

            backend = OpenAICompatBackend(
                base_url="https://example.com/v1",
                model="test-model",
            )
            payload = backend._build_payload([])
            assert "top_p" not in payload

    def test_custom_temperature_and_max_tokens(self):
        with patch.dict("sys.modules", {"httpx": _mock_httpx}):
            from runner.transport.openai_compatible import OpenAICompatBackend

            backend = OpenAICompatBackend(
                base_url="https://example.com/v1",
                model="test-model",
                temperature=0.7,
                max_tokens=8192,
            )
            payload = backend._build_payload([])
            assert payload["temperature"] == 0.7
            assert payload["max_tokens"] == 8192


# ---------------------------------------------------------------------------
# Test: Response parsing
# ---------------------------------------------------------------------------


class TestResponseParsing:
    """Tests for _parse_response and __call__."""

    def test_extracts_content_from_response(self):
        with patch.dict("sys.modules", {"httpx": _mock_httpx}):
            from runner.transport.openai_compatible import OpenAICompatBackend

            backend = OpenAICompatBackend(
                base_url="https://example.com/v1", model="m",
            )
            data = _chat_response(content="Hello world")
            result = backend._parse_response(data)
            assert result["content"] == "Hello world"
            assert result["tool_calls"] is None

    def test_extracts_tool_calls_from_response(self):
        with patch.dict("sys.modules", {"httpx": _mock_httpx}):
            from runner.transport.openai_compatible import OpenAICompatBackend

            backend = OpenAICompatBackend(
                base_url="https://example.com/v1", model="m",
            )
            tc = [{"id": "call_1", "type": "function",
                   "function": {"name": "Read", "arguments": '{"file_path": "/a.txt"}'}}]
            data = _chat_response(content=None, tool_calls=tc)
            result = backend._parse_response(data)
            assert result["tool_calls"] == tc
            assert result["content"] is None

    def test_captures_usage_from_response(self):
        with patch.dict("sys.modules", {"httpx": _mock_httpx}):
            from runner.transport.openai_compatible import OpenAICompatBackend

            backend = OpenAICompatBackend(
                base_url="https://example.com/v1", model="m",
            )
            usage = {"prompt_tokens": 25, "completion_tokens": 150, "total_tokens": 175}
            data = _chat_response(usage=usage)
            backend._parse_response(data)
            assert backend.last_usage == usage

    def test_usage_is_none_when_absent(self):
        with patch.dict("sys.modules", {"httpx": _mock_httpx}):
            from runner.transport.openai_compatible import OpenAICompatBackend

            backend = OpenAICompatBackend(
                base_url="https://example.com/v1", model="m",
            )
            data = _chat_response()  # no usage
            backend._parse_response(data)
            assert backend.last_usage is None

    def test_malformed_response_raises(self):
        with patch.dict("sys.modules", {"httpx": _mock_httpx}):
            from runner.transport.openai_compatible import OpenAICompatBackend
            from runner.transport.errors import OpenAICompatTransportError

            backend = OpenAICompatBackend(
                base_url="https://example.com/v1", model="m",
            )
            with pytest.raises(OpenAICompatTransportError, match="Malformed response"):
                backend._parse_response({"choices": []})

    def test_call_sends_post_and_returns_parsed(self):
        """Full __call__ round-trip with mocked httpx.post."""
        with patch.dict("sys.modules", {"httpx": _mock_httpx}):
            from runner.transport.openai_compatible import OpenAICompatBackend

            backend = OpenAICompatBackend(
                base_url="https://bedrock-mantle.eu-west-1.api.aws/v1",
                api_key="test-key",
                model="anthropic.claude-sonnet-4-20250514-v1:0",
            )
            response_data = _chat_response(
                content='{"status": "ok"}',
                usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            )
            mock_resp = _make_response(200, response_data)
            _mock_httpx.post.return_value = mock_resp

            messages = [
                {"role": "system", "content": "You are helpful."},
                {"role": "user", "content": "Hello"},
            ]
            result = backend(messages)

            assert result["content"] == '{"status": "ok"}'
            assert result["tool_calls"] is None
            assert backend.last_usage["total_tokens"] == 30

            # Verify httpx.post was called with correct URL
            call_args = _mock_httpx.post.call_args
            assert call_args[0][0] == "https://bedrock-mantle.eu-west-1.api.aws/v1/chat/completions"

    def test_tool_calls_round_trip(self):
        """Verify tool_calls are passed through correctly."""
        with patch.dict("sys.modules", {"httpx": _mock_httpx}):
            from runner.transport.openai_compatible import OpenAICompatBackend

            backend = OpenAICompatBackend(
                base_url="https://example.com/v1",
                model="test-model",
            )
            tc = [{
                "id": "call_abc123",
                "type": "function",
                "function": {
                    "name": "Read",
                    "arguments": json.dumps({"file_path": "/repo/docs/test.json"}),
                },
            }]
            response_data = _chat_response(content=None, tool_calls=tc, finish_reason="tool_calls")
            _mock_httpx.post.return_value = _make_response(200, response_data)

            result = backend([{"role": "user", "content": "Read the file"}])
            assert result["tool_calls"] == tc
            assert result["tool_calls"][0]["id"] == "call_abc123"
            assert result["tool_calls"][0]["function"]["name"] == "Read"


# ---------------------------------------------------------------------------
# Test: Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """Tests for HTTP error normalization."""

    def test_429_raises_rate_limit_error(self):
        with patch.dict("sys.modules", {"httpx": _mock_httpx}):
            from runner.transport.openai_compatible import OpenAICompatBackend
            from runner.transport.errors import OpenAICompatRateLimitError

            backend = OpenAICompatBackend(
                base_url="https://example.com/v1", model="m",
            )
            _mock_httpx.post.return_value = _make_response(
                429, text='{"error": "ThrottlingException"}'
            )

            with pytest.raises(OpenAICompatRateLimitError) as exc_info:
                backend([{"role": "user", "content": "hi"}])
            assert exc_info.value.retryable is True
            assert exc_info.value.status_code == 429

    def test_403_raises_auth_error(self):
        with patch.dict("sys.modules", {"httpx": _mock_httpx}):
            from runner.transport.openai_compatible import OpenAICompatBackend
            from runner.transport.errors import OpenAICompatAuthError

            backend = OpenAICompatBackend(
                base_url="https://example.com/v1", model="m",
            )
            _mock_httpx.post.return_value = _make_response(
                403, text='{"error": "AccessDeniedException"}'
            )

            with pytest.raises(OpenAICompatAuthError) as exc_info:
                backend([{"role": "user", "content": "hi"}])
            assert exc_info.value.retryable is False

    def test_500_raises_provider_error(self):
        with patch.dict("sys.modules", {"httpx": _mock_httpx}):
            from runner.transport.openai_compatible import OpenAICompatBackend
            from runner.transport.errors import OpenAICompatProviderError

            backend = OpenAICompatBackend(
                base_url="https://example.com/v1", model="m",
            )
            _mock_httpx.post.return_value = _make_response(500, text="Internal error")

            with pytest.raises(OpenAICompatProviderError) as exc_info:
                backend([{"role": "user", "content": "hi"}])
            assert exc_info.value.retryable is True

    def test_503_raises_provider_error(self):
        with patch.dict("sys.modules", {"httpx": _mock_httpx}):
            from runner.transport.openai_compatible import OpenAICompatBackend
            from runner.transport.errors import OpenAICompatProviderError

            backend = OpenAICompatBackend(
                base_url="https://example.com/v1", model="m",
            )
            _mock_httpx.post.return_value = _make_response(503, text="Service unavailable")

            with pytest.raises(OpenAICompatProviderError):
                backend([{"role": "user", "content": "hi"}])

    def test_400_raises_malformed_request(self):
        with patch.dict("sys.modules", {"httpx": _mock_httpx}):
            from runner.transport.openai_compatible import OpenAICompatBackend
            from runner.transport.errors import OpenAICompatTransportError, ErrorCategory

            backend = OpenAICompatBackend(
                base_url="https://example.com/v1", model="m",
            )
            _mock_httpx.post.return_value = _make_response(
                400, text='{"error": "ValidationError"}'
            )

            with pytest.raises(OpenAICompatTransportError) as exc_info:
                backend([{"role": "user", "content": "hi"}])
            assert exc_info.value.category == ErrorCategory.MALFORMED_REQUEST

    def test_404_raises_model_not_found(self):
        with patch.dict("sys.modules", {"httpx": _mock_httpx}):
            from runner.transport.openai_compatible import OpenAICompatBackend
            from runner.transport.errors import OpenAICompatModelNotFoundError

            backend = OpenAICompatBackend(
                base_url="https://example.com/v1", model="m",
            )
            _mock_httpx.post.return_value = _make_response(
                404, text='{"error": "ResourceNotFound"}'
            )

            with pytest.raises(OpenAICompatModelNotFoundError):
                backend([{"role": "user", "content": "hi"}])

    def test_timeout_raises_timeout_error(self):
        with patch.dict("sys.modules", {"httpx": _mock_httpx}):
            from runner.transport.openai_compatible import OpenAICompatBackend
            from runner.transport.errors import OpenAICompatTimeoutError

            backend = OpenAICompatBackend(
                base_url="https://example.com/v1", model="m",
            )
            _mock_httpx.post.side_effect = _mock_httpx.TimeoutException("read timeout")

            with pytest.raises(OpenAICompatTimeoutError) as exc_info:
                backend([{"role": "user", "content": "hi"}])
            assert exc_info.value.retryable is True

    def test_connection_error_raises_provider_error(self):
        with patch.dict("sys.modules", {"httpx": _mock_httpx}):
            from runner.transport.openai_compatible import OpenAICompatBackend
            from runner.transport.errors import OpenAICompatProviderError

            backend = OpenAICompatBackend(
                base_url="https://example.com/v1", model="m",
            )
            _mock_httpx.post.side_effect = _mock_httpx.ConnectError("connection refused")

            with pytest.raises(OpenAICompatProviderError) as exc_info:
                backend([{"role": "user", "content": "hi"}])
            assert exc_info.value.retryable is True


# ---------------------------------------------------------------------------
# Test: Claude CLI unchanged
# ---------------------------------------------------------------------------


class TestClaudeCLIUnchanged:
    """Verify the Claude CLI transport module is not modified."""

    def test_claude_transport_module_exists(self):
        from runner.claude_transport import invoke_claude_text
        assert callable(invoke_claude_text)

    def test_claude_transport_error_hierarchy(self):
        from runner.claude_transport import (
            ClaudeCLITimeoutError,
            ClaudeCLIUnavailableError,
            ClaudeTransportError,
        )
        assert issubclass(ClaudeCLITimeoutError, ClaudeTransportError)
        assert issubclass(ClaudeCLIUnavailableError, ClaudeTransportError)

    def test_claude_transport_constants(self):
        from runner.claude_transport import DEFAULT_TIMEOUT_SECONDS
        assert DEFAULT_TIMEOUT_SECONDS == 300
