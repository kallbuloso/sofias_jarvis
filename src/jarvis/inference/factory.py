"""Inference provider construction behind CONTRACT-04."""
from __future__ import annotations

from jarvis.adapters.openai_responses import OpenAIResponsesAdapter


class InferenceProviderError(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def build_inference_provider(provider_id: str, credential: str):
    if not isinstance(provider_id, str) or not provider_id.strip():
        raise InferenceProviderError("AI_PROVIDER_UNKNOWN")
    if not isinstance(credential, str) or not credential.strip():
        raise InferenceProviderError("AI_CREDENTIAL_NOT_CONFIGURED")

    if provider_id == "openai":
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise InferenceProviderError("PROVIDER_RUNTIME_MISSING") from exc
        client = OpenAI(api_key=credential.strip(), timeout=30.0)
        return OpenAIResponsesAdapter(client)

    raise InferenceProviderError("AI_PROVIDER_UNSUPPORTED")
