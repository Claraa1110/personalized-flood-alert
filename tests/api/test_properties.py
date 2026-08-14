"""Property CRUD: serialisation, ownership scoping and lookup fallbacks."""

from datetime import datetime
from uuid import uuid4

from geoalchemy2.shape import from_shape
from shapely.geometry import Point

from app.api.properties import lookup_district_and_risk, to_response
from app.models.property import Property
from tests.conftest import DEVICE_ID
from tests.fakes import FakeSession, Row

LAT, LNG = 25.0330, 121.5654


def _property(**overrides) -> Property:
    fields = {
        "id": uuid4(),
        "device_id": DEVICE_ID,
        "name": "家",
        "type": "house",
        "location": from_shape(Point(LNG, LAT), srid=4326),
        "address": "臺北市信義區",
        "floor_level": 2,
        "alert_enabled": True,
        "created_at": datetime(2026, 8, 14, 10, 0, 0),
        "district_name": "臺北市信義區",
        "flood_risk_level": 3,
        "custom_type_name": None,
    }
    fields.update(overrides)
    return Property(**fields)


# ── to_response ─────────────────────────────────────────────────────────────


def test_decodes_the_postgis_point_into_lat_lng():
    resp = to_response(_property())

    assert resp.latitude == LAT
    assert resp.longitude == LNG


def test_carries_the_stored_fields_through():
    prop = _property()

    resp = to_response(prop)

    assert resp.id == prop.id
    assert resp.name == "家"
    assert resp.type == "house"
    assert resp.floor_level == 2
    assert resp.alert_enabled is True
    assert resp.district_name == "臺北市信義區"
    assert resp.flood_risk_level == 3


def test_rainfall_fields_are_absent_without_an_observation():
    resp = to_response(_property())

    assert resp.rainfall_now_mm is None
    assert resp.rainfall_1hr_mm is None
    assert resp.rainfall_24hr_mm is None


def test_rainfall_fields_are_merged_when_an_observation_is_supplied():
    row = Row(rainfall_mm=3.5, rainfall_1hr=12.0, rainfall_24hr=48.5)

    resp = to_response(_property(), row)

    assert resp.rainfall_now_mm == 3.5
    assert resp.rainfall_1hr_mm == 12.0
    assert resp.rainfall_24hr_mm == 48.5


def test_custom_type_name_survives_serialisation():
    resp = to_response(_property(type="custom", custom_type_name="工作室"))

    assert resp.type == "custom"
    assert resp.custom_type_name == "工作室"


# ── lookup_district_and_risk ────────────────────────────────────────────────


async def test_concatenates_county_and_town_into_one_district_name():
    db = FakeSession()
    db.when("FROM districts", rows=[Row(county_name="臺北市", town_name="信義區")])
    db.when("flood_risk_zones", rows=[Row(risk_level=4)])

    district, risk = await lookup_district_and_risk(db, LAT, LNG)

    assert district == "臺北市信義區"
    assert risk == 4


async def test_missing_district_and_missing_flood_zone_are_the_neutral_values():
    db = FakeSession()

    district, risk = await lookup_district_and_risk(db, LAT, LNG)

    assert district is None
    assert risk == 0


async def test_a_postgis_failure_is_swallowed_into_the_neutral_values():
    """Characterisation: a broken spatial query is indistinguishable from
    "this point is not in any district".

    ``lookup_district_and_risk`` wraps both queries in bare
    ``except Exception``. If the districts table is missing, the geometry
    index is corrupt, or PostGIS is simply unavailable, every property gets
    created with ``district_name=None`` and ``flood_risk_level=0`` and nothing
    is logged. Those two fields are what the scheduler later uses to find
    thresholds, so the property silently becomes unmonitorable (see
    ROADMAP P0-3). Tracked as ROADMAP P0-5 (observability).
    """
    db = FakeSession()
    db.when_raises("FROM districts", RuntimeError("PostGIS unavailable"))
    db.when_raises("flood_risk_zones", RuntimeError("PostGIS unavailable"))

    district, risk = await lookup_district_and_risk(db, LAT, LNG)

    assert district is None
    assert risk == 0


