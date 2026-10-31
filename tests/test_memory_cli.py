"""Offline CLI integration: no endpoint contacted and no secrets printed."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

from jarvis.memory import connection
from jarvis.secrets.windows import WindowsCredentialStore


def load_main():
    spec = importlib.util.spec_from_file_location("jarvis_cli", Path(__file__).resolve().parents[1] / "main.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cli_memory_url_and_missing_key(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("JARVIS_MEMORY_URL", raising=False)
    cli = load_main()
    monkeypatch.setattr(sys, "argv", ["main.py", "--configure-memory-url", "https://memory.example/"])
    assert cli.main() == 0
    assert json.loads(capsys.readouterr().out)["status"] == "CONFIGURED"
    monkeypatch.setattr(WindowsCredentialStore, "get_memory_key", lambda self: None)
    monkeypatch.setattr(sys, "argv", ["main.py", "--memory-check"])
    assert cli.main() == 2
    assert json.loads(capsys.readouterr().out)["status"] == "CREDENTIAL_MISSING"


def test_cli_memory_check_shows_sanitized_diagnostic(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("JARVIS_MEMORY_URL", "https://memory.example")
    cli = load_main()
    monkeypatch.setattr(WindowsCredentialStore, "get_memory_key", lambda self: "SECRET-NEVER-PRINT")
    class MockConnection:
        def __init__(self, url, key):
            assert key == "SECRET-NEVER-PRINT"
        def diagnose(self):
            return {"status": "COMPATIBLE", "api_contract_version": "1"}
    monkeypatch.setattr(connection, "SofiasMemoryConnection", MockConnection)
    monkeypatch.setattr(sys, "argv", ["main.py", "--memory-check"])
    assert cli.main() == 0
    output = capsys.readouterr().out
    assert "SECRET-NEVER-PRINT" not in output
    assert json.loads(output)["status"] == "COMPATIBLE"


def test_cli_configuration_never_echoes_key(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    cli = load_main()
    monkeypatch.setattr(cli, "getpass", lambda _: "SECRET-NEVER-PRINT")
    seen = []
    monkeypatch.setattr(WindowsCredentialStore, "set_memory_key", lambda self, secret: seen.append(secret))
    monkeypatch.setattr(sys, "argv", ["main.py", "--configure-memory-key"])
    assert cli.main() == 0
    assert seen == ["SECRET-NEVER-PRINT"]
    assert "SECRET-NEVER-PRINT" not in capsys.readouterr().out
