"""Spaced repetition parameters page (requirements §11, §12.1 item 7)."""

from __future__ import annotations

import sqlite3
from dataclasses import fields

from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from langread.services.srs import SrsParams, SrsService

PARAM_HELP = {
    "initial_ease": "Starting easiness factor (Anki uses 2.5).",
    "initial_interval_days": "Days until a newly learned word first returns.",
    "exposure_multiplier": "Interval growth when a word is merely used in a new lesson.",
    "easy_bonus": "Extra interval multiplier when rated 'easy'.",
    "ease_delta_easy": "Ease change when rated 'easy'.",
    "ease_delta_difficult": "Ease change when rated 'difficult'.",
    "relearn_interval_days": "Interval right after a 'difficult' rating.",
    "min_interval_days": "Shortest normal interval (relearn step is exempt).",
    "max_interval_days": "Longest interval between exposures.",
    "ease_min": "Lower bound for the easiness factor.",
    "ease_max": "Upper bound for the easiness factor.",
}


class SrsPage(QWidget):
    def __init__(self, conn: sqlite3.Connection,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.service = SrsService(conn)

        form = QFormLayout()
        self._spinners: dict[str, QDoubleSpinBox] = {}
        for f in fields(SrsParams):
            spin = QDoubleSpinBox()
            spin.setDecimals(2)
            spin.setRange(0.05, 2000.0)
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
        params = SrsParams(**{n: s.value() for n, s in self._spinners.items()})
        self.service.set_params(params)
        self.status.setText("Saved.")
