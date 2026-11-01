"""Repository for the bundled HSK reference vocabulary (requirements §4.4, §5.5)."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable

from langread.db.connection import transaction
from langread.models import HskWord

HSK_APP_STATES = ("unused", "new", "basic", "learned")


class HskRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def _row_to_hsk(self, row: sqlite3.Row) -> HskWord:
        return HskWord(
            id=row["id"],
            text=row["text"],
            pinyin=row["pinyin"],
            definition=row["definition"],
            level=row["level"],
            app_state=row["app_state"],
        )

    def import_rows(self, rows: Iterable[tuple[str, str | None, str | None, int]]) -> int:
        """Bulk-import (text, pinyin, definition, level) rows; idempotent.

        Returns the number of newly inserted rows.
        """
        inserted = 0
        with transaction(self.conn):
            for text, pinyin, definition, level in rows:
                cur = self.conn.execute(
                    "INSERT OR IGNORE INTO hsk_words (text, pinyin, definition, level) "
                    "VALUES (?, ?, ?, ?)",
                    (text, pinyin, definition, level),
                )
                inserted += cur.rowcount
        return inserted

    def count(self, level: int | None = None) -> int:
        if level is None:
            row = self.conn.execute("SELECT COUNT(*) FROM hsk_words").fetchone()
        else:
            row = self.conn.execute(
                "SELECT COUNT(*) FROM hsk_words WHERE level = ?", (level,)
            ).fetchone()
        return row[0]

    def counts_by_level(self) -> dict[int, int]:
        rows = self.conn.execute(
            "SELECT level, COUNT(*) AS n FROM hsk_words GROUP BY level ORDER BY level"
        ).fetchall()
        return {r["level"]: r["n"] for r in rows}

    def list_level(self, level: int, app_state: str | None = None,
                   limit: int | None = None, offset: int = 0) -> list[HskWord]:
        """List a level's words in stored (list) order, optionally filtered."""
        if not 1 <= level <= 6:
            raise ValueError(f"invalid HSK level: {level}")
        sql = "SELECT * FROM hsk_words WHERE level = ?"
        params: list = [level]
        if app_state is not None:
            if app_state not in HSK_APP_STATES:
                raise ValueError(f"invalid app_state: {app_state}")
            sql += " AND app_state = ?"
            params.append(app_state)
        sql += " ORDER BY id LIMIT ? OFFSET ?"
        params.extend([limit if limit is not None else -1, offset])
        rows = self.conn.execute(sql, params).fetchall()
        return [self._row_to_hsk(r) for r in rows]

    def list_all(self) -> list[HskWord]:
        """All HSK words (used to build the segmentation dictionary)."""
        rows = self.conn.execute(
            "SELECT * FROM hsk_words ORDER BY level, id"
        ).fetchall()
        return [self._row_to_hsk(r) for r in rows]

    def find_by_text(self, text: str) -> list[HskWord]:
        rows = self.conn.execute(
            "SELECT * FROM hsk_words WHERE text = ? ORDER BY level", (text,)
        ).fetchall()
        return [self._row_to_hsk(r) for r in rows]

    def set_app_state(self, hsk_word_id: int, app_state: str) -> None:
        if app_state not in HSK_APP_STATES:
            raise ValueError(f"invalid app_state: {app_state}")
        with transaction(self.conn):
            self.conn.execute(
                "UPDATE hsk_words SET app_state = ? WHERE id = ?",
                (app_state, hsk_word_id),
            )
