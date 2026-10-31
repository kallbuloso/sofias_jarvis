"""Offline CLI gates: never ingest unapproved or non-ADR material."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
from uuid import uuid4

from jarvis.memory import knowledge_ingestion
from jarvis.secrets.windows import WindowsCredentialStore

RUN_ID = str(uuid4())
DATASET_ID = str(uuid4())


def load_main():
    path = Path(__file__).resolve().parents[1] / "main.py"
    spec = importlib.util.spec_from_file_location("jarvis_knowledge_ingest_cli", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeClient:
    effects = []
    def __init__(self, url, key):
        assert url == "https://memory.example" and key == "TOP-SECRET-KEY"

    def diagnose(self):
        return {"status": "COMPATIBLE"}

    def create_adr_dataset(self):
        self.effects.append("create")
        return {"status": "CREATED", "dataset_id": DATASET_ID,
                "slug": "jarvis-knowledge", "name": "JARVIS Knowledge"}

    def ingest_adr(self, record):
        assert record["content"].startswith("# ADR-0001")
        assert "# ADR-0002" not in record["content"]
        self.effects.append("ingest")
        return {"status": "ACCEPTED", "run_id": RUN_ID,
                "pipeline_status": "queued", "source_id": None}

    def inspect_run(self, run_id):
        self.effects.append(("run", run_id))
        return {"status": "running", "run_id": run_id}

    def dataset_stats(self):
        self.effects.append("stats")
        return {"slug": "jarvis-knowledge", "chunks": {"active": 0}}


def prepare(monkeypatch, tmp_path):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("JARVIS_MEMORY_URL", "https://memory.example")
    monkeypatch.setattr(WindowsCredentialStore, "get_memory_key",
                        lambda self: "TOP-SECRET-KEY")
    monkeypatch.setattr(knowledge_ingestion, "ADRKnowledgeClient", FakeClient)
    FakeClient.effects = []


def result(output):
    return json.loads(output[output.rfind("\n{") + 1:])


def test_dataset_creation_requires_exact_confirmation(monkeypatch, tmp_path, capsys):
    prepare(monkeypatch, tmp_path)
    monkeypatch.setattr(sys, "argv", ["main.py", "--knowledge-create-dataset"])
    replies = iter(["SIM", "CRIAR DATASET jarvis-knowledge"])
    monkeypatch.setattr("builtins.input", lambda _: next(replies))
    assert load_main().main() == 0
    assert FakeClient.effects == []
    assert result(capsys.readouterr().out)["status"] == "CANCELLED"
    assert load_main().main() == 0
    assert FakeClient.effects == ["create"]
    assert result(capsys.readouterr().out)["slug"] == "jarvis-knowledge"


def test_ingest_requires_exact_confirmation(monkeypatch, tmp_path, capsys):
    prepare(monkeypatch, tmp_path)
    monkeypatch.setattr(sys, "argv", ["main.py", "--knowledge-ingest-adr"])
    replies = iter(["NÃO", "INGESTIR ADR-0001"])
    monkeypatch.setattr("builtins.input", lambda _: next(replies))
    assert load_main().main() == 0
    assert FakeClient.effects == []
    assert result(capsys.readouterr().out)["status"] == "CANCELLED"
    assert load_main().main() == 0
    assert FakeClient.effects == ["ingest"]
    assert result(capsys.readouterr().out)["run_id"] == RUN_ID


def test_readonly_run_and_stats_never_prompt_for_confirmation(monkeypatch, tmp_path, capsys):
    prepare(monkeypatch, tmp_path)
    monkeypatch.setattr("builtins.input", lambda _: (
        _ for _ in ()).throw(AssertionError("READ operations cannot prompt"))
    )
    monkeypatch.setattr(sys, "argv", ["main.py", "--knowledge-run", RUN_ID])
    assert load_main().main() == 0
    assert result(capsys.readouterr().out)["status"] == "running"
    monkeypatch.setattr(sys, "argv", ["main.py", "--knowledge-stats"])
    assert load_main().main() == 0
    assert result(capsys.readouterr().out)["chunks"]["active"] == 0
    assert FakeClient.effects == [("run", RUN_ID), "stats"]


def test_missing_key_never_performs_mutation(monkeypatch, tmp_path, capsys):
    prepare(monkeypatch, tmp_path)
    monkeypatch.setattr(WindowsCredentialStore, "get_memory_key", lambda self: None)
    monkeypatch.setattr(sys, "argv", ["main.py", "--knowledge-create-dataset"])
    assert load_main().main() == 2
    assert FakeClient.effects == []
    assert result(capsys.readouterr().out)["status"] == "CREDENTIAL_MISSING"
