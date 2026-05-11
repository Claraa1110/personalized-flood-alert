import feedparser
import json
import logging
from datetime import datetime
from sqlalchemy import text
from app.database import AsyncSessionLocal
from openai import OpenAI
import os

logger = logging.getLogger(__name__)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

RSS_SOURCES = [
    {"name": "自由時報", "url": "https://news.ltn.com.tw/rss/all.xml"},
    {"name": "聯合新聞網", "url": "https://udn.com/rssfeed/news/2/6638?ch=news"},
    {
        "name": "Google新聞淹水",
        "url": "https://news.google.com/rss/search?q=淹水+台灣&hl=zh-TW&gl=TW&ceid=TW:zh-Hant",
    },
]


def get_llm_client():
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )


async def fetch_news():
    """抓取所有 RSS 來源的新聞並存進資料庫"""
    total = 0
    for source in RSS_SOURCES:
        try:
            count = await fetch_single_source(source["name"], source["url"])
            total += count
            logger.info(f"{source['name']}：新增 {count} 則")
        except Exception as e:
            logger.error(f"{source['name']} 抓取失敗：{e}")
    logger.info(f"新聞抓取完成，共新增 {total} 則")
    return total


async def fetch_single_source(source_name: str, rss_url: str) -> int:
    feed = feedparser.parse(rss_url)
    if not feed.entries:
        return 0

    count = 0
    async with AsyncSessionLocal() as session:
        for entry in feed.entries:
            try:
                url = entry.get("link", "")
                title = entry.get("title", "")
                if not url or not title:
                    continue

                existing = await session.execute(
                    text("SELECT id FROM news_articles WHERE url = :url LIMIT 1"),
                    {"url": url},
                )
                if existing.fetchone():
                    continue

                published_at = datetime.now()
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    published_at = datetime(*entry.published_parsed[:6])

                await session.execute(
                    text("""
                        INSERT INTO news_articles
                            (id, title, url, source, published_at, is_flood_related)
                        VALUES
                            (gen_random_uuid(), :title, :url, :source, :published_at, false)
                    """),
                    {
                        "title": title,
                        "url": url,
                        "source": source_name,
                        "published_at": published_at,
                    },
                )
                count += 1

            except Exception as e:
                print(f"新聞寫入失敗：{e}")
                logger.error(f"新聞寫入失敗：{e}")
                continue

        await session.commit()
    return count


def classify_news_batch(titles: list[str]) -> list[dict]:
    """批次分類新聞，一次送多則給 LLM"""
    client = get_llm_client()

    numbered = "\n".join([f"{i + 1}. {t}" for i, t in enumerate(titles)])

    prompt = f"""你是新聞分類助理。請判斷以下每則新聞標題是否描述「台灣當下正在發生的淹水或積水事件」。

判斷標準：
- is_flood_related true：描述當下發生的淹水、積水、暴雨成災、道路積水
- is_flood_related false：歷史回顧、政策討論、工程預算、國外新聞、氣象預報

只回答 JSON 陣列，不要其他文字，格式如下：
[
  {{"id": 1, "is_flood_related": true, "severity": "high", "confidence": 0.95}},
  {{"id": 2, "is_flood_related": false, "severity": "none", "confidence": 0.90}}
]

severity 只能是：high、medium、low、none

新聞標題：
{numbered}"""

    try:
        response = client.chat.completions.create(
            model="openai/gpt-4o-mini",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )
        result_text = response.choices[0].message.content
        print(f"=== LLM 原始回傳 ===\n{result_text}\n==================")
        result_text = result_text.strip()

        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]

        return json.loads(result_text)

    except Exception as e:
        logger.error(f"LLM 分類失敗：{e}")
        return [
            {
                "id": i + 1,
                "is_flood_related": False,
                "severity": "none",
                "confidence": 0.0,
            }
            for i in range(len(titles))
        ]


