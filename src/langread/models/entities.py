"""Model dataclasses shared across the app."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Topic:
    id: int
    name: str
    order_index: int
    created_at: str


@dataclass(frozen=True)
class Lesson:
    id: int
    topic_id: int
    order_index: int
    title: str | None
    status: str  # 'draft' | 'complete' | 'incomplete'
    audio_path: str | None
    created_at: str
    last_reviewed_at: str | None
    review_count: int = 0  # number of completed reviews (schema v2)


@dataclass(frozen=True)
class Sentence:
    id: int
    lesson_id: int
    para_index: int
    sent_index: int
    text: str
    segmentation: list[str] = field(default_factory=list)
    translation: str | None = None


@dataclass(frozen=True)
class Word:
    id: int
    text: str
    list_state: str  # 'new' | 'learned' | 'basic'
    pinyin: str | None = None
    definition: str | None = None
    hsk_word_id: int | None = None
    source: str | None = None
    added_at: str | None = None
    # where the current definition came from (schema v3):
    definition_source: str | None = None  # 'dictionary'|'llm'|'hsk'|'manual'
    # SRS state (meaningful when list_state == 'learned'):
    ease: float = 2.5
    reps: int = 0
    lapses: int = 0
    last_rated_at: str | None = None
    # lesson-frequency SRS (schema v4):
    first_learned_lesson_id: int | None = None  # lesson that introduced it
    last_seen_lesson_id: int | None = None      # last lesson it actually appeared in


@dataclass(frozen=True)
class HskWord:
    id: int
    text: str
    level: int  # 1..6
    pinyin: str | None = None
    definition: str | None = None
    app_state: str = "unused"  # 'unused' | 'new' | 'basic' | 'learned'


@dataclass(frozen=True)
class ReviewEvent:
    id: int
    lesson_id: int
    word_id: int | None
    rating: str | None  # 'difficult' | 'easy' | 'standard' | 'unchanged'
    reviewed_at: str
    device: str  # 'desktop' | 'android'
