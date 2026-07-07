import json as _json
import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal
from app.services.threshold_service import get_applicable_threshold

logger = logging.getLogger(__name__)


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


async def get_rainfall_for_location(lat: float, lng: float, db: AsyncSession) -> dict:
    """計算指定座標最近測站的 1H/3H/6H 累積雨量"""
    result = await db.execute(text("""
        WITH nearest AS (
            SELECT station_id
            FROM rainfall_observations
            WHERE observed_at >= NOW() - INTERVAL '1 hour'
            ORDER BY ST_Distance(location, ST_MakePoint(:lng, :lat)::geography)
            LIMIT 1
        ),
        hourly_1h AS (
            SELECT MAX(rainfall_mm) AS hourly_rainfall
            FROM rainfall_observations
            WHERE station_id = (SELECT station_id FROM nearest)
            AND observed_at >= NOW() - INTERVAL '1 hour'
            GROUP BY DATE_TRUNC('hour', observed_at)
        ),
        hourly_3h AS (
            SELECT DATE_TRUNC('hour', observed_at) AS hour,
                   MAX(rainfall_mm) AS hourly_rainfall
            FROM rainfall_observations
            WHERE station_id = (SELECT station_id FROM nearest)
            AND observed_at >= NOW() - INTERVAL '3 hours'
            GROUP BY DATE_TRUNC('hour', observed_at)
        ),
        hourly_6h AS (
            SELECT DATE_TRUNC('hour', observed_at) AS hour,
                   MAX(rainfall_mm) AS hourly_rainfall
            FROM rainfall_observations
            WHERE station_id = (SELECT station_id FROM nearest)
            AND observed_at >= NOW() - INTERVAL '6 hours'
            GROUP BY DATE_TRUNC('hour', observed_at)
        )
        SELECT
            COALESCE((SELECT SUM(hourly_rainfall) FROM hourly_1h), 0) AS rainfall_1hr,
            COALESCE((SELECT SUM(hourly_rainfall) FROM hourly_3h), 0) AS rainfall_3hr,
            COALESCE((SELECT SUM(hourly_rainfall) FROM hourly_6h), 0) AS rainfall_6hr
    """), {"lat": lat, "lng": lng})
    row = result.fetchone()
    if not row:
        return {"rainfall_1hr": 0.0, "rainfall_3hr": 0.0, "rainfall_6hr": 0.0}
    return {
        "rainfall_1hr": float(row.rainfall_1hr),
        "rainfall_3hr": float(row.rainfall_3hr),
        "rainfall_6hr": float(row.rainfall_6hr),
    }


async def evaluate_all_properties():
    """排程用：遍歷所有財產，用校正後門檻評估風險"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("""
            SELECT id, name,
                   ST_Y(location::geometry) AS lat,
                   ST_X(location::geometry) AS lng
            FROM properties
            WHERE alert_enabled = true
            AND location IS NOT NULL
        """))
        properties = result.fetchall()

        if not properties:
            logger.info("沒有需要評估的財產")
            return

        logger.info(f"開始評估 {len(properties)} 個財產的風險")
        alert_count = 0

        for prop in properties:
            try:
                threshold = await get_applicable_threshold(prop.lat, prop.lng, session)
                if not threshold:
                    continue

                t1h = threshold.get('threshold_1h')
                t3h = threshold.get('threshold_3h')
                t6h = threshold.get('threshold_6h')
                source = threshold.get('source', 'original')

                rainfall = await get_rainfall_for_location(prop.lat, prop.lng, session)
                rainfall_1hr = rainfall['rainfall_1hr']
                rainfall_3hr = rainfall['rainfall_3hr']
                rainfall_6hr = rainfall['rainfall_6hr']

                print(f"財產 {prop.id}（{prop.name}）")
                print(f"  門檻：1H={t1h}, 3H={t3h}, 6H={t6h}, 來源={source}")
                print(f"  雨量：1H={rainfall_1hr}, 3H={rainfall_3hr}, 6H={rainfall_6hr}")

                is_alert = False
                triggered_scale = None

                if t1h and rainfall_1hr and rainfall_1hr >= t1h:
                    print(f"  → 觸發 1H 警報")
                    is_alert = True
                    triggered_scale = f'1H（{rainfall_1hr}mm >= {t1h}mm）'
                elif t3h and rainfall_3hr and rainfall_3hr >= t3h:
                    print(f"  → 觸發 3H 警報")
                    is_alert = True
                    triggered_scale = f'3H（{rainfall_3hr}mm >= {t3h}mm）'
                elif t6h and rainfall_6hr and rainfall_6hr >= t6h:
                    print(f"  → 觸發 6H 警報")
                    is_alert = True
                    triggered_scale = f'6H（{rainfall_6hr}mm >= {t6h}mm）'
                else:
                    print(f"  → 未觸發警報")

                if is_alert:
                    existing = await session.execute(text("""
                        SELECT id FROM alerts
                        WHERE property_id = :pid
                        AND level = 'warning'
                        AND created_at > NOW() - INTERVAL '6 hours'
                        LIMIT 1
                    """), {"pid": str(prop.id)})
                    if not existing.fetchone():
                        msg = f'【{prop.name}】雨量超過警戒門檻 {triggered_scale}（門檻來源：{source}）'
                        await session.execute(text("""
                            INSERT INTO alerts
                                (id, property_id, level, message, triggered_by, created_at)
                            VALUES (
                                gen_random_uuid(), :pid, 'warning', :msg,
                                CAST(:triggered_by AS jsonb), NOW()
                            )
                        """), {
                            'pid': str(prop.id),
                            'msg': msg,
                            'triggered_by': _json.dumps({
                                'triggered_scale': triggered_scale,
                                'source': source,
                            }),
                        })
                        alert_count += 1
                        logger.info(f"財產 {prop.name}：超過門檻 {triggered_scale}")

            except Exception as e:
                logger.error(f"財產 {prop.name} 評估失敗：{e}")
                continue

        await session.commit()
        logger.info(f"風險評估完成，觸發 {alert_count} 個警報")
