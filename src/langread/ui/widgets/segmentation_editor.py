"""Hand-editable segmentation widget (D-6: merge/split tokens by hand).

Displays tokens as selectable chips; buttons merge the selected contiguous
runs into single tokens, split selected tokens into characters, or reset to
the originally supplied segmentation. Emits `changed` after every edit.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class SegmentationEditor(QWidget):
    changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._original: list[str] = []
        self._tokens: list[str] = []

        self._list = QListWidget()
        self._list.setViewMode(QListWidget.ViewMode.IconMode)
        self._list.setWrapping(True)
        self._list.setMovement(QListWidget.Movement.Static)
        self._list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self._list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self._list.setSpacing(4)
        self._list.setMinimumHeight(120)

        merge_button = QPushButton("Merge selected")
        merge_button.clicked.connect(self._merge)
        split_button = QPushButton("Split selected")
        split_button.clicked.connect(self._split)
        reset_button = QPushButton("Reset")
        reset_button.clicked.connect(self._reset)

        buttons = QHBoxLayout()
        buttons.addWidget(merge_button)
        buttons.addWidget(split_button)
        buttons.addStretch(1)
        buttons.addWidget(reset_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self._list)
        layout.addLayout(buttons)

    # ---- public API ----

    def set_tokens(self, tokens: list[str]) -> None:
        self._original = list(tokens)
        self._tokens = list(tokens)
        self._render()

    def tokens(self) -> list[str]:
        return list(self._tokens)

    def original_tokens(self) -> list[str]:
        return list(self._original)

    # ---- editing operations ----

    def _selected_rows(self) -> list[int]:
        return sorted(index.row() for index in self._list.selectedIndexes())

    def _merge(self) -> None:
        rows = self._selected_rows()
        if len(rows) < 2:
            return
        # group the selection into contiguous runs
        groups: list[list[int]] = []
        for row in rows:
            if groups and row == groups[-1][-1] + 1:
                groups[-1].append(row)
            else:
                groups.append([row])
        selected = set(rows)
        merged: list[str] = []
        i = 0
        while i < len(self._tokens):
            if i in selected:
                for group in groups:
                    if i in group:
                        merged.append("".join(self._tokens[j] for j in group))
                        i = group[-1] + 1
                        break
            else:
                merged.append(self._tokens[i])
                i += 1
        self._tokens = merged
        self._render()
        self.changed.emit()

    def _split(self) -> None:
        rows = set(self._selected_rows())
        if not rows:
            return
        result: list[str] = []
        for i, token in enumerate(self._tokens):
            if i in rows:
                result.extend(list(token))
            else:
                result.append(token)
        self._tokens = result
        self._render()
        self.changed.emit()

    def _reset(self) -> None:
        self._tokens = list(self._original)
        self._render()
        self.changed.emit()

    # ---- rendering ----

    def _render(self) -> None:
        self._list.clear()
        for token in self._tokens:
            self._list.addItem(token)
