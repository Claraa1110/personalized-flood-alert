from fastapi import APIRouter, Query
from sqlalchemy import select, func
from sqlalchemy.sql.expression import cast
from geoalchemy2 import Geography
from geoalchemy2.functions import ST_DWithin, ST_Distance, ST_MakePoint
from app.database import AsyncSessionLocal
from app.models.property import Property

router = APIRouter()


@router.get("/test-postgis")
async def test_postgis(
    lat: float = Query(...),
    lng: float = Query(...),
    radius: float = Query(5000),
):
    center = cast(ST_MakePoint(lng, lat), Geography(srid=4326))

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(
                Property.name,
                ST_Distance(Property.location, center).label("dist_m"),
            ).where(
                ST_DWithin(Property.location, center, radius)
            ).order_by("dist_m")
        )
        rows = result.all()

    return {
        "center": {"lat": lat, "lng": lng},
        "radius_m": radius,
        "results": [{"name": r.name, "dist_m": round(r.dist_m, 1)} for r in rows],
    }
