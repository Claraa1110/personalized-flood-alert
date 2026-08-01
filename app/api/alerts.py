from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.dependencies import get_db
from uuid import UUID
from app.auth import CurrentUser, get_current_user

router = APIRouter()


@router.get("/alerts")
async def get_alerts(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """查詢使用者所有財產的警報列表"""
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
            WHERE p.user_id = :user_id
            ORDER BY a.created_at DESC
            LIMIT 50
        """),
        {"user_id": user.user_id},
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
    user: CurrentUser = Depends(get_current_user),
):
    """查詢單一警報詳情"""
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
            AND p.user_id = :user_id
        """),
        {"alert_id": str(alert_id), "user_id": user.user_id},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="找不到這個警報")

    await db.execute(
        text(
            "UPDATE alerts SET read_at = NOW() WHERE id = :alert_id AND read_at IS NULL"
        ),
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
    user: CurrentUser = Depends(get_current_user),
):
    """把該使用者所有未讀警報標記為已讀"""
    await db.execute(
        text("""
            UPDATE alerts SET read_at = NOW()
            WHERE read_at IS NULL
            AND property_id IN (
                SELECT id FROM properties WHERE user_id = :user_id
            )
        """),
        {"user_id": user.user_id},
    )
    await db.commit()
    return {"message": "已標記全部已讀"}


@router.post("/alerts/evaluate")
async def trigger_evaluation():
    """手動觸發風險評估（測試用）"""
    from app.services.risk_engine import evaluate_all_properties

    await evaluate_all_properties()
    return {"message": "風險評估完成"}
