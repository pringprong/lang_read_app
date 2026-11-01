"""Desktop main menu — the eight top-level options (requirements §12.1)."""

from __future__ import annotations

import sqlite3

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from langread.app_config import db_path
from langread.db import connect

MENU_ITEMS: list[tuple[str, str, int]] = [
    ("Review a lesson", "Select a topic and review a lesson in that topic.", 0),
    ("Create a new topic", "Create a new topic and start a new chain of lessons.", 1),
    ("Create a new lesson", "Create a new lesson in an existing topic.", 2),
    ("Add new words", "Add words to the new word list (paste, manual, HSK).", 3),
    ("Manage word lists", "Review the new / learned / basic / HSK word lists.", 4),
    ("Model settings", "Prompt templates, model URLs, and API keys.", 5),
    ("SRS settings", "Spaced-repetition algorithm parameters.", 6),
    ("Sync with Android", "Export / import sync bundles over USB.", 7),
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

        for label, tooltip, index in MENU_ITEMS:
            button = QPushButton(label)
            button.setToolTip(tooltip)
            button.clicked.connect(lambda _=False, i=index: self._on_menu(i))
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

    def _on_menu(self, index: int) -> None:
        if index == 5:
            self._open_settings(initial_tab=0)
        elif index == 6:
            self._open_settings(initial_tab=2)
        elif index == 3:
            from langread.ui.words.add_words import AddWordsDialog

            AddWordsDialog(self.conn(), parent=self).exec()
        elif index == 4:
            from langread.ui.words.list_manager import WordListManager

            WordListManager(self.conn(), parent=self).exec()
        elif index == 1:
            self._create_topic()
        elif index == 2:
            self._create_lesson()
        else:
            self._not_implemented()

    # ---- topic / lesson creation (§7.1) ----

    def _create_topic(self) -> None:
        import sqlite3

        from PySide6.QtWidgets import QInputDialog

        from langread.db.repositories import TopicsRepo

        name, ok = QInputDialog.getText(self, "New topic", "Topic name:")
        if not ok or not name.strip():
            return
        try:
            topic = TopicsRepo(self.conn()).create(name.strip())
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "Duplicate topic", "That topic already exists.")
            return
        QMessageBox.information(
            self, "Topic created",
            f"Topic “{topic.name}” created. You can now create lessons in it.",
        )

    def _create_lesson(self) -> None:
        from PySide6.QtWidgets import QInputDialog

        from langread.db.repositories import TopicsRepo
        from langread.ui.lesson_create.wizard import LessonWizard

        topics = TopicsRepo(self.conn()).list_all()
        if not topics:
            QMessageBox.information(
                self, "No topics",
                "Create a topic first (menu option “Create a new topic”).",
            )
            return
        names = [t.name for t in topics]
        name, ok = QInputDialog.getItem(
            self, "Create a new lesson", "Topic:", names, 0, False
        )
        if not ok:
            return
        topic = TopicsRepo(self.conn()).get_by_name(name)
        if topic is None:
            return
        llm = self._generation_llm()
        wizard = LessonWizard(self.conn(), topic.id, topic.name, llm=llm,
                              db_path=db_path(), parent=self)
        wizard.exec()

    def _generation_llm(self):
        from langread.db.repositories import SettingsRepo
        from langread.services.llm_client import LlmClient
        from langread.services.model_settings import (
            ModelSettings,
            ModelSettingsError,
        )

        try:
            return LlmClient(ModelSettings(SettingsRepo(self.conn())).llm_config("gen"))
        except ModelSettingsError:
            return None  # wizard/generation reports the missing configuration

    def _open_settings(self, initial_tab: int) -> None:
        from langread.ui.settings_dialog import SettingsDialog

        dialog = SettingsDialog(self.conn(), parent=self, initial_tab=initial_tab)
        dialog.exec()

    def _not_implemented(self) -> None:
        QMessageBox.information(
            self,
            "Not implemented yet",
            "This feature is not implemented yet. See the milestone plan "
            "(20261101_desktop_app_plan.md).",
        )

