"""Small QThread helper for running blocking work off the UI thread."""

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
