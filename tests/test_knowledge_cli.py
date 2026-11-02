"""Knowledge CLI integration tests: no real requests, never expose API keys."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
from uuid import uuid4

from jarvis.memory import knowledge
from jarvis.secrets.windows import WindowsCredentialStore


def load_main():
    path = Path(__file__).resolve().parents[1] / "main.py"
    spec = importlib.util.spec_from_file_location("jarvis_knowledge_cli", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def configure(monkeypatch, tmp_path):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("JARVIS_MEMORY_URL", "https://memory.example")
    monkeypatch.setattr(WindowsCredentialStore, "get_memory_key", lambda self: "DO-NOT-PRINT")
    calls = []

    class Client:
        def __init__(self, url, key):
            assert url == "https://memory.example" and key == "DO-NOT-PRINT"
        def diagnose(self):
            return {"status": "COMPATIBLE"}
        def list_datasets(self):
            calls.append(("list",))
            return {"items": [{"dataset_id": str(uuid4()), "slug": "main", "name": "Main",
                               "status": "active"}], "total": 1, "limit": 50, "offset": 0}
        def query_chunks(self, *, query, datasets):
            calls.append(("query", query, datasets))
            return {"status": "NO_RESULTS", "query_id": str(uuid4()),
                    "mode": "chunks", "datasets": datasets,
                    "context": [], "references": []}

    monkeypatch.setattr(knowledge, "KnowledgeClient", Client)
    return calls


def test_dataset_discovery_cli_does_not_expose_key(monkeypatch, tmp_path, capsys):
    calls = configure(monkeypatch, tmp_path)
    monkeypatch.setattr(sys, "argv", ["main.py", "--knowledge-datasets"])
    assert load_main().main() == 0
    result = capsys.readouterr().out
    assert "DO-NOT-PRINT" not in result
    assert json.loads(result)["items"][0]["slug"] == "main"
    assert calls == [("list",)]


def test_explicit_knowledge_query_keeps_source_reference_boundary(monkeypatch, tmp_path, capsys):
    calls = configure(monkeypatch, tmp_path)
    monkeypatch.setattr(sys, "argv", [
        "main.py", "--knowledge-query", "--knowledge-dataset", "jarvis-docs",
    ])
    monkeypatch.setattr("builtins.input", lambda _: "Qual decisão consta no ADR?")
    assert load_main().main() == 0
    output = capsys.readouterr().out
    assert "DO-NOT-PRINT" not in output
    assert json.loads(output)["status"] == "NO_RESULTS"
    assert calls == [("query", "Qual decisão consta no ADR?", ["jarvis-docs"])]


def test_knowledge_query_requires_explicit_dataset(monkeypatch, tmp_path, capsys):
    calls = configure(monkeypatch, tmp_path)
    monkeypatch.setattr(sys, "argv", ["main.py", "--knowledge-query"])
    assert load_main().main() == 2
    assert json.loads(capsys.readouterr().out)["status"] == "DATASET_REQUIRED"
    assert calls == []


def test_missing_credentials_does_not_dispatch(monkeypatch, tmp_path, capsys):
    calls = configure(monkeypatch, tmp_path)
    monkeypatch.setattr(WindowsCredentialStore, "get_memory_key", lambda self: None)
    monkeypatch.setattr(sys, "argv", ["main.py", "--knowledge-datasets"])
    assert load_main().main() == 2
    assert json.loads(capsys.readouterr().out)["status"] == "CREDENTIAL_MISSING"
    assert calls == []
