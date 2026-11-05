"""Lesson review screen (requirements §8.2–8.7).

Page 1: lesson text with tappable words (§8.3 popups with list actions),
static highlighting of first-time new words (D-1), per-sentence translation
toggles (§8.4), and the audio bar (§8.5). Page 2 (after the audio ends or
"jump to end"): the word-review table (§8.6) with bulk rating. Completing
writes review events + SRS updates + last_reviewed_at (§8.7); canceling
writes nothing (word-list actions already taken remain).
"""

from __future__ import annotations

import html
import sqlite3
from pathlib import Path

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QWidget,
)

from langread.db.repositories import (
    HskRepo,
    LessonsRepo,
    SentencesRepo,
    SettingsRepo,
    WordsRepo,
)
from langread.services.segmentation import is_cjk
from langread.services.srs import RATINGS, SrsService

RATING_LABELS = {"standard": "Standard", "easy": "Easy", "difficult": "Difficult",
                 "unchanged": "Unchanged"}

# reading-text font size (user preference, persisted in the settings table)
FONT_SETTINGS_KEY = "ui.review_font_pt"
FONT_STEP = 2
FONT_MIN, FONT_MAX = 8, 40


class WordPopup(QWidget):
    """Word info + list actions (§8.3). Commits immediately when pressed."""

    list_changed = Signal()

    def __init__(self, text: str, word, hsk, conn: sqlite3.Connection,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent, Qt.WindowType.Popup)
        self.text = text
        self.word = word
        self.conn = conn
        self.words = WordsRepo(conn)

        from PySide6.QtWidgets import QVBoxLayout

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"<b>{text}</b>"))
        pinyin = (word.pinyin if word else (hsk.pinyin if hsk else None)) or ""
        layout.addWidget(QLabel(pinyin))
        definition = (word.definition if word else (hsk.definition if hsk else None))
        if definition:
            definition_label = QLabel(definition)
            definition_label.setWordWrap(True)
            layout.addWidget(definition_label)
        if word is not None:
            layout.addWidget(QLabel(f"On the {word.list_state} word list"))
        elif hsk is not None:
            layout.addWidget(QLabel(f"HSK level {hsk.level} (not on any app list)"))
        else:
            layout.addWidget(QLabel("Not on any list"))

        if word is None:
            new_button = QPushButton("Add to New Word List")
            new_button.clicked.connect(lambda: self._add("new"))
            basic_button = QPushButton("Add to Basic Word List")
            basic_button.clicked.connect(lambda: self._add("basic"))
            layout.addWidget(new_button)
            layout.addWidget(basic_button)
        elif word.list_state == "basic":
            move_button = QPushButton("Move Basic → New")
            move_button.clicked.connect(self._move_to_new)
            layout.addWidget(move_button)

    def _add(self, list_state: str) -> None:
        self.words.get_or_create(self.text, list_state=list_state, source="lesson")
        self.list_changed.emit()
        self.close()

    def _move_to_new(self) -> None:
        self.words.move_to_state(self.word.id, "new")
        self.list_changed.emit()
        self.close()


