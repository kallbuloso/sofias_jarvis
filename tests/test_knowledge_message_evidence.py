"""B-02: Knowledge provenance stays attached to the exact assistant message.

All tests use local SQLite and generated UUIDs; no external service calls.
"""
from __future__ import annotations

import sqlite3
from uuid import uuid4
from contextlib import closing

import pytest

from jarvis.conversation.store import SQLiteConversationStore
from jarvis.conversation.runtime import ConversationRuntime

DATASET = "jarvis-knowledge"


def reference():
    return {
        "source_name": "JARVIS ADR-0001",
        "source_id": str(uuid4()),
        "document_id": str(uuid4()),
        "chunk_id": str(uuid4()),
        "quote": "This text MUST NOT be saved in the evidence table.",
        "url": "https://untrusted.example/not-authoritative",
        "text": "Do not copy a Knowledge chunk into transcript metadata.",
    }


def test_evidence_survives_restart_and_conversation_switch(tmp_path):
    path = tmp_path / "jarvis.sqlite3"
    db = SQLiteConversationStore(path)
    first = db.create_conversation()
    second = db.create_conversation()
    db.append_user_message(first, "Pergunta documental")
    assistant = db.begin_assistant_message(first)
    db.append_assistant_delta(assistant, "Conforme ADR-0001")
    db.end_assistant_message(assistant, successful=True)
    other = db.begin_assistant_message(second)
    db.end_assistant_message(other, successful=True)
    item = reference()
    query_id = str(uuid4())
    db.save_knowledge_evidence(assistant, dataset=DATASET,
                               knowledge_status="RESULTS_FOUND",
                               query_id=query_id, references=[item])
    reopened = SQLiteConversationStore(path)
    messages = reopened.list_messages(first)
    assert "knowledgeEvidence" not in messages[0]
    evidence = messages[1]["knowledgeEvidence"]
    assert evidence["queryId"] == query_id
    assert evidence["dataset"] == DATASET
    assert evidence["knowledgeStatus"] == "RESULTS_FOUND"
    assert evidence["retrievedAt"]
    assert evidence["references"] == [{
        "source_name": item["source_name"],
        "source_id": item["source_id"],
        "document_id": item["document_id"],
        "chunk_id": item["chunk_id"],
    }]
    assert "knowledgeEvidence" not in reopened.list_messages(second)[0]
    assert reopened.completed_context(first) == [
        {"role": "user", "content": "Pergunta documental"},
        {"role": "assistant", "content": "Conforme ADR-0001"},
    ]
    with sqlite3.connect(path) as raw:
        stored = raw.execute(
            "SELECT references_json FROM message_knowledge_evidence "
            "WHERE assistant_message_id=?", (assistant,),
        ).fetchone()[0]
    assert item["quote"] not in stored
    assert "https://" not in stored
    assert item["text"] not in stored


@pytest.mark.parametrize("invalid", [
    {"dataset": "other"},
    {"knowledge_status": "UNSAFE"},
    {"query_id": "invalid"},
    {"references": [dict(reference(), chunk_id="not-uuid")]},
    {"references": [reference()] * 4},
    {"knowledge_status": "NO_RESULTS", "references": [reference()]},
])
def test_reject_unverified_or_unbounded_evidence_without_side_effects(tmp_path, invalid):
    db = SQLiteConversationStore(tmp_path / "jarvis.sqlite3")
    cid = db.create_conversation()
    message = db.begin_assistant_message(cid)
    kwargs = {
        "dataset": DATASET, "knowledge_status": "RESULTS_FOUND",
        "query_id": str(uuid4()), "references": [reference()],
    }
    kwargs.update(invalid)
    with pytest.raises((ValueError, TypeError)):
        db.save_knowledge_evidence(message, **kwargs)
    assert "knowledgeEvidence" not in db.list_messages(cid)[0]


