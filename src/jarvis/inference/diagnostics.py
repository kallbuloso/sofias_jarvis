"""Provider-neutral LiteLLM diagnostics for configured AI Connections.

This module intentionally bypasses Conversation routing and JARVIS policy
execution after a Connection/model has been explicitly selected. Its purpose is
to isolate provider-transport behavior in LiteLLM itself.
"""
from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from time import perf_counter
from typing import Any

from jarvis.adapters.litellm_inference import (
    _error_code,
    _safe_error_detail,
)
from jarvis.connections.registry import ProviderRegistry


_DIAGNOSTIC_TIMEOUT = 30.0


def _litellm_version() -> str:
    for distribution in ("litellm-core", "litellm"):
        try:
            return version(distribution)
        except PackageNotFoundError:
            continue
    return "unknown"


def _result(
    *,
    ok: bool,
    elapsed_ms: int,
    error_code: str | None = None,
    error_class: str | None = None,
    status_code: int | None = None,
    detail: str = "",
    first_token_ms: int | None = None,
) -> dict:
    value = {
        "ok": bool(ok),
        "elapsed_ms": int(elapsed_ms),
        "error_code": error_code,
        "error_class": error_class,
        "status_code": status_code,
        "detail": detail[:500],
    }
    if first_token_ms is not None:
        value["first_token_ms"] = int(first_token_ms)
    return value


def _failure(exc: Exception, started: float, *, first_token_ms=None) -> dict:
    status = getattr(exc, "status_code", None)
    if not isinstance(status, int):
        status = None
    return _result(
        ok=False,
        elapsed_ms=round((perf_counter() - started) * 1000),
        error_code=_error_code(exc),
        error_class=type(exc).__name__,
        status_code=status,
        detail=_safe_error_detail(exc),
        first_token_ms=first_token_ms,
    )


class LiteLLMConnectionDiagnostics:
    """Run three minimal transport probes against one resolved connection."""

    def __init__(
        self,
        *,
        provider_id: str,
        credential: str,
        completion_fn=None,
        timeout: float = _DIAGNOSTIC_TIMEOUT,
    ):
        descriptor = ProviderRegistry().get(provider_id)
        if (
            descriptor is None
            or descriptor.provider_type != "ai_inference"
            or descriptor.transport != "litellm"
            or not descriptor.litellm_prefix
        ):
            raise ValueError("AI_PROVIDER_UNSUPPORTED")
        if not isinstance(credential, str) or not credential.strip():
            raise ValueError("AI_CREDENTIAL_NOT_CONFIGURED")
        self.provider_id = provider_id
        self.prefix = descriptor.litellm_prefix
        self.credential = credential.strip()
        self.timeout = float(timeout)
        self._completion_fn = completion_fn

    def _completion(self):
        if self._completion_fn is not None:
            return self._completion_fn
        from litellm import completion
        return completion

    def _model(self, model: str) -> str:
        if not isinstance(model, str) or not model.strip():
            raise ValueError("AI_MODEL_NOT_AVAILABLE")
        model = model.strip()
        prefix = f"{self.prefix}/"
        return model if model.startswith(prefix) else f"{prefix}{model}"

    def _base(self, model: str, messages: list[dict]) -> dict:
        kwargs = {
            "model": self._model(model),
            "messages": messages,
            "api_key": self.credential,
            "timeout": self.timeout,
        }
        if self.provider_id == "anthropic":
            kwargs["max_tokens"] = 256
        return kwargs

    def plain(self, model: str) -> dict:
        started = perf_counter()
        try:
            response = self._completion()(**self._base(
                model,
                [{"role": "user", "content": "Reply with exactly: OK"}],
            ))
            choices = getattr(response, "choices", None)
            message = getattr(choices[0], "message", None) if choices else None
            content = getattr(message, "content", None) if message else None
            if not isinstance(content, str) or not content.strip():
                raise ValueError("empty diagnostic response")
            return _result(
                ok=True,
                elapsed_ms=round((perf_counter() - started) * 1000),
            )
        except Exception as exc:
            return _failure(exc, started)

    def structured(self, model: str) -> dict:
        started = perf_counter()
        kwargs = self._base(
            model,
            [{
                "role": "user",
                "content": "Return an object whose ok property is true.",
            }],
        )
        kwargs["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": "jarvis_litellm_diagnostic",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "ok": {"type": "boolean"},
                    },
                    "required": ["ok"],
                    "additionalProperties": False,
                },
            },
        }
        try:
            response = self._completion()(**kwargs)
            choices = getattr(response, "choices", None)
            message = getattr(choices[0], "message", None) if choices else None
            content = getattr(message, "content", None) if message else None
            if not isinstance(content, str) or not content.strip():
                raise ValueError("empty diagnostic structured response")
            return _result(
                ok=True,
                elapsed_ms=round((perf_counter() - started) * 1000),
            )
        except Exception as exc:
            return _failure(exc, started)

    def streaming(self, model: str) -> dict:
        started = perf_counter()
        first_token_ms = None
        try:
            kwargs = self._base(
                model,
                [{"role": "user", "content": "Reply with exactly: OK"}],
            )
            kwargs["stream"] = True
            stream = self._completion()(**kwargs)
            yielded = False
            completed = False
            for chunk in stream:
                choices = getattr(chunk, "choices", None)
                if not choices:
                    continue
                choice = choices[0]
                delta = getattr(choice, "delta", None)
                content = getattr(delta, "content", None) if delta else None
                if isinstance(content, str) and content:
                    yielded = True
                    if first_token_ms is None:
                        first_token_ms = round(
                            (perf_counter() - started) * 1000
                        )
                finish_reason = getattr(choice, "finish_reason", None)
                if finish_reason is not None:
                    completed = True
            if not yielded:
                raise ValueError("empty diagnostic stream")
            if not completed:
                raise ValueError("stream ended without finish reason")
            return _result(
                ok=True,
                elapsed_ms=round((perf_counter() - started) * 1000),
                first_token_ms=first_token_ms,
            )
        except Exception as exc:
            return _failure(
                exc, started, first_token_ms=first_token_ms,
            )

    def run(self, model: str) -> dict:
        qualified_model = self._model(model)
        return {
            "litellm_version": _litellm_version(),
            "provider_id": self.provider_id,
            "model": model.strip(),
            "qualified_model": qualified_model,
            "timeout_seconds": self.timeout,
            "plain": self.plain(model),
            "structured": self.structured(model),
            "streaming": self.streaming(model),
        }
