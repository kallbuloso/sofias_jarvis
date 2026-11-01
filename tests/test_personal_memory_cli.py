"""B-01 CLI user-memory confirmations: offline, no actual Memory service."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
from uuid import uuid4

import pytest

from jarvis.memory import cognitive
from jarvis.memory.journal import MemoryOperationJournal
from jarvis.secrets.windows import WindowsCredentialStore


def main_module():
    spec = importlib.util.spec_from_file_location(
        "jarvis_personal_cli", Path(__file__).resolve().parents[1] / "main.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def setup(monkeypatch, tmp_path):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("JARVIS_MEMORY_URL", "https://memory.example")
    monkeypatch.setattr(WindowsCredentialStore, "get_memory_key", lambda self: "PRIVATE-KEY")
    operation_id, memory_id = str(uuid4()), str(uuid4())
    journal = MemoryOperationJournal(tmp_path / "jarvis.sqlite3")
    journal.prepare(operation_id, "https://memory.example", {
        "idempotency_key": operation_id, "memory_type": "profile",
        "scope": "global", "content": "Prefiro teal.",
        "provenance": {"origin_kind": "user_asserted", "source_system": "jarvis",
                       "source_ref": f"memory-operation:{operation_id}"},
    })
    journal.claim(operation_id)
    journal.resolve(operation_id, status="confirmed", memory_id=memory_id)
    calls = []
    record = {
        "memory_id": memory_id, "memory_type": "profile",
        "scope": "global", "content": "Prefiro teal.", "lifecycle": "active",
        "provenance": {"origin_kind": "user_asserted", "source_system": "jarvis",
                       "source_ref": f"memory-operation:{operation_id}"},
    }
    class FakeClient:
        base_url = "https://memory.example"
        def __init__(self, url, key):
            assert url == self.base_url and key == "PRIVATE-KEY"
        def diagnose(self):
            return {"status": "COMPATIBLE"}
        def get(self, memory_id):
            calls.append("get")
            return dict(record)
        def forget(self, memory_id, *, idempotency_key):
            calls.append("forget")
            return {**record, "scope": None, "content": None,
                    "lifecycle": "forgotten"}
        def supersede(self, memory_id, *, content, provenance, idempotency_key):
            calls.append("supersede")
            replacement_id = str(uuid4())
            return {
                "old": {**record, "lifecycle": "superseded",
                        "superseded_by": replacement_id},
                "replacement": {**record, "memory_id": replacement_id,
                                "content": content, "provenance": provenance},
            }
    monkeypatch.setattr(cognitive, "CognitiveMemoryClient", FakeClient)
    return memory_id, journal, calls


@pytest.mark.parametrize("action,confirmation", [
    ("--memory-forget", "NÃO"),
    ("--memory-supersede", "NÃO"),
])
def test_cancel_never_mutates(monkeypatch, capsys, setup, action, confirmation):
    memory_id, journal, calls = setup
    answers = iter(["Prefiro azul.", confirmation] if action == "--memory-supersede"
                   else [confirmation])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    monkeypatch.setattr(sys, "argv", ["main.py", action, memory_id])
    assert main_module().main() == 0
    assert "CANCELLED" in capsys.readouterr().out
    assert calls == ["get"]
    assert journal.owned_user_memory(memory_id, "https://memory.example") is not None


def test_forget_requires_literal_uuid(monkeypatch, capsys, setup):
    memory_id, journal, calls = setup
    monkeypatch.setattr("builtins.input", lambda _: "ESQUECER " + memory_id)
    monkeypatch.setattr(sys, "argv", ["main.py", "--memory-forget", memory_id])
    assert main_module().main() == 0
    output = capsys.readouterr().out
    outcome = json.loads(output[output.rfind("{"):])
    assert outcome["status"] == "CONFIRMED"
    audit = journal.get(outcome["operation_id"])
    assert audit["confirmation_ref"].startswith("user-confirmation:")
    assert audit["confirmation_method"] == "cli_typed"
    assert audit["confirmed_by_user_at"] is not None
    assert calls == ["get", "get", "forget"]


def test_supersede_requires_literal_uuid_and_preserves_journal(monkeypatch, capsys, setup):
    memory_id, journal, calls = setup
    answers = iter(["Prefiro azul.", "SUBSTITUIR " + memory_id])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    monkeypatch.setattr(sys, "argv", ["main.py", "--memory-supersede", memory_id])
    assert main_module().main() == 0
    output = capsys.readouterr().out
    assert '"status": "CONFIRMED"' in output
    outcome = json.loads(output[output.rfind("{"):])
    audit = journal.get(outcome["operation_id"])
    assert audit["confirmation_ref"].startswith("user-confirmation:")
    assert audit["confirmation_method"] == "cli_typed"
    assert audit["confirmed_by_user_at"] is not None
    assert calls == ["get", "get", "supersede"]
