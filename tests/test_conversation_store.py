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


def test_delete_one_conversation_cascades_only_local_messages_and_evidence(tmp_path):
    import sqlite3
    from uuid import uuid4

    from jarvis.memory.journal import MemoryOperationJournal

    store = SQLiteConversationStore(tmp_path / "state.sqlite3")
    journal = MemoryOperationJournal(store.path)
    first = store.create_conversation()
    second = store.create_conversation()
    store.append_user_message(first, "Apagar este texto")
    assistant = store.begin_assistant_message(first)
    store.append_assistant_delta(assistant, "Consulta documental")
    store.end_assistant_message(assistant, successful=True)
    store.save_knowledge_evidence(
        assistant, dataset="jarvis-knowledge", knowledge_status="NO_RESULTS",
        query_id=str(uuid4()), references=[],
    )
    store.append_user_message(second, "Preservar esta conversa")

    operation_id, memory_id = str(uuid4()), str(uuid4())
    journal.prepare(operation_id, "https://memory.example", {
        "idempotency_key": operation_id, "memory_type": "profile",
        "scope": "global", "content": "Teal",
        "provenance": {"origin_kind": "user_asserted", "source_system": "jarvis",
                       "source_ref": "memory-operation:" + operation_id},
    })
    journal.claim(operation_id)
    journal.resolve(operation_id, status="confirmed", memory_id=memory_id)

    assert store.delete_conversation(first) is True
    assert store.delete_conversation(first) is False
    assert store.delete_conversation("not-a-uuid") is False
    with sqlite3.connect(store.path) as db:
        assert db.execute(
            "SELECT COUNT(*) FROM message_knowledge_evidence "
            "WHERE assistant_message_id=?", (assistant,)
        ).fetchone()[0] == 0
    reopened = SQLiteConversationStore(store.path)
    assert reopened.get_conversation(first) is None
    assert reopened.list_messages(second)[0]["content"] == "Preservar esta conversa"
    assert journal.get(operation_id)["status"] == "confirmed"
    assert journal.owned_user_memory(memory_id, "https://memory.example") is not None