async def test_flood_risk_lookup_pins_the_scenario_and_takes_the_worst_zone():
    db = FakeSession()
    db.when("FROM districts", rows=[Row(county_name="臺北市", town_name="信義區")])
    db.when("flood_risk_zones", rows=[Row(risk_level=2)])

    await lookup_district_and_risk(db, LAT, LNG)

    sql = db.sql_matching("flood_risk_zones")[0]
    assert "scenario = '24h_200mm'" in sql
    assert "ORDER BY risk_level DESC" in sql


# ── HTTP: ownership scoping ─────────────────────────────────────────────────


async def test_list_returns_an_empty_array_for_a_new_device(client, db):
    resp = await client.get("/api/properties")

    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_serialises_each_property(client, db):
    db.when("FROM properties", rows=[_property(name="家"), _property(name="店面")])

    body = (await client.get("/api/properties")).json()

    assert [p["name"] for p in body] == ["家", "店面"]
    assert body[0]["latitude"] == LAT


async def test_list_issues_one_rainfall_query_per_property(client, db):
    """Characterisation of the N+1 in ``list_properties``.

    Each property triggers its own 50 km PostGIS lookup, so the query count
    grows linearly with the number of properties a device owns.
    ``properties_risk.py`` already shows the fix (LEFT JOIN LATERAL).
    Tracked as ROADMAP P1-12.
    """
    db.when("FROM properties", rows=[_property() for _ in range(4)])

    await client.get("/api/properties")

    assert len(db.sql_matching("FROM rainfall_observations")) == 4


async def test_get_404s_when_the_property_belongs_to_another_device(client, db):
    resp = await client.get(f"/api/properties/{uuid4()}")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "找不到這個財產"


async def test_update_404s_when_the_property_belongs_to_another_device(client, db):
    resp = await client.put(
        f"/api/properties/{uuid4()}",
        json={"name": "家", "type": "house", "latitude": LAT, "longitude": LNG},
    )

    assert resp.status_code == 404
    assert db.commits == 0


async def test_delete_404s_when_the_property_belongs_to_another_device(client, db):
    resp = await client.delete(f"/api/properties/{uuid4()}")

    assert resp.status_code == 404
    assert db.deleted == []
    assert db.commits == 0


async def test_delete_removes_the_property_and_commits(client, db):
    prop = _property()
    db.when("FROM properties", rows=[prop])

    resp = await client.delete(f"/api/properties/{prop.id}")

    assert resp.status_code == 200
    assert db.deleted == [prop]
    assert db.commits == 1


async def test_routes_reject_a_malformed_property_id(client):
    assert (await client.get("/api/properties/not-a-uuid")).status_code == 422
    assert (await client.delete("/api/properties/not-a-uuid")).status_code == 422


# ── HTTP: request validation ────────────────────────────────────────────────


async def test_create_rejects_an_unknown_property_type(client):
    resp = await client.post(
        "/api/properties",
        json={"name": "家", "type": "spaceship", "latitude": LAT, "longitude": LNG},
    )
    assert resp.status_code == 422


async def test_create_rejects_out_of_range_coordinates(client):
    resp = await client.post(
        "/api/properties",
        json={"name": "家", "type": "house", "latitude": 91.0, "longitude": LNG},
    )
    assert resp.status_code == 422


async def test_create_rejects_a_ground_floor_below_one(client):
    resp = await client.post(
        "/api/properties",
        json={
            "name": "家",
            "type": "house",
            "latitude": LAT,
            "longitude": LNG,
            "floor_level": 0,
        },
    )
    assert resp.status_code == 422


async def test_create_requires_a_device_header(anon_client):
    resp = await anon_client.post(
        "/api/properties",
        json={"name": "家", "type": "house", "latitude": LAT, "longitude": LNG},
    )
    assert resp.status_code == 400


async def test_property_name_length_is_unbounded_at_the_api_boundary(client):
    """Characterisation: ``name`` has no ``max_length`` in the Pydantic schema
    but the column is ``String(100)``.

    A 500-character name passes validation and fails at the database instead,
    surfacing as a 500. Tracked as ROADMAP P2-5.
    """
    from app.schemas.property import PropertyCreate

    parsed = PropertyCreate(name="家" * 500, type="house", latitude=LAT, longitude=LNG)
    assert len(parsed.name) == 500
