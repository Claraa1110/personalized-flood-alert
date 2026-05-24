import asyncio
import json
import os
import httpx
from datetime import datetime
from sqlalchemy import text
from app.database import AsyncSessionLocal
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

SEARCH_QUERIES = [
    # 梅雨季
    "2024年5月台灣梅雨淹水 縣市鄉鎮地點災情",
    "2024年6月台灣梅雨鋒面淹水 縣市鄉鎮地點",

    # 凱米颱風（7月）
    "2024年7月凱米颱風高雄淹水 鄉鎮里別地點",
    "2024年7月凱米颱風台南嘉義淹水 鄉鎮地點",
    "2024年7月凱米颱風台灣中北部淹水 地點",

    # 西南氣流（7月底-8月）
    "2024年7月底西南氣流台灣淹水 縣市地點",
    "2024年8月台灣豪雨淹水 鄉鎮地點災情",

    # 秋季
    "2024年9月台灣颱風豪雨淹水 地點",

    # 山陀兒颱風（10月）
    "2024年10月山陀兒颱風台灣淹水 高雄台南地點",
    "2024年山陀兒颱風淹水災情 鄉鎮里別",
    
    # 康芮颱風（10月30日-11月1日）
    "2024年康芮颱風台灣淹水 縣市鄉鎮地點",
    "2024年10月康芮颱風淹水災情 鄉鎮里別",
]


async def search_and_extract(query: str) -> list[dict]:
    prompt = f"""請搜尋以下關鍵字，找出 2024 年台灣真實發生的淹水事件：
「{query}」

搜尋完後，從搜尋結果中抽取所有淹水事件。
只回傳 JSON 陣列，不要其他文字：

[
  {{
    "county": "高雄市",
    "district": "岡山區",
    "village": "嘉興里",
    "event_time": "2024-07-25T06:00:00",
    "description": "凱米颱風岡山嘉興里淹水腳踝",
    "confidence": "high"
  }}
]

規則：
- county：縣市，找不到填 null
- district：鄉鎮市區，找不到填 null
- village：村里，找不到填 null
- event_time：ISO 格式時間，找不到填 null
- description：一句話描述淹水情況
- confidence：high（地點+時間明確）/ medium（地點或時間不明確）/ low（資訊不足）
- 只包含台灣境內、2024 年的淹水事件
- 找不到任何事件回傳 []
"""

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "openai/gpt-4o-mini",
                    "max_tokens": 2000,
                    "messages": [{"role": "user", "content": prompt}],
                    "tools": [{"type": "web_search"}],
                },
            )

        data = response.json()

        if response.status_code != 200:
            print(f"  HTTP status: {response.status_code}")
            print(f"  錯誤：{data.get('error', {}).get('message', '')}")
            return []

        content = ""
        for choice in data.get("choices", []):
            msg = choice.get("message", {})
            if msg.get("content"):
                content = msg["content"]
                break

        if not content:
            print(f"  沒有文字回應")
            return []

        text_clean = content.strip()
        if "```" in text_clean:
            text_clean = text_clean.split("```")[1]
            if text_clean.startswith("json"):
                text_clean = text_clean[4:]

        start = text_clean.find("[")
        end = text_clean.rfind("]") + 1
        if start == -1 or end == 0:
            print(f"  找不到 JSON 陣列，原始回應：{content[:200]}")
            return []

        events = json.loads(text_clean[start:end])
        return events if isinstance(events, list) else []

    except Exception as e:
        print(f"  例外錯誤：{e}")
        return []


async def get_coords(session, district: str, county: str = None) -> tuple:
    if not district:
        return None, None

    params = {"district": district}
    where = "town_name = :district"
    if county:
        where += " AND county_name = :county"
        params["county"] = county

    result = await session.execute(
        text(f"""
            SELECT
                ST_Y(ST_Centroid(geometry::geometry)) as lat,
                ST_X(ST_Centroid(geometry::geometry)) as lng
            FROM districts
            WHERE {where}
            LIMIT 1
        """),
        params,
    )

    row = result.fetchone()
    if row:
        return row.lat, row.lng
    return None, None


async def save_events(events: list[dict]) -> int:
    if not events:
        return 0

    count = 0
    async with AsyncSessionLocal() as session:
        for event in events:
            try:
                county = event.get("county")
                district = event.get("district")
                village = event.get("village")
                event_time_raw = event.get("event_time")
                description = event.get("description", "")
                confidence = event.get("confidence", "low")

                event_time = None
                if event_time_raw:
                    try:
                        event_time = datetime.fromisoformat(
                            event_time_raw.replace("Z", "+00:00")
                        ).replace(tzinfo=None)
                    except Exception:
                        event_time = None

                lat, lng = await get_coords(session, district, county)
                if lat is None and county:
                    lat, lng = await get_coords(session, county)

                await session.execute(
                    text("""
                        INSERT INTO flood_events
                            (news_title, news_time,
                             location_name, county_name, district_name, village_name,
                             lat, lng, confidence)
                        VALUES (
                            :title, :news_time,
                            :location, :county, :district, :village,
                            :lat, :lng, :confidence
                        )
                        ON CONFLICT (county_name, district_name, village_name, news_time)
                        DO NOTHING
                    """),
                    {
                        "title": description,
                        "news_time": event_time,
                        "location": f"{county or ''}{district or ''}{village or ''}",
                        "county": county,
                        "district": district,
                        "village": village,
                        "lat": lat,
                        "lng": lng,
                        "confidence": confidence,
                    },
                )
                await session.commit()
                count += 1

            except Exception as e:
                print(f"  寫入失敗：{e}")
                await session.rollback()
                continue

    return count


async def main():
    print("開始搜尋 2024 年台灣淹水事件...\n")

    total = 0
    for query in SEARCH_QUERIES:
        print(f"搜尋：{query}")
        events = await search_and_extract(query)
        print(f"  找到 {len(events)} 個事件")

        saved = await save_events(events)
        print(f"  寫入 {saved} 筆\n")
        total += saved

        await asyncio.sleep(2)

    print(f"\n全部完成！共寫入 {total} 筆淹水事件")

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
                SELECT confidence, COUNT(*) as count
                FROM flood_events
                GROUP BY confidence
                ORDER BY confidence
            """)
        )
        print("\n=== 資料品質摘要 ===")
        for row in result.fetchall():
            print(f"  {row.confidence}: {row.count} 筆")

        result2 = await session.execute(
            text("""
                SELECT county_name, COUNT(*) as count
                FROM flood_events
                GROUP BY county_name
                ORDER BY count DESC
            """)
        )
        print("\n=== 地理分布 ===")
        for row in result2.fetchall():
            print(f"  {row.county_name}: {row.count} 筆")


if __name__ == "__main__":
    asyncio.run(main())
