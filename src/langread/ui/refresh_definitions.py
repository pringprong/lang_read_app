"""Refresh-definitions dialog (definitions plan §5.3): re-lookup every
word's pinyin/definition in the offline CC-CEDICT dictionary, optionally
falling back to the translation model for words the dictionary lacks.

Runs in a background worker thread (own DB connection), with an automatic
database backup before anything is written."""

from __future__ import annotations

import sqlite3

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QGroupBox,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from langread.db import connect


class RefreshWorker(QThread):
    """Runs DefinitionRefreshService.refresh() in a background thread."""

    progress = Signal(str, int, int)  # stage, current, total
    done = Signal(object)             # RefreshReport
    failed = Signal(str)

    def __init__(self, db_path, use_llm: bool, include_hsk: bool,
                 parent=None) -> None:
        super().__init__(parent)
        self._db_path = db_path
        self._use_llm = use_llm
        self._include_hsk = include_hsk

    def run(self) -> None:
        from langread.db.repositories import SettingsRepo
        from langread.services.definition_refresh import (
            DefinitionRefreshService,
        )
        from langread.services.dictionary import get_dictionary
        from langread.services.model_settings import (
            ModelSettings,
            ModelSettingsError,
        )

        conn = connect(self._db_path)
        try:
            dictionary = get_dictionary()
            if dictionary is None:
                self.failed.emit(
                    "The offline dictionary is unavailable "
                    "(missing bundled resource)."
                )
                return
            llm = None
            if self._use_llm:
                from langread.services.llm_client import LlmClient

                try:
                    llm = LlmClient(
                        ModelSettings(
                            SettingsRepo(conn)
                        ).llm_config("trans")
                    )
                except ModelSettingsError as exc:
                    self.failed.emit(f"Translation model not configured: {exc}")
                    return
            service = DefinitionRefreshService(conn, dictionary, llm=llm)
            report = service.refresh(
                use_llm=self._use_llm,
                include_hsk=self._include_hsk,
                progress=lambda stage, current, total: self.progress.emit(
                    stage, current, total
                ),
            )
            self.done.emit(report)
        except Exception as exc:  # noqa: BLE001 - forwarded to the UI
            self.failed.emit(str(exc))
        finally:
            conn.close()


class RefreshDefinitionsDialog(QDialog):
    def __init__(self, conn: sqlite3.Connection, db_path=None,
                 parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Refresh word definitions")
        self.resize(560, 340)
        self._db_path = db_path
        if db_path is None:
            from langread.app_config import db_path as default_db_path

            self._db_path = default_db_path()
        self._conn = conn
        self._worker: RefreshWorker | None = None

        intro = QLabel(
            "Rebuilds the pinyin and definition of every word on the New / "
            "Learned / Basic lists from the offline dictionary (CC-CEDICT). "
            "The database is backed up first; words not in the dictionary "
            "have their old definition cleared so the gap is visible."
        )
        intro.setWordWrap(True)

        options = QGroupBox("Options")
        self.use_llm = QCheckBox(
            "Use the translation model for words not in the dictionary"
        )
        self.include_hsk = QCheckBox(
            "Also refresh the HSK list definitions"
        )
        self.include_hsk.setChecked(True)
        options_layout = QVBoxLayout(options)
        options_layout.addWidget(self.use_llm)
        options_layout.addWidget(self.include_hsk)
        if not self._translation_model_configured():
            self.use_llm.setEnabled(False)
            self.use_llm.setToolTip(
                "The translation model is not configured (see Model settings)."
            )

        self.start_button = QPushButton("Start refresh")
        self.start_button.clicked.connect(self._start)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_label = QLabel("")
        self.progress_label.setWordWrap(True)
        self.status = QLabel("")
        self.status.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.addWidget(intro)
        layout.addWidget(options)
        layout.addWidget(self.start_button)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.progress_label)
        layout.addWidget(self.status)

    # ---- helpers ----

    def _translation_model_configured(self) -> bool:
        from langread.db.repositories import SettingsRepo
        from langread.services.model_settings import (
            ModelSettings,
            ModelSettingsError,
        )

        try:
            ModelSettings(SettingsRepo(self._conn)).llm_config("trans")
        except ModelSettingsError:
            return False
        return True

    def _start(self) -> None:
        self.start_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # busy until the first callback
        self.progress_label.setText("Loading the offline dictionary…")
        self.status.setText("")
        self._worker = RefreshWorker(
            self._db_path, self.use_llm.isChecked(), self.include_hsk.isChecked()
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.done.connect(self._on_done)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_progress(self, stage: str, current: int, total: int) -> None:
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.progress_label.setText(f"{stage}: {current} / {total}")

    def _on_done(self, report) -> None:
        self.progress_bar.setVisible(False)
        self.progress_label.setText("")
        self.start_button.setEnabled(True)
        self.status.setText(report.summary())
        if report.misses:
            shown = ", ".join(report.misses[:20])
            more = len(report.misses) - min(len(report.misses), 20)
            self.status.setText(
                self.status.text()
                + f"\nNot in the dictionary: {shown}"
                + (f" … (+{more} more)" if more > 0 else "")
            )

    def _on_failed(self, message: str) -> None:
        self.progress_bar.setVisible(False)
        self.progress_label.setText("")
        self.start_button.setEnabled(True)
        self.status.setText(f"Failed: {message}")
