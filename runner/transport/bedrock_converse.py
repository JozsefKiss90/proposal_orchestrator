"""
Native AWS Bedrock Converse API backend.

Implements the :class:`~runner.transport.tool_loop.ToolLoopBackend`
protocol by calling ``bedrock-runtime.converse()`` via ``boto3``.

This bypasses the bedrock-mantle OpenAI-compatible proxy and uses the
native Bedrock API directly with IAM credentials (standard AWS
credential chain: env vars, ~/.aws/credentials, instance profile, etc.).

Supports inference profiles (e.g. ``us.anthropic.claude-sonnet-4-6``)
which are required for on-demand throughput with newer Anthropic models.

This is a transport adapter.  It contains message format conversion,
boto3 invocation, and response extraction.  It does not perform domain
reasoning, evaluate gates, write canonical artifacts, or modify
scheduler state.

Requires ``boto3`` (``pip install boto3``).

Constitutional authority:
    Subordinate to CLAUDE.md.  Transport-layer only.
"""

from __future__ import annotations

import json
import logging
from typing import Any

try:
    import boto3
    from botocore.exceptions import ClientError, BotoCoreError
except ImportError:
    boto3 = None  # type: ignore[assignment]

from runner.transport.errors import (
    ErrorCategory,
    OpenAICompatProviderError,
    OpenAICompatTimeoutError,
    OpenAICompatTransportError,
)

logger = logging.getLogger(__name__)


