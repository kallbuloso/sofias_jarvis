"""LiteLLM provider-compatibility adapter behind CONTRACT-04.

JARVIS owns provider/connection/model policy and credentials. LiteLLM only
normalizes provider transport and response semantics for an already-resolved
connection.
"""
from __future__ import annotations

from collections.abc import Callable, Iterator
import json
from typing import Any


class LiteLLMInferenceError(RuntimeError):
    def __init__(
        self, message: str, *, code: str = "PROVIDER_REQUEST_FAILED",
        detail: str = "",
    ):
        self.code = code
        self.detail = detail[:500]
        super().__init__(message)


def _safe_error_detail(exc: Exception) -> str:
    """Keep only normalized provider error type/message, never raw request data."""
    body = getattr(exc, "body", None)
    error_type = ""
    message = ""
    if isinstance(body, dict):
        nested = body.get("error")
        if isinstance(nested, dict):
            raw_type = nested.get("type")
            raw_message = nested.get("message")
            if isinstance(raw_type, str):
                error_type = raw_type.strip()
            if isinstance(raw_message, str):
                message = raw_message.strip()
        elif isinstance(body.get("message"), str):
            message = body["message"].strip()
    parts = [item for item in (error_type, message) if item]
    return " ".join(": ".join(parts).split())[:500]


def _error_code(exc: Exception) -> str:
    status = getattr(exc, "status_code", None)
    body = getattr(exc, "body", None)
    error_type = ""
    message = ""
    if isinstance(body, dict):
        nested = body.get("error")
        if isinstance(nested, dict):
            if isinstance(nested.get("type"), str):
                error_type = nested["type"].lower()
            if isinstance(nested.get("message"), str):
                message = nested["message"].lower()

    if (status == 402 or "billing" in error_type or "credit balance" in message
            or "spend limit" in message):
        return "BILLING_UNAVAILABLE"
    if status == 400:
        return "PROVIDER_REQUEST_INVALID"
    if status == 401:
        return "AUTHENTICATION_FAILED"
    if status == 403:
        return "PERMISSION_INSUFFICIENT"
    if status == 404:
        return "MODEL_NOT_AVAILABLE"
    if status == 408:
        return "PROVIDER_TIMEOUT"
    if status == 429:
        return "RATE_LIMITED"
    if isinstance(status, int) and status >= 500:
        return "PROVIDER_UNAVAILABLE"

    name = type(exc).__name__.lower()
    if "timeout" in name:
        return "PROVIDER_TIMEOUT"
    if "connection" in name or "serviceunavailable" in name:
        return "PROVIDER_UNAVAILABLE"
    if "ratelimit" in name:
        return "RATE_LIMITED"
    if "authentication" in name:
        return "AUTHENTICATION_FAILED"
    if "permission" in name:
        return "PERMISSION_INSUFFICIENT"
    if "notfound" in name:
        return "MODEL_NOT_AVAILABLE"
    return "PROVIDER_REQUEST_FAILED"


def _provider_schema(value: Any, provider_id: str) -> Any:
    """Provider compatibility without changing the canonical JARVIS schema."""
    if isinstance(value, list):
        return [_provider_schema(item, provider_id) for item in value]
    if not isinstance(value, dict):
        return value

    node = {
        key: _provider_schema(item, provider_id)
        for key, item in value.items()
        if key not in {"type", "enum"}
    }
    declared_type = value.get("type")
    enum = value.get("enum")

    # Anthropic rejects nullable enum expressed as type=[..., null] plus an
    # enum containing null. The native parity baseline proved anyOf works.
    if (provider_id == "anthropic"
            and isinstance(declared_type, list)
            and "null" in declared_type
            and isinstance(enum, list)
            and None in enum):
        non_null_types = [item for item in declared_type if item != "null"]
        non_null_enum = [item for item in enum if item is not None]
        if not non_null_types:
            return {**node, "type": "null"}
        typed_branch = {
            "type": (
                non_null_types[0]
                if len(non_null_types) == 1 else non_null_types
            )
        }
        if non_null_enum:
            typed_branch["enum"] = non_null_enum
        node["anyOf"] = [typed_branch, {"type": "null"}]
        return node

    if "type" in value:
        node["type"] = _provider_schema(declared_type, provider_id)
    if "enum" in value:
        node["enum"] = _provider_schema(enum, provider_id)
    return node


