"""Lesson creation wizard (requirements §7.1–7.8): 3 steps in one dialog.

Step 1 word selection → step 2 background generation → step 3 hand-edit.
"Regenerate all" returns to step 1 (§7.8); "Approve & save" hands the draft
to the save pipeline (M7).
"""

from __future__ import annotations

import sqlite3

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
)

from langread.services.generation import LessonDraft
from langread.services.segmentation import SegmentationService
from langread.ui.lesson_create.final_edit import FinalEditPage
from langread.ui.lesson_create.generate_view import GeneratePage
from langread.ui.lesson_create.word_select import WordSelectPage


class LessonWizard(QDialog):
    def __init__(self, conn: sqlite3.Connection, topic_id: int, topic_name: str,
                 llm=None, db_path=None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Create a new lesson — {topic_name}")
        self.resize(860, 620)
        self.conn = conn
        self._llm = llm
        self._draft: LessonDraft | None = None
        if db_path is None:
            from langread.app_config import db_path as default_db_path

            db_path = default_db_path()
        self._db_path = db_path

        self.stack = QStackedWidget()
        self.word_page = WordSelectPage(conn, topic_id, llm)
        self.generate_page = GeneratePage(db_path, topic_id, llm)
        self.final_page = FinalEditPage(conn)
        self.stack.addWidget(self.word_page)     # 0
        self.stack.addWidget(self.generate_page)  # 1
        self.stack.addWidget(self.final_page)    # 2

        self.step_label = QLabel("Step 1 of 3 — word selection")
        self.back_button = QPushButton("Back")
        self.back_button.clicked.connect(self._go_back)
        self.back_button.setVisible(False)
        self.next_button = QPushButton("Generate lesson")
        self.next_button.clicked.connect(self._go_next)
        self.approve_button = QPushButton("Approve && save")
        self.approve_button.clicked.connect(self._approve)
        self.approve_button.setVisible(False)

        buttons = QHBoxLayout()
        buttons.addWidget(self.back_button)
        buttons.addStretch(1)
        buttons.addWidget(self.approve_button)
        buttons.addWidget(self.next_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.step_label)
        layout.addWidget(self.stack)
        layout.addLayout(buttons)

        self.generate_page.generation_finished.connect(self._on_generation_done)
        self.generate_page.generation_failed.connect(self._on_generation_failed)
        self._save_worker = None
        self._saved_lesson_id: int | None = None

    def saved_lesson_id(self) -> int | None:
        return self._saved_lesson_id

    # ---- navigation ----

    def _go_next(self) -> None:
        if self.stack.currentIndex() == 0:
            error = self.word_page.validation_error()
            if error:
                self.word_page.error_label.setText(error)
                return
            self.word_page.error_label.setText("")
            self._start_generation()
        elif self.stack.currentIndex() == 1:
            worker = self.generate_page._worker
            if worker is None or worker.isFinished():
                self._start_generation()  # retry after a failure
        elif self.stack.currentIndex() == 2:
            self.accept()

    def _start_generation(self) -> None:
        self.stack.setCurrentIndex(1)
        self.step_label.setText("Step 2 of 3 — generating lesson text")
        self.next_button.setEnabled(False)
        self.next_button.setText("Generate lesson")
        self.generate_page.start(
            self.word_page.selected_new(),
            self.word_page.selected_review(),
            self.word_page.paragraph_count(),
        )

    def _go_back(self) -> None:
        if self.stack.currentIndex() == 2:
            self._regenerate_all()
        elif self.stack.currentIndex() == 1:
            self.stack.setCurrentIndex(0)
            self.step_label.setText("Step 1 of 3 — word selection")
            self.back_button.setVisible(False)

    def _regenerate_all(self) -> None:
        """Back from the final page = change word list, regenerate all (§7.8)."""
        self.stack.setCurrentIndex(0)
        self.step_label.setText("Step 1 of 3 — word selection (changing the "
                                "words regenerates the whole lesson)")
        self.approve_button.setVisible(False)
        self.next_button.setVisible(True)
        self.next_button.setText("Generate lesson")

    # ---- generation callbacks ----

    def _on_generation_done(self, draft: LessonDraft) -> None:
        self._draft = draft
        self.final_page.set_draft(draft, SegmentationService(self.conn))
        self.stack.setCurrentIndex(2)
        self.step_label.setText("Step 3 of 3 — review and hand-edit")
        self.back_button.setVisible(True)
        self.back_button.setText("Change words (regenerate all)")
        self.next_button.setVisible(False)
        self.approve_button.setVisible(True)
        self.next_button.setEnabled(True)

    def _on_generation_failed(self, message: str) -> None:
        self.next_button.setEnabled(True)
        self.next_button.setText("Retry generation")
        QMessageBox.warning(
            self,
            "Generation failed",
            f"{message}\n\nYou can retry with the same word selection "
            "(Retry generation), or go back to change the words.",
        )

    # ---- approval: run the save pipeline (§7.9) ----

    def _approve(self) -> None:
        if self._draft is None or self._save_worker is not None:
            return
        self.approve_button.setEnabled(False)
        self.step_label.setText("Saving lesson — audio, translations, word lists…")
        from langread.ui.lesson_create.generate_view import SaveWorker

        self._save_worker = SaveWorker(self._db_path, self._draft, parent=self)
        self._save_worker.progress.connect(self._on_save_progress)
        self._save_worker.done.connect(self._on_save_done)
        self._save_worker.failed.connect(self._on_save_failed)
        self._save_worker.start()

    def _on_save_progress(self, stage: str, current: int, total: int) -> None:
        self.step_label.setText(f"Saving — {stage}: {current}/{total}")

    def _on_save_done(self, lesson_id: int) -> None:
        self._saved_lesson_id = lesson_id
        QMessageBox.information(
            self, "Lesson saved",
            f"Lesson #{lesson_id} was saved successfully. "
            "The new words moved to the Learned list.",
        )
        self.accept()

    def _on_save_failed(self, message: str) -> None:
        self.approve_button.setEnabled(True)
        self.step_label.setText("Step 3 of 3 — review and hand-edit")
        QMessageBox.warning(
            self,
            "Saving failed",
            f"{message}\n\nThe lesson was saved as INCOMPLETE; re-approving "
            "will finish the remaining steps.",
        )

    def wait_for_save_worker(self) -> None:
        """Used by tests: block until the save worker finishes."""
        if self._save_worker is not None:
            self._save_worker.wait()
