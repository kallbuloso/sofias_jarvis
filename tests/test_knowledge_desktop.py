"""Desktop Knowledge: opt-in gate, worker evidence, and disabled boundary."""
from __future__ import annotations

import json
import sys
from types import SimpleNamespace
from uuid import uuid4

import pytest

pytest.importorskip("PySide6")

from jarvis.desktop.bridge import JarvisBridge, ReplyWorker
from jarvis.memory import connection, knowledge, cognitive
from jarvis.conversation.store import SQLiteConversationStore
from jarvis.secrets.windows import WindowsCredentialStore

DATASET_ID = str(uuid4())
SOURCE_ID = str(uuid4())
DOCUMENT_ID = str(uuid4())
CHUNK_ID = str(uuid4())
QUERY_ID = str(uuid4())


def setup_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(connection, "configured_memory_url", lambda: "https://memory.example")
    monkeypatch.setattr(WindowsCredentialStore, "get_memory_key", lambda self: "PRIVATE-MEMORY")
    monkeypatch.setattr(WindowsCredentialStore, "get_openai_key", lambda self: "PRIVATE-OPENAI")
    sent, calls = [], []

    class Responses:
        def create(self, *, model, input, stream):
            sent.append(input)
            yield SimpleNamespace(type="response.output_text.delta",
                                  delta="Conforme o ADR-0001.")
            yield SimpleNamespace(type="response.completed", delta="")

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(
        OpenAI=lambda **kw: SimpleNamespace(responses=Responses()),
    ))

    class Reader:
        def __init__(self, url, key):
            assert (url, key) == ("https://memory.example", "PRIVATE-MEMORY")

        def list_datasets(self, **kwargs):
            calls.append(("list", kwargs))
            return {"items": [{
                "dataset_id": DATASET_ID, "slug": "jarvis-knowledge",
                "name": "JARVIS Knowledge", "status": "active",
            }], "total": 1}

        def query_chunks(self, **kwargs):
            calls.append(("query", kwargs))
            return {
                "status": "RESULTS_FOUND", "query_id": QUERY_ID,
                "mode": "chunks", "datasets": ["jarvis-knowledge"],
                "context": [{
                    "dataset_id": DATASET_ID, "source_id": SOURCE_ID,
                    "document_id": DOCUMENT_ID, "chunk_id": CHUNK_ID,
                    "source_name": "JARVIS ADR-0001",
                    "text": "Arquitetura modular aprovada.", "score": 0.016,
                }],
                "references": [{
                    "source_id": SOURCE_ID, "document_id": DOCUMENT_ID,
                    "chunk_id": CHUNK_ID, "source_name": "JARVIS ADR-0001",
                    "quote": "Arquitetura modular aprovada.", "url": None,
                    "score": 0.016,
                }],
            }

    monkeypatch.setattr(knowledge, "KnowledgeClient", Reader)
    return sent, calls


def test_invalid_knowledge_dataset_never_starts_worker(tmp_path, monkeypatch):
    setup_environment(monkeypatch, tmp_path)
    bridge = JarvisBridge()
    cid = json.loads(bridge.createConversation())["id"]
    for wrong in ("unknown", "other-dataset", "jarvis-knowledge/other",
                  "JARVIS-KNOWLEDGE", "jarvis-knowledge,other"):
        response = json.loads(bridge.sendMessageWithContext(
            cid, "Oi", "model", "", wrong,
        ))
        assert response == {"ok": False, "error": "invalid_knowledge_dataset"}
        assert bridge.active is False
    for wrong_scope in ("project:Other", "global,project:other"):
        response = json.loads(bridge.sendMessageWithContext(
            cid, "Oi", "model", wrong_scope, "jarvis-knowledge",
        ))
        assert response == {"ok": False, "error": "invalid_memory_scope"}
    assert json.loads(bridge.sendMessageWithContext(
        cid, "Oi", "model", "", "",
    )) == {"ok": False, "error": "context_not_selected"}


def test_knowledge_worker_emits_verified_references_without_history_leak(tmp_path, monkeypatch):
    sent, calls = setup_environment(monkeypatch, tmp_path)
    store = SQLiteConversationStore(tmp_path / "jarvis.sqlite3")
    cid = store.create_conversation()
    worker = ReplyWorker(
        cid, "Por que Modular Monolith?", "model", "PRIVATE-OPENAI",
        knowledge_dataset="jarvis-knowledge",
    )
    result_events, knowledge_events = [], []
    worker.done.connect(lambda *args: result_events.append(args))
    worker.knowledgeDone.connect(lambda *args: knowledge_events.append(args))
    worker.run()

    assert result_events == [(cid, "completed", "", "NOT_REQUESTED")]
    assert len(knowledge_events) == 1
    assert knowledge_events[0][0] == cid
    evidence = json.loads(knowledge_events[0][1])
    assert evidence["knowledgeStatus"] == "RESULTS_FOUND"
    assert evidence["queryId"] == QUERY_ID
    assert evidence["references"][0]["chunk_id"] == CHUNK_ID
    assert evidence["references"][0]["document_id"] == DOCUMENT_ID
    assert "PRIVATE-" not in json.dumps(evidence)
    assert calls == [
        ("list", {"limit": 100, "offset": 0}),
        ("query", {"query": "Por que Modular Monolith?",
                   "datasets": ["jarvis-knowledge"], "top_k": 3}),
    ]
    assert any("Evidências documentais" in m["content"] for m in sent[0])
    assert store.completed_context(cid) == [
        {"role": "user", "content": "Por que Modular Monolith?"},
        {"role": "assistant", "content": "Conforme o ADR-0001."},
    ]
    assert worker.api_key == ""


def test_without_knowledge_worker_never_touches_memory_vault(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(WindowsCredentialStore, "get_memory_key",
                        lambda self: (_ for _ in ()).throw(
                            AssertionError("No Knowledge requested")
                        ))
    cid = SQLiteConversationStore(tmp_path / "jarvis.sqlite3").create_conversation()
    class Responses:
        def create(self, *, model, input, stream):
            yield SimpleNamespace(type="response.output_text.delta", delta="Olá")
            yield SimpleNamespace(type="response.completed", delta="")
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(
        OpenAI=lambda **kw: SimpleNamespace(responses=Responses()),
    ))
    worker = ReplyWorker(cid, "Oi", "model", "PRIVATE-OPENAI")
    knowledge_events = []
    worker.knowledgeDone.connect(lambda *args: knowledge_events.append(args))
    worker.run()
    assert knowledge_events == []


def test_knowledge_and_cognitive_memory_can_coexist(tmp_path, monkeypatch):
    sent, calls = setup_environment(monkeypatch, tmp_path)
    recalls = []
    class FakeCognitive:
        def __init__(self, url, key):
            assert key == "PRIVATE-MEMORY"
        def recall(self, **kwargs):
            recalls.append(kwargs)
            return []
    monkeypatch.setattr(cognitive, "CognitiveMemoryClient", FakeCognitive)
    cid = SQLiteConversationStore(tmp_path / "jarvis.sqlite3").create_conversation()
    worker = ReplyWorker(
        cid, "O que foi decidido?", "model", "PRIVATE-OPENAI",
        memory_scope="global", knowledge_dataset="jarvis-knowledge",
    )
    events = []
    worker.done.connect(lambda *args: events.append(args))
    worker.run()
    assert events == [(cid, "completed", "", "NO_RESULTS")]
    assert len(recalls) == 1 and len(calls) == 2
    assert any("Dados auxiliares" in m["content"] for m in sent[0])
    assert any("Evidências documentais" in m["content"] for m in sent[0])
