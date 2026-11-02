"""M8 UI tests (offscreen): lesson list + lesson review screen."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QApplication, QMessageBox

from langread.db import connect
from langread.db.repositories import (
    LessonsRepo,
    TemplatesRepo,
    TopicsRepo,
    WordsRepo,
)
from langread.services.generation import LessonDraft, GeneratedParagraph
from langread.services.lesson_saver import LessonSaver
from langread.services.srs import SrsService
from langread.ui.review.lesson_review import LessonReviewWindow
from langread.ui.topic_lesson_list import LessonListDialog
from tests.integration.test_generation import NEW, REVIEW
from tests.integration.test_lesson_saver import TranslationStub, TtsStub


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture()
def env(tmp_path, monkeypatch):
    """A fully saved lesson (TtsStub + TranslationStub) ready for review."""
    monkeypatch.setenv("LANGREAD_DATA_DIR", str(tmp_path / "appdata"))
    conn = connect(tmp_path / "test.db")
    TemplatesRepo(conn).seed_defaults()
    topic = TopicsRepo(conn).create("Cooking")
    words = WordsRepo(conn)
    srs = SrsService(conn)
    for text in NEW:
        words.get_or_create(text, list_state="new", source="manual")
    for text in REVIEW:
        word, _ = words.get_or_create(text, list_state="new", source="manual")
        srs.promote_word(word.id, now="2026-11-01T00:00:00+00:00")

    paragraphs = []
    from langread.services.segmentation import SegmentationService

    segmentation = SegmentationService(conn)  # custom dict has NEW/REVIEW words
    for i in range(3):
        text = f"我们学{NEW[i]}。{REVIEW[i % 2]}也很有用。"
        paragraphs.append(GeneratedParagraph(
            index=i, text=text, sentences=[text],
            segmentations=[segmentation.token_texts(text)],
        ))
    draft = LessonDraft(topic_id=topic.id, topic_name=topic.name,
                        new_words=list(NEW), review_words=list(REVIEW),
                        paragraphs=paragraphs)
    audio_dir = tmp_path / "appdata" / "audio"
    lesson = LessonSaver(conn, tts=TtsStub(), translation=TranslationStub(),
                         audio_dir=audio_dir).save_lesson(draft)
    yield conn, topic.id, lesson.id
    conn.close()


def test_lesson_list_shows_lessons_and_review_dates(qapp, env, monkeypatch):
    conn, _topic_id, _lesson_id = env
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)
    dialog = LessonListDialog(conn)
    assert dialog.topic_combo.count() == 1
    assert dialog.table.rowCount() == 1
    assert dialog.table.item(0, 2).text() == "never reviewed"
    assert dialog.review_button.isEnabled()
    assert not dialog.finish_button.isEnabled()  # lesson is complete
    dialog.close()


def test_lesson_review_text_rendering(qapp, env):
    conn, _topic, lesson_id = env
    window = LessonReviewWindow(conn, lesson_id)
    html_text = window._last_html
    # new words appear as anchors (§8.3)
    assert 'href="w:' in html_text
    for text in NEW[:3]:
        assert f'href="w:{text}"' in html_text
    # first occurrence of each new word is highlighted (D-1)
    assert html_text.count('class="new"') >= 3
    # translation toggle link present (sentences are translated, §8.4)
    assert "[译]" in html_text
    # audio bar exists with a working jump button (§8.5)
    assert window.audio_bar.end_button.isEnabled()
    window.close()


def test_sentence_translation_toggle(qapp, env):
    conn, _topic, lesson_id = env
    window = LessonReviewWindow(conn, lesson_id)
    first = window._sentences[0]
    assert first.translation
    assert first.translation not in window.text_browser.toHtml()
    window._on_anchor(QUrl(f"tr:{first.id}"))
    assert first.translation in window.text_browser.toHtml()
    window._on_anchor(QUrl(f"tr:{first.id}"))  # toggle off again
    assert first.translation not in window.text_browser.toHtml()
    window.close()


def test_word_popup_actions(qapp, env):
    conn, _topic, lesson_id = env
    window = LessonReviewWindow(conn, lesson_id)
    # a token that is on no list (我们)
    window._show_word_popup("我们")
    popup = window._popup
    assert popup.word is None
    popup._add("new")  # §5.3: mark a word in a lesson as new
    assert WordsRepo(conn).get_by_text("我们").list_state == "new"
    # a basic word: move Basic → New (§8.3)
    words = WordsRepo(conn)
    words.get_or_create("东西", list_state="basic")
    window._word_cache.clear()
    window._show_word_popup("东西")
    popup = window._popup
    assert popup.word is not None and popup.word.list_state == "basic"
    popup._move_to_new()
    assert words.get_by_text("东西").list_state == "new"
    window.close()


def test_word_review_complete_and_cancel(qapp, env, monkeypatch):
    conn, _topic, lesson_id = env
    srs = SrsService(conn)
    lessons = LessonsRepo(conn)

    # --- cancel: nothing written (§8.7) ---
    window = LessonReviewWindow(conn, lesson_id)
    window._enter_word_review()
    rows = window.review_page.table.rowCount()
    assert rows == len(NEW) + len(REVIEW)  # all lesson words are learned
    window.review_page.set_rating(0, "difficult")
    window.reject()
    assert lessons.get(lesson_id).last_reviewed_at is None
    assert srs.reviews.events_for_lesson(lesson_id) == []
    window.close()

    # --- complete: events + SRS + timestamp (§8.6–8.7) ---
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)
    window = LessonReviewWindow(conn, lesson_id)
    window._enter_word_review()
    window.review_page.set_rating(0, "difficult")
    window.review_page.set_rating(1, "easy")
    word_rows = window.review_page._words
    interval_before = {w.id: w.interval_days for w in word_rows}
    window._complete_review(open_next=False)

    events = srs.reviews.events_for_lesson(lesson_id)
    assert len(events) == len(word_rows)
    ratings = {event.word_id: event.rating for event in events}
    assert ratings[word_rows[0].id] == "difficult"
    assert ratings[word_rows[1].id] == "easy"
    assert ratings[word_rows[2].id] == "standard"  # default
    # SRS applied: difficult → short interval; easy → bigger growth
    words = WordsRepo(conn)
    difficult_word = words.get(word_rows[0].id)
    easy_word = words.get(word_rows[1].id)
    assert difficult_word.interval_days == 0.5
    assert easy_word.interval_days > interval_before[easy_word.id]
    assert lessons.get(lesson_id).last_reviewed_at is not None
    window.close()


def test_bulk_rating(qapp, env):
    conn, _topic, lesson_id = env
    window = LessonReviewWindow(conn, lesson_id)
    window._enter_word_review()
    page = window.review_page
    page.table.selectAll()
    page.bulk_combo.setCurrentIndex(page.bulk_combo.findData("easy"))
    page._apply_bulk()
    assert set(page.ratings().values()) == {"easy"}
    window.close()


def test_jump_to_end_does_not_auto_advance(qapp, env):
    """§8.5: audio controls never auto-advance — the user decides when to go
    to the word review (listens multiple times)."""
    conn, _topic, lesson_id = env
    window = LessonReviewWindow(conn, lesson_id)
    window.audio_bar._jump_to_end()
    assert window.stack.currentIndex() == 0  # still on the reading page
    window.close()


def test_word_review_button_enters_word_review(qapp, env):
    conn, _topic, lesson_id = env
    window = LessonReviewWindow(conn, lesson_id)
    window.word_review_button.click()
    assert window.stack.currentIndex() == 1
    assert window.review_page.table.rowCount() > 0
    window.close()


def test_dark_mode_renders_light_text(qapp, env):
    """Palette-aware stylesheet: dark palette → light text color in CSS."""
    from PySide6.QtGui import QColor, QPalette

    conn, _topic, lesson_id = env
    window = LessonReviewWindow(conn, lesson_id)
    browser = window.text_browser
    dark = QPalette()
    dark.setColor(QPalette.ColorRole.Base, QColor("#2b2b2b"))
    dark.setColor(QPalette.ColorRole.Text, QColor("#eeeeee"))
    dark.setColor(QPalette.ColorRole.Link, QColor("#7ab8ff"))
    browser.setPalette(dark)
    window._render_text()  # palette change would also trigger this
    css = browser.document().defaultStyleSheet()
    assert "#eeeeee" in css          # body/anchor text color from palette
    assert "#b8b8b8" in css          # light-gray translation color
    assert "#202020" in css          # new-word highlight keeps dark text

    # light palette → dark text
    light = QPalette()
    light.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
    light.setColor(QPalette.ColorRole.Text, QColor("#000000"))
    browser.setPalette(light)
    window._render_text()
    css = browser.document().defaultStyleSheet()
    assert "#000000" in css
    assert "#606060" in css          # dark-gray translation color
    window.close()


def test_translation_toggle_spacing(qapp, env):
    """The [译] toggle is separated from the FOLLOWING sentence so it groups
    with its own sentence."""
    conn, _topic, lesson_id = env
    window = LessonReviewWindow(conn, lesson_id)
    html_text = window._last_html
    assert '[译]</a>&nbsp;&nbsp; ' in html_text
    assert '<a class="tr" href="tr:' in html_text
    window.close()

