"""M4 UI tests: SegmentationEditor merge/split/reset (offscreen)."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from langread.ui.widgets.segmentation_editor import SegmentationEditor


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _select_rows(editor: SegmentationEditor, rows: list[int]) -> None:
    for row in rows:
        editor._list.item(row).setSelected(True)


def test_merge_contiguous_selection(qapp):
    editor = SegmentationEditor()
    editor.set_tokens(["今天", "天气", "很", "好"])
    emitted = []
    editor.changed.connect(lambda: emitted.append(editor.tokens()))
    _select_rows(editor, [0, 1])
    editor._merge()
    assert editor.tokens() == ["今天天气", "很", "好"]
    assert emitted[-1] == ["今天天气", "很", "好"]


def test_merge_two_separate_runs(qapp):
    editor = SegmentationEditor()
    editor.set_tokens(["a", "b", "c", "d", "e", "f"])
    _select_rows(editor, [0, 1, 3, 4])
    editor._merge()
    assert editor.tokens() == ["ab", "c", "de", "f"]


def test_merge_requires_two_selected(qapp):
    editor = SegmentationEditor()
    editor.set_tokens(["你", "好"])
    _select_rows(editor, [0])
    editor._merge()
    assert editor.tokens() == ["你", "好"]


def test_split_into_characters(qapp):
    editor = SegmentationEditor()
    editor.set_tokens(["今天", "天气", "好"])
    _select_rows(editor, [0, 1])
    editor._split()
    assert editor.tokens() == ["今", "天", "天", "气", "好"]


def test_reset_restores_original(qapp):
    editor = SegmentationEditor()
    editor.set_tokens(["今天", "天气"])
    _select_rows(editor, [0, 1])
    editor._merge()
    assert editor.tokens() == ["今天天气"]
    editor._reset()
    assert editor.tokens() == ["今天", "天气"]
    assert editor.original_tokens() == ["今天", "天气"]


def test_set_tokens_renders_chips(qapp):
    editor = SegmentationEditor()
    editor.set_tokens(["你好", "，", "世界"])
    assert editor._list.count() == 3
    assert editor._list.item(0).text() == "你好"
