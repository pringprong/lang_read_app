"""Lesson management window (main menu → "Manage lessons").

Topic dropdown + lesson table showing order, status, when each lesson was
last reviewed (or "never"), and how many times it was reviewed. Actions:

- Review lesson (double-click works too)
- New lesson: the creation wizard for the selected topic (§7.1–7.8)
- Edit lesson text: hand-edit paragraphs / segmentation of a saved lesson
- Delete lesson: only the last lesson of the topic (its new words go back
  to the New list, text and audio are removed)
- Finish saving: resume the M7 save pipeline of an incomplete lesson
- Regenerate audio: for the selected lesson or for every lesson
"""

from __future__ import annotations

import sqlite3

from PySide6.QtCore import Qt, QThread, Signal
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

from langread.db import connect
from langread.db.repositories import LessonsRepo, SentencesRepo, TopicsRepo

_LESSON_COLUMNS = ["#", "Status", "Last reviewed", "Times reviewed"]


class RegenerateAudioWorker(QThread):
    """Re-synthesizes audio for one or more lessons in a background thread.

    Per-lesson failures don't abort the batch; they are collected and
    reported together at the end.
    """

    progress = Signal(int, int, int)          # lesson_id, current, total
    finished_batch = Signal(object, object)   # ok_ids, [(lesson_id, error)]

    def __init__(self, db_path, lesson_ids: list[int], parent=None) -> None:
        super().__init__(parent)
        self._db_path = db_path
        self._lesson_ids = lesson_ids

    def run(self) -> None:
        from langread.db.repositories import SettingsRepo
        from langread.services.lesson_saver import LessonSaver
        from langread.services.model_settings import ModelSettings
        from langread.services.tts import TtsService

        ok: list[int] = []
        failed: list[tuple[int, str]] = []
        conn = connect(self._db_path)
        try:
            tts = TtsService(ModelSettings(SettingsRepo(conn)).tts_config())
            saver = LessonSaver(conn, tts=tts)
            total = len(self._lesson_ids)
            for index, lesson_id in enumerate(self._lesson_ids):
                self.progress.emit(lesson_id, index + 1, total)
                try:
                    saver.regenerate_audio(lesson_id)
                    ok.append(lesson_id)
                except Exception as exc:  # noqa: BLE001 - batch continues
                    failed.append((lesson_id, str(exc)))
        finally:
            conn.close()
        self.finished_batch.emit(ok, failed)


