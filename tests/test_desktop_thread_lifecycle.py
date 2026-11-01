"""Actual Qt event-loop regression test for QThread.finished -> JarvisBridge slot.

Does not start WebEngine, touch credentials or contact external providers.
"""
from __future__ import annotations

import time

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QCoreApplication, QThread
from jarvis.desktop.bridge import JarvisBridge

_APP = None


def test_finished_signal_cleanup_runs_in_gui_thread(tmp_path, monkeypatch):
    global _APP
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    _APP = QCoreApplication.instance() or QCoreApplication([])
    bridge = JarvisBridge()
    thread = QThread()
    bridge._thread = thread

    events = []
    monkeypatch.setattr("jarvis.desktop.bridge.trace",
                        lambda event, **flags: events.append((event, flags)))

    thread.started.connect(thread.quit)
    thread.finished.connect(bridge._on_thread_finished)
    thread.start()
    deadline = time.monotonic() + 3.0
    while bridge._thread is not None and time.monotonic() < deadline:
        _APP.processEvents()
        time.sleep(0.01)

    assert bridge._thread is None
    assert any(name == "bridge_thread_finished" and data.get("in_gui_thread") is True
               for name, data in events)
    # Re-enter once to let Qt process the deferred deleteLater on QThread.
    _APP.processEvents()