def test_user_message_and_unknown_target_cannot_receive_evidence(tmp_path):
    db = SQLiteConversationStore(tmp_path / "jarvis.sqlite3")
    cid = db.create_conversation()
    user = db.append_user_message(cid, "Oi")
    for mid in (user, str(uuid4())):
        with pytest.raises(ValueError):
            db.save_knowledge_evidence(mid, dataset=DATASET,
                knowledge_status="NO_RESULTS", query_id=None, references=[])


def test_failed_and_interrupted_messages_preserve_evidence_without_completion(tmp_path):
    db = SQLiteConversationStore(tmp_path / "jarvis.sqlite3")
    cid = db.create_conversation()
    failed = db.begin_assistant_message(cid)
    db.append_assistant_delta(failed, "Parcial")
    db.end_assistant_message(failed, successful=False)
    interrupted = db.begin_assistant_message(cid)
    db.append_assistant_delta(interrupted, "Mais parcial")
    db.end_assistant_message(interrupted, successful=False, interrupted=True)
    for mid in (failed, interrupted):
        db.save_knowledge_evidence(mid, dataset=DATASET,
            knowledge_status="NO_RESULTS", query_id=str(uuid4()), references=[])
    messages = SQLiteConversationStore(db.path).list_messages(cid)
    assert [x["status"] for x in messages] == ["failed", "interrupted"]
    assert all(x["knowledgeEvidence"]["knowledgeStatus"] == "NO_RESULTS"
               for x in messages)
    assert db.completed_context(cid) == []


def test_duplicate_evidence_cannot_rewrite_original_attribution(tmp_path):
    db = SQLiteConversationStore(tmp_path / "jarvis.sqlite3")
    cid = db.create_conversation()
    mid = db.begin_assistant_message(cid)
    db.save_knowledge_evidence(mid, dataset=DATASET,
        knowledge_status="RESULTS_FOUND", query_id=str(uuid4()),
        references=[reference()])
    before = db.list_messages(cid)[0]["knowledgeEvidence"]
    with pytest.raises(sqlite3.IntegrityError):
        db.save_knowledge_evidence(mid, dataset=DATASET,
            knowledge_status="NO_RESULTS", query_id=None, references=[])
    assert db.list_messages(cid)[0]["knowledgeEvidence"] == before


def test_existing_v4_database_migrates_without_changing_history(tmp_path):
    path = tmp_path / "jarvis.sqlite3"
    db = SQLiteConversationStore(path)
    cid = db.create_conversation()
    mid = db.begin_assistant_message(cid)
    db.append_assistant_delta(mid, "Texto antes da migração")
    db.end_assistant_message(mid, successful=True)
    with sqlite3.connect(path) as raw:
        raw.execute("DROP TABLE message_knowledge_evidence")
        raw.execute("PRAGMA user_version = 4")
    reopened = SQLiteConversationStore(path)
    assert reopened.list_messages(cid)[0]["content"] == "Texto antes da migração"
    assert "knowledgeEvidence" not in reopened.list_messages(cid)[0]
    with sqlite3.connect(path) as raw:
        assert raw.execute("PRAGMA user_version").fetchone()[0] == 5
    reopened.save_knowledge_evidence(mid, dataset=DATASET,
        knowledge_status="NO_RESULTS", query_id=None, references=[])


def test_runtime_close_is_interrupted_and_tracks_exact_message_id(tmp_path):
    class Provider:
        def stream_text(self, *, model, messages):
            yield "parcial"
            yield "não entregue"
    store = SQLiteConversationStore(tmp_path / "jarvis.sqlite3")
    cid = store.create_conversation()
    runtime = ConversationRuntime(store, Provider())
    with closing(runtime.reply(conversation_id=cid, text="Oi", model="test")) as stream:
        assert next(stream) == "parcial"
    msg = store.list_messages(cid)[1]
    assert msg["id"] == runtime.last_assistant_message_id
    assert msg["status"] == "interrupted"
    assert msg["content"] == "parcial"
