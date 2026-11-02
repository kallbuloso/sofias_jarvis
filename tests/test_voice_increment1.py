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
    assert "@pointerdown.prevent=" in source and "startVoice($event)" in source
    assert "@pointerup.prevent=" in source and "stopVoice($event)" in source
    assert "call('startVoiceCapture'" in source
    assert "call('stopVoiceCapture'" in source

    bridge = Path("src/jarvis/desktop/bridge.py").read_text(encoding="utf-8")
    assert '"type": "voice_transcript"' in bridge
    assert "self.sendConversationalMessage(conversation_id, text.strip(), model)" in bridge

def test_voice_stt_start_is_deferred_past_audio_teardown():
    bridge = Path("src/jarvis/desktop/bridge.py").read_text(encoding="utf-8")
    assert "QTimer.singleShot(0, self._start_voice_transcription_thread)" in bridge
    assert "voice_capture_stop_end" in bridge
    assert "voice_transcription_thread_scheduled" in bridge


def test_desktop_diagnostics_can_capture_native_faults():
    diagnostics = Path("src/jarvis/desktop/diagnostics.py").read_text(
        encoding="utf-8"
    )
    assert "faulthandler.enable" in diagnostics
    assert "desktop-faulthandler.log" in diagnostics

