import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.dependencies import get_db
from app.services.city_forecast_map import CITY_FORECAST_MAP

router = APIRouter()

CWA_BASE_URL = "https://opendata.cwa.gov.tw/api/v1/rest/datastore"
TZ_8 = timezone(timedelta(hours=8))

# 縣市 → 完整 Location 陣列的快取（30 分鐘）
_county_cache: dict[str, dict] = {}


def _county_key(county_name: str) -> str:
    """統一「台」「臺」，避免快取 key 不一致"""
    return county_name.replace("台", "臺")


def _get_endpoint(county_name: str) -> Optional[str]:
    key = _county_key(county_name)
    return CITY_FORECAST_MAP.get(key) or CITY_FORECAST_MAP.get(county_name)


async def _fetch_county_locations(county_name: str) -> list:
    """呼叫縣市鄉鎮預報 API，回傳該縣所有 Location 陣列（含快取）。"""
    cache_key = _county_key(county_name)
    cached = _county_cache.get(cache_key)
    if cached and datetime.now(tz=TZ_8) < cached["expires_at"]:
        return cached["locations"]

    endpoint = _get_endpoint(county_name)
    if not endpoint:
        return []

    api_key = os.getenv("CWA_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="CWA_API_KEY 環境變數未設定")

    url = f"{CWA_BASE_URL}/{endpoint}"
    async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
        try:
            resp = await client.get(url, params={"Authorization": api_key, "format": "JSON"})
            resp.raise_for_status()
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="氣象署 API 請求逾時")
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=502,
                detail=f"氣象署 API 回應錯誤：HTTP {e.response.status_code}",
            )

    body = resp.json()
    locations: list = []
    for group in (body.get("records", {}).get("Locations") or []):
        locations.extend(group.get("Location") or [])

    _county_cache[cache_key] = {
        "expires_at": datetime.now(tz=TZ_8) + timedelta(minutes=30),
        "locations": locations,
    }
    return locations


def _get_pop_6h(location: dict) -> Optional[int]:
    """
    從 Location 取「未來 6 小時降雨機率」。
    氣象署 3 天預報使用 3 小時分段，故取最近的 2 個連續時段的最大值。
    """
    now = datetime.now(tz=TZ_8)

    pop_el = next(
        (el for el in location.get("WeatherElement", [])
         if "3小時降雨機率" in el.get("ElementName", "")),
        None,
    )
    if not pop_el:
        return None

    pops: list[int] = []
    for entry in pop_el.get("Time", []):
        end_str = entry.get("EndTime", "")
        try:
            end_dt = datetime.fromisoformat(end_str)
        except ValueError:
            continue

        if end_dt <= now:
            continue

        for ev in (entry.get("ElementValue") or [{}]):
            raw = next((v for v in ev.values() if v not in (None, "-", "")), None)
            if raw is not None:
                try:
                    pops.append(int(float(raw)))
                except (ValueError, TypeError):
                    pass
                break

        if len(pops) >= 2:  # 2 × 3h = 6h 涵蓋範圍
            break

    return max(pops) if pops else None


@router.get("/forecast")
async def get_forecast(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    db: AsyncSession = Depends(get_db),
):
    """給定座標，回傳所在鄉鎮未來 6 小時降雨機率（鄉鎮層級，縣市 API 結果共用快取）"""

    result = await db.execute(
        text("""
            SELECT town_name, county_name
            FROM districts
            WHERE ST_Contains(geometry, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326))
            LIMIT 1
        """),
        {"lat": lat, "lng": lng},
    )
    row = result.fetchone()

    if not row:
        return {"district_name": None, "max_pop_6h": None, "summary": "查無對應行政區"}

    town_name = row.town_name
    county_name = row.county_name

    try:
        locations = await _fetch_county_locations(county_name)
    except HTTPException:
        raise
    except Exception:
        return {"district_name": town_name, "max_pop_6h": None, "summary": "暫無預報資料"}

    if not locations:
        return {"district_name": town_name, "max_pop_6h": None, "summary": "暫無預報資料"}

    # 找對應鄉鎮
    town_loc = next(
        (loc for loc in locations if loc.get("LocationName") == town_name),
        None,
    )
    if not town_loc:
        town_loc = locations[0]  # fallback 到縣市第一個鄉鎮

    pop = _get_pop_6h(town_loc)
    summary = f"未來 6 小時降雨機率最高 {pop}%" if pop is not None else "暫無預報資料"

    return {
        "district_name": town_name,
        "max_pop_6h": pop,
        "summary": summary,
    }
