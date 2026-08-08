from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel
from app.dependencies import get_db
from app.auth import CurrentUser, get_current_user

router = APIRouter()


class NotificationSettingsBody(BaseModel):
    notify_enabled: bool
    sound_enabled: bool


@router.get("/notification-settings")
async def get_notification_settings(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    result = await db.execute(
        text("SELECT notify_enabled, sound_enabled FROM user_notification_settings WHERE user_id = :uid"),
        {"uid": user.user_id},
    )
    row = result.fetchone()
    if not row:
        return {"notify_enabled": True, "sound_enabled": True}
    return {"notify_enabled": row.notify_enabled, "sound_enabled": row.sound_enabled}


@router.put("/notification-settings")
async def update_notification_settings(
    body: NotificationSettingsBody,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    await db.execute(text("""
        INSERT INTO user_notification_settings (user_id, notify_enabled, sound_enabled, updated_at)
        VALUES (:uid, :notify, :sound, NOW())
        ON CONFLICT (user_id) DO UPDATE SET
            notify_enabled = EXCLUDED.notify_enabled,
            sound_enabled  = EXCLUDED.sound_enabled,
            updated_at     = NOW()
    """), {"uid": user.user_id, "notify": body.notify_enabled, "sound": body.sound_enabled})
    await db.commit()
    return {"notify_enabled": body.notify_enabled, "sound_enabled": body.sound_enabled}