class LessonReviewWindow(QDialog):
    def __init__(self, conn: sqlite3.Connection, lesson_id: int,
                 parent=None) -> None:
        super().__init__(parent)
        self.conn = conn
        self.lessons = LessonsRepo(conn)
        self.sentences = SentencesRepo(conn)
        self.words = WordsRepo(conn)
        self.hsk = HskRepo(conn)
        self.srs = SrsService(conn)

        lesson = self.lessons.get(lesson_id)
        if lesson is None:
            raise ValueError(f"lesson {lesson_id} does not exist")
        self.lesson = lesson
        self.setWindowTitle(
            f"Review — lesson {lesson.order_index}"
            + (f": {lesson.title}" if lesson.title else "")
        )
        self.resize(760, 640)

        self._sentences = self.sentences.list_for_lesson(lesson_id)
        new_ids = {r[1] for r in self.lessons.lesson_words(lesson_id) if r[2] == "new"}
        self._new_word_texts = set()
        for row in new_ids:
            word = self.words.get(row)
            if word is not None:
                self._new_word_texts.add(word.text)
        self._highlighted: set[str] = set()
        self._revealed: set[int] = set()
        self._word_cache: dict[str, object] = {}

        self._build_ui()
        self._font_pt = self._load_font_pt()
        self._apply_font_size()  # applies the font and renders the text

    def _build_ui(self) -> None:
        from PySide6.QtWidgets import QHBoxLayout, QPushButton, QTextBrowser, QVBoxLayout

        # ---- page 1: reading ----
        self.text_browser = QTextBrowser()
        self.text_browser.setOpenLinks(False)
        self.text_browser.anchorClicked.connect(self._on_anchor)

        from langread.app_config import audio_dir

        audio_file = None
        if self.lesson.audio_path:
            candidate = Path(audio_dir()) / self.lesson.audio_path
            audio_file = candidate if candidate.exists() else None
        from langread.ui.review.audio_bar import AudioBar

        self.audio_bar = AudioBar(audio_file, parent=self)

        # explicit navigation to the word review — the audio may be listened
        # to several times before continuing, so nothing auto-advances
        self.word_review_button = QPushButton("Word review →")
        self.word_review_button.clicked.connect(self._enter_word_review)
        cancel_button = QPushButton("Cancel review")
        cancel_button.clicked.connect(self.reject)

        # text size controls (persisted; §8.2 reading comfort)
        self.font_decrease_button = QPushButton("A−")
        self.font_decrease_button.setToolTip("Decrease the text size")
        self.font_decrease_button.clicked.connect(
            lambda: self._change_font_size(-FONT_STEP)
        )
        self.font_increase_button = QPushButton("A+")
        self.font_increase_button.setToolTip("Increase the text size")
        self.font_increase_button.clicked.connect(
            lambda: self._change_font_size(FONT_STEP)
        )

        reading_page = QWidget()
        reading_layout = QVBoxLayout(reading_page)
        reading_layout.addWidget(self.text_browser, 1)
        reading_layout.addWidget(self.audio_bar)
        nav_row = QHBoxLayout()
        nav_row.addWidget(cancel_button)
        nav_row.addWidget(self.font_decrease_button)
        nav_row.addWidget(self.font_increase_button)
        nav_row.addStretch(1)
        nav_row.addWidget(self.word_review_button)
        reading_layout.addLayout(nav_row)

        # ---- page 2: word review ----
        self.review_page = _WordReviewPage(self)
        self.review_page.complete.connect(lambda nxt: self._complete_review(nxt))
        self.review_page.cancelled.connect(self.reject)

        self.stack = QStackedWidget()
        self.stack.addWidget(reading_page)      # 0
        self.stack.addWidget(self.review_page)  # 1

        layout = QVBoxLayout(self)
        layout.addWidget(self.stack)

    # ---- font size (persisted user preference) ----

    def _load_font_pt(self) -> int:
        """The stored text size, or the default font size on first use."""
        stored = SettingsRepo(self.conn).get(FONT_SETTINGS_KEY, default=None)
        if isinstance(stored, (int, float)) and FONT_MIN <= stored <= FONT_MAX:
            return int(stored)
        return self.text_browser.font().pointSize() or 12

    def _apply_font_size(self) -> None:
        font = self.text_browser.font()
        font.setPointSize(self._font_pt)
        self.text_browser.setFont(font)
        self.text_browser.document().setDefaultFont(font)
        self._render_text()

    def _change_font_size(self, delta: int) -> None:
        """A− / A+ : step the text size and remember the choice."""
        new_pt = max(FONT_MIN, min(FONT_MAX, self._font_pt + delta))
        if new_pt == self._font_pt:
            return
        self._font_pt = new_pt
        SettingsRepo(self.conn).set(FONT_SETTINGS_KEY, self._font_pt)
        self._apply_font_size()

    # ---- text rendering (§8.2–8.4) ----

    def _stylesheet(self) -> str:
        """Palette-aware CSS so dark mode renders readable text."""
        from PySide6.QtGui import QPalette

        palette = self.text_browser.palette()
        base = palette.color(QPalette.ColorRole.Base)
        text = palette.color(QPalette.ColorRole.Text).name()
        is_dark = base.lightnessF() < 0.5
        translation = "#b8b8b8" if is_dark else "#606060"
        link = palette.color(QPalette.ColorRole.Link).name()
        return (
            f"body {{ color: {text}; }} "
            f"a {{ color: {text}; text-decoration: none; }} "
            f"a.tr {{ color: {link}; text-decoration: none; }} "
            f"a.new {{ background-color: #ffe08a; color: #202020; }} "
            f".translation {{ color: {translation}; }}"
        )

    def changeEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        from PySide6.QtCore import QEvent

        if event.type() == QEvent.Type.PaletteChange:
            self._render_text()
        super().changeEvent(event)

    def _render_text(self) -> None:
        scrollbar = self.text_browser.verticalScrollBar()
        scroll_position = scrollbar.value()
        # the default stylesheet only applies to HTML set afterwards
        self.text_browser.document().setDefaultStyleSheet(self._stylesheet())
        parts: list[str] = []
        current_para = None
        for index, sentence in enumerate(self._sentences):
            if current_para is not None and sentence.para_index != current_para:
                parts.append("<br><br>")
            current_para = sentence.para_index
            tokens_html: list[str] = []
            for token in sentence.segmentation:
                if is_cjk(token):
                    classes = []
                    if token in self._new_word_texts and token not in self._highlighted:
                        classes.append("new")
                        self._highlighted.add(token)
                    class_attr = f' class="{" ".join(classes)}"' if classes else ""
                    tokens_html.append(
                        f'<a href="w:{html.escape(token, quote=True)}"'
                        f'{class_attr}>{html.escape(token)}</a>'
                    )
                else:
                    tokens_html.append(html.escape(token))
            sentence_html = "".join(tokens_html)
            toggle = ""
            if sentence.translation:
                label = "[hide 译]" if sentence.id in self._revealed else "[译]"
                # trailing separation so the toggle groups with ITS sentence,
                # not the following one
                toggle = f' <a class="tr" href="tr:{sentence.id}">{label}</a>&nbsp;&nbsp; '
            translation_html = ""
            if sentence.id in self._revealed and sentence.translation:
                # §8.4: a line break after the translation keeps space around
                # the translated text before the next sentence starts
                next_sentence = (
                    self._sentences[index + 1]
                    if index + 1 < len(self._sentences) else None
                )
                trailing = (
                    "<br>"
                    if next_sentence is not None
                    and next_sentence.para_index == sentence.para_index
                    else ""
                )
                translation_html = (
                    '<br><span class="translation">'
                    f"{html.escape(sentence.translation)}</span>{trailing}"
                )
            parts.append(f"<span>{sentence_html}{toggle}{translation_html}</span>")
        rendered = "".join(parts)
        self.text_browser.setHtml(rendered)
        self._last_html = rendered
        scrollbar.setValue(scroll_position)

    # ---- interactions (§8.3, §8.4) ----

    def _on_anchor(self, url: QUrl) -> None:
        # CJK characters in hrefs arrive percent-encoded; decode robustly
        from urllib.parse import unquote

        target = unquote(bytes(url.toEncoded()).decode("ascii", "replace"))
        if target.startswith("w:"):
            self._show_word_popup(target[2:])
        elif target.startswith("tr:"):
            sentence_id = int(target[3:])
            if sentence_id in self._revealed:
                self._revealed.discard(sentence_id)
            else:
                self._revealed.add(sentence_id)
            self._render_text()

    def _lookup_word(self, text: str):
        if text not in self._word_cache:
            self._word_cache[text] = self.words.get_by_text(text)
        return self._word_cache[text]

    def _show_word_popup(self, text: str) -> None:
        word = self._lookup_word(text)
        hsk_entry = None
        if word is None:
            matches = self.hsk.find_by_text(text)
            hsk_entry = matches[0] if matches else None
        self._popup = WordPopup(text, word, hsk_entry, self.conn, parent=self)
        self._popup.list_changed.connect(self._on_word_list_changed)
        self._popup.move(QCursor.pos())
        self._popup.show()

    def _on_word_list_changed(self) -> None:
        self._word_cache.clear()  # list states changed; re-resolve

    # ---- word review (§8.6) ----

    def _enter_word_review(self) -> None:
        self.stack.setCurrentIndex(1)
        self.review_page.load_words(self._lesson_learned_words())

    def _lesson_learned_words(self) -> list:
        """This lesson's words that are on the Learned list (§8.6)."""
        rows = self.lessons.lesson_words(self.lesson.id)
        order = {"new": 0, "review": 1}
        words = []
        for _lid, word_id, role in sorted(
            rows, key=lambda r: (order.get(r[2], 2), r[1])
        ):
            word = self.words.get(word_id)
            if word is not None and word.list_state == "learned":
                words.append(word)
        return words

    # ---- completion (§8.7) ----

    def _complete_review(self, open_next: bool) -> None:
        from PySide6.QtWidgets import QMessageBox

        self.audio_bar.stop()  # never keep playing into the next lesson
        ratings = self.review_page.ratings()
        for word_id, rating in ratings.items():
            self.srs.rate_word(word_id, rating, self.lesson.id, device="desktop")
        self.lessons.mark_reviewed(self.lesson.id)
        QMessageBox.information(self, "Review complete",
                                "Review saved. SRS values updated.")
        if open_next:
            next_lesson = self._next_lesson()
            if next_lesson is not None:
                self.hide()
                LessonReviewWindow(self.conn, next_lesson.id,
                                   parent=self.parent()).exec()
        self.accept()

    def _next_lesson(self):
        lessons = self.lessons.list_for_topic(self.lesson.topic_id)
        ids = [lesson.id for lesson in lessons]
        if self.lesson.id in ids:
            index = ids.index(self.lesson.id)
            if index + 1 < len(ids):
                return lessons[index + 1]
        return None

    # ---- closing always stops playback ----

    def reject(self) -> None:
        self.audio_bar.stop()  # Cancel review (§8.7): no audio keeps playing
        super().reject()

    def accept(self) -> None:
        self.audio_bar.stop()
        super().accept()

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        self.audio_bar.stop()
        super().closeEvent(event)


