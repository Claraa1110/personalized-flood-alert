import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import text
from app.database import AsyncSessionLocal
from app.services.cwa_service import fetch_rainfall_stations
from app.services.risk_engine import evaluate_all_properties
from app.utils import TAIPEI

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


async def cleanup_old_data():
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(
                text("""
                DELETE FROM rainfall_observations
                WHERE observed_at < (NOW() AT TIME ZONE 'Asia/Taipei') - INTERVAL '48 hours'
            """)
            )
            await session.commit()
            logger.info("舊資料清理完成")
    except Exception as e:
        logger.error(f"資料清理失敗：{e}")


def setup_scheduler():
    scheduler.add_job(
        fetch_rainfall_stations,
        "interval",
        minutes=10,
        id="fetch_rainfall",
        replace_existing=True,
        max_instances=1,
    )

    scheduler.add_job(
        evaluate_all_properties,
        "interval",
        minutes=10,
        id="evaluate_risk",
        replace_existing=True,
        max_instances=1,
    )

    # 僅此 job 指定時區：容器時區為 UTC，不指定的話會在臺北時間 11:00 執行。
    # 這裡只設定單一 job 的 trigger 時區，不影響 scheduler 全域設定與其他 job。
    scheduler.add_job(
        cleanup_old_data,
        "cron",
        hour=3,
        timezone=TAIPEI,
        id="cleanup",
        replace_existing=True,
    )

    return scheduler
