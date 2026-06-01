from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def get_applicable_threshold(
    lat: float,
    lng: float,
    session: AsyncSession
) -> dict | None:
    """
    給定座標，回傳該地點的適用門檻。
    優先用校正後門檻，沒有才用 WRA 原始門檻。
    """

    # Step 1：用座標找鄉鎮市區
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

    # Step 2：查校正後門檻
    result = await session.execute(text('''
        SELECT
            county_name, district_name,
            corrected_1h as threshold_1h,
            corrected_3h as threshold_3h,
            corrected_6h as threshold_6h,
            original_1h, original_3h, original_6h,
            'corrected' as source
        FROM corrected_thresholds
        WHERE district_name = :district
        AND county_name = :county
        LIMIT 1
    '''), {
        'district': district.town_name,
        'county': district.county_name,
    })
    threshold = result.fetchone()
    if threshold:
        return dict(threshold._mapping)

    # Step 3：沒有校正門檻，用 WRA 原始門檻
    result = await session.execute(text('''
        SELECT
            district_name,
            MIN(threshold_1h_lv2) as threshold_1h,
            MIN(threshold_3h_lv2) as threshold_3h,
            MIN(threshold_6h_lv2) as threshold_6h,
            'original' as source
        FROM wra_alert_thresholds
        WHERE district_name = :district
        GROUP BY district_name
        LIMIT 1
    '''), {'district': district.town_name})
    threshold = result.fetchone()
    if threshold:
        return dict(threshold._mapping)

    return None
