"""Edit the text of an existing lesson (lesson management window).

Reuses the wizard's final-edit page (§7.8 / D-6): per-paragraph text
editing with re-splitting and re-segmentation. On save:

- sentences are replaced atomically; translations are kept for sentences
  whose text did not change (changed sentences lose their translation),
- if any paragraph text changed, the old audio file is deleted and the
  lesson's audio path cleared (the audio no longer matches the text;
  use "Regenerate audio" afterwards).
"""

from __future__ import annotations

import sqlite3

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from langread.db.repositories import LessonsRepo, SentencesRepo, TopicsRepo
from langread.models import Sentence
from langread.services.generation import GeneratedParagraph, LessonDraft
from langread.services.segmentation import SegmentationService
from langread.ui.lesson_create.final_edit import FinalEditPage

_AUDIO_SUFFIXES = (".mp3", ".wav", ".ogg", ".flac")


class EditLessonTextDialog(QDialog):
    def __init__(self, conn: sqlite3.Connection, lesson_id: int,
                 parent=None) -> None:
        super().__init__(parent)
        self.conn = conn
        self.lessons = LessonsRepo(conn)
        self.sentences = SentencesRepo(conn)
        self.topics = TopicsRepo(conn)

        lesson = self.lessons.get(lesson_id)
        if lesson is None:
            raise ValueError(f"lesson {lesson_id} does not exist")
        self.lesson_id = lesson_id
        topic = self.topics.get(lesson.topic_id)
        topic_name = topic.name if topic else ""
        self.setWindowTitle(
            f"Edit lesson text — lesson {lesson.order_index}"
            + (f": {lesson.title}" if lesson.title else "")
            + (f" ({topic_name})" if topic_name else "")
        )
        self.resize(860, 620)

        self._draft = self._draft_from_lesson(lesson_id)
        self._original_texts = [p.text for p in self._draft.paragraphs]

        self.edit_page = FinalEditPage(conn)
        self.edit_page.set_draft(self._draft, SegmentationService(conn))

        hint = QLabel(
            "Edit the text of any paragraph and apply it (re-split & "
            "re-segment). Unchanged sentences keep their translations; if the "
            "text changed, the audio must be regenerated afterwards."
        )
        hint.setWordWrap(True)

        self.save_button = QPushButton("Save changes")
        self.save_button.clicked.connect(self._save)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(cancel_button)
        buttons.addWidget(self.save_button)

        layout = QVBoxLayout(self)
        layout.addWidget(hint)
        layout.addWidget(self.edit_page, 1)
        layout.addLayout(buttons)

    # ---- load ----

    def _draft_from_lesson(self, lesson_id: int) -> LessonDraft:
        """Build a wizard-style draft from the stored sentences."""
        by_para: dict[int, list[Sentence]] = {}
        for sentence in self.sentences.list_for_lesson(lesson_id):
            by_para.setdefault(sentence.para_index, []).append(sentence)
        paragraphs = [
            GeneratedParagraph(
                index=para_index,
                text="".join(s.text for s in group),
                sentences=[s.text for s in group],
                segmentations=[list(s.segmentation) for s in group],
            )
            for para_index, group in sorted(by_para.items())
        ]
        lesson = self.lessons.get(lesson_id)
        assert lesson is not None
        return LessonDraft(
            topic_id=lesson.topic_id,
            topic_name="",
            new_words=[],
            review_words=[],
            paragraphs=paragraphs,
        )

    # ---- save ----

    def _save(self) -> None:
        draft = self.edit_page.draft()
        if draft is None:
            return

        # translations survive only for sentences whose text is unchanged
        available: dict[str, list[str]] = {}
        for sentence in self.sentences.list_for_lesson(self.lesson_id):
            if sentence.translation:
                available.setdefault(sentence.text, []).append(sentence.translation)

        new_sentences: list[Sentence] = []
        for para_index, paragraph in enumerate(draft.paragraphs):
            for i, text in enumerate(paragraph.sentences):
                segmentation = (
                    paragraph.segmentations[i]
                    if i < len(paragraph.segmentations)
                    else list(text)
                )
                translation = None
                if available.get(text):
                    translation = available[text].pop(0)
                new_sentences.append(
                    Sentence(id=0, lesson_id=self.lesson_id,
                             para_index=para_index, sent_index=i,
                             text=text, segmentation=segmentation,
                             translation=translation)
                )
        self.sentences.replace_for_lesson(self.lesson_id, new_sentences)

        text_changed = [p.text for p in draft.paragraphs] != self._original_texts
        if text_changed:
            self._delete_audio()
            QMessageBox.information(
                self, "Lesson text saved",
                "The lesson text was updated. The old audio no longer matches "
                "the text — use \"Regenerate audio\" in the lesson list.",
            )
        else:
            QMessageBox.information(self, "Lesson text saved",
                                    "The lesson was saved.")
        self.accept()

    def _delete_audio(self) -> None:
        from langread.app_config import audio_dir

        directory = audio_dir()
        for suffix in _AUDIO_SUFFIXES:
            candidate = directory / f"lesson_{self.lesson_id}{suffix}"
            if candidate.exists():
                candidate.unlink()
        self.lessons.set_audio_path(self.lesson_id, None)
