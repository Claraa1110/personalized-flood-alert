"""Tests for coordinate -> two-tier alert threshold resolution."""

import pytest

from app.services.threshold_service import get_two_tier_thresholds
from tests.fakes import FakeSession, Row

TAIPEI = (25.0330, 121.5654)


def _district(town="信義區", county="臺北市") -> Row:
    return Row(town_name=town, county_name=county)


def _wra(**overrides) -> Row:
    fields = {
        "lv1_1h": 40.0,
        "lv1_3h": 80.0,
        "lv1_6h": 120.0,
        "lv2_1h": 20.0,
        "lv2_3h": 40.0,
        "lv2_6h": 60.0,
    }
    fields.update(overrides)
    return Row(**fields)


@pytest.fixture
def session() -> FakeSession:
    return FakeSession()


async def test_returns_none_when_the_point_is_outside_every_district(session):
    session.when("FROM districts", rows=[])
    assert await get_two_tier_thresholds(*TAIPEI, session) is None


async def test_returns_none_when_the_district_has_no_wra_thresholds(session):
    session.when("FROM districts", rows=[_district()])
    session.when("wra_alert_thresholds", rows=[])
    assert await get_two_tier_thresholds(*TAIPEI, session) is None


async def test_returns_none_when_the_wra_row_exists_but_is_empty(session):
    session.when("FROM districts", rows=[_district()])
    session.when("wra_alert_thresholds", rows=[_wra(lv1_1h=None)])
    assert await get_two_tier_thresholds(*TAIPEI, session) is None


async def test_falls_back_to_official_wra_level2_when_uncalibrated(session):
    session.when("FROM districts", rows=[_district()])
    session.when("wra_alert_thresholds", rows=[_wra()])
    session.when("corrected_thresholds", rows=[])

    result = await get_two_tier_thresholds(*TAIPEI, session)

    assert result["level2_source"] == "original"
    assert result["district_name"] == "信義區"
    assert result["county_name"] == "臺北市"
    assert result["thresholds"]["level1"] == {"1h": 40.0, "3h": 80.0, "6h": 120.0}
    assert result["thresholds"]["level2"] == {"1h": 20.0, "3h": 40.0, "6h": 60.0}


async def test_prefers_calibrated_level2_thresholds_when_available(session):
    session.when("FROM districts", rows=[_district()])
    session.when("wra_alert_thresholds", rows=[_wra()])
    session.when(
        "corrected_thresholds",
        rows=[Row(corrected_1h=15.0, corrected_3h=30.0, corrected_6h=50.0)],
    )

    result = await get_two_tier_thresholds(*TAIPEI, session)

    assert result["level2_source"] == "corrected"
    assert result["thresholds"]["level2"] == {"1h": 15.0, "3h": 30.0, "6h": 50.0}
    # level1 always comes from WRA, never from calibration.
    assert result["thresholds"]["level1"]["1h"] == 40.0


async def test_level1_is_never_overridden_by_calibration(session):
    session.when("FROM districts", rows=[_district()])
    session.when("wra_alert_thresholds", rows=[_wra()])
    session.when(
        "corrected_thresholds",
        rows=[Row(corrected_1h=1.0, corrected_3h=1.0, corrected_6h=1.0)],
    )

    result = await get_two_tier_thresholds(*TAIPEI, session)
    assert result["thresholds"]["level1"] == {"1h": 40.0, "3h": 80.0, "6h": 120.0}


async def test_calibrated_value_at_or_above_level1_is_rejected_per_scale(session):
    """A calibrated amber threshold must stay strictly below the red one.

    Otherwise amber would never fire before red and the two-tier warning
    collapses into a single tier.
    """
    session.when("FROM districts", rows=[_district()])
    session.when("wra_alert_thresholds", rows=[_wra()])
    session.when(
        "corrected_thresholds",
        rows=[
            Row(
                corrected_1h=45.0,  # above level1 (40) -> rejected
                corrected_3h=80.0,  # equal to level1 (80) -> rejected
                corrected_6h=55.0,  # below level1 (120) -> kept
            )
        ],
    )

    result = await get_two_tier_thresholds(*TAIPEI, session)

    level2 = result["thresholds"]["level2"]
    assert level2["1h"] == 20.0  # fell back to WRA lv2
    assert level2["3h"] == 40.0  # fell back to WRA lv2
    assert level2["6h"] == 55.0  # calibrated value survived
    # The source label still says 'corrected' even after a partial fallback.
    assert result["level2_source"] == "corrected"


async def test_a_null_corrected_1h_disables_the_whole_calibrated_row(session):
    session.when("FROM districts", rows=[_district()])
    session.when("wra_alert_thresholds", rows=[_wra()])
    session.when(
        "corrected_thresholds",
        rows=[Row(corrected_1h=None, corrected_3h=30.0, corrected_6h=50.0)],
    )

    result = await get_two_tier_thresholds(*TAIPEI, session)

    assert result["level2_source"] == "original"
    assert result["thresholds"]["level2"]["3h"] == 40.0


async def test_partial_wra_coverage_yields_none_for_the_missing_scales(session):
    session.when("FROM districts", rows=[_district()])
    session.when("wra_alert_thresholds", rows=[_wra(lv1_6h=None, lv2_6h=None)])
    session.when("corrected_thresholds", rows=[])

    result = await get_two_tier_thresholds(*TAIPEI, session)

    assert result["thresholds"]["level1"]["6h"] is None
    assert result["thresholds"]["level2"]["6h"] is None


async def test_district_lookup_is_parameterised_not_interpolated(session):
    session.when("FROM districts", rows=[_district()])
    session.when("wra_alert_thresholds", rows=[_wra()])
    session.when("corrected_thresholds", rows=[])

    await get_two_tier_thresholds(*TAIPEI, session)

    params = session.params_for("FROM districts")[0]
    assert params == {"lat": TAIPEI[0], "lng": TAIPEI[1]}
