"""M0 smoke tests: app config paths and main-menu window construction."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from langread.app_config import audio_dir, backups_dir, data_dir, db_path
from langread.ui.main_menu import MainMenu


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    app = QApplication.instance() or QApplication([])
    yield app
    # keep the QApplication alive for the whole module; no teardown needed


def test_data_dir_override(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("LANGREAD_DATA_DIR", str(tmp_path / "custom"))
    d = data_dir()
    assert d == tmp_path / "custom"
    assert d.is_dir()
    assert db_path() == d / "langread.db"
    assert audio_dir() == d / "audio"
    assert backups_dir() == d / "backups"
    assert audio_dir().is_dir()
    assert backups_dir().is_dir()


def test_data_dir_default_creates_directory(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("LANGREAD_DATA_DIR", raising=False)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
    d = data_dir()
    assert d == tmp_path / "xdg" / "LangReadApp"
    assert d.is_dir()


def test_main_menu_constructs_and_lists_all_items(qapp: QApplication) -> None:
    window = MainMenu()
    assert window.windowTitle().startswith("LangRead")
    from PySide6.QtWidgets import QPushButton

    push_buttons = window.findChildren(QPushButton)
    assert len(push_buttons) == 9
    labels = [b.text() for b in push_buttons]
    assert "Manage lessons" in labels
    assert "Manage topics" in labels
    assert "Add new words" in labels
    assert "Refresh definitions" in labels
    assert "Sync with Android" in labels
    assert "Quit" in labels
    assert "Create a new lesson" not in labels  # moved into "Manage lessons"
    window.close()
