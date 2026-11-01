"""M1 unit tests: settings, reviews, templates repositories."""

from __future__ import annotations

import pytest

from langread.db import connect
from langread.db.repositories import (
    ReviewsRepo,
    SettingsRepo,
    TemplatesRepo,
)


@pytest.fixture()
def conn(tmp_path):
    conn = connect(tmp_path / "test.db")
    yield conn
    conn.close()


@pytest.fixture()
def settings(conn):
    return SettingsRepo(conn)


@pytest.fixture()
def reviews(conn):
    return ReviewsRepo(conn)


@pytest.fixture()
def templates(conn):
    return TemplatesRepo(conn)


# ---- settings ----


def test_settings_roundtrip_of_structured_values(settings):
    assert settings.get("missing", default={}) == {}
    settings.set("srs.params", {"initial": 1, "easy_bonus": 1.3})
    assert settings.get("srs.params") == {"initial": 1, "easy_bonus": 1.3}
    settings.set("srs.params", {"initial": 2})
    assert settings.get("srs.params") == {"initial": 2}
    settings.delete("srs.params")
    assert settings.get("srs.params") is None


# ---- reviews ----


def test_review_event_validation(reviews):
    with pytest.raises(ValueError):
        reviews.add(lesson_id=1, rating="bogus")
    with pytest.raises(ValueError):
        reviews.add(lesson_id=1, device="iphone")


def test_review_events_for_lesson_and_since(conn, reviews):
    from langread.db.repositories import LessonsRepo, TopicsRepo

    lesson = LessonsRepo(conn).create(topic_id=TopicsRepo(conn).create("T").id)
    e1 = reviews.add(lesson_id=lesson.id, word_id=None, rating="standard",
                     reviewed_at="2026-11-01T09:00:00+00:00")
    e2 = reviews.add(lesson_id=lesson.id, word_id=None, rating="difficult",
                     device="android", reviewed_at="2026-11-02T09:00:00+00:00")
    assert reviews.events_for_lesson(lesson.id) == [e1, e2]
    since = reviews.events_since("2026-11-02T00:00:00+00:00")
    assert since == [e2]
    android = reviews.events_since("2026-11-01T00:00:00+00:00", device="android")
    assert android == [e2]


# ---- templates ----


def test_templates_seed_get_upsert(templates):
    assert templates.seed_defaults() > 0
    assert templates.seed_defaults() == 0  # second call adds nothing
    names = templates.list_names()
    for expected in ("generate_paragraph", "generate_final_paragraph",
                     "translate_word", "segment_text"):
        assert expected in names
    original = templates.get("generate_paragraph")
    assert "{new_word}" in original  # placeholder present in the seed
    templates.upsert("generate_paragraph", "NEW {new_word} {repeat_words}")
    assert templates.get("generate_paragraph") == "NEW {new_word} {repeat_words}"
    templates.upsert("generate_paragraph", original)  # restore
    assert templates.get("generate_paragraph") == original
