"""Integration tests: schema v3 → v4 migration (lesson-frequency SRS).

Simulates a pre-v4 database (day-based SRS columns, no word_appearances,
no lesson tracking) and verifies `connect()` upgrades it in place.
"""

from __future__ import annotations

import sqlite3

from langread.db import connect

# The parts of the v3 schema the migration touches (subset of schema.sql
# as it was before v4).
_V3_SCHEMA = """
CREATE TABLE topics (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    order_index INTEGER NOT NULL,
    created_at  TEXT NOT NULL
);
CREATE TABLE lessons (
    id               INTEGER PRIMARY KEY,
    topic_id         INTEGER NOT NULL REFERENCES topics(id),
    order_index      INTEGER NOT NULL,
    title            TEXT,
    status           TEXT NOT NULL DEFAULT 'draft',
    audio_path       TEXT,
    created_at       TEXT NOT NULL,
    last_reviewed_at TEXT,
    review_count     INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE hsk_words (
    id         INTEGER PRIMARY KEY,
    text       TEXT NOT NULL,
    pinyin     TEXT,
    definition TEXT,
    level      INTEGER NOT NULL CHECK (level BETWEEN 1 AND 6),
    app_state  TEXT NOT NULL DEFAULT 'unused',
    UNIQUE (text, level)
);
CREATE TABLE words (
    id            INTEGER PRIMARY KEY,
    text          TEXT NOT NULL UNIQUE,
    pinyin        TEXT,
    definition    TEXT,
    list_state    TEXT NOT NULL CHECK (list_state IN ('new', 'learned', 'basic')),
    hsk_word_id   INTEGER REFERENCES hsk_words(id),
    source        TEXT,
    added_at      TEXT NOT NULL,
    definition_source TEXT,
    ease            REAL NOT NULL DEFAULT 2.5,
    interval_days   REAL,
    due_at          TEXT,
    reps            INTEGER NOT NULL DEFAULT 0,
    lapses          INTEGER NOT NULL DEFAULT 0,
    last_rated_at   TEXT
);
CREATE TABLE sentences (
    id           INTEGER PRIMARY KEY,
    lesson_id    INTEGER NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
    para_index   INTEGER NOT NULL,
    sent_index   INTEGER NOT NULL,
    text         TEXT NOT NULL,
    segmentation TEXT NOT NULL,
    translation  TEXT
);
CREATE TABLE word_topics (
    word_id  INTEGER NOT NULL REFERENCES words(id) ON DELETE CASCADE,
    topic_id INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    PRIMARY KEY (word_id, topic_id)
);
CREATE TABLE lesson_words (
    lesson_id INTEGER NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
    word_id   INTEGER NOT NULL REFERENCES words(id) ON DELETE CASCADE,
    role      TEXT NOT NULL,
    PRIMARY KEY (lesson_id, word_id)
);
CREATE TABLE review_events (
    id          INTEGER PRIMARY KEY,
    lesson_id   INTEGER NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
    word_id     INTEGER REFERENCES words(id) ON DELETE CASCADE,
    rating      TEXT,
    reviewed_at TEXT NOT NULL,
    device      TEXT NOT NULL
);
CREATE TABLE settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE prompt_templates (
    name       TEXT PRIMARY KEY,
    template   TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX idx_words_state ON words(list_state, added_at);
CREATE INDEX idx_words_due ON words(list_state, due_at);
"""


