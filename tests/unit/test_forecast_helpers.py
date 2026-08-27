import pytest

from app.api.forecast import _county_key, _get_endpoint
from app.services.city_forecast_map import CITY_FORECAST_MAP

# The 22 first-level administrative divisions of Taiwan (incl. the outlying
# counties) that the CWA township forecast covers.
EXPECTED_COUNTY_COUNT = 22


def test_normalises_the_two_ways_of_writing_tai():
    assert _county_key("台北市") == "臺北市"
    assert _county_key("臺北市") == "臺北市"
    assert _county_key("台中市") == _county_key("臺中市")


def test_normalisation_is_idempotent():
    once = _county_key("台南市")
    assert _county_key(once) == once


@pytest.mark.parametrize("county", ["台北市", "臺北市", "台東縣", "臺東縣"])
def test_resolves_an_endpoint_for_either_spelling(county):
    assert _get_endpoint(county) is not None
    assert _get_endpoint(county).startswith("F-D0047-")


def test_unknown_county_has_no_endpoint():
    assert _get_endpoint("東京都") is None
    assert _get_endpoint("") is None


def test_every_taiwanese_county_is_mapped():
    assert len(CITY_FORECAST_MAP) == EXPECTED_COUNTY_COUNT


def test_every_endpoint_id_is_unique():
    endpoints = list(CITY_FORECAST_MAP.values())
    assert len(set(endpoints)) == len(endpoints)


def test_every_endpoint_follows_the_cwa_dataset_naming():
    for county, endpoint in CITY_FORECAST_MAP.items():
        assert endpoint.startswith("F-D0047-"), county
        assert endpoint.removeprefix("F-D0047-").isdigit(), county


def test_map_keys_use_the_formal_tai_character():
    # Lookups normalise 台 -> 臺, so a key written with 台 would be unreachable.
    for county in CITY_FORECAST_MAP:
        assert "台" not in county, county
