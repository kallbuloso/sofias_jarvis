from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


def load_main():
    source = Path(__file__).resolve().parents[1] / "main.py"
    spec = importlib.util.spec_from_file_location("jarvis_cli", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_create_and_list_conversation(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    cli = load_main()
    monkeypatch.setattr(sys, "argv", ["main.py", "--create-conversation", "Teste"])
    assert cli.main() == 0
    capsys.readouterr()
    monkeypatch.setattr(sys, "argv", ["main.py", "--list-conversations"])
    assert cli.main() == 0
    assert "Teste" in capsys.readouterr().out


def test_chat_requires_configured_model(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("JARVIS_MODEL", raising=False)
    cli = load_main()
    monkeypatch.setattr(sys, "argv", ["main.py", "--chat"])
    assert cli.main() == 2
    assert "operação não concluída" in capsys.readouterr().err
