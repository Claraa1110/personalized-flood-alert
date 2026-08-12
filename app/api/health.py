from datetime import datetime

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/health/scheduler")
def scheduler_health():
    from app.services.cwa_service import last_rainfall_update

    if last_rainfall_update is None:
        return {"status": "no_data", "minutes_since_last_update": None}
    minutes = (datetime.now() - last_rainfall_update).total_seconds() / 60
    return {"status": "ok", "minutes_since_last_update": round(minutes, 1)}
