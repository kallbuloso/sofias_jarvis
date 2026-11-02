"""Offline smoke of natural text desktop routing (no real OpenAI/Memory)."""
from __future__ import annotations

import json
import sys
from types import SimpleNamespace
from uuid import uuid4

import pytest

pytest.importorskip("PySide6")
from jarvis.conversation.store import SQLiteConversationStore
from jarvis.desktop.bridge import JarvisBridge, ReplyWorker
from jarvis.memory import cognitive, connection, knowledge
from jarvis.secrets.windows import WindowsCredentialStore

_DATASET_ID = str(uuid4())
_SOURCE_ID = str(uuid4())
_DOCUMENT_ID = str(uuid4())
_CHUNK_ID = str(uuid4())
_QUERY_ID = str(uuid4())


def environment(monkeypatch, tmp_path, action, *, route_failure=False):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(connection, "configured_memory_url",
                        lambda: "https://memory.example")
    monkeypatch.setattr(WindowsCredentialStore, "get_memory_key",
                        lambda self: "PRIVATE-TEST-MEMORY")
    monkeypatch.setattr(WindowsCredentialStore, "get_openai_key",
                        lambda self: "PRIVATE-TEST-OPENAI")
    api_calls = []
    memory_calls = []
    knowledge_calls = []
    class Responses:
        def create(self, **kwargs):
            api_calls.append(kwargs)
            if not kwargs["stream"]:
                if route_failure:
                    raise RuntimeError("simulated_router_outage")
                return SimpleNamespace(output_text=json.dumps({
                    "action": action, "scope": "global" if action == "memory_recall"
                    else None,
                    "content": "Prefiro teal."
                    if action in {"memory_create", "memory_update"} else None,
                }))
            return iter([
                SimpleNamespace(type="response.output_text.delta",
                                delta="Resposta de teste."),
                SimpleNamespace(type="response.completed", delta=""),
            ])
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(
        OpenAI=lambda **kw: SimpleNamespace(responses=Responses()),
    ))
    class MemoryReader:
        base_url = "https://memory.example"

        def __init__(self, url, key):
            assert url == self.base_url
            assert key == "PRIVATE-TEST-MEMORY"
        def recall(self, **kwargs):
            memory_calls.append(kwargs)
            return []
        def create(self, **kwargs):
            raise AssertionError("No memory mutation permitted by text router")
        def forget(self, **kwargs):
            raise AssertionError("No memory mutation permitted by text router")
        def supersede(self, **kwargs):
            raise AssertionError("No memory mutation permitted by text router")
    monkeypatch.setattr(cognitive, "CognitiveMemoryClient", MemoryReader)

    class KnowledgeReader:
        def __init__(self, url, key):
            assert key == "PRIVATE-TEST-MEMORY"
        def list_datasets(self, **kwargs):
            knowledge_calls.append("list")
            return {"items": [{"dataset_id": _DATASET_ID, "slug": "jarvis-knowledge",
                                "status": "active", "name": "JARVIS Knowledge"}], "total": 1}
        def query_chunks(self, **kwargs):
            knowledge_calls.append("query")
            return {"status": "RESULTS_FOUND", "query_id": _QUERY_ID,
                    "datasets": ["jarvis-knowledge"], "mode": "chunks",
                    "context": [{
                        "dataset_id": _DATASET_ID, "source_id": _SOURCE_ID,
                        "document_id": _DOCUMENT_ID, "chunk_id": _CHUNK_ID,
                        "source_name": "ADR-0001", "text": "Modular Monolith",
                    }],
                    "references": [{
                        "source_id": _SOURCE_ID, "document_id": _DOCUMENT_ID,
                        "chunk_id": _CHUNK_ID, "source_name": "ADR-0001",
                        "quote": "Modular Monolith", "url": None,
                    }]}
    monkeypatch.setattr(knowledge, "KnowledgeClient", KnowledgeReader)
    return api_calls, memory_calls, knowledge_calls


