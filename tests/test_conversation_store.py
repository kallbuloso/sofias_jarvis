from __future__ import annotations

import pytest

from jarvis.conversation.store import SQLiteConversationStore


def test_conversations_survive_restart_and_are_isolated(tmp_path):
    path = tmp_path / "state.sqlite3"
    store = SQLiteConversationStore(path)
    a = store.create_conversation("Primeira")
    b = store.create_conversation("Segunda")
    store.append_user_message(a, "Olá")
    store.append_user_message(b, "Outra mensagem")

    reopened = SQLiteConversationStore(path)
    assert {item["id"] for item in reopened.list_conversations()} == {a, b}
    assert [m["content"] for m in reopened.list_messages(a)] == ["Olá"]
    assert [m["content"] for m in reopened.list_messages(b)] == ["Outra mensagem"]
    assert reopened.completed_context(a) == [{"role": "user", "content": "Olá"}]


def test_streaming_reply_is_never_silently_completed(tmp_path):
    store = SQLiteConversationStore(tmp_path / "db.sqlite3")
    conversation = store.create_conversation()
    message = store.begin_assistant_message(conversation)
    store.append_assistant_delta(message, "res")
    store.append_assistant_delta(message, "posta")
    assert store.completed_context(conversation) == []
    assert store.interrupt_inflight_messages() == 1
    assert store.list_messages(conversation)[0]["status"] == "interrupted"
    assert store.list_messages(conversation)[0]["content"] == "resposta"
    with pytest.raises(ValueError):
        store.append_assistant_delta(message, "duplicado")


def test_completed_and_failed_assistant_replies(tmp_path):
    store = SQLiteConversationStore(tmp_path / "db.sqlite3")
    conversation = store.create_conversation()
    complete = store.begin_assistant_message(conversation)
    store.append_assistant_delta(complete, "completa")
    store.end_assistant_message(complete, successful=True)
    failed = store.begin_assistant_message(conversation)
    store.append_assistant_delta(failed, "parcial")
    store.end_assistant_message(failed, successful=False)
    assert store.completed_context(conversation) == [
        {"role": "assistant", "content": "completa"}
    ]
    assert [m["status"] for m in store.list_messages(conversation)] == ["completed", "failed"]
    with pytest.raises(ValueError):
        store.end_assistant_message(complete, successful=True)


def test_invalid_operations_fail_without_side_effects(tmp_path):
    store = SQLiteConversationStore(tmp_path / "db.sqlite3")
    with pytest.raises(KeyError):
        store.append_user_message("unknown", "oi")
    with pytest.raises(KeyError):
        store.list_messages("unknown")
    with pytest.raises(ValueError):
        store.append_user_message(store.create_conversation(), "  ")
    assert store.list_conversations()[0]["title"] == "Nova conversa"


def test_context_order_limit(tmp_path):
    store = SQLiteConversationStore(tmp_path / "db.sqlite3")
    conversation = store.create_conversation()
    for i in range(4):
        store.append_user_message(conversation, str(i))
    assert [m["content"] for m in store.completed_context(conversation, limit=2)] == ["2", "3"]
    with pytest.raises(ValueError):
        store.completed_context(conversation, limit=0)
