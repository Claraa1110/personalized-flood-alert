import asyncio
import re
import time

import httpx
from fastapi import APIRouter, HTTPException, Query

router = APIRouter()

_NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
_NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"
_NOMINATIM_URL = _NOMINATIM_SEARCH_URL  # backward compat
_USER_AGENT = "FloodAlertApp/1.0"

# 速率限制：Nominatim 要求每秒最多 1 次
_last_call: float = 0.0
_lock = asyncio.Lock()


async def _nominatim_query(client: httpx.AsyncClient, q: str) -> list:
    params = {"q": q, "format": "json", "countrycodes": "tw", "limit": 1}
    headers = {"User-Agent": _USER_AGENT}
    try:
        resp = await client.get(_NOMINATIM_URL, params=params, headers=headers)
        resp.raise_for_status()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="地址查詢服務逾時，請稍後再試")
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=502,
            detail=f"地址查詢服務錯誤：HTTP {e.response.status_code}",
        )
    try:
        return resp.json()
    except Exception:
        raise HTTPException(status_code=502, detail="地址查詢服務回傳格式錯誤")


@router.get("/geocode")
async def geocode_address(address: str = Query(..., description="地址")):
    """將地址轉換為經緯度（使用 Nominatim / OpenStreetMap）"""
    global _last_call

    async with _lock:
        elapsed = time.monotonic() - _last_call
        if elapsed < 1.0:
            await asyncio.sleep(1.0 - elapsed)
        _last_call = time.monotonic()

    async with httpx.AsyncClient(timeout=10.0) as client:
        results = await _nominatim_query(client, address)

        # fallback：OSM 台灣門牌號碼資料稀疏，移除末尾號碼後重試
        if not results:
            fallback = re.sub(r'\d+號$', '', address).strip()
            if fallback and fallback != address:
                results = await _nominatim_query(client, fallback)

    if not results:
        raise HTTPException(
            status_code=404,
            detail="找不到此地址，請確認地址是否正確或改用地圖選點",
        )

    r = results[0]
    return {
        "lat": float(r["lat"]),
        "lng": float(r["lon"]),
        "formatted_address": r.get("display_name", address),
    }


def _build_tw_address(addr: dict) -> str:
    """從 Nominatim address 物件組出簡短的中文地址"""
    city = addr.get("city") or addr.get("county") or addr.get("state") or ""
    district = addr.get("city_district") or addr.get("suburb") or addr.get("town") or addr.get("village") or ""
    road = addr.get("road") or addr.get("pedestrian") or addr.get("footway") or ""
    return f"{city}{district}{road}".strip() or addr.get("display_name", "")


@router.get("/reverse-geocode")
async def reverse_geocode(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
):
    """將經緯度轉換為地址（使用 Nominatim reverse geocoding）"""
    global _last_call

    async with _lock:
        elapsed = time.monotonic() - _last_call
        if elapsed < 1.0:
            await asyncio.sleep(1.0 - elapsed)
        _last_call = time.monotonic()

    params = {"lat": lat, "lon": lng, "format": "json", "accept-language": "zh-TW,zh"}
    headers = {"User-Agent": _USER_AGENT}

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(_NOMINATIM_REVERSE_URL, params=params, headers=headers)
            resp.raise_for_status()
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="地址查詢服務逾時，請稍後再試")
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=502, detail=f"地址查詢服務錯誤：HTTP {e.response.status_code}")

    try:
        data = resp.json()
    except Exception:
        raise HTTPException(status_code=502, detail="地址查詢服務回傳格式錯誤")

    if "error" in data:
        raise HTTPException(status_code=404, detail="查無此座標對應地址")

    addr_obj = data.get("address", {})
    short_address = _build_tw_address(addr_obj)

    return {
        "lat": lat,
        "lng": lng,
        "formatted_address": short_address or data.get("display_name", ""),
    }