def test_natural_text_knowledge_query_retrieves_sources_without_switch(tmp_path, monkeypatch):
    calls, memory_calls, knowledge_calls = environment(
        monkeypatch, tmp_path, "knowledge_query",
    )
    db = SQLiteConversationStore(tmp_path / "jarvis.sqlite3")
    cid = db.create_conversation()
    worker = ReplyWorker(cid, "Qual arquitetura do ADR-0001?", "model", "PRIVATE",
                         conversational=True)
    done_events, knowledge_events = [], []
    worker.done.connect(lambda *args: done_events.append(args))
    worker.knowledgeDone.connect(lambda *args: knowledge_events.append(args))
    worker.run()
    assert done_events == [(cid, "completed", "", "NOT_REQUESTED")]
    assert len(knowledge_events) == 1
    evidence = json.loads(knowledge_events[0][1])
    assert evidence["knowledgeStatus"] == "RESULTS_FOUND"
    assert evidence["evidencePersistence"] == "SAVED"
    messages = db.list_messages(cid)
    assert messages[-1]["status"] == "completed"
    assert messages[-1]["knowledgeEvidence"]["knowledgeStatus"] == "RESULTS_FOUND"
    assert messages[-1]["knowledgeEvidence"]["references"][0]["chunk_id"] == _CHUNK_ID
    assert knowledge_calls == ["list", "query"]
    assert memory_calls == []
    assert [x["stream"] for x in calls] == [False, True]


def test_natural_text_recall_auto_routes_to_memory_without_knowledge(tmp_path, monkeypatch):
    calls, memory_calls, knowledge_calls = environment(
        monkeypatch, tmp_path, "memory_recall",
    )
    db = SQLiteConversationStore(tmp_path / "jarvis.sqlite3")
    cid = db.create_conversation()
    worker = ReplyWorker(cid, "O que você sabe da minha cor preferida?", "model",
                         "PRIVATE", conversational=True)
    worker.run()
    assert worker.routing_status == "CLASSIFIED"
    assert len(memory_calls) == 1
    assert memory_calls[0]["scopes"] == ["global"]
    assert not knowledge_calls
    assert db.list_messages(cid)[-1]["status"] == "completed"


@pytest.mark.parametrize("action", [
    "memory_create", "memory_update", "memory_forget", "reminder_request",
])
def test_mutating_and_scheduler_intents_are_not_executed(tmp_path, monkeypatch, action):
    calls, memory_calls, knowledge_calls = environment(
        monkeypatch, tmp_path, action,
    )
    db = SQLiteConversationStore(tmp_path / "jarvis.sqlite3")
    cid = db.create_conversation()
    worker = ReplyWorker(cid, "JARVIS faça a operação", "model", "PRIVATE",
                         conversational=True)
    proposals = []
    worker.createProposed.connect(lambda *args: proposals.append(args))
    worker.run()
    assert proposals == []  # Model classification cannot authorize a generic request.
    result = db.list_messages(cid)[-1]
    assert result["status"] == "completed"
    assert worker.create_proposal is None
    assert worker.direct_create is None
    assert "não" in result["content"].lower() or "Nenhuma" in result["content"]
    assert knowledge_calls == []
    if action in {"memory_update", "memory_forget"}:
        assert len(memory_calls) == 1  # read-only target resolution is allowed
    else:
        assert memory_calls == []
    assert [x["stream"] for x in calls] == [False]


def test_router_failure_does_not_fake_execution(tmp_path, monkeypatch):
    calls, memory_calls, knowledge_calls = environment(
        monkeypatch, tmp_path, "chat", route_failure=True,
    )
    db = SQLiteConversationStore(tmp_path / "jarvis.sqlite3")
    cid = db.create_conversation()
    worker = ReplyWorker(cid, "Lembre de algo amanhã", "model", "PRIVATE",
                         conversational=True)
    worker.run()
    assert worker.routing_status == "UNAVAILABLE"
    assert "Nenhuma memória" in db.list_messages(cid)[-1]["content"]
    assert [x["stream"] for x in calls] == [False]
    assert memory_calls == knowledge_calls == []


