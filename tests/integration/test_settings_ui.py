"""M3 UI tests (offscreen): settings dialog, models/templates/SRS pages."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLineEdit, QListWidget, QPlainTextEdit

from langread.db import connect
from langread.db.repositories import SettingsRepo, TemplatesRepo
from langread.services.srs import SrsService
from langread.ui.settings.models_page import ModelsPage
from langread.ui.settings.srs_page import SrsPage
from langread.ui.settings.templates_page import TemplatesPage
from langread.ui.settings_dialog import SettingsDialog


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture()
def conn(tmp_path):
    conn = connect(tmp_path / "test.db")
    yield conn
    conn.close()


def test_settings_dialog_has_three_tabs(qapp, conn):
    dialog = SettingsDialog(conn)
    assert dialog.tabs.count() == 3
    labels = [dialog.tabs.tabText(i) for i in range(3)]
    assert labels == ["Models", "Prompt templates", "Spaced repetition"]
    assert dialog.tabs.currentIndex() == 0
    dialog.close()


def test_models_page_saves_values(qapp, conn):
    page = ModelsPage(conn)
    groups = page._groups
    assert len(groups) == 3  # gen, trans, tts

    gen_group = groups[0]
    gen_group.base_url.setText("http://192.168.1.20:1234/v1")
    gen_group.model.setText("qwen-9b")
    tts_group = groups[2]
    tts_group.base_url.setText("http://192.168.1.20:8880/v1")
    tts_group.model.setText("kokoro")
    tts_group.voice.setText("zf_xiaobei")
    tts_group.speed.setValue(1.25)
    page.save()

    repo = SettingsRepo(conn)
    assert repo.get("gen.base_url") == "http://192.168.1.20:1234/v1"
    assert repo.get("gen.model") == "qwen-9b"
    assert repo.get("tts.voice") == "zf_xiaobei"
    assert repo.get("tts.speed") == 1.25


def test_models_page_reloads_saved_values(qapp, conn):
    repo = SettingsRepo(conn)
    repo.set("trans.base_url", "http://dashscope/v1")
    repo.set("trans.model", "qwen-max")
    page = ModelsPage(conn)
    trans_group = page._groups[1]
    assert trans_group.base_url.text() == "http://dashscope/v1"
    assert trans_group.model.text() == "qwen-max"


def test_models_page_test_connection_buttons(qapp, conn):
    """Regression test: the Test buttons must not touch the (thread-bound)
    SQLite connection from the worker thread."""
    from tests.fakes.openai_server import FakeOpenAiServer

    server = FakeOpenAiServer()
    url = server.start_and_url()
    try:
        repo = SettingsRepo(conn)
        repo.set("trans.base_url", url)
        repo.set("trans.model", "fake")
        repo.set("tts.base_url", url)
        repo.set("tts.model", "kokoro")

        page = ModelsPage(conn)

        # LLM test button (translation group)
        llm_group = page._groups[1]
        llm_group._test()
        llm_group._worker.wait()
        for _ in range(10):
            qapp.processEvents()
        assert "✅" in llm_group.status.text()
        assert "SQLite" not in llm_group.status.text()
        assert llm_group.test_button.isEnabled()

        # TTS test button
        tts_group = page._groups[2]
        tts_group._test()
        tts_group._worker.wait()
        for _ in range(10):
            qapp.processEvents()
        assert "✅" in tts_group.status.text()
        assert "SQLite" not in tts_group.status.text()
        assert tts_group.test_button.isEnabled()
    finally:
        server.stop()


def test_models_page_test_button_reports_missing_config(qapp, conn):
    page = ModelsPage(conn)  # nothing configured
    llm_group = page._groups[0]
    llm_group._test()
    assert "❌" in llm_group.status.text()
    assert "gen.base_url" in llm_group.status.text()
    assert llm_group.test_button.isEnabled()


def test_templates_page_edit_and_save(qapp, conn):
    TemplatesRepo(conn).seed_defaults()
    page = TemplatesPage(conn)
    list_widget = page.findChild(QListWidget)
    assert list_widget.count() >= 7

    list_widget.setCurrentRow(list_widget.count() - 1)
    name = page._current_name()
    editor = page.findChild(QPlainTextEdit)
    editor.setPlainText("NEW {word} template")
    page._save()
    assert TemplatesRepo(conn).get(name) == "NEW {word} template"

    # reload page → loads the saved value
    page2 = TemplatesPage(conn)
    list2 = page2.findChild(QListWidget)
    rows = [list2.item(i).text() for i in range(list2.count())]
    list2.setCurrentRow(rows.index(name))
    assert page2.findChild(QPlainTextEdit).toPlainText() == "NEW {word} template"


def test_srs_page_roundtrip(qapp, conn):
    page = SrsPage(conn)
    page._spinners["initial_interval_days"].setValue(3.0)
    page._spinners["easy_bonus"].setValue(1.6)
    page._save()

    params = SrsService(conn).params()
    assert params.initial_interval_days == 3.0
    assert params.easy_bonus == 1.6

    page2 = SrsPage(conn)
    assert page2._spinners["initial_interval_days"].value() == 3.0
    assert page2._spinners["easy_bonus"].value() == 1.6
