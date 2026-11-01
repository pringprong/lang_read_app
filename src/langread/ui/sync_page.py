"""Sync page (requirements §12.1 item 8, §10 / D-3): export content bundles
for the Android app over USB, and import Android results bundles."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QDialog,
    QGroupBox,
    QLabel,
    QVBoxLayout,
)

from langread.db import connect


class ExportWorker(QThread):
    done = Signal(object)   # ExportStats
    failed = Signal(str)

    def __init__(self, db_path, dest: Path, parent=None) -> None:
        super().__init__(parent)
        self._db_path = db_path
        self._dest = dest

    def run(self) -> None:
        from langread.services.sync import SyncService

        conn = connect(self._db_path)
        try:
            stats = SyncService(conn).export_bundle(self._dest)
        except Exception as exc:  # noqa: BLE001 - forwarded to the UI
            self.failed.emit(str(exc))
        else:
            self.done.emit(stats)
        finally:
            conn.close()


class ImportWorker(QThread):
    done = Signal(object)   # ImportStats
    failed = Signal(str)

    def __init__(self, db_path, bundle_path: Path, parent=None) -> None:
        super().__init__(parent)
        self._db_path = db_path
        self._bundle_path = bundle_path

    def run(self) -> None:
        from langread.services.sync import SyncService

        conn = connect(self._db_path)
        try:
            stats = SyncService(conn).import_results(self._bundle_path)
        except Exception as exc:  # noqa: BLE001 - forwarded to the UI
            self.failed.emit(str(exc))
        else:
            self.done.emit(stats)
        finally:
            conn.close()


class SyncPage(QDialog):
    def __init__(self, conn: sqlite3.Connection, db_path=None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Sync with Android")
        self.resize(640, 400)
        self._db_path = db_path
        if db_path is None:
            from langread.app_config import db_path as default_db_path

            self._db_path = default_db_path()
        self._conn = conn
        self._export_worker = None
        self._import_worker = None

        from PySide6.QtWidgets import (
            QHBoxLayout,
            QLineEdit,
            QPushButton,
        )

        # ---- export ----
        export_group = QGroupBox("Export lessons to the Android app")
        export_intro = QLabel(
            "Write a sync bundle (text, audio, word lists) to a file, then copy "
            "it to the Android phone over USB. Copy the phone's results bundle "
            "back and import it below."
        )
        export_intro.setWordWrap(True)
        self.export_path = QLineEdit()
        self.export_path.setPlaceholderText("Choose a destination…")
        export_browse = QPushButton("Browse…")
        export_browse.clicked.connect(self._browse_export)
        self.export_button = QPushButton("Export bundle")
        self.export_button.clicked.connect(self._export)
        self.export_status = QLabel("")
        self.export_status.setWordWrap(True)

        export_row = QHBoxLayout()
        export_row.addWidget(self.export_path, 1)
        export_row.addWidget(export_browse)
        export_buttons = QHBoxLayout()
        export_buttons.addWidget(self.export_button)
        export_buttons.addStretch(1)
        export_layout = QVBoxLayout(export_group)
        export_layout.addWidget(export_intro)
        export_layout.addLayout(export_row)
        export_layout.addLayout(export_buttons)
        export_layout.addWidget(self.export_status)

        # ---- import ----
        import_group = QGroupBox("Import results from the Android app")
        import_intro = QLabel(
            "The bundle is verified (checksums) and the database is backed up "
            "before anything is applied."
        )
        import_intro.setWordWrap(True)
        self.import_path = QLineEdit()
        self.import_path.setPlaceholderText("Choose the phone's results bundle…")
        import_browse = QPushButton("Browse…")
        import_browse.clicked.connect(self._browse_import)
        self.import_button = QPushButton("Import results")
        self.import_button.clicked.connect(self._import)
        self.import_status = QLabel("")
        self.import_status.setWordWrap(True)

        import_row = QHBoxLayout()
        import_row.addWidget(self.import_path, 1)
        import_row.addWidget(import_browse)
        import_buttons = QHBoxLayout()
        import_buttons.addWidget(self.import_button)
        import_buttons.addStretch(1)
        import_layout = QVBoxLayout(import_group)
        import_layout.addWidget(import_intro)
        import_layout.addLayout(import_row)
        import_layout.addLayout(import_buttons)
        import_layout.addWidget(self.import_status)

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.addWidget(export_group)
        layout.addWidget(import_group)
        layout.addStretch(1)
        layout.addWidget(close_button)

    # ---- export ----

    def _browse_export(self) -> None:
        from datetime import datetime

        from PySide6.QtWidgets import QFileDialog

        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        suggested = Path.home() / f"langread-sync-{stamp}.zip"
        path, _ = QFileDialog.getSaveFileName(
            self, "Export sync bundle", str(suggested), "Sync bundle (*.zip)"
        )
        if path:
            self.export_path.setText(path)

    def _export(self) -> None:
        dest = self.export_path.text().strip()
        if not dest:
            self.export_status.setText("Choose a destination file first.")
            return
        self.export_button.setEnabled(False)
        self.export_status.setText("Exporting…")
        self._export_worker = ExportWorker(self._db_path, Path(dest), parent=self)
        self._export_worker.done.connect(self._export_done)
        self._export_worker.failed.connect(self._export_failed)
        self._export_worker.start()

    def _export_done(self, stats) -> None:
        self.export_button.setEnabled(True)
        size_mb = stats.path.stat().st_size / (1024 * 1024)
        self.export_status.setText(
            f"✅ Exported {stats.lessons} lesson(s), {stats.words} word(s), "
            f"{stats.audio_files} audio file(s), {stats.events} event(s) "
            f"— {stats.path} ({size_mb:.1f} MB)"
        )

    def _export_failed(self, message: str) -> None:
        self.export_button.setEnabled(True)
        self.export_status.setText(f"❌ {message}")

    # ---- import ----

    def _browse_import(self) -> None:
        from PySide6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getOpenFileName(
            self, "Select results bundle", "", "Sync bundle (*.zip)"
        )
        if path:
            self.import_path.setText(path)

    def _import(self) -> None:
        bundle = self.import_path.text().strip()
        if not bundle:
            self.import_status.setText("Choose a results bundle file first.")
            return
        self.import_button.setEnabled(False)
        self.import_status.setText("Verifying and importing…")
        self._import_worker = ImportWorker(self._db_path, Path(bundle), parent=self)
        self._import_worker.done.connect(self._import_done)
        self._import_worker.failed.connect(self._import_failed)
        self._import_worker.start()

    def _import_done(self, stats) -> None:
        self.import_button.setEnabled(True)
        self.import_status.setText(
            f"✅ Imported: {stats.ratings_applied} rating(s) applied "
            f"({stats.ratings_skipped} older/skipped), "
            f"{stats.lessons_marked} lesson review(s), "
            f"{stats.word_actions} word action(s). "
            f"Backup: {stats.backup_path.name}"
        )

    def _import_failed(self, message: str) -> None:
        self.import_button.setEnabled(True)
        self.import_status.setText(f"❌ {message}")

    # ---- test helpers ----

    def wait_for_workers(self) -> None:
        if self._export_worker is not None:
            self._export_worker.wait()
        if self._import_worker is not None:
            self._import_worker.wait()


