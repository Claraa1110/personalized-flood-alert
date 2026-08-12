import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from dotenv import load_dotenv
from app.api.test import router as test_router
from app.api.properties import router as properties_router
from app.api.location import router as location_router
from app.api.rainfall import router as rainfall_router
from app.api.alerts import router as alerts_router
from app.api.thresholds import router as thresholds_router
from app.api.forecast import router as forecast_router
from app.api.geocode import router as geocode_router
from app.api.me import router as me_router
from app.api.push_tokens import router as push_tokens_router
from app.api.notification_settings import router as notification_settings_router
from app.api.properties_risk import router as properties_risk_router
from app.api.reset_password import router as reset_password_router
from app.api.privacy import router as privacy_router
from app.api.health import router as health_router
from app.scheduler import setup_scheduler
from app.services.cwa_service import fetch_rainfall_stations

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = setup_scheduler()
    scheduler.start()
    print("排程系統啟動")

    # 背景執行初始雨量載入，不阻塞 server 啟動
    asyncio.create_task(fetch_rainfall_stations())
    print("背景載入雨量資料中（不影響 API 回應）")

    yield

    scheduler.shutdown()
    print("排程系統關閉")


app = FastAPI(title="淹水預警系統 API", lifespan=lifespan)
app.include_router(test_router, prefix="/api")
app.include_router(properties_router, prefix="/api")
app.include_router(location_router, prefix="/api")
app.include_router(rainfall_router, prefix="/api")
app.include_router(alerts_router, prefix="/api")
app.include_router(thresholds_router, prefix="/api")
app.include_router(forecast_router, prefix="/api")
app.include_router(geocode_router, prefix="/api")
app.include_router(me_router, prefix="/api")
app.include_router(push_tokens_router, prefix="/api")
app.include_router(notification_settings_router, prefix="/api")
app.include_router(properties_risk_router, prefix="/api")
app.include_router(reset_password_router)
app.include_router(privacy_router)
app.include_router(health_router)
