"""M6 UI tests (offscreen): lesson wizard pages."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from langread.db import connect
from langread.db.repositories import TemplatesRepo, TopicsRepo, WordsRepo
from langread.services.generation import GenerationService, LessonDraft
from langread.services.segmentation import SegmentationService
from langread.ui.lesson_create.final_edit import FinalEditPage
from langread.ui.lesson_create.generate_view import GeneratePage
from langread.ui.lesson_create.word_select import WordSelectPage
from langread.ui.lesson_create.wizard import LessonWizard
from tests.integration.test_generation import NEW, REVIEW, ScriptedLlm


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture()
def conn(tmp_path):
    db_file = tmp_path / "test.db"
    conn = connect(db_file)
    TemplatesRepo(conn).seed_defaults()
    TemplatesRepo(conn).upsert(
        "generate_paragraph",
        "WORDS: new={new_word}; repeat={repeat_words}; review={review_words}; topic={topic_name}",
    )
    TemplatesRepo(conn).upsert(
        "generate_paragraph_no_new",
        "WORDS-NO-NEW: repeat={repeat_words}; review={review_words}; topic={topic_name}",
    )
    TemplatesRepo(conn).upsert("generate_final_paragraph", "FINAL: {all_new_words}")
    topic = TopicsRepo(conn).create("Cooking")
    for text in NEW:
        WordsRepo(conn).get_or_create(text, list_state="new")
    for text in REVIEW:
        WordsRepo(conn).get_or_create(text, list_state="basic")
    yield conn, topic.id, db_file
    conn.close()


def test_word_select_page_suggestions_and_validation(qapp, conn):
    _conn, topic_id, _db_file = conn
    page = WordSelectPage(_conn, topic_id, llm=None)
    assert page.new_list.count() == 5  # the five new words suggested
    # check all five
    for row in range(page.new_list.count()):
        page.new_list.item(row).setCheckState(Qt.CheckState.Checked)
    assert page.validation_error() is None
    assert page.selected_new() == NEW
    assert page.paragraph_count() == 8

    # uncheck one → validation error
    page.new_list.item(0).setCheckState(Qt.CheckState.Unchecked)
    assert page.validation_error() is not None

    # 5 new words with only 5 paragraphs → spin minimum (6) prevents this;
    # the constraint is instead validated by the wizard before generation
    assert page.paragraph_spin.minimum() == 6


def test_generate_page_runs_worker_to_completion(qapp, conn):
    _conn, topic_id, db_file = conn
    page = GeneratePage(db_file, topic_id, llm=ScriptedLlm())
    results = []
    page.generation_finished.connect(lambda draft: results.append(draft))
    page.start(NEW, REVIEW, 6)
    page.wait_for_worker()
    for _ in range(10):
        qapp.processEvents()  # let queued signals reach their slots
    assert len(results) == 1
    draft = results[0]
    assert isinstance(draft, LessonDraft)
    assert len(draft.paragraphs) == 6
    assert page.progress_list.count() == 6


def test_final_edit_page_text_and_segmentation_editing(qapp, conn):
    _conn, topic_id, _db_file = conn
    service = GenerationService(_conn, llm=ScriptedLlm())
    draft = service.generate_lesson(topic_id, NEW, REVIEW, 6)
    page = FinalEditPage(_conn)
    page.set_draft(draft, SegmentationService(_conn))
    assert page.tabs.count() == 6

    # hand-edit the first paragraph's text (D-6)
    tab = page.tabs.widget(0)
    tab.text_edit.setPlainText("我们学咕词一。咕复一很好。")
    tab._apply_text()
    paragraph = draft.paragraphs[0]
    assert paragraph.text == "我们学咕词一。咕复一很好。"
    assert paragraph.sentences == ["我们学咕词一。", "咕复一很好。"]
    assert "咕词一" in paragraph.segmentations[0]

    # hand-edit the segmentation of the first sentence
    tab.sentence_list.setCurrentRow(0)
    seg_before = tab.seg_editor.tokens()
    tab.seg_editor._list.item(0).setSelected(True)
    tab.seg_editor._list.item(1).setSelected(True)
    tab.seg_editor._merge()
    assert paragraph.segmentations[0] != seg_before
    assert len(paragraph.segmentations[0]) < len(seg_before)


def test_wizard_full_flow(qapp, conn):
    _conn, topic_id, db_file = conn
    wizard = LessonWizard(_conn, topic_id, "Cooking", llm=ScriptedLlm(),
                          db_path=db_file)
    assert wizard.stack.count() == 3
    # select all new words and advance
    for row in range(wizard.word_page.new_list.count()):
        wizard.word_page.new_list.item(row).setCheckState(Qt.CheckState.Checked)
    wizard._go_next()
    assert wizard.stack.currentIndex() == 1
    wizard.generate_page.wait_for_worker()
    for _ in range(10):
        qapp.processEvents()  # let queued signals reach their slots
    assert wizard.stack.currentIndex() == 2
    assert wizard._draft is not None
    assert wizard.final_page.tabs.count() == 8
    # regenerate-all returns to step 1 (§7.8)
    wizard._regenerate_all()
    assert wizard.stack.currentIndex() == 0


def test_wizard_retry_after_generation_failure(qapp, conn, monkeypatch):
    """After a failed generation, the button restarts generation instead of
    doing nothing."""
    from PySide6.QtWidgets import QMessageBox
    from langread.services.llm_client import LlmError

    class FailingLlm:
        def chat(self, prompt: str) -> str:
            raise LlmError("model returned an empty message")

    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: None)
    _conn, topic_id, db_file = conn
    wizard = LessonWizard(_conn, topic_id, "Cooking", llm=FailingLlm(),
                          db_path=db_file)
    for row in range(wizard.word_page.new_list.count()):
        wizard.word_page.new_list.item(row).setCheckState(Qt.CheckState.Checked)
    wizard._go_next()
    wizard.generate_page.wait_for_worker()
    for _ in range(10):
        qapp.processEvents()
    # generation failed: still on page 1, button relabelled and enabled
    assert wizard.stack.currentIndex() == 1
    assert "Retry" in wizard.next_button.text()
    assert wizard.next_button.isEnabled()

    # swap in a working model and press the button again → completes
    wizard.generate_page._llm = ScriptedLlm()
    wizard._go_next()
    wizard.generate_page.wait_for_worker()
    for _ in range(10):
        qapp.processEvents()
    assert wizard.stack.currentIndex() == 2
    assert wizard._draft is not None


def test_wizard_approve_saves_lesson(qapp, conn, monkeypatch, tmp_path):
    """End-to-end: generate → hand-edit-free approve → full save pipeline,
    with all three model endpoints pointed at the fake server."""
    from pathlib import Path

    from PySide6.QtWidgets import QMessageBox

    from langread.db.repositories import LessonsRepo, SettingsRepo
    from langread.services.model_settings import ModelSettings
    from tests.fakes.openai_server import FakeOpenAiServer

    _conn, topic_id, db_file = conn
    # keep generated audio inside the test sandbox
    monkeypatch.setenv("LANGREAD_DATA_DIR", str(tmp_path / "appdata"))

    server = FakeOpenAiServer()
    url = server.start_and_url()
    try:
        settings = ModelSettings(SettingsRepo(_conn))
        settings.save("tts", {"base_url": url, "model": "kokoro"})
        settings.save("trans", {"base_url": url, "model": "fake"})
        monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)

        wizard = LessonWizard(_conn, topic_id, "Cooking", llm=ScriptedLlm(),
                              db_path=db_file)
        for row in range(wizard.word_page.new_list.count()):
            wizard.word_page.new_list.item(row).setCheckState(Qt.CheckState.Checked)
        wizard._go_next()
        wizard.generate_page.wait_for_worker()
        for _ in range(10):
            qapp.processEvents()
        assert wizard.stack.currentIndex() == 2

        wizard._approve()
        wizard.wait_for_save_worker()
        for _ in range(10):
            qapp.processEvents()

        lesson_id = wizard.saved_lesson_id()
        assert lesson_id is not None
        lesson = LessonsRepo(_conn).get(lesson_id)
        assert lesson is not None and lesson.status == "complete"
        assert lesson.audio_path == f"lesson_{lesson_id}.mp3"
        audio_file = tmp_path / "appdata" / "audio" / lesson.audio_path
        assert audio_file.exists() and audio_file.stat().st_size > 0
    finally:
        server.stop()
