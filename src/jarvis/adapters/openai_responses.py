"""OpenAI Responses streaming adapter for TB-01.

Provider-specific events do not leak into the conversation persistence API.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any


class ProviderResponseError(RuntimeError):
    """The provider failed or did not confirm a completed response."""


class OpenAIResponsesAdapter:
    def __init__(self, client: Any):
        self.client = client

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
