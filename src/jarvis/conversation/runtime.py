"""Text conversation orchestration: persistence precedes and follows streaming."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Protocol

from jarvis.conversation.store import SQLiteConversationStore


class TextStreamProvider(Protocol):
    def stream_text(self, *, model: str, messages: list[dict]) -> Iterator[str]: ...


class ConversationRuntime:
    def __init__(self, store: SQLiteConversationStore, provider: TextStreamProvider):
        self.store = store
        self.provider = provider
        self.last_assistant_message_id: str | None = None
        self.last_user_message_id: str | None = None

    def reply(self, *, conversation_id: str, text: str, model: str) -> Iterator[str]:
        self.last_user_message_id = self.store.append_user_message(conversation_id, text)
        context = self.store.completed_context(conversation_id)
        message_id = self.store.begin_assistant_message(conversation_id)
        self.last_assistant_message_id = message_id
        try:
            for delta in self.provider.stream_text(model=model, messages=context):
                self.store.append_assistant_delta(message_id, delta)
                yield delta
            self.store.end_assistant_message(message_id, successful=True)
        except GeneratorExit:
            # Closing a streaming iterator is a cancelled/incomplete response.
            self.store.end_assistant_message(
                message_id, successful=False, interrupted=True,
            )
            raise
        except BaseException:
            self.store.end_assistant_message(message_id, successful=False)
            raise
