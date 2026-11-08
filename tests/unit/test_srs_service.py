"""Unit tests: SrsService persistence, ratings, selector, lesson tracking."""

from __future__ import annotations

import random

import pytest

from langread.db import connect
from langread.db.repositories import LessonsRepo, TopicsRepo, WordsRepo
from langread.services.srs import DEFAULT_PARAMS, SrsParams, SrsService

NOW = "2026-11-01T00:00:00+00:00"


@pytest.fixture()
def conn(tmp_path):
    conn = connect(tmp_path / "test.db")
    yield conn
    conn.close()


@pytest.fixture()
def srs(conn):
    return SrsService(conn)


@pytest.fixture()
def words(conn):
    return WordsRepo(conn)


@pytest.fixture()
def lesson_id(conn):
    topics = TopicsRepo(conn)
    lessons = LessonsRepo(conn)
    return lessons.create(topic_id=topics.create("Cooking").id).id


def test_params_default_and_persistence(srs):
    assert srs.params() == DEFAULT_PARAMS
    custom = SrsParams(learned_words_per_paragraph=3, weight_staleness=0.7)
    srs.set_params(custom)
    assert srs.params() == custom


def test_params_ignores_unknown_and_coerces_types(srs):
    srs.settings.set("srs.params", {"staleness_target_lessons": 5.0,
                                    "learned_words_per_paragraph": 4,
                                    "bogus_key": "x"})
    params = srs.params()
    assert params.staleness_target_lessons == 5.0
    assert params.learned_words_per_paragraph == 4
    assert params == SrsParams(staleness_target_lessons=5.0,
                               learned_words_per_paragraph=4)


def test_params_ignores_old_day_based_keys(srs):
    srs.settings.set("srs.params", {"initial_interval_days": 5.0,
                                    "easy_bonus": 1.5})
    assert srs.params() == DEFAULT_PARAMS


def test_promote_word_sets_lesson_tracking(srs, words, lesson_id):
    w, _ = words.get_or_create("厨房", list_state="new")
    learned = srs.promote_word(w.id, lesson_id)
    assert learned.list_state == "learned"
    assert learned.ease == 2.5
    assert (learned.reps, learned.lapses) == (0, 0)
    assert learned.first_learned_lesson_id == lesson_id
    assert learned.last_seen_lesson_id == lesson_id


def test_selector_reads_learned_list_and_next_lesson(srs, words, lesson_id):
    for text in ("甲", "乙"):
        w, _ = words.get_or_create(text, list_state="new")
        srs.promote_word(w.id, lesson_id)
    selector = srs.selector(rng=random.Random(0))
    assert selector._current == lesson_id + 1  # MAX(lessons.id) + 1
    picks = selector.pick(count=2)
    assert set(picks) == {"甲", "乙"}
    # top-weighted preview lists learned words
    assert set(selector.top_weighted(5)) == {"甲", "乙"}


def test_rate_word_logs_event_then_updates(srs, words, lesson_id):
    w, _ = words.get_or_create("厨房")
    srs.promote_word(w.id, lesson_id)
    rated = srs.rate_word(w.id, "easy", lesson_id, now=NOW)
    assert rated.ease == pytest.approx(2.65)
    assert rated.reps == 1
    events = srs.reviews.events_for_lesson(lesson_id)
    assert len(events) == 1
    assert events[0].word_id == w.id
    assert events[0].rating == "easy"
    assert events[0].device == "desktop"
    assert rated.last_rated_at == NOW


def test_rate_word_rejects_bad_rating(srs, words, lesson_id):
    w, _ = words.get_or_create("厨房")
    with pytest.raises(ValueError):
        srs.rate_word(w.id, "bogus", lesson_id, now=NOW)
    assert srs.reviews.events_for_lesson(lesson_id) == []


def test_difficult_rating_lowers_ease_and_counts_a_lapse(srs, words,
                                                         lesson_id):
    w, _ = words.get_or_create("厨房")
    srs.promote_word(w.id, lesson_id)
    rated = srs.rate_word(w.id, "difficult", lesson_id, now=NOW)
    assert rated.ease == pytest.approx(2.3)
    assert rated.lapses == 1
    # the word now scores higher in the lesson-frequency difficulty factor
    selector = srs.selector(current_lesson_no=lesson_id + 1)
    assert selector.top_weighted(1) == ["厨房"]
