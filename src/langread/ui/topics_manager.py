"""Topic management window (main menu → "Manage topics").

Lists the topics with their lesson counts and offers:
- create a new topic,
- rename a topic,
- delete a topic — only when it contains no lessons (D-9).
"""

from __future__ import annotations

import sqlite3

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from langread.db.repositories import TopicNotEmptyError, TopicsRepo

_TOPIC_COLUMNS = ["#", "Topic", "Lessons"]


class TopicsManagerDialog(QDialog):
    def __init__(self, conn: sqlite3.Connection, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Manage topics")
        self.resize(480, 400)
        self.conn = conn
        self.topics = TopicsRepo(conn)

        self.table = QTableWidget(0, len(_TOPIC_COLUMNS))
        self.table.setHorizontalHeaderLabels(_TOPIC_COLUMNS)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.table.itemSelectionChanged.connect(self._update_buttons)

        self.new_button = QPushButton("New topic…")
        self.new_button.clicked.connect(self._create_topic)
        self.rename_button = QPushButton("Rename topic…")
        self.rename_button.clicked.connect(self._rename_topic)
        self.delete_button = QPushButton("Delete topic")
        self.delete_button.clicked.connect(self._delete_topic)
        self.delete_button.setToolTip("Only topics without lessons can be deleted")
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)

        self.status_label = QLabel("")

        buttons = QHBoxLayout()
        buttons.addWidget(self.new_button)
        buttons.addWidget(self.rename_button)
        buttons.addWidget(self.delete_button)
        buttons.addStretch(1)
        buttons.addWidget(close_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.table, 1)
        layout.addLayout(buttons)
        layout.addWidget(self.status_label)

        self._reload()

    # ---- table ----

    def _reload(self) -> None:
        topic_list = self.topics.list_all()
        self.table.setRowCount(len(topic_list))
        for row, topic in enumerate(topic_list):
            number_item = QTableWidgetItem(str(topic.order_index))
            number_item.setData(Qt.ItemDataRole.UserRole, topic.id)
            self.table.setItem(row, 0, number_item)
            self.table.setItem(row, 1, QTableWidgetItem(topic.name))
            self.table.setItem(
                row, 2,
                QTableWidgetItem(str(self.topics.lesson_count(topic.id))),
            )
        if topic_list:
            self.table.selectRow(0)
        self._update_buttons()

    def _selected_topic_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return int(item.data(Qt.ItemDataRole.UserRole)) if item is not None else None

    def _selected_topic(self):
        topic_id = self._selected_topic_id()
        return self.topics.get(topic_id) if topic_id is not None else None

    def _update_buttons(self) -> None:
        topic = self._selected_topic()
        has_selection = topic is not None
        self.rename_button.setEnabled(has_selection)
        self.delete_button.setEnabled(
            has_selection and self.topics.lesson_count(topic.id) == 0
        )

    # ---- actions ----

    def _create_topic(self) -> None:
        name, ok = QInputDialog.getText(self, "New topic", "Topic name:")
        if not ok or not name.strip():
            return
        try:
            topic = self.topics.create(name.strip())
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "Duplicate topic",
                                "That topic already exists.")
            return
        self._reload()
        self.status_label.setText(f"Topic “{topic.name}” created.")

    def _rename_topic(self) -> None:
        topic = self._selected_topic()
        if topic is None:
            return
        name, ok = QInputDialog.getText(
            self, "Rename topic", "New topic name:", text=topic.name
        )
        if not ok or not name.strip():
            return
        new_name = name.strip()
        if new_name == topic.name:
            return
        existing = self.topics.get_by_name(new_name)
        if existing is not None and existing.id != topic.id:
            QMessageBox.warning(self, "Duplicate topic",
                                "Another topic with that name already exists.")
            return
        self.topics.rename(topic.id, new_name)
        self._reload()
        self.status_label.setText(f"Topic renamed to “{new_name}”.")

    def _delete_topic(self) -> None:
        topic = self._selected_topic()
        if topic is None:
            return
        if self.topics.lesson_count(topic.id) > 0:
            QMessageBox.warning(
                self, "Topic not empty",
                "Only topics without lessons can be deleted. Delete the "
                "topic's lessons first (Manage lessons).",
            )
            return
        answer = QMessageBox.question(
            self, "Delete topic",
            f"Delete the topic “{topic.name}”?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.topics.delete(topic.id)
        except TopicNotEmptyError:
            QMessageBox.warning(self, "Topic not empty",
                                "The topic still contains lessons.")
            return
        self._reload()
        self.status_label.setText(f"Topic “{topic.name}” deleted.")

