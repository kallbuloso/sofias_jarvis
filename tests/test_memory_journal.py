"""Cognitive mutation journal: persistence, old schema and fail-closed resume."""
from __future__ import annotations

import sqlite3
from uuid import uuid4

import pytest

from jarvis.conversation.store import SQLiteConversationStore
from jarvis.memory.journal import MemoryOperationJournal


def new_intent(scope="global"):
    op_id = str(uuid4())
    payload = {
        "content": "Prefiro a cor teal.",
        "scope": scope, "memory_type": "profile",
        "provenance": {"origin_kind": "user_asserted", "source_system": "jarvis",
                       "source_ref": f"memory-operation:{op_id}"},
        "idempotency_key": op_id,
    }
    return op_id, payload


def test_journal_records_intent_before_network_and_scrubs_on_confirmation(tmp_path):
    path = tmp_path / "jarvis.sqlite3"
    SQLiteConversationStore(path)
    journal = MemoryOperationJournal(path)
    op_id, payload = new_intent()
    journal.prepare(op_id, "https://memory.example", payload)
    before = journal.get(op_id)
    assert before["status"] == "prepared"
    assert "content" not in before
    claim = journal.claim(op_id)
    assert claim["payload"] == payload
    assert journal.get(op_id)["status"] == "in_flight"
    memory_id = str(uuid4())
    journal.resolve(op_id, status="confirmed", memory_id=memory_id)
    assert journal.get(op_id)["memory_id"] == memory_id
    assert journal.get(op_id)["status"] == "confirmed"
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT payload_json FROM cognitive_write_operations WHERE id=?", (op_id,)).fetchone()[0] is None


def test_unknown_is_retained_and_cannot_be_replayed_automatically(tmp_path):
    path = tmp_path / "jarvis.sqlite3"
    journal = MemoryOperationJournal(path)
    op_id, payload = new_intent()
    journal.prepare(op_id, "https://memory.example", payload)
    journal.claim(op_id)
    journal.resolve(op_id, status="unknown", error_code="RESULT_UNKNOWN")
    reopened = MemoryOperationJournal(path)
    assert reopened.get(op_id)["status"] == "unknown"
    with pytest.raises(ValueError, match="operation_not_prepared"):
        reopened.claim(op_id)
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT payload_json FROM cognitive_write_operations WHERE id=?", (op_id,)).fetchone()[0] is not None


def test_crash_in_flight_is_not_silently_assumed_failed(tmp_path):
    path = tmp_path / "jarvis.sqlite3"
    journal = MemoryOperationJournal(path)
    op_id, payload = new_intent()
    journal.prepare(op_id, "https://memory.example", payload)
    journal.claim(op_id)
    reopened = MemoryOperationJournal(path)
    assert reopened.get(op_id)["status"] == "in_flight"
    with pytest.raises(ValueError):
        reopened.claim(op_id)


def test_rejected_drops_content_and_duplicate_id_is_blocked(tmp_path):
    path = tmp_path / "jarvis.sqlite3"
    journal = MemoryOperationJournal(path)
    op_id, payload = new_intent()
    journal.prepare(op_id, "https://memory.example", payload)
    with pytest.raises(sqlite3.IntegrityError):
        journal.prepare(op_id, "https://memory.example", payload)
    journal.claim(op_id)
    journal.resolve(op_id, status="rejected", error_code="INVALID_REQUEST")
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT payload_json FROM cognitive_write_operations WHERE id=?", (op_id,)).fetchone()[0] is None


def test_existing_v1_database_is_migrated_without_losing_messages(tmp_path):
    path = tmp_path / "jarvis.sqlite3"
    old = SQLiteConversationStore(path)
    conv = old.create_conversation()
    old.append_user_message(conv, "Histórico antigo")
    with sqlite3.connect(path) as db:
        db.execute("DROP TABLE cognitive_write_operations")
        db.execute("PRAGMA user_version = 1")
    new = SQLiteConversationStore(path)
    assert new.list_messages(conv)[0]["content"] == "Histórico antigo"
    with sqlite3.connect(path) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 3
        assert db.execute("SELECT name FROM sqlite_master WHERE name='cognitive_write_operations'").fetchone()


def test_journal_rejects_key_mismatch_and_bad_transition(tmp_path):
    path = tmp_path / "jarvis.sqlite3"
    journal = MemoryOperationJournal(path)
    op_id, payload = new_intent()
    payload["idempotency_key"] = str(uuid4())
    with pytest.raises(ValueError, match="idempotency_key_mismatch"):
        journal.prepare(op_id, "https://memory.example", payload)
    payload["idempotency_key"] = op_id
    journal.prepare(op_id, "https://memory.example", payload)
    with pytest.raises(ValueError, match="operation_not_in_flight"):
        journal.resolve(op_id, status="confirmed", memory_id=str(uuid4()))



def test_v2_to_v3_migration_preserves_pending_create_journal(tmp_path):
    path = tmp_path / "jarvis.sqlite3"
    SQLiteConversationStore(path)
    op_id, payload = new_intent()
    journal = MemoryOperationJournal(path)
    journal.prepare(op_id, "https://memory.example", payload)
    with sqlite3.connect(path) as db:
        db.execute("DROP INDEX idx_tb02_mutation_pending")
        db.execute("DROP TABLE tb02_test_memories")
        db.execute("ALTER TABLE cognitive_write_operations DROP COLUMN operation_kind")
        db.execute("ALTER TABLE cognitive_write_operations DROP COLUMN target_memory_id")
        db.execute("PRAGMA user_version = 2")
    reopened = MemoryOperationJournal(path)
    assert reopened.get(op_id)["status"] == "prepared"
    assert reopened.claim(op_id)["payload"] == payload
    with sqlite3.connect(path) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 3
