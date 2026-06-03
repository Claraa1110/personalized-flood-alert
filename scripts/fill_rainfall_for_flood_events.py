import asyncio
from datetime import datetime, timedelta
from sqlalchemy import text
from app.database import AsyncSessionLocal
from app.services.codis_service import (
    find_nearby_stations,
    download_hourly_rainfall,
    calculate_max_rainfall,
)


async def main():
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("""
            SELECT id, county_name, district_name, lat, lng, news_time
            FROM flood_events
            WHERE lat IS NOT NULL
            AND lng IS NOT NULL
            AND news_time IS NOT NULL
            ORDER BY id
        """))
        events = result.fetchall()

    print(f"待填入雨量：{len(events)} 筆\n")

    filled = 0
    for event in events:
        label = f"{event.county_name or ''}{event.district_name or ''} {event.news_time}"
        print(f"處理：{label}")

        async with AsyncSessionLocal() as session:
            stations = await find_nearby_stations(event.lat, event.lng, radius_km=20, session=session)

        if not stations:
            async with AsyncSessionLocal() as session:
                stations = await find_nearby_stations(event.lat, event.lng, radius_km=30, session=session)

        if not stations:
            print("  找不到附近測站，跳過\n")
            continue

        station = stations[0]
        print(f"  測站：{station['station_name']}（{station['station_id']}）{station['distance_km']}km")

        start = event.news_time - timedelta(hours=12)
        hourly = download_hourly_rainfall(station['station_id'], start, event.news_time)

        if not hourly:
            print("  CODIS 無資料，跳過\n")
            continue

        rainfall = calculate_max_rainfall(hourly)
        print(f"  1H={rainfall['1h']}mm  3H={rainfall['3h']}mm  6H={rainfall['6h']}mm")

        # 先 commit flood_events
        async with AsyncSessionLocal() as session:
            await session.execute(text("""
                UPDATE flood_events
                SET rainfall_1h = :r1h, rainfall_3h = :r3h, rainfall_6h = :r6h
                WHERE id = :id
            """), {
                'r1h': rainfall['1h'],
                'r3h': rainfall['3h'],
                'r6h': rainfall['6h'],
                'id': event.id,
            })
            await session.commit()

        # 再逐筆存 codis_raw_rainfall
        for h in hourly:
            try:
                obs_time = datetime.fromisoformat(h['time']) if isinstance(h['time'], str) else h['time']
                async with AsyncSessionLocal() as session:
                    await session.execute(text("""
                        INSERT INTO codis_raw_rainfall
                            (flood_event_id, station_id, station_name, distance_km, obs_time, rainfall_mm)
                        VALUES (:fid, :sid, :sname, :dist, :obs_time, :rain)
                        ON CONFLICT (flood_event_id, station_id, obs_time) DO NOTHING
                    """), {
                        'fid': event.id,
                        'sid': station['station_id'],
                        'sname': station['station_name'],
                        'dist': station['distance_km'],
                        'obs_time': obs_time,
                        'rain': h['rainfall_mm'],
                    })
                    await session.commit()
            except Exception as e:
                print(f"  codis_raw_rainfall 寫入失敗：{e}")

        filled += 1
        print()
        await asyncio.sleep(0.5)

    print(f"完成！共填入 {filled} 筆\n")

    async with AsyncSessionLocal() as session:
        result = await session.execute(text("""
            SELECT COUNT(*) as total, COUNT(rainfall_1h) as with_rainfall
            FROM flood_events
        """))
        row = result.fetchone()
        print(f"flood_events 總計 {row.total} 筆，已有雨量資料 {row.with_rainfall} 筆")


if __name__ == "__main__":
    asyncio.run(main())
