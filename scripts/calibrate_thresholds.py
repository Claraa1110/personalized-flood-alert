import asyncio
from sqlalchemy import text
from app.database import AsyncSessionLocal

PCT_THRESHOLD = 0.6  # 60% 有效比例門檻

async def main():
    async with AsyncSessionLocal() as session:
        # 取得所有需要調降的地點
        result = await session.execute(text('''
            SELECT DISTINCT county_name, district_name
            FROM flood_events
            WHERE confidence = 'high'
            AND needs_adjustment = true
            AND rainfall_1h IS NOT NULL
            ORDER BY county_name, district_name
        '''))
        locations = result.fetchall()
        print(f'需要處理的地點：{len(locations)} 個鄉鎮')

        calibrated = 0

        for loc in locations:
            county = loc.county_name
            district = loc.district_name

            # 取得這個地點的所有事件
            result = await session.execute(text('''
                SELECT
                    rainfall_1h, rainfall_3h, rainfall_6h,
                    wra_threshold_1h, wra_threshold_3h, wra_threshold_6h
                FROM flood_events
                WHERE confidence = 'high'
                AND needs_adjustment = true
                AND rainfall_1h IS NOT NULL
                AND county_name = :county
                AND district_name = :district
            '''), {'county': county, 'district': district})
            events = result.fetchall()

            # 取得原始門檻（用第一筆）
            original_1h = events[0].wra_threshold_1h
            original_3h = events[0].wra_threshold_3h
            original_6h = events[0].wra_threshold_6h

            # 各時間尺度分別篩選 pct >= 60% 且 pct < 100% 的有效事件
            valid_1h = [
                e.rainfall_1h for e in events
                if e.wra_threshold_1h and
                PCT_THRESHOLD <= e.rainfall_1h / e.wra_threshold_1h < 1.0
            ]
            valid_3h = [
                e.rainfall_3h for e in events
                if e.wra_threshold_3h and
                PCT_THRESHOLD <= e.rainfall_3h / e.wra_threshold_3h < 1.0
            ]
            valid_6h = [
                e.rainfall_6h for e in events
                if e.wra_threshold_6h and
                PCT_THRESHOLD <= e.rainfall_6h / e.wra_threshold_6h < 1.0
            ]

            # 有效事件取最小值，無有效事件則維持原始門檻
            corrected_1h = round(min(valid_1h), 1) if valid_1h else original_1h
            corrected_3h = round(min(valid_3h), 1) if valid_3h else original_3h
            corrected_6h = round(min(valid_6h), 1) if valid_6h else original_6h

            # 計算 1H 調降幅度
            rate_1h = round(
                (original_1h - corrected_1h) / original_1h * 100, 1
            ) if corrected_1h != original_1h else 0.0

            await session.execute(text('''
                INSERT INTO corrected_thresholds
                    (county_name, district_name,
                     original_1h, original_3h, original_6h,
                     corrected_1h, corrected_3h, corrected_6h,
                     min_rainfall_1h, min_rainfall_3h, min_rainfall_6h,
                     event_count, adjustment_rate_1h)
                VALUES (
                    :county, :district,
                    :orig_1h, :orig_3h, :orig_6h,
                    :corr_1h, :corr_3h, :corr_6h,
                    :min_1h, :min_3h, :min_6h,
                    :count, :rate)
                ON CONFLICT (county_name, district_name)
                DO UPDATE SET
                    corrected_1h = EXCLUDED.corrected_1h,
                    corrected_3h = EXCLUDED.corrected_3h,
                    corrected_6h = EXCLUDED.corrected_6h,
                    min_rainfall_1h = EXCLUDED.min_rainfall_1h,
                    min_rainfall_3h = EXCLUDED.min_rainfall_3h,
                    min_rainfall_6h = EXCLUDED.min_rainfall_6h,
                    event_count = EXCLUDED.event_count,
                    adjustment_rate_1h = EXCLUDED.adjustment_rate_1h
            '''), {
                'county': county,
                'district': district,
                'orig_1h': original_1h,
                'orig_3h': original_3h,
                'orig_6h': original_6h,
                'corr_1h': corrected_1h,
                'corr_3h': corrected_3h,
                'corr_6h': corrected_6h,
                'min_1h': min(valid_1h) if valid_1h else None,
                'min_3h': min(valid_3h) if valid_3h else None,
                'min_6h': min(valid_6h) if valid_6h else None,
                'count': len(events),
                'rate': rate_1h,
            })

            print(f'  {county}{district}：'
                  f'1H {original_1h}→{corrected_1h}mm, '
                  f'3H {original_3h}→{corrected_3h}mm, '
                  f'6H {original_6h}→{corrected_6h}mm '
                  f'（{len(events)} 筆事件）')
            calibrated += 1

        await session.commit()
        print(f'\n校正完成！共處理 {calibrated} 個地點')


if __name__ == '__main__':
    asyncio.run(main())
