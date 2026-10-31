"""GUI bridge boundary tests (execute only when optional Qt is installed)."""

from __future__ import annotations

import json

import pytest

pytest.importorskip("PySide6")

from jarvis.desktop.bridge import JarvisBridge


def test_bridge_allows_conversation_crud_without_exposing_secrets(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    bridge = JarvisBridge()
    created = json.loads(bridge.createConversation())
    assert created["ok"]
    conv = created["id"]
    assert conv in [x["id"] for x in json.loads(bridge.listConversations())["items"]]
    assert json.loads(bridge.listMessages(conv))["items"] == []
    assert json.loads(bridge.listMessages("nonexistent"))["error"] == "unknown_conversation"
    boot = json.loads(bridge.bootstrap())
    assert "credentialConfigured" in boot
    assert not any("api_key" in k.lower() or "secret" in k.lower() for k in boot)


def test_bridge_refuses_missing_model_without_dispatch(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    bridge = JarvisBridge()
    conv = json.loads(bridge.createConversation())["id"]
    result = json.loads(bridge.sendMessage(conv, "Olá", " "))
    assert result == {"ok": False, "error": "missing_text_or_model"}
    assert bridge.active is False
