from __future__ import annotations

import json
import sys
from types import SimpleNamespace

import pytest

from jarvis.adapters.litellm_inference import (
    LiteLLMInferenceAdapter,
    LiteLLMInferenceError,
)
from jarvis.inference.factory import (
    InferenceProviderError,
    build_inference_provider,
    configured_inference_backend,
)


def _chunk(text="", finish_reason=None):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                delta=SimpleNamespace(content=text),
                finish_reason=finish_reason,
            )
        ]
    )


def test_litellm_stream_qualifies_openai_model_and_passes_secret_per_request():
    calls = []

    def completion(**kwargs):
        calls.append(kwargs)
        return iter([
            _chunk("Olá "),
            _chunk("Amaral"),
            _chunk("", "stop"),
        ])

    adapter = LiteLLMInferenceAdapter(
        provider_id="openai",
        litellm_prefix="openai",
        credential="PRIVATE",
        completion_fn=completion,
    )
    assert list(adapter.stream_text(
        model="gpt-6-luna",
        messages=[{"role": "user", "content": "Oi"}],
    )) == ["Olá ", "Amaral"]

    call = calls[0]
    assert call["model"] == "openai/gpt-6-luna"
    assert call["api_key"] == "PRIVATE"
    assert call["stream"] is True
    assert call["timeout"] == 30.0
    assert "max_tokens" not in call


def test_litellm_stream_preserves_already_qualified_model():
    calls = []

    def completion(**kwargs):
        calls.append(kwargs)
        return iter([_chunk("ok"), _chunk("", "stop")])

    adapter = LiteLLMInferenceAdapter(
        provider_id="anthropic",
        litellm_prefix="anthropic",
        credential="PRIVATE",
        completion_fn=completion,
    )
    assert list(adapter.stream_text(
        model="anthropic/claude-sonnet-5-5",
        messages=[{"role": "user", "content": "Oi"}],
    )) == ["ok"]
    assert calls[0]["model"] == "anthropic/claude-sonnet-5-5"
    assert calls[0]["max_tokens"] == 8192


def test_litellm_structured_output_uses_openai_format_and_anthropic_schema_compat():
    calls = []

    def completion(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content='{"action":"chat","scope":null,"content":null}'
                    )
                )
            ]
        )

    canonical = {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["chat"]},
            "scope": {
                "type": ["string", "null"],
                "enum": [None, "global", "project:jarvis"],
            },
            "content": {"type": ["string", "null"]},
        },
        "required": ["action", "scope", "content"],
        "additionalProperties": False,
    }
    adapter = LiteLLMInferenceAdapter(
        provider_id="anthropic",
        litellm_prefix="anthropic",
        credential="PRIVATE",
        completion_fn=completion,
    )
    value = adapter.generate_json(
        model="claude-sonnet-5-5",
        messages=[
            {"role": "developer", "content": "Classifique"},
            {"role": "user", "content": "Oi"},
        ],
        schema_name="jarvis_text_intent",
        schema=canonical,
    )
    assert value["action"] == "chat"

    call = calls[0]
    assert call["model"] == "anthropic/claude-sonnet-5-5"
    assert call["api_key"] == "PRIVATE"
    assert call["max_tokens"] == 4096
    fmt = call["response_format"]
    assert fmt["type"] == "json_schema"
    assert fmt["json_schema"]["name"] == "jarvis_text_intent"
    assert fmt["json_schema"]["strict"] is True
    sent_scope = fmt["json_schema"]["schema"]["properties"]["scope"]
    assert sent_scope == {
        "anyOf": [
            {
                "type": "string",
                "enum": ["global", "project:jarvis"],
            },
            {"type": "null"},
        ]
    }
    assert canonical["properties"]["scope"]["enum"][0] is None


def test_litellm_stream_rejects_nonterminal_or_empty_output():
    adapter = LiteLLMInferenceAdapter(
        provider_id="openai",
        litellm_prefix="openai",
        credential="PRIVATE",
        completion_fn=lambda **kwargs: iter([_chunk("partial")]),
    )
    with pytest.raises(LiteLLMInferenceError) as captured:
        list(adapter.stream_text(
            model="gpt-6-luna",
            messages=[{"role": "user", "content": "Oi"}],
        ))
    assert captured.value.code == "PROVIDER_RESPONSE_INCOMPLETE"


def test_litellm_normalizes_provider_error_without_raw_exception_text():
    class RateLimit(Exception):
        status_code = 429
        body = {
            "error": {
                "type": "rate_limit_error",
                "message": "safe detail",
            },
            "secret": "MUST-NOT-APPEAR",
        }

    def completion(**kwargs):
        raise RateLimit("raw PRIVATE-TOKEN")

    adapter = LiteLLMInferenceAdapter(
        provider_id="anthropic",
        litellm_prefix="anthropic",
        credential="PRIVATE",
        completion_fn=completion,
    )
    with pytest.raises(LiteLLMInferenceError) as captured:
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
    assert captured.value.code == "RATE_LIMITED"
    assert captured.value.detail == "rate_limit_error: safe detail"
    assert "PRIVATE" not in captured.value.detail
    assert "MUST-NOT-APPEAR" not in captured.value.detail


def test_factory_defaults_to_litellm_after_owner_validated_parity(monkeypatch):
    monkeypatch.delenv("JARVIS_INFERENCE_BACKEND", raising=False)
    assert configured_inference_backend() == "litellm"

    provider = build_inference_provider("anthropic", "PRIVATE")
    assert isinstance(provider, LiteLLMInferenceAdapter)
    assert provider.provider_id == "anthropic"
    assert provider.litellm_prefix == "anthropic"


def test_native_backend_remains_explicit_rollback(monkeypatch):
    monkeypatch.setenv("JARVIS_INFERENCE_BACKEND", "native")

    class FakeOpenAI:
        def __init__(self, **kwargs):
            self.responses = object()

    monkeypatch.setitem(
        sys.modules, "openai", SimpleNamespace(OpenAI=FakeOpenAI),
    )
    provider = build_inference_provider("openai", "PRIVATE")
    assert provider.__class__.__name__ == "OpenAIResponsesAdapter"


def test_factory_reads_litellm_backend_from_environment(monkeypatch):
    monkeypatch.setenv("JARVIS_INFERENCE_BACKEND", "litellm")
    provider = build_inference_provider("openai", "PRIVATE")
    assert isinstance(provider, LiteLLMInferenceAdapter)
    assert provider.litellm_prefix == "openai"


def test_invalid_backend_fails_closed(monkeypatch):
    monkeypatch.setenv("JARVIS_INFERENCE_BACKEND", "magic")
    with pytest.raises(
        InferenceProviderError, match="INFERENCE_BACKEND_INVALID"
    ):
        build_inference_provider("openai", "PRIVATE")
