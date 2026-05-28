import asyncio
from sqlalchemy import text
from app.database import AsyncSessionLocal
from app.services.codis_service import calculate_max_rainfall


async def recalculate_events(event_ids: list[int]):
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("""
            SELECT DISTINCT flood_event_id
            FROM codis_raw_rainfall
            WHERE flood_event_id = ANY(:ids)
        """), {'ids': event_ids})
        found_ids = [row.flood_event_id for row in result.fetchall()]

    print(f"找到 {len(found_ids)} 個事件有 codis_raw_rainfall 資料\n")

    for event_id in found_ids:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("""
                SELECT obs_time, rainfall_mm
                FROM codis_raw_rainfall
                WHERE flood_event_id = :eid
                ORDER BY obs_time
            """), {'eid': event_id})
            rows = result.fetchall()

        hourly = [{'time': str(r.obs_time), 'rainfall_mm': r.rainfall_mm} for r in rows]
        rainfall = calculate_max_rainfall(hourly)
        print(f"event_id={event_id}：1H={rainfall['1h']}mm  3H={rainfall['3h']}mm  6H={rainfall['6h']}mm")

        async with AsyncSessionLocal() as session:
            await session.execute(text("""
                UPDATE flood_events
                SET rainfall_1h = :r1h, rainfall_3h = :r3h, rainfall_6h = :r6h
                WHERE id = :id
            """), {
                'r1h': rainfall['1h'],
                'r3h': rainfall['3h'],
                'r6h': rainfall['6h'],
                'id': event_id,
            })
            await session.commit()

    print("\n重算完成")


async def main():
    await recalculate_events([16, 40])


if __name__ == "__main__":
    asyncio.run(main())