class _WordReviewPage(QWidget):
    """§8.6: rate this lesson's learned words; bulk multi-select."""

    complete = Signal(bool)   # True → open the next lesson afterwards
    cancelled = Signal()

    def __init__(self, owner: "LessonReviewWindow",
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._owner = owner
        self._words: list = []

        from PySide6.QtWidgets import (
            QTableWidget,
            QTableWidgetItem,
            QVBoxLayout,
        )

        intro = QLabel(
            "Words from this lesson on the Learned list — mark each word "
            "(Standard is the default), then complete the review."
        )
        intro.setWordWrap(True)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Word", "Pinyin", "Rating"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        self.bulk_combo = QComboBox()
        for rating in RATINGS:
            self.bulk_combo.addItem(RATING_LABELS[rating], rating)
        bulk_button = QPushButton("Apply to selected")
        bulk_button.clicked.connect(self._apply_bulk)
        select_all_button = QPushButton("Select all")
        select_all_button.clicked.connect(self.table.selectAll)

        complete_button = QPushButton("Mark review complete")
        complete_button.clicked.connect(lambda: self.complete.emit(False))
        next_button = QPushButton("Complete && next lesson")
        next_button.clicked.connect(lambda: self.complete.emit(True))
        cancel_button = QPushButton("Cancel (no changes)")
        cancel_button.clicked.connect(self.cancelled.emit)

        bulk_row = QHBoxLayout()
        bulk_row.addWidget(QLabel("Bulk:"))
        bulk_row.addWidget(self.bulk_combo)
        bulk_row.addWidget(bulk_button)
        bulk_row.addWidget(select_all_button)
        bulk_row.addStretch(1)
        bulk_row.addWidget(cancel_button)
        bulk_row.addWidget(complete_button)
        bulk_row.addWidget(next_button)

        layout = QVBoxLayout(self)
        layout.addWidget(intro)
        layout.addWidget(self.table, 1)
        layout.addLayout(bulk_row)

    def load_words(self, words) -> None:
        from PySide6.QtWidgets import QTableWidgetItem

        self._words = words
        self.table.setRowCount(len(words))
        for row, word in enumerate(words):
            self.table.setItem(row, 0, QTableWidgetItem(word.text))
            self.table.setItem(row, 1, QTableWidgetItem(word.pinyin or ""))
            combo = QComboBox()
            for rating in RATINGS:
                combo.addItem(RATING_LABELS[rating], rating)
            combo.setCurrentIndex(RATINGS.index("standard"))
            self.table.setCellWidget(row, 2, combo)

    def ratings(self) -> dict[int, str]:
        result: dict[int, str] = {}
        for row, word in enumerate(self._words):
            combo = self.table.cellWidget(row, 2)
            result[word.id] = combo.currentData() if combo else "standard"
        return result

    def set_rating(self, row: int, rating: str) -> None:
        combo = self.table.cellWidget(row, 2)
        if combo is not None:
            combo.setCurrentIndex([combo.itemData(i)
                                   for i in range(combo.count())].index(rating))

    def _apply_bulk(self) -> None:
        rating = self.bulk_combo.currentData()
        for row in {index.row() for index in self.table.selectedIndexes()}:
            self.set_rating(row, rating)



