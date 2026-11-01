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
                    if action == "memory_create" else None,
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
        def __init__(self, url, key):
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
                                "status": "active", "name": "JARVIS"}], "total": 1}
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
    worker.run()
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
    worker.run()
    result = db.list_messages(cid)[-1]
    assert result["status"] == "completed"
    assert "não" in result["content"].lower() or "Nenhuma" in result["content"]
    assert memory_calls == knowledge_calls == []
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
