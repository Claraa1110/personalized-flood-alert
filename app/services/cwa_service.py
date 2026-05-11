import os
import xml.etree.ElementTree as ET
from datetime import datetime

import httpx
from sqlalchemy import text

from app.database import AsyncSessionLocal

QPE_NS = {"cwa": "urn:cwa:gov:tw:cwacommon:0.1"}

CWA_API_KEY = os.getenv("CWA_API_KEY")

last_rainfall_update: datetime | None = None


async def fetch_rainfall_stations():
    """抓取全台雨量站觀測資料並寫入資料庫"""
    global last_rainfall_update
    try:
        url = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/O-A0002-001"
        limit = 500
        offset = 0
        all_stations = []

        async with httpx.AsyncClient(timeout=30, verify=False) as client:
            while True:
                params = {
                    "Authorization": CWA_API_KEY,
                    "format": "JSON",
                    "limit": limit,
                    "offset": offset,
                }
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                stations = data["records"]["Station"]
                if not stations:
                    break
                all_stations.extend(stations)
                if len(stations) < limit:
                    break
                offset += limit

        print(f"抓到 {len(all_stations)} 個雨量站")
        await save_rainfall_observations(all_stations)
        last_rainfall_update = datetime.now()
        print("寫入完成")
    except Exception as e:
        print(f"抓取雨量站資料失敗：{e}")


def parse_rainfall(value) -> float:
    try:
        v = float(value)
        return max(0.0, v)
    except (TypeError, ValueError):
        return 0.0


async def save_rainfall_observations(stations: list):
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
            rainfall_now = parse_rainfall(
                rainfall_elem.get("Now", {}).get("Precipitation")
            )
            rainfall_1hr = parse_rainfall(
                rainfall_elem.get("Past1hr", {}).get("Precipitation")
            )
            rainfall_3hr = parse_rainfall(
                rainfall_elem.get("Past3hr", {}).get("Precipitation")
            )
            rainfall_24hr = parse_rainfall(
                rainfall_elem.get("Past24hr", {}).get("Precipitation")
            )

            obs_time_str = station.get("ObsTime", {}).get("DateTime", "")
            observed_at = (
                datetime.fromisoformat(obs_time_str).replace(tzinfo=None)
                if obs_time_str
                else datetime.now()
            )

            geo = station.get("GeoInfo", {})

            async with AsyncSessionLocal() as session:
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
                await session.commit()
            count += 1

        except Exception as e:
            print(f"  站 {station.get('StationName')} 失敗：{e}")
            continue

    print(f"成功寫入 {count} 筆")


async def get_qpe_rainfall(lat: float, lng: float) -> dict:
    """給定座標，從 QPE API 取得該位置的雨量估計值"""
    col = round((lng - 118) / 0.0125)
    row = round((lat - 20) / 0.0125)

    if not (0 <= col < 441 and 0 <= row < 561):
        return {"rainfall_mm": 0.0, "source": "qpe", "note": "座標超出範圍"}

    index = row * 441 + col

    try:
        url = "https://opendata.cwa.gov.tw/fileapi/v1/opendataapi/O-B0045-001"
        async with httpx.AsyncClient(
            timeout=60, verify=False, follow_redirects=True
        ) as client:
            response = await client.get(url, params={"Authorization": CWA_API_KEY})
            response.raise_for_status()

        root = ET.fromstring(response.text)
        dataset = root.find("cwa:dataset", QPE_NS)
        contents = dataset.find("cwa:contents", QPE_NS)
        content = contents.find("cwa:content", QPE_NS)
        values = content.text.strip().split(",")

        rainfall = max(0.0, float(values[index])) if index < len(values) else 0.0

        return {
            "rainfall_mm": rainfall,
            "source": "qpe",
            "grid_index": index,
            "lat": lat,
            "lng": lng,
        }

    except Exception as e:
        print(f"QPE 查詢失敗：{e}")
        return await get_nearest_station_rainfall(lat, lng)


async def get_nearest_station_rainfall(lat: float, lng: float) -> dict:
    """備案：從資料庫找最近的雨量站資料"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
                SELECT rainfall_mm, rainfall_1hr, rainfall_3hr, rainfall_24hr,
                       station_name,
                       ST_Distance(location, ST_MakePoint(:lng, :lat)::geography) AS dist_m
                FROM rainfall_observations
                WHERE ST_DWithin(location, ST_MakePoint(:lng, :lat)::geography, 50000)
                ORDER BY dist_m
                LIMIT 1
            """),
            {"lat": lat, "lng": lng},
        )
        row = result.fetchone()

    if not row:
        return {"rainfall_mm": 0.0, "source": "none"}

    return {
        "rainfall_mm": row.rainfall_mm,
        "rainfall_1hr": row.rainfall_1hr,
        "rainfall_3hr": row.rainfall_3hr,
        "rainfall_24hr": row.rainfall_24hr,
        "source": "station",
        "station_name": row.station_name,
        "dist_m": round(row.dist_m),
    }
