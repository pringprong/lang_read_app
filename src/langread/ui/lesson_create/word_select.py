"""Wizard step 1: word selection (requirements §7.2)."""

from __future__ import annotations

import sqlite3

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGroupBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from langread.db.repositories import WordsRepo
from langread.services.generation import GenerationService

MIN_NEW, MAX_NEW = 5, 10
MIN_PARAGRAPHS, MAX_PARAGRAPHS = 6, 12


class WordSelectPage(QWidget):
    def __init__(self, conn: sqlite3.Connection, topic_id: int,
                 llm=None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.repo = WordsRepo(conn)
        service = GenerationService(conn, llm)
        suggested_new, suggested_review = service.suggest_lesson_words(topic_id)

        layout = QVBoxLayout(self)

        new_group = QGroupBox("New words to introduce (5–10)")
        new_layout = QVBoxLayout(new_group)
        new_hint = QLabel("Suggestions are checked; change the selection as needed.")
        new_hint.setWordWrap(True)
        self.new_list = QListWidget()
        for word in suggested_new:
            item = QListWidgetItem(word)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.new_list.addItem(item)
        new_layout.addWidget(new_hint)
        new_layout.addWidget(self.new_list)
        layout.addWidget(new_group)

        review_group = QGroupBox("Review words (previously learned, due for review)")
        review_layout = QVBoxLayout(review_group)
        self.review_list = QListWidget()
        for word in suggested_review:
            item = QListWidgetItem(word)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if suggested_review else Qt.CheckState.Unchecked)
            if suggested_review:
                item.setCheckState(Qt.CheckState.Unchecked)
            self.review_list.addItem(item)
        review_layout.addWidget(self.review_list)
        layout.addWidget(review_group)

        para_group = QGroupBox("Lesson length")
        para_layout = QVBoxLayout(para_group)
        self.paragraph_spin = QSpinBox()
        self.paragraph_spin.setRange(MIN_PARAGRAPHS, MAX_PARAGRAPHS)
        self.paragraph_spin.setValue(8)
        para_hint = QLabel(
            "Paragraphs must exceed the number of new words — the final "
            "paragraph introduces no new words (§6.4)."
        )
        para_hint.setWordWrap(True)
        para_layout.addWidget(self.paragraph_spin)
        para_layout.addWidget(para_hint)
        layout.addWidget(para_group)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: red;")
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)

    def checked(self, list_widget: QListWidget) -> list[str]:
        return [
            list_widget.item(row).text()
            for row in range(list_widget.count())
            if list_widget.item(row).checkState() == Qt.CheckState.Checked
        ]

    def selected_new(self) -> list[str]:
        return self.checked(self.new_list)

    def selected_review(self) -> list[str]:
        return self.checked(self.review_list)

    def paragraph_count(self) -> int:
        return self.paragraph_spin.value()

    def validation_error(self) -> str | None:
        new = self.selected_new()
        if not MIN_NEW <= len(new) <= MAX_NEW:
            return f"Select between {MIN_NEW} and {MAX_NEW} new words (currently {len(new)})."
        if self.paragraph_count() <= len(new):
            return (
                f"{len(new)} new words need more than {len(new)} paragraphs "
                f"(currently {self.paragraph_count()})."
            )
        return None
