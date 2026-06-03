import asyncio
from app.database import AsyncSessionLocal
from app.services.threshold_service import get_applicable_threshold

async def main():
    print("開始測試警報觸發...\n")

    # 測試案例：高雄市前金區，模擬 1H=50mm 超過門檻
    test_cases = [
        {
            'name': '高雄市前金區財產',
            'lat': 22.6273,
            'lng': 120.3014,
            'mock_rainfall': {'1h': 50, '3h': 80, '6h': 120},
        },
        {
            'name': '台北市信義區財產',
            'lat': 25.0339,
            'lng': 121.5645,
            'mock_rainfall': {'1h': 30, '3h': 60, '6h': 90},
        },
    ]

    async with AsyncSessionLocal() as session:
        for case in test_cases:
            print(f"測試：{case['name']}")

            # 取得門檻
            threshold = await get_applicable_threshold(
                case['lat'], case['lng'], session
            )
            if not threshold:
                print("  找不到門檻，跳過\n")
                continue

            t1h = threshold.get('threshold_1h')
            t3h = threshold.get('threshold_3h')
            t6h = threshold.get('threshold_6h')
            source = threshold.get('source')

            print(f"  門檻（{source}）：1H={t1h}, 3H={t3h}, 6H={t6h}")
            print(f"  模擬雨量：1H={case['mock_rainfall']['1h']}, "
                  f"3H={case['mock_rainfall']['3h']}, "
                  f"6H={case['mock_rainfall']['6h']}")

            # 比對邏輯
            r1h = case['mock_rainfall']['1h']
            r3h = case['mock_rainfall']['3h']
            r6h = case['mock_rainfall']['6h']

            if t1h and r1h >= t1h:
                print(f"  → 觸發 1H 警報（{r1h}mm >= {t1h}mm）")
            elif t3h and r3h >= t3h:
                print(f"  → 觸發 3H 警報（{r3h}mm >= {t3h}mm）")
            elif t6h and r6h >= t6h:
                print(f"  → 觸發 6H 警報（{r6h}mm >= {t6h}mm）")
            else:
                print(f"  → 未觸發警報")
            print()

if __name__ == "__main__":
    asyncio.run(main())
