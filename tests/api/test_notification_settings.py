from tests.fakes import Row


async def test_defaults_to_everything_on_for_a_new_device(client, db):
    resp = await client.get("/api/notification-settings")

    assert resp.status_code == 200
    assert resp.json() == {"notify_enabled": True, "sound_enabled": True}


async def test_returns_stored_settings(client, db):
    db.when(
        "user_notification_settings",
        rows=[Row(notify_enabled=False, sound_enabled=True)],
    )

    body = (await client.get("/api/notification-settings")).json()

    assert body == {"notify_enabled": False, "sound_enabled": True}


async def test_update_persists_and_echoes_the_new_settings(client, db):
    resp = await client.put(
        "/api/notification-settings",
        json={"notify_enabled": False, "sound_enabled": False},
    )

    assert resp.status_code == 200
    assert resp.json() == {"notify_enabled": False, "sound_enabled": False}
    assert db.commits == 1

    sql = db.sql_matching("INSERT INTO user_notification_settings")[0]
    assert "ON CONFLICT (device_id)" in sql  # upsert, not duplicate rows


async def test_update_is_an_upsert_keyed_on_the_device(client, db):
    await client.put(
        "/api/notification-settings",
        json={"notify_enabled": True, "sound_enabled": False},
    )

    params = db.params_for("INSERT INTO user_notification_settings")[0]
    assert params["notify"] is True
    assert params["sound"] is False
    assert params["device_id"]


async def test_update_rejects_a_missing_field(client):
    resp = await client.put("/api/notification-settings", json={"notify_enabled": True})
    assert resp.status_code == 422


async def test_update_rejects_a_non_boolean(client):
    resp = await client.put(
        "/api/notification-settings",
        json={"notify_enabled": "maybe", "sound_enabled": True},
    )
    assert resp.status_code == 422
