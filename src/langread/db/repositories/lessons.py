"""Repository for lessons (requirements §4.2)."""

from __future__ import annotations

import sqlite3

from langread.db.connection import transaction, utcnow_iso
from langread.models import Lesson

LESSON_STATUSES = ("draft", "complete", "incomplete")


class LessonsRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def _row_to_lesson(self, row: sqlite3.Row) -> Lesson:
        return Lesson(
            id=row["id"],
            topic_id=row["topic_id"],
            order_index=row["order_index"],
            title=row["title"],
            status=row["status"],
            audio_path=row["audio_path"],
            created_at=row["created_at"],
            last_reviewed_at=row["last_reviewed_at"],
            review_count=row["review_count"],
        )

    def create(self, topic_id: int, title: str | None = None,
               status: str = "draft") -> Lesson:
        if status not in LESSON_STATUSES:
            raise ValueError(f"invalid lesson status: {status}")
        with transaction(self.conn):
            row = self.conn.execute(
                "SELECT COALESCE(MAX(order_index), 0) + 1 FROM lessons WHERE topic_id = ?",
                (topic_id,),
            ).fetchone()
            cur = self.conn.execute(
                "INSERT INTO lessons (topic_id, order_index, title, status, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (topic_id, row[0], title, status, utcnow_iso()),
            )
        lesson = self.get(cur.lastrowid)
        assert lesson is not None  # just inserted
        return lesson

    def get(self, lesson_id: int) -> Lesson | None:
        row = self.conn.execute(
            "SELECT * FROM lessons WHERE id = ?", (lesson_id,)
        ).fetchone()
        return self._row_to_lesson(row) if row else None

    def list_for_topic(self, topic_id: int) -> list[Lesson]:
        rows = self.conn.execute(
            "SELECT * FROM lessons WHERE topic_id = ? ORDER BY order_index, id",
            (topic_id,),
        ).fetchall()
        return [self._row_to_lesson(r) for r in rows]

    def list_by_status(self, status: str) -> list[Lesson]:
        rows = self.conn.execute(
            "SELECT * FROM lessons WHERE status = ? ORDER BY id", (status,)
        ).fetchall()
        return [self._row_to_lesson(r) for r in rows]

    def list_all(self) -> list[Lesson]:
        rows = self.conn.execute(
            "SELECT * FROM lessons ORDER BY topic_id, order_index, id"
        ).fetchall()
        return [self._row_to_lesson(r) for r in rows]

    def set_status(self, lesson_id: int, status: str) -> None:
        if status not in LESSON_STATUSES:
            raise ValueError(f"invalid lesson status: {status}")
        with transaction(self.conn):
            self.conn.execute(
                "UPDATE lessons SET status = ? WHERE id = ?", (status, lesson_id)
            )

    def set_audio_path(self, lesson_id: int, audio_path: str) -> None:
        with transaction(self.conn):
            self.conn.execute(
                "UPDATE lessons SET audio_path = ? WHERE id = ?", (audio_path, lesson_id)
            )

    def mark_reviewed(self, lesson_id: int, reviewed_at: str | None = None) -> None:
        """Record a completed review: timestamp + review_count (schema v2)."""
        with transaction(self.conn):
            self.conn.execute(
                "UPDATE lessons SET last_reviewed_at = ?, "
                "review_count = review_count + 1 WHERE id = ?",
                (reviewed_at or utcnow_iso(), lesson_id),
            )

    def delete(self, lesson_id: int) -> None:
        """Delete a lesson (sentences/lesson_words cascade via FK)."""
        with transaction(self.conn):
            self.conn.execute("DELETE FROM lessons WHERE id = ?", (lesson_id,))

    def lesson_words(self, lesson_id: int) -> list[tuple[int, int, str]]:
        """Rows of (lesson_id, word_id, role) for the lesson."""
        rows = self.conn.execute(
            "SELECT lesson_id, word_id, role FROM lesson_words WHERE lesson_id = ? "
            "ORDER BY word_id",
            (lesson_id,),
        ).fetchall()
        return [(r[0], r[1], r[2]) for r in rows]

    def add_lesson_word(self, lesson_id: int, word_id: int, role: str) -> None:
        if role not in ("new", "review"):
            raise ValueError(f"invalid lesson_words role: {role}")
        with transaction(self.conn):
            self.conn.execute(
                "INSERT OR IGNORE INTO lesson_words (lesson_id, word_id, role) "
                "VALUES (?, ?, ?)",
                (lesson_id, word_id, role),
            )

    def add_appearance(self, lesson_id: int, word_id: int,
                       para_index: int) -> None:
        """Record an actual appearance of a learned word in one paragraph
        (schema v4; idempotent)."""
        with transaction(self.conn):
            self.conn.execute(
                "INSERT OR IGNORE INTO word_appearances "
                "(word_id, lesson_id, para_index) VALUES (?, ?, ?)",
                (word_id, lesson_id, para_index),
            )

    def appearances_for_lesson(self, lesson_id: int) -> list[tuple[int, int]]:
        """Rows of (word_id, para_index) for the lesson, paragraph order."""
        rows = self.conn.execute(
            "SELECT word_id, para_index FROM word_appearances "
            "WHERE lesson_id = ? ORDER BY para_index, word_id",
            (lesson_id,),
        ).fetchall()
        return [(r[0], r[1]) for r in rows]

    def next_lesson_no(self) -> int:
        """The lesson number the NEXT created lesson will get (global
        sequence = lessons.id; the lesson-frequency SRS clock)."""
        row = self.conn.execute(
            "SELECT COALESCE(MAX(id), 0) FROM lessons"
        ).fetchone()
        return int(row[0]) + 1
