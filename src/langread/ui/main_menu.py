"""Desktop main menu — the eight top-level options (requirements §12.1)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

MENU_ITEMS: list[tuple[str, str]] = [
    ("Review a lesson", "Select a topic and review a lesson in that topic."),
    ("Create a new topic", "Create a new topic and start a new chain of lessons."),
    ("Create a new lesson", "Create a new lesson in an existing topic."),
    ("Add new words", "Add words to the new word list (paste, manual, HSK)."),
    ("Manage word lists", "Review the new / learned / basic / HSK word lists."),
    ("Model settings", "Prompt templates, model URLs, and API keys."),
    ("SRS settings", "Spaced-repetition algorithm parameters."),
    ("Sync with Android", "Export / import sync bundles over USB."),
]


class MainMenu(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("LangRead — Main Menu")
        self.resize(520, 480)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(8)

        title = QLabel("LangRead")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 22px; font-weight: bold;")
        layout.addWidget(title)

        subtitle = QLabel("Chinese reading & listening — spaced repetition")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)
        layout.addSpacing(12)

        for label, tooltip in MENU_ITEMS:
            button = QPushButton(label)
            button.setToolTip(tooltip)
            button.clicked.connect(self._not_implemented)
            layout.addWidget(button)

        self.setCentralWidget(central)

    def _not_implemented(self) -> None:
        QMessageBox.information(
            self,
            "Not implemented yet",
            "This feature is not implemented yet. See the milestone plan "
            "(20261101_desktop_app_plan.md).",
        )
