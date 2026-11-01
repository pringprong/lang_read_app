"""M4 unit tests: segmentation service (custom dict, resolution, fallback)."""

from __future__ import annotations

import pytest

from langread.db import connect
from langread.db.repositories import HskRepo, TemplatesRepo, WordsRepo
from langread.services.llm_client import LlmError
from langread.services.segmentation import SegmentationService, is_cjk


class StubLlm:
    """Stands in for LlmClient.chat_json."""

    def __init__(self, result=None, error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.calls: list[str] = []

    def chat_json(self, prompt: str):
        self.calls.append(prompt)
        if self.error is not None:
            raise self.error
        return self.result


@pytest.fixture()
def conn(tmp_path):
    conn = connect(tmp_path / "test.db")
    TemplatesRepo(conn).seed_defaults()
    yield conn
    conn.close()


@pytest.fixture()
def words(conn):
    return WordsRepo(conn)


@pytest.fixture()
def hsk(conn):
    return HskRepo(conn)


def test_is_cjk():
    assert is_cjk("你好")
    assert is_cjk("，") is False
    assert is_cjk("ABC") is False


def test_basic_segmentation_with_punctuation(conn):
    service = SegmentationService(conn)
    tokens = service.segment("你好，世界。")
    texts = [t.text for t in tokens]
    assert texts == ["你好", "，", "世界", "。"]
    assert [t.is_cjk for t in tokens] == [True, False, True, False]


def test_custom_dictionary_makes_app_words_atomic(conn, words):
    # nonsense word: jieba alone would not produce it as one token
    words.get_or_create("咕噜哇", list_state="new", source="manual")
    service = SegmentationService(conn)
    service.refresh_dictionary()  # word added after construction
    tokens = service.segment("咕噜哇")
    assert [t.text for t in tokens] == ["咕噜哇"]


def test_token_resolution_to_word_list(conn, words):
    word, _ = words.get_or_create("厨房", list_state="new", source="manual")
    words.set_translation(word.id, "chúfáng", "kitchen")
    service = SegmentationService(conn)
    token = service.segment("厨房很大")[0]
    assert token.word_id == word.id
    assert token.list_state == "new"
    assert token.pinyin == "chúfáng"
    assert token.definition == "kitchen"


def test_token_resolution_to_hsk_only(conn, hsk):
    hsk.import_rows([("厨房", "chúfáng", "kitchen", 4)])
    service = SegmentationService(conn)
    service.refresh_dictionary()
    token = service.segment("厨房很大")[0]
    assert token.word_id is None
    assert token.list_state is None
    assert token.hsk_word_id is not None
    assert token.pinyin == "chúfáng"


def test_unknown_token_has_no_resolution(conn):
    service = SegmentationService(conn)
    tokens = service.segment("你好")
    # not on any list → unresolved (but still a valid token)
    assert all(t.word_id is None and t.hsk_word_id is None for t in tokens)


def test_needs_fallback_detection(conn, monkeypatch):
    service = SegmentationService(conn)
    # "天气" is a real jieba dictionary word → no fallback
    assert service._needs_fallback(["天气"]) is False
    # single characters and punctuation never trigger fallback
    assert service._needs_fallback(["的", "。"]) is False
    # nonsense multi-char token unknown to jieba → fallback
    assert service._needs_fallback(["焱焱焱焱"]) is True


def test_llm_fallback_used_when_needed(conn, monkeypatch):
    stub = StubLlm(result=["今天", "天气很", "好"])
    service = SegmentationService(conn, llm=stub)
    monkeypatch.setattr(service, "_needs_fallback", lambda raw: True)
    tokens = service.segment("今天天气很好")
    assert [t.text for t in tokens] == ["今天", "天气很", "好"]
    assert len(stub.calls) == 1
    assert "今天天气很好" in stub.calls[0]


def test_llm_fallback_rejected_on_character_mismatch(conn, monkeypatch):
    # LLM returns tokens covering different characters → jieba result kept
    stub = StubLlm(result=["完全", "无关"])
    service = SegmentationService(conn, llm=stub)
    monkeypatch.setattr(service, "_needs_fallback", lambda raw: True)
    texts = [t.text for t in service.segment("今天天气很好")]
    assert "完全" not in texts  # LLM result rejected
    assert "".join(texts) == "今天天气很好"


def test_llm_fallback_error_falls_back_to_jieba(conn, monkeypatch):
    stub = StubLlm(error=LlmError("connection refused"))
    service = SegmentationService(conn, llm=stub)
    monkeypatch.setattr(service, "_needs_fallback", lambda raw: True)
    texts = [t.text for t in service.segment("今天天气很好")]
    assert "".join(texts) == "今天天气很好"


def test_no_llm_configured_means_no_fallback_call(conn):
    service = SegmentationService(conn, llm=None)
    tokens = service.segment("今天天气很好")  # plain jieba path
    assert "".join(t.text for t in tokens) == "今天天气很好"


def test_fallback_disabled_flag(conn, monkeypatch):
    stub = StubLlm(result=["今天", "天气很", "好"])
    service = SegmentationService(conn, llm=stub)
    monkeypatch.setattr(service, "_needs_fallback", lambda raw: True)
    texts = [t.text for t in service.segment("今天天气很好", use_llm_fallback=False)]
    assert "".join(texts) == "今天天气很好"
    assert stub.calls == []
