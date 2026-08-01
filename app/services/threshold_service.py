import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def get_two_tier_thresholds(
    lat: float,
    lng: float,
    session: AsyncSession,
) -> dict | None:
    """
    給定座標，回傳兩級警戒門檻：
    - level2（二級預警）: 優先使用校正門檻，否則用 WRA lv2
    - level1（一級警戒）: 一律使用 WRA lv1
    """
    # Step 1：找行政區
    result = await session.execute(text('''
        SELECT town_name, county_name
        FROM districts
        WHERE ST_Within(
            ST_MakePoint(:lng, :lat)::geography::geometry,
            geometry::geometry
        )
        LIMIT 1
    '''), {'lat': lat, 'lng': lng})
    district = result.fetchone()
    if not district:
        return None

    town_name = district.town_name
    county_name = district.county_name

    # Step 2：查 WRA 官方門檻（lv1 & lv2 都需要）
    result = await session.execute(text('''
        SELECT
            MIN(threshold_1h_lv1) AS lv1_1h,
            MIN(threshold_3h_lv1) AS lv1_3h,
            MIN(threshold_6h_lv1) AS lv1_6h,
            MIN(threshold_1h_lv2) AS lv2_1h,
            MIN(threshold_3h_lv2) AS lv2_3h,
            MIN(threshold_6h_lv2) AS lv2_6h
        FROM wra_alert_thresholds
        WHERE district_name = :district
    '''), {'district': town_name})
    wra = result.fetchone()

    if not wra or wra.lv1_1h is None:
        return None

    level1 = {
        '1h': float(wra.lv1_1h),
        '3h': float(wra.lv1_3h) if wra.lv1_3h is not None else None,
        '6h': float(wra.lv1_6h) if wra.lv1_6h is not None else None,
    }

    # Step 3：查校正門檻（供 level2 使用）
    result = await session.execute(text('''
        SELECT corrected_1h, corrected_3h, corrected_6h
        FROM corrected_thresholds
        WHERE district_name = :district
        AND county_name = :county
        LIMIT 1
    '''), {'district': town_name, 'county': county_name})
    corrected = result.fetchone()

    if corrected and corrected.corrected_1h is not None:
        level2 = {
            '1h': float(corrected.corrected_1h),
            '3h': float(corrected.corrected_3h) if corrected.corrected_3h is not None else None,
            '6h': float(corrected.corrected_6h) if corrected.corrected_6h is not None else None,
        }
        level2_source = 'corrected'
    else:
        level2 = {
            '1h': float(wra.lv2_1h) if wra.lv2_1h is not None else None,
            '3h': float(wra.lv2_3h) if wra.lv2_3h is not None else None,
            '6h': float(wra.lv2_6h) if wra.lv2_6h is not None else None,
        }
        level2_source = 'original'

    # 防呆：level2 門檻不應 >= level1 門檻，異常時 fallback 至 WRA lv2
    for scale in ('1h', '3h', '6h'):
        l2 = level2[scale]
        l1 = level1[scale]
        if l2 is not None and l1 is not None and l2 >= l1:
            logger.warning(
                f"[threshold] {county_name}{town_name} {scale}: "
                f"level2({l2}) >= level1({l1})，校正門檻異常，改用 WRA lv2"
            )
            wra_lv2 = getattr(wra, f'lv2_{scale}')
            level2[scale] = float(wra_lv2) if wra_lv2 is not None else None

    return {
        'district_name': town_name,
        'county_name': county_name,
        'level2_source': level2_source,
        'thresholds': {
            'level1': level1,
            'level2': level2,
        },
    }
