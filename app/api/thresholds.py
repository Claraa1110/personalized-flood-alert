from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.dependencies import get_db

router = APIRouter()


@router.get("/corrected-thresholds")
async def get_corrected_thresholds(
    db: AsyncSession = Depends(get_db),
):
    """查詢所有校正後門檻"""
    result = await db.execute(text('''
        SELECT
            county_name, district_name,
            original_1h, corrected_1h,
            original_3h, corrected_3h,
            original_6h, corrected_6h,
            event_count,
            adjustment_rate_1h
        FROM corrected_thresholds
        ORDER BY county_name, district_name
    '''))
    rows = result.fetchall()
    return {
        'total': len(rows),
        'thresholds': [dict(row._mapping) for row in rows]
    }


@router.get("/threshold")
async def get_threshold_by_location(
    lat: float = Query(..., description="緯度"),
    lng: float = Query(..., description="經度"),
    db: AsyncSession = Depends(get_db),
):
    """給定座標，查詢兩級警戒門檻、當前雨量及風險等級（safe / level2 / level1）"""
    from app.services.threshold_service import get_two_tier_thresholds
    from app.services.risk_engine import get_rainfall_for_location

    thresholds = await get_two_tier_thresholds(lat, lng, db)
    if not thresholds:
        return {'error': '找不到對應門檻'}

    rainfall = await get_rainfall_for_location(lat, lng, db)
    r1h = rainfall['rainfall_1hr']
    r3h = rainfall['rainfall_3hr']
    r6h = rainfall['rainfall_6hr']

    t1 = thresholds['thresholds']['level1']
    t2 = thresholds['thresholds']['level2']

    # 先判一級警戒，再判二級預警
    level = 'safe'
    for actual, thresh in [(r1h, t1['1h']), (r3h, t1['3h']), (r6h, t1['6h'])]:
        if thresh and actual and actual >= thresh:
            level = 'level1'
            break

    if level == 'safe':
        for actual, thresh in [(r1h, t2['1h']), (r3h, t2['3h']), (r6h, t2['6h'])]:
            if thresh and actual and actual >= thresh:
                level = 'level2'
                break

    return {
        'district_name': thresholds['district_name'],
        'level': level,
        'level2_source': thresholds['level2_source'],
        'thresholds': thresholds['thresholds'],
        'current_rainfall': {
            '1h': r1h,
            '3h': r3h,
            '6h': r6h,
        },
    }
