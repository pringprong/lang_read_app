"""Lesson text generation pipeline (requirements §7.3–7.7, D-12).

Generates a lesson one paragraph at a time: builds each prompt from the
editable template + the cadence planner's word list, calls the sentence
generation model, splits the reply into sentences, segments them, checks
which requested words were actually used, retries when the first-use word
is missing, and feeds usage back into the planner for the next paragraph.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass, field
from typing import Callable

from langread.db.repositories import TemplatesRepo, TopicsRepo, WordsRepo
from langread.services.cadence import CadenceError, CadencePlanner
from langread.services.llm_client import LlmError
from langread.services.segmentation import SegmentationService

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[。！？!?；;])")
_LEFTOVER_PLACEHOLDER_RE = re.compile(r"\{[a-z_]+\}")


class GenerationError(Exception):
    """Configuration or generation failure."""


def split_sentences(text: str) -> list[str]:
    """Split Chinese text into sentences, keeping the ending punctuation."""
    parts = _SENTENCE_SPLIT_RE.split(text.strip())
    return [part.strip() for part in parts if part.strip()]


def _clean_reply(text: str) -> str:
    """Strip common LLM reply wrappers (fences, quotes, labels)."""
    cleaned = text.strip()
    cleaned = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", cleaned).strip()
    cleaned = cleaned.strip('"“”').strip()
    cleaned = re.sub(r"^(段落|Paragraph|Text)\s*[:：]\s*", "", cleaned).strip()
    return cleaned


def fill_template(template: str, values: dict[str, str]) -> str:
    """Replace {placeholders}; raises if unknown placeholders remain."""
    prompt = template
    for key, value in values.items():
        prompt = prompt.replace("{" + key + "}", value)
    leftover = _LEFTOVER_PLACEHOLDER_RE.search(prompt)
    if leftover:
        raise GenerationError(
            f"unknown or unfilled placeholder {leftover.group(0)!r} in prompt template"
        )
    return prompt


@dataclass
class GeneratedParagraph:
    index: int
    text: str
    sentences: list[str] = field(default_factory=list)
    segmentations: list[list[str]] = field(default_factory=list)
    used_words: list[str] = field(default_factory=list)
    retries: int = 0


@dataclass
class LessonDraft:
    topic_id: int
    topic_name: str
    new_words: list[str]
    review_words: list[str]
    paragraphs: list[GeneratedParagraph] = field(default_factory=list)

    def paragraph_texts(self) -> list[str]:
        return [p.text for p in self.paragraphs]

    def all_sentences(self) -> list[str]:
        return [s for p in self.paragraphs for s in p.sentences]


class GenerationService:
    def __init__(self, conn: sqlite3.Connection, llm=None) -> None:
        self.conn = conn
        self.llm = llm  # any object with .chat(prompt) -> str (LlmClient in prod)
        self.templates = TemplatesRepo(conn)
        self.topics = TopicsRepo(conn)
        self.words = WordsRepo(conn)
        self.segmentation = SegmentationService(conn)

    # ---- suggestions (§7.2) ----

    def suggest_lesson_words(self, topic_id: int | None,
                             n_new: int = 10, n_review: int = 6
                             ) -> tuple[list[str], list[str]]:
        """Suggested new words (D-11) and review words (SRS due, §7.2)."""
        new_words = [w.text for w in self.words.suggest_new_words(topic_id, n_new)]
        review_words = [w.text for w in self.words.due_learned_words(topic_id, n_review)]
        return new_words, review_words

    # ---- generation ----

    def generate_lesson(self, topic_id: int, new_words: list[str],
                        review_words: list[str], n_paragraphs: int,
                        progress: Callable[[int, str], None] | None = None
                        ) -> LessonDraft:
        if self.llm is None:
            raise GenerationError(
                "sentence generation model is not configured "
                "(open Model settings to set it)"
            )
        topic = self.topics.get(topic_id)
        if topic is None:
            raise GenerationError(f"topic {topic_id} does not exist")
        try:
            planner = CadencePlanner(new_words, review_words, n_paragraphs)
        except CadenceError as exc:
            raise GenerationError(str(exc)) from exc

        basic_sample = "、".join(
            w.text for w in self.words.list_by_state("basic")[:50]
        )
        paragraphs: list[GeneratedParagraph] = []
        for index in range(n_paragraphs):
            plan = planner.plan_paragraph(index)
            paragraph = self._generate_paragraph(plan, topic.name, basic_sample)
            planner.record_usage(paragraph.used_words)
            paragraphs.append(paragraph)
            if progress is not None:
                progress(index, paragraph.text)

        return LessonDraft(
            topic_id=topic_id,
            topic_name=topic.name,
            new_words=list(new_words),
            review_words=list(review_words),
            paragraphs=paragraphs,
        )

    def _generate_paragraph(self, plan, topic_name: str,
                            basic_sample: str) -> GeneratedParagraph:
        if plan.is_final:
            template = self.templates.get("generate_final_paragraph")
            if not template:
                raise GenerationError("missing template: generate_final_paragraph")
            prompt = fill_template(template, {
                "topic_name": topic_name,
                "all_new_words": "、".join(plan.all_new_words),
            })
        else:
            template = self.templates.get("generate_paragraph")
            if not template:
                raise GenerationError("missing template: generate_paragraph")
            prompt = fill_template(template, {
                "topic_name": topic_name,
                "new_word": plan.first_use or "（本段没有新词）",
                "repeat_words": "、".join(plan.repeat_words) or "（无）",
                "review_words": "、".join(plan.review_words) or "（无）",
            })

        requested = (
            set(plan.all_new_words) if plan.is_final
            else (({plan.first_use} if plan.first_use else set())
                  | set(plan.repeat_words) | set(plan.review_words))
        )

        text, used, retries = self._chat_until_valid(prompt, plan.first_use, requested)
        sentences = split_sentences(text)
        segmentations = [self.segmentation.token_texts(s) for s in sentences]
        return GeneratedParagraph(
            index=plan.index,
            text=text,
            sentences=sentences,
            segmentations=segmentations,
            used_words=sorted(used),
            retries=retries,
        )

    def _chat_until_valid(self, prompt: str, first_use: str | None,
                          requested: set[str]):
        """Call the model; retry (≤2) if the first-use word is missing (§7.6).

        A retry that itself fails (e.g. an empty reply from a reasoning
        model) keeps the earlier usable text instead of failing the lesson.
        """
        text = _clean_reply(self.llm.chat(prompt))
        used = self._usage_of(text, requested)
        retries = 0
        while first_use is not None and first_use not in used and retries < 2:
            retry_prompt = (
                prompt
                + f"\n\nIMPORTANT: The paragraph MUST contain the word “{first_use}” "
                "exactly. Rewrite the paragraph with it."
            )
            try:
                retry_text = _clean_reply(self.llm.chat(retry_prompt))
            except LlmError:
                break  # keep the earlier text; the word is simply missing
            text = retry_text
            used = self._usage_of(text, requested)
            retries += 1
        return text, used, retries

    def _usage_of(self, text: str, requested: set[str]) -> set[str]:
        tokens = set(self.segmentation.token_texts(text))
        return requested & tokens

