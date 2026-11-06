"""Repository for sentences (requirements §4.3).

A sentence's segmentation is stored as a JSON array of word tokens and is
decoded/encoded here so callers always work with plain lists.
"""

from __future__ import annotations

import json
import sqlite3

from langread.db.connection import transaction
from langread.models import Sentence


class SentencesRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def _row_to_sentence(self, row: sqlite3.Row) -> Sentence:
        return Sentence(
            id=row["id"],
            lesson_id=row["lesson_id"],
            para_index=row["para_index"],
            sent_index=row["sent_index"],
            text=row["text"],
            segmentation=json.loads(row["segmentation"]),
            translation=row["translation"],
        )

    def replace_for_lesson(self, lesson_id: int,
                           sentences: list[Sentence]) -> list[Sentence]:
        """Atomically replace all sentences of a lesson.

        Sentence `id`s in the input are ignored; the stored rows get new ids.
        Returns the stored sentences (with ids), in order.
        """
        with transaction(self.conn):
            self.conn.execute(
                "DELETE FROM sentences WHERE lesson_id = ?", (lesson_id,)
            )
            stored: list[Sentence] = []
            for i, s in enumerate(sentences):
                seg = s.segmentation if s.segmentation else list(s.text)
                cur = self.conn.execute(
                    "INSERT INTO sentences "
                    "(lesson_id, para_index, sent_index, text, segmentation, translation) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        lesson_id,
                        s.para_index,
                        s.sent_index,
                        s.text,
                        json.dumps(seg, ensure_ascii=False),
                        s.translation,
                    ),
                )
                stored.append(
                    Sentence(
                        id=cur.lastrowid,
                        lesson_id=lesson_id,
                        para_index=s.para_index,
                        sent_index=s.sent_index,
                        text=s.text,
                        segmentation=seg,
                        translation=s.translation,
                    )
                )
        return stored

    def list_for_lesson(self, lesson_id: int) -> list[Sentence]:
        rows = self.conn.execute(
            "SELECT * FROM sentences WHERE lesson_id = ? "
            "ORDER BY para_index, sent_index, id",
            (lesson_id,),
        ).fetchall()
        return [self._row_to_sentence(r) for r in rows]

    def clear_translations(self, lesson_id: int) -> None:
        """Set translation = NULL for every sentence of a lesson.

        Used before re-translating a whole lesson ("Regenerate translation").
        """
        with transaction(self.conn):
            self.conn.execute(
                "UPDATE sentences SET translation = NULL WHERE lesson_id = ?",
                (lesson_id,),
            )

    def count_for_lesson(self, lesson_id: int) -> int:
        row = self.conn.execute(
            "SELECT COUNT(*) FROM sentences WHERE lesson_id = ?", (lesson_id,)
        ).fetchone()
        return row[0]

    def update(self, sentence_id: int, text: str | None = None,
               segmentation: list[str] | None = None,
               translation: str | None = None) -> None:
        """Update selected fields of one sentence (hand-editing, D-6)."""
        with transaction(self.conn):
            if text is not None:
                self.conn.execute(
                    "UPDATE sentences SET text = ? WHERE id = ?", (text, sentence_id)
                )
            if segmentation is not None:
                self.conn.execute(
                    "UPDATE sentences SET segmentation = ? WHERE id = ?",
                    (json.dumps(segmentation, ensure_ascii=False), sentence_id),
                )
            if translation is not None:
                self.conn.execute(
                    "UPDATE sentences SET translation = ? WHERE id = ?",
                    (translation, sentence_id),
                )
