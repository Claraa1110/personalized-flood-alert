import os

import httpx
from fastapi import APIRouter, Query, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.sql.expression import cast
from geoalchemy2 import Geography
from geoalchemy2.functions import ST_DWithin, ST_Distance, ST_MakePoint
from app.dependencies import get_db
from app.models.property import Property
from app.utils import haversine

router = APIRouter()


@router.get("/test-postgis")
async def test_postgis(
    lat: float = Query(...),
    lng: float = Query(...),
    radius: float = Query(5000),
    db: AsyncSession = Depends(get_db),
):
    center = cast(ST_MakePoint(lng, lat), Geography(srid=4326))

    result = await db.execute(
        select(
            Property.name,
            ST_Distance(Property.location, center).label("dist_m"),
        )
        .where(ST_DWithin(Property.location, center, radius))
        .order_by("dist_m")
    )
    rows = result.all()

    return {
        "center": {"lat": lat, "lng": lng},
        "radius_m": radius,
        "results": [{"name": r.name, "dist_m": round(r.dist_m, 1)} for r in rows],
    }


@router.get("/test-integrated")
async def test_integrated(
    lat: float = Query(...),
    lng: float = Query(...),
    db: AsyncSession = Depends(get_db),
):
    center = cast(ST_MakePoint(lng, lat), Geography(srid=4326))

    result = await db.execute(
        select(
            Property.name,
            ST_Distance(Property.location, center).label("dist_m"),
        )
        .where(ST_DWithin(Property.location, center, 5000))
        .order_by("dist_m")
    )
    rows = result.all()

    return {
        "message": "整合測試成功",
        "center": {"lat": lat, "lng": lng},
        "nearby_properties": [
            {"name": r.name, "dist_m": round(r.dist_m, 1)} for r in rows
        ],
        "total": len(rows),
    }


@router.get("/test-rainfall")
async def test_rainfall(lat: float = Query(...), lng: float = Query(...)):
    api_key = os.getenv("CWA_API_KEY")
    url = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/O-A0002-001"

    async with httpx.AsyncClient(timeout=10, verify=False) as client:
        resp = await client.get(
            url, params={"Authorization": api_key, "format": "JSON"}
        )
        resp.raise_for_status()
        data = resp.json()

    stations = data.get("records", {}).get("Station", [])
    if not stations:
        raise HTTPException(status_code=404, detail="No stations found")

    nearest = None
    min_dist = float("inf")

    for s in stations:
        try:
            coords = s["GeoInfo"]["Coordinates"]
            wgs84 = next(c for c in coords if c["CoordinateName"] == "WGS84")
            slat = float(wgs84["StationLatitude"])
            slng = float(wgs84["StationLongitude"])
        except (KeyError, StopIteration, ValueError):
            continue

        dist = haversine(lat, lng, slat, slng)
        if dist < min_dist:
            min_dist = dist
            nearest = s

    if not nearest:
        raise HTTPException(status_code=404, detail="No valid stations found")

    rainfall = nearest["RainfallElement"]["Now"]["Precipitation"]
    observed_at = nearest["ObsTime"]["DateTime"]

    return {
        "station_name": nearest["StationName"],
        "distance_km": round(min_dist, 2),
        "rainfall_mm": float(rainfall) if rainfall != -99 else 0.0,
        "observed_at": observed_at,
    }
