"""Word list manager (requirements §12.1 item 5, §5.4, §5.5).

One dialog, four tabs: New / Learned / Basic / HSK words, with the
list-to-list moves and bulk HSK import actions.
"""

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
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from langread.db.repositories import HskRepo, TopicsRepo, WordsRepo
from langread.services.hsk import HskService
from langread.services.word_import import WordImportService

_LIST_COLUMNS = ["Word", "Pinyin", "Definition", "Added"]
LEARNED_COLUMNS = ["Word", "Pinyin", "Definition", "Last lesson", "Ease", "Reps"]
_HSK_COLUMNS = ["Word", "Pinyin", "Definition", "Level", "In app"]


class _ListTab(QWidget):
    """Shared table for the New / Learned / Basic tabs."""

    def __init__(self, state: str, words: WordsRepo,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.state = state
        self.words = words
        self.is_learned = state == "learned"

        columns = LEARNED_COLUMNS if self.is_learned else _LIST_COLUMNS
        self.table = QTableWidget(0, len(columns))
        self.table.setHorizontalHeaderLabels(columns)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )

        self.info = QLabel("")
        self.buttons = QHBoxLayout()

        layout = QVBoxLayout(self)
        layout.addWidget(self.info)
        layout.addWidget(self.table)
        layout.addLayout(self.buttons)
        self.reload()

    def reload(self) -> None:
        word_list = self.words.list_by_state(self.state)
        self.table.setRowCount(len(word_list))
        for row, word in enumerate(word_list):
            self.table.setItem(row, 0, QTableWidgetItem(word.text))
            self.table.setItem(row, 1, QTableWidgetItem(word.pinyin or ""))
            self.table.setItem(row, 2, QTableWidgetItem(word.definition or ""))
            if self.is_learned:
                last_lesson = (
                    str(word.last_seen_lesson_id)
                    if word.last_seen_lesson_id is not None else ""
                )
                self.table.setItem(row, 3, QTableWidgetItem(last_lesson))
                self.table.setItem(row, 4, QTableWidgetItem(f"{word.ease:.2f}"))
                self.table.setItem(row, 5, QTableWidgetItem(str(word.reps)))
            else:
                self.table.setItem(row, 3, QTableWidgetItem(word.added_at or ""))
        self.info.setText(f"{len(word_list)} words on the {self.state} list")

    def selected_rows(self) -> list[int]:
        return sorted({index.row() for index in self.table.selectedIndexes()})

    def word_texts_at(self, rows: list[int]) -> list[str]:
        return [self.table.item(row, 0).text() for row in rows]


