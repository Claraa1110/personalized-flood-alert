import asyncio
from sqlalchemy import text
from app.database import AsyncSessionLocal


async def match_threshold_for_event(session, event):
    # 第一優先：座標 ST_Within → 村里 → 門檻
    result = await session.execute(text('''
        SELECT
            t.threshold_1h_lv2, t.threshold_1h_lv1,
            t.threshold_3h_lv2, t.threshold_3h_lv1,
            t.threshold_6h_lv2, t.threshold_6h_lv1,
            v.village_name, :m1 as method
        FROM villages v
        JOIN wra_alert_thresholds t
            ON t.area_name = v.village_name
            AND t.district_name = v.district_name
        WHERE ST_Within(
            ST_MakePoint(:lng, :lat)::geography::geometry,
            v.geometry::geometry
        )
        LIMIT 1
    '''), {'lat': event.lat, 'lng': event.lng, 'm1': '第一優先'})
    row = result.fetchone()
    if row and row.threshold_1h_lv2:
        return row

    # 第二優先：village_name 直接 JOIN
    if event.village_name:
        result = await session.execute(text('''
            SELECT
                threshold_1h_lv2, threshold_1h_lv1,
                threshold_3h_lv2, threshold_3h_lv1,
                threshold_6h_lv2, threshold_6h_lv1,
                area_name as village_name, :m2 as method
            FROM wra_alert_thresholds
            WHERE area_name = :village
            AND district_name = :district
            LIMIT 1
        '''), {
            'village': event.village_name,
            'district': event.district_name,
            'm2': '第二優先',
        })
        row = result.fetchone()
        if row and row.threshold_1h_lv2:
            return row

    # 第三優先：鄉鎮最嚴格門檻
    if event.district_name:
        result = await session.execute(text('''
            SELECT
                MIN(threshold_1h_lv2) as threshold_1h_lv2,
                MIN(threshold_1h_lv1) as threshold_1h_lv1,
                MIN(threshold_3h_lv2) as threshold_3h_lv2,
                MIN(threshold_3h_lv1) as threshold_3h_lv1,
                MIN(threshold_6h_lv2) as threshold_6h_lv2,
                MIN(threshold_6h_lv1) as threshold_6h_lv1,
                :district as village_name, :m3 as method
            FROM wra_alert_thresholds
            WHERE district_name = :district
        '''), {
            'district': event.district_name,
            'm3': '第三優先',
        })
        row = result.fetchone()
        if row and row.threshold_1h_lv2:
            return row

    return None


async def main():
    async with AsyncSessionLocal() as session:
        result = await session.execute(text('''
            SELECT id, lat, lng, county_name, district_name, village_name
            FROM flood_events
            WHERE confidence = 'high'
            AND rainfall_1h IS NOT NULL
            ORDER BY id
        '''))
        events = result.fetchall()
        print(f'共 {len(events)} 個事件需要對應門檻')

        success = 0
        failed = 0
        method_count = {}

        for event in events:
            threshold = await match_threshold_for_event(session, event)

            if not threshold:
                print(f'  事件 {event.id}（{event.district_name}）：找不到門檻')
                failed += 1
                continue

            await session.execute(text('''
                UPDATE flood_events
                SET wra_threshold_1h = :t1h,
                    wra_threshold_3h = :t3h,
                    wra_threshold_6h = :t6h
                WHERE id = :id
            '''), {
                't1h': threshold.threshold_1h_lv2,
                't3h': threshold.threshold_3h_lv2,
                't6h': threshold.threshold_6h_lv2,
                'id': event.id,
            })

            method = threshold.method
            method_count[method] = method_count.get(method, 0) + 1
            success += 1
            print(f'  事件 {event.id}（{event.district_name}）：'
                  f'1H門檻={threshold.threshold_1h_lv2}mm [{method}]')

        await session.commit()
        print(f'\n完成！成功：{success}，失敗：{failed}')
        print(f'對應方法分布：{method_count}')


if __name__ == '__main__':
    asyncio.run(main())
