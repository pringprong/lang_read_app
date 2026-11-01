"""M1 unit tests: words, HSK repositories."""

from __future__ import annotations

import pytest

from langread.db import connect, utcnow_iso
from langread.db.repositories import HskRepo, TopicsRepo, WordsRepo


@pytest.fixture()
def conn(tmp_path):
    conn = connect(tmp_path / "test.db")
    yield conn
    conn.close()


@pytest.fixture()
def words(conn):
    return WordsRepo(conn)


@pytest.fixture()
def hsk(conn):
    return HskRepo(conn)


@pytest.fixture()
def topics(conn):
    return TopicsRepo(conn)


# ---- words ----


def test_get_or_create_is_idempotent(words):
    w1, created1 = words.get_or_create("厨房", list_state="new", source="manual")
    w2, created2 = words.get_or_create("厨房", list_state="basic", source="paste")
    assert created1 and not created2
    assert w1.id == w2.id
    assert w2.list_state == "new"  # existing membership wins (§5.1)


def test_get_or_create_validates_state_and_source(words):
    with pytest.raises(ValueError):
        words.get_or_create("好", list_state="bogus")
    with pytest.raises(ValueError):
        words.get_or_create("好", source="bogus")


def test_list_by_state_oldest_first(words):
    words.get_or_create("一")
    words.get_or_create("二")
    words.get_or_create("三")
    listed = words.list_by_state("new")
    assert [w.text for w in listed] == ["一", "二", "三"]
    assert words.count_by_state("new") == 3


def test_move_to_state_syncs_hsk(words, hsk):
    hsk.import_rows([("厨房", "chúfáng", "kitchen", 4)])
    hsk_row = hsk.find_by_text("厨房")[0]
    w, _ = words.get_or_create("厨房", hsk_word_id=hsk_row.id)
    words.move_to_state(w.id, "basic")
    assert words.get(w.id).list_state == "basic"
    assert hsk.find_by_text("厨房")[0].app_state == "basic"


def test_set_translation_and_srs(words):
    w, _ = words.get_or_create("厨房")
    words.set_translation(w.id, "chúfáng", "kitchen")
    words.set_srs(
        w.id, ease=2.8, interval_days=4.0, due_at="2026-11-05T00:00:00+00:00",
        reps=2, lapses=1, last_rated_at="2026-11-01T00:00:00+00:00",
    )
    got = words.get(w.id)
    assert (got.pinyin, got.definition) == ("chúfáng", "kitchen")
    assert (got.ease, got.interval_days, got.reps, got.lapses) == (2.8, 4.0, 2, 1)


def test_word_topic_association(words, topics):
    cooking = topics.create("Cooking")
    travel = topics.create("Travel")
    w, _ = words.get_or_create("机场", source="manual")
    words.associate_topic(w.id, cooking.id)
    words.associate_topic(w.id, cooking.id)  # idempotent
    words.associate_topic(w.id, travel.id)
    names = [t.name for t in words.topics_for_word(w.id)]
    assert names == ["Cooking", "Travel"]


def test_suggest_new_words_topic_first_oldest_first(words, topics):
    cooking = topics.create("Cooking")
    for text in ("一", "二", "三"):  # added in order
        words.get_or_create(text)
    airport, _ = words.get_or_create("机场")  # newest, but topic-linked
    words.associate_topic(airport.id, cooking.id)

    suggested = words.suggest_new_words(cooking.id, limit=10)
    assert suggested[0].text == "机场"  # topic words first
    assert [w.text for w in suggested[1:]] == ["一", "二", "三"]  # oldest first


def test_due_learned_words_topic_first_and_ordering(words, topics):
    cooking = topics.create("Cooking")

    def learned(text, due_day, topic_id=None):
        w, _ = words.get_or_create(text)
        words.move_to_state(w.id, "learned")
        words.set_srs(
            w.id, ease=2.5, interval_days=1.0,
            due_at=f"2026-11-{due_day:02d}T00:00:00+00:00",
            reps=1, lapses=0, last_rated_at=None,
        )
        if topic_id:
            words.associate_topic(w.id, topic_id)
        return w

    learned("甲", 5)              # due Nov 5, no topic
    learned("乙", 3, cooking.id)  # due Nov 3, Cooking
    learned("丙", 1)              # due Nov 1, no topic

    by_topic = words.due_learned_words(topic_id=cooking.id)
    # topic words first, then others by due date (reqs §7.2: "mainly same topic")
    assert [w.text for w in by_topic] == ["乙", "丙", "甲"]
    # with a limit, the topic word is suggested first
    assert [w.text for w in words.due_learned_words(topic_id=cooking.id, limit=1)] == ["乙"]

    all_due = words.due_learned_words()
    assert [w.text for w in all_due] == ["丙", "乙", "甲"]  # global due order

    only_due_now = words.due_learned_words(now_iso="2026-11-02T00:00:00+00:00")
    assert [w.text for w in only_due_now] == ["丙"]


# ---- HSK ----


def test_hsk_import_idempotent_and_counts(hsk):
    rows = [("你好", "nǐ hǎo", "hello", 1), ("谢谢", "xièxie", "thank you", 1)]
    assert hsk.import_rows(rows) == 2
    assert hsk.import_rows(rows) == 0  # idempotent
    assert hsk.count() == 2
    assert hsk.count(1) == 2
    assert hsk.count(2) == 0
    assert hsk.counts_by_level() == {1: 2}


def test_hsk_list_level_filter_and_pagination(hsk):
    hsk.import_rows([(f"词{i}", None, None, 1) for i in range(5)])
    page1 = hsk.list_level(1, limit=3)
    page2 = hsk.list_level(1, limit=3, offset=3)
    assert len(page1) == 3 and len(page2) == 2
    assert hsk.list_level(1, app_state="unused") == page1 + page2


def test_hsk_level_validation(hsk):
    with pytest.raises(ValueError):
        hsk.list_level(7)
