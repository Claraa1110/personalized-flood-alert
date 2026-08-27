from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db
from app.auth import get_device_id

router = APIRouter()

# ─── Advice texts (mirrors advice.ts) ────────────────────────────────────────

_ADVICE: dict[str, dict[str, str]] = {
    'level2': {
        'house':     '留意積水，可準備擋水設施，貴重物品移至高處',
        'car':       '留意路況，考慮先將車輛移至高處',
        'shop':      '留意進水，可準備擋水設施，生財器具、貨物先墊高',
        'warehouse': '留意進水，庫存墊高、檢查排水',
        'farm':      '留意排水，檢查田間水路是否暢通',
    },
    'level1': {
        'house':     '緊急：一樓人員注意安全，切勿進入地下室',
        'car':       '緊急：立即移車，地下停車場請盡速駛離',
        'shop':      '緊急：關閉電源，人員撤離，遠離淹水區',
        'warehouse': '緊急：關閉電源總開關，人員撤離',
        'farm':      '緊急：注意人身安全，勿冒險巡田或搶收',
    },
}
_ADVICE_DEFAULT = {
    'level2': '該地區可能有淹水風險，請留意天氣變化',
    'level1': '緊急：該地區已達警戒，請注意人身安全並遠離淹水區域',
}


def _get_advice(level: str, prop_type: str) -> str | None:
    if level == 'safe':
        return None
    return _ADVICE.get(level, {}).get(prop_type) or _ADVICE_DEFAULT.get(level)


def _f(v) -> float | None:
    return float(v) if v is not None else None


def _evaluate(r1h: float, r3h: float, r6h: float,
               t1: dict, t2: dict) -> tuple[str, float]:
    """Return (level, risk_pct). risk_pct = max rainfall as % of level2 threshold."""
    for actual, key in [(r1h, '1h'), (r3h, '3h'), (r6h, '6h')]:
        thresh = t1.get(key)
        if thresh and actual >= thresh:
            pct = _max_pct(r1h, r3h, r6h, t2)
            return 'level1', max(pct, 100.0)

    for actual, key in [(r1h, '1h'), (r3h, '3h'), (r6h, '6h')]:
        thresh = t2.get(key)
        if thresh and actual >= thresh:
            return 'level2', _max_pct(r1h, r3h, r6h, t2)

    return 'safe', _max_pct(r1h, r3h, r6h, t2)


def _max_pct(r1h: float, r3h: float, r6h: float, t2: dict) -> float:
    pcts = []
    for actual, key in [(r1h, '1h'), (r3h, '3h'), (r6h, '6h')]:
        thresh = t2.get(key)
        if thresh:
            pcts.append(actual / thresh * 100)
    return max(pcts) if pcts else 0.0


# ─── Endpoint ─────────────────────────────────────────────────────────────────

