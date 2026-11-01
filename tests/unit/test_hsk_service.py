"""M5 tests: HSK dataset loading and service."""

from __future__ import annotations

import pytest

from langread.db import connect
from langread.db.repositories import HskRepo
from langread.services.hsk import HSK_CSV, HskService, load_hsk_rows


@pytest.fixture(scope="module")
def rows():
    return load_hsk_rows()


def test_bundled_csv_shape(rows):
    assert len(rows) == 4991  # official 5,000 minus cross-level duplicates
    levels = {}
    for text, _pinyin, _definition, level in rows:
        levels[level] = levels.get(level, 0) + 1
    assert levels[1] == 150
    assert levels[6] == 2500


def test_bundled_csv_known_entries(rows):
    by_text = {text: (level, pinyin, definition)
               for text, pinyin, definition, level in rows}
    china = by_text["中国"]
    assert china[0] == 1
    assert "China" in (china[2] or "")


def test_hsk_import_if_needed(tmp_path):
    conn = connect(tmp_path / "test.db")
    try:
        service = HskService(conn)
        inserted = service.import_if_needed()
        assert inserted == 4991
        # second call is a no-op
        assert service.import_if_needed() == 0
        counts = HskRepo(conn).counts_by_level()
        assert counts[1] == 150
        assert counts[6] == 2500
    finally:
        conn.close()


def test_hsk_csv_header_validation(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("a,b,c,d\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_hsk_rows(bad)
