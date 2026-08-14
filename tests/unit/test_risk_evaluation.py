"""Tests for the risk classification used by ``GET /api/properties-with-risk``.

This is the logic that decides what colour a property shows in the app, so it
is the highest-consequence pure function in the backend.
"""

import pytest

from app.api.properties_risk import _evaluate, _f, _get_advice, _max_pct

# 1h/3h/6h thresholds in mm. level1 = red (WRA warning), level2 = amber.
T1 = {"1h": 40.0, "3h": 80.0, "6h": 120.0}
T2 = {"1h": 20.0, "3h": 40.0, "6h": 60.0}


# ── level classification ────────────────────────────────────────────────────


def test_no_rain_is_safe():
    level, pct = _evaluate(0.0, 0.0, 0.0, T1, T2)
    assert level == "safe"
    assert pct == 0.0


def test_below_every_threshold_is_safe():
    level, _ = _evaluate(19.9, 39.9, 59.9, T1, T2)
    assert level == "safe"


def test_crossing_a_level2_threshold_raises_amber():
    level, _ = _evaluate(25.0, 0.0, 0.0, T1, T2)
    assert level == "level2"


def test_crossing_a_level1_threshold_raises_red():
    level, _ = _evaluate(45.0, 0.0, 0.0, T1, T2)
    assert level == "level1"


@pytest.mark.parametrize("scale_index", [0, 1, 2])
def test_any_single_timescale_can_trigger(scale_index):
    rain = [0.0, 0.0, 0.0]
    rain[scale_index] = [40.0, 80.0, 120.0][scale_index]
    level, _ = _evaluate(*rain, T1, T2)
    assert level == "level1"


def test_threshold_is_inclusive():
    # Exactly at the threshold must trigger, not sit one drop below.
    assert _evaluate(20.0, 0.0, 0.0, T1, T2)[0] == "level2"
    assert _evaluate(40.0, 0.0, 0.0, T1, T2)[0] == "level1"


def test_level1_wins_over_level2_when_both_are_crossed():
    level, _ = _evaluate(45.0, 45.0, 0.0, T1, T2)
    assert level == "level1"


def test_a_null_threshold_for_one_scale_does_not_block_the_others():
    t1 = {"3h": 80.0}  # 1h and 6h unknown for this district
    t2 = {"3h": 40.0}
    assert _evaluate(500.0, 85.0, 500.0, t1, t2)[0] == "level1"


# ── risk percentage ─────────────────────────────────────────────────────────


def test_pct_is_the_worst_scale_relative_to_the_amber_threshold():
    # 10/20 = 50%, 30/40 = 75%, 15/60 = 25% -> 75%
    _, pct = _evaluate(10.0, 30.0, 15.0, T1, T2)
    assert pct == pytest.approx(75.0)


def test_pct_is_floored_at_100_once_red_is_reached():
    _, pct = _evaluate(45.0, 0.0, 0.0, T1, T2)
    assert pct >= 100.0


def test_max_pct_ignores_scales_without_a_threshold():
    assert _max_pct(10.0, 999.0, 999.0, {"1h": 20.0}) == pytest.approx(50.0)


def test_max_pct_without_any_threshold_is_zero():
    assert _max_pct(999.0, 999.0, 999.0, {}) == 0.0


# ── missing-threshold behaviour ─────────────────────────────────────────────


def test_property_outside_any_known_district_reports_safe():
    """Characterisation of a real safety gap.

    When PostGIS finds no district (offshore islands, boundary gaps, an
    un-imported county) both threshold dicts are empty and every rainfall
    value classifies as 'safe'. The app shows a reassuring green badge for a
    property standing in 500 mm of rain, and the scheduler separately skips
    the property entirely, so no alert is written either. There should be an
    explicit 'unknown' state. Tracked as ROADMAP P0-3.
    """
    level, pct = _evaluate(500.0, 500.0, 500.0, {}, {})
    assert level == "safe"
    assert pct == 0.0


def test_missing_amber_thresholds_still_allow_red():
    level, _ = _evaluate(45.0, 0.0, 0.0, T1, {})
    assert level == "level1"


# ── advice copy ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize("prop_type", ["house", "car", "shop", "warehouse", "farm"])
@pytest.mark.parametrize("level", ["level1", "level2"])
def test_every_property_type_has_bespoke_advice(level, prop_type):
    advice = _get_advice(level, prop_type)
    assert advice
    assert advice != _get_advice(level, "unknown-type")


def test_safe_properties_get_no_advice():
    assert _get_advice("safe", "house") is None


def test_unknown_property_type_falls_back_to_generic_advice():
    assert _get_advice("level1", "spaceship") == _get_advice("level1", "custom")
    assert _get_advice("level2", "spaceship") is not None


def test_level1_advice_is_more_urgent_than_level2():
    for prop_type in ("house", "car", "shop", "warehouse", "farm"):
        assert "緊急" in _get_advice("level1", prop_type)
        assert "緊急" not in _get_advice("level2", prop_type)


# ── small helpers ───────────────────────────────────────────────────────────


def test_f_converts_numerics_and_passes_none_through():
    assert _f(3) == 3.0
    assert isinstance(_f(3), float)
    assert _f("4.5") == 4.5
    assert _f(None) is None
