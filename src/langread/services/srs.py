"""Spaced repetition engine — lesson-frequency variant.

Replaces the original day-based SM-2 variant (plan
20261108_lesson_based_SRS_update.md): the SRS clock counts LESSONS — the
global `lessons.id` sequence, across all topics — so many lessons created on
the same day each advance the schedule.

Selection: every generated paragraph suggests a few Learned words, chosen by
weighted random sampling over three factors (weights user-configurable):
1. novelty   — recency of first learning (decays over ~5 lessons to routine)
2. staleness — lessons since the word last ACTUALLY appeared (the heart of
   the system; only real appearances count, the LLM may skip suggestions)
3. difficulty — from review ratings via ease (least important; neutral for
   words that have never been rated, e.g. same-day unreviewed lessons)

Rating semantics (§8.6, day intervals removed):
- difficult → ease decreased, lapses+1
- easy      → ease increased, reps+1
- standard  → reps+1
- unchanged → no change at all
"""

from __future__ import annotations

import random
import sqlite3
from dataclasses import asdict, dataclass, fields, replace

from langread.db import utcnow_iso
from langread.db.repositories import (
    LessonsRepo,
    ReviewsRepo,
    SettingsRepo,
    WordsRepo,
)
from langread.models import Word

RATINGS = ("difficult", "easy", "standard", "unchanged")


@dataclass(frozen=True)
class SrsState:
    """SRS state of one learned word (mirrors the words table columns)."""

    ease: float = 2.5
    reps: int = 0
    lapses: int = 0
    last_rated_at: str | None = None


@dataclass(frozen=True)
class SrsParams:
    # All knobs are user-configurable in-app (desktop main menu §12.1 item 7).
    # --- rating math ---
    initial_ease: float = 2.5
    ease_delta_easy: float = 0.15
    ease_delta_difficult: float = -0.20
    ease_min: float = 1.3
    ease_max: float = 3.0
    # --- lesson-frequency selection ---
    learned_words_per_paragraph: int = 2
    novelty_window_lessons: float = 5.0
    staleness_target_lessons: float = 8.0
    weight_novelty: float = 0.30
    weight_staleness: float = 0.50
    weight_difficulty: float = 0.20
    same_lesson_cooldown_paragraphs: int = 0  # 0 = the whole lesson


# params are stored as JSON numbers; these must be round ints
INT_PARAM_FIELDS = frozenset(
    {"learned_words_per_paragraph", "same_lesson_cooldown_paragraphs"}
)

DEFAULT_PARAMS = SrsParams()
SETTINGS_KEY = "srs.params"

# difficulty of a word that has never been rated: the same constant for every
# unrated word, so it changes nothing about the *ranking* — when many
# same-day lessons are unreviewed, factor 3 simply contributes nothing
UNRATED_DIFFICULTY = 0.5


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _clamp_ease(ease: float, params: SrsParams) -> float:
    return _clamp(ease, params.ease_min, params.ease_max)


def promote(params: SrsParams) -> SrsState:
    """Initial SRS state when a new word is promoted to Learned (§7.9.3)."""
    return SrsState(ease=_clamp_ease(params.initial_ease, params))


def apply_rating(state: SrsState, rating: str, params: SrsParams,
                 now: str) -> SrsState:
    """Apply one review rating (§8.6). `now` is an ISO-8601 string."""
    if rating not in RATINGS:
        raise ValueError(f"invalid rating: {rating!r}")

    if rating == "unchanged":
        return state

    if rating == "difficult":
        # the word should come back quite soon: ease down + a lapse
        return replace(
            state,
            ease=_clamp_ease(state.ease + params.ease_delta_difficult, params),
            lapses=state.lapses + 1,
            last_rated_at=now,
        )

    if rating == "standard":
        return replace(state, reps=state.reps + 1, last_rated_at=now)

    # easy
    return replace(
        state,
        ease=_clamp_ease(state.ease + params.ease_delta_easy, params),
        reps=state.reps + 1,
        last_rated_at=now,
    )


# ---- lesson-frequency selection engine (pure) ----


@dataclass(frozen=True)
class WordCandidate:
    """A learned word eligible for per-paragraph selection."""

    text: str
    first_learned_lesson_id: int | None = None
    last_seen_lesson_id: int | None = None
    ease: float = 2.5
    reps: int = 0

    @classmethod
    def from_word(cls, word: Word) -> "WordCandidate":
        return cls(
            text=word.text,
            first_learned_lesson_id=word.first_learned_lesson_id,
            last_seen_lesson_id=word.last_seen_lesson_id,
            ease=word.ease,
            reps=word.reps,
        )