def _make_v3_database(path):
    conn = sqlite3.connect(str(path), isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(_V3_SCHEMA)
    conn.execute(
        "CREATE TABLE schema_migrations ("
        "version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
    )
    for version in (1, 2, 3):
        conn.execute(
            "INSERT INTO schema_migrations (version, applied_at) "
            "VALUES (?, '2026-11-01T00:00:00+00:00')",
            (version,),
        )
    # one topic, one lesson, one learned word (introduced in that lesson)
    # + one sentence whose segmentation contains the word
    conn.execute(
        "INSERT INTO topics (id, name, order_index, created_at) "
        "VALUES (1, 'Cooking', 1, '2026-11-01T00:00:00+00:00')"
    )
    conn.execute(
        "INSERT INTO lessons (id, topic_id, order_index, status, created_at) "
        "VALUES (1, 1, 1, 'complete', '2026-11-01T00:00:00+00:00')"
    )
    conn.execute(
        "INSERT INTO words (id, text, list_state, source, added_at, ease, "
        "interval_days, due_at, reps, lapses, last_rated_at) "
        "VALUES (1, '厨房', 'learned', 'manual', "
        "'2026-11-01T00:00:00+00:00', 2.3, 4.0, "
        "'2026-11-05T00:00:00+00:00', 2, 1, '2026-11-01T00:00:00+00:00')"
    )
    conn.execute(
        "INSERT INTO lesson_words (lesson_id, word_id, role) VALUES (1, 1, 'new')"
    )
    conn.execute(
        "INSERT INTO sentences (id, lesson_id, para_index, sent_index, text, "
        "segmentation) VALUES (1, 1, 0, 0, '我们在厨房做饭。', "
        "'[\"我们\", \"在\", \"厨房\", \"做饭\"]')"
    )
    conn.close()


def test_v3_database_upgrades_to_v4(tmp_path):
    db_path = tmp_path / "old.db"
    _make_v3_database(db_path)

    conn = connect(db_path)  # runs migrate() — applies v4
    try:
        # day-based columns are gone, new tracking columns exist
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(words)")}
        assert "interval_days" not in columns
        assert "due_at" not in columns
        assert "first_learned_lesson_id" in columns
        assert "last_seen_lesson_id" in columns
        # word data intact
        row = conn.execute("SELECT * FROM words WHERE id = 1").fetchone()
        assert row["text"] == "厨房"
        assert row["ease"] == 2.3 and row["reps"] == 2 and row["lapses"] == 1
        # backfill: learned in lesson 1 (lesson_words role 'new') and the
        # appearance was rebuilt from the stored sentence segmentation
        assert row["first_learned_lesson_id"] == 1
        assert row["last_seen_lesson_id"] == 1
        appearances = conn.execute(
            "SELECT word_id, lesson_id, para_index FROM word_appearances"
        ).fetchall()
        assert [
            (a["word_id"], a["lesson_id"], a["para_index"]) for a in appearances
        ] == [(1, 1, 0)]
        # migration recorded; reconnecting is a no-op
        versions = {
            row["version"] for row in conn.execute("SELECT version FROM schema_migrations")
        }
        assert versions == {1, 2, 3, 4}
    finally:
        conn.close()
    conn = connect(db_path)
    try:
        versions = {
            row["version"] for row in conn.execute("SELECT version FROM schema_migrations")
        }
        assert versions == {1, 2, 3, 4}
    finally:
        conn.close()


def test_partially_migrated_database_completes_v4(tmp_path):
    """Regression: a v4 migration that CRASHED mid-way (the production bug —
    DROP COLUMN failed because idx_words_due still referenced due_at, so
    version 4 was never recorded). The guarded re-run must complete it."""
    db_path = tmp_path / "partial.db"
    _make_v3_database(db_path)
    # replay exactly the statements that succeeded before the crash
    conn = sqlite3.connect(str(db_path), isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("ALTER TABLE words ADD COLUMN first_learned_lesson_id INTEGER")
    conn.execute("ALTER TABLE words ADD COLUMN last_seen_lesson_id INTEGER")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS word_appearances ("
        "word_id    INTEGER NOT NULL REFERENCES words(id)   ON DELETE CASCADE, "
        "lesson_id  INTEGER NOT NULL REFERENCES lessons(id) ON DELETE CASCADE, "
        "para_index INTEGER NOT NULL, "
        "PRIMARY KEY (word_id, lesson_id, para_index))"
    )
    conn.close()

    conn = connect(db_path)  # migrate() re-runs and completes v4
    try:
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(words)")}
        assert "interval_days" not in columns
        assert "due_at" not in columns
        assert "first_learned_lesson_id" in columns
        # the stale v3 index is gone; the kept one survives
        indexes = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index' "
                "AND tbl_name = 'words'"
            )
        }
        assert "idx_words_due" not in indexes
        assert "idx_words_state" in indexes
        versions = {
            row["version"] for row in conn.execute("SELECT version FROM schema_migrations")
        }
        assert versions == {1, 2, 3, 4}
    finally:
        conn.close()


def test_empty_v3_database_upgrades_cleanly(tmp_path):
    """The production case: 0 lessons, 0 learned words — no-op backfill."""
    db_path = tmp_path / "empty.db"
    _make_v3_database(db_path)
    conn = sqlite3.connect(str(db_path), isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    for table in ("sentences", "lesson_words", "review_events", "words",
                  "lessons", "topics"):
        conn.execute(f"DELETE FROM {table}")
    conn.close()

    conn = connect(db_path)
    try:
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(words)")}
        assert "interval_days" not in columns
        assert "first_learned_lesson_id" in columns
        assert conn.execute(
            "SELECT COUNT(*) FROM word_appearances"
        ).fetchone()[0] == 0
    finally:
        conn.close()
