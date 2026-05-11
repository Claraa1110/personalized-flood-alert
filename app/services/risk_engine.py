import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal
from app.services.cwa_service import get_qpe_rainfall

logger = logging.getLogger(__name__)


def calculate_risk_score(
    rainfall_1hr: float,
    flood_potential: int,
    news_severity: str,
) -> int:
    score = 0

    if rainfall_1hr > 80:
        score += 40
    elif rainfall_1hr > 50:
        score += 25
    elif rainfall_1hr > 30:
        score += 10

    score += flood_potential * 5

    if news_severity == "high":
        score += 25
    elif news_severity == "medium":
        score += 15
    elif news_severity == "low":
        score += 5

    return score


def score_to_level(score: int) -> str:
    if score >= 70:
        return "emergency"
    elif score >= 40:
        return "warning"
    elif score >= 20:
        return "notice"
    else:
        return "safe"


async def get_news_signal_near(lat: float, lng: float, db: AsyncSession) -> dict:
    """查詢附近 30 公里內最嚴重的淹水新聞"""
    result = await db.execute(
        text("""
            SELECT severity
            FROM news_articles
            WHERE is_flood_related = true
            AND location_geom IS NOT NULL
            AND ST_DWithin(
                location_geom,
                ST_MakePoint(:lng, :lat)::geography,
                30000
            )
            AND published_at > NOW() - INTERVAL '6 hours'
            ORDER BY
                CASE severity
                    WHEN 'high' THEN 1
                    WHEN 'medium' THEN 2
                    WHEN 'low' THEN 3
                    ELSE 4
                END
            LIMIT 1
        """),
        {"lat": lat, "lng": lng},
    )
    row = result.fetchone()
    if row:
        return {"severity": row.severity, "has_news": True}
    return {"severity": "none", "has_news": False}


async def evaluate_risk_for_property(property_row, db: AsyncSession) -> dict:
    """評估單一財產的風險"""
    lat, lng = property_row.lat, property_row.lng

    try:
        rainfall_data = await get_qpe_rainfall(lat, lng)
        rainfall_1hr = rainfall_data.get("rainfall_1hr", 0.0) or 0.0
    except Exception as e:
        logger.warning(f"雨量查詢失敗，使用 0：{e}")
        rainfall_1hr = 0.0

    flood_potential = property_row.flood_risk_level or 0
    news_signal = await get_news_signal_near(lat, lng, db)

    score = calculate_risk_score(
        rainfall_1hr=rainfall_1hr,
        flood_potential=flood_potential,
        news_severity=news_signal["severity"],
    )
    level = score_to_level(score)
    print(
        f"  rainfall_1hr={rainfall_1hr}, flood_potential={flood_potential}, news={news_signal['severity']} → score={score}, level={level}"
    )

    return {
        "property_id": property_row.id,
        "score": score,
        "level": level,
        "rainfall_1hr": rainfall_1hr,
        "flood_potential": flood_potential,
        "news_severity": news_signal["severity"],
    }


async def create_alert_if_needed(
    property_id, level: str, score: int, result: dict, db: AsyncSession
):
    """如果需要警報，寫進 alerts 表（防重複）"""
    if level == "safe":
        return

    existing = await db.execute(
        text("""
            SELECT id FROM alerts
            WHERE property_id = :pid
            AND level = :level
            AND created_at > NOW() - INTERVAL '6 hours'
            LIMIT 1
        """),
        {"pid": property_id, "level": level},
    )
    if existing.fetchone():
        return

    level_text = {
        "emergency": "緊急警報",
        "warning": "淹水警戒",
        "notice": "注意警示",
    }
    message = (
        f"{level_text.get(level, level)}："
        f"風險分數 {score} 分，"
        f"1小時雨量 {result['rainfall_1hr']:.1f}mm，"
        f"淹水潛勢等級 {result['flood_potential']}，"
        f"新聞訊號 {result['news_severity']}"
    )

    import json as _json

    await db.execute(
        text("""
            INSERT INTO alerts (id, property_id, level, message, triggered_by, created_at)
            VALUES (
                gen_random_uuid(),
                :property_id,
                :level,
                :message,
                CAST(:triggered_by AS jsonb),
                NOW()
            )
        """),
        {
            "property_id": str(property_id),
            "level": level,
            "message": message,
            "triggered_by": _json.dumps(
                {
                    "score": score,
                    "rainfall_1hr": result["rainfall_1hr"],
                    "news_severity": result["news_severity"],
                }
            ),
        },
    )


async def evaluate_all_properties():
    """排程用：遍歷所有財產，評估風險"""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            text("""
                SELECT id, name, location, flood_risk_level, user_id,
                       ST_Y(location::geometry) AS lat,
                       ST_X(location::geometry) AS lng
                FROM properties
                WHERE alert_enabled = true
            """)
        )
        properties = result.fetchall()

        if not properties:
            logger.info("沒有需要評估的財產")
            return

        logger.info(f"開始評估 {len(properties)} 個財產的風險")
        alert_count = 0

        for prop in properties:
            try:
                result = await evaluate_risk_for_property(prop, db)
                level = result["level"]

                if level != "safe":
                    await create_alert_if_needed(
                        prop.id, level, result["score"], result, db
                    )
                    alert_count += 1
                    logger.info(f"財產 {prop.name}：{level}（{result['score']} 分）")

            except Exception as e:
                print(f"財產 {prop.name} 評估失敗：{e}")
                logger.error(f"財產 {prop.name} 評估失敗：{e}")
                continue

        await db.commit()
        logger.info(f"風險評估完成，觸發 {alert_count} 個警報")
