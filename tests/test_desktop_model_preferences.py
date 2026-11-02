"""Desktop model choice is local, durable and never a credential."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from jarvis.desktop.model_preferences import (
    bootstrap_model,
    load_preferred_model,
    save_preferred_model,
)


def test_saved_model_survives_restart_and_never_touches_conversations(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("JARVIS_MODEL", raising=False)
    assert bootstrap_model() == ""
    save_preferred_model("gpt-6-luna")
    assert load_preferred_model() == "gpt-6-luna"
    assert bootstrap_model() == "gpt-6-luna"
    assert json.loads((tmp_path / "desktop-preferences.json").read_text()) == {
        "model": "gpt-6-luna"
    }
    assert not (tmp_path / "jarvis.sqlite3").exists()


def test_explicit_environment_model_wins_without_overwriting_local(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    save_preferred_model("gpt-6-luna")
    monkeypatch.setenv("JARVIS_MODEL", "gpt-6-luna2")
    assert bootstrap_model() == "gpt-6-luna2"
    assert load_preferred_model() == "gpt-6-luna"
    monkeypatch.delenv("JARVIS_MODEL")
    assert bootstrap_model() == "gpt-6-luna"


@pytest.mark.parametrize("invalid", ["", "  ", "gpt model", "x\ny", "/broken", "x" * 129])
def test_invalid_model_does_not_replace_previous_choice(tmp_path, monkeypatch, invalid):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    save_preferred_model("gpt-6-luna")
    with pytest.raises(ValueError, match="invalid_model_name"):
        save_preferred_model(invalid)
    assert load_preferred_model() == "gpt-6-luna"


def test_invalid_or_corrupt_preferences_are_ignored(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("JARVIS_MODEL", raising=False)
    file = tmp_path / "desktop-preferences.json"
    for raw in ('{', '[]', '{"model":123}', '{"model":"ok","api_key":"SECRET"}',
                '{"model":"x" ' + " " * 5000 + '}'):
        file.write_text(raw, encoding="utf-8")
        assert bootstrap_model() == ""


def test_bridge_bootstrap_uses_persisted_model_and_keeps_credentials_private(
        tmp_path, monkeypatch):
    pytest.importorskip("PySide6")
    from jarvis.desktop.bridge import JarvisBridge
    from jarvis.secrets.windows import WindowsCredentialStore

    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("JARVIS_MODEL", raising=False)
    monkeypatch.setattr(WindowsCredentialStore, "get_openai_key",
                        lambda self: "PRIVATE-OPENAI-TOKEN")
    monkeypatch.setattr(WindowsCredentialStore, "get_memory_key",
                        lambda self: None)
    save_preferred_model("gpt-6-luna")
    bridge = JarvisBridge()
    response = json.loads(bridge.bootstrap())
    assert response["model"] == "gpt-6-luna"
    assert response["credentialConfigured"] is True
    assert "PRIVATE-OPENAI-TOKEN" not in json.dumps(response)


def test_no_preferences_file_when_model_not_saved(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("JARVIS_MODEL", raising=False)
    assert load_preferred_model() == ""
    assert not list(tmp_path.glob("*"))
