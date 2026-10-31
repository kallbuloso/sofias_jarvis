"""CLI confirmation gates for disposable TB-02 mutations (no real network)."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
from uuid import uuid4

from jarvis.memory import cognitive
from jarvis.memory.journal import MemoryOperationJournal
from jarvis.memory.test_lifecycle import TEST_A, TEST_B
from jarvis.secrets.windows import WindowsCredentialStore


def load_main():
    spec = importlib.util.spec_from_file_location(
        "jarvis_test_cli", Path(__file__).resolve().parents[1] / "main.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeCognitive:
    base_url = "https://memory.example"
    created_calls = 0
    mutated_calls = 0

    def __init__(self, url, key):
        assert url == self.base_url and key == "PRIVATE-TEST-KEY"

    def diagnose(self):
        return {"status": "COMPATIBLE"}

    def create(self, *, memory_type, scope, content, provenance, idempotency_key):
        type(self).created_calls += 1
        return {
            "memory_id": "fe32e0bf-f0b6-45ef-a775-390eb4f1aef5",
            "memory_type": memory_type, "scope": scope, "content": content,
            "lifecycle": "active", "provenance": provenance,
        }

    def get(self, memory_id):
        raise AssertionError("Remote GET must never occur for unregistered target")


def setup(monkeypatch, tmp_path):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("JARVIS_MEMORY_URL", "https://memory.example")
    monkeypatch.setattr(WindowsCredentialStore, "get_memory_key", lambda self: "PRIVATE-TEST-KEY")
    monkeypatch.setattr(cognitive, "CognitiveMemoryClient", FakeCognitive)
    FakeCognitive.created_calls = 0
    FakeCognitive.mutated_calls = 0


def test_create_is_cancelled_before_any_write(monkeypatch, tmp_path, capsys):
    setup(monkeypatch, tmp_path)
    monkeypatch.setattr("builtins.input", lambda _: "CANCELAR")
    monkeypatch.setattr(sys, "argv", ["main.py", "--memory-test-create"])
    assert load_main().main() == 0
    assert json.loads(capsys.readouterr().out.splitlines()[-1])["status"] == "CANCELLED"
    assert FakeCognitive.created_calls == 0


def test_create_is_authorized_and_registered_with_test_only_marker(monkeypatch, tmp_path, capsys):
    setup(monkeypatch, tmp_path)
    monkeypatch.setattr("builtins.input", lambda _: "CRIAR TESTE")
    monkeypatch.setattr(sys, "argv", ["main.py", "--memory-test-create"])
    assert load_main().main() == 0
    raw = capsys.readouterr().out
    result = json.loads(raw[raw.find("{"):])
    assert result["status"] == "CONFIRMED"
    assert result["memory_id"] == "fe32e0bf-f0b6-45ef-a775-390eb4f1aef5"
    assert FakeCognitive.created_calls == 1
    row = MemoryOperationJournal(tmp_path / "jarvis.sqlite3").test_item(result["memory_id"])
    assert row["lifecycle"] == "active"
    assert row["scope"] == "project:jarvis"
    assert row["marker"].startswith("jarvis-tb02-test:")
    assert "PRIVATE-TEST-KEY" not in raw


def test_test_memory_list_is_local_only(monkeypatch, tmp_path, capsys):
    setup(monkeypatch, tmp_path)
    monkeypatch.setattr("builtins.input", lambda _: "CRIAR TESTE")
    monkeypatch.setattr(sys, "argv", ["main.py", "--memory-test-create"])
    assert load_main().main() == 0
    capsys.readouterr()
    monkeypatch.setattr(WindowsCredentialStore, "get_memory_key", lambda self: (
        _ for _ in ()).throw(AssertionError("test list must not access vault")
    ))
    monkeypatch.setattr(sys, "argv", ["main.py", "--memory-test-list"])
    assert load_main().main() == 0
    result = json.loads(capsys.readouterr().out)
    assert len(result["items"]) == 1
    assert result["items"][0]["lifecycle"] == "active"


def test_teal_memory_is_denied_even_with_confirmation_prompt(monkeypatch, tmp_path, capsys):
    setup(monkeypatch, tmp_path)
    monkeypatch.setattr(sys, "argv", [
        "main.py", "--memory-test-forget",
        "ab89ac04-7134-49c6-9fa2-2880a296d50a",
    ])
    monkeypatch.setattr("builtins.input", lambda _: (
        _ for _ in ()).throw(AssertionError("must not prompt on unregistered target")
    ))
    assert load_main().main() == 2
    assert FakeCognitive.created_calls == 0
    assert "ValueError" in capsys.readouterr().err


def test_no_implicit_new_memory_id_or_other_side_effects(monkeypatch, tmp_path, capsys):
    setup(monkeypatch, tmp_path)
    monkeypatch.setattr(sys, "argv", ["main.py", "--memory-test-list"])
    assert load_main().main() == 0
    result = json.loads(capsys.readouterr().out)
    assert result["items"] == []
    assert FakeCognitive.created_calls == 0



def test_supersede_cancellation_never_calls_mutating_method(monkeypatch, tmp_path, capsys):
    setup(monkeypatch, tmp_path)
    from jarvis.memory import test_lifecycle

    target = "fe32e0bf-f0b6-45ef-a775-390eb4f1aef5"
    calls = []
    def preview(self, memory_id, *, action):
        calls.append(("preview", memory_id, action))
        return {"memory_id": target, "scope": "project:jarvis",
                "content": TEST_A, "lifecycle": "active"}
    def supersede(self, memory_id):
        calls.append(("supersede", memory_id))
        return {"status": "CONFIRMED"}
    monkeypatch.setattr(test_lifecycle.TestMemoryLab, "preview", preview)
    monkeypatch.setattr(test_lifecycle.TestMemoryLab, "supersede", supersede)
    monkeypatch.setattr(sys, "argv", ["main.py", "--memory-test-supersede", target])
    monkeypatch.setattr("builtins.input", lambda _: "SUBSTITUIR")
    assert load_main().main() == 0
    assert calls == [("preview", target, "supersede")]
    assert json.loads(capsys.readouterr().out.splitlines()[-1])["status"] == "CANCELLED"


def test_forget_needs_exact_target_uuid_confirmation(monkeypatch, tmp_path, capsys):
    setup(monkeypatch, tmp_path)
    from jarvis.memory import test_lifecycle

    target = "fe32e0bf-f0b6-45ef-a775-390eb4f1aef5"
    calls = []
    def preview(self, memory_id, *, action):
        calls.append(("preview", memory_id, action))
        return {"memory_id": target, "scope": "project:jarvis",
                "content": TEST_B, "lifecycle": "active"}
    def forget(self, memory_id):
        calls.append(("forget", memory_id))
        return {"status": "CONFIRMED", "memory_id": memory_id}
    monkeypatch.setattr(test_lifecycle.TestMemoryLab, "preview", preview)
    monkeypatch.setattr(test_lifecycle.TestMemoryLab, "forget", forget)
    monkeypatch.setattr(sys, "argv", ["main.py", "--memory-test-forget", target])
    responses = iter(["ESQUECER", f"ESQUECER {target}"])
    monkeypatch.setattr("builtins.input", lambda _: next(responses))
    assert load_main().main() == 0
    assert calls == [("preview", target, "forget")]
    capsys.readouterr()
    assert load_main().main() == 0
    assert calls[-3:] == [
        ("preview", target, "forget"),
        ("preview", target, "forget"),
        ("forget", target),
    ]
    assert json.loads(capsys.readouterr().out.splitlines()[-1])["status"] == "CONFIRMED"