class LessonListDialog(QDialog):
    def __init__(self, conn: sqlite3.Connection, db_path=None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Manage lessons")
        self.resize(680, 520)
        self.conn = conn
        self._db_path = db_path
        if db_path is None:
            from langread.app_config import db_path as default_db_path

            self._db_path = default_db_path()
        self.topics = TopicsRepo(conn)
        self.lessons = LessonsRepo(conn)
        self.sentences = SentencesRepo(conn)
        self._finalize_worker = None
        self._regenerate_worker = None

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
        self.table.itemSelectionChanged.connect(self._on_selection_changed)

        self.review_button = QPushButton("Review lesson")
        self.review_button.clicked.connect(self._review_selected)
        self.new_lesson_button = QPushButton("New lesson…")
        self.new_lesson_button.setToolTip(
            "Create a new lesson in the selected topic (creation wizard)"
        )
        self.new_lesson_button.clicked.connect(self._new_lesson)
        self.edit_button = QPushButton("Edit lesson text…")
        self.edit_button.setToolTip("Hand-edit the text of the selected lesson")
        self.edit_button.clicked.connect(self._edit_selected)
        self.edit_button.setEnabled(False)
        self.delete_button = QPushButton("Delete lesson…")
        self.delete_button.setToolTip(
            "Delete the LAST lesson of the topic; its new words return to the "
            "New word list"
        )
        self.delete_button.setEnabled(False)
        self.delete_button.clicked.connect(self._delete_selected)
        self.finish_button = QPushButton("Finish saving")
        self.finish_button.clicked.connect(self._finish_saving)
        self.finish_button.setEnabled(False)
        self.regenerate_button = QPushButton("Regenerate audio")
        self.regenerate_button.setToolTip(
            "Re-synthesize this lesson's audio (e.g. after changing TTS "
            "settings or the Latin voice)"
        )
        self.regenerate_button.clicked.connect(self._regenerate_selected)
        self.regenerate_button.setEnabled(False)
        self.regenerate_all_button = QPushButton("Regenerate ALL audio…")
        self.regenerate_all_button.setToolTip(
            "Re-synthesize the audio of every lesson in the app"
        )
        self.regenerate_all_button.clicked.connect(self._regenerate_all)
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.accept)

        self.status_label = QLabel("")

        lesson_buttons = QHBoxLayout()
        lesson_buttons.addWidget(self.review_button)
        lesson_buttons.addWidget(self.new_lesson_button)
        lesson_buttons.addWidget(self.edit_button)
        lesson_buttons.addWidget(self.delete_button)
        lesson_buttons.addWidget(self.finish_button)

        audio_buttons = QHBoxLayout()
        audio_buttons.addWidget(self.regenerate_button)
        audio_buttons.addWidget(self.regenerate_all_button)
        audio_buttons.addStretch(1)
        audio_buttons.addWidget(self.close_button)

        layout = QVBoxLayout(self)
        topic_row = QHBoxLayout()
        topic_row.addWidget(QLabel("Topic:"))
        topic_row.addWidget(self.topic_combo, 1)
        layout.addLayout(topic_row)
        layout.addWidget(self.table, 1)
        layout.addLayout(lesson_buttons)
        layout.addLayout(audio_buttons)
        layout.addWidget(self.status_label)

        if self.topic_combo.count() == 0:
            QMessageBox.information(
                self, "No topics",
                "There are no topics yet. Create one via “Manage topics” "
                "in the main menu first.",
            )
            return
        self._reload_lessons()

    # ---- table ----

    def _selected_lesson_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return int(item.data(Qt.ItemDataRole.UserRole)) if item is not None else None

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
                row, 3, QTableWidgetItem(str(lesson.review_count))
            )
        self.finish_button.setEnabled(False)
        self.review_button.setEnabled(bool(lesson_list))
        if lesson_list:
            self.table.selectRow(0)
            self._update_lesson_buttons(lesson_list[0].status)
        else:
            self._update_lesson_buttons(None)

    def _on_selection_changed(self) -> None:
        lesson_id = self._selected_lesson_id()
        lesson = self.lessons.get(lesson_id) if lesson_id is not None else None
        self._update_lesson_buttons(lesson.status if lesson else None)

    def _update_lesson_buttons(self, status: str | None) -> None:
        """Enable state of all per-lesson buttons for the current selection."""
        self._update_finish_button(status)
        lesson_id = self._selected_lesson_id()
        has_lesson = lesson_id is not None
        self.edit_button.setEnabled(has_lesson)
        self.regenerate_button.setEnabled(
            has_lesson
            and bool(self.sentences.list_for_lesson(lesson_id))
        )
        # delete: only the last lesson of the topic (the table is sorted by
        # order, so the last row is the last lesson)
        self.delete_button.setEnabled(
            has_lesson and self.table.currentRow() == self.table.rowCount() - 1
        )

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

    def _new_lesson(self) -> None:
        """Open the lesson-creation wizard for the selected topic (§7.1)."""
        topic_id = self.topic_combo.currentData()
        topic = self.topics.get(topic_id) if topic_id is not None else None
        if topic is None:
            return
        from langread.services.model_settings import generation_llm
        from langread.ui.lesson_create.wizard import LessonWizard

        wizard = LessonWizard(self.conn, topic.id, topic.name,
                              llm=generation_llm(self.conn),
                              db_path=self._db_path, parent=self)
        wizard.exec()
        self._reload_lessons()

    def _edit_selected(self) -> None:
        lesson_id = self._selected_lesson_id()
        if lesson_id is None:
            return
        from langread.ui.lesson_create.edit_lesson import EditLessonTextDialog

        dialog = EditLessonTextDialog(self.conn, lesson_id, parent=self)
        dialog.exec()
        self._reload_lessons()

    def _delete_selected(self) -> None:
        """Delete the last lesson of the topic; new words go back to New."""
        lesson_id = self._selected_lesson_id()
        if lesson_id is None:
            return
        lesson = self.lessons.get(lesson_id)
        if lesson is None:
            return
        topic = self.topics.get(lesson.topic_id)
        topic_name = topic.name if topic else ""
        answer = QMessageBox.question(
            self, "Delete lesson",
            f"Delete lesson {lesson.order_index}"
            + (f" of “{topic_name}”" if topic_name else "")
            + "?\n\nIts new words will return to the New word list, and its "
            "text and audio will be deleted. This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        from langread.services.lesson_saver import LessonSaver

        try:
            demoted = LessonSaver(self.conn).delete_lesson(lesson_id)
        except Exception as exc:  # noqa: BLE001 - report and keep the dialog
            QMessageBox.warning(self, "Delete failed", str(exc))
            return
        message = "Lesson deleted."
        if demoted:
            message += f"\n{len(demoted)} word(s) moved back to the New list:\n" \
                       + ", ".join(demoted)
        QMessageBox.information(self, "Lesson deleted", message)
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

    # ---- audio regeneration ----

    def _regenerate_selected(self) -> None:
        lesson_id = self._selected_lesson_id()
        if lesson_id is None:
            return
        self._start_regeneration([lesson_id])

    def _regenerate_all(self) -> None:
        lesson_ids = [lesson.id for lesson in self.lessons.list_all()]
        if not lesson_ids:
            return
        answer = QMessageBox.question(
            self, "Regenerate all audio",
            f"Re-synthesize the audio of all {len(lesson_ids)} lesson(s)? "
            "This re-runs text-to-speech for every paragraph and may take "
            "a while.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._start_regeneration(lesson_ids)

    def _start_regeneration(self, lesson_ids: list[int]) -> None:
        self.regenerate_button.setEnabled(False)
        self.regenerate_all_button.setEnabled(False)
        self.regenerate_all_button.setText("Regenerating…")
        self._regenerate_worker = RegenerateAudioWorker(
            self._db_path, lesson_ids, parent=self
        )
        self._regenerate_worker.progress.connect(self._on_regenerate_progress)
        self._regenerate_worker.finished_batch.connect(self._on_regenerate_done)
        self._regenerate_worker.start()

    def _on_regenerate_progress(self, lesson_id: int, current: int, total: int) -> None:
        self.status_label.setText(
            f"Regenerating audio — lesson {lesson_id} ({current}/{total})"
        )

    def _on_regenerate_done(self, ok_ids, failures) -> None:
        self.regenerate_all_button.setText("Regenerate ALL audio…")
        self.regenerate_all_button.setEnabled(True)
        self._on_selection_changed()  # refresh enabled state
        self._reload_lessons()
        if failures:
            details = "\n".join(f"lesson {lid}: {err}" for lid, err in failures)
            QMessageBox.warning(
                self, "Audio regeneration",
                f"Finished with {len(ok_ids)} success(es) and "
                f"{len(failures)} failure(s):\n{details}",
            )
            self.status_label.setText(
                f"⚠ {len(ok_ids)} regenerated, {len(failures)} failed"
            )
        else:
            self.status_label.setText(f"✅ Audio regenerated ({len(ok_ids)} lesson(s)).")

    def wait_for_regenerate_worker(self) -> None:
        """Used by tests: block until the regeneration worker finishes."""
        if self._regenerate_worker is not None:
            self._regenerate_worker.wait()

