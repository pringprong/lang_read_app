"""Spaced repetition parameters page (requirements §11, §12.1 item 7).

Renders every field of `SrsParams` automatically — int fields as spin boxes,
float fields as double spin boxes — with tooltips from PARAM_HELP.
"""

from __future__ import annotations

import sqlite3
from dataclasses import fields

from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from langread.services.srs import INT_PARAM_FIELDS, SrsParams, SrsService

PARAM_HELP = {
    "initial_ease": "Starting easiness factor (Anki uses 2.5).",
    "ease_delta_easy": "Ease change when rated 'easy'.",
    "ease_delta_difficult": "Ease change when rated 'difficult'.",
    "ease_min": "Lower bound for the easiness factor.",
    "ease_max": "Upper bound for the easiness factor.",
    "learned_words_per_paragraph": (
        "Learned words suggested to each paragraph's prompt."
    ),
    "novelty_window_lessons": (
        "Lessons after first learning during which a word stays boosted."
    ),
    "staleness_target_lessons": (
        "Lessons without an appearance after which a word is fully 'stale' "
        "(maximum return priority)."
    ),
    "weight_novelty": (
        "Weight of factor 1: how recently the word was first learned."
    ),
    "weight_staleness": (
        "Weight of factor 2: how long since the word last actually appeared "
        "(the core of spaced repetition)."
    ),
    "weight_difficulty": (
        "Weight of factor 3: your difficult/easy ratings (least important)."
    ),
    "same_lesson_cooldown_paragraphs": (
        "Paragraphs a word waits before it can be suggested again within the "
        "same lesson (0 = once per lesson)."
    ),
}


class SrsPage(QWidget):
    def __init__(self, conn: sqlite3.Connection,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.service = SrsService(conn)

        form = QFormLayout()
        self._spinners: dict[str, QSpinBox | QDoubleSpinBox] = {}
        for f in fields(SrsParams):
            if f.name in INT_PARAM_FIELDS:
                spin: QSpinBox | QDoubleSpinBox = QSpinBox()
                spin.setRange(0, 100)
            else:
                spin = QDoubleSpinBox()
                spin.setDecimals(2)
                spin.setRange(0.0, 2000.0)
                spin.setSingleStep(0.05)
            spin.setToolTip(PARAM_HELP.get(f.name, ""))
            self._spinners[f.name] = spin
            label_text = f.name.replace("_", " ")
            form.addRow(f"{label_text}:", spin)

        self.save_button = QPushButton("Save parameters")
        self.save_button.clicked.connect(self._save)
        self.status = QLabel("")

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.save_button)
        layout.addWidget(self.status)
        layout.addStretch(1)
        self._load()

    def _load(self) -> None:
        params = self.service.params()
        for name, spin in self._spinners.items():
            spin.setValue(float(getattr(params, name)))

    def _save(self) -> None:
        values = {}
        for name, spin in self._spinners.items():
            value: float | int = spin.value()
            if name in INT_PARAM_FIELDS:
                value = int(value)
            values[name] = value
        params = SrsParams(**values)
        self.service.set_params(params)
        self.status.setText("Saved.")
