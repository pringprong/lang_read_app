"""Small QThread helpers for running blocking work off the UI thread."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QThread, Signal


class Worker(QThread):
    """Runs `fn()` in a background thread; emits done(result, error)."""

    done = Signal(object, object)  # result, exception-or-None

    def __init__(self, fn: Callable[[], Any], parent: QThread | None = None) -> None:
        super().__init__(parent)
        self._fn = fn

    def run(self) -> None:  # QThread entry point
        try:
            result = self._fn()
        except Exception as exc:  # noqa: BLE001 - forwarded to the UI
            self.done.emit(None, exc)
        else:
            self.done.emit(result, None)


def run_async(fn: Callable[[], Any], on_done: Callable[[Any, Exception | None], None],
              parent: QThread | None = None) -> Worker:
    """Start `fn` in the background and call `on_done(result, error)` on the UI thread."""
    worker = Worker(fn, parent)
    worker.done.connect(on_done)
    worker.start()
    return worker


class SentenceTranslationWorker(QThread):
    """Translates a lesson's sentences in a background thread (own DB
    connection, so the UI connection is never used cross-thread).

    retranslate=False → only sentences without a stored translation
    (e.g. after a lesson's text was edited and saved);
    retranslate=True  → every sentence, replacing existing translations
    ("Regenerate translation" in the lesson list).
    """

    progress = Signal(int, int)  # current sentence, total
    done = Signal(int)           # number of sentences translated
    failed = Signal(str)

    def __init__(self, db_path, lesson_id: int, retranslate: bool = False,
                 parent: QThread | None = None) -> None:
        super().__init__(parent)
        self._db_path = db_path
        self._lesson_id = lesson_id
        self._retranslate = retranslate

    def run(self) -> None:  # QThread entry point
        from langread.db import connect
        from langread.db.repositories import SettingsRepo
        from langread.services.dictionary import get_dictionary
        from langread.services.lesson_saver import LessonSaver, SaveError
        from langread.services.llm_client import LlmClient
        from langread.services.model_settings import (
            ModelSettings,
            ModelSettingsError,
        )
        from langread.services.translation import TranslationService

        conn = connect(self._db_path)
        try:
            try:
                translation = TranslationService(
                    conn,
                    LlmClient(ModelSettings(SettingsRepo(conn)).llm_config("trans")),
                    dictionary=get_dictionary(),
                )
            except ModelSettingsError as exc:
                self.failed.emit(str(exc))
                return
            saver = LessonSaver(conn, translation=translation)
            if self._retranslate:
                count = saver.retranslate_sentences(
                    self._lesson_id, progress=self._emit_progress
                )
            else:
                count = saver.translate_missing_sentences(
                    self._lesson_id, progress=self._emit_progress
                )
            self.done.emit(count)
        except SaveError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # noqa: BLE001 - forwarded to the UI
            self.failed.emit(f"translation failed: {exc}")
        finally:
            conn.close()

    def _emit_progress(self, stage: str, current: int, total: int) -> None:
        self.progress.emit(current, total)
