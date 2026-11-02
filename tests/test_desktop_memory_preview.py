"""B-01b: read-only personal memory preview in the desktop Qt bridge."""
from __future__ import annotations

import json
import time
from uuid import uuid4

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QCoreApplication
from jarvis.desktop.bridge import JarvisBridge, MemoryPreviewWorker
from jarvis.memory import cognitive, connection, personal_lifecycle
from jarvis.secrets.windows import WindowsCredentialStore

MEMORY_ID = "ab89ac04-7134-49c6-9fa2-2880a296d50a"


def configure(monkeypatch, tmp_path, *, fail=False):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(connection, "configured_memory_url",
                        lambda: "https://memory.example")
    monkeypatch.setattr(WindowsCredentialStore, "get_memory_key",
                        lambda self: "NEVER-EXPOSE-THIS-KEY")
    calls = []

    class FakeClient:
        base_url = "https://memory.example"

        def __init__(self, url, key):
            assert url == self.base_url
            assert key == "NEVER-EXPOSE-THIS-KEY"

        def diagnose(self):
            calls.append("diagnose")
            return {"status": "COMPATIBLE"}

        def get(self, memory_id):
            calls.append("get")
            return {}

        def forget(self, *args, **kwargs):
            raise AssertionError("Preview must not forget")

        def supersede(self, *args, **kwargs):
            raise AssertionError("Preview must not supersede")

    def preview(self, memory_id, *, action):
        calls.append("preview")
        assert action in {"forget", "supersede"}
        if fail:
            raise RuntimeError("NEVER-EXPOSE-THIS-KEY")
        return {
            "memory_id": memory_id, "memory_type": "profile",
            "scope": "global", "lifecycle": "active",
            "content": "Para interfaces gráficas, prefiro teal.",
            "source_ref": "memory-operation:internal",
        }

    monkeypatch.setattr(cognitive, "CognitiveMemoryClient", FakeClient)
    monkeypatch.setattr(personal_lifecycle.PersonalMemoryLifecycle,
                        "preview", preview)
    return calls


def test_invalid_memory_target_never_starts_worker(monkeypatch, tmp_path):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    bridge = JarvisBridge()
    for action, target, code in (
        ("delete-all", MEMORY_ID, "invalid_action"),
        ("forget", "untrusted", "invalid_memory_id"),
        ("supersede", "", "invalid_memory_id"),
    ):
        result = json.loads(bridge.previewPersonalMemory(action, target))
        assert result == {"ok": False, "error": code}
        assert bridge.active is False


def test_preview_worker_never_mutates_and_never_logs_credentials(monkeypatch, tmp_path):
    calls = configure(monkeypatch, tmp_path)
    worker = MemoryPreviewWorker("forget", MEMORY_ID)
    results = []
    worker.finishedPreview.connect(lambda result: results.append(json.loads(result)))
    worker.run()
    assert len(results) == 1 and results[0]["ok"] is True
    assert results[0]["preview"]["memory_id"] == MEMORY_ID
    assert "source_ref" not in results[0]["preview"]
    assert "NEVER-EXPOSE-THIS-KEY" not in json.dumps(results[0])
    assert calls == ["diagnose", "preview"]


def test_preview_worker_failure_is_sanitized(monkeypatch, tmp_path):
    calls = configure(monkeypatch, tmp_path, fail=True)
    worker = MemoryPreviewWorker("supersede", MEMORY_ID)
    results = []
    worker.finishedPreview.connect(lambda result: results.append(result))
    worker.run()
    assert len(results) == 1 and "NEVER-EXPOSE-THIS-KEY" not in results[0]
    assert json.loads(results[0]) == {"ok": False, "error": "RuntimeError"}
    assert calls == ["diagnose", "preview"]


def test_read_only_preview_thread_exits_on_gui_thread(monkeypatch, tmp_path):
    app = QCoreApplication.instance() or QCoreApplication([])
    calls = configure(monkeypatch, tmp_path)
    bridge = JarvisBridge()
    events = []
    bridge.streamEvent.connect(lambda event: events.append(json.loads(event)))
    result = json.loads(bridge.previewPersonalMemory("forget", MEMORY_ID))
    assert result["ok"] is True and bridge.active
    deadline = time.monotonic() + 5.0
    try:
        while bridge.active and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(0.01)
    finally:
        if bridge._preview_thread is not None:
            bridge._preview_thread.quit()
            bridge._preview_thread.wait(3000)
            app.processEvents()
    assert not bridge.active
    assert len(events) == 1
    assert events[0]["type"] == "memory_preview"
    assert events[0]["ok"] is True
    assert calls == ["diagnose", "preview"]
    app.processEvents()
