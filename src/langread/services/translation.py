"""Translation model service (requirements §9.2).

Word definitions/pinyin (with a pypinyin cross-check/fallback) and
whole-sentence translations, both via the editable prompt templates.
"""

from __future__ import annotations

import re
import sqlite3

from langread.db.repositories import TemplatesRepo
from langread.services.llm_client import LlmClient, LlmError


class TranslationError(Exception):
    """Failure calling the translation model."""


def _clean_translation(text: str) -> str:
    cleaned = text.strip()
    cleaned = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", cleaned).strip()
    cleaned = cleaned.strip('"“”').strip()
    return cleaned


def pinyin_fallback(word: str) -> str:
    """Offline pinyin with tone marks via pypinyin (D-4 cross-check)."""
    from pypinyin import Style, pinyin

    parts = pinyin(word, style=Style.TONE, errors="ignore")
    return " ".join("".join(part) for part in parts)


class TranslationService:
    def __init__(self, conn: sqlite3.Connection, llm: LlmClient | None = None,
                 dictionary=None) -> None:
        """`dictionary` is an optional DictionaryService — when it has an
        entry for a word, translate_word() returns it directly and the
        model is not called (definitions plan §4.1)."""
        self.templates = TemplatesRepo(conn)
        self.llm = llm
        self.dictionary = dictionary

    # ---- sentence translations (§7.9 step 2) ----

    def translate_sentence(self, sentence: str) -> str:
        if self.llm is None:
            raise TranslationError(
                "translation model is not configured "
                "(open Model settings to set it)"
            )
        template = self.templates.get("translate_sentence")
        if not template:
            raise TranslationError("missing template: translate_sentence")
        prompt = template.replace("{sentence}", sentence)
        try:
            reply = self.llm.chat(prompt)
        except LlmError as exc:
            raise TranslationError(f"sentence translation failed: {exc}") from exc
        return _clean_translation(reply)

    # ---- word pinyin + definition (§7.9 step 3) ----

    def translate_word(self, word: str) -> tuple[str | None, str | None]:
        """Return (pinyin, definition); (None, None) if the model can't answer.

        The offline dictionary is checked first (definitions plan §4.1):
        a hit is returned directly and the model is never called.
        """
        if self.dictionary is not None:
            entry = self.dictionary.lookup(word)
            if entry is not None and (entry.pinyin or entry.definition):
                return entry.pinyin, entry.definition
        if self.llm is None:
            return None, None
        template = self.templates.get("translate_word")
        if not template:
            return None, None
        prompt = template.replace("{word}", word)
        try:
            result = self.llm.chat_json(prompt)
        except LlmError:
            return None, None
        if not isinstance(result, dict):
            return None, None
        pinyin = result.get("pinyin")
        definition = result.get("definition")
        return (
            str(pinyin).strip() if isinstance(pinyin, str) and pinyin.strip() else None,
            str(definition).strip()
            if isinstance(definition, str) and definition.strip()
            else None,
        )
