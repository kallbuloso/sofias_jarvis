"""Persist non-secret desktop AI provider/connection/model selection."""
from __future__ import annotations

import json
import os
import re
import tempfile
from uuid import UUID

from jarvis.config import data_directory


_PROVIDER_PATTERN = re.compile(r"^[a-z][a-z0-9._-]{0,63}$")
_MODEL_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
_FILENAME = "desktop-ai-selection.json"


def _valid_provider(value: object) -> bool:
    return isinstance(value, str) and _PROVIDER_PATTERN.fullmatch(value) is not None


def _valid_model(value: object) -> bool:
    return isinstance(value, str) and _MODEL_PATTERN.fullmatch(value) is not None


def _valid_connection(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        return str(UUID(value)) == value
    except (ValueError, TypeError, AttributeError):
        return False


def load_ai_selection() -> dict | None:
    path = data_directory() / _FILENAME
    try:
        with path.open("r", encoding="utf-8") as file:
            raw = file.read(8193)
        if len(raw) > 8192:
            return None
        value = json.loads(raw)
    except (OSError, UnicodeError, ValueError):
        return None
    if not isinstance(value, dict) or set(value) != {
        "provider_id", "connection_id", "models",
    }:
        return None
    if not _valid_provider(value["provider_id"]):
        return None
    if not _valid_connection(value["connection_id"]):
        return None
    models = value["models"]
    if (not isinstance(models, dict)
            or not models
            or not all(_valid_provider(k) and _valid_model(v)
                       for k, v in models.items())):
        return None
    if value["provider_id"] not in models:
        return None
    return {
        "provider_id": value["provider_id"],
        "connection_id": value["connection_id"],
        "models": dict(models),
    }


def save_ai_selection(
    provider_id: str, connection_id: str, model: str,
) -> dict:
    if not _valid_provider(provider_id):
        raise ValueError("invalid_provider_id")
    if not _valid_connection(connection_id):
        raise ValueError("invalid_connection_id")
    if not _valid_model(model):
        raise ValueError("invalid_model_name")

    current = load_ai_selection()
    models = dict(current["models"]) if current else {}
    models[provider_id] = model
    value = {
        "provider_id": provider_id,
        "connection_id": connection_id,
        "models": models,
    }

    target = data_directory() / _FILENAME
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        fd, temporary = tempfile.mkstemp(
            prefix=".jarvis-ai-", suffix=".tmp", dir=target.parent,
        )
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            json.dump(value, output, ensure_ascii=True, sort_keys=True)
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
    return value
