"""Runtime paths. Never store provider credentials in application settings."""

from __future__ import annotations

import os
from pathlib import Path


def data_directory() -> Path:
    """Application-owned storage, separate from source and provider databases."""
    override = os.getenv("JARVIS_DATA_DIR")
    if override:
        return Path(override).expanduser().resolve()

    if os.name == "nt":
        root = os.getenv("LOCALAPPDATA")
        if root:
            return Path(root) / "JARVIS"
        return Path.home() / "AppData" / "Local" / "JARVIS"

    root = os.getenv("XDG_DATA_HOME")
    return Path(root).expanduser() / "jarvis" if root else Path.home() / ".local" / "share" / "jarvis"


def database_path() -> Path:
    return data_directory() / "jarvis.sqlite3"
