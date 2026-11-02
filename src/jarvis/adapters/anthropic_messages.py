"""Anthropic Messages adapter behind CONTRACT-04."""
from __future__ import annotations

from collections.abc import Iterator
import json
from typing import Any


class AnthropicProviderResponseError(RuntimeError):
    """Anthropic failed or did not complete a provider-neutral response."""

    def __init__(
        self, message: str, *, code: str = "PROVIDER_RESPONSE_INVALID",
        detail: str = "",
    ):
        self.code = code
        self.detail = detail
        super().__init__(message)


def _safe_api_detail(exc: Exception) -> str:
    """Keep only Anthropic's normalized error type/message, never raw payloads."""
    body = getattr(exc, "body", None)
    error_type = ""
    message = ""
    if isinstance(body, dict):
        nested = body.get("error")
        if isinstance(nested, dict):
            raw_type = nested.get("type")
            raw_message = nested.get("message")
            if isinstance(raw_type, str):
                error_type = raw_type.strip()
            if isinstance(raw_message, str):
                message = raw_message.strip()
    parts = [part for part in (error_type, message) if part]
    detail = ": ".join(parts)
    detail = " ".join(detail.split())
    return detail[:500]


def _api_error_code(exc: Exception) -> str:
    status = getattr(exc, "status_code", None)
    body = getattr(exc, "body", None)
    error_type = None
    if isinstance(body, dict):
        nested = body.get("error")
        if isinstance(nested, dict):
            error_type = nested.get("type")
    message = str(exc).lower()
    if (status == 402 or error_type == "billing_error"
            or "credit balance" in message
            or "spend limit" in message
            or "billing" in message):
        return "BILLING_UNAVAILABLE"
    if status == 400:
        return "PROVIDER_REQUEST_INVALID"
    if status == 401:
        return "AUTHENTICATION_FAILED"
    if status == 403:
        return "PERMISSION_INSUFFICIENT"
    if status == 404:
        return "MODEL_NOT_AVAILABLE"
    if status == 429:
        return "RATE_LIMITED"
    if isinstance(status, int) and status >= 500:
        return "PROVIDER_UNAVAILABLE"
    name = type(exc).__name__.lower()
    if "timeout" in name:
        return "PROVIDER_TIMEOUT"
    if "connection" in name:
        return "PROVIDER_UNAVAILABLE"
    return "PROVIDER_REQUEST_FAILED"


def _anthropic_schema(value):
    """Normalize provider-specific JSON Schema quirks without changing Core schema."""
    if isinstance(value, list):
        return [_anthropic_schema(item) for item in value]
    if not isinstance(value, dict):
        return value

    node = {
        key: _anthropic_schema(item)
        for key, item in value.items()
        if key not in {"type", "enum"}
    }
    declared_type = value.get("type")
    enum = value.get("enum")

    if (isinstance(declared_type, list)
            and "null" in declared_type
            and isinstance(enum, list)
            and None in enum):
        non_null_types = [item for item in declared_type if item != "null"]
        non_null_enum = [item for item in enum if item is not None]
        if not non_null_types:
            return {**node, "type": "null"}

        typed_branch = {
            "type": (
                non_null_types[0]
                if len(non_null_types) == 1
                else non_null_types
            )
        }
        if non_null_enum:
            typed_branch["enum"] = non_null_enum
        node["anyOf"] = [
            typed_branch,
            {"type": "null"},
        ]
        return node

    if "type" in value:
        node["type"] = _anthropic_schema(declared_type)
    if "enum" in value:
        node["enum"] = _anthropic_schema(enum)
    return node


def _normalize_messages(messages: list[dict]) -> tuple[str | None, list[dict]]:
    if not isinstance(messages, list) or not messages:
        raise ValueError("At least one message is required")

    system_parts: list[str] = []
    normalized: list[dict] = []
    for item in messages:
        if not isinstance(item, dict):
            raise ValueError("invalid_message")
        role = item.get("role")
        content = item.get("content")
        if role not in {"developer", "system", "user", "assistant"}:
            raise ValueError("unsupported_message_role")
        if not isinstance(content, str) or not content:
            raise ValueError("invalid_message_content")
        if role in {"developer", "system"}:
            system_parts.append(content)
        else:
            normalized.append({"role": role, "content": content})

    if not normalized:
        raise ValueError("At least one user/assistant message is required")
    system = "\n\n".join(system_parts) if system_parts else None
    return system, normalized


class AnthropicMessagesAdapter:
    def __init__(self, client: Any, *, max_tokens: int = 8192):
        self.client = client
        self.max_tokens = max_tokens

    def stream_text(self, *, model: str, messages: list[dict]) -> Iterator[str]:
        if not isinstance(model, str) or not model.strip():
            raise ValueError("AI model must be configured")
        system, normalized = _normalize_messages(messages)
        kwargs = {
            "model": model.strip(),
            "max_tokens": self.max_tokens,
            "messages": normalized,
        }
        if system is not None:
            kwargs["system"] = system

        try:
            with self.client.messages.stream(**kwargs) as stream:
                for text in stream.text_stream:
                    if text:
                        yield text
                final = stream.get_final_message()
        except Exception as exc:
            raise AnthropicProviderResponseError(
                "Anthropic streaming request failed",
                code=_api_error_code(exc),
                detail=_safe_api_detail(exc),
            ) from exc

        stop_reason = getattr(final, "stop_reason", None)
        if stop_reason not in {"end_turn", "stop_sequence"}:
            raise AnthropicProviderResponseError(
                f"Provider did not complete safely: {stop_reason or 'unknown'}",
                code="PROVIDER_RESPONSE_INCOMPLETE",
            )

    def generate_json(
        self, *, model: str, messages: list[dict],
        schema_name: str, schema: dict,
    ) -> dict:
        if not isinstance(model, str) or not model.strip():
            raise ValueError("AI model must be configured")
        if not isinstance(schema_name, str) or not schema_name.strip():
            raise ValueError("schema_name is required")
        if not isinstance(schema, dict):
            raise ValueError("schema must be an object")

        system, normalized = _normalize_messages(messages)
        kwargs = {
            "model": model.strip(),
            "max_tokens": min(self.max_tokens, 4096),
            "messages": normalized,
            "output_config": {
                "format": {
                    "type": "json_schema",
                    "schema": _anthropic_schema(schema),
                }
            },
        }
        if system is not None:
            kwargs["system"] = system

        try:
            response = self.client.messages.create(**kwargs)
        except Exception as exc:
            raise AnthropicProviderResponseError(
                "Anthropic structured request failed",
                code=_api_error_code(exc),
                detail=_safe_api_detail(exc),
            ) from exc
        stop_reason = getattr(response, "stop_reason", None)
        if stop_reason not in {"end_turn", "stop_sequence"}:
            raise AnthropicProviderResponseError(
                f"Provider did not complete structured output safely: "
                f"{stop_reason or 'unknown'}",
                code="PROVIDER_RESPONSE_INCOMPLETE",
            )
        raw = next(
            (
                getattr(block, "text", None)
                for block in getattr(response, "content", [])
                if getattr(block, "type", None) == "text"
                and isinstance(getattr(block, "text", None), str)
            ),
            None,
        )
        if not isinstance(raw, str) or not raw or len(raw) > 18000:
            raise AnthropicProviderResponseError(
                "Provider returned invalid structured output",
                code="PROVIDER_RESPONSE_INVALID",
            )
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise AnthropicProviderResponseError(
                "Provider returned non-object structured output",
                code="PROVIDER_RESPONSE_INVALID",
            )
        return value
