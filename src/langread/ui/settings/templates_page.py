"""Prompt template editor page (requirements §4.5, §7.5)."""

from __future__ import annotations

import sqlite3

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from langread.db.repositories import TemplatesRepo

# Placeholders each template may use (shown in the editor as reference).
TEMPLATE_PLACEHOLDERS: dict[str, list[str]] = {
    "segment_text": ["{text}"],
    "parse_pasted_text": ["{text}"],
    "generate_paragraph": [
        "{topic_name}", "{new_word}", "{repeat_words}", "{review_words}",
    ],
    "generate_paragraph_no_new": [
        "{topic_name}", "{repeat_words}", "{review_words}",
    ],
    "generate_sentence": [
        "{topic_name}", "{new_word}", "{repeat_words}", "{review_words}",
    ],
    "generate_final_paragraph": ["{topic_name}", "{all_new_words}"],
    "translate_word": ["{word}"],
    "translate_sentence": ["{sentence}"],
}


class TemplatesPage(QWidget):
    def __init__(self, conn: sqlite3.Connection,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.repo = TemplatesRepo(conn)
        self.repo.seed_defaults()
        self._dirty = False

        self.list_widget = QListWidget()
        self.list_widget.currentRowChanged.connect(self._on_select)

        self.editor = QPlainTextEdit()
        self.editor.setPlaceholderText("Select a template on the left to edit it.")

        self.hint = QLabel("")
        self.hint.setWordWrap(True)

        self.save_button = QPushButton("Save template")
        self.save_button.clicked.connect(self._save)
        self.reset_button = QPushButton("Restore all defaults…")
        self.reset_button.setToolTip(
            "Overwrite every template with the bundled defaults "
            "(any manual edits are lost)."
        )
        self.reset_button.clicked.connect(self._restore_defaults)

        buttons = QHBoxLayout()
        buttons.addWidget(self.reset_button)
        buttons.addStretch(1)
        buttons.addWidget(self.save_button)

        right = QVBoxLayout()
        right.addWidget(self.editor)
        right.addWidget(self.hint)
        right.addLayout(buttons)

        split = QHBoxLayout(self)
        split.addWidget(self.list_widget, 1)
        split.addLayout(right, 2)

        self._reload_list()

    def _reload_list(self) -> None:
        self.list_widget.clear()
        self.list_widget.addItems(self.repo.list_names())

    def _on_select(self, row: int) -> None:
        self._load_current()

    def _current_name(self) -> str | None:
        item = self.list_widget.currentItem()
        return item.text() if item else None

    def _load_current(self) -> None:
        name = self._current_name()
        if name is None:
            return
        template = self.repo.get(name) or ""
        self.editor.setPlainText(template)
        placeholders = TEMPLATE_PLACEHOLDERS.get(name, [])
        self.hint.setText("Available placeholders: " + "  ".join(placeholders)
                          if placeholders else "(no placeholders)")
        self._dirty = False

    def _save(self) -> None:
        name = self._current_name()
        if name is None:
            return
        self.repo.upsert(name, self.editor.toPlainText())
        self._dirty = False

    def _restore_defaults(self) -> None:
        """Overwrite all templates with the bundled defaults (confirmed)."""
        from PySide6.QtWidgets import QMessageBox

        answer = QMessageBox.question(
            self, "Restore defaults",
            "Overwrite ALL prompt templates with the bundled defaults? "
            "Any manual edits will be lost.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.repo.seed_defaults(force=True)
        self._reload_list()
