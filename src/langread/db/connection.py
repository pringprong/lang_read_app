"""SQLite connection handling and schema migrations."""

from __future__ import annotations

import datetime as dt
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

SCHEMA_VERSION = 3

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
