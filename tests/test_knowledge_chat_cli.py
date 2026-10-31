"""Knowledge chat opt-in and combined cognitive+documentary context (offline)."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from uuid import uuid4

from jarvis.conversation.store import SQLiteConversationStore
from jarvis.memory import knowledge, cognitive
from jarvis.secrets.windows import WindowsCredentialStore

DATASET_ID = str(uuid4())
SOURCE_ID = str(uuid4())
DOCUMENT_ID = str(uuid4())
CHUNK_ID = str(uuid4())
QUERY_ID = str(uuid4())


def main_module():
    spec = importlib.util.spec_from_file_location(
        "jarvis_knowledge_chat_cli", Path(__file__).resolve().parents[1] / "main.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def environment(monkeypatch, tmp_path):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("JARVIS_MEMORY_URL", "https://memory.example")
    monkeypatch.setattr(WindowsCredentialStore, "get_openai_key", lambda self: "FAKE-OPENAI")
    monkeypatch.setattr(WindowsCredentialStore, "get_memory_key", lambda self: "FAKE-MEMORY")
    monkeypatch.setattr("builtins.input", lambda _: "Por que Modular Monolith?")
    requests, retrievals, cognitive_recalls = [], [], []

    class Responses:
        def create(self, *, model, input, stream):
            requests.append(input)
            yield SimpleNamespace(type="response.output_text.delta", delta="Conforme ADR-0001.")
            yield SimpleNamespace(type="response.completed", delta="")

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(
        OpenAI=lambda api_key: SimpleNamespace(responses=Responses()),
    ))

    class FakeKnowledge:
        def __init__(self, url, key):
            assert url == "https://memory.example" and key == "FAKE-MEMORY"

        def list_datasets(self, **kwargs):
            retrievals.append(("list", kwargs))
            return {"items": [{
                "dataset_id": DATASET_ID, "slug": "jarvis-knowledge", "name": "JARVIS Knowledge",
                "status": "active",
            }], "total": 1}

        def query_chunks(self, **kwargs):
            retrievals.append(("query", kwargs))
            return {
                "status": "RESULTS_FOUND", "mode": "chunks",
                "datasets": ["jarvis-knowledge"], "query_id": QUERY_ID,
                "context": [{
                    "dataset_id": DATASET_ID, "source_id": SOURCE_ID,
                    "document_id": DOCUMENT_ID, "chunk_id": CHUNK_ID,
                    "source_name": "JARVIS ADR-0001",
                    "text": "MVP usa Modular Monolith por simplicidade.",
                    "score": 0.016,
                }],
                "references": [{
                    "source_id": SOURCE_ID, "document_id": DOCUMENT_ID,
                    "chunk_id": CHUNK_ID, "source_name": "JARVIS ADR-0001",
                    "quote": "Modular Monolith por simplicidade",
                    "url": None, "score": 0.016,
                }],
            }

    class FakeCognitive:
        def __init__(self, url, key):
            assert key == "FAKE-MEMORY"

        def recall(self, **kwargs):
            cognitive_recalls.append(kwargs)
            return []

    monkeypatch.setattr(knowledge, "KnowledgeClient", FakeKnowledge)
    monkeypatch.setattr(cognitive, "CognitiveMemoryClient", FakeCognitive)
    return requests, retrievals, cognitive_recalls


def test_chat_knowledge_opt_in_injects_source_and_outputs_verified_ids(monkeypatch, tmp_path, capsys):
    requests, retrievals, _ = environment(monkeypatch, tmp_path)
    monkeypatch.setattr(sys, "argv", [
        "main.py", "--chat", "--model", "model",
        "--use-knowledge", "--knowledge-dataset", "jarvis-knowledge",
    ])
    assert main_module().main() == 0
    out = capsys.readouterr().out
    assert '"knowledge_retrieval": "RESULTS_FOUND"' in out
    assert QUERY_ID in out and CHUNK_ID in out and SOURCE_ID in out
    assert "FAKE-MEMORY" not in out
    assert retrievals[0][0] == "list" and retrievals[1][0] == "query"
    _, messages = "model", requests[0]
    assert messages[0]["role"] == "developer"
    evidence = json.loads(messages[1]["content"].split("\n", 1)[1])
    assert evidence["references"][0]["chunk_id"] == CHUNK_ID
    assert messages[-1] == {"role": "user", "content": "Por que Modular Monolith?"}
    store = SQLiteConversationStore(tmp_path / "jarvis.sqlite3")
    cid = store.list_conversations()[0]["id"]
    assert [(m["role"], m["content"]) for m in store.list_messages(cid)] == [
        ("user", "Por que Modular Monolith?"), ("assistant", "Conforme ADR-0001."),
    ]


def test_chat_default_remains_unchanged_and_never_queries_knowledge(monkeypatch, tmp_path, capsys):
    requests, retrievals, _ = environment(monkeypatch, tmp_path)
    monkeypatch.setattr(sys, "argv", ["main.py", "--chat", "--model", "model"])
    assert main_module().main() == 0
    assert requests == [[{"role": "user", "content": "Por que Modular Monolith?"}]]
    assert retrievals == []
    assert "knowledge_retrieval" not in capsys.readouterr().out


def test_chat_requires_explicit_dataset_even_when_opted_in(monkeypatch, tmp_path, capsys):
    requests, retrievals, _ = environment(monkeypatch, tmp_path)
    monkeypatch.setattr(sys, "argv", ["main.py", "--chat", "--model", "model", "--use-knowledge"])
    assert main_module().main() == 2
    assert retrievals == [] and requests == []
    assert "operação não concluída" in capsys.readouterr().err


def test_chat_cannot_select_nonapproved_dataset(monkeypatch, tmp_path, capsys):
    requests, retrievals, _ = environment(monkeypatch, tmp_path)
    monkeypatch.setattr(sys, "argv", [
        "main.py", "--chat", "--model", "model",
        "--use-knowledge", "--knowledge-dataset", "other",
    ])
    assert main_module().main() == 2
    assert retrievals == [] and requests == []


def test_chat_cannot_select_dataset_without_opt_in(monkeypatch, tmp_path):
    requests, retrievals, _ = environment(monkeypatch, tmp_path)
    monkeypatch.setattr(sys, "argv", [
        "main.py", "--chat", "--model", "model", "--knowledge-dataset", "jarvis-knowledge",
    ])
    assert main_module().main() == 2
    assert retrievals == [] and requests == []


def test_memory_and_knowledge_remain_independent(monkeypatch, tmp_path, capsys):
    requests, retrievals, cognitive_recalls = environment(monkeypatch, tmp_path)
    monkeypatch.setattr(sys, "argv", [
        "main.py", "--chat", "--model", "model", "--use-memory",
        "--memory-scope", "global", "--use-knowledge",
        "--knowledge-dataset", "jarvis-knowledge",
    ])
    assert main_module().main() == 0
    assert len(retrievals) == 2 and len(cognitive_recalls) == 1
    sent = requests[0]
    assert sent[-1]["content"] == "Por que Modular Monolith?"
    assert any("Evidências documentais" in m["content"] for m in sent)
    assert any("Dados auxiliares" in m["content"] for m in sent)
    out = capsys.readouterr().out
    assert "knowledge_retrieval" in out and "memory_retrieval" in out
