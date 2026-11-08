"""Unit tests: SRS engine — lesson-frequency variant (rating matrix, clamps,
selection weights, LearnedWordSelector)."""

from __future__ import annotations

import random

import pytest

from langread.services.srs import (
    DEFAULT_PARAMS,
    RATINGS,
    SrsParams,
    SrsState,
    WordCandidate,
    apply_rating,
    difficulty,
    novelty,
    promote,
    selection_weight,
    staleness,
)
from langread.services.srs import LearnedWordSelector

NOW = "2026-11-01T00:00:00+00:00"


def test_ratings_constant():
    assert RATINGS == ("difficult", "easy", "standard", "unchanged")


# ---- promotion ----


def test_promote_initial_state():
    state = promote(DEFAULT_PARAMS)
    assert state.ease == 2.5
    assert (state.reps, state.lapses, state.last_rated_at) == (0, 0, None)


# ---- rating matrix from a fresh promotion ----


FRESH = promote(DEFAULT_PARAMS)


def test_rating_standard():
    out = apply_rating(FRESH, "standard", DEFAULT_PARAMS, NOW)
    assert out.reps == 1
    assert out.lapses == 0
    assert out.ease == 2.5
    assert out.last_rated_at == NOW


def test_rating_easy():
    out = apply_rating(FRESH, "easy", DEFAULT_PARAMS, NOW)
    assert out.ease == pytest.approx(2.65)  # +0.15
    assert out.reps == 1


def test_rating_difficult():
    out = apply_rating(FRESH, "difficult", DEFAULT_PARAMS, NOW)
    assert out.ease == pytest.approx(2.3)  # -0.20
    assert out.lapses == 1
    assert out.reps == 0  # difficult does not count as a normal rep


def test_rating_unchanged_is_identity():
    out = apply_rating(FRESH, "unchanged", DEFAULT_PARAMS, NOW)
    assert out == FRESH


def test_invalid_rating_rejected():
    with pytest.raises(ValueError):
        apply_rating(FRESH, "bogus", DEFAULT_PARAMS, NOW)


def test_ease_clamped_high_and_low():
    state = SrsState(ease=2.9)
    out = apply_rating(state, "easy", DEFAULT_PARAMS, NOW)
    assert out.ease == 3.0  # 2.9+0.15 → clamped
    state = SrsState(ease=1.35)
    out = apply_rating(state, "difficult", DEFAULT_PARAMS, NOW)
    assert out.ease == 1.3


def test_easy_chain_clamps_at_ease_max():
    state = FRESH
    for _ in range(6):
        state = apply_rating(state, "easy", DEFAULT_PARAMS, NOW)
    assert state.ease == 3.0
    assert state.reps == 6


# ---- factor functions ----


def test_novelty_decays_linearly_to_zero():
    params = DEFAULT_PARAMS  # window = 5 lessons
    assert novelty(0, params) == 1.0
    assert novelty(2.5, params) == pytest.approx(0.5)
    assert novelty(5, params) == 0.0
    assert novelty(9, params) == 0.0  # clamped at 0 (routine)


def test_staleness_saturates_at_target():
    params = DEFAULT_PARAMS  # target = 8 lessons
    assert staleness(0, params) == 0.0
    assert staleness(4, params) == pytest.approx(0.5)
    assert staleness(8, params) == 1.0
    assert staleness(50, params) == 1.0  # fully stale forever after


def test_difficulty_unrated_is_neutral():
    assert difficulty(2.5, False, DEFAULT_PARAMS) == 0.5
    assert difficulty(1.3, False, DEFAULT_PARAMS) == 0.5


def test_difficulty_low_ease_is_harder():
    hard = difficulty(1.4, True, DEFAULT_PARAMS)
    easy = difficulty(2.9, True, DEFAULT_PARAMS)
    assert 0.0 <= easy < hard <= 1.0


# ---- selection weight ----


def _candidate(text, first=1, last=None, ease=2.5, reps=0):
    return WordCandidate(
        text=text,
        first_learned_lesson_id=first,
        last_seen_lesson_id=last if last is not None else first,
        ease=ease,
        reps=reps,
    )


def test_weight_recently_learned_beats_old():
    current = 10
    fresh = _candidate("新", first=9)             # learned 1 lesson ago
    old = _candidate("旧", first=1, last=9)      # learned 9 lessons ago, seen recently
    # equal staleness → factor 1 (novelty) decides
    assert selection_weight(fresh, current, DEFAULT_PARAMS) > selection_weight(
        old, current, DEFAULT_PARAMS
    )


def test_weight_stale_word_beats_freshly_used():
    current = 10
    stale = _candidate("陈", first=1, last=1)   # not seen for 9 lessons
    recent = _candidate("近", first=1, last=9)  # used 1 lesson ago
    assert selection_weight(stale, current, DEFAULT_PARAMS) > selection_weight(
        recent, current, DEFAULT_PARAMS
    )


