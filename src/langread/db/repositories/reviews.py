"""Repository for the append-only review-events log (requirements §4, §10).

Review events are the source for SRS updates and for Android→desktop sync
reconciliation; SRS fields on `words` are a materialized current state.
"""

from __future__ import annotations

import sqlite3

from langread.db.connection import transaction, utcnow_iso
from langread.models import ReviewEvent

RATINGS = ("difficult", "easy", "standard", "unchanged")
DEVICES = ("desktop", "android")


class ReviewsRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def _row_to_event(self, row: sqlite3.Row) -> ReviewEvent:
        return ReviewEvent(
            id=row["id"],
            lesson_id=row["lesson_id"],
            word_id=row["word_id"],
            rating=row["rating"],
            reviewed_at=row["reviewed_at"],
            device=row["device"],
        )

    def add(self, lesson_id: int, word_id: int | None = None,
            rating: str | None = None, device: str = "desktop",
            reviewed_at: str | None = None) -> ReviewEvent:
        if rating is not None and rating not in RATINGS:
            raise ValueError(f"invalid rating: {rating}")
        if device not in DEVICES:
            raise ValueError(f"invalid device: {device}")
        with transaction(self.conn):
            cur = self.conn.execute(
                "INSERT INTO review_events "
                "(lesson_id, word_id, rating, reviewed_at, device) VALUES (?, ?, ?, ?, ?)",
                (lesson_id, word_id, rating, reviewed_at or utcnow_iso(), device),
            )
        event = self.get(cur.lastrowid)
        assert event is not None  # just inserted
        return event

    def get(self, event_id: int) -> ReviewEvent | None:
        row = self.conn.execute(
            "SELECT * FROM review_events WHERE id = ?", (event_id,)
        ).fetchone()
        return self._row_to_event(row) if row else None

    def events_for_lesson(self, lesson_id: int) -> list[ReviewEvent]:
        rows = self.conn.execute(
            "SELECT * FROM review_events WHERE lesson_id = ? ORDER BY id",
            (lesson_id,),
        ).fetchall()
        return [self._row_to_event(r) for r in rows]

    def events_since(self, since_iso: str,
                     device: str | None = None) -> list[ReviewEvent]:
        """Events at or after a timestamp (sync export selection, §10)."""
        sql = "SELECT * FROM review_events WHERE reviewed_at >= ?"
        params: list = [since_iso]
        if device is not None:
            if device not in DEVICES:
                raise ValueError(f"invalid device: {device}")
            sql += " AND device = ?"
            params.append(device)
        sql += " ORDER BY reviewed_at, id"
        rows = self.conn.execute(sql, params).fetchall()
        return [self._row_to_event(r) for r in rows]
