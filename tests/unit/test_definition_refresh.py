"""Definition refresh service tests (plan §5) + schema v3 migration."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from langread.db import connect
from langread.db.repositories import HskRepo, TemplatesRepo, WordsRepo
from langread.services.definition_refresh import DefinitionRefreshService
from langread.services.dictionary import DictEntry

from tests.unit.test_translation import StubLlm


class FakeDictionary:
    """DictionaryService stand-in with a fixed entry table."""

    def __init__(self, entries: dict[str, tuple[str | None, str]]):
        self.entries = {
            word: DictEntry(headword=word, pinyin=pinyin, definition=definition)
            for word, (pinyin, definition) in entries.items()
        }

    def lookup(self, word):
        return self.entries.get(word)


@pytest.fixture()
def conn(tmp_path):
    conn = connect(tmp_path / "test.db")
    TemplatesRepo(conn).seed_defaults()
    yield conn
    conn.close()


@pytest.fixture()
def backups_dir(tmp_path):
    return tmp_path / "backups"


def _make_words(conn) -> None:
    words = WordsRepo(conn)
    # in the dictionary, with a bad old definition
    w, _ = words.get_or_create("厨房", list_state="new", source="manual")
    words.set_translation(w.id, "WRONG", "a wrong old definition", "llm")
    # not in the dictionary, old bad definition
    w, _ = words.get_or_create("咕噜哇", list_state="new", source="manual")
    words.set_translation(w.id, "gūlūwā", "gibberish (wrong)", "llm")


def test_refresh_overwrites_from_dictionary_and_clears_misses(
        conn, tmp_path, backups_dir):
    _make_words(conn)
    dictionary = FakeDictionary({"厨房": ("chú fáng", "kitchen")})
    service = DefinitionRefreshService(
        conn, dictionary, backups_dir=backups_dir
    )
    report = service.refresh()

    words = WordsRepo(conn)
    kitchen = words.get_by_text("厨房")
    assert kitchen.pinyin == "chú fáng"
    assert kitchen.definition == "kitchen"
    assert kitchen.definition_source == "dictionary"
    # miss: definition cleared, pinyin kept
    missing = words.get_by_text("咕噜哇")
    assert missing.definition is None
    assert missing.definition_source is None
    assert missing.pinyin == "gūlūwā"

    assert report.total_words == 2
    assert report.from_dictionary == 1
    assert report.not_found == 1
    assert report.misses == ["咕噜哇"]
    # a backup was taken before writing
    backups = list(backups_dir.glob("pre-refresh-*.db"))
    assert len(backups) == 1
    assert report.backup_path == backups[0]


def test_refresh_dry_run_changes_nothing(conn, tmp_path, backups_dir):
    _make_words(conn)
    dictionary = FakeDictionary({"厨房": ("chú fáng", "kitchen")})
    service = DefinitionRefreshService(
        conn, dictionary, backups_dir=backups_dir
    )
    report = service.refresh(dry_run=True)

    assert report.dry_run is True
    assert report.from_dictionary == 1
    assert report.backup_path is None
    assert not list(backups_dir.glob("pre-refresh-*.db"))
    words = WordsRepo(conn)
    assert words.get_by_text("厨房").definition == "a wrong old definition"
    assert words.get_by_text("咕噜哇").definition == "gibberish (wrong)"


def test_refresh_llm_fills_misses_when_opted_in(conn, tmp_path, backups_dir):
    _make_words(conn)
    dictionary = FakeDictionary({"厨房": ("chú fáng", "kitchen")})
    llm = StubLlm(word_result={"pinyin": "gū lū wā", "definition": "gibberish"})
    service = DefinitionRefreshService(
        conn, dictionary, llm=llm, backups_dir=backups_dir, llm_delay=0.0
    )
    report = service.refresh(use_llm=True)

    words = WordsRepo(conn)
    filled = words.get_by_text("咕噜哇")
    assert filled.definition == "gibberish"
    assert filled.definition_source == "llm"
    assert report.from_llm == 1
    assert report.not_found == 0


def test_refresh_updates_hsk_words_when_included(conn, tmp_path, backups_dir):
    _make_words(conn)
    HskRepo(conn).import_rows(
        [("厨房", "chu fang", "old kitchen gloss", 4),
         ("咕噜哇", "gūlūwā", "gibberish", 6)]
    )
    dictionary = FakeDictionary({"厨房": ("chú fáng", "kitchen")})
    service = DefinitionRefreshService(
        conn, dictionary, backups_dir=backups_dir
    )
    report = service.refresh(include_hsk=True)

    hsk = HskRepo(conn)
    entry = hsk.find_by_text("厨房")[0]
    assert entry.pinyin == "chú fáng"
    assert entry.definition == "kitchen"
    unchanged = hsk.find_by_text("咕噜哇")[0]
    assert unchanged.definition == "gibberish"  # dictionary miss → kept
    assert report.hsk_total == 2
    assert report.hsk_refreshed == 1


def test_refresh_without_a_dictionary_clears_everything(
        conn, tmp_path, backups_dir):
    _make_words(conn)
    service = DefinitionRefreshService(
        conn, FakeDictionary({}), backups_dir=backups_dir
    )
    report = service.refresh()
    words = WordsRepo(conn)
    assert words.get_by_text("厨房").definition is None
    assert words.get_by_text("咕噜哇").definition is None
    assert report.not_found == 2
    assert report.misses == ["厨房", "咕噜哇"]


# ---- schema v3 migration ----


def test_schema_v3_adds_definition_source_column(tmp_path):
    """A database created at v2 (before the column) migrates to v3."""
    from langread.db.connection import _SCHEMA_FILE

    old_schema = "\n".join(
        line
        for line in _SCHEMA_FILE.read_text(encoding="utf-8").splitlines()
        if "definition_source" not in line
        and "'dictionary', 'llm', 'hsk', 'manual'" not in line
    )
    db = tmp_path / "old-v2.db"
    legacy = sqlite3.connect(db)
    legacy.executescript(old_schema)
    legacy.execute(
        "CREATE TABLE schema_migrations "
        "(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
    )
    legacy.execute(
        "INSERT INTO schema_migrations (version, applied_at) VALUES "
        "(1, '2026-01-01'), (2, '2026-01-02')"
    )
    legacy.commit()
    legacy.close()

    conn = connect(db)  # applies pending migrations
    try:
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(words)")}
        assert "definition_source" in columns
        versions = {
            row["version"]
            for row in conn.execute("SELECT version FROM schema_migrations")
        }
        assert {1, 2, 3} <= versions

        words = WordsRepo(conn)
        word, _ = words.get_or_create("厨房", list_state="new", source="manual")
        words.set_translation(word.id, "chú fáng", "kitchen", "dictionary")
        word = words.get(word.id)
        assert word.definition_source == "dictionary"

        with pytest.raises(ValueError):
            words.set_translation(word.id, "chú fáng", "kitchen", "bogus")
    finally:
        conn.close()
