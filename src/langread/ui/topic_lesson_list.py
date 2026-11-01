"""Topic and lesson selection (requirements §8.1, §12.1 item 1).

Topic dropdown + lesson table showing order, status, and when each lesson
was last reviewed (or "never"). Incomplete lessons offer "Finish saving"
(resume of the M7 pipeline).
"""

from __future__ import annotations

import sqlite3

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from langread.db.repositories import LessonsRepo, SentencesRepo, TopicsRepo

_LESSON_COLUMNS = ["#", "Status", "Last reviewed", "Paragraphs"]


class LessonListDialog(QDialog):
    def __init__(self, conn: sqlite3.Connection, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Review a lesson")
        self.resize(640, 480)
        self.conn = conn
        self.topics = TopicsRepo(conn)
        self.lessons = LessonsRepo(conn)
        self.sentences = SentencesRepo(conn)
        self._finalize_worker = None

        self.topic_combo = QComboBox()
        for topic in self.topics.list_all():
            self.topic_combo.addItem(topic.name, topic.id)
        self.topic_combo.currentIndexChanged.connect(self._reload_lessons)

        self.table = QTableWidget(0, len(_LESSON_COLUMNS))
        self.table.setHorizontalHeaderLabels(_LESSON_COLUMNS)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self.table.doubleClicked.connect(lambda _i: self._review_selected())
        self.table.cellClicked.connect(self._on_cell_clicked)

        self.review_button = QPushButton("Review lesson")
        self.review_button.clicked.connect(self._review_selected)
        self.finish_button = QPushButton("Finish saving")
        self.finish_button.clicked.connect(self._finish_saving)
        self.finish_button.setEnabled(False)
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.accept)

        buttons = QHBoxLayout()
        buttons.addWidget(self.review_button)
        buttons.addWidget(self.finish_button)
        buttons.addStretch(1)
        buttons.addWidget(self.close_button)

        layout = QVBoxLayout(self)
        topic_row = QHBoxLayout()
        topic_row.addWidget(QLabel("Topic:"))
        topic_row.addWidget(self.topic_combo, 1)
        layout.addLayout(topic_row)
        layout.addWidget(self.table, 1)
        layout.addLayout(buttons)

        if self.topic_combo.count() == 0:
            QMessageBox.information(
                self, "No topics",
                "There are no topics yet. Create one from the main menu first.",
            )
            return
        self._reload_lessons()

    # ---- table ----

    def _selected_lesson_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        return int(self.table.item(row, 0).data(Qt.ItemDataRole.UserRole))

    def _reload_lessons(self) -> None:
        topic_id = self.topic_combo.currentData()
        if topic_id is None:
            return
        lesson_list = self.lessons.list_for_topic(topic_id)
        self.table.setRowCount(len(lesson_list))
        for row, lesson in enumerate(lesson_list):
            number_item = QTableWidgetItem(str(lesson.order_index))
            number_item.setData(Qt.ItemDataRole.UserRole, lesson.id)
            self.table.setItem(row, 0, number_item)
            self.table.setItem(row, 1, QTableWidgetItem(lesson.status))
            self.table.setItem(
                row, 2, QTableWidgetItem(lesson.last_reviewed_at or "never reviewed")
            )
            self.table.setItem(
                row, 3,
                QTableWidgetItem(str(self.sentences.count_for_lesson(lesson.id))),
            )
        self.finish_button.setEnabled(False)
        self.review_button.setEnabled(bool(lesson_list))
        if lesson_list:
            self.table.selectRow(0)
            self._update_finish_button(lesson_list[0].status)

    def _on_cell_clicked(self, row: int, _column: int) -> None:
        lesson_id = self._selected_lesson_id()
        lesson = self.lessons.get(lesson_id) if lesson_id is not None else None
        self._update_finish_button(lesson.status if lesson else None)

    def _update_finish_button(self, status: str | None) -> None:
        self.finish_button.setEnabled(status == "incomplete")

    # ---- actions ----

    def _review_selected(self) -> None:
        lesson_id = self._selected_lesson_id()
        if lesson_id is None:
            return
        from langread.ui.review.lesson_review import LessonReviewWindow

        LessonReviewWindow(self.conn, lesson_id, parent=self).exec()
        self._reload_lessons()

    def _finish_saving(self) -> None:
        lesson_id = self._selected_lesson_id()
        if lesson_id is None:
            return
        from langread.app_config import db_path
        from langread.ui.lesson_create.generate_view import FinalizeWorker

        self.finish_button.setEnabled(False)
        self.finish_button.setText("Saving…")
        self._finalize_worker = FinalizeWorker(db_path(), lesson_id, parent=self)
        self._finalize_worker.done.connect(lambda _id: self._finalize_done())
        self._finalize_worker.failed.connect(self._finalize_failed)
        self._finalize_worker.start()

    def _finalize_done(self) -> None:
        self.finish_button.setText("Finish saving")
        self._reload_lessons()
        QMessageBox.information(self, "Lesson saved", "Saving completed.")

    def _finalize_failed(self, message: str) -> None:
        self.finish_button.setText("Finish saving")
        self.finish_button.setEnabled(True)
        QMessageBox.warning(self, "Saving failed", message)

