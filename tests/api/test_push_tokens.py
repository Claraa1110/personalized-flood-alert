import pytest

import app.api.push_tokens as push_tokens_module
from tests.fakes import Row

VALID_TOKEN = "ExponentPushToken[xxxxxxxxxxxxxxxxxxxxxx]"


@pytest.fixture
def sent(monkeypatch):
    """Captures calls to ``send_push_notifications`` instead of hitting Expo."""
    calls: list[dict] = []

    async def fake_send(tokens, title, body, badge=None, sound="default"):
        calls.append(
            {
                "tokens": tokens,
                "title": title,
                "body": body,
                "badge": badge,
                "sound": sound,
            }
        )

    monkeypatch.setattr(push_tokens_module, "send_push_notifications", fake_send)
    return calls


# ── POST /api/register-push-token ───────────────────────────────────────────


async def test_registers_a_valid_token(client, db):
    resp = await client.post("/api/register-push-token", json={"push_token": VALID_TOKEN})

    assert resp.status_code == 200
    assert db.commits == 1
    params = db.params_for("INSERT INTO push_tokens")[0]
    assert params["token"] == VALID_TOKEN


async def test_trims_whitespace_around_the_token(client, db):
    await client.post("/api/register-push-token", json={"push_token": f"  {VALID_TOKEN}  "})

    assert db.params_for("INSERT INTO push_tokens")[0]["token"] == VALID_TOKEN


@pytest.mark.parametrize(
    "token",
    [
        "",
        "fcm-raw-token",
        "ExpoPushToken[abc]",  # the older Expo prefix
        "exponentpushtoken[abc]",  # wrong case
        "prefix-ExponentPushToken[abc]",
    ],
)
async def test_rejects_a_token_that_is_not_an_expo_token(client, db, token):
    resp = await client.post("/api/register-push-token", json={"push_token": token})

    assert resp.status_code == 400
    assert db.sql_matching("INSERT INTO push_tokens") == []


async def test_registration_is_idempotent_per_device_and_token(client, db):
    await client.post("/api/register-push-token", json={"push_token": VALID_TOKEN})

    sql = db.sql_matching("INSERT INTO push_tokens")[0]
    assert "ON CONFLICT (device_id, push_token)" in sql
    assert "DO UPDATE SET updated_at" in sql


async def test_rejects_a_body_without_a_token(client):
    assert (await client.post("/api/register-push-token", json={})).status_code == 422


# ── POST /api/test-push ─────────────────────────────────────────────────────


async def test_test_push_404s_when_the_device_has_no_token(client, db, sent):
    resp = await client.post("/api/test-push")

    assert resp.status_code == 404
    assert sent == []


async def test_test_push_sends_to_every_registered_token(client, db, sent):
    db.when("SELECT push_token FROM push_tokens", rows=[Row(push_token=VALID_TOKEN)])

    resp = await client.post("/api/test-push")

    assert resp.status_code == 200
    assert len(sent) == 1
    assert sent[0]["tokens"] == [VALID_TOKEN]
    assert sent[0]["sound"] == "default"


async def test_test_push_is_suppressed_when_notifications_are_off(client, db, sent):
    db.when("SELECT push_token FROM push_tokens", rows=[Row(push_token=VALID_TOKEN)])
    db.when(
        "user_notification_settings",
        rows=[Row(notify_enabled=False, sound_enabled=True)],
    )

    body = (await client.post("/api/test-push")).json()

    assert sent == []
    assert body["sound"] is None


async def test_test_push_is_silent_when_sound_is_off(client, db, sent):
    db.when("SELECT push_token FROM push_tokens", rows=[Row(push_token=VALID_TOKEN)])
    db.when(
        "user_notification_settings",
        rows=[Row(notify_enabled=True, sound_enabled=False)],
    )

    body = (await client.post("/api/test-push")).json()

    assert sent[0]["sound"] is None
    assert body["sound"] is None