def novelty(age: float, params: SrsParams) -> float:
    """Factor 1: recency of first learning, decaying to 0 at the window edge
    (a word learned ~5 lessons ago is routine again)."""
    if params.novelty_window_lessons <= 0:
        return 0.0
    return _clamp(1.0 - age / params.novelty_window_lessons, 0.0, 1.0)


def staleness(gap: float, params: SrsParams) -> float:
    """Factor 2: lessons since the last ACTUAL appearance (saturating — a
    fully stale word always gets the maximum boost, so every learned word
    eventually returns)."""
    if params.staleness_target_lessons <= 0:
        return 1.0
    return _clamp(gap / params.staleness_target_lessons, 0.0, 1.0)


def difficulty(ease: float, rated: bool, params: SrsParams) -> float:
    """Factor 3 (least important): harder (low-ease) words score higher;
    neutral for words that have never been rated."""
    if not rated:
        return UNRATED_DIFFICULTY
    span = params.ease_max - params.ease_min
    if span <= 0:
        return UNRATED_DIFFICULTY
    return _clamp((params.ease_max - ease) / span, 0.0, 1.0)


def selection_weight(candidate: WordCandidate, current_lesson_no: int,
                     params: SrsParams) -> float:
    """The weighted average of the three factors for one learned word."""
    first = candidate.first_learned_lesson_id or current_lesson_no
    last = candidate.last_seen_lesson_id or first
    age = max(0.0, float(current_lesson_no - first))
    gap = max(0.0, float(current_lesson_no - last))
    rated = candidate.reps > 0
    return (
        params.weight_novelty * novelty(age, params)
        + params.weight_staleness * staleness(gap, params)
        + params.weight_difficulty * difficulty(candidate.ease, rated, params)
    )


class LearnedWordSelector:
    """Picks which Learned words each paragraph's prompt should suggest.

    Weighted random sampling without replacement. A word that has already
    actually appeared in the current lesson is put on cooldown (default: the
    whole lesson) so different learned words spread across the paragraphs.
    The LLM is free to skip suggestions — only real appearances (fed back
    via `record_usage`) count as exposure.
    """

    def __init__(self, candidates: list[WordCandidate], current_lesson_no: int,
                 params: SrsParams,
                 rng: random.Random | None = None) -> None:
        self._params = params
        self._current = current_lesson_no
        self._rng = rng if rng is not None else random.Random()
        # words first learned in THIS lesson (its new words) are ineligible —
        # the cadence repeat mechanism already handles them
        self._candidates = [
            c for c in candidates
            if c.first_learned_lesson_id is None
            or c.first_learned_lesson_id < current_lesson_no
        ]
        self._texts = {c.text for c in self._candidates}
        self._used_at: dict[str, int] = {}  # text -> paragraph index

    def pick(self, count: int | None = None,
             paragraph_index: int | None = None) -> list[str]:
        """Suggest up to `count` (default: params) learned-word texts."""
        if count is None:
            count = self._params.learned_words_per_paragraph
        pool = [
            c for c in self._candidates
            if self._is_eligible(c.text, paragraph_index)
        ]
        picked: list[str] = []
        for _ in range(min(count, len(pool))):
            weights = [
                selection_weight(c, self._current, self._params) for c in pool
            ]
            total = sum(weights)
            if total <= 0:
                chosen_text = self._rng.choice(pool).text
            else:
                point = self._rng.random() * total
                accumulated = 0.0
                chosen_index = len(pool) - 1
                for i, weight in enumerate(weights):
                    accumulated += weight
                    if point <= accumulated:
                        chosen_index = i
                        break
                chosen_text = pool[chosen_index].text
            picked.append(chosen_text)
            pool = [c for c in pool if c.text != chosen_text]
        return picked

    def record_usage(self, texts, paragraph_index: int | None = None) -> None:
        """Feed back the learned words that ACTUALLY appeared in a paragraph
        (suggested or spontaneous) so the cooldown can exclude them."""
        for text in texts:
            if text in self._texts:
                self._used_at[text] = (
                    paragraph_index if paragraph_index is not None else 0
                )

    def top_weighted(self, limit: int) -> list[str]:
        """The highest-weight candidates (informational preview, §7.2)."""
        ranked = sorted(
            self._candidates,
            key=lambda c: (
                -selection_weight(c, self._current, self._params), c.text
            ),
        )
        return [c.text for c in ranked[:limit]]

    def _is_eligible(self, text: str, paragraph_index: int | None) -> bool:
        if text not in self._used_at:
            return True
        cooldown = self._params.same_lesson_cooldown_paragraphs
        if cooldown <= 0 or paragraph_index is None:
            return False  # whole-lesson cooldown
        return (paragraph_index - self._used_at[text]) > cooldown


