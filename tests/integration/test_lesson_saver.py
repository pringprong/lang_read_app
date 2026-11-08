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
        from tests.fakes.openai_server import make_mp3

        return make_mp3()


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
    # the review words were learned in a PRIOR lesson (the anchor lesson)
    anchor = LessonsRepo(conn).create(topic_id=topic.id)
    for text in REVIEW:
        word, _ = words.get_or_create(text, list_state="new", source="manual")
        srs.promote_word(word.id, anchor.id)

    # a draft that mirrors what the generation pipeline produces
    from langread.services.segmentation import SegmentationService

    segmentation = SegmentationService(conn)  # dict has NEW/REVIEW words
    paragraphs = []
    for i in range(6):
        text = f"我们学{NEW[i] if i < 5 else '东西'}。{REVIEW[i % 2]}也很有用。"
        paragraphs.append(GeneratedParagraph(
            index=i, text=text, sentences=[text],
            segmentations=[segmentation.token_texts(text)],
        ))
    draft = LessonDraft(
        topic_id=topic.id, topic_name=topic.name,
        new_words=list(NEW), review_words=list(REVIEW), paragraphs=paragraphs,
    )
    yield conn, topic.id, draft, tmp_path / "audio"
    conn.close()


def _saver(conn, audio_dir, tts, translation):
    return LessonSaver(conn, tts=tts, translation=translation, audio_dir=audio_dir)


def test_translate_missing_and_retranslate_sentences(env):
    """translate_missing_sentences: only the untranslated ones (edit flow);
    retranslate_sentences: all of them, replacing stored translations."""
    conn, _topic_id, draft, audio_dir = env
    sentences = SentencesRepo(conn)
    saver = _saver(conn, audio_dir, TtsStub(), TranslationStub())
    lesson = saver.save_lesson(draft)
    stored = sentences.list_for_lesson(lesson.id)
    assert all(s.translation for s in stored)

    # simulate an edit: the first sentence loses its translation
    conn.execute("UPDATE sentences SET translation = NULL WHERE id = ?",
                 (stored[0].id,))
    stub = TranslationStub()
    count = _saver(conn, audio_dir, TtsStub(), stub).translate_missing_sentences(
        lesson.id
    )
    assert count == 1
    assert stub.sentence_calls == [stored[0].text]  # only the missing one
    assert all(s.translation for s in sentences.list_for_lesson(lesson.id))

    # retranslate: every sentence, stored translations replaced
    stub2 = TranslationStub()
    count2 = _saver(conn, audio_dir, TtsStub(), stub2).retranslate_sentences(
        lesson.id
    )
    assert count2 == len(stored)
    assert len(stub2.sentence_calls) == len(stored)
    assert all(s.translation for s in sentences.list_for_lesson(lesson.id))

    # no translation model → a clear error, not a silent no-op
    with pytest.raises(SaveError, match="not configured"):
        _saver(conn, audio_dir, TtsStub(), None).translate_missing_sentences(
            lesson.id
        )
    with pytest.raises(SaveError, match="not configured"):
        _saver(conn, audio_dir, TtsStub(), None).retranslate_sentences(lesson.id)


def test_save_lesson_full_pipeline(env):
    conn, topic_id, draft, audio_dir = env
    saver = _saver(conn, audio_dir, TtsStub(), TranslationStub())
    progress_calls = []
    lesson = saver.save_lesson(
        draft, progress=lambda s, c, t: progress_calls.append((s, c, t))
    )

    assert lesson.status == "complete"
    assert lesson.topic_id == topic_id
    assert lesson.order_index == 2  # the anchor lesson (where the review
    #                          words were learned) took order_index 1
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
        assert word.ease == 2.5
        assert word.first_learned_lesson_id == lesson.id
        assert word.last_seen_lesson_id == lesson.id

    # review words actually APPEARED: appearances recorded per paragraph,
    # last_seen advanced to this lesson (lesson-frequency SRS exposure)
    lessons = LessonsRepo(conn)
    appearance_pairs = set(lessons.appearances_for_lesson(lesson.id))
    for i, text in enumerate(REVIEW):
        word = words.get_by_text(text)
        assert word.last_seen_lesson_id == lesson.id
        # appears in its paragraphs (REVIEW[0] → 0, 2, 4; REVIEW[1] → 1, 3, 5)
        assert (word.id, i) in appearance_pairs
        assert (word.id, i + 2) in appearance_pairs

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

    # audio: one file, one TTS call per sentence (uniform speaking pace),
    # valid MP3 (D-1) — the env draft stores each paragraph as one row
    # containing two sentences, so 6 rows × 2 sentences = 12 calls
    audio_file = audio_dir / f"lesson_{lesson.id}.mp3"
    assert audio_file.exists()
    assert looks_like_mp3(audio_file.read_bytes())
    assert len(saver.tts.calls) == 12

    # progress covered all stages
    stages = {stage for stage, _c, _t in progress_calls}
    assert {"translations", "promoting words", "SRS updates", "audio"} <= stages


