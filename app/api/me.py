from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.auth import get_device_id
from app.dependencies import get_db
from app.limiter import limiter

router = APIRouter()


@router.get("/me")
async def get_me(device_id: str = Depends(get_device_id)):
    return {"device_id": device_id}


@router.delete("/me/data", status_code=200)
@limiter.limit("5/hour")
async def delete_all_data(
    request: Request,
    db: AsyncSession = Depends(get_db),
    device_id: str = Depends(get_device_id),
):
    try:
        await db.execute(
            text("""
                DELETE FROM alerts
                WHERE property_id IN (
                    SELECT id FROM properties WHERE device_id = :device_id
                )
            """),
            {"device_id": device_id},
        )
        await db.execute(
            text("DELETE FROM properties WHERE device_id = :device_id"),
            {"device_id": device_id},
        )
        await db.execute(
            text("DELETE FROM push_tokens WHERE device_id = :device_id"),
            {"device_id": device_id},
        )
        await db.execute(
            text("DELETE FROM user_notification_settings WHERE device_id = :device_id"),
            {"device_id": device_id},
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=500, detail="刪除失敗，請稍後再試")
    return {"message": "所有資料已刪除"}
