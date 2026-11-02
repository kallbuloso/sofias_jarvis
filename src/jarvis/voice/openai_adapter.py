"""OpenAI STT adapter for CONTRACT-05's final-transcript subset."""
from __future__ import annotations

import os


class VoiceProviderError(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class OpenAITranscriptionAdapter:
    """Transcribe one completed WAV turn; partial events are intentionally absent."""

    def __init__(self, api_key: str, *, model: str | None = None):
        if not isinstance(api_key, str) or not api_key.strip():
            raise VoiceProviderError("AUTH_REQUIRED")
        self.api_key = api_key
        self.model = (model or os.getenv("JARVIS_STT_MODEL") or "gpt-transcribe").strip()
        if not self.model:
            raise VoiceProviderError("INVALID_MODEL")

    def transcribe(self, wav_bytes: bytes) -> str:
        if not isinstance(wav_bytes, (bytes, bytearray)) or len(wav_bytes) < 44:
            raise VoiceProviderError("INVALID_AUDIO")
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key, timeout=30.0)
            result = client.audio.transcriptions.create(
                model=self.model,
                file=("jarvis-voice.wav", bytes(wav_bytes), "audio/wav"),
            )
        except Exception as exc:
            raise VoiceProviderError("RECOGNITION_FAILED") from exc
        text = getattr(result, "text", None)
        if not isinstance(text, str) or not text.strip():
            raise VoiceProviderError("RECOGNITION_FAILED")
        return text.strip()
