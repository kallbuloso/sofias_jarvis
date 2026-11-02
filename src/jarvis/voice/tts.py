"""Local text-to-speech output for the Windows desktop.

The canonical assistant response remains text in Conversation History.
This adapter only renders that text through the host OS speech engine.
"""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtTextToSpeech import QTextToSpeech


class LocalSpeechOutput(QObject):
    stateChanged = Signal(str)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._speech = QTextToSpeech(self)
        self._speech.stateChanged.connect(self._on_state)
        try:
            locales = list(self._speech.availableLocales())
            preferred = next(
                (locale for locale in locales if locale.name().lower() == "pt_br"),
                None,
            )
            if preferred is None:
                preferred = next(
                    (locale for locale in locales
                     if locale.name().lower().startswith("pt_")),
                    None,
                )
            if preferred is not None:
                self._speech.setLocale(preferred)
        except Exception:
            pass

    @property
    def available(self) -> bool:
        try:
            return bool(QTextToSpeech.availableEngines()) and (
                self._speech.state() != QTextToSpeech.State.Error
            )
        except Exception:
            return False

    @property
    def speaking(self) -> bool:
        return self._speech.state() in {
            QTextToSpeech.State.Speaking,
            QTextToSpeech.State.Paused,
        }

    def say(self, text: str) -> bool:
        if not isinstance(text, str) or not text.strip() or not self.available:
            return False
        self._speech.say(text.strip())
        return True

    def stop(self) -> None:
        if self.speaking:
            self._speech.stop(QTextToSpeech.BoundaryHint.Immediate)

    def _on_state(self, state) -> None:
        mapping = {
            QTextToSpeech.State.Ready: "IDLE",
            QTextToSpeech.State.Speaking: "SPEAKING",
            QTextToSpeech.State.Paused: "PAUSED",
            QTextToSpeech.State.Error: "ERROR",
        }
        self.stateChanged.emit(mapping.get(state, "ERROR"))
