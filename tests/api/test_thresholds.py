from tests.fakes import Row

TAIPEI = {"lat": 25.0330, "lng": 121.5654}


def _stub_thresholds(db, *, district=True, rainfall=None, corrected=()):
    db.when(
        "FROM districts WHERE ST_Within",
        rows=[Row(town_name="信義區", county_name="臺北市")] if district else [],
    )
    db.when(
        "FROM wra_alert_thresholds",
        rows=[
            Row(
                lv1_1h=40.0,
                lv1_3h=80.0,
                lv1_6h=120.0,
                lv2_1h=20.0,
                lv2_3h=40.0,
                lv2_6h=60.0,
            )
        ]
        if district
        else [],
    )
    db.when("FROM corrected_thresholds WHERE district_name", rows=corrected)
    db.when("FROM rainfall_observations", rows=[rainfall] if rainfall else [])


# ── GET /api/threshold ──────────────────────────────────────────────────────


async def test_reports_safe_when_it_is_not_raining(anon_client, db):
    _stub_thresholds(db)

    body = (await anon_client.get("/api/threshold", params=TAIPEI)).json()

    assert body["level"] == "safe"
    assert body["district_name"] == "信義區"
    assert body["level2_source"] == "original"
    assert body["current_rainfall"] == {"1h": 0.0, "3h": 0.0, "6h": 0.0}


async def test_reports_amber_and_red(anon_client, db):
    _stub_thresholds(db, rainfall=Row(rainfall_1hr=25.0, rainfall_3hr=0.0, rainfall_6hr=0.0))
    assert (await anon_client.get("/api/threshold", params=TAIPEI)).json()["level"] == "level2"


async def test_red_takes_precedence(anon_client, db):
    _stub_thresholds(db, rainfall=Row(rainfall_1hr=45.0, rainfall_3hr=90.0, rainfall_6hr=0.0))
    assert (await anon_client.get("/api/threshold", params=TAIPEI)).json()["level"] == "level1"


async def test_returns_both_tiers_so_the_client_can_render_a_gauge(anon_client, db):
    _stub_thresholds(db)

    body = (await anon_client.get("/api/threshold", params=TAIPEI)).json()

    assert body["thresholds"]["level1"] == {"1h": 40.0, "3h": 80.0, "6h": 120.0}
    assert body["thresholds"]["level2"] == {"1h": 20.0, "3h": 40.0, "6h": 60.0}


async def test_marks_the_level2_source_as_calibrated(anon_client, db):
    _stub_thresholds(
        db,
        corrected=[Row(corrected_1h=15.0, corrected_3h=30.0, corrected_6h=50.0)],
    )

    body = (await anon_client.get("/api/threshold", params=TAIPEI)).json()

    assert body["level2_source"] == "corrected"
    assert body["thresholds"]["level2"]["1h"] == 15.0


async def test_unknown_district_returns_200_with_an_error_body(anon_client, db):
    """Characterisation: the failure is reported as a 200 with an 'error' key.

    Clients cannot distinguish this from a successful response by status code,
    and the payload shape changes entirely. Tracked as ROADMAP P2-6.
    """
    _stub_thresholds(db, district=False)

    resp = await anon_client.get("/api/threshold", params=TAIPEI)

    assert resp.status_code == 200
    assert resp.json() == {"error": "找不到對應門檻"}


async def test_coordinates_are_not_range_validated(anon_client, db):
    """Characterisation: unlike the other geo routes this one takes any float.

    ``lat=999`` reaches PostGIS instead of being rejected with a 422.
    Tracked as ROADMAP P2-6.
    """
    _stub_thresholds(db, district=False)

    resp = await anon_client.get("/api/threshold", params={"lat": 999, "lng": 999})

    assert resp.status_code == 200


# ── GET /api/corrected-thresholds ───────────────────────────────────────────


async def test_lists_every_calibrated_district(anon_client, db):
    db.when(
        "FROM corrected_thresholds ORDER BY",
        rows=[
            Row(
                county_name="臺北市",
                district_name="信義區",
                original_1h=20.0,
                corrected_1h=15.0,
                original_3h=40.0,
                corrected_3h=30.0,
                original_6h=60.0,
                corrected_6h=50.0,
                event_count=4,
                adjustment_rate_1h=-0.25,
            )
        ],
    )

    body = (await anon_client.get("/api/corrected-thresholds")).json()

    assert body["total"] == 1
    row = body["thresholds"][0]
    assert row["district_name"] == "信義區"
    assert row["original_1h"] == 20.0
    assert row["corrected_1h"] == 15.0
    assert row["event_count"] == 4


async def test_empty_calibration_table(anon_client, db):
    body = (await anon_client.get("/api/corrected-thresholds")).json()
    assert body == {"total": 0, "thresholds": []}
