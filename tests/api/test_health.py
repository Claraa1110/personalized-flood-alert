from datetime import datetime, timedelta

import app.services.cwa_service as cwa_service


async def test_health_reports_ok(anon_client):
    resp = await anon_client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_health_needs_no_device_header(anon_client):
    assert (await anon_client.get("/health")).status_code == 200


async def test_scheduler_health_reports_no_data_before_the_first_fetch(anon_client, monkeypatch):
    monkeypatch.setattr(cwa_service, "last_rainfall_update", None)

    body = (await anon_client.get("/health/scheduler")).json()

    assert body == {"status": "no_data", "minutes_since_last_update": None}


async def test_scheduler_health_reports_freshness_after_a_fetch(anon_client, monkeypatch):
    monkeypatch.setattr(cwa_service, "last_rainfall_update", datetime.now() - timedelta(minutes=7))

    body = (await anon_client.get("/health/scheduler")).json()

    assert body["status"] == "ok"
    assert body["minutes_since_last_update"] == 7.0


async def test_scheduler_health_reports_ok_even_when_badly_stale(anon_client, monkeypatch):
    """Characterisation of a monitoring gap.

    The rainfall job runs every 10 minutes. A last update from 12 hours ago
    means alerting has been blind for 12 hours, yet the endpoint still says
    "ok", so an uptime check watching this route stays green. There is no
    staleness threshold. Tracked as ROADMAP P0-5.
    """
    monkeypatch.setattr(cwa_service, "last_rainfall_update", datetime.now() - timedelta(hours=12))

    body = (await anon_client.get("/health/scheduler")).json()

    assert body["status"] == "ok"
    assert body["minutes_since_last_update"] == 720.0
