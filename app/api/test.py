from fastapi import APIRouter, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.sql.expression import cast
from geoalchemy2 import Geography
from geoalchemy2.functions import ST_DWithin, ST_Distance, ST_MakePoint
from app.dependencies import get_db
from app.models.property import Property

router = APIRouter()


@router.get("/test-postgis")
async def test_postgis(
    lat: float = Query(...),
    lng: float = Query(...),
    radius: float = Query(5000),
    db: AsyncSession = Depends(get_db),
):
    center = cast(ST_MakePoint(lng, lat), Geography(srid=4326))

    result = await db.execute(
        select(
            Property.name,
            ST_Distance(Property.location, center).label("dist_m"),
        )
        .where(ST_DWithin(Property.location, center, radius))
        .order_by("dist_m")
    )
    rows = result.all()

    return {
        "center": {"lat": lat, "lng": lng},
        "radius_m": radius,
        "results": [{"name": r.name, "dist_m": round(r.dist_m, 1)} for r in rows],
    }


@router.get("/test-integrated")
async def test_integrated(
    lat: float = Query(...),
    lng: float = Query(...),
    db: AsyncSession = Depends(get_db),
):
    center = cast(ST_MakePoint(lng, lat), Geography(srid=4326))

    result = await db.execute(
        select(
            Property.name,
            ST_Distance(Property.location, center).label("dist_m"),
        )
        .where(ST_DWithin(Property.location, center, 5000))
        .order_by("dist_m")
    )
    rows = result.all()

    return {
        "message": "整合測試成功",
        "center": {"lat": lat, "lng": lng},
        "nearby_properties": [
            {"name": r.name, "dist_m": round(r.dist_m, 1)} for r in rows
        ],
        "total": len(rows),
    }
