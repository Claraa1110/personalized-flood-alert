"""
Test CWA rainfall station API to confirm data structure.
Usage: uv run python scripts/test_cwa_api.py
"""
import asyncio
import json
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

CWA_API_KEY = os.getenv("CWA_API_KEY")


async def test_rainfall_stations():
    url = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/O-A0002-001"
    params = {
        "Authorization": CWA_API_KEY,
        "format": "JSON",
        "limit": 5,
    }

    async with httpx.AsyncClient(timeout=30, verify=False) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()

    print("=== API 回傳結構 ===")
    print(f"success: {data.get('success')}")

    stations = data["records"]["Station"]
    print(f"\n總共 {len(stations)} 個雨量站（目前只抓 5 筆）")

    print("\n=== 第一個雨量站的完整資料 ===")
    print(json.dumps(stations[0], ensure_ascii=False, indent=2))

    print("\n=== 前 5 個雨量站摘要 ===")
    for station in stations:
        station_id = station.get("StationId", "N/A")
        station_name = station.get("StationName", "N/A")

        coords = station.get("GeoInfo", {}).get("Coordinates", [])
        lat, lng = None, None
        for coord in coords:
            if coord.get("CoordinateName") == "WGS84":
                lat = coord.get("StationLatitude")
                lng = coord.get("StationLongitude")

        rainfall = station.get("RainfallElement", {})
        now = rainfall.get("Now", {}).get("Precipitation", "N/A")
        past_1hr = rainfall.get("Past1hr", {}).get("Precipitation", "N/A")

        print(f"站名：{station_name}（{station_id}）")
        print(f"  座標：{lat}, {lng}")
        print(f"  當前雨量：{now} mm")
        print(f"  過去1小時：{past_1hr} mm")
        print()


if __name__ == "__main__":
    asyncio.run(test_rainfall_stations())
