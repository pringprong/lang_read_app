"""M6 unit tests: cadence planner."""

from __future__ import annotations

import pytest

from langread.services.cadence import CadenceError, CadencePlanner

NEW = ["词一", "词二", "词三", "词四", "词五"]


def test_first_use_one_per_paragraph_then_none():
    planner = CadencePlanner(NEW, 8)
    plans = [planner.plan_paragraph(i) for i in range(8)]
    assert [p.first_use for p in plans[:5]] == NEW
    assert plans[5].first_use is None
    assert plans[6].first_use is None


def test_final_paragraph_all_new_words_no_first_use():
    planner = CadencePlanner(NEW, 8)
    final = planner.plan_paragraph(7)
    assert final.is_final
    assert final.first_use is None
    assert final.all_new_words == NEW


def test_repeats_are_introduced_words():
    planner = CadencePlanner(NEW, 8)
    plan = planner.plan_paragraph(3)  # 词一..词三 introduced
    assert set(plan.repeat_words) <= {"词一", "词二", "词三"}
    assert "词四" not in plan.repeat_words and "词五" not in plan.repeat_words


def test_repeats_prefer_lowest_usage():
    planner = CadencePlanner(NEW, 8)
    # 词一 used twice already, 词二 once, 词三 never
    planner.record_usage(["词一", "词一", "词二"])
    plan = planner.plan_paragraph(3)  # introduced: 词一/词二/词三, max 3 repeats
    # lowest usage first: 词三 (0), 词二 (1), 词一 (2)
    assert plan.repeat_words == ["词三", "词二", "词一"]


def test_review_words_are_passed_through_per_paragraph():
    """Review (Learned) words are chosen by the SRS selector, not the
    planner — the planner passes them through unchanged, final paragraph
    included."""
    planner = CadencePlanner(NEW, 8)
    assert planner.plan_paragraph(0, ["复习一", "复习二"]).review_words == [
        "复习一", "复习二"
    ]
    assert planner.plan_paragraph(4, ["复习三"]).review_words == ["复习三"]
    assert planner.plan_paragraph(7, ["复习一"]).review_words == ["复习一"]
    # no review words supplied → empty, never an error
    assert planner.plan_paragraph(1).review_words == []
    assert planner.plan_paragraph(7).review_words == []


def test_validation_errors():
    with pytest.raises(CadenceError, match="5–10"):
        CadencePlanner(NEW[:4], 8)
    with pytest.raises(CadenceError, match="11"):
        CadencePlanner([f"词{i}" for i in range(11)], 12)
    with pytest.raises(CadenceError, match="final paragraph"):
        CadencePlanner(NEW, 5)  # 5 new words, 5 paragraphs
    with pytest.raises(CadenceError, match="out of range"):
        CadencePlanner(NEW, 8).plan_paragraph(8)


def test_usage_counts_tracking():
    planner = CadencePlanner(NEW, 8)
    planner.record_usage(["词一", "词一", "复习二", "unknown"])
    assert planner.usage_counts()["词一"] == 2
    assert "复习二" not in planner.usage_counts()  # not a planned new word
    assert "unknown" not in planner.usage_counts()
