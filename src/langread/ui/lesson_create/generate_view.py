"""Wizard step 2: background generation with progress (requirements §7.3–7.7)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QLabel, QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from langread.db import connect
from langread.services.generation import GenerationService, LessonDraft


class GenerationWorker(QThread):
    """Generates the lesson in a background thread.

    SQLite connections are thread-bound, so the worker opens its OWN
    connection to the database file for the duration of the run.
    """

    progress = Signal(int, str)     # paragraph index, text
    done = Signal(object)           # LessonDraft
    failed = Signal(str)            # error message

    def __init__(self, db_path, llm, topic_id: int,
                 new_words: list[str], review_words: list[str],
                 n_paragraphs: int, parent=None) -> None:
        super().__init__(parent)
        self._db_path = db_path
        self._llm = llm
        self._topic_id = topic_id
        self._new_words = new_words
        self._review_words = review_words
        self._n_paragraphs = n_paragraphs

    def run(self) -> None:
        conn = connect(self._db_path)
        try:
            service = GenerationService(conn, llm=self._llm)
            draft = service.generate_lesson(
                self._topic_id, self._new_words, self._review_words,
                self._n_paragraphs,
                progress=lambda index, text: self.progress.emit(index, text),
            )
        except Exception as exc:  # noqa: BLE001 - forwarded to the UI
            self.failed.emit(str(exc))
        else:
            self.done.emit(draft)
        finally:
            conn.close()


class GeneratePage(QWidget):
    generation_finished = Signal(object)  # LessonDraft
    generation_failed = Signal(str)

    def __init__(self, db_path, topic_id: int, llm=None,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._db_path = db_path
        self._topic_id = topic_id
        self._llm = llm
        self._worker: GenerationWorker | None = None

        self.status = QLabel("Generating… one paragraph at a time.")
        self.status.setWordWrap(True)
        self.progress_list = QListWidget()

        layout = QVBoxLayout(self)
        layout.addWidget(self.status)
        layout.addWidget(self.progress_list)

    def start(self, new_words: list[str], review_words: list[str],
              n_paragraphs: int) -> None:
        self.progress_list.clear()
        self.status.setText("Generating… one paragraph at a time.")
        self._worker = GenerationWorker(
            self._db_path, self._llm, self._topic_id, new_words, review_words,
            n_paragraphs, parent=self,
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.done.connect(self._on_done)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_progress(self, index: int, text: str) -> None:
        preview = text if len(text) <= 60 else text[:57] + "…"
        self.progress_list.addItem(QListWidgetItem(f"Paragraph {index + 1}: {preview}"))
        self.progress_list.scrollToBottom()

    def _on_done(self, draft) -> None:
        self.status.setText("Generation complete. Review the text on the next page.")
        self.generation_finished.emit(draft)

    def _on_failed(self, message: str) -> None:
        self.status.setText(f"Generation failed: {message}")
        self.generation_failed.emit(message)

    def wait_for_worker(self) -> None:
        """Used by tests: block until the worker thread finishes."""
        if self._worker is not None:
            self._worker.wait()

