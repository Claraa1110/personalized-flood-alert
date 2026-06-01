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
    """給定座標，查詢適用的門檻（校正後或原始）"""
    from app.services.threshold_service import get_applicable_threshold
    threshold = await get_applicable_threshold(lat, lng, db)
    if not threshold:
        return {'error': '找不到對應門檻'}
    return threshold
