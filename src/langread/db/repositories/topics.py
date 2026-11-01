"""Repository for topics (requirements §4.1, §13)."""

from __future__ import annotations

import sqlite3

from langread.db.connection import transaction, utcnow_iso
from langread.models import Topic


class TopicNotEmptyError(Exception):
    """Raised when deleting a topic that still contains lessons (D-9)."""


class TopicsRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def _row_to_topic(self, row: sqlite3.Row) -> Topic:
        return Topic(
            id=row["id"],
            name=row["name"],
            order_index=row["order_index"],
            created_at=row["created_at"],
        )

    def create(self, name: str) -> Topic:
        with transaction(self.conn):
            row = self.conn.execute(
                "SELECT COALESCE(MAX(order_index), 0) + 1 FROM topics"
            ).fetchone()
            cur = self.conn.execute(
                "INSERT INTO topics (name, order_index, created_at) VALUES (?, ?, ?)",
                (name, row[0], utcnow_iso()),
            )
        topic = self.get(cur.lastrowid)
        assert topic is not None  # just inserted
        return topic

    def get(self, topic_id: int) -> Topic | None:
        row = self.conn.execute(
            "SELECT * FROM topics WHERE id = ?", (topic_id,)
        ).fetchone()
        return self._row_to_topic(row) if row else None

    def get_by_name(self, name: str) -> Topic | None:
        row = self.conn.execute(
            "SELECT * FROM topics WHERE name = ?", (name,)
        ).fetchone()
        return self._row_to_topic(row) if row else None

    def list_all(self) -> list[Topic]:
        rows = self.conn.execute(
            "SELECT * FROM topics ORDER BY order_index, id"
        ).fetchall()
        return [self._row_to_topic(r) for r in rows]

    def rename(self, topic_id: int, name: str) -> None:
        with transaction(self.conn):
            self.conn.execute(
                "UPDATE topics SET name = ? WHERE id = ?", (name, topic_id)
            )

    def lesson_count(self, topic_id: int) -> int:
        row = self.conn.execute(
            "SELECT COUNT(*) FROM lessons WHERE topic_id = ?", (topic_id,)
        ).fetchone()
        return row[0]

    def delete(self, topic_id: int) -> None:
        """Delete a topic. Blocked while it contains lessons (D-9)."""
        with transaction(self.conn):
            count = self.conn.execute(
                "SELECT COUNT(*) FROM lessons WHERE topic_id = ?", (topic_id,)
            ).fetchone()[0]
            if count:
                raise TopicNotEmptyError(
                    f"Topic still contains {count} lesson(s); delete or move them first."
                )
            self.conn.execute("DELETE FROM topics WHERE id = ?", (topic_id,))
