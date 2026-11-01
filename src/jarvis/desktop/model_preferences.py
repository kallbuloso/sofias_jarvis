"""Persist the owner's chosen OpenAI model independently of chat transcripts.

No API keys or provider credentials are stored here. The file has a
small, strict schema and is atomically replaced to avoid truncated JSON.
An explicit JARVIS_MODEL environment setting takes precedence on launch.
"""

from __future__ import annotations

import json
import os
import re
import tempfile

from jarvis.config import data_directory


_MODEL_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
_FILENAME = "desktop-preferences.json"


def valid_model_name(value: object) -> bool:
    return isinstance(value, str) and _MODEL_PATTERN.fullmatch(value) is not None


def load_preferred_model() -> str:
    """Return an optional local choice; invalid/corrupt files fail safely."""
    path = data_directory() / _FILENAME
    try:
        with path.open("r", encoding="utf-8") as file:
            raw = file.read(4097)
        if len(raw) > 4096:
            return ""
        value = json.loads(raw)
    except (OSError, UnicodeError, ValueError):
        return ""
    if not isinstance(value, dict) or set(value) != {"model"}:
        return ""
    model = value["model"]
    return model if valid_model_name(model) else ""


def bootstrap_model() -> str:
    """Environment explicitly overrides persisted local desktop preference."""
    configured = os.getenv("JARVIS_MODEL", "")
    if configured.strip():
        return configured.strip() if valid_model_name(configured.strip()) else ""
    return load_preferred_model()


def save_preferred_model(value: str) -> None:
    """Atomically remember the submitted model without touching SQLite."""
    if not valid_model_name(value):
        raise ValueError("invalid_model_name")
    target = data_directory() / _FILENAME
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        fd, temporary = tempfile.mkstemp(prefix=".jarvis-model-", suffix=".tmp",
                                        dir=target.parent)
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            json.dump({"model": value}, output, ensure_ascii=True)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, target)
    finally:
        if temporary is not None:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
