"""Lesson save pipeline (requirements §7.9) — atomic and resumable.

Steps (each idempotent, so an interrupted save can be resumed by re-running
`finalize_lesson` on the incomplete lesson):
  A. create the lesson row (status='incomplete'), sentences, lesson_words
     (new words; review roles are derived from actual appearances in step D)
  B. whole-sentence translations (skipped if the translation model is not
     configured — sentences keep NULL translations)
  C. word promotion: new words gain pinyin/definition (translation model,
     pypinyin fallback), move New→Learned with an initial SRS state and
     lesson tracking
  D. appearance recording: which learned words actually appear in which
     paragraph (from the FINAL, possibly hand-edited, sentence segmentations)
     — word_appearances rows, lesson_words(role='review'), and
     last_seen_lesson_id updates (the lesson-frequency SRS exposure)
  E. one MP3 for the whole lesson (one TTS call per sentence, concatenated;
     Kokoro's speaking pace rises with the length of a single request, so
     whole-paragraph requests made long paragraphs play noticeably faster)
  F. mark the lesson 'complete'
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from pathlib import Path

from langread.db.repositories import HskRepo, LessonsRepo, SentencesRepo, WordsRepo
from langread.models import Lesson, Sentence
from langread.services.generation import LessonDraft, split_sentences
from langread.services.srs import SrsService
from langread.services.translation import TranslationService, pinyin_fallback
from langread.services.tts import (
    TtsService,
    concat_audio,
    detect_audio_format,
)

ProgressFn = Callable[[str, int, int], None]


class SaveError(Exception):
    """Failure during the lesson save pipeline."""


class LessonSaver:
    def __init__(self, conn: sqlite3.Connection, tts: TtsService | None = None,
                 translation: TranslationService | None = None,
                 audio_dir: Path | None = None) -> None:
        self.conn = conn
        self.tts = tts
        self.translation = translation
        self.lessons = LessonsRepo(conn)
        self.sentences = SentencesRepo(conn)
        self.words = WordsRepo(conn)
        self.hsk = HskRepo(conn)
        self.srs = SrsService(conn)
        if audio_dir is None:
            from langread.app_config import audio_dir as default_audio_dir

            audio_dir = default_audio_dir()
        self._audio_dir = Path(audio_dir)

    # ---- entry point (§7.8 "approve and save") ----

    def save_lesson(self, draft: LessonDraft,
                    progress: ProgressFn | None = None) -> Lesson:
        """Create the lesson from a draft and run the full pipeline."""
        lesson = self.lessons.create(topic_id=draft.topic_id,
                                     status="incomplete")
        sentences = [
            Sentence(id=0, lesson_id=lesson.id, para_index=paragraph.index,
                     sent_index=i, text=text, segmentation=segmentation)
            for paragraph in draft.paragraphs
            for i, (text, segmentation) in enumerate(
                zip(paragraph.sentences, paragraph.segmentations)
            )
        ]
        self.sentences.replace_for_lesson(lesson.id, sentences)

        for text in draft.new_words:
            word, created = self.words.get_or_create(text, list_state="new",
                                                     source="paste")
            if created:
                self._link_hsk(word)
            self.lessons.add_lesson_word(lesson.id, word.id, "new")
            self.words.associate_topic(word.id, draft.topic_id)
        # review roles are NOT taken from the draft: they are derived from the
        # words that actually appear in the lesson text (step D)

        return self.finalize_lesson(lesson.id, progress=progress)

    def _link_hsk(self, word) -> None:
        """Link a newly created word to its bundled HSK entry, if any."""
        from langread.services.word_import import link_hsk_entry

        link_hsk_entry(self.conn, word.id)

    # ---- resumable core ----

    def finalize_lesson(self, lesson_id: int,
                        progress: ProgressFn | None = None) -> Lesson:
        """Run/complete the remaining pipeline steps (idempotent)."""
        lesson = self.lessons.get(lesson_id)
        if lesson is None:
            raise SaveError(f"lesson {lesson_id} does not exist")
        if lesson.status == "complete":
            return lesson

        self._translate_sentences(lesson_id, progress)
        self._promote_new_words(lesson_id, progress)
        self._record_appearances(lesson_id, progress)
        self._generate_audio(lesson_id, progress)
        self.lessons.set_status(lesson_id, "complete")
        result = self.lessons.get(lesson_id)
        assert result is not None
        return result

    # ---- steps ----

    def translate_missing_sentences(self, lesson_id: int,
                                    progress: ProgressFn | None = None) -> int:
        """Translate the lesson's untranslated sentences (§7.9 step 2).

        Used after editing a saved lesson: changed sentences lose their
        stored translation and are translated again here. Returns the
        number of sentences translated.
        """
        if self.translation is None:
            raise SaveError(
                "translation model is not configured "
                "(open Model settings to set it)"
            )
        return self._translate_sentences(lesson_id, progress)

    def retranslate_sentences(self, lesson_id: int,
                              progress: ProgressFn | None = None) -> int:
        """Re-translate ALL of the lesson's sentences, replacing the stored
        ones ("Regenerate translation"). Returns the number translated."""
        if self.translation is None:
            raise SaveError(
                "translation model is not configured "
                "(open Model settings to set it)"
            )
        self.sentences.clear_translations(lesson_id)
        return self._translate_sentences(lesson_id, progress)

    def _translate_sentences(self, lesson_id: int,
                             progress: ProgressFn | None) -> int:
        if self.translation is None:
            return 0  # sentences keep NULL translations (documented behavior)
        sentences = self.sentences.list_for_lesson(lesson_id)
        translated = 0
        for i, sentence in enumerate(sentences):
            if progress:
                progress("translations", i + 1, len(sentences))
            if sentence.translation is not None:
                continue
            try:
                translation = self.translation.translate_sentence(sentence.text)
            except TranslationError:
                continue  # leave untranslated; resumable later
            self.sentences.update(sentence.id, translation=translation)
            translated += 1
        return translated

    def _promote_new_words(self, lesson_id: int, progress: ProgressFn | None) -> None:
        rows = [r for r in self.lessons.lesson_words(lesson_id) if r[2] == "new"]
        for i, (_lid, word_id, _role) in enumerate(rows):
            if progress:
                progress("promoting words", i + 1, len(rows))
            word = self.words.get(word_id)
            if word is None or word.list_state != "new":
                continue  # already promoted (resume) or missing
            pinyin, definition, source = self._word_translation(word.text)
            if word.pinyin is None or word.definition is None:
                self.words.set_translation(
                    word.id, word.pinyin or pinyin, word.definition or definition,
                    definition_source=(
                        word.definition_source if word.definition is not None
                        else source
                    ),
                )
            self.srs.promote_word(word_id, lesson_id)  # New → Learned (§7.9.3)

    def _word_translation(
        self, word: str
    ) -> tuple[str | None, str | None, str | None]:
        """(pinyin, definition, definition_source) for one word.

        The translation service checks its offline dictionary first (plan
        §4.1); a dictionary hit is detected here so the source is recorded.
        """
        if self.translation is not None:
            pinyin, definition = self.translation.translate_word(word)
            if pinyin or definition:
                dictionary = getattr(self.translation, "dictionary", None)
                if dictionary is not None and dictionary.lookup(word) is not None:
                    return pinyin, definition, "dictionary"
                return pinyin, definition, "llm"
        return pinyin_fallback(word), None, None  # offline fallback (pypinyin)

    def _record_appearances(self, lesson_id: int,
                            progress: ProgressFn | None) -> None:
        """Record the learned words that ACTUALLY appear in each paragraph.

        Runs on the FINAL sentence segmentations (after any hand edits in
        wizard step 3), so a word the user deleted is not an exposure and a
        word the user typed in is one. For every appearing learned word:
        - insert a `word_appearances` row (word, lesson, paragraph)
        - add a `lesson_words(role='review')` row (unless already role='new')
        - advance `last_seen_lesson_id` (forward-only, so resume is safe)

        No review event is written: an appearance is not a review.
        """
        learned_by_text = {
            w.text: w
            for w in self.words.list_by_state("learned")
        }
        paragraphs: dict[int, set[str]] = {}
        for sentence in self.sentences.list_for_lesson(lesson_id):
            paragraphs.setdefault(sentence.para_index, set()).update(
                sentence.segmentation
            )
        appearing: set[int] = set()
        for para_index, tokens in sorted(paragraphs.items()):
            for text in sorted(tokens):
                word = learned_by_text.get(text)
                if word is None:
                    continue
                self.lessons.add_appearance(lesson_id, word.id, para_index)
                self.lessons.add_lesson_word(lesson_id, word.id, "review")
                appearing.add(word.id)
        for i, word_id in enumerate(sorted(appearing)):
            if progress:
                progress("SRS updates", i + 1, len(appearing))
            self.words.set_last_seen_lesson(word_id, lesson_id)

    def _generate_audio(self, lesson_id: int, progress: ProgressFn | None) -> None:
        if self.tts is None:
            raise SaveError(
                "text-to-speech model is not configured "
                "(open Model settings to set it)"
            )
        existing = self._find_existing_audio(lesson_id)
        if existing is not None:
            self.lessons.set_audio_path(lesson_id, existing.name)
            return  # already synthesized (resume)
        paragraphs = self._sentence_texts(lesson_id)
        chunks: list[bytes] = []
        for i, texts in enumerate(paragraphs):
            if progress:
                progress("audio", i + 1, len(paragraphs))
            for text in texts:
                try:
                    chunks.append(self.tts.synthesize(text))
                except Exception as exc:
                    raise SaveError(f"audio generation failed: {exc}") from exc
        audio_format = detect_audio_format(chunks[0]) if chunks else None
        if audio_format is None:
            raise SaveError("TTS produced unrecognized audio data")
        data = concat_audio(chunks, audio_format)
        out_path = self._audio_dir / f"lesson_{lesson_id}.{audio_format}"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(data)
        self.lessons.set_audio_path(lesson_id, out_path.name)

    def _find_existing_audio(self, lesson_id: int) -> Path | None:
        """Any previously written lesson audio file (mp3/wav/ogg/flac)."""
        for suffix in (".mp3", ".wav", ".ogg", ".flac"):
            candidate = self._audio_dir / f"lesson_{lesson_id}{suffix}"
            if candidate.exists() and candidate.stat().st_size > 0:
                return candidate
        return None

    # ---- audio regeneration ----

    def regenerate_audio(self, lesson_id: int,
                         progress: ProgressFn | None = None) -> Lesson:
        """Delete the lesson's audio file and synthesize it fresh.

        Used when the TTS setup changed (e.g. a Latin voice was configured
        after the original synthesis skipped Latin text).
        """
        lesson = self.lessons.get(lesson_id)
        if lesson is None:
            raise SaveError(f"lesson {lesson_id} does not exist")
        if not self.sentences.list_for_lesson(lesson_id):
            raise SaveError(f"lesson {lesson_id} has no sentences")
        for suffix in (".mp3", ".wav", ".ogg", ".flac"):
            candidate = self._audio_dir / f"lesson_{lesson_id}{suffix}"
            if candidate.exists():
                candidate.unlink()
        self.lessons.set_audio_path(lesson_id, None)
        self._generate_audio(lesson_id, progress)
        result = self.lessons.get(lesson_id)
        assert result is not None
        return result

    # ---- lesson deletion ----

    def delete_lesson(self, lesson_id: int) -> list[str]:
        """Delete a lesson — only the LAST one in its topic (D-lesson delete).

        Reverses the word promotion of §7.9.3: this lesson's new words move
        back to the New list. Sentences, lesson_words and review events are
        removed via FK cascade; the audio file is deleted from disk.

        Returns the texts of the words moved back to the New list.
        """
        lesson = self.lessons.get(lesson_id)
        if lesson is None:
            raise SaveError(f"lesson {lesson_id} does not exist")
        topic_lessons = self.lessons.list_for_topic(lesson.topic_id)
        if topic_lessons and topic_lessons[-1].id != lesson_id:
            raise SaveError(
                "only the last lesson in a topic can be deleted — earlier "
                "lessons may reuse this lesson's words"
            )
        demoted: list[str] = []
        # words whose appearance history includes this lesson (their
        # last_seen_lesson_id must be repaired after the delete)
        affected = [
            row[0] for row in self.conn.execute(
                "SELECT DISTINCT word_id FROM word_appearances WHERE lesson_id = ?",
                (lesson_id,),
            )
        ]
        for _lid, word_id, role in self.lessons.lesson_words(lesson_id):
            if role != "new":
                continue  # review words existed before this lesson
            word = self.words.get(word_id)
            if word is None or word.list_state != "learned":
                continue  # never promoted (incomplete) or moved elsewhere
            self.words.move_to_state(word_id, "new")
            # reset the lesson-frequency tracking so a later re-promotion
            # starts fresh (appearances cascade-deleted with the lesson)
            self.words.clear_lesson_track(word_id)
            demoted.append(word.text)
        # NULL out word references to this lesson so the foreign keys allow
        # the delete (the appearance rows themselves cascade)
        self.words.reset_lesson_references(lesson_id)
        for suffix in (".mp3", ".wav", ".ogg", ".flac"):
            candidate = self._audio_dir / f"lesson_{lesson_id}{suffix}"
            if candidate.exists():
                candidate.unlink()
        self.lessons.delete(lesson_id)
        # repair last_seen: the previous lesson the word actually appeared in
        for word_id in affected:
            word = self.words.get(word_id)
            if word is None or word.list_state != "learned":
                continue  # demoted above, or moved elsewhere
            row = self.conn.execute(
                "SELECT MAX(lesson_id) FROM word_appearances WHERE word_id = ?",
                (word_id,),
            ).fetchone()
            if row and row[0] is not None:
                self.words.set_lesson_track(word_id,
                                            last_seen_lesson_id=int(row[0]))
        return demoted

    def _sentence_texts(self, lesson_id: int) -> list[list[str]]:
        """The lesson's texts grouped per paragraph, one item per sentence.

        Each stored sentence row is (re-)split on sentence enders so every
        TTS request carries exactly one sentence: TTS servers such as Kokoro
        speak longer single requests faster, so synthesizing a whole
        paragraph at once made long paragraphs (notably the 5-sentence final
        paragraph, §6.4) play noticeably faster than the rest of the lesson.
        """
        sentences = self.sentences.list_for_lesson(lesson_id)
        paragraphs: dict[int, list[str]] = {}
        for sentence in sentences:
            parts = split_sentences(sentence.text) or [sentence.text]
            paragraphs.setdefault(sentence.para_index, []).extend(parts)
        return [texts for _index, texts in sorted(paragraphs.items())]
