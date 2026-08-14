"""Route table and OpenAPI contract.

Guards against a router being dropped from ``main.py`` during a refactor, and
records which debug surfaces are currently reachable in production.

Routes are read from the generated OpenAPI schema rather than by walking
``app.routes``: recent FastAPI keeps included routers as opaque container
objects, so a flat iteration over ``app.routes`` sees only the four built-in
docs endpoints.
"""

import pytest

from app.main import app

# Routes the README documents as the public API.
DOCUMENTED_ROUTES = [
    ("GET", "/health"),
    ("GET", "/health/scheduler"),
    ("POST", "/api/properties"),
    ("GET", "/api/properties"),
    ("GET", "/api/properties/{property_id}"),
    ("PUT", "/api/properties/{property_id}"),
    ("DELETE", "/api/properties/{property_id}"),
    ("GET", "/api/properties-with-risk"),
    ("GET", "/api/location/district"),
    ("GET", "/api/location/flood-risk"),
    ("GET", "/api/rainfall"),
    ("GET", "/api/forecast"),
    ("GET", "/api/geocode"),
    ("GET", "/api/alerts"),
    ("GET", "/api/alerts/{alert_id}"),
    ("POST", "/api/alerts/evaluate"),
    ("GET", "/api/threshold"),
    ("GET", "/api/corrected-thresholds"),
    ("POST", "/api/register-push-token"),
    ("GET", "/api/notification-settings"),
    ("PUT", "/api/notification-settings"),
    ("GET", "/privacy"),
]

# Shipped but absent from the README.
UNDOCUMENTED_ROUTES = [
    ("GET", "/api/me"),
    ("POST", "/api/alerts/mark-all-read"),
    ("GET", "/api/rainfall/history"),
    ("GET", "/api/reverse-geocode"),
    ("GET", "/reset-password"),
]

# Debug and seeding surfaces - see ROADMAP P0-6.
DEBUG_ROUTES = [
    ("GET", "/api/test-postgis"),
    ("GET", "/api/test-integrated"),
    ("GET", "/api/test-rainfall"),
    ("POST", "/api/test-push"),
    ("POST", "/api/alerts/seed-test"),
    ("DELETE", "/api/alerts/seed-test"),
]


def _routes() -> set[tuple[str, str]]:
    paths = app.openapi()["paths"]
    return {(method.upper(), path) for path, operations in paths.items() for method in operations}


@pytest.mark.parametrize("method, path", DOCUMENTED_ROUTES)
def test_every_documented_route_is_registered(method, path):
    assert (method, path) in _routes()


def test_the_route_table_holds_no_surprises():
    """Full inventory. Adding or removing a route must be a deliberate edit.

    This is the guard that makes ROADMAP P0-6 actionable: when the debug
    routes are deleted, this test fails until DEBUG_ROUTES is emptied too.
    """
    expected = set(DOCUMENTED_ROUTES + UNDOCUMENTED_ROUTES + DEBUG_ROUTES)
    assert _routes() == expected


def test_openapi_schema_builds():
    schema = app.openapi()
    assert schema["info"]["title"] == "淹水預警系統 API"
    assert schema["paths"]


def test_api_routes_are_unversioned():
    """Characterisation: no ``/v1`` prefix, so no route can change shape safely.

    Every published mobile build is pinned to today's response bodies.
    Tracked as ROADMAP P2-6.
    """
    api_paths = {path for _, path in _routes() if path.startswith("/api")}
    assert api_paths
    assert not any(path.startswith("/api/v") for path in api_paths)


@pytest.mark.parametrize("method, path", DEBUG_ROUTES)
def test_debug_routes_are_currently_reachable(method, path):
    """Characterisation, not an endorsement.

    These routes ship to production unauthenticated or behind nothing but a
    self-asserted device id. ``/api/alerts/seed-test`` writes fabricated
    warning records into a user's alert history, and ``/api/test-postgis``
    returns other devices' property names without any device filter.
    Tracked as ROADMAP P0-6.
    """
    assert (method, path) in _routes()


async def test_risk_evaluation_can_be_triggered_by_anyone(anon_client, monkeypatch):
    """``POST /api/alerts/evaluate`` takes no device id and no credential.

    It walks every property in the database and fans out push notifications,
    so any anonymous caller can force a full evaluation cycle - repeatedly.
    Tracked as ROADMAP P0-6.
    """
    import app.services.risk_engine as risk_engine

    called: list[bool] = []

    async def fake_evaluate():
        called.append(True)

    # The route imports the function at call time, so patching the module
    # attribute is enough.
    monkeypatch.setattr(risk_engine, "evaluate_all_properties", fake_evaluate)

    resp = await anon_client.post("/api/alerts/evaluate")

    assert resp.status_code == 200
    assert called == [True]