def test_finalize_is_idempotent(env):
    conn, _topic, draft, audio_dir = env
    saver = _saver(conn, audio_dir, TtsStub(), TranslationStub())
    lesson = saver.save_lesson(draft)
    sentences_before = SentencesRepo(conn).count_for_lesson(lesson.id)
    review_word = WordsRepo(conn).get_by_text(REVIEW[0])
    last_seen_before = review_word.last_seen_lesson_id
    appearances_before = LessonsRepo(conn).appearances_for_lesson(lesson.id)

    # second run: no-op, nothing duplicated, no re-exposure
    again = saver.finalize_lesson(lesson.id)
    assert again.id == lesson.id and again.status == "complete"
    assert SentencesRepo(conn).count_for_lesson(lesson.id) == sentences_before
    assert WordsRepo(conn).get_by_text(REVIEW[0]).last_seen_lesson_id == last_seen_before
    assert LessonsRepo(conn).appearances_for_lesson(lesson.id) == appearances_before


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
    # words not re-promoted: the lesson tracking is unchanged
    assert WordsRepo(conn).get_by_text(NEW[0]).first_learned_lesson_id == lesson.id


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


def test_audio_one_tts_call_per_sentence(env):
    """Regression: audio is synthesized sentence by sentence, not paragraph
    by paragraph. TTS servers (Kokoro) speak longer single requests faster,
    so the 5-sentence final paragraph (§6.4) played noticeably faster than
    the 3-sentence paragraphs when a whole paragraph was one request."""
    conn, topic_id, _draft, audio_dir = env
    paragraphs = [
        GeneratedParagraph(index=0, text="句子一。句子二。句子三。",
                           sentences=["句子一。", "句子二。", "句子三。"],
                           segmentations=[["句子一"], ["句子二"], ["句子三"]]),
        GeneratedParagraph(index=1,
                           text="句子一。句子二。句子三。句子四。句子五。",
                           sentences=["句子一。", "句子二。", "句子三。",
                                      "句子四。", "句子五。"],
                           segmentations=[["句子一"], ["句子二"], ["句子三"],
                                          ["句子四"], ["句子五"]]),
    ]
    draft = LessonDraft(topic_id=topic_id, topic_name="Cooking",
                        new_words=[], review_words=[], paragraphs=paragraphs)
    stub = TtsStub()
    saver = _saver(conn, audio_dir, stub, TranslationStub())
    lesson = saver.save_lesson(draft)

    assert lesson.status == "complete"
    # one call per sentence: 3 + 5 — never one call per whole paragraph
    assert len(stub.calls) == 8
    assert all(text.count("。") == 1 for text in stub.calls)
    assert stub.calls[:3] == ["句子一。", "句子二。", "句子三。"]


def test_save_lesson_with_wav_tts(env):
    """A TTS server returning WAV still produces a valid single lesson
    audio file (properly merged), stored with the .wav extension."""
    from tests.fakes.openai_server import make_wav

    conn, _topic, draft, audio_dir = env

    class WavTtsStub:
        def __init__(self) -> None:
            self.calls = 0

        def synthesize(self, text: str) -> bytes:
            self.calls += 1
            return make_wav()

    saver = _saver(conn, audio_dir, WavTtsStub(), TranslationStub())
    lesson = saver.save_lesson(draft)
    assert lesson.status == "complete"
    assert lesson.audio_path == f"lesson_{lesson.id}.wav"
    audio_file = audio_dir / lesson.audio_path
    assert audio_file.exists()
    from langread.services.tts import detect_audio_format

    data = audio_file.read_bytes()
    assert detect_audio_format(data) == "wav"
    # 6 rows × 2 sentences each = 12 calls, merged into one file:
    # data payload = 12 × 100 samples × 2 bytes
    assert data[44:] == make_wav(100)[44:] * 12




def test_appearances_follow_the_final_text(env):
    """Apex behavior of the appearance step: what is recorded follows the
    FINAL (hand-edited) text — a learned word removed while editing is NOT
    an exposure, and a different learned word typed in IS one."""
    from langread.services.segmentation import SegmentationService
    from langread.services.srs import SrsService

    conn, topic_id, draft, audio_dir = env
    words = WordsRepo(conn)
    lessons = LessonsRepo(conn)
    srs = SrsService(conn)

    # a third learned word the original draft never mentions
    extra, _ = words.get_or_create("咕复三", list_state="new", source="manual")
    anchor = lessons.create(topic_id=topic_id)
    srs.promote_word(extra.id, anchor.id)
    removed_last_seen_before = words.get_by_text(REVIEW[0]).last_seen_lesson_id

    # hand edits (wizard step 3): REVIEW[0] removed from every paragraph,
    # paragraph 1 gains the extra learned word
    from langread.services.generation import split_sentences

    segmentation = SegmentationService(conn)
    for paragraph in draft.paragraphs:
        paragraph.text = paragraph.text.replace(f"{REVIEW[0]}也很有用。", "")
        paragraph.sentences = split_sentences(paragraph.text)
        paragraph.segmentations = [
            segmentation.token_texts(s) for s in paragraph.sentences
        ]
    p1 = draft.paragraphs[1]
    p1.text = f"我们学{NEW[1]}。咕复三也很有用。"
    p1.sentences = [p1.text]
    p1.segmentations = [segmentation.token_texts(p1.text)]

    lesson = _saver(conn, audio_dir, TtsStub(), TranslationStub()).save_lesson(draft)
    pairs = set(lessons.appearances_for_lesson(lesson.id))

    removed = words.get_by_text(REVIEW[0])
    assert removed.id not in {word_id for word_id, _para in pairs}
    assert removed.last_seen_lesson_id == removed_last_seen_before  # unchanged
    roles = dict((r[1], r[2]) for r in lessons.lesson_words(lesson.id))
    assert removed.id not in roles

    assert (extra.id, 1) in pairs
    assert roles[extra.id] == "review"
    assert words.get_by_text("咕复三").last_seen_lesson_id == lesson.id
