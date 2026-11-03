"""UI tests (offscreen) for the manage-lessons / manage-topics windows and
the lesson deletion + text-editing features."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QInputDialog, QMessageBox

from langread.db import connect
from langread.db.repositories import (
    LessonsRepo,
    SentencesRepo,
    TemplatesRepo,
    TopicsRepo,
    WordsRepo,
)
from langread.services.generation import GeneratedParagraph, LessonDraft
from langread.services.lesson_saver import LessonSaver, SaveError
from langread.services.segmentation import SegmentationService
from langread.services.srs import SrsService
from langread.ui.lesson_create.edit_lesson import EditLessonTextDialog
from langread.ui.topics_manager import TopicsManagerDialog
from langread.ui.topic_lesson_list import LessonListDialog
from tests.integration.test_generation import NEW, REVIEW
from tests.integration.test_lesson_saver import TranslationStub, TtsStub


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture()
def env(tmp_path, monkeypatch):
    """A topic with two saved lessons; lesson 1 has two sentences in its
    first paragraph (for the translation-spacing test)."""
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

    segmentation = SegmentationService(conn)
    audio_dir = tmp_path / "appdata" / "audio"
    saver = LessonSaver(conn, tts=TtsStub(), translation=TranslationStub(),
                        audio_dir=audio_dir)

    def make_lesson(paragraph_specs, new_words, review_words):
        paragraphs = [
            GeneratedParagraph(
                index=i, text="".join(parts),
                sentences=list(parts),
                segmentations=[segmentation.token_texts(s) for s in parts],
            )
            for i, parts in enumerate(paragraph_specs)
        ]
        draft = LessonDraft(topic_id=topic.id, topic_name=topic.name,
                            new_words=new_words, review_words=review_words,
                            paragraphs=paragraphs)
        return saver.save_lesson(draft)

    lesson1 = make_lesson(
        [(f"我们学{NEW[0]}。", f"{REVIEW[0]}也很有用。"), (f"我们学{NEW[1]}。",)],
        [NEW[0], NEW[1]], [REVIEW[0]],
    )
    lesson2 = make_lesson([(f"我们学{NEW[2]}。",)], [NEW[2]], [])
    yield conn, topic, lesson1.id, lesson2.id, audio_dir
    conn.close()


# ---- lesson list (manage lessons) ----


def test_lesson_list_columns_and_review_count(qapp, env, monkeypatch):
    conn, topic, lesson1_id, lesson2_id, _audio_dir = env
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)
    dialog = LessonListDialog(conn)
    assert dialog.windowTitle() == "Manage lessons"
    assert dialog.table.columnCount() == 4
    assert dialog.table.horizontalHeaderItem(3).text() == "Times reviewed"
    assert dialog.table.rowCount() == 2
    assert dialog.table.item(0, 3).text() == "0"

    # delete: only enabled for the LAST lesson of the topic
    dialog.table.selectRow(0)
    assert not dialog.delete_button.isEnabled()
    dialog.table.selectRow(1)
    assert dialog.delete_button.isEnabled()
    assert dialog.edit_button.isEnabled()

    # a completed review increments the count
    LessonsRepo(conn).mark_reviewed(lesson1_id)
    dialog._reload_lessons()
    dialog.table.selectRow(0)
    assert dialog.table.item(0, 3).text() == "1"
    dialog.close()


def test_new_lesson_button_opens_wizard(qapp, env, monkeypatch):
    conn, topic, _l1, _l2, _audio_dir = env
    opened = []

    class FakeWizard:
        def __init__(self, conn, topic_id, topic_name, llm=None,
                     db_path=None, parent=None) -> None:
            opened.append((topic_id, topic_name))

        def exec(self):
            return 0

    monkeypatch.setattr("langread.ui.lesson_create.wizard.LessonWizard", FakeWizard)
    dialog = LessonListDialog(conn)
    dialog.new_lesson_button.click()
    assert opened == [(topic.id, topic.name)]
    dialog.close()


# ---- lesson deletion ----


def test_delete_lesson_service(env):
    conn, topic, lesson1_id, lesson2_id, audio_dir = env
    saver = LessonSaver(conn, tts=TtsStub(), translation=None,
                        audio_dir=audio_dir)

    # only the last lesson of a topic can be deleted
    with pytest.raises(SaveError, match="last lesson"):
        saver.delete_lesson(lesson1_id)

    # deleting the last lesson moves its new word back to the New list
    words = WordsRepo(conn)
    assert words.get_by_text(NEW[2]).list_state == "learned"
    demoted = saver.delete_lesson(lesson2_id)
    assert demoted == [NEW[2]]
    assert words.get_by_text(NEW[2]).list_state == "new"
    assert LessonsRepo(conn).get(lesson2_id) is None
    assert SentencesRepo(conn).list_for_lesson(lesson2_id) == []
    assert not (audio_dir / f"lesson_{lesson2_id}.mp3").exists()

    # the second-last lesson became the last and can be deleted too
    demoted1 = saver.delete_lesson(lesson1_id)
    assert sorted(demoted1) == sorted([NEW[0], NEW[1]])
    assert words.get_by_text(NEW[0]).list_state == "new"
    assert LessonsRepo(conn).list_for_topic(topic.id) == []


def test_delete_lesson_button(qapp, env, monkeypatch):
    conn, _topic, lesson1_id, lesson2_id, _audio_dir = env
    monkeypatch.setattr(QMessageBox, "question",
                        lambda *a, **k: QMessageBox.StandardButton.Yes)
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)
    dialog = LessonListDialog(conn)
    dialog.table.selectRow(1)
    assert dialog.delete_button.isEnabled()
    dialog.delete_button.click()
    assert LessonsRepo(conn).get(lesson2_id) is None
    assert dialog.table.rowCount() == 1
    # the remaining (now last) lesson is deletable in turn
    assert dialog.delete_button.isEnabled()
    dialog.close()


# ---- lesson text editing ----


def test_edit_lesson_text(qapp, env, monkeypatch):
    conn, _topic, lesson1_id, _l2, audio_dir = env
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)
    sentences = SentencesRepo(conn)
    before = sentences.list_for_lesson(lesson1_id)
    assert len(before) == 3  # 2 sentences in paragraph 1 + 1 in paragraph 2

    dialog = EditLessonTextDialog(conn, lesson1_id)
    assert dialog.edit_page.tabs.count() == 2

    # rewrite paragraph 1's text; applying re-splits and re-segments it
    tab = dialog.edit_page.tabs.widget(0)
    tab.text_edit.setPlainText(f"我们学{NEW[3]}。")
    tab._apply_text()
    assert len(tab.paragraph().sentences) == 1
    dialog.save_button.click()

    after = sentences.list_for_lesson(lesson1_id)
    assert [s.text for s in after] == [f"我们学{NEW[3]}。", before[2].text]
    # unchanged sentences keep their translation; changed ones lose it
    assert after[0].translation is None
    assert after[1].translation == before[2].translation

    # the text changed → the stale audio is removed and the path cleared
    assert not (audio_dir / f"lesson_{lesson1_id}.mp3").exists()
    assert LessonsRepo(conn).get(lesson1_id).audio_path is None


def test_edit_lesson_text_unchanged_keeps_audio(qapp, env, monkeypatch):
    conn, _topic, lesson1_id, _l2, audio_dir = env
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)
    dialog = EditLessonTextDialog(conn, lesson1_id)
    dialog.save_button.click()  # save without any edits
    assert (audio_dir / f"lesson_{lesson1_id}.mp3").exists()
    assert LessonsRepo(conn).get(lesson1_id).audio_path is not None


# ---- translation spacing in the review window ----


def test_translation_newline_before_next_sentence(qapp, env):
    from langread.ui.review.lesson_review import LessonReviewWindow

    conn, _topic, lesson1_id, _l2, _audio_dir = env
    window = LessonReviewWindow(conn, lesson1_id)
    first = window._sentences[0]
    assert first.translation
    window._revealed.add(first.id)
    window._render_text()
    # the revealed translation is followed by a line break before the next
    # sentence of the same paragraph (§8.4 spacing)
    assert f"{first.translation}</span><br>" in window._last_html
    window.close()


# ---- manage topics ----


def test_topics_manager_create_rename_delete(qapp, tmp_path, monkeypatch):
    conn = connect(tmp_path / "topics.db")
    try:
        topics = TopicsRepo(conn)
        cooking = topics.create("Cooking")
        topics.create("Travel")
        LessonsRepo(conn).create(topic_id=cooking.id)  # 1 lesson in Cooking

        dialog = TopicsManagerDialog(conn)
        assert dialog.table.rowCount() == 2
        assert dialog.table.item(0, 1).text() == "Cooking"
        assert dialog.table.item(0, 2).text() == "1"
        assert dialog.table.item(1, 2).text() == "0"

        # delete is only enabled for a topic without lessons
        dialog.table.selectRow(0)
        assert not dialog.delete_button.isEnabled()
        dialog.table.selectRow(1)
        assert dialog.delete_button.isEnabled()

        # create a new topic
        monkeypatch.setattr(QInputDialog, "getText",
                            lambda *a, **k: ("Sports", True))
        dialog.new_button.click()
        assert dialog.table.rowCount() == 3
        assert topics.get_by_name("Sports") is not None

        # rename it
        dialog.table.selectRow(2)
        monkeypatch.setattr(QInputDialog, "getText",
                            lambda *a, **k: ("Hobby", True))
        dialog.rename_button.click()
        assert topics.get_by_name("Hobby") is not None
        assert topics.get_by_name("Sports") is None

        # delete the empty (renamed) topic; reloading after the rename
        # re-selected the first row, so pick the topic again
        dialog.table.selectRow(2)
        monkeypatch.setattr(QMessageBox, "question",
                            lambda *a, **k: QMessageBox.StandardButton.Yes)
        dialog.delete_button.click()
        assert topics.get_by_name("Hobby") is None
        assert dialog.table.rowCount() == 2
        dialog.close()
    finally:
        conn.close()
