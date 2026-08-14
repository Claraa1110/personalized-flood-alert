"""Every device-scoped route must demand ``X-Device-Id`` and filter on it."""

import pytest

from tests.conftest import DEVICE_ID

DEVICE_SCOPED_GET_ROUTES = [
    "/api/me",
    "/api/alerts",
    "/api/properties",
    "/api/properties-with-risk",
    "/api/notification-settings",
]


@pytest.mark.parametrize("route", DEVICE_SCOPED_GET_ROUTES)
async def test_rejects_a_request_with_no_device_header(anon_client, route):
    resp = await anon_client.get(route)
    assert resp.status_code == 400
    assert "X-Device-Id" in resp.json()["detail"]


@pytest.mark.parametrize("route", DEVICE_SCOPED_GET_ROUTES)
async def test_rejects_a_blank_device_header(anon_client, route):
    resp = await anon_client.get(route, headers={"X-Device-Id": "   "})
    assert resp.status_code == 400


async def test_me_echoes_the_calling_device(client):
    resp = await client.get("/api/me")
    assert resp.status_code == 200
    assert resp.json() == {"device_id": DEVICE_ID}


async def test_alert_list_is_filtered_by_device_id(client, db):
    await client.get("/api/alerts")

    params = db.params_for("FROM alerts a")[0]
    assert params == {"device_id": DEVICE_ID}


async def test_notification_settings_are_filtered_by_device_id(client, db):
    await client.get("/api/notification-settings")

    params = db.params_for("user_notification_settings")[0]
    assert params == {"device_id": DEVICE_ID}


async def test_properties_with_risk_is_filtered_by_device_id(client, db):
    await client.get("/api/properties-with-risk")

    for params in db.params_for("p.device_id = :device_id"):
        assert params["device_id"] == DEVICE_ID


async def test_any_caller_may_impersonate_any_device(client, db):
    """Characterisation of the current trust model.

    ``X-Device-Id`` is an unverified, client-supplied identifier. A caller who
    learns another user's device id gets full read/write access to that user's
    properties and alerts, and the value is never checked for shape either.
    Tracked as ROADMAP P0-1.
    """
    resp = await client.get("/api/alerts", headers={"X-Device-Id": "someone-elses-id"})

    assert resp.status_code == 200
    assert db.params_for("FROM alerts a")[0] == {"device_id": "someone-elses-id"}
