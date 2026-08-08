import json as _json
import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal
from app.services.threshold_service import get_two_tier_thresholds
from app.push import send_push_notifications

logger = logging.getLogger(__name__)

_PUSH_ADVICE: dict[str, dict[str, str]] = {
    "level2": {
        "house":     "留意積水，可準備擋水設施，貴重物品移至高處",
        "car":       "留意路況，考慮先將車輛移至高處",
        "shop":      "留意進水，可準備擋水設施，生財器具、貨物先墊高",
        "warehouse": "留意進水，庫存墊高、檢查排水",
        "farm":      "留意排水，檢查田間水路是否暢通",
    },
    "level1": {
        "house":     "緊急：一樓人員注意安全，切勿進入地下室",
        "car":       "緊急：立即移車，地下停車場請盡速駛離",
        "shop":      "緊急：關閉電源，人員撤離，遠離淹水區",
        "warehouse": "緊急：關閉電源總開關，人員撤離",
        "farm":      "緊急：注意人身安全，勿冒險巡田或搶收",
    },
}
_PUSH_ADVICE_DEFAULT = {
    "level2": "該地區可能有淹水風險，請留意天氣變化",
    "level1": "緊急：該地區已達警戒，請注意人身安全並遠離淹水區域",
}


def _get_push_advice(level: str, prop_type: str) -> str:
    return _PUSH_ADVICE.get(level, {}).get(prop_type) or _PUSH_ADVICE_DEFAULT.get(level, "")


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
    """取最近測站的官方 1H/3H/6H 雨量（直接讀氣象署 Past1hr/3hr/6hr）"""
    result = await db.execute(text("""
        SELECT rainfall_1hr, rainfall_3hr, rainfall_6hr
        FROM rainfall_observations
        WHERE observed_at >= NOW() - INTERVAL '2 hours'
          AND ST_DWithin(location, ST_MakePoint(:lng, :lat)::geography, 50000)
        ORDER BY observed_at DESC,
                 ST_Distance(location, ST_MakePoint(:lng, :lat)::geography)
        LIMIT 1
    """), {"lat": lat, "lng": lng})
    row = result.fetchone()
    if not row:
        return {"rainfall_1hr": 0.0, "rainfall_3hr": 0.0, "rainfall_6hr": 0.0}
    return {
        "rainfall_1hr": float(row.rainfall_1hr or 0),
        "rainfall_3hr": float(row.rainfall_3hr or 0),
        "rainfall_6hr": float(row.rainfall_6hr or 0),
    }


