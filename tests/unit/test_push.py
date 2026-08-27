"""Tests for Expo push delivery.

Push failures must never break alert persistence, so these tests pin the
"swallow everything" contract as much as the happy path.
"""

import pytest

import app.push as push_module
from app.push import send_push_notifications

VALID = "ExponentPushToken[xxxxxxxxxxxxxxxxxxxxxx]"
OTHER = "ExponentPushToken[yyyyyyyyyyyyyyyyyyyyyy]"


class FakeResponse:
    def __init__(self, status_code=200, text="{}"):
        self.status_code = status_code
        self.text = text


class FakeClient:
    """Records the single POST the module makes, or raises on demand."""

    def __init__(self, response=None, raises=None):
        self.response = response or FakeResponse()
        self.raises = raises
        self.calls: list[dict] = []

    def __call__(self, *args, **kwargs):
        self.init_kwargs = kwargs
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False

    async def post(self, url, json=None, headers=None):
        self.calls.append({"url": url, "json": json, "headers": headers})
        if self.raises:
            raise self.raises
        return self.response


@pytest.fixture
def fake_client(monkeypatch):
    client = FakeClient()
    monkeypatch.setattr(push_module.httpx, "AsyncClient", client)
    return client


async def test_sends_one_message_per_token(fake_client):
    await send_push_notifications([VALID, OTHER], "標題", "內容")

    assert len(fake_client.calls) == 1
    messages = fake_client.calls[0]["json"]
    assert [m["to"] for m in messages] == [VALID, OTHER]
    assert all(m["title"] == "標題" and m["body"] == "內容" for m in messages)


async def test_posts_to_the_expo_endpoint(fake_client):
    await send_push_notifications([VALID], "t", "b")
    assert fake_client.calls[0]["url"] == "https://exp.host/--/api/v2/push/send"


async def test_targets_the_flood_alerts_android_channel(fake_client):
    await send_push_notifications([VALID], "t", "b")
    assert fake_client.calls[0]["json"][0]["channelId"] == "flood-alerts"


async def test_drops_tokens_that_are_not_expo_tokens(fake_client):
    await send_push_notifications([VALID, "fcm-raw-token", "", "null"], "t", "b")
    assert [m["to"] for m in fake_client.calls[0]["json"]] == [VALID]


@pytest.mark.parametrize("tokens", [[], ["garbage"], ["", "ExpoPushToken[abc]"]])
async def test_skips_the_network_call_entirely_when_no_token_is_valid(fake_client, tokens):
    await send_push_notifications(tokens, "t", "b")
    assert fake_client.calls == []


async def test_badge_is_omitted_when_not_supplied(fake_client):
    await send_push_notifications([VALID], "t", "b")
    assert "badge" not in fake_client.calls[0]["json"][0]


async def test_badge_is_included_when_supplied(fake_client):
    await send_push_notifications([VALID], "t", "b", badge=3)
    assert fake_client.calls[0]["json"][0]["badge"] == 3


async def test_badge_zero_is_sent_and_not_treated_as_absent(fake_client):
    # badge=0 is how a client clears the app icon count.
    await send_push_notifications([VALID], "t", "b", badge=0)
    assert fake_client.calls[0]["json"][0]["badge"] == 0


async def test_sound_defaults_to_default_and_can_be_silenced(fake_client):
    await send_push_notifications([VALID], "t", "b")
    assert fake_client.calls[0]["json"][0]["sound"] == "default"

    fake_client.calls.clear()
    await send_push_notifications([VALID], "t", "b", sound=None)
    assert fake_client.calls[0]["json"][0]["sound"] is None


async def test_a_transport_error_never_propagates(monkeypatch):
    client = FakeClient(raises=OSError("connection reset"))
    monkeypatch.setattr(push_module.httpx, "AsyncClient", client)

    await send_push_notifications([VALID], "t", "b")  # must not raise


async def test_a_non_200_response_never_propagates(monkeypatch):
    client = FakeClient(response=FakeResponse(status_code=502, text="bad gateway"))
    monkeypatch.setattr(push_module.httpx, "AsyncClient", client)

    await send_push_notifications([VALID], "t", "b")  # must not raise


async def test_per_token_expo_receipts_are_not_inspected(fake_client):
    """Characterisation: a 200 with per-message errors is treated as success.

    Expo returns 200 with ``{"data": [{"status": "error",
    "details": {"error": "DeviceNotRegistered"}}]}`` for dead tokens. Nothing
    parses that, so dead tokens are never pruned and delivery failures are
    invisible. Tracked as ROADMAP P2-2.
    """
    fake_client.response = FakeResponse(
        status_code=200,
        text='{"data":[{"status":"error","details":{"error":"DeviceNotRegistered"}}]}',
    )
    await send_push_notifications([VALID], "t", "b")
    # No exception, no retry, no bookkeeping - exactly one fire-and-forget POST.
    assert len(fake_client.calls) == 1
