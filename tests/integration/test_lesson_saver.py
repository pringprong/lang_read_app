"""M7 integration tests: lesson save pipeline (§7.9)."""

from __future__ import annotations

import pytest

from langread.db import connect
from langread.db.repositories import (
    HskRepo,
    LessonsRepo,
    SentencesRepo,
    TemplatesRepo,
    TopicsRepo,
    WordsRepo,
)
from langread.services.generation import LessonDraft, GeneratedParagraph
from langread.services.lesson_saver import LessonSaver, SaveError
from langread.services.srs import SrsService
from langread.services.tts import looks_like_mp3
from tests.integration.test_generation import NEW, REVIEW


class TtsStub:
    def __init__(self, fail_on_calls: set[int] | None = None) -> None:
        self.calls: list[str] = []
        self.fail_on_calls = fail_on_calls or set()

    def synthesize(self, text: str) -> bytes:
        self.calls.append(text)
        if len(self.calls) in self.fail_on_calls:
            raise RuntimeError("tts is down")
        return b"ID3" + b"\x00" * 16


class TranslationStub:
    def __init__(self) -> None:
        self.sentence_calls: list[str] = []
        self.word_calls: list[str] = []

    def translate_sentence(self, sentence: str) -> str:
        self.sentence_calls.append(sentence)
        return f"EN: {sentence}"

    def translate_word(self, word: str):
        self.word_calls.append(word)
        return (f"PIN[{word}]", f"DEF[{word}]")


@pytest.fixture()
def env(tmp_path):
    """conn, topic, draft, audio_dir with review words already learned."""
    conn = connect(tmp_path / "test.db")
    TemplatesRepo(conn).seed_defaults()
    topic = TopicsRepo(conn).create("Cooking")
    words = WordsRepo(conn)
    srs = SrsService(conn)
    for text in NEW:
        words.get_or_create(text, list_state="new", source="manual")
    for text in REVIEW:
        word, _ = words.get_or_create(text, list_state="new", source="manual")
        srs.promote_word(word.id, now="2026-11-01T00:00:00+00:00")

    # a draft that mirrors what the generation pipeline produces
    paragraphs = []
    for i in range(6):
        text = f"我们学{NEW[i] if i < 5 else '东西'}。{REVIEW[i % 2]}也很有用。"
        paragraphs.append(GeneratedParagraph(
            index=i, text=text, sentences=[text],
            segmentations=[[c for c in text]],
        ))
    draft = LessonDraft(
        topic_id=topic.id, topic_name=topic.name,
        new_words=list(NEW), review_words=list(REVIEW), paragraphs=paragraphs,
    )
    yield conn, topic.id, draft, tmp_path / "audio"
    conn.close()


def _saver(conn, audio_dir, tts, translation):
    return LessonSaver(conn, tts=tts, translation=translation, audio_dir=audio_dir)


def test_save_lesson_full_pipeline(env):
    conn, topic_id, draft, audio_dir = env
    saver = _saver(conn, audio_dir, TtsStub(), TranslationStub())
    progress_calls = []
    lesson = saver.save_lesson(
        draft, progress=lambda s, c, t: progress_calls.append((s, c, t))
    )

    assert lesson.status == "complete"
    assert lesson.topic_id == topic_id
    assert lesson.order_index == 1
    assert lesson.audio_path == f"lesson_{lesson.id}.mp3"

    # sentences stored with translations and segmentations
    sentences = SentencesRepo(conn).list_for_lesson(lesson.id)
    assert len(sentences) == 6
    assert all(s.translation and s.translation.startswith("EN: ") for s in sentences)
    assert all(s.segmentation for s in sentences)

    # new words promoted with pinyin/definition and initial SRS (§7.9.3)
    words = WordsRepo(conn)
    for text in NEW:
        word = words.get_by_text(text)
        assert word.list_state == "learned"
        assert word.pinyin == f"PIN[{text}]"
        assert word.definition == f"DEF[{text}]"
        assert word.interval_days == 1.0 and word.reps == 1

    # review words got exposure growth (§7.9.4): interval 1 → 2.5
    for text in REVIEW:
        word = words.get_by_text(text)
        assert word.interval_days == pytest.approx(2.5)

    # lesson_words roles recorded
    roles = dict((r[1], r[2]) for r in LessonsRepo(conn).lesson_words(lesson.id))
    for text in NEW:
        assert roles[words.get_by_text(text).id] == "new"
    for text in REVIEW:
        assert roles[words.get_by_text(text).id] == "review"

    # word-topic associations
    for text in NEW:
        word = words.get_by_text(text)
        assert [t.name for t in words.topics_for_word(word.id)] == ["Cooking"]

    # audio: one file, one TTS call per paragraph, valid MP3 (D-1)
    audio_file = audio_dir / f"lesson_{lesson.id}.mp3"
    assert audio_file.exists()
    assert looks_like_mp3(audio_file.read_bytes())
    assert len(saver.tts.calls) == 6

    # progress covered all stages
    stages = {stage for stage, _c, _t in progress_calls}
    assert {"translations", "promoting words", "SRS updates", "audio"} <= stages


