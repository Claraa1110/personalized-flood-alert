"""
Test QPE grid rainfall lookup by coordinate.
Usage: PYTHONPATH=. uv run python scripts/test_qpe_lookup.py
"""

import asyncio
from app.services.cwa_service import get_qpe_rainfall


async def test():
    result = await get_qpe_rainfall(25.0339, 121.5645)
    print("台北 101:", result)

    result = await get_qpe_rainfall(22.6318, 120.2986)
    print("高雄:", result)

    result = await get_qpe_rainfall(35.0, 135.0)
    print("日本（超出範圍）:", result)


if __name__ == "__main__":
    asyncio.run(test())
