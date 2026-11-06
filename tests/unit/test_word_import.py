"""M5 tests: word import flows (paste, manual, HSK, list moves)."""

from __future__ import annotations

import pytest

from langread.db import connect
from langread.db.repositories import HskRepo, TopicsRepo, WordsRepo
from langread.services.word_import import WordImportService


@pytest.fixture()
def conn(tmp_path):
    conn = connect(tmp_path / "test.db")
    yield conn
    conn.close()


@pytest.fixture()
def service(conn):
    return WordImportService(conn)


@pytest.fixture()
def words(conn):
    return WordsRepo(conn)


@pytest.fixture()
def hsk(conn):
    return HskRepo(conn)


def test_parse_pasted_text_distinct_in_order(service):
    parsed = service.parse_pasted_text("你好，世界。你好")
    texts = [p.text for p in parsed]
    assert texts == ["你好", "世界"]  # distinct, first-appearance order, no punct


def test_parse_pasted_text_flags_existing_and_hsk(service, words, hsk):
    # use a non-HSK nonsense word: bundled HSK words are already imported
    words.get_or_create("厨房", list_state="new", source="manual")
    hsk.import_rows([("咕噜哇", "gūlūwā", "gibberish", 3)])
    service.segmentation.refresh_dictionary()
    parsed = service.parse_pasted_text("厨房很大，咕噜哇很小。")
    by_text = {p.text: p for p in parsed}
    assert by_text["厨房"].existing is not None
    assert by_text["厨房"].existing.list_state == "new"
    assert by_text["咕噜哇"].hsk is not None
    assert by_text["咕噜哇"].hsk.pinyin == "gūlūwā"
    assert by_text["咕噜哇"].existing is None


def test_import_from_paste_marks_new_and_basic(service, words):
    parsed = service.parse_pasted_text("我喜欢喝茶，也喜欢喝咖啡。")
    new_words = {"喝茶"}
    summary = service.import_from_paste(parsed, new_words)
    assert summary.added_new == 1
    assert summary.added_basic >= 1
    tea = words.get_by_text("喝茶")
    assert tea is not None and tea.list_state == "new"
    coffee = words.get_by_text("咖啡")
    assert coffee is not None and coffee.list_state == "basic"


def test_import_from_paste_existing_membership_wins(service, words):
    words.get_or_create("咖啡", list_state="new", source="manual")
    parsed = service.parse_pasted_text("咖啡")
    summary = service.import_from_paste(parsed, set())
    assert summary.already_known == 1
    assert summary.added_basic == 0
    assert words.get_by_text("咖啡").list_state == "new"  # unchanged


def test_import_from_paste_links_hsk_and_topic(service, words, hsk, conn):
    hsk.import_rows([("咕噜哇", "gūlūwā", "gibberish", 3)])
    service.segmentation.refresh_dictionary()
    topic = TopicsRepo(conn).create("Tech")
    parsed = service.parse_pasted_text("咕噜哇很好")
    summary = service.import_from_paste(parsed, {"咕噜哇"}, topic_id=topic.id)
    assert summary.added_new == 1
    word = words.get_by_text("咕噜哇")
    assert word.hsk_word_id is not None
    assert word.pinyin == "gūlūwā"
    assert word.definition == "gibberish"
    assert [t.name for t in words.topics_for_word(word.id)] == ["Tech"]
    assert hsk.find_by_text("咕噜哇")[0].app_state == "new"


def test_add_manual(service, words):
    word, created = service.add_manual("机场")
    assert created and word.list_state == "new"
    assert word.source == "manual"
    word2, created2 = service.add_manual("机场")
    assert not created2


# ---- offline dictionary fill (definitions plan §4.2) ----

CEDICT_FIXTURE = (
    "廚房 厨房 [chu2 fang2] /kitchen/CL:間|间[jian1]/\n"
    "機場 机场 [ji1 chang3] /airport/airfield/\n"
)


def test_add_manual_fills_from_dictionary(conn, words, monkeypatch, tmp_path):
    path = tmp_path / "cedict.txt"
    path.write_text(CEDICT_FIXTURE, encoding="utf-8")
    monkeypatch.setenv("LANGREAD_CEDICT", str(path))
    service = WordImportService(conn)

    word, _ = service.add_manual("厨房")
    assert word.pinyin == "chú fáng"
    assert word.definition == "kitchen"
    assert word.definition_source == "dictionary"


