import math

import pytest

from app.utils import haversine


def test_distance_to_self_is_zero():
    assert haversine(25.0330, 121.5654, 25.0330, 121.5654) == pytest.approx(0.0)


def test_one_degree_of_latitude_is_about_111km():
    # A degree of latitude is R * pi / 180 regardless of longitude.
    expected = 6371 * math.pi / 180
    assert haversine(25.0, 121.0, 26.0, 121.0) == pytest.approx(expected, rel=1e-9)


def test_taipei_to_kaohsiung():
    # Taipei 101 -> Kaohsiung station, ~296 km great-circle.
    d = haversine(25.0330, 121.5654, 22.6273, 120.3014)
    assert d == pytest.approx(296, abs=5)


def test_is_symmetric():
    a = haversine(25.0, 121.5, 22.6, 120.3)
    b = haversine(22.6, 120.3, 25.0, 121.5)
    assert a == pytest.approx(b)


def test_longitude_degree_shrinks_toward_the_pole():
    at_equator = haversine(0.0, 120.0, 0.0, 121.0)
    at_taiwan = haversine(25.0, 120.0, 25.0, 121.0)
    assert at_taiwan < at_equator
    assert at_taiwan == pytest.approx(at_equator * math.cos(math.radians(25)), rel=1e-3)


def test_antipodal_points_are_half_the_circumference():
    d = haversine(0.0, 0.0, 0.0, 180.0)
    assert d == pytest.approx(6371 * math.pi, rel=1e-9)
