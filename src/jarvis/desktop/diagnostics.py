"""Opt-in crash diagnostics for the desktop's Qt event lifecycle.

Only static event identifiers, state flags and numeric status codes are written.
Never log prompts, response text, document excerpts, URLs or API credentials.
Diagnostics are disabled by default and cannot affect normal data contracts.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import threading

from jarvis.config import data_directory

_LOCK = threading.Lock()
_QT_HANDLER = None
_MARKERS = (
    "QThread: Destroyed while thread is still running",
    "QDxgiVSyncService not destroyed in time",
    "QWebEngine",
    "GPU process",
)


def diagnostics_enabled() -> bool:
    return os.environ.get("JARVIS_DESKTOP_DIAGNOSTICS") == "1"


def diagnostic_path() -> Path:
    return data_directory() / "desktop-lifecycle.jsonl"


def trace(event: str, **flags: str | int | bool | None) -> None:
    """Synchronous small diagnostic record, safe even just before native abort."""
    if not diagnostics_enabled():
        return
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "pid": os.getpid(),
        "thread": threading.get_ident(),
    }
    # Fail closed on unexpected fields; never serialize arbitrary objects.
    for name, value in flags.items():
        if (isinstance(name, str) and name.isidentifier()
                and (value is None or type(value) in (str, int, bool))):
            record[name] = value[:80] if isinstance(value, str) else value
    try:
        path = diagnostic_path()
        with _LOCK:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as file:
                file.write(json.dumps(record, ensure_ascii=False) + "\n")
                file.flush()
                os.fsync(file.fileno())
    except OSError:
        # Diagnostics must never break normal or protected operations.
        pass


def install_qt_diagnostics() -> None:
    """Record Qt severities and known lifecycle markers, not raw messages."""
    global _QT_HANDLER
    if not diagnostics_enabled() or _QT_HANDLER is not None:
        return
    from PySide6.QtCore import qInstallMessageHandler

    def handler(level, context, message):
        try:
            severity = str(getattr(level, "name", level))
            markers = [name for name in _MARKERS if name in message]
            # No raw Qt text: it can contain paths or application data.
            if markers or "Fatal" in severity or "Critical" in severity:
                trace(
                    "qt_message",
                    severity=severity,
                    marker=";".join(markers)[:80] or "OTHER",
                )
        except Exception:
            pass

    _QT_HANDLER = handler  # Strong reference until the process terminates.
    qInstallMessageHandler(handler)
