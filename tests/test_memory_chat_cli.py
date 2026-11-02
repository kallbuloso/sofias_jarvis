"""CLI read-only memory opt-in: fake provider and fake Memory, no real network."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

from jarvis.conversation.store import SQLiteConversationStore
from jarvis.memory import cognitive
from jarvis.secrets.windows import WindowsCredentialStore


def load_main():
    spec = importlib.util.spec_from_file_location(
        "jarvis_cli", Path(__file__).resolve().parents[1] / "main.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def configure_chat(monkeypatch, tmp_path, *, memory_exists=True):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("JARVIS_MEMORY_URL", "https://memory.example")
    monkeypatch.setattr(WindowsCredentialStore, "get_openai_key", lambda self: "FAKE-OPENAI")
    monkeypatch.setattr(WindowsCredentialStore, "get_memory_key", lambda self: "FAKE-MEMORY")
    inputs, recalls = [], []

    class Responses:
        def create(self, *, model, input, stream):
            inputs.append(input)
            yield SimpleNamespace(type="response.output_text.delta", delta="Cor teal.")
            yield SimpleNamespace(type="response.completed", delta="")

    monkeypatch.setitem(
        sys.modules, "openai",
        SimpleNamespace(OpenAI=lambda api_key: SimpleNamespace(responses=Responses())),
    )

    class MemoryClient:
        def __init__(self, url, key):
            assert url == "https://memory.example"
            assert key == "FAKE-MEMORY"

        def recall(self, **kwargs):
            recalls.append(kwargs)
            if not memory_exists:
                return []
            return [{
                "memory": {
                    "memory_id": "ab89ac04-7134-49c6-9fa2-2880a296d50a",
                    "scope": "global", "content": "Prefiro a cor teal",
                    "lifecycle": "active",
                    "provenance": {"origin_kind": "user_asserted"},
                },
                "relevance": 0.774, "is_current_truth": True,
            }]

    monkeypatch.setattr(cognitive, "CognitiveMemoryClient", MemoryClient)
    monkeypatch.setattr("builtins.input", lambda prompt: "Qual minha cor preferida?")
    return inputs, recalls


def test_explicit_memory_chat_uses_recall_without_storing_evidence(monkeypatch, tmp_path, capsys):
    requests, recalls = configure_chat(monkeypatch, tmp_path)
    cli = load_main()
    monkeypatch.setattr(sys, "argv", [
        "main.py", "--chat", "--model", "configured-model",
        "--use-memory", "--memory-scope", "global",
    ])
    assert cli.main() == 0
    output = capsys.readouterr().out
    assert "Cor teal." in output
    assert '"memory_retrieval": "RESULTS_FOUND"' in output
    assert "FAKE-MEMORY" not in output and "FAKE-OPENAI" not in output
    assert len(recalls) == 1 and recalls[0]["scopes"] == ["global"]
    assert len(requests) == 1 and requests[0][-1]["content"] == "Qual minha cor preferida?"
    assert "Prefiro a cor teal" in requests[0][1]["content"]
    store = SQLiteConversationStore(tmp_path / "jarvis.sqlite3")
    conversation_id = store.list_conversations()[0]["id"]
    assert [(m["role"], m["content"]) for m in store.list_messages(conversation_id)] == [
        ("user", "Qual minha cor preferida?"), ("assistant", "Cor teal."),
    ]


def test_default_chat_does_not_contact_memory(monkeypatch, tmp_path, capsys):
    requests, recalls = configure_chat(monkeypatch, tmp_path)
    cli = load_main()
    monkeypatch.setattr(sys, "argv", ["main.py", "--chat", "--model", "configured-model"])
    assert cli.main() == 0
    output = capsys.readouterr().out
    assert "Cor teal." in output
    assert "memory_retrieval" not in output
    assert recalls == []
    assert requests == [[{"role": "user", "content": "Qual minha cor preferida?"}]]


def test_explicit_memory_chat_requires_scope(monkeypatch, tmp_path, capsys):
    requests, recalls = configure_chat(monkeypatch, tmp_path)
    cli = load_main()
    monkeypatch.setattr(sys, "argv", [
        "main.py", "--chat", "--model", "configured-model", "--use-memory",
    ])
    assert cli.main() == 2
    assert not recalls and not requests
    assert "operação não concluída" in capsys.readouterr().err


def test_memory_unavailable_degrades_without_claiming_recall(monkeypatch, tmp_path, capsys):
    requests, recalls = configure_chat(monkeypatch, tmp_path)
    monkeypatch.delenv("JARVIS_MEMORY_URL", raising=False)
    monkeypatch.setattr(WindowsCredentialStore, "get_memory_key", lambda self: None)
    cli = load_main()
    monkeypatch.setattr(sys, "argv", [
        "main.py", "--chat", "--model", "configured-model",
        "--use-memory", "--memory-scope", "global",
    ])
    assert cli.main() == 0
    output = capsys.readouterr().out
    assert '"memory_retrieval": "UNAVAILABLE"' in output
    assert len(requests) == 1 and recalls == []
    assert '"status":"UNAVAILABLE"' in requests[0][1]["content"]
