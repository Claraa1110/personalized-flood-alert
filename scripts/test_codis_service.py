import asyncio
from datetime import datetime, timedelta
from app.database import AsyncSessionLocal
from app.services.codis_service import (
    find_nearby_stations,
    download_hourly_rainfall,
    calculate_max_rainfall,
)

async def main():
    # 測試：高雄市岡山區嘉興里（凱米颱風事件）
    lat, lng = 22.8051, 120.2979
    news_time = datetime(2024, 7, 25, 6, 0, 0)
    start = news_time - timedelta(hours=6)

    print("=== Step 1：找附近測站 ===")
    async with AsyncSessionLocal() as session:
        stations = await find_nearby_stations(lat, lng, radius_km=20, session=session)

    print(f"找到 {len(stations)} 個測站（20km 內）")
    for s in stations[:5]:
        print(f"  {s['station_name']}（{s['station_id']}）距離 {s['distance_km']}km")

    if not stations:
        print("找不到測站，擴大到 30km")
        async with AsyncSessionLocal() as session:
            stations = await find_nearby_stations(lat, lng, radius_km=30, session=session)
        print(f"找到 {len(stations)} 個測站（30km 內）")

    print("\n=== Step 2：下載最近測站的雨量 ===")
    if stations:
        station = stations[0]
        print(f"使用測站：{station['station_name']}（{station['station_id']}）")
        hourly = download_hourly_rainfall(station['station_id'], start, news_time)
        print(f"下載 {len(hourly)} 筆逐小時資料")
        for h in hourly:
            print(f"  {h['time']}：{h['rainfall_mm']}mm")

        print("\n=== Step 3：計算致災雨量 ===")
        rainfall = calculate_max_rainfall(hourly)
        print(f"1H 最大：{rainfall['1h']}mm")
        print(f"3H 最大：{rainfall['3h']}mm")
        print(f"6H 累積：{rainfall['6h']}mm")

if __name__ == "__main__":
    asyncio.run(main())
