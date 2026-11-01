"""Cadence planner (requirements §6, §7.6).

Pure logic: given the lesson's new words, review words, and paragraph count,
decide which words each paragraph's prompt should request, and track actual
usage so later paragraphs repeat the least-used words.

Rules enforced:
- at most one first-use new word per paragraph (§6.2)
- no first-use new word in the final paragraph (§6.4)
- the final paragraph must use ALL new words (§6.4)
- repeats prefer previously introduced words with the lowest usage (§6.3)
- review words rotate through the list

Note: |new words| must be < paragraph count, so the wizard allows up to 12
paragraphs when 10 new words are selected (a documented deviation from the
5–10 paragraph range, which is only tight when 9–10 new words are used).
"""

from __future__ import annotations

from dataclasses import dataclass, field


class CadenceError(Exception):
    """Invalid lesson word/paragraph configuration."""


@dataclass
class ParagraphPlan:
    index: int
    is_final: bool
    first_use: str | None = None
    repeat_words: list[str] = field(default_factory=list)
    review_words: list[str] = field(default_factory=list)
    all_new_words: list[str] = field(default_factory=list)


class CadencePlanner:
    def __init__(self, new_words: list[str], review_words: list[str],
                 n_paragraphs: int, *, max_repeats: int = 3,
                 max_review: int = 2) -> None:
        if not 5 <= len(new_words) <= 10:
            raise CadenceError(
                f"a lesson introduces 5–10 new words (got {len(new_words)})"
            )
        if n_paragraphs <= len(new_words):
            raise CadenceError(
                f"need more paragraphs than new words "
                f"({n_paragraphs} ≤ {len(new_words)}); the final paragraph "
                "introduces no new words"
            )
        self.new_words = list(new_words)
        self.review_words = list(review_words)
        self.n_paragraphs = n_paragraphs
        self.max_repeats = max_repeats
        self.max_review = max_review
        self._usage: dict[str, int] = {w: 0 for w in new_words + review_words}
        self._review_cursor = 0

    # ---- planning ----

    def plan_paragraph(self, index: int) -> ParagraphPlan:
        if not 0 <= index < self.n_paragraphs:
            raise CadenceError(f"paragraph index out of range: {index}")

        if index == self.n_paragraphs - 1:
            return ParagraphPlan(
                index=index,
                is_final=True,
                first_use=None,
                repeat_words=[],
                review_words=self._next_review(),
                all_new_words=list(self.new_words),
            )

        first_use = self.new_words[index] if index < len(self.new_words) else None
        introduced = self.new_words[:index]
        repeats = sorted(introduced, key=lambda w: (self._usage.get(w, 0), w))
        repeats = repeats[: self.max_repeats]
        return ParagraphPlan(
            index=index,
            is_final=False,
            first_use=first_use,
            repeat_words=repeats,
            review_words=self._next_review(),
        )

    def _next_review(self) -> list[str]:
        if not self.review_words or self.max_review <= 0:
            return []
        chosen: list[str] = []
        for _ in range(min(self.max_review, len(self.review_words))):
            chosen.append(self.review_words[self._review_cursor % len(self.review_words)])
            self._review_cursor += 1
        return chosen

    # ---- usage tracking (§7.6) ----

    def record_usage(self, used_words: list[str]) -> None:
        for word in used_words:
            if word in self._usage:
                self._usage[word] += 1

    def usage_counts(self) -> dict[str, int]:
        return dict(self._usage)