def test_finalize_is_idempotent(env):
    conn, _topic, draft, audio_dir = env
    saver = _saver(conn, audio_dir, TtsStub(), TranslationStub())
    lesson = saver.save_lesson(draft)
    sentences_before = SentencesRepo(conn).count_for_lesson(lesson.id)
    review_word = WordsRepo(conn).get_by_text(REVIEW[0])
    interval_before = review_word.interval_days

    # second run: no-op, nothing duplicated, no re-exposure
    again = saver.finalize_lesson(lesson.id)
    assert again.id == lesson.id and again.status == "complete"
    assert SentencesRepo(conn).count_for_lesson(lesson.id) == sentences_before
    assert WordsRepo(conn).get_by_text(REVIEW[0]).interval_days == interval_before


def test_interrupted_save_is_resumable(env):
    conn, _topic, draft, audio_dir = env
    # TTS fails on every call → pipeline leaves an incomplete lesson
    failing = _saver(
        conn, audio_dir, TtsStub(fail_on_calls={1, 2, 3, 4, 5, 6}), TranslationStub()
    )
    with pytest.raises(SaveError):
        failing.save_lesson(draft)

    lessons = LessonsRepo(conn)
    incomplete = lessons.list_by_status("incomplete")
    assert len(incomplete) == 1
    lesson = incomplete[0]
    # translations and word promotion already applied
    sentences = SentencesRepo(conn).list_for_lesson(lesson.id)
    assert all(s.translation for s in sentences)
    assert WordsRepo(conn).get_by_text(NEW[0]).list_state == "learned"

    # resume with a working TTS → completes, audio exists
    working = _saver(conn, audio_dir, TtsStub(), TranslationStub())
    finished = working.finalize_lesson(lesson.id)
    assert finished.status == "complete"
    assert (audio_dir / f"lesson_{lesson.id}.mp3").exists()
    # words not re-promoted, review not re-exposed (already done pre-failure)
    assert WordsRepo(conn).get_by_text(NEW[0]).reps == 1


def test_tts_required_for_save(env):
    conn, _topic, draft, audio_dir = env
    saver = _saver(conn, audio_dir, tts=None, translation=TranslationStub())
    with pytest.raises(SaveError, match="text-to-speech"):
        saver.save_lesson(draft)


def test_translation_optional(env):
    conn, _topic, draft, audio_dir = env
    # no translation service: sentences stay untranslated, words get pypinyin
    saver = _saver(conn, audio_dir, TtsStub(), translation=None)
    lesson = saver.save_lesson(draft)
    assert lesson.status == "complete"
    sentences = SentencesRepo(conn).list_for_lesson(lesson.id)
    assert all(s.translation is None for s in sentences)
    word = WordsRepo(conn).get_by_text(NEW[0])
    assert word.list_state == "learned"
    assert word.pinyin  # pypinyin fallback
    assert word.definition is None


def test_hsk_link_promoted_to_learned(env):
    conn, _topic, draft, audio_dir = env
    from langread.services.hsk import HskService

    HskService(conn).import_if_needed()
    # replace the first draft word with a real HSK word
    hsk_word = "桌子"
    draft.new_words[0] = hsk_word
    draft.paragraphs[0].text = f"我们学{hsk_word}。"
    draft.paragraphs[0].sentences = [draft.paragraphs[0].text]

    saver = _saver(conn, audio_dir, TtsStub(), TranslationStub())
    lesson = saver.save_lesson(draft)
    assert lesson.status == "complete"
    words = WordsRepo(conn)
    word = words.get_by_text(hsk_word)
    assert word.list_state == "learned"
    assert word.hsk_word_id is not None
    assert HskRepo(conn).find_by_text(hsk_word)[0].app_state == "learned"


