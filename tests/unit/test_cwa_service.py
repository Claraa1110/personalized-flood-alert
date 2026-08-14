import pytest

from app.services.cwa_service import parse_rainfall


@pytest.mark.parametrize(
    "raw, expected",
    [
        (12.5, 12.5),
        ("12.5", 12.5),
        (0, 0.0),
        ("0", 0.0),
        (0.5, 0.5),
    ],
)
def test_parses_valid_measurements(raw, expected):
    assert parse_rainfall(raw) == expected


@pytest.mark.parametrize("raw", [None, "", "N/A", "  ", object()])
def test_unparseable_values_become_zero(raw):
    assert parse_rainfall(raw) == 0.0


@pytest.mark.parametrize("sentinel", [-99, -990, -99.0, "-99"])
def test_cwa_missing_value_sentinels_are_flattened_to_zero(sentinel):
    """Characterisation test: CWA encodes 'no data' as -99 / -990.

    ``max(0.0, v)`` turns every one of those into 0.0 mm, so a rain gauge
    that is offline is indistinguishable from a gauge reporting no rain.
    In an alerting system that silently suppresses warnings. Tracked as
    ROADMAP P0-4.
    """
    assert parse_rainfall(sentinel) == 0.0


@pytest.mark.xfail(
    strict=True,
    reason="ROADMAP P0-4: missing readings must be None, not 0.0 mm",
)
@pytest.mark.parametrize("sentinel", [-99, -990])
def test_missing_readings_should_be_distinguishable_from_zero(sentinel):
    assert parse_rainfall(sentinel) is None


def test_negative_readings_are_clamped_not_dropped():
    # A physically impossible negative reading is silently clamped to 0.
    assert parse_rainfall(-3.2) == 0.0
