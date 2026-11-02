from pathlib import Path


def test_local_tts_renders_canonical_text_and_has_explicit_stop():
    source = Path("src/jarvis/voice/tts.py").read_text(encoding="utf-8")
    assert "QTextToSpeech" in source
    assert "self._speech.say(text.strip())" in source
    assert "self._speech.stop(QTextToSpeech.BoundaryHint.Immediate)" in source
    assert "pt_br" in source.lower()


def test_voice_reply_tts_uses_persisted_assistant_message_not_second_inference():
    bridge = Path("src/jarvis/desktop/bridge.py").read_text(encoding="utf-8")
    assert "self._voice_reply_conversation" in bridge
    assert "self._store.list_messages(conversation_id)" in bridge
    assert "self._pending_speech = (conversation_id, spoken.strip())" in bridge
    assert "self._speech.say(text)" in bridge


def test_stop_speech_does_not_cancel_conversation_or_task():
    bridge = Path("src/jarvis/desktop/bridge.py").read_text(encoding="utf-8")
    start = bridge.index("def stopSpeech")
    end = bridge.index("@Slot(str, str, str, result=str)", start)
    block = bridge[start:end]
    assert "self._speech.stop()" in block
    assert "cancelled.set()" not in block
    assert "_mutation_gate.clear()" not in block


def test_desktop_exposes_stop_voice_only_while_speaking():
    source = Path("frontend/src/App.vue").read_text(encoding="utf-8")
    assert "voiceState === 'SPEAKING' ? 'Parar voz' : 'Falar'" in source
    assert "@click=\"stopSpeech\"" in source
