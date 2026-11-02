"""Anthropic Messages adapter behind CONTRACT-04."""
from __future__ import annotations

from collections.abc import Iterator
import json
from typing import Any


class AnthropicProviderResponseError(RuntimeError):
    """Anthropic failed or did not complete a provider-neutral response."""


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

        with self.client.messages.stream(**kwargs) as stream:
            for text in stream.text_stream:
                if text:
                    yield text
            final = stream.get_final_message()

        stop_reason = getattr(final, "stop_reason", None)
        if stop_reason not in {"end_turn", "stop_sequence"}:
            raise AnthropicProviderResponseError(
                f"Provider did not complete safely: {stop_reason or 'unknown'}"
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
                    "schema": schema,
                }
            },
        }
        if system is not None:
            kwargs["system"] = system

        response = self.client.messages.create(**kwargs)
        stop_reason = getattr(response, "stop_reason", None)
        if stop_reason not in {"end_turn", "stop_sequence"}:
            raise AnthropicProviderResponseError(
                f"Provider did not complete structured output safely: "
                f"{stop_reason or 'unknown'}"
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
                "Provider returned invalid structured output"
            )
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise AnthropicProviderResponseError(
                "Provider returned non-object structured output"
            )
        return value
