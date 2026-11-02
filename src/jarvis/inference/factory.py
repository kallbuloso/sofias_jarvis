"""Inference provider construction behind CONTRACT-04."""
from __future__ import annotations

import os

from jarvis.adapters.anthropic_messages import AnthropicMessagesAdapter
from jarvis.adapters.litellm_inference import LiteLLMInferenceAdapter
from jarvis.adapters.openai_responses import OpenAIResponsesAdapter
from jarvis.connections.registry import ProviderRegistry


_BACKENDS = {"native", "litellm"}


class InferenceProviderError(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def configured_inference_backend(explicit: str | None = None) -> str:
    value = (
        explicit
        if explicit is not None
        else os.getenv("JARVIS_INFERENCE_BACKEND", "litellm")
    )
    if not isinstance(value, str) or value.strip().lower() not in _BACKENDS:
        raise InferenceProviderError("INFERENCE_BACKEND_INVALID")
    return value.strip().lower()


def _build_native_provider(provider_id: str, credential: str):
    if provider_id == "openai":
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise InferenceProviderError("PROVIDER_RUNTIME_MISSING") from exc
        client = OpenAI(api_key=credential.strip(), timeout=30.0)
        return OpenAIResponsesAdapter(client)

    if provider_id == "anthropic":
        try:
            from anthropic import Anthropic
        except ImportError as exc:
            raise InferenceProviderError("PROVIDER_RUNTIME_MISSING") from exc
        client = Anthropic(api_key=credential.strip(), timeout=30.0)
        return AnthropicMessagesAdapter(client)

    raise InferenceProviderError("AI_PROVIDER_UNSUPPORTED")


def _build_litellm_provider(provider_id: str, credential: str):
    descriptor = ProviderRegistry().get(provider_id)
    if descriptor is None or descriptor.provider_type != "ai_inference":
        raise InferenceProviderError("AI_PROVIDER_UNKNOWN")
    if descriptor.transport != "litellm" or not descriptor.litellm_prefix:
        raise InferenceProviderError("AI_PROVIDER_UNSUPPORTED")
    return LiteLLMInferenceAdapter(
        provider_id=provider_id,
        litellm_prefix=descriptor.litellm_prefix,
        credential=credential,
    )


def build_inference_provider(
    provider_id: str, credential: str, *, backend: str | None = None,
):
    if not isinstance(provider_id, str) or not provider_id.strip():
        raise InferenceProviderError("AI_PROVIDER_UNKNOWN")
    if not isinstance(credential, str) or not credential.strip():
        raise InferenceProviderError("AI_CREDENTIAL_NOT_CONFIGURED")

    provider_id = provider_id.strip()
    selected = configured_inference_backend(backend)
    if selected == "native":
        return _build_native_provider(provider_id, credential)
    return _build_litellm_provider(provider_id, credential)
