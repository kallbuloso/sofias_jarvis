"""Explicit cognitive Create command, with no live HTTP requests."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

from jarvis.memory import cognitive
from jarvis.memory.journal import MemoryOperationJournal
from jarvis.secrets.windows import WindowsCredentialStore


def load_main():
    path = Path(__file__).resolve().parents[1] / "main.py"
    spec = importlib.util.spec_from_file_location("jarvis_cli", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def configure(monkeypatch, tmp_path, response=None, error=None):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("JARVIS_MEMORY_URL", "https://memory.example")
    monkeypatch.setattr(WindowsCredentialStore, "get_memory_key", lambda self: "DONT-LOG-ME")
    calls = []

    class FakeClient:
        def __init__(self, url, key):
            assert key == "DONT-LOG-ME"
            assert url == "https://memory.example"

        def diagnose(self):
            return {"status": "COMPATIBLE"}

        def create(self, **kwargs):
            calls.append(kwargs)
            if error:
                raise error
            return {"memory_id": "101c823a-dd1b-41a3-a11c-94ea1f4ee70b",
                    "scope": kwargs["scope"], "lifecycle": "active"}

    monkeypatch.setattr(cognitive, "CognitiveMemoryClient", FakeClient)
    return calls


def test_explicit_confirmation_is_required(monkeypatch, tmp_path, capsys):
    calls = configure(monkeypatch, tmp_path)
    cli = load_main()
    inputs = iter(["Prefiro teal", "não"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    monkeypatch.setattr(sys, "argv", ["main.py", "--memory-create", "--memory-scope", "global"])
    assert cli.main() == 0
    assert json.loads(capsys.readouterr().out.splitlines()[-1])["status"] == "CANCELLED"
    assert calls == []


def test_authorized_write_persists_confirmed_identity(monkeypatch, tmp_path, capsys):
    calls = configure(monkeypatch, tmp_path)
    cli = load_main()
    inputs = iter(["Prefiro teal", "GRAVAR"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    monkeypatch.setattr(sys, "argv", ["main.py", "--memory-create", "--memory-scope", "global"])
    assert cli.main() == 0
    output = capsys.readouterr().out
    assert "DONT-LOG-ME" not in output
    data = json.loads(output[output.find("{"):])
    assert data["status"] == "CONFIRMED"
    assert len(calls) == 1
    assert calls[0]["provenance"]["origin_kind"] == "user_asserted"
    assert calls[0]["provenance"]["source_ref"] == "memory-operation:" + data["operation_id"]
    assert MemoryOperationJournal(tmp_path / "jarvis.sqlite3").get(data["operation_id"])["status"] == "confirmed"


def test_unknown_outcome_is_not_retried(monkeypatch, tmp_path, capsys):
    from jarvis.memory.cognitive import CognitiveMemoryError

    calls = configure(monkeypatch, tmp_path, error=CognitiveMemoryError("RESULT_UNKNOWN"))
    cli = load_main()
    inputs = iter(["Prefiro teal", "GRAVAR"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    monkeypatch.setattr(sys, "argv", ["main.py", "--memory-create", "--memory-scope", "global"])
    assert cli.main() == 2
    output = capsys.readouterr().out
    data = json.loads(output[output.find("{"):])
    assert data["status"] == "RESULT_UNKNOWN"
    assert data["retry_automatically"] is False
    assert len(calls) == 1
    assert MemoryOperationJournal(tmp_path / "jarvis.sqlite3").get(data["operation_id"])["status"] == "unknown"


def test_scope_must_be_explicit_and_exact(monkeypatch, tmp_path, capsys):
    calls = configure(monkeypatch, tmp_path)
    cli = load_main()
    for params in ([], ["--memory-scope", "project:Other"], ["--memory-scope", "global", "--memory-scope", "project:jarvis"]):
        monkeypatch.setattr(sys, "argv", ["main.py", "--memory-create", *params])
        assert cli.main() == 2
        assert calls == []
        capsys.readouterr()



def test_cli_rejects_secret_like_memory_content(monkeypatch, tmp_path, capsys):
    calls = configure(monkeypatch, tmp_path)
    cli = load_main()
    monkeypatch.setattr("builtins.input", lambda _: "Minha senha: ultra-secreta")
    monkeypatch.setattr(sys, "argv", ["main.py", "--memory-create", "--memory-scope", "global"])
    assert cli.main() == 2
    assert json.loads(capsys.readouterr().out)["status"] == "SENSITIVE_CONTENT_REJECTED"
    assert calls == []
