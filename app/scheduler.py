import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import text
from app.database import AsyncSessionLocal
from app.services.cwa_service import fetch_rainfall_stations

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def cleanup_old_data():
    """每天清理舊資料，只保留最近 48 小時"""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("""
                DELETE FROM rainfall_observations
                WHERE observed_at < NOW() - INTERVAL '48 hours'
            """))
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
        cleanup_old_data,
        "cron",
        hour=3,
        id="cleanup",
        replace_existing=True,
    )

    # TODO 第 5 週新增
    # scheduler.add_job(fetch_flood_alerts, 'interval', minutes=5)
    # scheduler.add_job(fetch_water_levels, 'interval', minutes=10)

    # TODO 第 6 週新增
    # scheduler.add_job(fetch_news, 'interval', hours=1)
    # scheduler.add_job(evaluate_risk, 'interval', minutes=10)

    return scheduler