def test_bridge_single_entry_dispatches_model_without_manual_switch(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(WindowsCredentialStore, "get_openai_key",
                        lambda self: "PRIVATE-OPENAI")
    bridge = JarvisBridge()
    cid = json.loads(bridge.createConversation())["id"]
    captured = []
    def dispatch(*args, **kwargs):
        captured.append((args, kwargs))
        return json.dumps({"ok": True})
    monkeypatch.setattr(bridge, "_dispatch", dispatch)
    assert json.loads(bridge.sendConversationalMessage(cid, "Lembre o ADR", "model"))["ok"]
    assert captured == [((cid, "Lembre o ADR", "model"), {
        "memory_scope": None, "knowledge_dataset": None, "conversational": True,
    })]


def test_user_direct_create_executes_once_with_persisted_message_receipt(
        tmp_path, monkeypatch):
    from jarvis.memory.journal import MemoryOperationJournal
    environment(monkeypatch, tmp_path, "memory_create")
    calls = []

    class Writer:
        base_url = "https://memory.example"

        def __init__(self, url, key):
            assert url == self.base_url and key == "PRIVATE-TEST-MEMORY"

        def diagnose(self):
            return {"status": "COMPATIBLE"}

        def create(self, *, memory_type, scope, content, provenance, idempotency_key):
            calls.append((scope, content, dict(provenance), idempotency_key))
            return {
                "memory_id": str(uuid4()), "memory_type": memory_type,
                "scope": scope, "content": content,
                "lifecycle": "active", "provenance": dict(provenance),
            }

    monkeypatch.setattr(cognitive, "CognitiveMemoryClient", Writer)
    db = SQLiteConversationStore(tmp_path / "jarvis.sqlite3")
    cid = db.create_conversation()
    worker = ReplyWorker(
        cid, "JARVIS, lembre que no projeto JARVIS a palavra de teste é morango.",
        "model", "PRIVATE", conversational=True,
    )
    proposed = []
    worker.createProposed.connect(lambda *args: proposed.append(args))
    worker.run()
    messages = SQLiteConversationStore(db.path).list_messages(cid)
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"
    assert messages[1]["status"] == "completed"
    assert "Guardei essa informação" in messages[1]["content"]
    assert proposed == []  # explicit low-risk Create has no second-click dialog
    assert len(calls) == 1
    assert calls[0][0] == "project:jarvis"
    assert calls[0][1] == "no projeto JARVIS a palavra de teste é morango"
    journal = MemoryOperationJournal(db.path)
    with journal._store._connection() as sqlite:
        row = sqlite.execute(
            "SELECT id FROM cognitive_write_operations "
            "WHERE confirmation_ref=?",
            ("user-message:" + messages[0]["id"],),
        ).fetchone()
    assert row is not None
    audit = journal.get(row["id"])
    assert audit["status"] == "confirmed"
    assert audit["confirmation_method"] == "user_direct_intent"
    assert audit["confirmation_conversation_id"] == cid
    assert calls[0][2]["confirmation_ref"] == audit["confirmation_ref"]
    assert calls[0][2]["source_ref"] == "memory-operation:" + row["id"]


def test_direct_create_ambiguous_scope_does_not_touch_memory(tmp_path, monkeypatch):
    calls, memory_calls, knowledge_calls = environment(
        monkeypatch, tmp_path, "memory_create",
    )
    db = SQLiteConversationStore(tmp_path / "jarvis.sqlite3")
    cid = db.create_conversation()
    worker = ReplyWorker(
        cid, "JARVIS, lembre que a palavra de teste é morango.",
        "model", "PRIVATE", conversational=True,
    )
    worker.run()
    assert "preferência geral" in db.list_messages(cid)[-1]["content"]
    assert worker.direct_create is None
    assert memory_calls == knowledge_calls == []
    assert [x["stream"] for x in calls] == [False]


def test_direct_create_remote_result_unknown_does_not_claim_saved(tmp_path, monkeypatch):
    from jarvis.memory.cognitive import CognitiveMemoryError
    from jarvis.memory.journal import MemoryOperationJournal
    environment(monkeypatch, tmp_path, "memory_create")
    attempts = []

    class UnknownWriter:
        base_url = "https://memory.example"

        def __init__(self, url, key):
            pass

        def diagnose(self):
            return {"status": "COMPATIBLE"}

        def create(self, **kwargs):
            attempts.append(kwargs)
            raise CognitiveMemoryError("RESULT_UNKNOWN")

    monkeypatch.setattr(cognitive, "CognitiveMemoryClient", UnknownWriter)
    db = SQLiteConversationStore(tmp_path / "jarvis.sqlite3")
    cid = db.create_conversation()
    worker = ReplyWorker(
        cid, "JARVIS, lembre que no projeto JARVIS o teste usa morango.",
        "model", "PRIVATE", conversational=True,
    )
    worker.run()
    assert len(attempts) == 1
    assert "não confirmou" in db.list_messages(cid)[-1]["content"]
    assert "Não vou repetir" in db.list_messages(cid)[-1]["content"]
    with MemoryOperationJournal(db.path)._store._connection() as conn:
        status = conn.execute(
            "SELECT status FROM cognitive_write_operations"
        ).fetchone()[0]
    assert status == "unknown"


def test_direct_create_missing_connection_never_prepares_journal(tmp_path, monkeypatch):
    from jarvis.memory.journal import MemoryOperationJournal
    environment(monkeypatch, tmp_path, "memory_create")
    monkeypatch.setattr(connection, "configured_memory_url", lambda: None)
    db = SQLiteConversationStore(tmp_path / "jarvis.sqlite3")
    cid = db.create_conversation()
    worker = ReplyWorker(
        cid, "JARVIS, lembre que no projeto JARVIS o teste usa azul.",
        "model", "PRIVATE", conversational=True,
    )
    worker.run()
    assert "não está configurado" in db.list_messages(cid)[-1]["content"]
    with MemoryOperationJournal(db.path)._store._connection() as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM cognitive_write_operations"
        ).fetchone()[0] == 0


