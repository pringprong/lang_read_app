"""Word import flows (requirements §5): paste, manual, HSK, and list moves.

Whenever a word is added to the words table and a matching HSK entry exists,
it is linked (hsk_word_id) and the HSK entry's app_state is kept in sync,
so definitions/pinyin come for free for HSK vocabulary.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from langread.db.repositories import HskRepo, TopicsRepo, WordsRepo
from langread.models import HskWord, Word
from langread.services.segmentation import SegmentationService


@dataclass(frozen=True)
class ParsedWord:
    """One distinct word found in pasted text, with existing context."""

    text: str
    existing: Word | None = None   # already on New/Learned/Basic
    hsk: HskWord | None = None     # bundled HSK entry (info display)


@dataclass(frozen=True)
class ImportSummary:
    added_new: int = 0
    added_basic: int = 0
    already_known: int = 0  # words that stayed on their existing list


class WordImportService:
    def __init__(self, conn: sqlite3.Connection,
                 segmentation: SegmentationService | None = None) -> None:
        self.conn = conn
        self.words = WordsRepo(conn)
        self.hsk = HskRepo(conn)
        self.topics = TopicsRepo(conn)
        if segmentation is None:
            # The bundled HSK dataset feeds the segmentation dictionary, so
            # make sure it is imported before building it (fresh databases).
            from langread.services.hsk import HskService

            HskService(conn).import_if_needed()
            segmentation = SegmentationService(conn)
        self.segmentation = segmentation

    # ---- shared helpers ----

    def _link_hsk(self, word: Word) -> Word:
        """Attach HSK info (id, pinyin, definition) if available."""
        matches = self.hsk.find_by_text(word.text)
        if not matches or word.hsk_word_id is not None:
            return word
        entry = matches[0]
        if word.pinyin is None:
            self.words.set_translation(word.id, entry.pinyin, entry.definition)
        self.conn.execute(
            "UPDATE words SET hsk_word_id = ? WHERE id = ?", (entry.id, word.id)
        )
        self.hsk.set_app_state(entry.id, word.list_state)
        return self.words.get(word.id)  # type: ignore[return-value]

    def _create_word(self, text: str, list_state: str, source: str,
                     topic_id: int | None) -> tuple[Word, bool]:
        word, created = self.words.get_or_create(
            text, list_state=list_state, source=source
        )
        if created:
            word = self._link_hsk(word)
            if topic_id is not None:
                self.words.associate_topic(word.id, topic_id)
        return word, created

    # ---- §5.1 paste flow ----

    def parse_pasted_text(self, text: str) -> list[ParsedWord]:
        """Distinct CJK words in order of first appearance, with context."""
        tokens = self.segmentation.segment(text)
        seen: set[str] = set()
        result: list[ParsedWord] = []
        for token in tokens:
            if not token.is_cjk or token.text in seen:
                continue
            seen.add(token.text)
            hsk_matches = self.hsk.find_by_text(token.text)
            result.append(ParsedWord(
                text=token.text,
                existing=(
                    self.words.get_by_text(token.text)
                    if token.word_id is None
                    else self.words.get(token.word_id)
                ),
                hsk=hsk_matches[0] if hsk_matches else None,
            ))
        return result

    def import_from_paste(self, parsed: list[ParsedWord],
                          marked_new: set[str],
                          topic_id: int | None = None) -> ImportSummary:
        """Marked words → New list; the rest (unknown to the app) → Basic (§5.1)."""
        added_new = added_basic = already_known = 0
        for item in parsed:
            if item.existing is not None:
                already_known += 1
                continue
            if item.text in marked_new:
                self._create_word(item.text, "new", "paste", topic_id)
                added_new += 1
            else:
                self._create_word(item.text, "basic", "paste", topic_id)
                added_basic += 1
        return ImportSummary(added_new, added_basic, already_known)

    # ---- §5.2 manual entry ----

    def add_manual(self, text: str,
                   topic_id: int | None = None) -> tuple[Word, bool]:
        text = text.strip()
        if not text:
            raise ValueError("empty word")
        return self._create_word(text, "new", "manual", topic_id)

    # ---- §5.5 HSK flow ----

    def add_from_hsk(self, hsk_word: HskWord, target: str = "new",
                     topic_id: int | None = None) -> tuple[Word, bool]:
        """Add an HSK word to the New or Basic list, with pinyin/definition."""
        if target not in ("new", "basic"):
            raise ValueError(f"invalid target list: {target}")
        word, created = self.words.get_or_create(
            hsk_word.text, list_state=target, source="hsk",
            hsk_word_id=hsk_word.id,
            pinyin=hsk_word.pinyin, definition=hsk_word.definition,
        )
        if created:
            if topic_id is not None:
                self.words.associate_topic(word.id, topic_id)
            self.hsk.set_app_state(hsk_word.id, target)
        return word, created

    # ---- §5.4 basic → new ----

    def move_basic_to_new(self, word_id: int) -> Word:
        self.words.move_to_state(word_id, "new")
        word = self.words.get(word_id)
        assert word is not None
        return word

    def move_new_to_basic(self, word_id: int) -> Word:
        """Mistake fix: a word added to New in error (§4.4)."""
        self.words.move_to_state(word_id, "basic")
        word = self.words.get(word_id)
        assert word is not None
        return word
