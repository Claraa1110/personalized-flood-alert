"""Shared pytest fixtures.

Environment variables are set *before* any ``app.*`` module is imported,
because ``app/database.py`` builds the async engine at import time and
``app/services/*`` read API keys at import time. See docs/ROADMAP.md P1-3
(move configuration into a validated Settings object) for the real fix.
"""

import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test_flood_alert")
os.environ.setdefault("CWA_API_KEY", "test-cwa-key")
os.environ.setdefault("OPENROUTER_API_KEY", "test-openrouter-key")
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("ENVIRONMENT", "test")

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.dependencies import get_db  # noqa: E402
from app.main import app as fastapi_app  # noqa: E402
from tests.fakes import FakeSession  # noqa: E402

DEVICE_ID = "11111111-2222-3333-4444-555555555555"


@pytest.fixture
def db() -> FakeSession:
    """An in-memory stand-in for ``AsyncSession``.

    Stub queries with ``db.when("FROM alerts", rows=[...])``; anything not
    stubbed returns an empty result set.
    """
    return FakeSession()


@pytest.fixture
async def client(db: FakeSession):
    """HTTP client bound to the ASGI app with the DB dependency faked out.

    Uses ``ASGITransport`` rather than ``TestClient`` on purpose: it does not
    run lifespan events, so the APScheduler jobs and the startup CWA fetch
    never fire during tests.
    """
    fastapi_app.dependency_overrides[get_db] = lambda: db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=fastapi_app),
            base_url="http://test",
            headers={"X-Device-Id": DEVICE_ID},
        ) as ac:
            yield ac
    finally:
        fastapi_app.dependency_overrides.clear()


@pytest.fixture
async def anon_client(db: FakeSession):
    """Same as ``client`` but sends no ``X-Device-Id`` header."""
    fastapi_app.dependency_overrides[get_db] = lambda: db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=fastapi_app), base_url="http://test"
        ) as ac:
            yield ac
    finally:
        fastapi_app.dependency_overrides.clear()
