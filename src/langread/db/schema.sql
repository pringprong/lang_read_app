-- LangRead database schema, version 1.
-- Applied atomically by langread.db.connection.migrate().

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
    status           TEXT NOT NULL DEFAULT 'draft'
                     CHECK (status IN ('draft', 'complete', 'incomplete')),
    audio_path       TEXT,
    created_at       TEXT NOT NULL,
    last_reviewed_at TEXT
);
CREATE INDEX idx_lessons_topic ON lessons(topic_id, order_index);
CREATE INDEX idx_lessons_status ON lessons(status);

CREATE TABLE sentences (
    id           INTEGER PRIMARY KEY,
    lesson_id    INTEGER NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
    para_index   INTEGER NOT NULL,
    sent_index   INTEGER NOT NULL,
    text         TEXT NOT NULL,
    segmentation TEXT NOT NULL,        -- JSON array of word tokens
    translation  TEXT
);
CREATE INDEX idx_sentences_lesson ON sentences(lesson_id, para_index, sent_index);

CREATE TABLE hsk_words (
    id         INTEGER PRIMARY KEY,
    text       TEXT NOT NULL,
    pinyin     TEXT,
    definition TEXT,
    level      INTEGER NOT NULL CHECK (level BETWEEN 1 AND 6),
    app_state  TEXT NOT NULL DEFAULT 'unused'
               CHECK (app_state IN ('unused', 'new', 'basic', 'learned')),
    UNIQUE (text, level)
);
CREATE INDEX idx_hsk_level ON hsk_words(level, app_state);

CREATE TABLE words (
    id            INTEGER PRIMARY KEY,
    text          TEXT NOT NULL UNIQUE,          -- simplified Chinese, no spaces
    pinyin        TEXT,
    definition    TEXT,
    list_state    TEXT NOT NULL CHECK (list_state IN ('new', 'learned', 'basic')),
    hsk_word_id   INTEGER REFERENCES hsk_words(id),
    source        TEXT CHECK (source IN
                  ('paste', 'manual', 'lesson', 'basic', 'hsk')),
    added_at      TEXT NOT NULL,
    -- SRS fields, meaningful when list_state = 'learned':
    ease            REAL NOT NULL DEFAULT 2.5,
    interval_days   REAL,
    due_at          TEXT,
    reps            INTEGER NOT NULL DEFAULT 0,
    lapses          INTEGER NOT NULL DEFAULT 0,
    last_rated_at   TEXT
);
CREATE INDEX idx_words_state ON words(list_state, added_at);
CREATE INDEX idx_words_due ON words(list_state, due_at);

CREATE TABLE word_topics (
    word_id  INTEGER NOT NULL REFERENCES words(id) ON DELETE CASCADE,
    topic_id INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    PRIMARY KEY (word_id, topic_id)
);

CREATE TABLE lesson_words (
    lesson_id INTEGER NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
    word_id   INTEGER NOT NULL REFERENCES words(id) ON DELETE CASCADE,
    role      TEXT NOT NULL CHECK (role IN ('new', 'review')),
    PRIMARY KEY (lesson_id, word_id)
);
CREATE INDEX idx_lesson_words_word ON lesson_words(word_id);

CREATE TABLE review_events (
    id          INTEGER PRIMARY KEY,
    lesson_id   INTEGER NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
    word_id     INTEGER REFERENCES words(id) ON DELETE CASCADE,
    rating      TEXT CHECK (rating IN ('difficult', 'easy', 'standard', 'unchanged')),
    reviewed_at TEXT NOT NULL,
    device      TEXT NOT NULL CHECK (device IN ('desktop', 'android'))
);
CREATE INDEX idx_review_events_time ON review_events(reviewed_at);

CREATE TABLE settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL                  -- JSON
);

CREATE TABLE prompt_templates (
    name       TEXT PRIMARY KEY,
    template   TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