async def classify_unclassified_news():
    """把資料庫裡還沒分類的新聞批次送給 LLM 分類"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
                SELECT id, title FROM news_articles
                WHERE severity IS NULL
                AND published_at > NOW() - INTERVAL '24 hours'
                ORDER BY published_at DESC
                LIMIT 100
            """)
        )
        rows = result.fetchall()

        if not rows:
            logger.info("沒有待分類的新聞")
            return 0

        batch_size = 10
        classified = 0

        for i in range(0, len(rows), batch_size):
            batch = rows[i : i + batch_size]
            titles = [row.title for row in batch]

            try:
                results = classify_news_batch(titles)

                for j, row in enumerate(batch):
                    result_item = next(
                        (r for r in results if r["id"] == j + 1),
                        {
                            "is_flood_related": False,
                            "severity": "none",
                            "confidence": 0.0,
                        },
                    )

                    await session.execute(
                        text("""
                            UPDATE news_articles
                            SET is_flood_related = :is_flood,
                                severity = :severity
                            WHERE id = :id
                        """),
                        {
                            "is_flood": result_item.get("is_flood_related", False),
                            "severity": result_item.get("severity", "none"),
                            "id": row.id,
                        },
                    )
                    classified += 1

                await session.commit()
                logger.info(f"已分類 {min(i + batch_size, len(rows))}/{len(rows)} 則")

            except Exception as e:
                logger.error(f"批次分類失敗：{e}")
                continue

    logger.info(f"分類完成，共處理 {classified} 則")
    return classified


async def fetch_and_classify_news():
    """排程用：抓新聞 + 分類 + 地名抽取"""
    await fetch_news()
    await classify_unclassified_news()
    await extract_locations_for_flood_news()


async def get_location_centroid(location_name: str, db) -> tuple[float, float] | None:
    """把地名轉成座標（查 districts 表的中心點）"""
    result = await db.execute(
        text("""
            SELECT
                ST_X(ST_Centroid(geometry::geometry)) AS lng,
                ST_Y(ST_Centroid(geometry::geometry)) AS lat
            FROM districts
            WHERE town_name LIKE :name
               OR county_name LIKE :name
            LIMIT 1
        """),
        {"name": f"%{location_name}%"},
    )
    row = result.fetchone()
    if row:
        return (row.lat, row.lng)
    return None


async def extract_locations_for_flood_news():
    """對所有淹水新聞做地名抽取"""
    from app.services.llm_service import extract_locations

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
                SELECT id, title FROM news_articles
                WHERE is_flood_related = true
                AND (locations IS NULL OR locations::text = '[]')
                AND published_at > NOW() - INTERVAL '24 hours'
                ORDER BY published_at DESC
                LIMIT 50
            """)
        )
        rows = result.fetchall()

        if not rows:
            logger.info("沒有需要地名抽取的新聞")
            return 0

        count = 0
        for row in rows:
            try:
                locations = extract_locations(row.title)

                if not locations:
                    await session.execute(
                        text(
                            "UPDATE news_articles SET locations = '[]' WHERE id = :id"
                        ),
                        {"id": row.id},
                    )
                    continue

                coords = None
                for loc in locations:
                    coords = await get_location_centroid(loc, session)
                    if coords:
                        break

                if coords:
                    lat, lng = coords
                    await session.execute(
                        text("""
                            UPDATE news_articles
                            SET locations = :locations,
                                location_geom = ST_MakePoint(:lng, :lat)::geography
                            WHERE id = :id
                        """),
                        {
                            "locations": json.dumps(locations, ensure_ascii=False),
                            "lat": lat,
                            "lng": lng,
                            "id": row.id,
                        },
                    )
                else:
                    await session.execute(
                        text(
                            "UPDATE news_articles SET locations = :locations WHERE id = :id"
                        ),
                        {
                            "locations": json.dumps(locations, ensure_ascii=False),
                            "id": row.id,
                        },
                    )

                count += 1
                logger.info(f"地名抽取：{row.title[:30]} → {locations}")

            except Exception as e:
                logger.error(f"地名抽取失敗：{row.title[:30]}，錯誤：{e}")
                continue

        await session.commit()
        logger.info(f"地名抽取完成，共處理 {count} 則")
        return count
