"""Desktop main menu — the eight top-level options (requirements §12.1)."""

from __future__ import annotations

import sqlite3

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from langread.app_config import db_path
from langread.db import connect

MENU_ITEMS: list[tuple[str, str, str]] = [
    ("Manage lessons", "Select a topic; review, create, edit or delete its lessons.", "lessons"),
    ("Manage topics", "Create, rename or delete topics.", "topics"),
    ("Add new words", "Add words to the new word list (paste, manual, HSK).", "words_add"),
    ("Manage word lists", "Review the new / learned / basic / HSK word lists.", "words_lists"),
    ("Model settings", "Prompt templates, model URLs, and API keys.", "settings_models"),
    ("SRS settings", "Spaced-repetition algorithm parameters.", "settings_srs"),
    ("Sync with Android", "Export / import sync bundles over USB.", "sync"),
    ("Quit", "Close LangRead.", "quit"),
]


class MainMenu(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("LangRead — Main Menu")
        self.resize(520, 480)
        self._conn: sqlite3.Connection | None = None

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(8)

        title = QLabel("LangRead")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 22px; font-weight: bold;")
        layout.addWidget(title)

        subtitle = QLabel("Chinese reading & listening — spaced repetition")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)
        layout.addSpacing(12)

        for label, tooltip, action in MENU_ITEMS:
            button = QPushButton(label)
            button.setToolTip(tooltip)
            button.clicked.connect(lambda _=False, a=action: self._on_menu(a))
            layout.addWidget(button)

        self.setCentralWidget(central)

    # ---- infrastructure ----

    def conn(self) -> sqlite3.Connection:
        """Lazily open the single app database connection."""
        if self._conn is None:
            self._conn = connect(db_path())
        return self._conn

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        if self._conn is not None:
            self._conn.close()
            self._conn = None
        super().closeEvent(event)

    # ---- menu dispatch ----

    def _on_menu(self, action: str) -> None:
        if action == "quit":
            self.close()  # last window closed → the app exits
        elif action == "lessons":
            from langread.ui.topic_lesson_list import LessonListDialog

            LessonListDialog(self.conn(), db_path=db_path(), parent=self).exec()
        elif action == "topics":
            from langread.ui.topics_manager import TopicsManagerDialog

            TopicsManagerDialog(self.conn(), parent=self).exec()
        elif action == "words_add":
            from langread.ui.words.add_words import AddWordsDialog

            AddWordsDialog(self.conn(), parent=self).exec()
        elif action == "words_lists":
            from langread.ui.words.list_manager import WordListManager

            WordListManager(self.conn(), parent=self).exec()
        elif action == "settings_models":
            self._open_settings(initial_tab=0)
        elif action == "settings_srs":
            self._open_settings(initial_tab=2)
        elif action == "sync":
            from langread.ui.sync_page import SyncPage

            SyncPage(self.conn(), db_path=db_path(), parent=self).exec()

    def _open_settings(self, initial_tab: int) -> None:
        from langread.ui.settings_dialog import SettingsDialog

        dialog = SettingsDialog(self.conn(), parent=self, initial_tab=initial_tab)
        dialog.exec()