def test_weight_difficult_beats_easy_when_rated():
    current = 10
    hard = _candidate("难", first=2, ease=1.4, reps=1)
    easy = _candidate("易", first=2, ease=2.9, reps=1)
    assert selection_weight(hard, current, DEFAULT_PARAMS) > selection_weight(
        easy, current, DEFAULT_PARAMS
    )


def test_weight_never_reused_word_counts_first_lesson_as_last_seen():
    never = _candidate("旧", first=1)
    assert selection_weight(never, 6, DEFAULT_PARAMS) == selection_weight(
        _candidate("旧", first=1, last=1), 6, DEFAULT_PARAMS
    )


def test_unrated_words_with_same_age_and_gap_have_equal_weights():
    a = _candidate("甲", first=3, reps=0)
    b = _candidate("乙", first=3, reps=0, ease=1.4)
    assert selection_weight(a, 10, DEFAULT_PARAMS) == selection_weight(
        b, 10, DEFAULT_PARAMS
    )


# ---- selector ----


def test_selector_pick_respects_count_and_uniqueness():
    candidates = [_candidate(f"词{i:02d}") for i in range(10)]
    selector = LearnedWordSelector(candidates, 11, DEFAULT_PARAMS,
                                   rng=random.Random(42))
    picks = selector.pick(3)
    assert len(picks) == 3
    assert len(set(picks)) == 3


def test_selector_pick_fewer_when_pool_is_small():
    selector = LearnedWordSelector([_candidate("甲")], 5, DEFAULT_PARAMS,
                                   rng=random.Random(0))
    assert selector.pick(2) == ["甲"]


def test_selector_pick_empty_pool():
    selector = LearnedWordSelector([], 5, DEFAULT_PARAMS)
    assert selector.pick(2) == []


def test_selector_excludes_words_learned_in_current_lesson():
    candidates = [_candidate("旧词", first=1), _candidate("今词", first=5)]
    selector = LearnedWordSelector(candidates, 5, DEFAULT_PARAMS,
                                   rng=random.Random(0))
    for _ in range(20):
        assert "今词" not in selector.pick(count=1)


def test_selector_whole_lesson_cooldown_excludes_used_words():
    candidates = [_candidate(f"词{i}") for i in range(3)]
    selector = LearnedWordSelector(candidates, 10, DEFAULT_PARAMS,
                                   rng=random.Random(7))
    selector.record_usage(["词0"], paragraph_index=0)
    for _ in range(20):
        picks = selector.pick(count=3, paragraph_index=1)
        assert "词0" not in picks
        assert set(picks) == {"词1", "词2"}


def test_selector_cooldown_paragraphs_param_allows_return():
    params = SrsParams(same_lesson_cooldown_paragraphs=1)
    candidates = [_candidate(f"词{i}") for i in range(3)]
    selector = LearnedWordSelector(candidates, 10, params,
                                   rng=random.Random(7))
    selector.record_usage(["词0"], paragraph_index=0)
    # 2 paragraphs later (gap 2 > cooldown 1) the word is eligible again
    picks = selector.pick(count=3, paragraph_index=2)
    assert "词0" in picks


def test_selector_seeded_rng_is_deterministic():
    candidates = [_candidate(f"词{i:02d}", first=i + 1) for i in range(10)]
    a = LearnedWordSelector(candidates, 11, DEFAULT_PARAMS,
                            rng=random.Random(99)).pick(3)
    b = LearnedWordSelector(candidates, 11, DEFAULT_PARAMS,
                            rng=random.Random(99)).pick(3)
    assert a == b


def test_selector_stale_words_picked_far_more_often():
    stale = [_candidate(f"陈{i:02d}", first=1, last=1) for i in range(5)]
    fresh = [_candidate(f"近{i:02d}", first=1, last=9) for i in range(5)]
    counts = {"stale": 0, "fresh": 0}
    for seed in range(200):
        selector = LearnedWordSelector(stale + fresh, 10, DEFAULT_PARAMS,
                                       rng=random.Random(seed))
        pick = selector.pick(count=1)[0]
        counts["stale" if pick.startswith("陈") else "fresh"] += 1
    assert counts["stale"] > counts["fresh"] * 2


def test_selector_zero_weights_fall_back_to_uniform():
    params = SrsParams(weight_novelty=0.0, weight_staleness=0.0,
                       weight_difficulty=0.0)
    selector = LearnedWordSelector([_candidate("甲"), _candidate("乙")], 5,
                                   params, rng=random.Random(3))
    picks = selector.pick(2)
    assert len(picks) == 2  # uniform fallback still picks distinct words


def test_selector_top_weighted_orders_by_weight():
    stale = _candidate("陈", first=1, last=1)
    fresh = _candidate("近", first=1, last=9)
    selector = LearnedWordSelector([fresh, stale], 10, DEFAULT_PARAMS)
    assert selector.top_weighted(2)[0] == "陈"
