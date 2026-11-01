"""M2 unit tests: SRS engine pure functions (rating matrix, clamps, exposure)."""

from __future__ import annotations

import pytest

from langread.services.srs import (
    DEFAULT_PARAMS,
    RATINGS,
    SrsParams,
    SrsState,
    apply_exposure,
    apply_rating,
    promote,
)

NOW = "2026-11-01T00:00:00+00:00"


def test_ratings_constant():
    assert RATINGS == ("difficult", "easy", "standard", "unchanged")


# ---- promotion ----


def test_promote_initial_state():
    state = promote(DEFAULT_PARAMS, NOW)
    assert state.ease == 2.5
    assert state.interval_days == 1.0
    assert state.due_at == "2026-11-02T00:00:00+00:00"
    assert (state.reps, state.lapses, state.last_rated_at) == (1, 0, NOW)


# ---- rating matrix from a fresh promotion ----

FRESH = promote(DEFAULT_PARAMS, NOW)


def test_rating_standard():
    out = apply_rating(FRESH, "standard", DEFAULT_PARAMS, NOW)
    assert out.interval_days == pytest.approx(2.5)  # 1.0 × ease 2.5
    assert out.reps == 2
    assert out.lapses == 0
    assert out.ease == 2.5
    assert out.due_at == "2026-11-03T12:00:00+00:00"  # +2.5 days
    assert out.last_rated_at == NOW


def test_rating_easy():
    out = apply_rating(FRESH, "easy", DEFAULT_PARAMS, NOW)
    assert out.interval_days == pytest.approx(3.25)  # 1.0 × 2.5 × 1.3
    assert out.ease == pytest.approx(2.65)  # +0.15
    assert out.reps == 2
    assert out.due_at == "2026-11-04T06:00:00+00:00"  # +3.25 days


def test_rating_difficult():
    out = apply_rating(FRESH, "difficult", DEFAULT_PARAMS, NOW)
    assert out.interval_days == pytest.approx(0.5)  # relearn step
    assert out.ease == pytest.approx(2.3)  # -0.20
    assert out.lapses == 1
    assert out.reps == 1  # unchanged by difficult
    assert out.due_at == "2026-11-01T12:00:00+00:00"  # +0.5 days


def test_rating_unchanged_is_identity():
    out = apply_rating(FRESH, "unchanged", DEFAULT_PARAMS, NOW)
    assert out == FRESH


def test_invalid_rating_rejected():
    with pytest.raises(ValueError):
        apply_rating(FRESH, "bogus", DEFAULT_PARAMS, NOW)


# ---- growth chains ----


def test_standard_chain_grows_geometrically():
    state = FRESH
    intervals = []
    for _ in range(4):
        state = apply_rating(state, "standard", DEFAULT_PARAMS, NOW)
        intervals.append(state.interval_days)
    # 1×2.5 → clamped to ≥ min(1); growth: 2.5, 6.25, 15.625, 39.06
    assert intervals[0] == pytest.approx(2.5)
    assert intervals[1] == pytest.approx(6.25)
    assert intervals[2] == pytest.approx(15.625)
    assert intervals[3] == pytest.approx(39.0625)


def test_interval_clamped_to_max():
    state = SrsState(ease=2.5, interval_days=300.0, reps=10)
    out = apply_rating(state, "standard", DEFAULT_PARAMS, NOW)
    assert out.interval_days == 365.0  # 300×2.5=750 → clamped


def test_ease_clamped_high_and_low():
    state = SrsState(ease=2.9)
    out = apply_rating(state, "easy", DEFAULT_PARAMS, NOW)
    assert out.ease == 3.0  # 2.9+0.15 → clamped
    state = SrsState(ease=1.35)
    out = apply_rating(state, "difficult", DEFAULT_PARAMS, NOW)
    assert out.ease == 1.3


def test_min_interval_applies_to_standard_growth():
    params = SrsParams(min_interval_days=3.0)
    state = SrsState(ease=1.0, interval_days=1.0)
    out = apply_rating(state, "standard", params, NOW)
    assert out.interval_days == 3.0  # 1×1=1 → clamped up to 3
    # …but the difficult relearn step is exempt (sub-day return, §8.6.1)
    out = apply_rating(state, "difficult", params, NOW)
    assert out.interval_days == 0.5


# ---- exposure ----


def test_exposure_grows_gently_and_keeps_reps():
    out = apply_exposure(FRESH, DEFAULT_PARAMS, NOW)
    assert out.interval_days == pytest.approx(2.5)  # 1 × 2.5 × 1.0
    assert out.reps == FRESH.reps and out.lapses == FRESH.lapses
    assert out.last_rated_at == FRESH.last_rated_at  # not a review
    assert out.due_at == "2026-11-03T12:00:00+00:00"


def test_exposure_multiplier_param():
    params = SrsParams(exposure_multiplier=0.5)  # gentler growth
    out = apply_exposure(FRESH, params, NOW)
    assert out.interval_days == pytest.approx(1.25)


def test_exposure_on_word_without_interval_uses_initial():
    state = SrsState(ease=2.5, interval_days=None)
    out = apply_exposure(state, DEFAULT_PARAMS, NOW)
    assert out.interval_days == pytest.approx(2.5)


def test_exposure_custom_now_must_be_iso_string():
    with pytest.raises(ValueError):
        apply_exposure(FRESH, DEFAULT_PARAMS, "not-a-date")
