import os
import math
from contextlib import asynccontextmanager
from datetime import datetime

import httpx
from fastapi import FastAPI, Query, HTTPException
from dotenv import load_dotenv
from app.api.test import router as test_router
from app.api.properties import router as properties_router
from app.api.location import router as location_router
from app.api.rainfall import router as rainfall_router
from app.api.alerts import router as alerts_router
from app.scheduler import setup_scheduler
from app.services.cwa_service import fetch_rainfall_stations

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = setup_scheduler()
    scheduler.start()
    print("排程系統啟動")

    try:
        await fetch_rainfall_stations()
        print("初始雨量資料載入完成")
    except Exception as e:
        print(f"初始載入失敗（不影響服務）：{e}")

    yield

    scheduler.shutdown()
    print("排程系統關閉")


app = FastAPI(title="淹水預警系統 API", lifespan=lifespan)
app.include_router(test_router, prefix="/api")
app.include_router(properties_router, prefix="/api")
app.include_router(location_router, prefix="/api")
app.include_router(rainfall_router, prefix="/api")
app.include_router(alerts_router, prefix="/api")


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.asin(math.sqrt(a))


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/scheduler")
def scheduler_health():
    from app.services.cwa_service import last_rainfall_update

    if last_rainfall_update is None:
        return {"status": "no_data", "minutes_since_last_update": None}
    minutes = (datetime.now() - last_rainfall_update).total_seconds() / 60
    return {"status": "ok", "minutes_since_last_update": round(minutes, 1)}


@app.get("/api/test-rainfall")
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
