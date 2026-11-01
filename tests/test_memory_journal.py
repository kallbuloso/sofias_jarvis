"""Cognitive mutation journal: persistence, old schema and fail-closed resume."""
from __future__ import annotations

import sqlite3
from uuid import uuid4

import pytest

from jarvis.conversation.store import SQLiteConversationStore
from jarvis.memory.journal import MemoryOperationJournal
from jarvis.memory.personal_confirmation import PersonalMutationAuthorization


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
        assert db.execute("PRAGMA user_version").fetchone()[0] == 4
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
        # Reconstruct a REAL v2 schema, not just a v2 user_version.
        # Otherwise SQLite v4 consent columns survive the downgrade fixture,
        # and the legitimate v3->v4 migration refuses to add duplicates.
        db.execute("DROP INDEX idx_cognitive_confirmation_ref")
        for name in (
            "confirmation_ref",
            "confirmation_method",
            "confirmation_conversation_id",
            "confirmed_by_user_at",
        ):
            db.execute(f"ALTER TABLE cognitive_write_operations DROP COLUMN {name}")
        db.execute("DROP INDEX idx_tb02_mutation_pending")
        db.execute("DROP TABLE tb02_test_memories")
        db.execute("ALTER TABLE cognitive_write_operations DROP COLUMN operation_kind")
        db.execute("ALTER TABLE cognitive_write_operations DROP COLUMN target_memory_id")
        db.execute("PRAGMA user_version = 2")
    reopened = MemoryOperationJournal(path)
    assert reopened.get(op_id)["status"] == "prepared"
    assert reopened.claim(op_id)["payload"] == payload
    with sqlite3.connect(path) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 4


def test_legacy_journal_does_not_invent_authorization(tmp_path):
    journal = MemoryOperationJournal(tmp_path / "jarvis.sqlite3")
    operation_id, payload = new_intent()
    journal.prepare(operation_id, "https://memory.example", payload)
    journal.claim(operation_id)
    journal.resolve(operation_id, status="confirmed", memory_id=str(uuid4()))
    record = journal.get(operation_id)
    assert record["confirmation_ref"] is None
    assert record["confirmed_by_user_at"] is None
    assert record["confirmation_method"] is None


def test_audit_receipt_is_atomic_with_prepared_intent(tmp_path):
    path = tmp_path / "jarvis.sqlite3"
    journal = MemoryOperationJournal(path)
    owner_id, owner_payload = new_intent()
    journal.prepare(owner_id, "https://memory.example", owner_payload)
    journal.claim(owner_id)
    target = str(uuid4())
    journal.resolve(owner_id, status="confirmed", memory_id=target)

    mutation_id = str(uuid4())
    receipt = PersonalMutationAuthorization.from_typed_confirmation(
        action="forget", target_memory_id=target,
        phrase="ESQUECER " + target, method="cli_typed",
    )
    with pytest.raises(ValueError, match="requires_typed_confirmation"):
        journal.prepare(mutation_id, "https://memory.example",
                        {"idempotency_key": mutation_id, "memory_id": target},
                        kind="user_forget", target_memory_id=target)

    assert journal.get(mutation_id) is None
    journal.prepare(mutation_id, "https://memory.example",
                    {"idempotency_key": mutation_id, "memory_id": target},
                    kind="user_forget", target_memory_id=target,
                    confirmation=receipt)
    entry = journal.get(mutation_id)
    assert entry["status"] == "prepared"
    assert entry["confirmation_ref"] == "user-confirmation:" + receipt.authorization_id
    assert entry["confirmation_method"] == "cli_typed"
    assert entry["confirmed_by_user_at"]
    journal.claim(mutation_id)
    journal.resolve(mutation_id, status="confirmed", memory_id=target)
    restarted = MemoryOperationJournal(path).get(mutation_id)
    assert restarted["confirmation_ref"] == entry["confirmation_ref"]
    with sqlite3.connect(path) as db:
        row = db.execute(
            "SELECT payload_json FROM cognitive_write_operations WHERE id=?",
            (mutation_id,),
        ).fetchone()
    assert row[0] is None


def test_authorization_receipt_cannot_be_reused(tmp_path):
    journal = MemoryOperationJournal(tmp_path / "jarvis.sqlite3")
    owner_id, payload = new_intent()
    journal.prepare(owner_id, "https://memory.example", payload)
    journal.claim(owner_id)
    target = str(uuid4())
    journal.resolve(owner_id, status="confirmed", memory_id=target)
    consent = PersonalMutationAuthorization.from_typed_confirmation(
        action="forget", target_memory_id=target,
        phrase="ESQUECER " + target, method="cli_typed",
    )

    def make_intent(op):
        journal.prepare(op, "https://memory.example",
                        {"idempotency_key": op, "memory_id": target},
                        kind="user_forget", target_memory_id=target,
                        confirmation=consent)

    first = str(uuid4())
    make_intent(first)
    journal.claim(first)
    journal.resolve(first, status="rejected", error_code="TEST_REJECTED")
    with pytest.raises(sqlite3.IntegrityError):
        make_intent(str(uuid4()))


def test_existing_v3_database_migrates_to_v4_without_faking_human_consent(tmp_path):
    path = tmp_path / "jarvis.sqlite3"
    journal = MemoryOperationJournal(path)
    op_id, payload = new_intent()
    journal.prepare(op_id, "https://memory.example", payload)
    journal.claim(op_id)
    memory_id = str(uuid4())
    journal.resolve(op_id, status="confirmed", memory_id=memory_id)
    with sqlite3.connect(path) as db:
        db.execute("DROP INDEX idx_cognitive_confirmation_ref")
        for name in (
            "confirmation_ref",
            "confirmation_method",
            "confirmation_conversation_id",
            "confirmed_by_user_at",
        ):
            db.execute(f"ALTER TABLE cognitive_write_operations DROP COLUMN {name}")
        db.execute("PRAGMA user_version = 3")
    # A fully valid v3 database must migrate once to v4.
    reopened = MemoryOperationJournal(path)
    operation = reopened.get(op_id)
    assert operation["status"] == "confirmed"
    assert operation["memory_id"] == memory_id
    assert operation["confirmation_ref"] is None
    assert operation["confirmation_method"] is None
    assert operation["confirmation_conversation_id"] is None
    assert operation["confirmed_by_user_at"] is None
    with sqlite3.connect(path) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 4
        columns = {row[1] for row in db.execute(
            "PRAGMA table_info(cognitive_write_operations)"
        )}
    assert {
        "confirmation_ref", "confirmation_method",
        "confirmation_conversation_id", "confirmed_by_user_at",
    } <= columns
