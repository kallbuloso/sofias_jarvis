from __future__ import annotations

from types import SimpleNamespace

from jarvis.inference.diagnostics import LiteLLMConnectionDiagnostics


def _response(content):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content),
            )
        ]
    )


def _chunk(content="", finish_reason=None):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                delta=SimpleNamespace(content=content),
                finish_reason=finish_reason,
            )
        ]
    )


def test_diagnostics_runs_plain_structured_and_streaming_with_same_provider():
    calls = []

    def completion(**kwargs):
        calls.append(kwargs)
        if kwargs.get("stream"):
            return iter([
                _chunk("O"),
                _chunk("K"),
                _chunk("", "stop"),
            ])
        if "response_format" in kwargs:
            return _response('{"ok": true}')
        return _response("OK")

    diagnostics = LiteLLMConnectionDiagnostics(
        provider_id="gemini",
        credential="PRIVATE",
        completion_fn=completion,
        timeout=7.5,
    )

    result = diagnostics.run("gemini-3.8-flash")

    assert result["provider_id"] == "gemini"
    assert result["model"] == "gemini-3.8-flash"
    assert result["qualified_model"] == "gemini/gemini-3.8-flash"
    assert result["timeout_seconds"] == 7.5
    assert result["plain"]["ok"] is True
    assert result["structured"]["ok"] is True
    assert result["streaming"]["ok"] is True
    assert result["streaming"]["first_token_ms"] is not None

    assert len(calls) == 3
    for call in calls:
        assert call["model"] == "gemini/gemini-3.8-flash"
        assert call["api_key"] == "PRIVATE"
        assert call["timeout"] == 7.5

    assert calls[0].get("stream") is None
    assert "response_format" not in calls[0]
    assert calls[1]["response_format"]["type"] == "json_schema"
    assert calls[2]["stream"] is True


def test_diagnostics_failure_preserves_safe_error_metadata_and_redacts_secret():
    class ProviderTimeout(Exception):
        status_code = 408
        message = "request failed for token PRIVATE"

    def completion(**kwargs):
        raise ProviderTimeout("request failed for token PRIVATE")

    diagnostics = LiteLLMConnectionDiagnostics(
        provider_id="gemini",
        credential="PRIVATE",
        completion_fn=completion,
        timeout=1.0,
    )

    result = diagnostics.run("gemini-3.8-flash")

    for probe_name in ("plain", "structured", "streaming"):
        probe = result[probe_name]
        assert probe["ok"] is False
        assert probe["error_code"] == "PROVIDER_TIMEOUT"
        assert probe["error_class"] == "ProviderTimeout"
        assert probe["status_code"] == 408
        assert "PRIVATE" not in probe["detail"]
        assert "[REDACTED]" in probe["detail"]


def test_structured_probe_rejects_non_json_success_response():
    def completion(**kwargs):
        if kwargs.get("stream"):
            return iter([_chunk("OK"), _chunk("", "stop")])
        if "response_format" in kwargs:
            return _response("not-json")
        return _response("OK")

    diagnostics = LiteLLMConnectionDiagnostics(
        provider_id="openai",
        credential="PRIVATE",
        completion_fn=completion,
    )

    result = diagnostics.run("gpt-6-luna")

    assert result["plain"]["ok"] is True
    assert result["structured"]["ok"] is False
    assert result["structured"]["error_class"] == "JSONDecodeError"
    assert result["streaming"]["ok"] is True


def test_streaming_probe_reports_missing_terminal_chunk():
    def completion(**kwargs):
        if kwargs.get("stream"):
            return iter([_chunk("OK")])
        if "response_format" in kwargs:
            return _response('{"ok": true}')
        return _response("OK")

    diagnostics = LiteLLMConnectionDiagnostics(
        provider_id="anthropic",
        credential="PRIVATE",
        completion_fn=completion,
    )

    result = diagnostics.run("claude-sonnet-5-5")

    assert result["plain"]["ok"] is True
    assert result["structured"]["ok"] is True
    assert result["streaming"]["ok"] is False
    assert result["streaming"]["error_class"] == "ValueError"
