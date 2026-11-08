"""SQLite connection handling and schema migrations."""

from __future__ import annotations

import datetime as dt
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

SCHEMA_VERSION = 4

_SCHEMA_FILE = Path(__file__).parent / "schema.sql"


def utcnow_iso() -> str:
    """Current UTC time as a sortable ISO-8601 string."""
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def connect(db_path: Path | str) -> sqlite3.Connection:
    """Open (and migrate) the database.

    The connection is in autocommit mode; use the `transaction` context
    manager for atomic multi-statement work.
    """
    conn = sqlite3.connect(str(db_path), isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    migrate(conn)
    return conn


def migrate(conn: sqlite3.Connection) -> None:
    """Apply pending schema migrations.

    v1: the initial schema (schema.sql).
    v2: `lessons.review_count` (times-reviewed column in the lesson list).
    v3: `words.definition_source` (where each definition came from).
    v4: lesson-frequency SRS — `word_appearances` table, `words.first_learned_lesson_id`
        / `words.last_seen_lesson_id`, and the day-based `words.interval_days` /
        `words.due_at` columns dropped.
    """
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        "version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
    )
    applied = {row["version"] for row in conn.execute("SELECT version FROM schema_migrations")}
    if 1 not in applied:
        conn.executescript(_SCHEMA_FILE.read_text(encoding="utf-8"))
        conn.execute(
            "INSERT INTO schema_migrations (version, applied_at) VALUES (1, ?)",
            (utcnow_iso(),),
        )
    if 2 not in applied:
        # fresh databases already have the column (schema.sql is kept in
        # sync); databases created at v1 need the ALTER
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(lessons)")}
        if "review_count" not in columns:
            conn.execute(
                "ALTER TABLE lessons ADD COLUMN review_count INTEGER NOT NULL DEFAULT 0"
            )
        conn.execute(
            "INSERT INTO schema_migrations (version, applied_at) VALUES (2, ?)",
            (utcnow_iso(),),
        )
    if 3 not in applied:
        # v3: words.definition_source (NULL for all existing rows)
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(words)")}
        if "definition_source" not in columns:
            conn.execute(
                "ALTER TABLE words ADD COLUMN definition_source TEXT "
                "CHECK (definition_source IN "
                "('dictionary', 'llm', 'hsk', 'manual'))"
            )
        conn.execute(
            "INSERT INTO schema_migrations (version, applied_at) VALUES (3, ?)",
            (utcnow_iso(),),
        )
    if 4 not in applied:
        # v4: lesson-frequency SRS (plan 20261108_lesson_based_SRS_update.md)
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(words)")}
        if "first_learned_lesson_id" not in columns:
            conn.execute(
                "ALTER TABLE words ADD COLUMN first_learned_lesson_id INTEGER"
            )
        if "last_seen_lesson_id" not in columns:
            conn.execute(
                "ALTER TABLE words ADD COLUMN last_seen_lesson_id INTEGER"
            )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS word_appearances ("
            "word_id    INTEGER NOT NULL REFERENCES words(id)   ON DELETE CASCADE, "
            "lesson_id  INTEGER NOT NULL REFERENCES lessons(id) ON DELETE CASCADE, "
            "para_index INTEGER NOT NULL, "
            "PRIMARY KEY (word_id, lesson_id, para_index))"
        )
        # drop the day-based SRS columns (nothing of value in the production
        # database: it has no lessons / learned words at upgrade time).
        # SQLite cannot DROP COLUMN while an index still references it, so any
        # index on the dropped columns goes first (v3 had idx_words_due).
        for column in ("interval_days", "due_at"):
            stale_indexes = conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'index' AND tbl_name = 'words' "
                "AND sql LIKE '%' || ? || '%'",
                (column,),
            ).fetchall()
            for index in stale_indexes:
                conn.execute(f'DROP INDEX IF EXISTS "{index["name"]}"')
            if column in columns:
                conn.execute(f"ALTER TABLE words DROP COLUMN {column}")
        _backfill_lesson_srs(conn)
        conn.execute(
            "INSERT INTO schema_migrations (version, applied_at) VALUES (4, ?)",
            (utcnow_iso(),),
        )


def _backfill_lesson_srs(conn: sqlite3.Connection) -> None:
    """Populate word_appearances / lesson-id columns from existing data.

    For the production database (0 lessons, 0 learned words) this is a no-op;
    it exists so test databases and future reuse upgrade correctly.
    """
    learned = {
        row["text"]: row["id"]
        for row in conn.execute(
            "SELECT id, text FROM words WHERE list_state = 'learned'"
        )
    }
    if not learned:
        return
    # rebuild actual appearances from the stored sentence segmentations
    for lesson_id, para_index, segmentation in conn.execute(
        "SELECT lesson_id, para_index, segmentation FROM sentences "
        "ORDER BY lesson_id, para_index, sent_index"
    ):
        try:
            tokens = json.loads(segmentation)
        except (TypeError, ValueError):
            continue
        for text in set(tokens):
            word_id = learned.get(text)
            if word_id is not None:
                conn.execute(
                    "INSERT OR IGNORE INTO word_appearances "
                    "(word_id, lesson_id, para_index) VALUES (?, ?, ?)",
                    (word_id, lesson_id, para_index),
                )
    conn.execute(
        "UPDATE words SET "
        "first_learned_lesson_id = COALESCE("
        "  (SELECT MIN(lw.lesson_id) FROM lesson_words lw "
        "   WHERE lw.word_id = words.id AND lw.role = 'new'),"
        "  (SELECT MIN(a.lesson_id) FROM word_appearances a "
        "   WHERE a.word_id = words.id)), "
        "last_seen_lesson_id = COALESCE("
        "  (SELECT MAX(a.lesson_id) FROM word_appearances a "
        "   WHERE a.word_id = words.id),"
        "  (SELECT MIN(lw.lesson_id) FROM lesson_words lw "
        "   WHERE lw.word_id = words.id AND lw.role = 'new'),"
        "  (SELECT MIN(lw.lesson_id) FROM lesson_words lw "
        "   WHERE lw.word_id = words.id)) "
        "WHERE list_state = 'learned'"
    )


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Run a block inside a single atomic transaction."""
    conn.execute("BEGIN")
    try:
        yield conn
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
