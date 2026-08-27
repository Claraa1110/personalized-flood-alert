from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.dependencies import get_db
from app.auth import get_device_id

router = APIRouter()


class PushTokenBody(BaseModel):
    push_token: str


@router.post("/register-push-token", status_code=200)
async def register_push_token(
    body: PushTokenBody,
    db: AsyncSession = Depends(get_db),
    device_id: str = Depends(get_device_id),
):
    token = body.push_token.strip()
    if not token.startswith("ExponentPushToken["):
        raise HTTPException(status_code=400, detail="無效的 Expo Push Token 格式")

    await db.execute(
        text("""
            INSERT INTO push_tokens (id, user_id, device_id, push_token, created_at, updated_at)
            VALUES (gen_random_uuid(), gen_random_uuid(), :device_id, :token, NOW(), NOW())
            ON CONFLICT (device_id, push_token) WHERE device_id IS NOT NULL
            DO UPDATE SET updated_at = NOW()
        """),
        {"device_id": device_id, "token": token},
    )
    await db.commit()
    return {"message": "push token 已儲存"}


