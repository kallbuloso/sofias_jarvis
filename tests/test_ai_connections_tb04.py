from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from jarvis.adapters.openai_responses import OpenAIResponsesAdapter
from jarvis.connections.manager import ConnectionManager
from jarvis.connections.store import ConnectionStore
from jarvis.inference.factory import build_inference_provider


class FakeVault:
    def __init__(self, legacy=None):
        self.legacy = legacy
        self.connection_secrets = {}

    def get_openai_key(self):
        return self.legacy

    def get_connection_secret(self, connection_id):
        return self.connection_secrets.get(connection_id)

    def set_connection_secret(self, connection_id, secret):
        self.connection_secrets[connection_id] = secret

    def delete_connection_secret(self, connection_id):
        self.connection_secrets.pop(connection_id, None)


def test_legacy_openai_key_becomes_enabled_ai_connection_without_copying_secret(tmp_path):
    store = ConnectionStore(tmp_path / "jarvis.sqlite3")
    vault = FakeVault("LEGACY-OPENAI")
    manager = ConnectionManager(store, vault)

    item = manager.ensure_default_openai_connection()
    assert item["provider_id"] == "openai"
    assert item["provider_type"] == "ai_inference"
    assert item["configured"] is True
    assert item["enabled"] is True

    persisted = store.get(item["id"])
    assert persisted["credential_ref"] == "legacy:openai:default"
    assert vault.connection_secrets == {}
    assert b"LEGACY-OPENAI" not in (tmp_path / "jarvis.sqlite3").read_bytes()


def test_openai_ai_connection_resolves_provider_connection_and_secret(tmp_path):
    store = ConnectionStore(tmp_path / "jarvis.sqlite3")
    vault = FakeVault("PRIVATE-OPENAI")
    manager = ConnectionManager(store, vault)
    migrated = manager.ensure_default_openai_connection()

    item, secret = manager.resolve_ai_connection(provider_id="openai")
    assert item["id"] == migrated["id"]
    assert item["provider_id"] == "openai"
    assert secret == "PRIVATE-OPENAI"
    assert "PRIVATE-OPENAI" not in json.dumps(item)


def test_disabled_openai_connection_cannot_start_new_inference(tmp_path):
    store = ConnectionStore(tmp_path / "jarvis.sqlite3")
    manager = ConnectionManager(store, FakeVault("PRIVATE-OPENAI"))
    item = manager.ensure_default_openai_connection()
    manager.set_enabled(item["id"], False)

    with pytest.raises(ValueError, match="AI_CONNECTION_NOT_AVAILABLE"):
        manager.resolve_ai_connection(provider_id="openai")


def test_openai_registry_declares_inference_capabilities(tmp_path):
    manager = ConnectionManager(
        ConnectionStore(tmp_path / "jarvis.sqlite3"), FakeVault(),
    )
    descriptor = next(
        item for item in manager.providers() if item["provider_id"] == "openai"
    )
    assert descriptor["provider_type"] == "ai_inference"
    assert "inference.text.streaming" in descriptor["capabilities"]
    assert "inference.structured_json" in descriptor["capabilities"]


def test_openai_adapter_structured_json_is_hidden_behind_contract():
    calls = []

    class Responses:
        def create(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(output_text='{"action":"chat","scope":null,"content":null}')

    adapter = OpenAIResponsesAdapter(SimpleNamespace(responses=Responses()))
    result = adapter.generate_json(
        model="model",
        messages=[{"role": "user", "content": "Oi"}],
        schema_name="test_schema",
        schema={
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    )
    assert result["action"] == "chat"
    assert calls[0]["stream"] is False
    assert calls[0]["text"]["format"]["type"] == "json_schema"


def test_inference_factory_supports_openai_without_leaking_sdk_to_core(monkeypatch):
    created = []

    class Client:
        def __init__(self, **kwargs):
            created.append(kwargs)
            self.responses = object()

    monkeypatch.setitem(
        __import__("sys").modules,
        "openai",
        SimpleNamespace(OpenAI=Client),
    )
    provider = build_inference_provider("openai", "PRIVATE")
    assert isinstance(provider, OpenAIResponsesAdapter)
    assert created == [{"api_key": "PRIVATE", "timeout": 30.0}]


def test_inference_factory_rejects_unknown_provider():
    with pytest.raises(Exception, match="AI_PROVIDER_UNSUPPORTED"):
        build_inference_provider("not-real", "PRIVATE")
