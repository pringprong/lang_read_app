"""Repository for words on the New / Learned / Basic lists (requirements §4.4)."""

from __future__ import annotations

import sqlite3

from langread.db.connection import transaction, utcnow_iso
from langread.models import Word

WORD_STATES = ("new", "learned", "basic")
WORD_SOURCES = ("paste", "manual", "lesson", "basic", "hsk")


class WordsRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def _row_to_word(self, row: sqlite3.Row) -> Word:
        return Word(
            id=row["id"],
            text=row["text"],
            pinyin=row["pinyin"],
            definition=row["definition"],
            list_state=row["list_state"],
            hsk_word_id=row["hsk_word_id"],
            source=row["source"],
            added_at=row["added_at"],
            ease=row["ease"],
            interval_days=row["interval_days"],
            due_at=row["due_at"],
            reps=row["reps"],
            lapses=row["lapses"],
            last_rated_at=row["last_rated_at"],
        )

    def get(self, word_id: int) -> Word | None:
        row = self.conn.execute(
            "SELECT * FROM words WHERE id = ?", (word_id,)
        ).fetchone()
        return self._row_to_word(row) if row else None

    def get_by_text(self, text: str) -> Word | None:
        row = self.conn.execute(
            "SELECT * FROM words WHERE text = ?", (text,)
        ).fetchone()
        return self._row_to_word(row) if row else None

    def get_or_create(
        self,
        text: str,
        *,
        list_state: str = "new",
        source: str | None = None,
        pinyin: str | None = None,
        definition: str | None = None,
        hsk_word_id: int | None = None,
    ) -> tuple[Word, bool]:
        """Return (word, created). Existing membership wins (§5.1)."""
        if list_state not in WORD_STATES:
            raise ValueError(f"invalid word state: {list_state}")
        if source is not None and source not in WORD_SOURCES:
            raise ValueError(f"invalid word source: {source}")
        existing = self.get_by_text(text)
        if existing is not None:
            return existing, False
        with transaction(self.conn):
            cur = self.conn.execute(
                "INSERT INTO words "
                "(text, pinyin, definition, list_state, hsk_word_id, source, added_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (text, pinyin, definition, list_state, hsk_word_id, source, utcnow_iso()),
            )
        word = self.get(cur.lastrowid)
        assert word is not None  # just inserted
        return word, True

    def list_by_state(self, state: str) -> list[Word]:
        """All words in a list, oldest-added first (D-11)."""
        if state not in WORD_STATES:
            raise ValueError(f"invalid word state: {state}")
        rows = self.conn.execute(
            "SELECT * FROM words WHERE list_state = ? ORDER BY added_at, id",
            (state,),
        ).fetchall()
        return [self._row_to_word(r) for r in rows]

    def count_by_state(self, state: str) -> int:
        row = self.conn.execute(
            "SELECT COUNT(*) FROM words WHERE list_state = ?", (state,)
        ).fetchone()
        return row[0]

    def move_to_state(self, word_id: int, new_state: str) -> None:
        """Move a word between lists, syncing the linked HSK entry (§4.4)."""
        if new_state not in WORD_STATES:
            raise ValueError(f"invalid word state: {new_state}")
        with transaction(self.conn):
            self.conn.execute(
                "UPDATE words SET list_state = ? WHERE id = ?", (new_state, word_id)
            )
            row = self.conn.execute(
                "SELECT hsk_word_id FROM words WHERE id = ?", (word_id,)
            ).fetchone()
            if row and row["hsk_word_id"] is not None:
                self.conn.execute(
                    "UPDATE hsk_words SET app_state = ? WHERE id = ?",
                    (new_state, row["hsk_word_id"]),
                )

    def set_translation(self, word_id: int, pinyin: str | None,
                        definition: str | None) -> None:
        with transaction(self.conn):
            self.conn.execute(
                "UPDATE words SET pinyin = ?, definition = ? WHERE id = ?",
                (pinyin, definition, word_id),
            )

    def set_srs(self, word_id: int, *, ease: float, interval_days: float | None,
                due_at: str | None, reps: int, lapses: int,
                last_rated_at: str | None) -> None:
        with transaction(self.conn):
            self.conn.execute(
                "UPDATE words SET ease = ?, interval_days = ?, due_at = ?, "
                "reps = ?, lapses = ?, last_rated_at = ? WHERE id = ?",
                (ease, interval_days, due_at, reps, lapses, last_rated_at, word_id),
            )

    def associate_topic(self, word_id: int, topic_id: int) -> None:
        with transaction(self.conn):
            self.conn.execute(
                "INSERT OR IGNORE INTO word_topics (word_id, topic_id) VALUES (?, ?)",
                (word_id, topic_id),
            )

    def topics_for_word(self, word_id: int) -> list:
        rows = self.conn.execute(
            "SELECT t.* FROM topics t JOIN word_topics wt ON wt.topic_id = t.id "
            "WHERE wt.word_id = ? ORDER BY t.order_index",
            (word_id,),
        ).fetchall()
        from langread.models import Topic

        return [
            Topic(id=r["id"], name=r["name"], order_index=r["order_index"],
                  created_at=r["created_at"])
            for r in rows
        ]

    def suggest_new_words(self, topic_id: int | None, limit: int) -> list[Word]:
        """Suggest new words: oldest-added first, topic-associated first (D-11)."""
        sql = (
            "SELECT w.* FROM words w "
            "LEFT JOIN word_topics wt ON wt.word_id = w.id AND wt.topic_id = ? "
            "WHERE w.list_state = 'new' "
            "ORDER BY (wt.topic_id IS NULL), w.added_at, w.id LIMIT ?"
        )
        rows = self.conn.execute(sql, (topic_id, limit)).fetchall()
        return [self._row_to_word(r) for r in rows]

    def due_learned_words(self, topic_id: int | None = None,
                          limit: int | None = None,
                          now_iso: str | None = None) -> list[Word]:
        """Learned words ordered by due date (SRS suggestions, §7.2)."""
        params: list = []
        where = "w.list_state = 'learned' AND w.due_at IS NOT NULL"
        if now_iso is not None:
            where += " AND w.due_at <= ?"
            params.append(now_iso)
        if topic_id is not None:
            join = "LEFT JOIN word_topics wt ON wt.word_id = w.id AND wt.topic_id = ?"
            params.insert(0, topic_id)
            order = "(wt.topic_id IS NULL), w.due_at"
        else:
            join = ""
            order = "w.due_at"
        sql = f"SELECT w.* FROM words w {join} WHERE {where} ORDER BY {order}, w.id"
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)
        rows = self.conn.execute(sql, params).fetchall()
        return [self._row_to_word(r) for r in rows]