def test_dictionary_wins_over_hsk_fill(conn, words, hsk, monkeypatch, tmp_path):
    path = tmp_path / "cedict.txt"
    path.write_text(CEDICT_FIXTURE, encoding="utf-8")
    monkeypatch.setenv("LANGREAD_CEDICT", str(path))
    hsk.import_rows([("厨房", "chu fang", "kitchen (HSK gloss)", 4)])
    service = WordImportService(conn)

    word, _ = service.add_manual("厨房")
    # linked to the HSK entry, but the dictionary values won
    assert word.hsk_word_id is not None
    assert word.definition == "kitchen"
    assert word.pinyin == "chú fáng"
    assert word.definition_source == "dictionary"
    assert hsk.find_by_text("厨房")[0].app_state == "new"


def test_add_from_hsk_overridden_by_dictionary(conn, words, hsk, monkeypatch,
                                               tmp_path):
    path = tmp_path / "cedict.txt"
    path.write_text(CEDICT_FIXTURE, encoding="utf-8")
    monkeypatch.setenv("LANGREAD_CEDICT", str(path))
    entry = hsk.import_rows([("厨房", "chu fang", "kitchen (HSK gloss)", 4)])
    assert entry == 1
    service = WordImportService(conn)

    word, created = service.add_from_hsk(hsk.find_by_text("厨房")[0])
    assert created
    assert word.hsk_word_id is not None
    assert word.definition == "kitchen"
    assert word.definition_source == "dictionary"


def test_add_manual_rejects_empty(service):
    with pytest.raises(ValueError):
        service.add_manual("   ")


def test_add_from_hsk(service, words, hsk):
    hsk.import_rows([("咕噜哇", "gūlūwā", "gibberish", 3)])
    entry = hsk.find_by_text("咕噜哇")[0]
    word, created = service.add_from_hsk(entry, target="new")
    assert created
    assert (word.list_state, word.pinyin, word.definition) == (
        "new", "gūlūwā", "gibberish",
    )
    assert word.hsk_word_id == entry.id
    assert hsk.find_by_text("咕噜哇")[0].app_state == "new"
    # adding again is idempotent and does not duplicate
    _, created2 = service.add_from_hsk(entry, target="new")
    assert not created2


def test_add_from_hsk_rejects_bad_target(service, hsk):
    hsk.import_rows([("厨房", None, None, 4)])
    with pytest.raises(ValueError):
        service.add_from_hsk(hsk.find_by_text("厨房")[0], target="learned")


def test_add_from_hsk_existing_word_takes_effect(service, words, hsk):
    """Regression: an HSK word that already exists on another list (e.g.
    created from the lesson-review popup, never linked) must still be
    linked and moved to the target list — not silently ignored."""
    hsk.import_rows([("聊天", "liáo tiān", "to chat", 4)])
    entry = hsk.find_by_text("聊天")[0]
    # the word already exists on the New list, unlinked — the HSK browser
    # still shows it as "unused"
    words.get_or_create("聊天", list_state="new", source="lesson")
    assert entry.app_state == "unused"

    word, created = service.add_from_hsk(entry, target="basic")
    assert not created  # no duplicate row
    word = words.get_by_text("聊天")
    assert words.count_by_state("new") + words.count_by_state("basic") == 1
    assert word.list_state == "basic"  # moved to Basic — action took effect
    assert word.hsk_word_id == entry.id  # linked to the HSK entry
    assert word.pinyin == entry.pinyin and word.definition == entry.definition
    assert hsk.find_by_text("聊天")[0].app_state == "basic"  # synced


def test_add_from_hsk_existing_word_on_target_list(service, words, hsk):
    """A word already on the target list (but unlinked) is linked and the
    HSK entry synced, so it stops showing as "unused"."""
    hsk.import_rows([("东西", "dōng xi", "thing", 2)])
    entry = hsk.find_by_text("东西")[0]
    words.get_or_create("东西", list_state="basic", source="lesson")

    word, created = service.add_from_hsk(entry, target="basic")
    assert not created
    word = words.get_by_text("东西")
    assert word.list_state == "basic"  # unchanged
    assert word.hsk_word_id == entry.id
    assert hsk.find_by_text("东西")[0].app_state == "basic"


def test_move_between_basic_and_new(service, words):
    word, _ = service.add_manual("桌子")
    service.move_new_to_basic(word.id)
    assert words.get_by_text("桌子").list_state == "basic"
    service.move_basic_to_new(word.id)
    assert words.get_by_text("桌子").list_state == "new"
