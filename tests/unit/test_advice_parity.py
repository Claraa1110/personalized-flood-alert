"""The push advice copy and the in-app advice copy must not drift.

``app/services/risk_engine.py`` and ``app/api/properties_risk.py`` each carry
their own hand-copied advice table (and MobileApp carries a third, in
``advice.ts``). These tests pin them together so an edit to one shows up as a
failure rather than as inconsistent wording between a notification and the
screen it opens. Deduplicating them is ROADMAP P1-4.
"""

import pytest

from app.api.properties_risk import _ADVICE, _ADVICE_DEFAULT, _get_advice
from app.services.risk_engine import (
    _PUSH_ADVICE,
    _PUSH_ADVICE_DEFAULT,
    _get_push_advice,
)

PROPERTY_TYPES = ["house", "car", "shop", "warehouse", "farm"]


def test_the_two_tables_cover_the_same_levels():
    assert set(_ADVICE) == set(_PUSH_ADVICE)
    assert set(_ADVICE_DEFAULT) == set(_PUSH_ADVICE_DEFAULT)


def test_the_two_tables_cover_the_same_property_types():
    for level in _ADVICE:
        assert set(_ADVICE[level]) == set(_PUSH_ADVICE[level])


@pytest.mark.parametrize("prop_type", PROPERTY_TYPES)
@pytest.mark.parametrize("level", ["level1", "level2"])
def test_wording_is_identical_across_both_tables(level, prop_type):
    assert _get_advice(level, prop_type) == _get_push_advice(level, prop_type)


@pytest.mark.parametrize("level", ["level1", "level2"])
def test_fallback_wording_is_identical(level):
    assert _get_advice(level, "unknown") == _get_push_advice(level, "unknown")


def test_push_advice_for_an_unknown_level_is_empty_string():
    # risk_engine returns "" where properties_risk returns None - the two
    # helpers differ in their empty case.
    assert _get_push_advice("safe", "house") == ""
    assert _get_advice("safe", "house") is None
