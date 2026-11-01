"""Application paths and resource loading.

All runtime data (SQLite database, MP3 audio, backups) lives in a per-OS user
data directory. Tests can redirect everything with the LANGREAD_DATA_DIR
environment variable.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "LangReadApp"
ENV_DATA_DIR = "LANGREAD_DATA_DIR"


def data_dir() -> Path:
    """Return (and create) the application data directory."""
    override = os.environ.get(ENV_DATA_DIR)
    if override:
        path = Path(override)
    elif sys.platform == "win32":
        base = Path(os.environ["LOCALAPPDATA"])
        path = base / APP_NAME
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
        path = base / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def db_path() -> Path:
    return data_dir() / "langread.db"


def audio_dir() -> Path:
    path = data_dir() / "audio"
    path.mkdir(parents=True, exist_ok=True)
    return path


def backups_dir() -> Path:
    path = data_dir() / "backups"
    path.mkdir(parents=True, exist_ok=True)
    return path


def resource_dir() -> Path:
    """Bundled read-only resources (HSK data, default prompt templates)."""
    return Path(__file__).parent / "resources"