class BedrockConverseBackend:
    """Backend for the native AWS Bedrock Converse API.

    Conforms to the :class:`~runner.transport.tool_loop.ToolLoopBackend`
    protocol: callable with ``(messages) -> {"content": ..., "tool_calls": ...}``.

    Uses ``boto3.client('bedrock-runtime').converse()`` with IAM
    credentials from the standard AWS credential chain.

    Parameters
    ----------
    model_id:
        Bedrock model ID or inference profile ID.
        Examples: ``us.anthropic.claude-sonnet-4-6``,
        ``us.anthropic.claude-haiku-4-5-20251001-v1:0``.
    region_name:
        AWS region.  Default ``us-east-1``.
    temperature:
        Sampling temperature.  Default ``0.0``.
    max_tokens:
        Maximum completion tokens.  Default ``4096``.
    tools:
        Optional list of OpenAI-format tool schemas.  Converted to
        Bedrock Converse ``toolConfig`` format.
    """

    def __init__(
        self,
        *,
        model_id: str,
        region_name: str = "us-east-1",
        temperature: float = 0.0,
        max_tokens: int = 4096,
        tools: list[dict[str, Any]] | None = None,
    ) -> None:
        if boto3 is None:
            raise ImportError(
                "boto3 is required for BedrockConverseBackend. "
                "Install it with: pip install boto3"
            )

        self._model_id = model_id
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._tools = tools or []
        self._last_usage: dict[str, int] | None = None

        self._client = boto3.client(
            "bedrock-runtime",
            region_name=region_name,
        )

    # -- ToolLoopBackend protocol ------------------------------------------

    def __call__(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        """Send a Converse request and return a ToolLoopBackend-compatible response."""
        converse_kwargs = self._build_request(messages)

        try:
            response = self._client.converse(**converse_kwargs)
        except ClientError as exc:
            raise self._classify_client_error(exc) from exc
        except BotoCoreError as exc:
            raise OpenAICompatProviderError(
                f"Bedrock Converse failed: {exc}",
                category=ErrorCategory.PROVIDER_ERROR,
                retryable=True,
            ) from exc

        return self._parse_response(response)

    # -- Public properties -------------------------------------------------

    @property
    def last_usage(self) -> dict[str, int] | None:
        """Token usage from the most recent request."""
        return self._last_usage

    @property
    def model(self) -> str:
        """The configured model/inference-profile ID."""
        return self._model_id

    # -- Message conversion ------------------------------------------------

    def _build_request(
        self, messages: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Convert OpenAI messages to Converse API kwargs."""
        system_blocks: list[dict[str, Any]] = []
        converse_messages: list[dict[str, Any]] = []

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role == "system":
                system_blocks.append({"text": content or ""})

            elif role == "user":
                converse_messages.append({
                    "role": "user",
                    "content": [{"text": content or ""}],
                })

            elif role == "assistant":
                blocks: list[dict[str, Any]] = []
                if content:
                    blocks.append({"text": content})
                # Convert OpenAI tool_calls to Converse toolUse blocks
                for tc in msg.get("tool_calls", []):
                    func = tc.get("function", {})
                    raw_args = func.get("arguments", "{}")
                    if isinstance(raw_args, str):
                        try:
                            parsed_args = json.loads(raw_args)
                        except (json.JSONDecodeError, TypeError):
                            parsed_args = {}
                    else:
                        parsed_args = raw_args
                    blocks.append({
                        "toolUse": {
                            "toolUseId": tc.get("id", ""),
                            "name": func.get("name", ""),
                            "input": parsed_args,
                        }
                    })
                if blocks:
                    converse_messages.append({
                        "role": "assistant",
                        "content": blocks,
                    })

            elif role == "tool":
                # Convert OpenAI tool result to Converse toolResult
                tool_call_id = msg.get("tool_call_id", "")
                tool_content = msg.get("content", "")
                converse_messages.append({
                    "role": "user",
                    "content": [{
                        "toolResult": {
                            "toolUseId": tool_call_id,
                            "content": [{"text": tool_content}],
                        }
                    }],
                })

        kwargs: dict[str, Any] = {
            "modelId": self._model_id,
            "messages": converse_messages,
            "inferenceConfig": {
                "maxTokens": self._max_tokens,
                "temperature": self._temperature,
            },
        }

        if system_blocks:
            kwargs["system"] = system_blocks

        if self._tools:
            kwargs["toolConfig"] = {
                "tools": [self._convert_tool(t) for t in self._tools],
            }

        return kwargs

    @staticmethod
    def _convert_tool(openai_tool: dict[str, Any]) -> dict[str, Any]:
        """Convert an OpenAI tool schema to Converse toolSpec format."""
        func = openai_tool.get("function", {})
        params = func.get("parameters", {})

        # Build Converse inputSchema from OpenAI parameters
        input_schema: dict[str, Any] = {
            "json": params if params else {"type": "object", "properties": {}},
        }

        return {
            "toolSpec": {
                "name": func.get("name", ""),
                "description": func.get("description", ""),
                "inputSchema": input_schema,
            }
        }

    # -- Response parsing --------------------------------------------------

    def _parse_response(self, response: dict[str, Any]) -> dict[str, Any]:
        """Convert Converse response to ToolLoopBackend format."""
        # Capture usage
        usage = response.get("usage", {})
        if usage:
            self._last_usage = {
                "prompt_tokens": usage.get("inputTokens", 0),
                "completion_tokens": usage.get("outputTokens", 0),
                "total_tokens": usage.get("totalTokens", 0),
            }

        output = response.get("output", {})
        message = output.get("message", {})
        content_blocks = message.get("content", [])

        text_parts: list[str] = []
        tool_calls: list[dict[str, Any]] = []

        for block in content_blocks:
            if "text" in block:
                text_parts.append(block["text"])
            elif "toolUse" in block:
                tu = block["toolUse"]
                tool_calls.append({
                    "id": tu.get("toolUseId", ""),
                    "type": "function",
                    "function": {
                        "name": tu.get("name", ""),
                        "arguments": json.dumps(tu.get("input", {})),
                    },
                })

        return {
            "content": "\n".join(text_parts) if text_parts else None,
            "tool_calls": tool_calls if tool_calls else None,
        }

    # -- Error classification ----------------------------------------------

    @staticmethod
    def _classify_client_error(exc: ClientError) -> OpenAICompatTransportError:
        """Map boto3 ClientError to transport exception."""
        code = exc.response.get("Error", {}).get("Code", "")
        message = exc.response.get("Error", {}).get("Message", str(exc))
        status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode", 0)

        if code in ("ThrottlingException", "TooManyRequestsException"):
            return OpenAICompatTransportError(
                f"Bedrock rate limited: {message}",
                category=ErrorCategory.RATE_LIMITED,
                retryable=True,
            )
        if code in ("AccessDeniedException", "UnrecognizedClientException"):
            return OpenAICompatTransportError(
                f"Bedrock auth failed: {message}",
                category=ErrorCategory.AUTH_FAILURE,
                retryable=False,
            )
        if code in ("ResourceNotFoundException", "ModelNotReadyException"):
            return OpenAICompatTransportError(
                f"Bedrock model not found: {message}",
                category=ErrorCategory.MODEL_NOT_FOUND,
                retryable=False,
            )
        if code == "ValidationException":
            return OpenAICompatTransportError(
                f"Bedrock validation error: {message}",
                category=ErrorCategory.MALFORMED_REQUEST,
                retryable=False,
            )
        if code in ("InternalServerException", "ServiceUnavailableException"):
            return OpenAICompatProviderError(
                f"Bedrock server error: {message}",
                category=ErrorCategory.PROVIDER_ERROR,
                retryable=True,
            )

        return OpenAICompatTransportError(
            f"Bedrock error ({code}): {message}",
            category=ErrorCategory.UNKNOWN,
            retryable=False,
        )
