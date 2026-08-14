from datetime import datetime
from uuid import UUID, uuid4

from tests.fakes import Row

ALERT_ID = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
PROPERTY_ID = uuid4()
CREATED_AT = datetime(2026, 8, 14, 3, 30, 0)
READ_AT = datetime(2026, 8, 14, 4, 0, 0)


def _alert_row(**overrides) -> Row:
    fields = {
        "id": ALERT_ID,
        "property_id": PROPERTY_ID,
        "level": "level1",
        "message": "【家】達一級警戒 3H 雨量 68.5mm（已達警戒值 45.0mm）",
        "created_at": CREATED_AT,
        "read_at": None,
        "property_name": "家",
        "property_address": "臺北市信義區",
    }
    fields.update(overrides)
    return Row(**fields)


# ── GET /api/alerts ─────────────────────────────────────────────────────────


async def test_empty_alert_list(client, db):
    resp = await client.get("/api/alerts")

    assert resp.status_code == 200
    assert resp.json() == {"total": 0, "alerts": []}


async def test_serialises_an_alert(client, db):
    db.when("FROM alerts a", rows=[_alert_row()])

    body = (await client.get("/api/alerts")).json()

    assert body["total"] == 1
    alert = body["alerts"][0]
    assert alert["id"] == str(ALERT_ID)
    assert alert["property_id"] == str(PROPERTY_ID)
    assert alert["level"] == "level1"
    assert alert["property_name"] == "家"
    assert alert["created_at"] == CREATED_AT.isoformat()


async def test_unread_alerts_are_flagged(client, db):
    db.when("FROM alerts a", rows=[_alert_row(read_at=None)])

    alert = (await client.get("/api/alerts")).json()["alerts"][0]

    assert alert["is_read"] is False
    assert alert["read_at"] is None


async def test_read_alerts_are_flagged(client, db):
    db.when("FROM alerts a", rows=[_alert_row(read_at=READ_AT)])

    alert = (await client.get("/api/alerts")).json()["alerts"][0]

    assert alert["is_read"] is True
    assert alert["read_at"] == READ_AT.isoformat()


async def test_total_counts_the_returned_page_not_the_whole_history(client, db):
    """The list is capped at 50 rows and ``total`` is just ``len(rows)``.

    A device with more than 50 alerts sees ``total == 50`` and has no way to
    page further back. Tracked as ROADMAP P2-5.
    """
    db.when("FROM alerts a", rows=[_alert_row() for _ in range(50)])

    body = (await client.get("/api/alerts")).json()

    assert body["total"] == 50
    assert "LIMIT 50" in db.sql_matching("FROM alerts a")[0]


# ── GET /api/alerts/{id} ────────────────────────────────────────────────────


async def test_alert_detail_returns_404_for_another_devices_alert(client, db):
    db.when("a.triggered_by", rows=[])

    resp = await client.get(f"/api/alerts/{ALERT_ID}")

    assert resp.status_code == 404


async def test_alert_detail_returns_the_trigger_payload(client, db):
    triggered_by = {"scale": "3H", "actual_mm": 68.5, "threshold_mm": 45.0}
    db.when("a.triggered_by", rows=[_alert_row(triggered_by=triggered_by)])

    body = (await client.get(f"/api/alerts/{ALERT_ID}")).json()

    assert body["triggered_by"] == triggered_by
    assert body["level"] == "level1"


async def test_reading_an_alert_marks_it_read(client, db):
    db.when("a.triggered_by", rows=[_alert_row(triggered_by={})])

    await client.get(f"/api/alerts/{ALERT_ID}")

    updates = db.sql_matching("UPDATE alerts SET read_at")
    assert len(updates) == 1
    assert "read_at IS NULL" in updates[0]
    assert db.commits == 1


async def test_a_404_does_not_mark_anything_read(client, db):
    db.when("a.triggered_by", rows=[])

    await client.get(f"/api/alerts/{ALERT_ID}")

    assert db.sql_matching("UPDATE alerts SET read_at") == []
    assert db.commits == 0


async def test_alert_detail_rejects_a_malformed_id(client):
    assert (await client.get("/api/alerts/not-a-uuid")).status_code == 422


# ── POST /api/alerts/mark-all-read ──────────────────────────────────────────


async def test_mark_all_read_is_scoped_to_the_calling_device(client, db):
    resp = await client.post("/api/alerts/mark-all-read")

    assert resp.status_code == 200
    sql = db.sql_matching("UPDATE alerts SET read_at")[0]
    assert "WHERE device_id = :device_id" in sql
    assert db.commits == 1
