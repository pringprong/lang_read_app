"""M7 unit tests: translation service (sentence + word, pypinyin fallback)."""

from __future__ import annotations

import pytest

from langread.db import connect
from langread.db.repositories import TemplatesRepo
from langread.services.llm_client import LlmError
from langread.services.translation import (
    TranslationError,
    TranslationService,
    pinyin_fallback,
)


class StubLlm:
    def __init__(self, sentence_reply="OK", word_result=None, error=None) -> None:
        self.sentence_reply = sentence_reply
        self.word_result = word_result
        self.error = error

    def chat(self, prompt: str) -> str:
        if self.error:
            raise self.error
        return self.sentence_reply

    def chat_json(self, prompt: str):
        if self.error:
            raise self.error
        return self.word_result


@pytest.fixture()
def conn(tmp_path):
    conn = connect(tmp_path / "test.db")
    TemplatesRepo(conn).seed_defaults()
    yield conn
    conn.close()


def test_translate_sentence_strips_wrappers(conn):
    service = TranslationService(conn, llm=StubLlm(sentence_reply='"Hello there."'))
    assert service.translate_sentence("你好。") == "Hello there."


def test_translate_sentence_requires_llm(conn):
    with pytest.raises(TranslationError, match="not configured"):
        TranslationService(conn, llm=None).translate_sentence("你好。")


def test_translate_sentence_wraps_llm_errors(conn):
    service = TranslationService(
        conn, llm=StubLlm(error=LlmError("connection refused"))
    )
    with pytest.raises(TranslationError, match="connection refused"):
        service.translate_sentence("你好。")


def test_translate_word_parses_json(conn):
    service = TranslationService(
        conn, llm=StubLlm(word_result={"pinyin": "chú fáng", "definition": "kitchen"})
    )
    assert service.translate_word("厨房") == ("chú fáng", "kitchen")


def test_translate_word_invalid_shapes(conn):
    # non-dict JSON → (None, None), not an exception
    service = TranslationService(conn, llm=StubLlm(word_result=["not", "a", "dict"]))
    assert service.translate_word("厨房") == (None, None)
    service = TranslationService(conn, llm=StubLlm(word_result={"pinyin": "  "}))
    assert service.translate_word("厨房") == (None, None)
    service = TranslationService(conn, llm=StubLlm(error=LlmError("boom")))
    assert service.translate_word("厨房") == (None, None)
    assert TranslationService(conn, llm=None).translate_word("厨房") == (None, None)


def test_pinyin_fallback_with_tones():
    assert pinyin_fallback("厨房") == "chú fáng"
    assert pinyin_fallback("你好") == "nǐ hǎo"
