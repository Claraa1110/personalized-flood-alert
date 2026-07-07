import asyncio
from app.services.risk_engine import evaluate_all_properties

async def main():
    print("開始測試警報觸發（真實雨量）...\n")
    await evaluate_all_properties()
    print("\n完成！")

if __name__ == "__main__":
    asyncio.run(main())
