"""Chinese word segmentation service (requirements §4.3, §5.1, D-5).

Primary engine: jieba, loaded with a custom dictionary built from the app's
own word lists + HSK vocabulary, so any word the app knows is segmented
atomically. LLM fallback: when jieba produces a suspicious multi-character
token that is in neither the app dictionaries nor jieba's own dictionary,
the sentence is re-segmented via the `segment_text` prompt template.

Tokens carry resolution info (word-list membership, HSK link, pinyin,
definition) for the review-time word popups (§8.3) and usage tracking (§7.6).
"""

from __future__ import annotations

import logging
import re
import sqlite3
from dataclasses import dataclass

import jieba

from langread.db.repositories import HskRepo, TemplatesRepo, WordsRepo
from langread.models import HskWord, Word
from langread.services.llm_client import LlmClient, LlmError

_CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")


def is_cjk(text: str) -> bool:
    """True if the string contains at least one CJK ideograph."""
    return bool(_CJK_RE.search(text))


@dataclass(frozen=True)
class Token:
    """One segment of a sentence plus its word-list resolution."""

    text: str
    is_cjk: bool
    word_id: int | None = None        # words-table id when on New/Learned/Basic
    list_state: str | None = None     # 'new' | 'learned' | 'basic' | None
    hsk_word_id: int | None = None    # HSK link when not on any app list
    pinyin: str | None = None
    definition: str | None = None


class SegmentationService:
    """Segment text and resolve tokens against the word lists.

    jieba keeps global (process-wide) state; `refresh_dictionary()` reloads
    the custom dictionary after word-list changes.
    """

    DICT_FREQ = 1_000_000  # app words outrank everything in jieba's DAG

    def __init__(self, conn: sqlite3.Connection,
                 llm: LlmClient | None = None) -> None:
        jieba.setLogLevel(logging.WARNING)
        self.conn = conn
        self.words_repo = WordsRepo(conn)
        self.hsk_repo = HskRepo(conn)
        self.templates = TemplatesRepo(conn)
        self.llm = llm
        self._words_map: dict[str, Word] = {}
        self._hsk_map: dict[str, HskWord] = {}
        self._dict_version: tuple[int, int] | None = None
        self.refresh_dictionary()

    # ---- dictionary management ----

    def refresh_dictionary(self) -> None:
        """(Re)load app words and HSK vocabulary into jieba and the maps.

        The version is the per-list word counts + HSK count, so any
        list-to-list move or addition triggers a refresh.
        """
        jieba.initialize()
        words: list[Word] = []
        state_counts: dict[str, int] = {}
        for state in ("new", "learned", "basic"):
            state_words = self.words_repo.list_by_state(state)
            state_counts[state] = len(state_words)
            words.extend(state_words)
        hsk_words = self.hsk_repo.list_all()
        version = (state_counts["new"], state_counts["learned"],
                   state_counts["basic"], len(hsk_words))
        if version == self._dict_version:
            return
        self._words_map = {w.text: w for w in words}
        self._hsk_map = {h.text: h for h in hsk_words}
        for text in list(self._words_map) + list(self._hsk_map):
            jieba.add_word(text, freq=self.DICT_FREQ)
        self._dict_version = version

    # ---- segmentation ----

    def segment(self, text: str, *, use_llm_fallback: bool = True) -> list[Token]:
        """Segment `text` into tokens with word-list resolution."""
        raw = [t for t in jieba.cut(text) if t.strip()]
        if use_llm_fallback and self.llm is not None and self._needs_fallback(raw):
            fallback = self._llm_resegment(text)
            if fallback is not None:
                return fallback
        return self._resolve(raw)

    def token_texts(self, text: str) -> list[str]:
        return [token.text for token in self.segment(text)]

    # ---- fallback logic ----

    def _needs_fallback(self, raw_tokens: list[str]) -> bool:
        """A multi-character CJK token unknown to both the app and jieba
        is a sign of mis-segmentation (usually HMM-glued characters)."""
        for token in raw_tokens:
            if (
                len(token) >= 2
                and is_cjk(token)
                and token not in self._words_map
                and token not in self._hsk_map
            ):
                freq = jieba.dt.FREQ.get(token)
                if not freq:
                    return True
        return False

    def _llm_resegment(self, text: str) -> list[Token] | None:
        """Re-segment via the LLM; returns None if unavailable/invalid."""
        template = self.templates.get("segment_text")
        if not template:
            return None
        prompt = template.replace("{text}", text)
        try:
            result = self.llm.chat_json(prompt) if self.llm else None
        except LlmError:
            return None
        if not isinstance(result, list) or not all(isinstance(x, str) for x in result):
            return None
        cleaned = [x.strip() for x in result if x.strip()]
        if not cleaned:
            return None
        # The LLM split must cover exactly the same characters (D-5 integrity).
        if self._signature("".join(cleaned)) != self._signature(text):
            return None
        return self._resolve(cleaned)

    @staticmethod
    def _signature(text: str) -> str:
        return "".join(ch for ch in text if is_cjk(ch))

    # ---- resolution ----

    def _resolve(self, raw_tokens: list[str]) -> list[Token]:
        tokens: list[Token] = []
        for text in raw_tokens:
            cjk = is_cjk(text)
            word = self._words_map.get(text)
            if word is not None:
                tokens.append(Token(
                    text=text, is_cjk=cjk, word_id=word.id,
                    list_state=word.list_state, pinyin=word.pinyin,
                    definition=word.definition,
                ))
                continue
            hsk = self._hsk_map.get(text)
            if hsk is not None:
                tokens.append(Token(
                    text=text, is_cjk=cjk, hsk_word_id=hsk.id,
                    pinyin=hsk.pinyin, definition=hsk.definition,
                ))
                continue
            tokens.append(Token(text=text, is_cjk=cjk))
        return tokens

