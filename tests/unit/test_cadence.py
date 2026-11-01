"""M6 unit tests: cadence planner."""

from __future__ import annotations

import pytest

from langread.services.cadence import CadenceError, CadencePlanner

NEW = ["词一", "词二", "词三", "词四", "词五"]
REVIEW = ["复习一", "复习二", "复习三"]


def test_first_use_one_per_paragraph_then_none():
    planner = CadencePlanner(NEW, REVIEW, 8)
    plans = [planner.plan_paragraph(i) for i in range(8)]
    assert [p.first_use for p in plans[:5]] == NEW
    assert plans[5].first_use is None
    assert plans[6].first_use is None


def test_final_paragraph_all_new_words_no_first_use():
    planner = CadencePlanner(NEW, REVIEW, 8)
    final = planner.plan_paragraph(7)
    assert final.is_final
    assert final.first_use is None
    assert final.all_new_words == NEW


def test_repeats_are_introduced_words():
    planner = CadencePlanner(NEW, REVIEW, 8)
    plan = planner.plan_paragraph(3)  # 词一..词三 introduced
    assert set(plan.repeat_words) <= {"词一", "词二", "词三"}
    assert "词四" not in plan.repeat_words and "词五" not in plan.repeat_words


def test_repeats_prefer_lowest_usage():
    planner = CadencePlanner(NEW, REVIEW, 8)
    # 词一 used twice already, 词二 once, 词三 never
    planner.record_usage(["词一", "词一", "词二"])
    plan = planner.plan_paragraph(3)  # introduced: 词一/词二/词三, max 3 repeats
    # lowest usage first: 词三 (0), 词二 (1), 词一 (2)
    assert plan.repeat_words == ["词三", "词二", "词一"]


def test_review_words_rotate():
    planner = CadencePlanner(NEW, REVIEW, 8, max_review=2)
    first = planner.plan_paragraph(0).review_words
    second = planner.plan_paragraph(1).review_words
    third = planner.plan_paragraph(2).review_words
    assert first == ["复习一", "复习二"]
    assert second == ["复习三", "复习一"]  # wraps around
    assert third == ["复习二", "复习三"]


def test_validation_errors():
    with pytest.raises(CadenceError, match="5–10"):
        CadencePlanner(NEW[:4], REVIEW, 8)
    with pytest.raises(CadenceError, match="11"):
        CadencePlanner([f"词{i}" for i in range(11)], REVIEW, 12)
    with pytest.raises(CadenceError, match="final paragraph"):
        CadencePlanner(NEW, REVIEW, 5)  # 5 new words, 5 paragraphs


def test_usage_counts_tracking():
    planner = CadencePlanner(NEW, REVIEW, 8)
    planner.record_usage(["词一", "词一", "复习二", "unknown"])
    assert planner.usage_counts()["词一"] == 2
    assert planner.usage_counts()["复习二"] == 1
    assert "unknown" not in planner.usage_counts()
