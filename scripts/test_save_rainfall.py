"""
Test fetching and saving CWA rainfall station data.
Usage: uv run python scripts/test_save_rainfall.py
"""
import asyncio
from app.services.cwa_service import fetch_rainfall_stations

if __name__ == "__main__":
    asyncio.run(fetch_rainfall_stations())
