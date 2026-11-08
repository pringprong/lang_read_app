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
                 new_words: list[str], n_paragraphs: int, parent=None) -> None:
        super().__init__(parent)
        self._db_path = db_path
        self._llm = llm
        self._topic_id = topic_id
        self._new_words = new_words
        self._n_paragraphs = n_paragraphs

    def run(self) -> None:
        conn = connect(self._db_path)
        try:
            service = GenerationService(conn, llm=self._llm)
            draft = service.generate_lesson(
                self._topic_id, self._new_words, self._n_paragraphs,
                progress=lambda index, text: self.progress.emit(index, text),
            )
        except Exception as exc:  # noqa: BLE001 - forwarded to the UI
            self.failed.emit(str(exc))
        else:
            self.done.emit(draft)
        finally:
            conn.close()


class SaveWorker(QThread):
    """Runs the lesson save pipeline (§7.9) in a background thread."""

    progress = Signal(str, int, int)  # stage, current, total
    done = Signal(int)                # lesson id
    failed = Signal(str)

    def __init__(self, db_path, draft: LessonDraft, parent=None) -> None:
        super().__init__(parent)
        self._db_path = db_path
        self._draft = draft

    def run(self) -> None:
        from langread.db.repositories import SettingsRepo
        from langread.services.dictionary import get_dictionary
        from langread.services.lesson_saver import LessonSaver, SaveError
        from langread.services.llm_client import LlmClient
        from langread.services.model_settings import (
            ModelSettings,
            ModelSettingsError,
        )
        from langread.services.translation import TranslationService
        from langread.services.tts import TtsService

        conn = connect(self._db_path)
        try:
            settings = ModelSettings(SettingsRepo(conn))
            tts = TtsService(settings.tts_config())  # required: raises if unset
            try:
                translation = TranslationService(
                    conn, LlmClient(settings.llm_config("trans")),
                    dictionary=get_dictionary(),
                )
            except ModelSettingsError:
                translation = None  # optional: sentences stay untranslated
            saver = LessonSaver(conn, tts=tts, translation=translation)
            lesson = saver.save_lesson(
                self._draft,
                progress=lambda stage, current, total: self.progress.emit(
                    stage, current, total
                ),
            )
        except ModelSettingsError as exc:
            self.failed.emit(str(exc))
        except SaveError as exc:
            self.failed.emit(f"Saving failed: {exc}")
        except Exception as exc:  # noqa: BLE001 - forwarded to the UI
            self.failed.emit(f"Saving failed: {exc}")
        else:
            self.done.emit(lesson.id)
        finally:
            conn.close()



class FinalizeWorker(QThread):
    """Resumes an interrupted lesson save (§7.9 resume) in a background thread."""

    done = Signal(int)   # lesson id
    failed = Signal(str)

    def __init__(self, db_path, lesson_id: int, parent=None) -> None:
        super().__init__(parent)
        self._db_path = db_path
        self._lesson_id = lesson_id

    def run(self) -> None:
        from langread.db.repositories import SettingsRepo
        from langread.services.dictionary import get_dictionary
        from langread.services.lesson_saver import LessonSaver, SaveError
        from langread.services.llm_client import LlmClient
        from langread.services.model_settings import (
            ModelSettings,
            ModelSettingsError,
        )
        from langread.services.translation import TranslationService
        from langread.services.tts import TtsService

        conn = connect(self._db_path)
        try:
            settings = ModelSettings(SettingsRepo(conn))
            tts = TtsService(settings.tts_config())
            try:
                translation = TranslationService(
                    conn, LlmClient(settings.llm_config("trans")),
                    dictionary=get_dictionary(),
                )
            except ModelSettingsError:
                translation = None
            saver = LessonSaver(conn, tts=tts, translation=translation)
            lesson = saver.finalize_lesson(self._lesson_id)
        except Exception as exc:  # noqa: BLE001 - forwarded to the UI
            self.failed.emit(str(exc))
        else:
            self.done.emit(lesson.id)
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

    def start(self, new_words: list[str], n_paragraphs: int) -> None:
        self.progress_list.clear()
        self.status.setText("Generating… one paragraph at a time.")
        self._worker = GenerationWorker(
            self._db_path, self._llm, self._topic_id, new_words,
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

