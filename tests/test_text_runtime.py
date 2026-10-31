from __future__ import annotations

from types import SimpleNamespace

import pytest

from jarvis.adapters.openai_responses import OpenAIResponsesAdapter, ProviderResponseError
from jarvis.conversation.runtime import ConversationRuntime
from jarvis.conversation.store import SQLiteConversationStore


class FakeResponses:
    def __init__(self, kinds):
        self.kinds = kinds
        self.calls = []

    def create(self, *, model, input, stream):
        self.calls.append((model, input, stream))
        return (SimpleNamespace(type=kind, delta=delta) for kind, delta in self.kinds)


def test_realistic_stream_persists_completed_reply(tmp_path):
    store = SQLiteConversationStore(tmp_path / "state.sqlite3")
    conv = store.create_conversation()
    fake = FakeResponses([
        ("response.output_text.delta", "Bom "),
        ("response.output_text.delta", "dia"),
        ("response.completed", ""),
    ])
    runtime = ConversationRuntime(store, OpenAIResponsesAdapter(SimpleNamespace(responses=fake)))
    assert list(runtime.reply(conversation_id=conv, text="Olá", model="configured-model")) == ["Bom ", "dia"]
    assert fake.calls == [("configured-model", [{"role": "user", "content": "Olá"}], True)]
    assert [(m["role"], m["content"], m["status"]) for m in store.list_messages(conv)] == [
        ("user", "Olá", "completed"),
        ("assistant", "Bom dia", "completed"),
    ]


def test_failure_is_not_persisted_as_completed(tmp_path):
    store = SQLiteConversationStore(tmp_path / "state.sqlite3")
    conv = store.create_conversation()
    fake = FakeResponses([("response.output_text.delta", "parcial")])
    runtime = ConversationRuntime(store, OpenAIResponsesAdapter(SimpleNamespace(responses=fake)))
    with pytest.raises(ProviderResponseError):
        list(runtime.reply(conversation_id=conv, text="Olá", model="model"))
    assert [m["status"] for m in store.list_messages(conv)] == ["completed", "failed"]
    assert [m["content"] for m in store.completed_context(conv)] == ["Olá"]


def test_provider_failure_event_is_not_success(tmp_path):
    store = SQLiteConversationStore(tmp_path / "state.sqlite3")
    conv = store.create_conversation()
    fake = FakeResponses([("response.failed", "")])
    runtime = ConversationRuntime(store, OpenAIResponsesAdapter(SimpleNamespace(responses=fake)))
    with pytest.raises(ProviderResponseError):
        list(runtime.reply(conversation_id=conv, text="Olá", model="model"))
    assert store.list_messages(conv)[-1]["status"] == "failed"


def test_model_must_be_configured():
    fake = FakeResponses([])
    adapter = OpenAIResponsesAdapter(SimpleNamespace(responses=fake))
    with pytest.raises(ValueError):
        list(adapter.stream_text(model=" ", messages=[{"role": "user", "content": "Hi"}]))
    assert fake.calls == []
