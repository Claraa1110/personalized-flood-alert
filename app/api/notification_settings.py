from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel
from app.dependencies import get_db
from app.auth import get_device_id

router = APIRouter()


class NotificationSettingsBody(BaseModel):
    notify_enabled: bool
    sound_enabled: bool


@router.get("/notification-settings")
async def get_notification_settings(
    db: AsyncSession = Depends(get_db),
    device_id: str = Depends(get_device_id),
):
    result = await db.execute(
        text("SELECT notify_enabled, sound_enabled FROM user_notification_settings WHERE device_id = :device_id"),
        {"device_id": device_id},
    )
    row = result.fetchone()
    if not row:
        return {"notify_enabled": True, "sound_enabled": True}
    return {"notify_enabled": row.notify_enabled, "sound_enabled": row.sound_enabled}


@router.put("/notification-settings")
async def update_notification_settings(
    body: NotificationSettingsBody,
    db: AsyncSession = Depends(get_db),
    device_id: str = Depends(get_device_id),
):
    await db.execute(text("""
        INSERT INTO user_notification_settings (user_id, device_id, notify_enabled, sound_enabled, updated_at)
        VALUES (gen_random_uuid(), :device_id, :notify, :sound, NOW())
        ON CONFLICT (device_id) WHERE device_id IS NOT NULL
        DO UPDATE SET
            notify_enabled = EXCLUDED.notify_enabled,
            sound_enabled  = EXCLUDED.sound_enabled,
            updated_at     = NOW()
    """), {"device_id": device_id, "notify": body.notify_enabled, "sound": body.sound_enabled})
    await db.commit()
    return {"notify_enabled": body.notify_enabled, "sound_enabled": body.sound_enabled}
