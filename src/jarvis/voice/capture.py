"""Ephemeral push-to-talk capture for the Windows desktop.

Audio remains in memory and is converted to PCM WAV only after capture stops.
No raw audio file is written by this module.
"""
from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import wave

from PySide6.QtCore import QBuffer, QIODevice, QObject
from PySide6.QtMultimedia import QAudioFormat, QAudioSource, QMediaDevices


class VoiceCaptureError(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class CapturedTurn:
    conversation_id: str
    wav_bytes: bytes
    sample_rate: int
    duration_ms: int


def pcm16_wav(raw: bytes, *, sample_rate: int, channels: int = 1) -> bytes:
    if not raw:
        raise VoiceCaptureError("EMPTY_AUDIO")
    if sample_rate < 8000 or sample_rate > 192000 or channels != 1:
        raise VoiceCaptureError("UNSUPPORTED_AUDIO_FORMAT")
    target = BytesIO()
    with wave.open(target, "wb") as out:
        out.setnchannels(channels)
        out.setsampwidth(2)
        out.setframerate(sample_rate)
        out.writeframes(raw)
    return target.getvalue()


class QtPushToTalkCapture(QObject):
    """One local microphone turn bound to the Conversation that started it."""

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._source: QAudioSource | None = None
        self._buffer: QBuffer | None = None
        self._conversation_id: str | None = None
        self._sample_rate = 0

    @property
    def active(self) -> bool:
        return self._source is not None

    @property
    def conversation_id(self) -> str | None:
        return self._conversation_id

    @staticmethod
    def _format_for(device) -> QAudioFormat:
        for rate in (16000, 24000, 48000, 44100):
            fmt = QAudioFormat()
            fmt.setSampleRate(rate)
            fmt.setChannelCount(1)
            fmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)
            if device.isFormatSupported(fmt):
                return fmt
        raise VoiceCaptureError("UNSUPPORTED_AUDIO_FORMAT")

    def start(self, conversation_id: str) -> None:
        if self.active:
            raise VoiceCaptureError("CAPTURE_ALREADY_ACTIVE")
        device = QMediaDevices.defaultAudioInput()
        if device.isNull():
            raise VoiceCaptureError("INPUT_DEVICE_UNAVAILABLE")
        fmt = self._format_for(device)
        buffer = QBuffer(self)
        if not buffer.open(QIODevice.OpenModeFlag.WriteOnly):
            raise VoiceCaptureError("CAPTURE_BUFFER_FAILED")
        source = QAudioSource(device, fmt, self)
        source.start(buffer)
        self._conversation_id = conversation_id
        self._sample_rate = fmt.sampleRate()
        self._buffer = buffer
        self._source = source

    def stop(self) -> CapturedTurn:
        if not self.active or self._buffer is None or self._conversation_id is None:
            raise VoiceCaptureError("CAPTURE_NOT_ACTIVE")
        source = self._source
        buffer = self._buffer
        conversation_id = self._conversation_id
        sample_rate = self._sample_rate
        duration_ms = max(0, int(source.processedUSecs() / 1000))
        source.stop()
        buffer.close()
        raw = bytes(buffer.data())
        self._source = None
        self._buffer = None
        self._conversation_id = None
        self._sample_rate = 0
        source.deleteLater()
        buffer.deleteLater()
        return CapturedTurn(
            conversation_id=conversation_id,
            wav_bytes=pcm16_wav(raw, sample_rate=sample_rate),
            sample_rate=sample_rate,
            duration_ms=duration_ms,
        )

    def cancel(self) -> None:
        """Stop and discard an in-progress turn; never materialize a transcript."""
        source, buffer = self._source, self._buffer
        self._source = None
        self._buffer = None
        self._conversation_id = None
        self._sample_rate = 0
        if source is not None:
            source.stop()
            source.deleteLater()
        if buffer is not None:
            buffer.close()
            buffer.deleteLater()
