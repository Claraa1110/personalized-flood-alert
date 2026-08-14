import pytest
from fastapi import HTTPException

from app.auth import get_device_id


async def test_returns_the_header_value():
    assert await get_device_id("device-abc") == "device-abc"


async def test_strips_surrounding_whitespace():
    assert await get_device_id("  device-abc \n") == "device-abc"


@pytest.mark.parametrize("value", [None, "", "   ", "\t\n"])
async def test_rejects_missing_or_blank_header(value):
    with pytest.raises(HTTPException) as exc:
        await get_device_id(value)
    assert exc.value.status_code == 400
    assert "X-Device-Id" in exc.value.detail


async def test_accepts_any_string_without_verification():
    """Characterises today's trust model, which is *not* authentication.

    Any caller may claim any device id and thereby read and mutate that
    device's properties and alerts. Tracked as ROADMAP P0-1.
    """
    assert await get_device_id("../../etc/passwd") == "../../etc/passwd"
    assert await get_device_id("not-even-a-uuid") == "not-even-a-uuid"
