"""Settings dialog with tabs: Models, Prompt templates, Spaced repetition."""

from __future__ import annotations

import sqlite3

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QTabWidget, QVBoxLayout

from langread.ui.settings.models_page import ModelsPage
from langread.ui.settings.srs_page import SrsPage
from langread.ui.settings.templates_page import TemplatesPage


class SettingsDialog(QDialog):
    def __init__(self, conn: sqlite3.Connection,
                 parent=None, initial_tab: int = 0) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(720, 560)

        self.tabs = QTabWidget()
        self.models_page = ModelsPage(conn)
        self.templates_page = TemplatesPage(conn)
        self.srs_page = SrsPage(conn)
        self.tabs.addTab(self.models_page, "Models")
        self.tabs.addTab(self.templates_page, "Prompt templates")
        self.tabs.addTab(self.srs_page, "Spaced repetition")
        self.tabs.setCurrentIndex(initial_tab)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close, parent=self
        )
        buttons.rejected.connect(self.reject)
        buttons.clicked.connect(lambda _b: self.reject())

        layout = QVBoxLayout(self)
        layout.addWidget(self.tabs)
        layout.addWidget(buttons)
