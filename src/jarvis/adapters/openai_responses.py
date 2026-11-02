"""OpenAI Responses streaming adapter for TB-01.

Provider-specific events do not leak into the conversation persistence API.
"""

from __future__ import annotations

from collections.abc import Iterator
import json
from typing import Any


class ProviderResponseError(RuntimeError):
    """The provider failed or did not confirm a completed response."""


class OpenAIResponsesAdapter:
    def __init__(self, client: Any):
        self.client = client

    def generate_json(
        self, *, model: str, messages: list[dict],
        schema_name: str, schema: dict,
    ) -> dict:
        """Provider-neutral structured JSON capability for Core classifiers."""
        if not model.strip():
            raise ValueError("AI model must be configured")
        if not messages:
            raise ValueError("At least one message is required")
        reply = self.client.responses.create(
            model=model,
            input=messages,
            text={"format": {
                "type": "json_schema",
                "name": schema_name,
                "strict": True,
                "schema": schema,
            }},
            stream=False,
        )
        raw = getattr(reply, "output_text", None)
        if not isinstance(raw, str) or len(raw) > 18000:
            raise ProviderResponseError("Provider returned invalid structured output")
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise ProviderResponseError("Provider returned non-object structured output")
        return value

    def stream_text(self, *, model: str, messages: list[dict]) -> Iterator[str]:
        if not model.strip():
            raise ValueError("AI model must be configured")
        if not messages:
            raise ValueError("At least one message is required")
        events = self.client.responses.create(model=model, input=messages, stream=True)
        completed = False
        try:
            for event in events:
                kind = getattr(event, "type", None)
                if kind == "response.output_text.delta":
                    delta = getattr(event, "delta", "")
                    if delta:
                        yield delta
                elif kind == "response.completed":
                    completed = True
                elif kind in {"response.failed", "response.incomplete", "error"}:
                    raise ProviderResponseError(f"Provider did not complete: {kind}")
            if not completed:
                raise ProviderResponseError("Provider stream ended without completion event")
        finally:
            close = getattr(events, "close", None)
            if callable(close):
                close()
