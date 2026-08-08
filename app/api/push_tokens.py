from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.dependencies import get_db
from app.auth import CurrentUser, get_current_user
from app.push import send_push_notifications

router = APIRouter()


class PushTokenBody(BaseModel):
    push_token: str


@router.post("/register-push-token", status_code=200)
async def register_push_token(
    body: PushTokenBody,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    token = body.push_token.strip()
    if not token.startswith("ExponentPushToken["):
        raise HTTPException(status_code=400, detail="無效的 Expo Push Token 格式")

    # INSERT ... ON CONFLICT (user_id, push_token) DO UPDATE updated_at
    await db.execute(
        text("""
            INSERT INTO push_tokens (id, user_id, push_token, created_at, updated_at)
            VALUES (gen_random_uuid(), :user_id, :token, NOW(), NOW())
            ON CONFLICT (user_id, push_token)
            DO UPDATE SET updated_at = NOW()
        """),
        {"user_id": user.user_id, "token": token},
    )
    await db.commit()
    return {"message": "push token 已儲存"}


@router.post("/test-push")
async def test_push(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """對當前登入使用者的所有裝置發一則測試推播。"""
    rows = await db.execute(
        text("SELECT push_token FROM push_tokens WHERE user_id = :uid"),
        {"uid": user.user_id},
    )
    tokens = [r.push_token for r in rows.fetchall()]
    if not tokens:
        raise HTTPException(status_code=404, detail="找不到此使用者的推播 token，請先在實體裝置登入 App")

    pref = (await db.execute(
        text("SELECT notify_enabled, sound_enabled FROM user_notification_settings WHERE user_id = :uid"),
        {"uid": user.user_id},
    )).fetchone()
    notify_enabled = pref.notify_enabled if pref else True
    sound_enabled = pref.sound_enabled if pref else True

    if not notify_enabled:
        return {"message": "推播通知已關閉，未送出", "sound": None}

    sound = "default" if sound_enabled else None
    await send_push_notifications(
        tokens,
        title="🔔 測試推播",
        body="測試推播：這是一則測試通知",
        sound=sound,
    )
    return {"message": f"已送出測試推播至 {len(tokens)} 個裝置", "sound": sound}
