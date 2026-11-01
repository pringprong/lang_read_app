"""Wizard step 3: final review / hand-editing (requirements §7.8, D-6)."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt, Signal

from langread.services.generation import (
    GenerationService,
    LessonDraft,
    split_sentences,
)
from langread.ui.widgets.segmentation_editor import SegmentationEditor


class _ParagraphTab(QWidget):
    """Text + per-sentence segmentation editor for one paragraph."""

    segmentation_changed = Signal()

    def __init__(self, paragraph, segmentation_service,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._paragraph = paragraph
        self._segmentation = segmentation_service

        self.text_edit = QPlainTextEdit()
        self.text_edit.setPlainText(paragraph.text)

        apply_button = QPushButton("Apply text edit (re-split & re-segment)")
        apply_button.clicked.connect(self._apply_text)

        self.sentence_list = QListWidget()
        self.sentence_list.currentRowChanged.connect(self._load_sentence)

        self.seg_editor = SegmentationEditor()
        self.seg_editor.changed.connect(self._save_segmentation)
        self.seg_hint = QLabel(
            "Select a sentence above, then merge/split its word tokens."
        )
        self.seg_hint.setWordWrap(True)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self.sentence_list)
        bottom = QWidget()
        bottom_layout = QVBoxLayout(bottom)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.addWidget(self.seg_hint)
        bottom_layout.addWidget(self.seg_editor)
        splitter.addWidget(bottom)

        layout = QVBoxLayout(self)
        layout.addWidget(self.text_edit)
        layout.addWidget(apply_button)
        layout.addWidget(splitter)
        self._reload_sentences()

    # ---- sentence handling ----

    def _reload_sentences(self, select: int = 0) -> None:
        self.sentence_list.clear()
        for sentence in self._paragraph.sentences:
            self.sentence_list.addItem(QListWidgetItem(sentence))
        if self._paragraph.sentences:
            self.sentence_list.setCurrentRow(min(select, len(self._paragraph.sentences) - 1))
            self._load_sentence(self.sentence_list.currentRow())

    def _load_sentence(self, row: int) -> None:
        if 0 <= row < len(self._paragraph.segmentations):
            self.seg_editor.set_tokens(self._paragraph.segmentations[row])

    def _save_segmentation(self) -> None:
        row = self.sentence_list.currentRow()
        if 0 <= row < len(self._paragraph.segmentations):
            self._paragraph.segmentations[row] = self.seg_editor.tokens()
            self.segmentation_changed.emit()

    def _apply_text(self) -> None:
        """Re-split the edited text into sentences and re-segment (D-6)."""
        text = self.text_edit.toPlainText().strip()
        self._paragraph.text = text
        self._paragraph.sentences = split_sentences(text)
        self._paragraph.segmentations = [
            self._segmentation.token_texts(sentence)
            for sentence in self._paragraph.sentences
        ]
        self._reload_sentences()

    def paragraph(self):
        return self._paragraph


class FinalEditPage(QWidget):
    def __init__(self, conn, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._conn = conn
        self._draft: LessonDraft | None = None

        self.info = QLabel("Review the lesson. Hand-edit the text of any paragraph "
                           "or its word segmentation, then approve on the last page.")
        self.info.setWordWrap(True)
        self.tabs = QTabWidget()

        layout = QVBoxLayout(self)
        layout.addWidget(self.info)
        layout.addWidget(self.tabs)

    def set_draft(self, draft: LessonDraft, segmentation_service) -> None:
        self._draft = draft
        self.tabs.clear()
        for paragraph in draft.paragraphs:
            tab = _ParagraphTab(paragraph, segmentation_service)
            self.tabs.addTab(tab, f"§{paragraph.index + 1}")

    def draft(self) -> LessonDraft | None:
        # paragraph objects are shared references, so text/segmentation
        # edits made in the tabs are already reflected in the draft
        return self._draft