class SrsService:
    """Bridges the pure engine to the database (words + review events)."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self.words = WordsRepo(conn)
        self.settings = SettingsRepo(conn)
        self.reviews = ReviewsRepo(conn)

    # ---- parameters ----

    def params(self) -> SrsParams:
        stored = self.settings.get(SETTINGS_KEY, default={}) or {}
        known = {f.name for f in fields(SrsParams)}
        overrides: dict = {}
        for key, value in stored.items():
            if key not in known:
                continue  # unknown (e.g. old day-based) keys are ignored
            try:
                overrides[key] = (
                    int(value) if key in INT_PARAM_FIELDS else float(value)
                )
            except (TypeError, ValueError):
                continue
        return replace(DEFAULT_PARAMS, **overrides)

    def set_params(self, params: SrsParams) -> None:
        self.settings.set(SETTINGS_KEY, asdict(params))

    # ---- state helpers ----

    @staticmethod
    def _state_of(word: Word) -> SrsState:
        return SrsState(
            ease=word.ease,
            reps=word.reps,
            lapses=word.lapses,
            last_rated_at=word.last_rated_at,
        )

    def _write(self, word_id: int, state: SrsState) -> Word:
        self.words.set_srs(
            word_id,
            ease=state.ease,
            reps=state.reps,
            lapses=state.lapses,
            last_rated_at=state.last_rated_at,
        )
        word = self.words.get(word_id)
        assert word is not None
        return word

    # ---- operations ----

    def selector(self, current_lesson_no: int | None = None,
                 rng: random.Random | None = None) -> LearnedWordSelector:
        """A selector over the current Learned list (lesson create pipeline).

        `current_lesson_no` defaults to the lesson number the NEXT created
        lesson will get (the SRS clock while generating).
        """
        if current_lesson_no is None:
            current_lesson_no = LessonsRepo(self.conn).next_lesson_no()
        candidates = [
            WordCandidate.from_word(w)
            for w in self.words.list_by_state("learned")
        ]
        return LearnedWordSelector(
            candidates, current_lesson_no, self.params(), rng=rng
        )

    def promote_word(self, word_id: int, lesson_id: int) -> Word:
        """New → Learned with an initial SRS state and lesson tracking
        (lesson save pipeline §7.9.3)."""
        state = promote(self.params())
        self.words.move_to_state(word_id, "learned")
        self.words.set_lesson_track(
            word_id,
            first_learned_lesson_id=lesson_id,
            last_seen_lesson_id=lesson_id,
        )
        return self._write(word_id, state)

    def rate_word(self, word_id: int, rating: str, lesson_id: int, *,
                  device: str = "desktop", now: str | None = None) -> Word:
        """Apply a review rating: log the event first, then update SRS (§8.6)."""
        if rating not in RATINGS:
            raise ValueError(f"invalid rating: {rating!r}")
        now = now or utcnow_iso()
        self.reviews.add(
            lesson_id=lesson_id, word_id=word_id, rating=rating,
            device=device, reviewed_at=now,
        )
        word = self.words.get(word_id)
        assert word is not None
        state = apply_rating(self._state_of(word), rating, self.params(), now)
        return self._write(word_id, state)

    def apply_rating_at(self, word_id: int, rating: str, reviewed_at: str) -> Word:
        """Apply an SRS rating for a given timestamp WITHOUT logging an event
        (used by sync reconciliation — the event is inserted separately)."""
        if rating not in RATINGS:
            raise ValueError(f"invalid rating: {rating!r}")
        word = self.words.get(word_id)
        assert word is not None
        state = apply_rating(self._state_of(word), rating, self.params(), reviewed_at)
        return self._write(word_id, state)

