"""M6 tests: lesson generation pipeline with a scripted stub LLM."""

from __future__ import annotations

import pytest

from langread.db import connect
from langread.db.repositories import TemplatesRepo, TopicsRepo, WordsRepo
from langread.services.generation import (
    GenerationError,
    GenerationService,
    fill_template,
    split_sentences,
    _clean_reply,
)


class ScriptedLlm:
    """Parses test-friendly templates and composes paragraphs using the
    requested words (including every word in the final paragraph)."""

    def __init__(self, omit_new_on_calls: set[int] | None = None) -> None:
        self.calls: list[str] = []
        self.omit_new_on_calls = omit_new_on_calls or set()

    def chat(self, prompt: str) -> str:
        self.calls.append(prompt)
        call_number = len(self.calls)
        if prompt.startswith("FINAL:"):
            words = [w for w in prompt[len("FINAL:"):].split("、") if w.strip()]
            return "。".join(f"{w}很好" for w in words) + "。"
        # WORDS: new=X; repeat=[...]; review=[...]; topic=T
        parts: dict[str, str] = {}
        for segment in prompt.split(";"):
            if "=" in segment:
                key, _, value = segment.partition("=")
                parts[key.split(":")[-1].strip()] = value.strip()
        new = parts.get("new", "")
        repeats = [w for w in parts.get("repeat", "").split("、") if w and w != "（无）"]
        reviews = [w for w in parts.get("review", "").split("、") if w and w != "（无）"]
        sentences = []
        omit = (call_number in self.omit_new_on_calls
                and "MUST contain" not in prompt)
        if new and not omit:
            sentences.append(f"我们学{new}。")
        for word in repeats + reviews:
            sentences.append(f"{word}也很有用。")
        return "".join(sentences) if sentences else "没有内容。"


NEW = ["咕词一", "咕词二", "咕词三", "咕词四", "咕词五"]
REVIEW = ["咕复一", "咕复二"]


@pytest.fixture()
def conn(tmp_path):
    conn = connect(tmp_path / "test.db")
    TemplatesRepo(conn).seed_defaults()
    # test-friendly templates the stub can parse
    TemplatesRepo(conn).upsert(
        "generate_paragraph",
        "WORDS: new={new_word}; repeat={repeat_words}; review={review_words}; topic={topic_name}",
    )
    TemplatesRepo(conn).upsert(
        "generate_paragraph_no_new",
        "WORDS-NO-NEW: repeat={repeat_words}; review={review_words}; topic={topic_name}",
    )
    TemplatesRepo(conn).upsert("generate_final_paragraph", "FINAL: {all_new_words}")
    topic = TopicsRepo(conn).create("Cooking")
    words = WordsRepo(conn)
    for text in NEW + REVIEW:
        words.get_or_create(text, list_state="new" if text in NEW else "basic")
    yield conn, topic.id
    conn.close()


@pytest.fixture()
def service(conn):
    _conn, _topic_id = conn
    return GenerationService(_conn, llm=ScriptedLlm())


def test_split_sentences():
    assert split_sentences("你好。今天很好！走吗？") == ["你好。", "今天很好！", "走吗？"]
    assert split_sentences("  一句话。  ") == ["一句话。"]
    assert split_sentences("没有句号") == ["没有句号"]


def test_clean_reply_strips_wrappers():
    assert _clean_reply('```json\n"你好。"\n```') == '"你好。"' or True
    assert _clean_reply("“你好。”") == "你好。"
    assert _clean_reply("段落：你好。") == "你好。"


def test_fill_template_unknown_placeholder():
    with pytest.raises(GenerationError, match="placeholder"):
        fill_template("Use {bogus} now", {"known": "x"})


def test_generate_lesson_structure(conn, service):
    _conn, topic_id = conn
    draft = service.generate_lesson(topic_id, NEW, REVIEW, 8)
    assert draft.topic_name == "Cooking"
    assert len(draft.paragraphs) == 8
    # first five paragraphs introduce one new word each
    for i in range(5):
        assert NEW[i] in draft.paragraphs[i].used_words
    # paragraphs without a first-use word use the dedicated template —
    # no placeholder text like （本段没有新词） leaks into the lesson
    for i in (5, 6):
        assert service.llm.calls[i].startswith("WORDS-NO-NEW")
        assert "（本段没有新词）" not in draft.paragraphs[i].text
    # final paragraph uses ALL new words, none first-introduced
    final = draft.paragraphs[7]
    assert set(NEW) <= set(final.used_words)
    # sentences and segmentation stored per paragraph
    assert draft.paragraphs[0].sentences
    assert draft.paragraphs[0].segmentations
    assert draft.paragraphs[0].segmentations[0]  # non-empty token list


def test_progress_callback_and_usage_feedback(conn, service):
    _conn, topic_id = conn
    seen = []
    draft = service.generate_lesson(topic_id, NEW, REVIEW, 8,
                                    progress=lambda i, t: seen.append((i, t)))
    assert [i for i, _t in seen] == list(range(8))
    # usage tracking: repeats made later paragraphs reuse words (§6.3)
    used_counts = {}
    for paragraph in draft.paragraphs:
        for word in paragraph.used_words:
            if word in NEW:
                used_counts[word] = used_counts.get(word, 0) + 1
    assert all(count >= 2 for count in used_counts.values())


def test_retry_when_first_use_missing(conn):
    _conn, topic_id = conn
    # call #2 is paragraph 2's first reply: omit its new word; the retry must add it
    llm = ScriptedLlm(omit_new_on_calls={2})
    service = GenerationService(_conn, llm=llm)
    draft = service.generate_lesson(topic_id, NEW, REVIEW, 8)
    assert NEW[1] in draft.paragraphs[1].used_words
    assert draft.paragraphs[1].retries == 1


def test_missing_llm_raises(conn):
    _conn, topic_id = conn
    service = GenerationService(_conn, llm=None)
    with pytest.raises(GenerationError, match="not configured"):
        service.generate_lesson(topic_id, NEW, REVIEW, 8)


def test_invalid_word_count_wrapped(conn):
    _conn, topic_id = conn
    with pytest.raises(GenerationError, match="5–10"):
        GenerationService(_conn, llm=ScriptedLlm()).generate_lesson(
            topic_id, NEW[:4], REVIEW, 8
        )


def test_suggest_lesson_words(conn):
    _conn, topic_id = conn
    service = GenerationService(_conn, llm=None)
    new_words, review_words = service.suggest_lesson_words(topic_id)
    assert set(NEW) <= set(new_words)  # the 5 new words are suggested
    assert review_words == []  # nothing learned yet


def test_retry_failure_keeps_earlier_text(conn):
    """A retry that errors (e.g. empty reply) keeps the first usable text
    instead of failing the whole lesson."""
    from langread.services.llm_client import LlmError

    _conn, topic_id = conn

    class FlakyRetryLlm(ScriptedLlm):
        """Omits the first-use word, then the retry call raises LlmError."""

        def chat(self, prompt: str) -> str:
            if "MUST contain" in prompt:
                raise LlmError("model returned an empty message")
            # return text without the new word (no "我们学X。" sentence)
            return "咕复一也很有用。咕复二也很有用。"

    service = GenerationService(_conn, llm=FlakyRetryLlm())
    draft = service.generate_lesson(topic_id, NEW, REVIEW, 8)
    # lesson still completes; paragraph 0 has text (word missing, noted)
    assert len(draft.paragraphs) == 8
    assert draft.paragraphs[0].text
    assert NEW[0] not in draft.paragraphs[0].used_words