class LiteLLMInferenceAdapter:
    """One CONTRACT-04 adapter for LiteLLM-supported chat providers."""

    def __init__(
        self, *, provider_id: str, litellm_prefix: str, credential: str,
        completion_fn: Callable[..., Any] | None = None,
        timeout: float = 30.0,
        max_tokens: int = 8192,
    ):
        if not isinstance(provider_id, str) or not provider_id.strip():
            raise ValueError("provider_id is required")
        if not isinstance(litellm_prefix, str) or not litellm_prefix.strip():
            raise ValueError("litellm_prefix is required")
        if not isinstance(credential, str) or not credential.strip():
            raise ValueError("credential is required")
        self.provider_id = provider_id.strip()
        self.litellm_prefix = litellm_prefix.strip().rstrip("/")
        self.credential = credential.strip()
        self._completion_fn = completion_fn
        self.timeout = timeout
        self.max_tokens = max_tokens

    def _completion(self) -> Callable[..., Any]:
        if self._completion_fn is not None:
            return self._completion_fn
        try:
            from litellm import completion
        except ImportError as exc:
            raise LiteLLMInferenceError(
                "LiteLLM Core is not installed",
                code="PROVIDER_RUNTIME_MISSING",
            ) from exc
        return completion

    def _model(self, model: str) -> str:
        if not isinstance(model, str) or not model.strip():
            raise ValueError("AI model must be configured")
        model = model.strip()
        prefix = f"{self.litellm_prefix}/"
        return model if model.startswith(prefix) else f"{prefix}{model}"

    def _base_kwargs(self, model: str, messages: list[dict]) -> dict:
        if not isinstance(messages, list) or not messages:
            raise ValueError("At least one message is required")
        kwargs = {
            "model": self._model(model),
            "messages": messages,
            "api_key": self.credential,
            "timeout": self.timeout,
        }
        # Anthropic's native endpoint requires a completion limit. Keeping this
        # inside the compatibility adapter avoids provider syntax in the Core.
        if self.provider_id == "anthropic":
            kwargs["max_tokens"] = self.max_tokens
        return kwargs

    def stream_text(
        self, *, model: str, messages: list[dict],
    ) -> Iterator[str]:
        kwargs = self._base_kwargs(model, messages)
        kwargs["stream"] = True
        try:
            stream = self._completion()(**kwargs)
            completed = False
            yielded = False
            for chunk in stream:
                choices = getattr(chunk, "choices", None)
                if not choices:
                    continue
                choice = choices[0]
                delta = getattr(choice, "delta", None)
                content = getattr(delta, "content", None) if delta is not None else None
                if isinstance(content, str) and content:
                    yielded = True
                    yield content
                finish_reason = getattr(choice, "finish_reason", None)
                if finish_reason is not None:
                    if finish_reason not in {"stop", "end_turn", "stop_sequence"}:
                        raise LiteLLMInferenceError(
                            f"Provider ended with {finish_reason}",
                            code="PROVIDER_RESPONSE_INCOMPLETE",
                        )
                    completed = True
            if yielded and not completed:
                raise LiteLLMInferenceError(
                    "LiteLLM stream ended without a terminal finish reason",
                    code="PROVIDER_RESPONSE_INCOMPLETE",
                )
            if not yielded:
                raise LiteLLMInferenceError(
                    "LiteLLM stream produced no text",
                    code="PROVIDER_RESPONSE_INVALID",
                )
        except LiteLLMInferenceError:
            raise
        except Exception as exc:
            raise LiteLLMInferenceError(
                "LiteLLM streaming request failed",
                code=_error_code(exc),
                detail=_safe_error_detail(exc),
            ) from exc

    def generate_json(
        self, *, model: str, messages: list[dict],
        schema_name: str, schema: dict,
    ) -> dict:
        if not isinstance(schema_name, str) or not schema_name.strip():
            raise ValueError("schema_name is required")
        if not isinstance(schema, dict):
            raise ValueError("schema must be an object")

        kwargs = self._base_kwargs(model, messages)
        if self.provider_id == "anthropic":
            kwargs["max_tokens"] = min(self.max_tokens, 4096)
        kwargs["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": schema_name.strip(),
                "strict": True,
                "schema": _provider_schema(schema, self.provider_id),
            },
        }
        try:
            response = self._completion()(**kwargs)
        except Exception as exc:
            raise LiteLLMInferenceError(
                "LiteLLM structured request failed",
                code=_error_code(exc),
                detail=_safe_error_detail(exc),
            ) from exc

        try:
            choices = getattr(response, "choices", None)
            if not choices:
                raise ValueError("missing choices")
            message = getattr(choices[0], "message", None)
            raw = getattr(message, "content", None) if message is not None else None
            if not isinstance(raw, str) or not raw or len(raw) > 18000:
                raise ValueError("invalid structured content")
            value = json.loads(raw)
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise LiteLLMInferenceError(
                "LiteLLM returned invalid structured output",
                code="PROVIDER_RESPONSE_INVALID",
            ) from exc
        if not isinstance(value, dict):
            raise LiteLLMInferenceError(
                "LiteLLM returned non-object structured output",
                code="PROVIDER_RESPONSE_INVALID",
            )
        return value
