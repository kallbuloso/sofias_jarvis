from __future__ import annotations

from io import BytesIO
from pathlib import Path
import sys
from types import SimpleNamespace
import wave

import pytest

pytest.importorskip("PySide6")

from jarvis.voice.capture import VoiceCaptureError, pcm16_wav
from jarvis.voice.openai_adapter import OpenAITranscriptionAdapter


def test_pcm16_capture_is_wrapped_as_ephemeral_mono_wav():
    raw = (b"\x01\x00\xff\xff") * 160
    payload = pcm16_wav(raw, sample_rate=16000)
    with wave.open(BytesIO(payload), "rb") as source:
        assert source.getnchannels() == 1
        assert source.getsampwidth() == 2
        assert source.getframerate() == 16000
        assert source.readframes(source.getnframes()) == raw


def test_empty_audio_never_becomes_a_transcriptable_turn():
    with pytest.raises(VoiceCaptureError, match="EMPTY_AUDIO"):
        pcm16_wav(b"", sample_rate=16000)


def test_openai_stt_adapter_returns_only_nonempty_final_text(monkeypatch):
    calls = []

    class Transcriptions:
        def create(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(text="  Confirmo.  ")

    fake_client = SimpleNamespace(
        audio=SimpleNamespace(transcriptions=Transcriptions())
    )
    monkeypatch.setitem(
        sys.modules, "openai",
        SimpleNamespace(OpenAI=lambda **kwargs: fake_client),
    )
    adapter = OpenAITranscriptionAdapter("PRIVATE", model="stt-test")
    assert adapter.transcribe(b"RIFF" + b"\x00" * 60) == "Confirmo."
    assert calls[0]["model"] == "stt-test"
    assert calls[0]["file"][0] == "jarvis-voice.wav"
    assert calls[0]["file"][2] == "audio/wav"


def test_desktop_push_to_talk_contract_uses_press_release_and_canonical_bridge():
    source = Path("frontend/src/App.vue").read_text(encoding="utf-8")
    assert "@pointerdown.prevent=\"startVoice\"" in source
    assert "@pointerup.prevent=\"stopVoice\"" in source
    assert "call('startVoiceCapture'" in source
    assert "call('stopVoiceCapture'" in source

    bridge = Path("src/jarvis/desktop/bridge.py").read_text(encoding="utf-8")
    assert '"type": "voice_transcript"' in bridge
    assert "self.sendConversationalMessage(conversation_id, text.strip(), model)" in bridge
