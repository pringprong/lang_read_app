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


@pytest.fixture()
def lessons(conn):
    from langread.db.repositories import LessonsRepo

    return LessonsRepo(conn)


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
        w.id, ease=2.8, reps=2, lapses=1,
        last_rated_at="2026-11-01T00:00:00+00:00",
    )
    got = words.get(w.id)
    assert (got.pinyin, got.definition) == ("chúfáng", "kitchen")
    assert (got.ease, got.reps, got.lapses) == (2.8, 2, 1)


def test_lesson_track_set_clear_and_forward_only(words, topics, lessons):
    cooking = topics.create("Cooking")
    lesson1 = lessons.create(topic_id=cooking.id)
    lesson2 = lessons.create(topic_id=cooking.id)
    w, _ = words.get_or_create("厨房")
    words.set_lesson_track(w.id, first_learned_lesson_id=lesson1.id,
                           last_seen_lesson_id=lesson1.id)
    got = words.get(w.id)
    assert (got.first_learned_lesson_id, got.last_seen_lesson_id) == (
        lesson1.id, lesson1.id
    )

    # an actual appearance only ever moves last_seen FORWARD
    words.set_last_seen_lesson(w.id, lesson2.id)
    assert words.get(w.id).last_seen_lesson_id == lesson2.id
    words.set_last_seen_lesson(w.id, lesson1.id)  # stale replay (resume) — ignored
    assert words.get(w.id).last_seen_lesson_id == lesson2.id

    words.clear_lesson_track(w.id)  # lesson delete → word demoted
    got = words.get(w.id)
    assert (got.first_learned_lesson_id, got.last_seen_lesson_id) == (None, None)


def test_learned_word_lesson_tracking_query(words, topics, lessons):
    cooking = topics.create("Cooking")
    anchor = lessons.create(topic_id=cooking.id)  # lesson 1: where 甲 was learned
    w, _ = words.get_or_create("甲")
    words.move_to_state(w.id, "learned")
    words.set_lesson_track(w.id, first_learned_lesson_id=anchor.id,
                           last_seen_lesson_id=anchor.id)
    lesson = lessons.create(topic_id=cooking.id)  # lesson 2: reuses 甲
    lessons.add_appearance(lesson.id, w.id, para_index=3)
    assert lessons.appearances_for_lesson(lesson.id) == [(w.id, 3)]
    words.set_last_seen_lesson(w.id, lesson.id)
    tracked = {x.text: x for x in words.list_by_state("learned")}
    assert tracked["甲"].first_learned_lesson_id == anchor.id
    assert tracked["甲"].last_seen_lesson_id == lesson.id


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
