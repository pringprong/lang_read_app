"""Shared fixture database for the Android↔desktop round-trip tools.

Builds a small desktop database (real repos, real schema) that the content
bundle is exported from and results bundles are imported into.

Run with the desktop repo's venv python:
  /home/pringprong/lang_read_app/.venv/bin/python tool/<script>.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

DESKTOP_SRC = Path("/home/pringprong/lang_read_app/src")
if str(DESKTOP_SRC) not in sys.path:
    sys.path.insert(0, str(DESKTOP_SRC))

from langread.db.connection import connect  # noqa: E402
from langread.db.repositories import (  # noqa: E402
    LessonsRepo,
    ReviewsRepo,
    SentencesRepo,
    TopicsRepo,
    WordsRepo,
)
from langread.models import Sentence  # noqa: E402

NEW_WORDS = ["锅", "炒", "食材"]
LEARNED_WORDS = ["饭", "菜", "水"]
BASIC_WORDS = ["我", "你"]


def build_fixture(db_path: Path, audio_dir: Path) -> dict:
    """Two topics / three lessons (one draft) + words + sentences + audio.

    Returns {"conn": conn, "lessons": {title: Lesson}}.
    """
    conn = connect(db_path)
    topics = TopicsRepo(conn)
    lessons = LessonsRepo(conn)
    sentences = SentencesRepo(conn)
    words = WordsRepo(conn)
    reviews = ReviewsRepo(conn)

    cooking = topics.create("Cooking")
    travel = topics.create("Travel")

    for t in LEARNED_WORDS:
        words.get_or_create(t, list_state="learned", source="manual",
                            pinyin=f"py-{t}", definition=f"def of {t}")
    for t in BASIC_WORDS:
        words.get_or_create(t, list_state="basic", source="manual",
                            pinyin=f"py-{t}", definition=f"def of {t}")

    audio_dir.mkdir(parents=True, exist_ok=True)

    def add_lesson(topic_id: int, title: str, status: str,
                   sentence_specs: list[tuple[int, int, str, list[str], str]],
                   new_word_texts: list[str],
                   review_word_texts: list[str],
                   with_audio: bool):
        lesson = lessons.create(topic_id, title)
        lessons.set_status(lesson.id, status)
        if with_audio:
            lessons.set_audio_path(lesson.id, f"lesson_{lesson.id}.mp3")
            (audio_dir / f"lesson_{lesson.id}.mp3").write_bytes(
                b"ID3-fake-mp3-audio-for-tests" + bytes(64)
            )
        sents = [
            Sentence(id=0, lesson_id=lesson.id, para_index=p, sent_index=si,
                     text=text, segmentation=seg, translation=trans)
            for (p, si, text, seg, trans) in sentence_specs
        ]
        sentences.replace_for_lesson(lesson.id, sents)
        for t in new_word_texts:
            w, _ = words.get_or_create(t, list_state="new", source="manual",
                                       pinyin=f"py-{t}", definition=f"def of {t}")
            lessons.add_lesson_word(lesson.id, w.id, "new")
        for t in review_word_texts:
            w = words.get_by_text(t)
            if w is not None:
                lessons.add_lesson_word(lesson.id, w.id, "review")
        return lesson

    lesson1 = add_lesson(
        cooking.id, "First meal", "complete",
        [
            (0, 0, "我用锅做饭。", ["我", "用", "锅", "做", "饭", "。"],
             "I cook rice with the pot."),
            (0, 1, "锅很热。", ["锅", "很", "热", "。"], "The pot is hot."),
            (1, 0, "这个菜很好吃。", ["这个", "菜", "很", "好吃", "。"],
             "This dish is delicious."),
        ],
        new_word_texts=["锅"],
        review_word_texts=["饭", "菜"],
        with_audio=True,
    )
    lesson2 = add_lesson(
        cooking.id, "Second meal", "complete",
        [
            (0, 0, "我们炒菜。", ["我们", "炒", "菜", "。"], "We stir-fry vegetables."),
        ],
        new_word_texts=["炒", "食材"],
        review_word_texts=["饭"],
        with_audio=True,
    )
    add_lesson(  # draft lessons must not appear on Android (§3.2)
        travel.id, "Draft trip notes", "draft",
        [(0, 0, "我坐火车。", ["我", "坐", "火车", "。"], "I take the train.")],
        new_word_texts=[],
        review_word_texts=[],
        with_audio=False,
    )

    # Desktop-side review history → events.jsonl in the exported bundle.
    fan = words.get_by_text("饭")
    if fan is not None:
        reviews.add(lesson_id=lesson1.id, word_id=fan.id, rating="standard",
                    device="desktop", reviewed_at="2026-11-05T10:00:00+00:00")
    reviews.add(lesson_id=lesson1.id, device="desktop",
                reviewed_at="2026-11-05T10:05:00+00:00")

    # A couple of HSK rows (direct SQL keeps this script dependency-free).
    conn.executescript(
        "INSERT INTO hsk_words (text, pinyin, definition, level, app_state) VALUES "
        "('饭', 'fàn', 'rice; food', 1, 'learned'); "
        "INSERT INTO hsk_words (text, pinyin, definition, level, app_state) VALUES "
        "('水', 'shuǐ', 'water', 1, 'learned');"
    )

    return {"conn": conn,
            "lessons": {"first": lesson1, "second": lesson2}}


def temp_workspace() -> tuple[Path, Path, Path, Path]:
    """(workspace dir, db path, audio dir, backups dir) in a temp directory."""
    ws = Path(tempfile.mkdtemp(prefix="langread_roundtrip_"))
    return ws, ws / "desktop.db", ws / "audio", ws / "backups"
