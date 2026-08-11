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


@router.post("/alerts/evaluate")
async def trigger_evaluation():
    from app.services.risk_engine import evaluate_all_properties
    await evaluate_all_properties()
    return {"message": "風險評估完成"}


@router.post("/alerts/seed-test")
async def seed_test_alerts(
    db: AsyncSession = Depends(get_db),
    device_id: str = Depends(get_device_id),
):
    import json as _json
    from uuid import uuid4

    rows = (await db.execute(text("""
        SELECT id, name FROM properties
        WHERE device_id = :device_id
        ORDER BY created_at
        LIMIT 3
    """), {"device_id": device_id})).fetchall()

    if not rows:
        return {"inserted": 0, "message": "沒有財產可以綁定"}

    def pick(i):
        return rows[i] if i < len(rows) else rows[0]

    seeds = [
        (pick(0), "level1", "3H", 68.5, 45.0, "一級警戒", "警戒值",  0),
        (pick(1), "level2", "1H", 32.0, 25.0, "二級預警", "預警值", 25),
        (pick(2), "level1", "6H", 102.0, 80.0, "一級警戒", "警戒值", 70),
    ]

    inserted = 0
    for prop, level, scale, actual, thresh, level_label, thresh_label, mins_ago in seeds:
        msg = f"【{prop.name}】達{level_label} {scale} 雨量 {actual}mm（已達{thresh_label} {thresh}mm）"
        await db.execute(text("""
            INSERT INTO alerts (id, property_id, level, message, triggered_by, created_at, read_at)
            VALUES (
                gen_random_uuid(), :pid, :level, :msg,
                CAST(:tb AS jsonb),
                NOW() - (:mins * INTERVAL '1 minute'),
                NULL
            )
        """), {
            "pid": str(prop.id),
            "level": level,
            "msg": msg,
            "tb": _json.dumps({"scale": scale, "actual_mm": actual, "threshold_mm": thresh}),
            "mins": mins_ago,
        })
        inserted += 1

    await db.commit()
    return {"inserted": inserted, "message": f"已插入 {inserted} 筆測試警報"}


@router.delete("/alerts/seed-test")
async def delete_test_alerts(
    db: AsyncSession = Depends(get_db),
    device_id: str = Depends(get_device_id),
):
    result = await db.execute(text("""
        DELETE FROM alerts
        WHERE property_id IN (SELECT id FROM properties WHERE device_id = :device_id)
        AND message ~ '雨量 (68\\.5|32\\.0|102\\.0)mm'
    """), {"device_id": device_id})
    await db.commit()
    return {"deleted": result.rowcount, "message": f"已清除 {result.rowcount} 筆測試警報"}
