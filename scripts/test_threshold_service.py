import asyncio
from app.database import AsyncSessionLocal
from app.services.threshold_service import get_applicable_threshold

async def main():
    test_cases = [
        # (lat, lng, 描述)
        (22.8051, 120.2979, "高雄市仁武區（有校正門檻）"),
        (23.4518, 120.3833, "嘉義縣水上鄉（有校正門檻）"),
        (25.0339, 121.5645, "台北市信義區（無校正門檻，用 WRA 原始）"),
        (22.6499, 120.3179, "高雄市三民區（有校正門檻）"),
    ]

    async with AsyncSessionLocal() as session:
        for lat, lng, desc in test_cases:
            result = await get_applicable_threshold(lat, lng, session)
            if result:
                print(f"\n{desc}")
                print(f"  來源：{result['source']}")
                print(f"  1H 門檻：{result['threshold_1h']}mm")
                print(f"  3H 門檻：{result['threshold_3h']}mm")
                print(f"  6H 門檻：{result['threshold_6h']}mm")
            else:
                print(f"\n{desc}")
                print("  找不到門檻")

if __name__ == "__main__":
    asyncio.run(main())
