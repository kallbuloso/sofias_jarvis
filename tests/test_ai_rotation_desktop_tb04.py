from __future__ import annotations

import json

import pytest

pytest.importorskip("PySide6")

from jarvis.connections.manager import ConnectionManager
from jarvis.connections.store import ConnectionStore
from jarvis.desktop.bridge import JarvisBridge
from jarvis.secrets.windows import WindowsCredentialStore


def test_disabled_selected_anthropic_never_silently_falls_back_to_openai(
    tmp_path, monkeypatch,
):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    secrets = {}

    monkeypatch.setattr(
        WindowsCredentialStore, "get_openai_key",
        lambda self: "OPENAI-PRIVATE",
    )
    monkeypatch.setattr(
        WindowsCredentialStore, "get_memory_key",
        lambda self: None,
    )
    monkeypatch.setattr(
        WindowsCredentialStore, "get_connection_secret",
        lambda self, connection_id: secrets.get(connection_id),
    )
    monkeypatch.setattr(
        WindowsCredentialStore, "set_connection_secret",
        lambda self, connection_id, secret: secrets.__setitem__(
            connection_id, secret
        ),
    )
    monkeypatch.setattr(
        WindowsCredentialStore, "delete_connection_secret",
        lambda self, connection_id: secrets.pop(connection_id, None),
    )

    bridge = JarvisBridge()
    initial = json.loads(bridge.bootstrap())
    assert initial["aiProvider"] == "openai"

    manager = ConnectionManager(
        ConnectionStore(tmp_path / "jarvis.sqlite3"),
        WindowsCredentialStore(),
    )
    anthropic = manager.create_ai(
        "anthropic", "ANTHROPIC-PRIVATE", label="Claude principal",
    )
    manager.set_enabled(anthropic["id"], True)

    class Verifier:
        def inspect(self, secret):
            return {
                "availability": "available",
                "available_models": [
                    {"id": "claude-sonnet-5-5", "lifecycle": "active"}
                ],
            }

    manager._ai_verifiers["anthropic"] = Verifier()
    manager.verify_ai(anthropic["id"])

    selected = json.loads(bridge.selectAIConnection(
        "anthropic", anthropic["id"], "claude-sonnet-5-5",
    ))
    assert selected["ok"] is True
    manager.set_enabled(anthropic["id"], False)

    conv = json.loads(bridge.createConversation())["id"]
    refused = json.loads(bridge.sendMessage(conv, "Oi", "claude-sonnet-5-5"))
    assert refused["ok"] is False
    assert refused["error"] == "AI_CONNECTION_NOT_AVAILABLE"

    restarted = JarvisBridge()
    boot = json.loads(restarted.bootstrap())
    assert boot["aiProvider"] == "anthropic"
    assert boot["aiConnectionId"] == anthropic["id"]
    assert boot["credentialConfigured"] is False
