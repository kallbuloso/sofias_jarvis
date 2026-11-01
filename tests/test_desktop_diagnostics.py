"""TB-02 native abort diagnostics: no prompts, secrets or network data."""
from __future__ import annotations

import json
from pathlib import Path

from jarvis.desktop import diagnostics


def test_lifecycle_trace_is_off_by_default(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("JARVIS_DESKTOP_DIAGNOSTICS", raising=False)
    diagnostics.trace("window_construct_begin")
    assert not (tmp_path / "desktop-lifecycle.jsonl").exists()


def test_opted_in_trace_records_only_small_static_fields(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("JARVIS_DESKTOP_DIAGNOSTICS", "1")
    diagnostics.trace("bridge_worker_done_received", result="completed",
                      worker_active=False)
    lines = (tmp_path / "desktop-lifecycle.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    item = json.loads(lines[0])
    assert item["event"] == "bridge_worker_done_received"
    assert item["worker_active"] is False
    assert item["result"] == "completed"
    assert item["thread"] > 0 and item["pid"] > 0


def test_trace_drops_complex_objects_and_does_not_depend_on_network(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("JARVIS_DESKTOP_DIAGNOSTICS", "1")
    diagnostics.trace("window_close_requested", payload={"prompt": "private"},
                      suspicious_field=[1, 2], worker_active=True)
    data = json.loads((tmp_path / "desktop-lifecycle.jsonl").read_text(encoding="utf-8"))
    assert data["worker_active"] is True
    assert "payload" not in data
    assert "suspicious_field" not in data
    assert "private" not in json.dumps(data)
