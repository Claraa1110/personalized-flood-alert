import os
from datetime import datetime

import httpx
from sqlalchemy import text

from app.database import AsyncSessionLocal

CWA_API_KEY = os.getenv("CWA_API_KEY")


async def fetch_rainfall_stations():
    """抓取全台雨量站觀測資料並寫入資料庫"""
    url = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/O-A0002-001"
    params = {
        "Authorization": CWA_API_KEY,
        "format": "JSON",
        "limit": 500,
    }

    async with httpx.AsyncClient(timeout=30, verify=False) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()

    stations = data["records"]["Station"]
    print(f"抓到 {len(stations)} 個雨量站")
    await save_rainfall_observations(stations)
    print("寫入完成")


def parse_rainfall(value) -> float:
    try:
        v = float(value)
        return max(0.0, v)
    except (TypeError, ValueError):
        return 0.0


async def save_rainfall_observations(stations: list):
    async with AsyncSessionLocal() as session:
        count = 0
        for station in stations:
            try:
                lat, lng = None, None
                for coord in station.get("GeoInfo", {}).get("Coordinates", []):
                    if coord.get("CoordinateName") == "WGS84":
                        lat = float(coord["StationLatitude"])
                        lng = float(coord["StationLongitude"])
                        break

                if lat is None or lng is None:
                    continue

                rainfall_elem = station.get("RainfallElement", {})
                rainfall_now = parse_rainfall(rainfall_elem.get("Now", {}).get("Precipitation"))
                rainfall_1hr = parse_rainfall(rainfall_elem.get("Past1hr", {}).get("Precipitation"))
                rainfall_3hr = parse_rainfall(rainfall_elem.get("Past3hr", {}).get("Precipitation"))
                rainfall_24hr = parse_rainfall(rainfall_elem.get("Past24hr", {}).get("Precipitation"))

                obs_time_str = station.get("ObsTime", {}).get("DateTime", "")
                observed_at = datetime.fromisoformat(obs_time_str).replace(tzinfo=None) if obs_time_str else datetime.now()

                geo = station.get("GeoInfo", {})

                await session.execute(
                    text("""
                        INSERT INTO rainfall_observations
                            (source, latitude, longitude, location, rainfall_mm,
                             rainfall_1hr, rainfall_3hr, rainfall_24hr,
                             station_id, station_name, county_name, town_name, observed_at)
                        VALUES (
                            'station',
                            :lat, :lng,
                            ST_MakePoint(:lng, :lat)::geography,
                            :rainfall_mm,
                            :rainfall_1hr,
                            :rainfall_3hr,
                            :rainfall_24hr,
                            :station_id,
                            :station_name,
                            :county_name,
                            :town_name,
                            :observed_at
                        )
                    """),
                    {
                        "lat": lat,
                        "lng": lng,
                        "rainfall_mm": rainfall_now,
                        "rainfall_1hr": rainfall_1hr,
                        "rainfall_3hr": rainfall_3hr,
                        "rainfall_24hr": rainfall_24hr,
                        "station_id": station.get("StationId"),
                        "station_name": station.get("StationName"),
                        "county_name": geo.get("CountyName"),
                        "town_name": geo.get("TownName"),
                        "observed_at": observed_at,
                    },
                )
                count += 1

            except Exception as e:
                print(f"  站 {station.get('StationName')} 失敗：{e}")
                await session.rollback()
                continue

        await session.commit()
        print(f"成功寫入 {count} 筆")
