"""Spaced repetition engine — Anki-like SM-2 variant (requirements §11, D-2).

The core is pure: state + rating + parameters + now → new state. The
`SrsService` wrapper persists results through `WordsRepo` and writes the
append-only `review_events` log entry *before* applying an update.

Rating semantics (§8.6):
- difficult → interval reset to the relearn step, ease decreased, lapses+1
- easy      → extra interval growth (easy_bonus), ease increased, reps+1
- standard  → normal SM-2 interval growth (interval × ease), reps+1
- unchanged → no change at all
"""

from __future__ import annotations

import datetime as dt
import sqlite3
from dataclasses import asdict, dataclass, fields, replace

from langread.db import utcnow_iso
from langread.db.repositories import ReviewsRepo, SettingsRepo, WordsRepo
from langread.models import Word

RATINGS = ("difficult", "easy", "standard", "unchanged")


@dataclass(frozen=True)
class SrsState:
    """SRS state of one learned word (mirrors the words table columns)."""

    ease: float = 2.5
    interval_days: float | None = None
    due_at: str | None = None
    reps: int = 0
    lapses: int = 0
    last_rated_at: str | None = None


@dataclass(frozen=True)
class SrsParams:
    # All knobs are user-configurable in-app (desktop main menu §12.1 item 7).
    initial_ease: float = 2.5
    initial_interval_days: float = 1.0
    exposure_multiplier: float = 1.0
    easy_bonus: float = 1.3
    ease_delta_easy: float = 0.15
    ease_delta_difficult: float = -0.20
    relearn_interval_days: float = 0.5
    min_interval_days: float = 1.0
    max_interval_days: float = 365.0
    ease_min: float = 1.3
    ease_max: float = 3.0


DEFAULT_PARAMS = SrsParams()
SETTINGS_KEY = "srs.params"


def _parse(now: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(now)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed


def _add_days(now: str, days: float) -> str:
    return (_parse(now) + dt.timedelta(days=days)).isoformat()


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _clamp_ease(ease: float, params: SrsParams) -> float:
    return _clamp(ease, params.ease_min, params.ease_max)


def _clamp_interval(interval: float, params: SrsParams) -> float:
    return _clamp(interval, params.min_interval_days, params.max_interval_days)


def promote(params: SrsParams, now: str) -> SrsState:
    """Initial SRS state when a new word is promoted to Learned (§7.9.3)."""
    interval = _clamp_interval(params.initial_interval_days, params)
    return SrsState(
        ease=_clamp_ease(params.initial_ease, params),
        interval_days=interval,
        due_at=_add_days(now, interval),
        reps=1,
        lapses=0,
        last_rated_at=now,
    )


def apply_exposure(state: SrsState, params: SrsParams, now: str) -> SrsState:
    """Gentle interval growth when a word is merely used in a new lesson (§7.9.4).

    Not a review: reps/lapses are unchanged, and no review event is written.
    """
    base = (
        state.interval_days
        if state.interval_days is not None
        else params.initial_interval_days
    )
    interval = _clamp_interval(base * state.ease * params.exposure_multiplier, params)
    return replace(state, interval_days=interval, due_at=_add_days(now, interval))


def apply_rating(state: SrsState, rating: str, params: SrsParams,
                 now: str) -> SrsState:
    """Apply one review rating (§8.6). `now` is an ISO-8601 string."""
    if rating not in RATINGS:
        raise ValueError(f"invalid rating: {rating!r}")

    if rating == "unchanged":
        return state

    if rating == "difficult":
        # Relearn step: the interval is intentionally NOT clamped to
        # min_interval_days so a sub-day "quite soon" return is possible (§8.6.1).
        interval = max(params.relearn_interval_days, 0.0)
        ease = _clamp_ease(state.ease + params.ease_delta_difficult, params)
        return replace(
            state,
            ease=ease,
            interval_days=interval,
            due_at=_add_days(now, interval),
            lapses=state.lapses + 1,
            last_rated_at=now,
        )

    base = (
        state.interval_days
        if state.interval_days is not None
        else params.initial_interval_days
    )
    if rating == "standard":
        interval = _clamp_interval(base * state.ease, params)
        ease = _clamp_ease(state.ease, params)
        reps = state.reps + 1
    else:  # easy
        ease = _clamp_ease(state.ease + params.ease_delta_easy, params)
        interval = _clamp_interval(base * state.ease * params.easy_bonus, params)
        reps = state.reps + 1
    return replace(
        state,
        ease=ease,
        interval_days=interval,
        due_at=_add_days(now, interval),
        reps=reps,
        last_rated_at=now,
    )


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
        overrides = {k: v for k, v in stored.items() if k in known}
        return replace(DEFAULT_PARAMS, **overrides)

    def set_params(self, params: SrsParams) -> None:
        self.settings.set(SETTINGS_KEY, asdict(params))

    # ---- state helpers ----

    @staticmethod
    def _state_of(word: Word) -> SrsState:
        return SrsState(
            ease=word.ease,
            interval_days=word.interval_days,
            due_at=word.due_at,
            reps=word.reps,
            lapses=word.lapses,
            last_rated_at=word.last_rated_at,
        )

    def _write(self, word_id: int, state: SrsState) -> Word:
        self.words.set_srs(
            word_id,
            ease=state.ease,
            interval_days=state.interval_days,
            due_at=state.due_at,
            reps=state.reps,
            lapses=state.lapses,
            last_rated_at=state.last_rated_at,
        )
        word = self.words.get(word_id)
        assert word is not None
        return word

    # ---- operations ----

    def promote_word(self, word_id: int, now: str | None = None) -> Word:
        """New → Learned with an initial SRS state (lesson save pipeline §7.9.3)."""
        now = now or utcnow_iso()
        state = promote(self.params(), now)
        self.words.move_to_state(word_id, "learned")
        return self._write(word_id, state)

    def apply_exposure(self, word_id: int, now: str | None = None) -> Word:
        """Record that a learned word was used in a newly saved lesson (§7.9.4)."""
        now = now or utcnow_iso()
        word = self.words.get(word_id)
        assert word is not None
        state = apply_exposure(self._state_of(word), self.params(), now)
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

