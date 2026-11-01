"""Add-words dialog (requirements §5.1 paste flow, §5.2 manual entry)."""

from __future__ import annotations

import sqlite3

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from langread.db.repositories import TopicsRepo
from langread.services.word_import import WordImportService

_PARSE_COLUMNS = ["New word?", "Word", "Status", "Pinyin", "Definition"]


class PasteTab(QWidget):
    def __init__(self, service: WordImportService, topics: TopicsRepo,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.service = service
        self.topics = topics
        self._parsed = []

        from PySide6.QtWidgets import QPlainTextEdit

        intro = QLabel(
            "Paste Chinese text below. After parsing, tick the words that are NEW "
            "to you — they go to the New Word List. All other words go to the "
            "Basic Word List. Words already on a list are left unchanged."
        )
        intro.setWordWrap(True)

        self.text_box = QPlainTextEdit()
        self.text_box.setPlaceholderText("在此粘贴中文文本…")

        controls = QHBoxLayout()
        self.parse_button = QPushButton("Parse text")
        self.parse_button.clicked.connect(self._parse)
        self.topic_combo = QComboBox()
        self.topic_combo.addItem("(no topic)", None)
        for topic in topics.list_all():
            self.topic_combo.addItem(topic.name, topic.id)
        self.import_button = QPushButton("Import words")
        self.import_button.clicked.connect(self._import)
        self.import_button.setEnabled(False)
        controls.addWidget(self.parse_button)
        controls.addStretch(1)
        controls.addWidget(QLabel("Associate with:"))
        controls.addWidget(self.topic_combo)
        controls.addWidget(self.import_button)

        self.table = QTableWidget(0, len(_PARSE_COLUMNS))
        self.table.setHorizontalHeaderLabels(_PARSE_COLUMNS)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(
            4, QHeaderView.ResizeMode.Stretch
        )
        self.status = QLabel("")

        layout = QVBoxLayout(self)
        layout.addWidget(intro)
        layout.addWidget(self.text_box)
        layout.addLayout(controls)
        layout.addWidget(self.table)
        layout.addWidget(self.status)

    def _parse(self) -> None:
        text = self.text_box.toPlainText()
        if not text.strip():
            self.status.setText("Paste some text first.")
            return
        self._parsed = self.service.parse_pasted_text(text)
        self.table.setRowCount(len(self._parsed))
        for row, item in enumerate(self._parsed):
            box = QCheckBox()
            box.setEnabled(item.existing is None)  # existing words stay put
            self._wrap_checkbox(row, box)
            self.table.setItem(row, 1, QTableWidgetItem(item.text))
            if item.existing is not None:
                status = f"on {item.existing.list_state} list"
            elif item.hsk is not None:
                status = f"HSK {item.hsk.level}"
            else:
                status = "unknown"
            self.table.setItem(row, 2, QTableWidgetItem(status))
            info = item.existing or item.hsk
            self.table.setItem(row, 3, QTableWidgetItem((info.pinyin if info else None) or ""))
            self.table.setItem(row, 4, QTableWidgetItem((info.definition if info else None) or ""))
        self.status.setText(f"Found {len(self._parsed)} distinct words.")
        self.import_button.setEnabled(bool(self._parsed))

    def _wrap_checkbox(self, row: int, box: QCheckBox) -> None:
        widget = QWidget()
        box_layout = QHBoxLayout(widget)
        box_layout.addWidget(box)
        box_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        box_layout.setContentsMargins(0, 0, 0, 0)
        self.table.setCellWidget(row, 0, widget)

    def checkbox_at(self, row: int) -> QCheckBox | None:
        widget = self.table.cellWidget(row, 0)
        return widget.findChild(QCheckBox) if widget else None

    def _import(self) -> None:
        marked: set[str] = set()
        for row in range(self.table.rowCount()):
            box = self.checkbox_at(row)
            if box is not None and box.isChecked():
                marked.add(self.table.item(row, 1).text())
        summary = self.service.import_from_paste(
            self._parsed, marked, self.topic_combo.currentData()
        )
        self.status.setText(
            f"Imported: {summary.added_new} new, {summary.added_basic} basic, "
            f"{summary.already_known} already on a list."
        )
        self.import_button.setEnabled(False)


class ManualTab(QWidget):
    def __init__(self, service: WordImportService, topics: TopicsRepo,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.service = service

        self.word_edit = QLineEdit()
        self.word_edit.setPlaceholderText("新词")
        self.topic_combo = QComboBox()
        self.topic_combo.addItem("(no topic)", None)
        for topic in topics.list_all():
            self.topic_combo.addItem(topic.name, topic.id)
        self.add_button = QPushButton("Add to New Word List")
        self.add_button.clicked.connect(self._add)
        self.status = QLabel("")

        form = QHBoxLayout()
        form.addWidget(QLabel("Word:"))
        form.addWidget(self.word_edit, 1)
        form.addWidget(QLabel("Topic:"))
        form.addWidget(self.topic_combo)
        form.addWidget(self.add_button)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.status)
        layout.addStretch(1)

    def _add(self) -> None:
        text = self.word_edit.text().strip()
        if not text:
            self.status.setText("Enter a word first.")
            return
        try:
            word, created = self.service.add_manual(
                text, self.topic_combo.currentData()
            )
        except ValueError as exc:
            self.status.setText(str(exc))
            return
        if created:
            self.status.setText(f"Added “{word.text}” to the New Word List.")
            self.word_edit.clear()
        else:
            self.status.setText(
                f"“{word.text}” is already on the {word.list_state} list."
            )


class AddWordsDialog(QDialog):
    def __init__(self, conn: sqlite3.Connection, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add words")
        self.resize(760, 540)
        self.service = WordImportService(conn)

        self.tabs = QTabWidget()
        self.paste_tab = PasteTab(self.service, TopicsRepo(conn))
        self.manual_tab = ManualTab(self.service, TopicsRepo(conn))
        self.tabs.addTab(self.paste_tab, "From pasted text")
        self.tabs.addTab(self.manual_tab, "One at a time")

        close = QPushButton("Close")
        close.clicked.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.addWidget(self.tabs)
        layout.addWidget(close, alignment=Qt.AlignmentFlag.AlignRight)

