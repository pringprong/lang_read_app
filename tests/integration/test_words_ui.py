"""M5 UI tests (offscreen): word list manager and add-words dialog."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from langread.db import connect
from langread.db.repositories import HskRepo, WordsRepo
from langread.services.word_import import WordImportService
from langread.ui.words.add_words import AddWordsDialog
from langread.ui.words.list_manager import WordListManager


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture()
def conn(tmp_path):
    conn = connect(tmp_path / "test.db")
    yield conn
    conn.close()


def _add_words(conn, texts, state):
    service = WordImportService(conn)
    for text in texts:
        word, _ = service.add_manual(text)
        if state == "basic":
            service.move_new_to_basic(word.id)


def test_word_list_manager_tabs_and_counts(qapp, conn):
    _add_words(conn, ["桌子", "椅子"], "new")
    _add_words(conn, ["水杯"], "basic")
    manager = WordListManager(conn)
    assert manager.tabs.count() == 4
    assert manager.new_tab.table.rowCount() == 2
    assert manager.basic_tab.table.rowCount() == 1
    # HSK tab was populated on construction; 150 level-1 words minus
    # 桌子/椅子 (HSK 1 words now on the new list) = 148 unused
    assert manager.hsk_table.rowCount() == 148
    manager.close()


def test_word_list_manager_basic_to_new_move(qapp, conn):
    _add_words(conn, ["水杯"], "basic")
    manager = WordListManager(conn)
    manager.basic_tab.table.selectRow(0)
    manager._basic_to_new()
    words = WordsRepo(conn)
    assert words.get_by_text("水杯").list_state == "new"
    assert manager.new_tab.table.rowCount() == 1
    assert manager.basic_tab.table.rowCount() == 0
    manager.close()


def test_word_list_manager_hsk_bulk_add(qapp, conn):
    manager = WordListManager(conn)
    # pick a known level-1 HSK word
    target_text = manager.hsk_table.item(0, 0).text()
    manager.hsk_table.selectRow(0)
    manager._hsk_add("new")
    words = WordsRepo(conn)
    word = words.get_by_text(target_text)
    assert word is not None and word.list_state == "new"
    assert word.hsk_word_id is not None
    assert HskRepo(conn).find_by_text(target_text)[0].app_state == "new"
    manager.close()


def test_add_words_paste_flow(qapp, conn):
    dialog = AddWordsDialog(conn)
    paste = dialog.paste_tab
    paste.text_box.setPlainText("我喜欢喝茶，也喜欢喝咖啡。")
    paste._parse()
    row_count = paste.table.rowCount()
    assert row_count >= 2
    # tick the 喝茶 row
    for row in range(row_count):
        if paste.table.item(row, 1).text() == "喝茶":
            paste.checkbox_at(row).setChecked(True)
    paste._import()
    words = WordsRepo(conn)
    assert words.get_by_text("喝茶").list_state == "new"
    assert words.get_by_text("咖啡").list_state == "basic"
    assert "Imported: 1 new" in paste.status.text()
    dialog.close()


def test_add_words_paste_existing_word_not_markable(qapp, conn):
    _add_words(conn, ["喝茶"], "new")
    dialog = AddWordsDialog(conn)
    paste = dialog.paste_tab
    paste.text_box.setPlainText("喝茶")
    paste._parse()
    box = paste.checkbox_at(0)
    assert box.isEnabled() is False
    dialog.close()


def test_add_words_manual_flow(qapp, conn):
    dialog = AddWordsDialog(conn)
    manual = dialog.manual_tab
    manual.word_edit.setText("机场")
    manual._add()
    words = WordsRepo(conn)
    assert words.get_by_text("机场").list_state == "new"
    assert "Added" in manual.status.text()
    # duplicate add reports existing
    manual.word_edit.setText("机场")
    manual._add()
    assert "already" in manual.status.text()
    dialog.close()
