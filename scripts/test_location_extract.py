import asyncio
import json
import uuid
from app.services.news_service import extract_locations_for_flood_news
from app.services.llm_service import extract_locations


async def main():
    print("=== 測試地名抽取 ===")
    test_titles = [
        "高雄岡山大雨 多處道路積水",
        "台北市信義區道路積水 交通受阻",
        "颱風外圍環流 花蓮多處淹水",
    ]
    for title in test_titles:
        locations = extract_locations(title)
        print(f"標題：{title}")
        print(f"地名：{locations}\n")

    print("=== 對資料庫淹水新聞做地名抽取 ===")

    from app.database import AsyncSessionLocal
    from sqlalchemy import text

    async with AsyncSessionLocal() as session:
        await session.execute(
            text("""
                INSERT INTO news_articles (id, title, url, source, published_at, is_flood_related, severity)
                VALUES
                    (:id1, '高雄岡山大雨 多處道路積水嚴重', 'https://test.com/t1', '測試', NOW(), true, 'high'),
                    (:id2, '台北市信義區道路積水 交通受阻', 'https://test.com/t2', '測試', NOW(), true, 'medium'),
                    (:id3, '颱風外圍環流 花蓮多處淹水', 'https://test.com/t3', '測試', NOW(), true, 'high')
            """),
            {"id1": uuid.uuid4(), "id2": uuid.uuid4(), "id3": uuid.uuid4()},
        )
        await session.commit()

    count = await extract_locations_for_flood_news()
    print(f"處理了 {count} 則新聞")

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
                SELECT title, locations, location_geom IS NOT NULL as has_coords
                FROM news_articles
                WHERE source = '測試'
            """)
        )
        for row in result.fetchall():
            print(f"標題：{row.title[:30]}")
            print(f"地名：{row.locations}")
            print(f"有座標：{row.has_coords}\n")

        await session.execute(text("DELETE FROM news_articles WHERE source = '測試'"))
        await session.commit()


if __name__ == "__main__":
    asyncio.run(main())