async def evaluate_all_properties():
    """排程用：遍歷所有財產，依兩級門檻評估風險並發送警報"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("""
            SELECT id, user_id, name, district_name, type, custom_type_name,
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
        pending_pushes: list[dict] = []  # 收集待推播，commit 後統一送

        for prop in properties:
            try:
                thresholds = await get_two_tier_thresholds(prop.lat, prop.lng, session)
                if not thresholds:
                    continue

                t1 = thresholds['thresholds']['level1']
                t2 = thresholds['thresholds']['level2']
                level2_source = thresholds['level2_source']

                rainfall = await get_rainfall_for_location(prop.lat, prop.lng, session)
                r1h = rainfall['rainfall_1hr']
                r3h = rainfall['rainfall_3hr']
                r6h = rainfall['rainfall_6hr']

                print(f"財產 {prop.id}（{prop.name}）")
                print(f"  一級門檻：1H={t1['1h']}, 3H={t1['3h']}, 6H={t1['6h']}")
                print(f"  二級門檻：1H={t2['1h']}, 3H={t2['3h']}, 6H={t2['6h']} (來源:{level2_source})")
                print(f"  雨量：1H={r1h}, 3H={r3h}, 6H={r6h}")

                triggered_level = None
                triggered_scale = None
                triggered_actual = None
                triggered_threshold = None

                # 先查一級警戒（紅）
                for scale, actual, thresh in [
                    ('1H', r1h, t1['1h']),
                    ('3H', r3h, t1['3h']),
                    ('6H', r6h, t1['6h']),
                ]:
                    if thresh and actual and actual >= thresh:
                        triggered_level = 'level1'
                        triggered_scale = scale
                        triggered_actual = actual
                        triggered_threshold = thresh
                        break

                # 未達一級，再查二級預警（黃）
                if not triggered_level:
                    for scale, actual, thresh in [
                        ('1H', r1h, t2['1h']),
                        ('3H', r3h, t2['3h']),
                        ('6H', r6h, t2['6h']),
                    ]:
                        if thresh and actual and actual >= thresh:
                            triggered_level = 'level2'
                            triggered_scale = scale
                            triggered_actual = actual
                            triggered_threshold = thresh
                            break

                if not triggered_level:
                    print(f"  → 未觸發警報")
                    continue

                level_label = '一級警戒' if triggered_level == 'level1' else '二級預警'
                threshold_label = '警戒值' if triggered_level == 'level1' else '預警值'
                print(f"  → 觸發 {level_label}（{triggered_scale}）")

                # 每個等級各自在 1 小時內不重複發送
                existing = await session.execute(text("""
                    SELECT id FROM alerts
                    WHERE property_id = :pid
                    AND level = :level
                    AND created_at > NOW() - INTERVAL '1 hour'
                    LIMIT 1
                """), {'pid': str(prop.id), 'level': triggered_level})
                if existing.fetchone():
                    print(f"  → {level_label} 警報已在 1 小時內發送，跳過")
                    continue

                msg = (
                    f'【{prop.name}】達{level_label} {triggered_scale} '
                    f'雨量 {triggered_actual}mm（已達{threshold_label} {triggered_threshold}mm）'
                )
                await session.execute(text("""
                    INSERT INTO alerts
                        (id, property_id, level, message, triggered_by, created_at)
                    VALUES (
                        gen_random_uuid(), :pid, :level, :msg,
                        CAST(:triggered_by AS jsonb), NOW()
                    )
                """), {
                    'pid': str(prop.id),
                    'level': triggered_level,
                    'msg': msg,
                    'triggered_by': _json.dumps({
                        'scale': triggered_scale,
                        'actual_mm': triggered_actual,
                        'threshold_mm': triggered_threshold,
                        'level2_source': level2_source,
                    }),
                })
                alert_count += 1
                logger.info(f"財產 {prop.name}：{level_label} 觸發（{triggered_scale}）")
                pending_pushes.append({
                    "user_id": str(prop.user_id),
                    "level": triggered_level,
                    "name": prop.name,
                    "district": prop.district_name or "",
                    "type": getattr(prop, "type", "custom") or "custom",
                })

            except Exception as e:
                logger.error(f"財產 {prop.name} 評估失敗：{e}")
                continue

        await session.commit()
        logger.info(f"風險評估完成，觸發 {alert_count} 個警報")

        # commit 後送推播（不影響警報記錄）
        for push in pending_pushes:
            try:
                # 查通知偏好，預設都開啟
                pref_row = await session.execute(
                    text("SELECT notify_enabled, sound_enabled FROM user_notification_settings WHERE user_id = :uid"),
                    {"uid": push["user_id"]},
                )
                pref = pref_row.fetchone()
                notify_enabled = pref.notify_enabled if pref else True
                sound_enabled = pref.sound_enabled if pref else True

                if not notify_enabled:
                    logger.info(f"使用者 {push['user_id']} 已關閉推播，跳過")
                    continue

                token_rows = await session.execute(
                    text("SELECT push_token FROM push_tokens WHERE user_id = :uid"),
                    {"uid": push["user_id"]},
                )
                tokens = [r.push_token for r in token_rows.fetchall()]
                if not tokens:
                    continue

                # 計算該使用者目前有幾個財產在警戒中（作為 app icon badge 數字）
                badge_row = await session.execute(text("""
                    SELECT COUNT(DISTINCT a.property_id) AS cnt
                    FROM alerts a
                    JOIN properties p ON a.property_id = p.id
                    WHERE p.user_id = :uid
                    AND a.level IN ('level1', 'level2')
                    AND a.created_at > NOW() - INTERVAL '6 hours'
                """), {"uid": push["user_id"]})
                badge = int((badge_row.fetchone() or (1,))[0]) or 1

                advice_text = _get_push_advice(push["level"], push["type"])
                if push["level"] == "level1":
                    title = f"🚨 【{push['name']}】警戒"
                    body = f"{push['district']} · {advice_text}" if push["district"] else advice_text
                else:
                    title = f"⚠️ 【{push['name']}】注意"
                    body = f"{push['district']} · {advice_text}" if push["district"] else advice_text

                sound = "default" if sound_enabled else None
                await send_push_notifications(tokens, title, body, badge=badge, sound=sound)
            except Exception as e:
                logger.warning(f"推播發送例外（{push['name']}）: {e}")