def test_direct_create_disagrees_with_model_scope_never_executes(tmp_path, monkeypatch):
    calls, memory_calls, knowledge_calls = environment(
        monkeypatch, tmp_path, "memory_create",
    )
    class WrongScopeResponses:
        def create(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(output_text=json.dumps({
                "action": "memory_create", "scope": "global",
                "content": "qualquer outro conteúdo sugerido pela IA",
            }))
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(
        OpenAI=lambda **kw: SimpleNamespace(responses=WrongScopeResponses()),
    ))
    db = SQLiteConversationStore(tmp_path / "jarvis.sqlite3")
    cid = db.create_conversation()
    worker = ReplyWorker(
        cid, "JARVIS, lembre que no projeto JARVIS usamos Vuetify 3.",
        "model", "PRIVATE", conversational=True,
    )
    worker.run()
    assert "Não consegui determinar um escopo consistente" in (
        db.list_messages(cid)[-1]["content"]
    )
    assert worker.direct_create is None
    assert not memory_calls and not knowledge_calls

def test_pending_forget_confirmation_is_consumed_before_llm_routing(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(WindowsCredentialStore, "get_openai_key",
                        lambda self: "PRIVATE-OPENAI")
    bridge = JarvisBridge()
    cid = json.loads(bridge.createConversation())["id"]
    memory_id = str(uuid4())
    proposal = {
        "action": "forget",
        "preview": {
            "memory_id": memory_id,
            "scope": "global",
            "memory_type": "profile",
            "lifecycle": "active",
            "content": "Prefiro teal",
            "source_ref": "memory-operation:test",
        },
    }
    bridge._on_conversational_mutation_proposed(cid, json.dumps(proposal))
    captured = []

    def dispatch(*args, **kwargs):
        captured.append((args, kwargs))
        return json.dumps({"ok": True})

    monkeypatch.setattr(bridge, "_dispatch", dispatch)
    result = json.loads(bridge.sendConversationalMessage(cid, "Confirmo", "model"))
    assert result["ok"] is True
    assert len(captured) == 1
    assert captured[0][1]["conversational"] is False
    pending = captured[0][1]["confirmed_forget"]
    assert pending.action == "forget"
    assert pending.preview["memory_id"] == memory_id
    assert bridge._pending_forget_token is None
    assert bridge._pending_forget_conversation is None

