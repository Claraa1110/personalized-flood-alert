from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.services.cwa_service import get_qpe_rainfall

router = APIRouter()


@router.get("/rainfall")
async def get_rainfall(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    db: AsyncSession = Depends(get_db),
):
    """給定座標，回傳即時雨量"""
    qpe_result = await get_qpe_rainfall(lat, lng)

    station_result = await db.execute(
        text("""
            SELECT
                station_name,
                rainfall_mm,
                rainfall_1hr,
                rainfall_3hr,
                rainfall_24hr,
                observed_at,
                ST_Distance(location, ST_MakePoint(:lng, :lat)::geography) AS dist_m
            FROM rainfall_observations
            WHERE ST_DWithin(location, ST_MakePoint(:lng, :lat)::geography, 50000)
            ORDER BY observed_at DESC, dist_m
            LIMIT 1
        """),
        {"lat": lat, "lng": lng},
    )
    station = station_result.fetchone()

    if not station:
        raise HTTPException(status_code=404, detail="附近找不到雨量資料")

    # Fetch hourly series for the nearest station (past 7 h, one row per hour)
    hourly_result = await db.execute(
        text("""
            WITH ranked AS (
                SELECT
                    COALESCE(rainfall_1hr, rainfall_mm)::float AS mm,
                    observed_at,
                    DATE_TRUNC('hour', observed_at) AS bucket,
                    ROW_NUMBER() OVER (
                        PARTITION BY DATE_TRUNC('hour', observed_at)
                        ORDER BY observed_at DESC
                    ) AS rn
                FROM rainfall_observations
                WHERE station_name = :station_name
                  AND observed_at >= NOW() - INTERVAL '7 hours'
            )
            SELECT mm, observed_at
            FROM ranked
            WHERE rn = 1
            ORDER BY observed_at ASC
        """),
        {"station_name": station.station_name},
    )
    hourly_rows = hourly_result.fetchall()
    hourly_series = [
        {
            "mm": float(row.mm or 0),
            "observed_at": row.observed_at.isoformat(),
        }
        for row in hourly_rows
        if row.observed_at is not None
    ]

    return {
        "latitude": lat,
        "longitude": lng,
        "rainfall_now_mm": qpe_result.get("rainfall_mm", station.rainfall_mm),
        "rainfall_1hr_mm": station.rainfall_1hr,
        "rainfall_3hr_mm": station.rainfall_3hr,
        "rainfall_24hr_mm": station.rainfall_24hr,
        "nearest_station": station.station_name,
        "station_distance_km": round(station.dist_m / 1000, 2),
        "observed_at": station.observed_at.isoformat() if station.observed_at else None,
        "source": qpe_result.get("source", "station"),
        "hourly_series": hourly_series,
    }


@router.get("/rainfall/history")
async def get_rainfall_history(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    hours: int = Query(default=24, ge=1, le=72),
    db: AsyncSession = Depends(get_db),
):
    """給定座標，回傳過去 N 小時的雨量時序資料"""
    since = datetime.now() - timedelta(hours=hours)

    result = await db.execute(
        text("""
            SELECT
                station_name,
                rainfall_mm,
                observed_at,
                ST_Distance(location, ST_MakePoint(:lng, :lat)::geography) AS dist_m
            FROM rainfall_observations
            WHERE ST_DWithin(location, ST_MakePoint(:lng, :lat)::geography, 50000)
            AND observed_at >= :since
            ORDER BY observed_at DESC
            LIMIT 100
        """),
        {"lat": lat, "lng": lng, "since": since},
    )
    rows = result.fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail="附近找不到歷史雨量資料")

    return {
        "latitude": lat,
        "longitude": lng,
        "nearest_station": rows[0].station_name,
        "hours": hours,
        "data": [
            {
                "rainfall_mm": row.rainfall_mm,
                "observed_at": row.observed_at.isoformat() if row.observed_at else None,
            }
            for row in rows
        ],
    }
