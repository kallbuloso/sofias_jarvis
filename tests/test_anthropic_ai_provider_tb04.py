from __future__ import annotations

import json
import sys
from types import SimpleNamespace

import pytest

from jarvis.adapters.anthropic_messages import (
    AnthropicMessagesAdapter,
    AnthropicProviderResponseError,
)
from jarvis.connections.manager import ConnectionManager
from jarvis.connections.store import ConnectionStore
from jarvis.desktop.ai_preferences import load_ai_selection, save_ai_selection
from jarvis.inference.factory import build_inference_provider


class FakeStream:
    def __init__(self, chunks, stop_reason="end_turn"):
        self.text_stream = iter(chunks)
        self._final = SimpleNamespace(stop_reason=stop_reason)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def get_final_message(self):
        return self._final


class FakeMessages:
    def __init__(self):
        self.stream_calls = []
        self.create_calls = []
        self.stream_stop_reason = "end_turn"

    def stream(self, **kwargs):
        self.stream_calls.append(kwargs)
        return FakeStream(["Olá ", "Amaral"], self.stream_stop_reason)

    def create(self, **kwargs):
        self.create_calls.append(kwargs)
        return SimpleNamespace(
            stop_reason="end_turn",
            content=[SimpleNamespace(
                type="text",
                text='{"action":"chat","scope":null,"content":null}',
            )],
        )


def test_anthropic_adapter_translates_developer_messages_to_system():
    messages = FakeMessages()
    adapter = AnthropicMessagesAdapter(SimpleNamespace(messages=messages))
    result = list(adapter.stream_text(
        model="claude-sonnet-5-5",
        messages=[
            {"role": "developer", "content": "Regra do Core"},
            {"role": "user", "content": "Oi"},
            {"role": "assistant", "content": "Olá"},
            {"role": "user", "content": "Continue"},
        ],
    ))
    assert result == ["Olá ", "Amaral"]
    call = messages.stream_calls[0]
    assert call["system"] == "Regra do Core"
    assert call["messages"] == [
        {"role": "user", "content": "Oi"},
        {"role": "assistant", "content": "Olá"},
        {"role": "user", "content": "Continue"},
    ]
    assert call["max_tokens"] == 8192


def test_anthropic_structured_output_uses_raw_json_schema():
    messages = FakeMessages()
    adapter = AnthropicMessagesAdapter(SimpleNamespace(messages=messages))
    result = adapter.generate_json(
        model="claude-sonnet-5-5",
        messages=[
            {"role": "developer", "content": "Classifique"},
            {"role": "user", "content": "Oi"},
        ],
        schema_name="jarvis_intent",
        schema={
            "type": "object",
            "properties": {"action": {"type": "string"}},
            "required": ["action"],
            "additionalProperties": False,
        },
    )
    assert result["action"] == "chat"
    call = messages.create_calls[0]
    assert call["system"] == "Classifique"
    assert call["output_config"]["format"]["type"] == "json_schema"
    assert call["output_config"]["format"]["schema"]["additionalProperties"] is False


def test_anthropic_nonfinal_stop_reason_is_not_success():
    messages = FakeMessages()
    messages.stream_stop_reason = "max_tokens"
    adapter = AnthropicMessagesAdapter(SimpleNamespace(messages=messages))
    with pytest.raises(AnthropicProviderResponseError, match="max_tokens"):
        list(adapter.stream_text(
            model="claude-sonnet-5-5",
            messages=[{"role": "user", "content": "Oi"}],
        ))


class FakeVault:
    def __init__(self):
        self.secrets = {}

    def get_openai_key(self):
        return None

    def get_connection_secret(self, connection_id):
        return self.secrets.get(connection_id)

    def set_connection_secret(self, connection_id, secret):
        self.secrets[connection_id] = secret

    def delete_connection_secret(self, connection_id):
        self.secrets.pop(connection_id, None)


def test_anthropic_connection_is_separate_disabled_and_secret_free_in_sqlite(tmp_path):
    store = ConnectionStore(tmp_path / "jarvis.sqlite3")
    vault = FakeVault()
    manager = ConnectionManager(store, vault)

    item = manager.create_ai("anthropic", "ANTHROPIC-PRIVATE", label="Claude principal")
    assert item["provider_id"] == "anthropic"
    assert item["provider_type"] == "ai_inference"
    assert item["configured"] is True
    assert item["enabled"] is False
    assert b"ANTHROPIC-PRIVATE" not in (tmp_path / "jarvis.sqlite3").read_bytes()

    enabled = manager.set_enabled(item["id"], True)
    assert enabled["enabled"] is True

    class Verifier:
        def inspect(self, secret):
            assert secret == "ANTHROPIC-PRIVATE"
            return {
                "availability": "available",
                "available_models": [
                    {"id": "claude-sonnet-5-5", "lifecycle": "active"}
                ],
            }

    manager._ai_verifiers["anthropic"] = Verifier()
    manager.verify_ai(item["id"])
    resolved, secret = manager.resolve_ai_connection(
        provider_id="anthropic",
        connection_id=item["id"],
        model_id="claude-sonnet-5-5",
    )
    assert resolved["id"] == item["id"]
    assert secret == "ANTHROPIC-PRIVATE"
    assert "ANTHROPIC-PRIVATE" not in json.dumps(resolved)


def test_ai_selection_persists_provider_connection_and_per_provider_models(
    tmp_path, monkeypatch,
):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    from uuid import uuid4
    openai_id = str(uuid4())
    anthropic_id = str(uuid4())

    first = save_ai_selection("openai", openai_id, "gpt-6-luna")
    assert first["models"] == {"openai": "gpt-6-luna"}

    second = save_ai_selection(
        "anthropic", anthropic_id, "claude-sonnet-5-5",
    )
    assert second["provider_id"] == "anthropic"
    assert second["connection_id"] == anthropic_id
    assert second["models"] == {
        "openai": "gpt-6-luna",
        "anthropic": "claude-sonnet-5-5",
    }
    assert load_ai_selection() == second
    raw = (tmp_path / "desktop-ai-selection.json").read_text()
    assert "secret" not in raw.lower()
    assert "api_key" not in raw.lower()


def test_inference_factory_builds_anthropic_adapter(monkeypatch):
    created = []

    class Client:
        def __init__(self, **kwargs):
            created.append(kwargs)
            self.messages = object()

    monkeypatch.setitem(sys.modules, "anthropic", SimpleNamespace(Anthropic=Client))
    provider = build_inference_provider("anthropic", "PRIVATE")
    assert isinstance(provider, AnthropicMessagesAdapter)
    assert created == [{"api_key": "PRIVATE", "timeout": 30.0}]

def test_anthropic_sdk_error_codes_are_normalized_without_exposing_message():
    class BillingError(Exception):
        status_code = 402
        body = {"error": {"type": "billing_error"}}

    class BillingMessages:
        def create(self, **kwargs):
            raise BillingError("credit balance is too low")

    adapter = AnthropicMessagesAdapter(
        SimpleNamespace(messages=BillingMessages())
    )
    with pytest.raises(AnthropicProviderResponseError) as captured:
        adapter.generate_json(
            model="claude-sonnet-5-5",
            messages=[{"role": "user", "content": "Oi"}],
            schema_name="x",
            schema={
                "type": "object",
                "properties": {"ok": {"type": "boolean"}},
                "required": ["ok"],
                "additionalProperties": False,
            },
        )
    assert captured.value.code == "BILLING_UNAVAILABLE"