class WordListManager(QDialog):
    def __init__(self, conn: sqlite3.Connection, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Word lists")
        self.resize(860, 560)
        self.conn = conn

        self.words = WordsRepo(conn)
        self.hsk_repo = HskRepo(conn)
        self.topics = TopicsRepo(conn)
        HskService(conn).import_if_needed()
        self.import_service = WordImportService(conn)

        self.tabs = QTabWidget()
        self.new_tab = self._build_list_tab("new")
        self.learned_tab = self._build_list_tab("learned")
        self.basic_tab = self._build_list_tab("basic")
        self.hsk_tab = self._build_hsk_tab()
        self.tabs.addTab(self.new_tab, "New")
        self.tabs.addTab(self.learned_tab, "Learned")
        self.tabs.addTab(self.basic_tab, "Basic")
        self.tabs.addTab(self.hsk_tab, "HSK")

        close = QPushButton("Close")
        close.clicked.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.addWidget(self.tabs)
        layout.addWidget(close, alignment=Qt.AlignmentFlag.AlignRight)

    # ---- tabs ----

    def _build_list_tab(self, state: str) -> _ListTab:
        tab = _ListTab(state, self.words)
        if state == "new":
            move_button = QPushButton("Move selected → Basic list")
            move_button.clicked.connect(self._new_to_basic)
            assign_button = QPushButton("Assign selected to topic…")
            assign_button.clicked.connect(self._assign_topic)
            tab.buttons.addWidget(move_button)
            tab.buttons.addWidget(assign_button)
        elif state == "basic":
            move_button = QPushButton("Move selected → New list")
            move_button.clicked.connect(self._basic_to_new)
            tab.buttons.addWidget(move_button)
        tab.buttons.addStretch(1)
        return tab

    # ---- actions ----

    def _new_to_basic(self) -> None:
        self._move_selected(self.new_tab, "basic")

    def _basic_to_new(self) -> None:
        self._move_selected(self.basic_tab, "new")

    def _move_selected(self, tab: _ListTab, target: str) -> None:
        rows = tab.selected_rows()
        if not rows:
            return
        for text in tab.word_texts_at(rows):
            word = self.words.get_by_text(text)
            if word is not None:
                self.words.move_to_state(word.id, target)
        self._reload_lists()

    def _assign_topic(self) -> None:
        rows = self.new_tab.selected_rows()
        if not rows:
            return
        topics = self.topics.list_all()
        if not topics:
            QMessageBox.information(self, "No topics", "Create a topic first.")
            return
        name, ok = QInputDialog.getItem(
            self, "Assign topic", "Topic:", [t.name for t in topics], 0, False
        )
        if not ok:
            return
        topic = self.topics.get_by_name(name)
        if topic is None:
            return
        for text in self.new_tab.word_texts_at(rows):
            word = self.words.get_by_text(text)
            if word is not None:
                self.words.associate_topic(word.id, topic.id)

    # ---- HSK tab ----

    def _build_hsk_tab(self) -> QWidget:
        tab = QWidget()
        controls = QHBoxLayout()
        self.level_combo = QComboBox()
        counts = self.hsk_repo.counts_by_level()
        for level in range(1, 7):
            self.level_combo.addItem(f"HSK {level} ({counts.get(level, 0)} words)", level)
        self.level_combo.currentIndexChanged.connect(self._reload_hsk)
        self.unused_only = QCheckBox("Show only words not used in the app")
        self.unused_only.setChecked(True)
        self.unused_only.stateChanged.connect(self._reload_hsk)

        add_new = QPushButton("Add selected → New list")
        add_new.clicked.connect(lambda: self._hsk_add("new"))
        add_basic = QPushButton("Add selected → Basic list")
        add_basic.clicked.connect(lambda: self._hsk_add("basic"))

        controls.addWidget(QLabel("Level:"))
        controls.addWidget(self.level_combo)
        controls.addWidget(self.unused_only)
        controls.addStretch(1)
        controls.addWidget(add_new)
        controls.addWidget(add_basic)

        self.hsk_table = QTableWidget(0, len(_HSK_COLUMNS))
        self.hsk_table.setHorizontalHeaderLabels(_HSK_COLUMNS)
        self.hsk_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.hsk_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.hsk_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.hsk_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )

        self.hsk_info = QLabel("")
        layout = QVBoxLayout(tab)
        layout.addLayout(controls)
        layout.addWidget(self.hsk_info)
        layout.addWidget(self.hsk_table)
        self._reload_hsk()
        return tab

    def _reload_hsk(self) -> None:
        level = self.level_combo.currentData() or 1
        state = "unused" if self.unused_only.isChecked() else None
        entries = self.hsk_repo.list_level(level, app_state=state)
        self.hsk_table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            self.hsk_table.setItem(row, 0, QTableWidgetItem(entry.text))
            self.hsk_table.setItem(row, 1, QTableWidgetItem(entry.pinyin or ""))
            self.hsk_table.setItem(row, 2, QTableWidgetItem(entry.definition or ""))
            self.hsk_table.setItem(row, 3, QTableWidgetItem(str(entry.level)))
            self.hsk_table.setItem(row, 4, QTableWidgetItem(entry.app_state))
        self.hsk_info.setText(f"{len(entries)} words shown")

    def _hsk_add(self, target: str) -> None:
        rows = sorted({index.row() for index in self.hsk_table.selectedIndexes()})
        added = 0
        for row in rows:
            text = self.hsk_table.item(row, 0).text()
            matches = self.hsk_repo.find_by_text(text)
            if not matches:
                continue
            self.import_service.add_from_hsk(matches[0], target=target)
            added += 1
        if added:
            self._reload_hsk()
            self._reload_lists()

    def _reload_lists(self) -> None:
        self.new_tab.reload()
        self.learned_tab.reload()
        self.basic_tab.reload()


