"""M1 unit tests: topics, lessons, sentences repositories."""

from __future__ import annotations

import pytest

from langread.db import connect
from langread.db.repositories import (
    LessonsRepo,
    SentencesRepo,
    TopicNotEmptyError,
    TopicsRepo,
)
from langread.models import Sentence


@pytest.fixture()
def conn(tmp_path):
    conn = connect(tmp_path / "test.db")
    yield conn
    conn.close()


@pytest.fixture()
def topics(conn):
    return TopicsRepo(conn)


@pytest.fixture()
def lessons(conn):
    return LessonsRepo(conn)


@pytest.fixture()
def sentences(conn):
    return SentencesRepo(conn)


# ---- topics ----


def test_topic_create_and_ordering(topics):
    t1 = topics.create("Cooking")
    t2 = topics.create("Travel")
    assert (t1.order_index, t2.order_index) == (1, 2)
    listed = topics.list_all()
    assert [t.name for t in listed] == ["Cooking", "Travel"]


def test_topic_get_by_name_and_rename(topics):
    topics.create("Cooking")
    t = topics.get_by_name("Cooking")
    assert t is not None and t.id is not None
    topics.rename(t.id, "厨房")
    assert topics.get_by_name("厨房") is not None
    assert topics.get_by_name("Cooking") is None


def test_topic_delete_blocked_when_not_empty(topics, lessons):
    t = topics.create("Cooking")
    lessons.create(topic_id=t.id)
    with pytest.raises(TopicNotEmptyError):
        topics.delete(t.id)
    assert topics.get(t.id) is not None


def test_topic_delete_ok_when_empty(topics):
    t = topics.create("Cooking")
    topics.delete(t.id)
    assert topics.get(t.id) is None


def test_topic_duplicate_name_rejected(topics):
    topics.create("Cooking")
    import sqlite3

    with pytest.raises(sqlite3.IntegrityError):
        topics.create("Cooking")


# ---- lessons ----


def test_lesson_create_defaults_and_listing(topics, lessons):
    t = topics.create("Cooking")
    l1 = lessons.create(topic_id=t.id, title="First lesson")
    l2 = lessons.create(topic_id=t.id)
    assert l1.status == "draft"
    assert l1.title == "First lesson"
    assert [l.id for l in lessons.list_for_topic(t.id)] == [l1.id, l2.id]
    assert lessons.list_by_status("draft") == [l1, l2]


def test_lesson_invalid_status_rejected(topics, lessons):
    t = topics.create("Cooking")
    with pytest.raises(ValueError):
        lessons.create(topic_id=t.id, status="bogus")


def test_lesson_status_audio_and_reviewed(topics, lessons):
    t = topics.create("Cooking")
    l = lessons.create(topic_id=t.id)
    assert l.last_reviewed_at is None
    lessons.set_status(l.id, "incomplete")
    lessons.set_audio_path(l.id, "audio/lesson_1.mp3")
    lessons.mark_reviewed(l.id, reviewed_at="2026-11-01T10:00:00+00:00")
    got = lessons.get(l.id)
    assert got.status == "incomplete"
    assert got.audio_path == "audio/lesson_1.mp3"
    assert got.last_reviewed_at == "2026-11-01T10:00:00+00:00"


def test_lesson_delete_cascades_sentences(topics, lessons, sentences):
    t = topics.create("Cooking")
    l = lessons.create(topic_id=t.id)
    sentences.replace_for_lesson(
        l.id,
        [Sentence(id=0, lesson_id=0, para_index=0, sent_index=0,
                  text="你好", segmentation=["你好"])],
    )
    assert sentences.count_for_lesson(l.id) == 1
    lessons.delete(l.id)
    assert sentences.count_for_lesson(l.id) == 0


def test_lesson_words_role_validation(topics, lessons):
    t = topics.create("Cooking")
    l = lessons.create(topic_id=t.id)
    with pytest.raises(ValueError):
        lessons.add_lesson_word(l.id, 1, "bogus")


# ---- sentences ----


def test_sentences_replace_and_order(sentences, topics, lessons):
    t = topics.create("T")
    l = lessons.create(topic_id=t.id)
    stored = sentences.replace_for_lesson(
        l.id,
        [
            Sentence(id=0, lesson_id=0, para_index=0, sent_index=0,
                     text="今天天气很好。", segmentation=["今天", "天气", "很", "好"]),
            Sentence(id=0, lesson_id=0, para_index=1, sent_index=0,
                     text="我很高兴。", segmentation=["我", "很", "高兴"]),
            Sentence(id=0, lesson_id=0, para_index=1, sent_index=1,
                     text="你呢？", segmentation=["你", "呢"]),
        ],
    )
    assert [s.id for s in stored] != [0, 0, 0]  # ids assigned
    listed = sentences.list_for_lesson(l.id)
    assert [s.text for s in listed] == ["今天天气很好。", "我很高兴。", "你呢？"]
    assert listed[0].segmentation == ["今天", "天气", "很", "好"]
    assert listed[0].para_index == 0 and listed[2].para_index == 1


def test_sentences_update_fields(sentences, topics, lessons):
    t = topics.create("T")
    l = lessons.create(topic_id=t.id)
    stored = sentences.replace_for_lesson(
        l.id,
        [Sentence(id=0, lesson_id=0, para_index=0, sent_index=0, text="你好")],
    )
    sid = stored[0].id
    sentences.update(sid, text="你好吗？", segmentation=["你好", "吗"],
                     translation="How are you?")
    got = sentences.list_for_lesson(l.id)[0]
    assert got.text == "你好吗？"
    assert got.segmentation == ["你好", "吗"]
    assert got.translation == "How are you?"


def test_sentences_default_segmentation_falls_back_to_characters(
    sentences, topics, lessons
):
    t = topics.create("T")
    l = lessons.create(topic_id=t.id)
    stored = sentences.replace_for_lesson(
        l.id,
        [Sentence(id=0, lesson_id=0, para_index=0, sent_index=0, text="你好")],
    )
    assert stored[0].segmentation == ["你", "好"]
