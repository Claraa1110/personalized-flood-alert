import os
from datetime import datetime, timedelta
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.dependencies import get_db

router = APIRouter()

CWA_FORECAST_URL = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-D0047-089"

# 全台 raw locations 快取（所有鄉鎮共用）
_raw_cache: dict = {"expires_at": datetime.min, "loc_groups": []}

# 解析結果 per-town 快取
_cache: dict[str, dict] = {}


def _get_cached(town: str) -> Optional[list]:
    entry = _cache.get(town)
    if entry and datetime.now() < entry["expires_at"]:
        return entry["data"]
    return None


def _set_cached(town: str, data: list) -> None:
    _cache[town] = {
        "expires_at": datetime.now() + timedelta(minutes=30),
        "data": data,
    }


# 氣象署可能用的降雨機率欄位名稱（英文或中文）
_POP_NAMES = ("PoP3h", "3小時降雨機率", "降雨機率3小時", "降雨機率")

async def _fetch_pop_slots(town_name: str, county_name: str) -> list[dict]:
    """呼叫氣象署 F-D0047-089，解析並回傳未來最多 2 個 3-小時時段的降雨機率"""
    global _raw_cache

    # ── 全台 raw 資料快取（30 min）────────────────────────────────────
    if datetime.now() < _raw_cache["expires_at"]:
        loc_groups = _raw_cache["loc_groups"]
    else:
        api_key = os.getenv("CWA_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="CWA_API_KEY 環境變數未設定")

        # 不帶 LocationName filter：CWA F-D0047-089 的 LocationName 只匹配縣市，
        # 不支援鄉鎮名直接過濾，需拿全台資料再本地搜尋。
        params = {"Authorization": api_key, "format": "JSON"}

        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            try:
                resp = await client.get(CWA_FORECAST_URL, params=params)
                resp.raise_for_status()
            except httpx.TimeoutException:
                raise HTTPException(status_code=504, detail="氣象署 API 請求逾時")
            except httpx.HTTPStatusError as e:
                raise HTTPException(
                    status_code=502,
                    detail=f"氣象署 API 回應錯誤：HTTP {e.response.status_code}",
                )

        try:
            body = resp.json()
        except Exception:
            raise HTTPException(status_code=502, detail="氣象署回傳非 JSON 格式")

        records = body.get("records", {})
        loc_groups = records.get("Locations", []) if isinstance(records, dict) else []
        _raw_cache = {
            "expires_at": datetime.now() + timedelta(minutes=30),
            "loc_groups": loc_groups,
        }

    # ── 用 county_name 找縣市 entry（F-D0047-089 是縣市層級資料）────
    # CWA 官方用「臺」，資料庫可能用「台」，兩種都試
    cwa_county = county_name.replace("台", "臺")
    target_loc = None
    for group in loc_groups:
        for loc in (group.get("Location") or []):
            if loc.get("LocationName") in (cwa_county, county_name):
                target_loc = loc
                break
        if target_loc:
            break

    if not target_loc:
        return []

    # ── 找 3小時降雨機率 WeatherElement ───────────────────────────────
    pop_el = next(
        (el for el in target_loc.get("WeatherElement", [])
         if el.get("ElementName") in _POP_NAMES),
        None,
    )
    if not pop_el:
        return []

    # ── 解析時間（ISO 8601：2026-07-07T12:00:00+08:00）────────────────
    from datetime import timezone
    tz_8 = timezone(timedelta(hours=8))
    now_tz = datetime.now(tz=tz_8)
    slots: list[dict] = []

    for entry in pop_el.get("Time", []):
        end_str = entry.get("EndTime", "")
        start_str = entry.get("StartTime", "")
        try:
            end_dt = datetime.fromisoformat(end_str)
            start_dt = datetime.fromisoformat(start_str)
        except ValueError:
            continue

        if end_dt <= now_tz:
            continue

        # ElementValue key: ProbabilityOfPrecipitation（或 PoP3h 等）
        pop = None
        for ev in (entry.get("ElementValue") or [{}]):
            raw = next((v for v in ev.values() if v not in (None, "-", "")), None)
            if raw is not None:
                try:
                    pop = int(float(raw))
                except (ValueError, TypeError):
                    pass
                break

        slots.append({
            "time": start_str[:16].replace("T", " "),
            "pop": pop,
        })

        if len(slots) >= 2:
            break

    return slots


@router.get("/forecast/raw")
async def get_forecast_raw(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    db: AsyncSession = Depends(get_db),
):
    """Debug: 回傳 CWA F-D0047-089 縣市所有 WeatherElement 前 2 個時段原始資料"""
    result = await db.execute(
        text("SELECT town_name, county_name FROM districts WHERE ST_Contains(geometry, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)) LIMIT 1"),
        {"lat": lat, "lng": lng},
    )
    row = result.fetchone()
    if not row:
        return {"error": "查無行政區"}

    county_name = row.county_name
    cwa_county = county_name.replace("台", "臺")

    if datetime.now() >= _raw_cache["expires_at"]:
        api_key = os.getenv("CWA_API_KEY")
        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            resp = await client.get(CWA_FORECAST_URL, params={"Authorization": api_key, "format": "JSON"})
            resp.raise_for_status()
        body = resp.json()
        records = body.get("records", {})
        loc_groups = records.get("Locations", []) if isinstance(records, dict) else []
        _raw_cache["expires_at"] = datetime.now() + timedelta(minutes=30)
        _raw_cache["loc_groups"] = loc_groups

    loc_groups = _raw_cache["loc_groups"]
    target = None
    for group in loc_groups:
        for loc in (group.get("Location") or []):
            if loc.get("LocationName") in (cwa_county, county_name):
                target = loc
                break
        if target:
            break

    if not target:
        return {"error": f"找不到縣市: {cwa_county}"}

    output = {}
    for we in target.get("WeatherElement", []):
        name = we.get("ElementName", "")
        times = we.get("Time", [])[:2]
        output[name] = [
            {"StartTime": t.get("StartTime"), "EndTime": t.get("EndTime"), "ElementValue": t.get("ElementValue")}
            for t in times
        ]

    return {"county": target.get("LocationName"), "elements": output}


@router.get("/forecast")
async def get_forecast(
    lat: float = Query(..., ge=-90, le=90, description="緯度"),
    lng: float = Query(..., ge=-180, le=180, description="經度"),
    db: AsyncSession = Depends(get_db),
):
    """給定座標，回傳所在鄉鎮未來 6 小時（2 個逐 3 小時時段）降雨機率預報"""

    # Step 1: 用座標反查鄉鎮名稱
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
        return {
            "district_name": None,
            "forecast": [],
            "max_pop_6h": None,
            "summary": "查無對應行政區，暫無預報資料",
        }

    town_name = row.town_name
    county_name = row.county_name

    # Step 2: 快取命中直接回傳
    cached = _get_cached(town_name)
    if cached is not None:
        slots = cached
    else:
        # Step 3: 呼叫氣象署 API
        try:
            slots = await _fetch_pop_slots(town_name, county_name)
        except HTTPException:
            raise
        except Exception as e:
            print(f"[forecast] _fetch_pop_slots 例外：{type(e).__name__}: {e}", flush=True)
            return {
                "district_name": town_name,
                "forecast": [],
                "max_pop_6h": None,
                "summary": "暫無預報資料",
            }
        # 只快取非空結果，空結果讓下次 request 重新打 API
        if slots:
            _set_cached(town_name, slots)

    if not slots:
        return {
            "district_name": town_name,
            "forecast": [],
            "max_pop_6h": None,
            "summary": "暫無預報資料",
        }

    # Step 4: 彙整摘要
    pops = [s["pop"] for s in slots if s["pop"] is not None]
    max_pop = max(pops) if pops else None
    summary = (
        f"未來 6 小時降雨機率最高 {max_pop}%"
        if max_pop is not None
        else "暫無預報資料"
    )

    return {
        "district_name": town_name,
        "forecast": slots,
        "max_pop_6h": max_pop,
        "summary": summary,
    }