@router.get("/properties-with-risk")
async def get_properties_with_risk(
    db: AsyncSession = Depends(get_db),
    device_id: str = Depends(get_device_id),
):
    # ── Query 1: 所有財產 + 行政區 LATERAL ───────────────────────────────────
    props_rows = (await db.execute(text("""
        SELECT
            p.id, p.name, p.type, p.custom_type_name,
            p.address, p.district_name, p.alert_enabled, p.priority_stars,
            ST_Y(p.location::geometry) AS lat,
            ST_X(p.location::geometry) AS lng,
            d.town_name, d.county_name
        FROM properties p
        LEFT JOIN LATERAL (
            SELECT town_name, county_name FROM districts
            WHERE ST_Within(
                ST_SetSRID(p.location::geometry, 4326),
                geometry::geometry
            )
            LIMIT 1
        ) d ON true
        WHERE p.device_id = :device_id
    """), {"device_id": device_id})).fetchall()

    if not props_rows:
        return []

    # ── Query 2: 各財產雨量 ────────────────────────────────────────────────
    rainfall_rows = (await db.execute(text("""
        SELECT
            p.id AS property_id,
            COALESCE(r.rainfall_1hr, 0) AS r1h,
            COALESCE(r.rainfall_3hr, 0) AS r3h,
            COALESCE(r.rainfall_6hr, 0) AS r6h
        FROM properties p
        LEFT JOIN LATERAL (
            SELECT rainfall_1hr, rainfall_3hr, rainfall_6hr
            FROM rainfall_observations
            WHERE observed_at >= NOW() - INTERVAL '2 hours'
              AND ST_DWithin(location, p.location, 50000)
            ORDER BY observed_at DESC, ST_Distance(location, p.location)
            LIMIT 1
        ) r ON true
        WHERE p.device_id = :device_id
    """), {"device_id": device_id})).fetchall()

    rainfall_map = {str(row.property_id): row for row in rainfall_rows}

    # ── Query 3 & 4: 批次查門檻 ───────────────────────────────────────────────
    towns = list({p.town_name for p in props_rows if p.town_name})
    wra_map: dict[str, dict] = {}
    corrected_map: dict[str, dict] = {}

    if towns:
        for row in (await db.execute(text("""
            SELECT district_name,
                MIN(threshold_1h_lv1) AS lv1_1h, MIN(threshold_3h_lv1) AS lv1_3h, MIN(threshold_6h_lv1) AS lv1_6h,
                MIN(threshold_1h_lv2) AS lv2_1h, MIN(threshold_3h_lv2) AS lv2_3h, MIN(threshold_6h_lv2) AS lv2_6h
            FROM wra_alert_thresholds
            WHERE district_name = ANY(:towns)
            GROUP BY district_name
        """), {"towns": towns})).fetchall():
            wra_map[row.district_name] = {
                'l1': {'1h': _f(row.lv1_1h), '3h': _f(row.lv1_3h), '6h': _f(row.lv1_6h)},
                'l2': {'1h': _f(row.lv2_1h), '3h': _f(row.lv2_3h), '6h': _f(row.lv2_6h)},
            }

        for row in (await db.execute(text("""
            SELECT county_name, district_name,
                corrected_1h, corrected_3h, corrected_6h
            FROM corrected_thresholds
            WHERE district_name = ANY(:towns)
        """), {"towns": towns})).fetchall():
            key = f"{row.county_name}|{row.district_name}"
            corrected_map[key] = {
                '1h': _f(row.corrected_1h),
                '3h': _f(row.corrected_3h),
                '6h': _f(row.corrected_6h),
            }

    # ── Compute risk per property ──────────────────────────────────────────────
    results = []
    for p in props_rows:
        rain = rainfall_map.get(str(p.id))
        r1h = float(rain.r1h) if rain else 0.0
        r3h = float(rain.r3h) if rain else 0.0
        r6h = float(rain.r6h) if rain else 0.0

        wra = wra_map.get(p.town_name) if p.town_name else None
        t1 = {k: v for k, v in (wra['l1'] if wra else {}).items() if v is not None}

        corrected_key = f"{p.county_name}|{p.town_name}" if p.town_name else None
        corrected = corrected_map.get(corrected_key) if corrected_key else None

        if corrected:
            raw_t2 = {k: v for k, v in corrected.items() if v is not None}
            t2 = {}
            for scale in ('1h', '3h', '6h'):
                c = raw_t2.get(scale)
                l1 = t1.get(scale)
                if c is not None and l1 is not None and c >= l1:
                    wra_l2 = (wra['l2'] if wra else {}).get(scale)
                    t2[scale] = wra_l2
                else:
                    t2[scale] = c
            t2 = {k: v for k, v in t2.items() if v is not None}
        elif wra:
            t2 = {k: v for k, v in wra['l2'].items() if v is not None}
        else:
            t2 = {}

        prop_type = (p.type or 'custom')
        level, risk_pct = _evaluate(r1h, r3h, r6h, t1, t2)

        results.append({
            'id': str(p.id),
            'name': p.name,
            'type': prop_type,
            'custom_type_name': p.custom_type_name,
            'address': p.address,
            'district_name': p.district_name,
            'latitude': float(p.lat),
            'longitude': float(p.lng),
            'rainfall': {'1h': r1h, '3h': r3h, '6h': r6h},
            'level': level,
            'risk_action': _get_advice(level, prop_type),
            'risk_pct': round(risk_pct, 1),
            'priority_stars': int(p.priority_stars) if p.priority_stars is not None else 3,
        })

    return results
