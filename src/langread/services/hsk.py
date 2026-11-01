"""Loading of the bundled HSK 1–6 vocabulary dataset (D-7).

Data source: complete-hsk-vocabulary (MIT, https://github.com/drkameleon/
complete-hsk-vocabulary), old HSK standard, exclusive per-level wordlists,
normalized into resources/hsk/hsk.csv by scripts/build_hsk_csv.py.
Imported once into the hsk_words table on first use.
"""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

from langread.app_config import resource_dir
from langread.db.repositories import HskRepo, SettingsRepo

HSK_CSV = resource_dir() / "hsk" / "hsk.csv"
IMPORTED_KEY = "hsk.imported"


def load_hsk_rows(path: Path = HSK_CSV) -> list[tuple[str, str | None, str | None, int]]:
    """Read (text, pinyin, definition, level) rows from the bundled CSV."""
    rows: list[tuple[str, str | None, str | None, int]] = []
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        if header != ["level", "text", "pinyin", "definition"]:
            raise ValueError(f"unexpected HSK CSV header: {header!r}")
        for level, text, pinyin, definition in reader:
            rows.append((text, pinyin or None, definition or None, int(level)))
    return rows


class HskService:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self.repo = HskRepo(conn)
        self.settings = SettingsRepo(conn)

    def import_if_needed(self) -> int:
        """Import the bundled dataset on first use; returns rows inserted."""
        if self.settings.get(IMPORTED_KEY):
            return 0
        return self.import_bundled()

    def import_bundled(self) -> int:
        """(Re)import the bundled dataset; idempotent. Returns rows inserted."""
        inserted = self.repo.import_rows(load_hsk_rows())
        self.settings.set(IMPORTED_KEY, True)
        return inserted
