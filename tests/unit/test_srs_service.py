"""M2 unit tests: SrsService persistence and event logging."""

from __future__ import annotations

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
    custom = SrsParams(initial_interval_days=2.0, easy_bonus=1.5)
    srs.set_params(custom)
    assert srs.params() == custom


def test_params_ignores_unknown_keys(srs):
    srs.settings.set("srs.params", {"initial_interval_days": 5.0,
                                    "bogus_key": "x"})
    params = srs.params()
    assert params.initial_interval_days == 5.0
    assert params == SrsParams(initial_interval_days=5.0)


def test_promote_word(srs, words):
    w, _ = words.get_or_create("厨房", list_state="new")
    learned = srs.promote_word(w.id, now=NOW)
    assert learned.list_state == "learned"
    assert learned.interval_days == 1.0
    assert learned.due_at == "2026-11-02T00:00:00+00:00"
    assert (learned.reps, learned.lapses) == (1, 0)


def test_apply_exposure_updates_due_only(srs, words):
    w, _ = words.get_or_create("厨房")
    srs.promote_word(w.id, now=NOW)
    exposed = srs.apply_exposure(w.id, now=NOW)
    assert exposed.interval_days == pytest.approx(2.5)
    assert exposed.reps == 1  # unchanged
    # no review event for exposure (not a review, §7.9.4)
    assert srs.reviews.events_for_lesson(1) == []


def test_rate_word_logs_event_then_updates(srs, words, lesson_id):
    w, _ = words.get_or_create("厨房")
    srs.promote_word(w.id, now=NOW)
    rated = srs.rate_word(w.id, "easy", lesson_id, now=NOW)
    assert rated.ease == pytest.approx(2.65)
    assert rated.reps == 2
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


def test_difficult_rating_makes_word_due_soon(srs, words, lesson_id):
    # §8.6.1: difficult → word should come back quite soon
    w, _ = words.get_or_create("厨房")
    srs.promote_word(w.id, now=NOW)
    rated = srs.rate_word(w.id, "difficult", lesson_id, now=NOW)
    assert rated.interval_days == 0.5
    assert rated.due_at == "2026-11-01T12:00:00+00:00"
    # the word now surfaces first in due-word suggestions
    words.get_or_create("乙")
    other = words.get_by_text("乙")
    words.move_to_state(other.id, "learned")
    words.set_srs(other.id, ease=2.5, interval_days=10.0,
                  due_at="2026-11-10T00:00:00+00:00", reps=1, lapses=0,
                  last_rated_at=None)
    due = words.due_learned_words()
    assert due[0].id == w.id
