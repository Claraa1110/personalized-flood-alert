from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.dependencies import get_db
from uuid import UUID
from app.auth import get_device_id

router = APIRouter()


@router.get("/alerts")
async def get_alerts(
    db: AsyncSession = Depends(get_db),
    device_id: str = Depends(get_device_id),
):
    result = await db.execute(
        text("""
            SELECT
                a.id,
                a.property_id,
                a.level,
                a.message,
                a.created_at,
                a.read_at,
                p.name as property_name,
                p.address as property_address
            FROM alerts a
            JOIN properties p ON a.property_id = p.id
            WHERE p.device_id = :device_id
            ORDER BY a.created_at DESC
            LIMIT 50
        """),
        {"device_id": device_id},
    )
    rows = result.fetchall()
    return {
        "total": len(rows),
        "alerts": [
            {
                "id": str(row.id),
                "property_id": str(row.property_id),
                "level": row.level,
                "message": row.message,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "read_at": row.read_at.isoformat() if row.read_at else None,
                "property_name": row.property_name,
                "property_address": row.property_address,
                "is_read": row.read_at is not None,
            }
            for row in rows
        ],
    }


@router.get("/alerts/{alert_id}")
async def get_alert_detail(
    alert_id: UUID,
    db: AsyncSession = Depends(get_db),
    device_id: str = Depends(get_device_id),
):
    result = await db.execute(
        text("""
            SELECT
                a.id, a.level, a.message, a.triggered_by,
                a.created_at, a.read_at,
                p.name as property_name,
                p.address as property_address
            FROM alerts a
            JOIN properties p ON a.property_id = p.id
            WHERE a.id = :alert_id
            AND p.device_id = :device_id
        """),
        {"alert_id": str(alert_id), "device_id": device_id},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="找不到這個警報")

    # read_at 與 created_at 同樣以 NOW()（UTC）寫入，前端補 'Z' 當 UTC 解讀。
    # 切勿改為 Asia/Taipei，否則已讀時間會比實際超前 8 小時，與 created_at 基準不一。
    await db.execute(
        text("UPDATE alerts SET read_at = NOW() WHERE id = :alert_id AND read_at IS NULL"),
        {"alert_id": str(alert_id)},
    )
    await db.commit()

    return {
        "id": str(row.id),
        "level": row.level,
        "message": row.message,
        "triggered_by": row.triggered_by,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "read_at": row.read_at.isoformat() if row.read_at else None,
        "property_name": row.property_name,
        "property_address": row.property_address,
    }


@router.post("/alerts/mark-all-read")
async def mark_all_read(
    db: AsyncSession = Depends(get_db),
    device_id: str = Depends(get_device_id),
):
    # 同上：read_at 存 UTC，與 created_at 及前端解讀一致。
    # 切勿改為 Asia/Taipei，會造成已讀時間基準與建立時間不一致。
    await db.execute(
        text("""
            UPDATE alerts SET read_at = NOW()
            WHERE read_at IS NULL
            AND property_id IN (
                SELECT id FROM properties WHERE device_id = :device_id
            )
        """),
        {"device_id": device_id},
    )
    await db.commit()
    return {"message": "已標記全部已讀"}


