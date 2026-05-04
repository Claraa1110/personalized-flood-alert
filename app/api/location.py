from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.dependencies import get_db

router = APIRouter()


class DistrictResponse(BaseModel):
    town_id: str
    town_name: str
    town_eng: str | None
    county_id: str
    county_name: str


@router.get("/location/district", response_model=DistrictResponse)
async def get_district(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        text("""
            SELECT town_id, town_name, town_eng, county_id, county_name
            FROM districts
            WHERE ST_Contains(geometry, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326))
            LIMIT 1
        """),
        {"lat": lat, "lng": lng},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="查無對應行政區")
    return DistrictResponse(
        town_id=row.town_id,
        town_name=row.town_name,
        town_eng=row.town_eng,
        county_id=row.county_id,
        county_name=row.county_name,
    )
