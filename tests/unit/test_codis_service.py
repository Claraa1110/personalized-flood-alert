import pytest

from app.services.codis_service import _get_stn_type, calculate_max_rainfall

# ── station id -> CODIS stn_type ────────────────────────────────────────────


@pytest.mark.parametrize(
    "station_id, expected",
    [
        ("466920", "cwb"),  # numeric ids are manned CWA stations
        ("467490", "cwb"),
        ("C0V660", "auto_C0"),  # letter + digit prefix
        ("C1R120", "auto_C1"),
        ("CAP020", "auto_CAP"),  # all-letter prefix
        ("A2F080", "auto_A2"),
    ],
)
def test_maps_station_id_to_stn_type(station_id, expected):
    assert _get_stn_type(station_id) == expected


def test_unrecognised_station_id_raises():
    """Characterisation: ids that start with neither digit nor A-Z blow up.

    ``re.match(r'^([A-Z]+)', ...)`` returns None and ``.group(1)`` raises
    AttributeError rather than a typed, handled error. Tracked as ROADMAP P2-4.
    """
    with pytest.raises(AttributeError):
        _get_stn_type("c0v660")  # lowercase


# ── 1h / 3h / 6h accumulation ───────────────────────────────────────────────


def _series(*values: float) -> list[dict]:
    return [{"time": f"t{i}", "rainfall_mm": v} for i, v in enumerate(values)]


def test_empty_series_is_all_zero():
    assert calculate_max_rainfall([]) == {"1h": 0.0, "3h": 0.0, "6h": 0.0}


def test_six_hours_of_rain():
    result = calculate_max_rainfall(_series(5, 10, 20, 8, 2, 1))
    assert result["1h"] == 20.0  # single largest hour
    assert result["3h"] == 38.0  # best consecutive 3h window: 10+20+8
    assert result["6h"] == 46.0  # whole-window total


def test_three_hour_window_scans_every_position():
    # The heaviest 3h block sits at the end of the series.
    result = calculate_max_rainfall(_series(1, 1, 1, 30, 30, 30))
    assert result["3h"] == 90.0


def test_results_are_rounded_to_one_decimal():
    result = calculate_max_rainfall(_series(1.05, 2.049, 3.0))
    assert result == {"1h": 3.0, "3h": 6.1, "6h": 6.1}


@pytest.mark.parametrize("short_series", [_series(80.0), _series(40.0, 40.0)])
def test_series_shorter_than_three_hours_reports_zero_for_3h(short_series):
    """Characterisation of a real defect.

    ``range(max(0, n - 2))`` is empty when n < 3, so ``max_3h`` stays 0.0
    even though 80 mm fell. The README promises 6h >= 3h >= 1h; this breaks
    that invariant and under-reports the 3h figure that feeds threshold
    calibration. Tracked as ROADMAP P1-5.
    """
    result = calculate_max_rainfall(short_series)
    assert result["1h"] > 0
    assert result["3h"] == 0.0


def test_windows_are_monotonic_for_full_length_series():
    result = calculate_max_rainfall(_series(5, 10, 20, 8, 2, 1))
    assert result["6h"] >= result["3h"] >= result["1h"]


@pytest.mark.xfail(
    strict=True,
    reason="ROADMAP P1-5: accumulation windows must stay monotonic for short series",
)
@pytest.mark.parametrize("series", [_series(80.0), _series(40.0, 40.0)])
def test_short_series_should_also_be_monotonic(series):
    result = calculate_max_rainfall(series)
    assert result["6h"] >= result["3h"] >= result["1h"]
