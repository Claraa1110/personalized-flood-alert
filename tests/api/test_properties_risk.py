"""End-to-end shape of ``GET /api/properties-with-risk``.

This is the screen the user actually looks at during a storm, so the response
contract is worth pinning: field names, level values and the badge percentage.
"""

from uuid import uuid4

from tests.fakes import Row

PROP_ID = uuid4()


def _property_row(**overrides) -> Row:
    fields = {
        "id": PROP_ID,
        "name": "家",
        "type": "house",
        "custom_type_name": None,
        "address": "臺北市信義區",
        "district_name": "臺北市信義區",
        "alert_enabled": True,
        "lat": 25.0330,
        "lng": 121.5654,
        "town_name": "信義區",
        "county_name": "臺北市",
    }
    fields.update(overrides)
    return Row(**fields)


def _rainfall_row(r1h=0.0, r3h=0.0, r6h=0.0) -> Row:
    return Row(property_id=PROP_ID, r1h=r1h, r3h=r3h, r6h=r6h)


def _wra_row(**overrides) -> Row:
    fields = {
        "district_name": "信義區",
        "lv1_1h": 40.0,
        "lv1_3h": 80.0,
        "lv1_6h": 120.0,
        "lv2_1h": 20.0,
        "lv2_3h": 40.0,
        "lv2_6h": 60.0,
    }
    fields.update(overrides)
    return Row(**fields)


def _stub(db, *, props, rainfall=(), wra=(), corrected=()):
    db.when("FROM properties p LEFT JOIN LATERAL ( SELECT town_name", rows=props)
    db.when("rainfall_observations", rows=rainfall)
    db.when("FROM wra_alert_thresholds", rows=wra)
    db.when("FROM corrected_thresholds", rows=corrected)


async def test_a_device_with_no_properties_gets_an_empty_list(client, db):
    resp = await client.get("/api/properties-with-risk")

    assert resp.status_code == 200
    assert resp.json() == []


async def test_dry_property_is_safe_with_no_advice(client, db):
    _stub(db, props=[_property_row()], rainfall=[_rainfall_row()], wra=[_wra_row()])

    body = (await client.get("/api/properties-with-risk")).json()

    assert len(body) == 1
    assert body[0]["level"] == "safe"
    assert body[0]["risk_action"] is None
    assert body[0]["risk_pct"] == 0.0


async def test_response_carries_the_full_property_contract(client, db):
    _stub(db, props=[_property_row()], rainfall=[_rainfall_row()], wra=[_wra_row()])

    item = (await client.get("/api/properties-with-risk")).json()[0]

    assert item["id"] == str(PROP_ID)
    assert item["name"] == "家"
    assert item["type"] == "house"
    assert item["address"] == "臺北市信義區"
    assert item["latitude"] == 25.0330
    assert item["longitude"] == 121.5654
    assert item["rainfall"] == {"1h": 0.0, "3h": 0.0, "6h": 0.0}


async def test_amber_when_the_calibrated_threshold_is_crossed(client, db):
    _stub(
        db,
        props=[_property_row()],
        rainfall=[_rainfall_row(r1h=25.0)],
        wra=[_wra_row()],
    )

    item = (await client.get("/api/properties-with-risk")).json()[0]

    assert item["level"] == "level2"
    assert item["risk_pct"] == 125.0  # 25 mm against a 20 mm amber threshold
    assert "留意" in item["risk_action"]


async def test_red_when_the_wra_warning_threshold_is_crossed(client, db):
    _stub(
        db,
        props=[_property_row()],
        rainfall=[_rainfall_row(r3h=95.0)],
        wra=[_wra_row()],
    )

    item = (await client.get("/api/properties-with-risk")).json()[0]

    assert item["level"] == "level1"
    assert item["risk_pct"] >= 100.0
    assert item["risk_action"].startswith("緊急")


async def test_calibrated_thresholds_take_priority_over_wra(client, db):
    _stub(
        db,
        props=[_property_row()],
        rainfall=[_rainfall_row(r1h=16.0)],
        wra=[_wra_row()],
        corrected=[
            Row(
                county_name="臺北市",
                district_name="信義區",
                corrected_1h=15.0,
                corrected_3h=30.0,
                corrected_6h=50.0,
            )
        ],
    )

    item = (await client.get("/api/properties-with-risk")).json()[0]

    # 16 mm clears the calibrated 15 mm but not the official 20 mm.
    assert item["level"] == "level2"


async def test_a_calibrated_threshold_above_level1_is_ignored(client, db):
    _stub(
        db,
        props=[_property_row()],
        rainfall=[_rainfall_row(r1h=25.0)],
        wra=[_wra_row()],
        corrected=[
            Row(
                county_name="臺北市",
                district_name="信義區",
                corrected_1h=45.0,  # above the 40 mm red threshold - nonsense
                corrected_3h=None,
                corrected_6h=None,
            )
        ],
    )

    item = (await client.get("/api/properties-with-risk")).json()[0]

    # Falls back to the official 20 mm amber threshold rather than trusting 45.
    assert item["level"] == "level2"


async def test_a_property_with_no_rainfall_row_reads_as_zero(client, db):
    _stub(db, props=[_property_row()], rainfall=[], wra=[_wra_row()])

    item = (await client.get("/api/properties-with-risk")).json()[0]

    assert item["rainfall"] == {"1h": 0.0, "3h": 0.0, "6h": 0.0}
    assert item["level"] == "safe"


async def test_custom_property_type_is_preserved(client, db):
    _stub(
        db,
        props=[_property_row(type="custom", custom_type_name="工作室")],
        rainfall=[_rainfall_row(r1h=25.0)],
        wra=[_wra_row()],
    )

    item = (await client.get("/api/properties-with-risk")).json()[0]

    assert item["type"] == "custom"
    assert item["custom_type_name"] == "工作室"
    assert item["risk_action"] == "該地區可能有淹水風險，請留意天氣變化"


async def test_a_property_outside_every_district_reads_as_safe(client, db):
    """Characterisation of the same gap as ROADMAP P0-3, seen over HTTP.

    No district means no thresholds, and no thresholds means 'safe' - even
    with 300 mm of rain on the property.
    """
    _stub(
        db,
        props=[_property_row(town_name=None, county_name=None)],
        rainfall=[_rainfall_row(r1h=300.0, r3h=300.0, r6h=300.0)],
    )

    item = (await client.get("/api/properties-with-risk")).json()[0]

    assert item["level"] == "safe"
    assert item["risk_pct"] == 0.0
    assert item["rainfall"]["1h"] == 300.0
