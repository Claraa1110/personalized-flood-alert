import pytest

from tests.fakes import Row

TAIPEI = {"lat": 25.0330, "lng": 121.5654}


# ── GET /api/location/district ──────────────────────────────────────────────


async def test_returns_the_containing_district(anon_client, db):
    db.when(
        "town_eng",
        rows=[
            Row(
                town_id="63000050",
                town_name="信義區",
                town_eng="Xinyi Dist.",
                county_id="63000",
                county_name="臺北市",
            )
        ],
    )

    resp = await anon_client.get("/api/location/district", params=TAIPEI)

    assert resp.status_code == 200
    assert resp.json() == {
        "town_id": "63000050",
        "town_name": "信義區",
        "town_eng": "Xinyi Dist.",
        "county_id": "63000",
        "county_name": "臺北市",
    }


async def test_404s_when_the_point_is_outside_every_district(anon_client, db):
    resp = await anon_client.get("/api/location/district", params=TAIPEI)

    assert resp.status_code == 404
    assert resp.json()["detail"] == "查無對應行政區"


async def test_district_tolerates_a_missing_english_name(anon_client, db):
    db.when(
        "town_eng",
        rows=[
            Row(
                town_id="1",
                town_name="信義區",
                town_eng=None,
                county_id="63000",
                county_name="臺北市",
            )
        ],
    )

    assert (await anon_client.get("/api/location/district", params=TAIPEI)).json()[
        "town_eng"
    ] is None


@pytest.mark.parametrize(
    "params",
    [
        {"lat": 91, "lng": 121},
        {"lat": -91, "lng": 121},
        {"lat": 25, "lng": 181},
        {"lat": 25, "lng": -181},
        {"lat": "north", "lng": 121},
        {"lng": 121},
        {"lat": 25},
    ],
)
async def test_rejects_out_of_range_or_missing_coordinates(anon_client, params):
    resp = await anon_client.get("/api/location/district", params=params)
    assert resp.status_code == 422


# ── GET /api/location/flood-risk ────────────────────────────────────────────


async def test_returns_the_flood_potential_level(anon_client, db):
    db.when("flood_risk_zones", rows=[Row(risk_level=4)])

    body = (await anon_client.get("/api/location/flood-risk", params=TAIPEI)).json()

    assert body["risk_level"] == 4
    assert body["scenario"] == "24h_200mm"
    assert body["description"] == "高風險"


async def test_a_point_in_no_flood_zone_is_level_zero_not_a_404(anon_client, db):
    body = (await anon_client.get("/api/location/flood-risk", params=TAIPEI)).json()

    assert body["risk_level"] == 0
    assert body["description"] == "無資料或風險極低"


async def test_scenario_is_selectable(anon_client, db):
    db.when("flood_risk_zones", rows=[Row(risk_level=2)])

    body = (
        await anon_client.get(
            "/api/location/flood-risk", params={**TAIPEI, "scenario": "24h_350mm"}
        )
    ).json()

    assert body["scenario"] == "24h_350mm"
    assert db.params_for("flood_risk_zones")[0]["scenario"] == "24h_350mm"


async def test_scenario_whitespace_is_trimmed(anon_client, db):
    await anon_client.get(
        "/api/location/flood-risk", params={**TAIPEI, "scenario": "  24h_200mm  "}
    )

    assert db.params_for("flood_risk_zones")[0]["scenario"] == "24h_200mm"


async def test_an_unmapped_risk_level_falls_back_to_unknown(anon_client, db):
    db.when("flood_risk_zones", rows=[Row(risk_level=99)])

    body = (await anon_client.get("/api/location/flood-risk", params=TAIPEI)).json()

    assert body["description"] == "未知"
