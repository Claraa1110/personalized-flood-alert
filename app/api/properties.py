from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import Point
from app.dependencies import get_db
from app.models.property import Property
from app.schemas.property import PropertyCreate, PropertyResponse
from app.auth import get_device_id
from app.limiter import limiter

router = APIRouter()


def to_response(prop: Property, rainfall_row=None) -> PropertyResponse:
    shape = to_shape(prop.location)
    response = PropertyResponse(
        id=prop.id,
        name=prop.name,
        type=prop.type,
        address=prop.address,
        floor_level=prop.floor_level,
        alert_enabled=prop.alert_enabled,
        created_at=prop.created_at,
        latitude=shape.y,
        longitude=shape.x,
        district_name=prop.district_name,
        flood_risk_level=prop.flood_risk_level,
        custom_type_name=prop.custom_type_name,
        priority_stars=prop.priority_stars,
    )
    if rainfall_row:
        response.rainfall_now_mm = rainfall_row.rainfall_mm
        response.rainfall_1hr_mm = rainfall_row.rainfall_1hr
        response.rainfall_24hr_mm = rainfall_row.rainfall_24hr
    return response


async def lookup_rainfall(db: AsyncSession, lat: float, lng: float):
    result = await db.execute(
        text("""
            SELECT rainfall_mm, rainfall_1hr, rainfall_24hr
            FROM rainfall_observations
            WHERE ST_DWithin(
                location,
                ST_MakePoint(:lng, :lat)::geography,
                50000
            )
            ORDER BY observed_at DESC,
                     ST_Distance(location, ST_MakePoint(:lng, :lat)::geography)
            LIMIT 1
        """),
        {"lat": lat, "lng": lng},
    )
    return result.fetchone()


async def resolve_district_or_reject(db: AsyncSession, lat: float, lng: float) -> str:
    """
    以 districts 圖資判定座標所屬行政區，查無者直接拒絕。

    不以經緯度方框驗證——方框會讓臺灣周邊海域的座標通過。
    行政區是後續查詢警戒門檻的依據，查不到就等於永遠無法評估風險，
    故於寫入前即擋下，不可降級為空值靜默接受。
    """
    result = await db.execute(
        text("""
            SELECT county_name, town_name
            FROM districts
            WHERE ST_Contains(geometry, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326))
            LIMIT 1
        """),
        {"lat": lat, "lng": lng},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(
            status_code=400,
            detail="無法辨識此座標所在的行政區，本系統目前僅支援臺灣地區",
        )
    return f"{row.county_name}{row.town_name}"


async def has_nearby_station(db: AsyncSession, lat: float, lng: float) -> bool:
    """座標 10 公里內是否有 2 小時內回報的雨量測站（與風險評估的搜尋條件一致）"""
    result = await db.execute(
        text("""
            SELECT 1
            FROM rainfall_observations
            WHERE observed_at >= (NOW() AT TIME ZONE 'Asia/Taipei') - INTERVAL '2 hours'
              AND ST_DWithin(location, ST_MakePoint(:lng, :lat)::geography, 10000)
            LIMIT 1
        """),
        {"lat": lat, "lng": lng},
    )
    return result.fetchone() is not None


async def lookup_flood_risk(db: AsyncSession, lat: float, lng: float) -> int:
    flood_risk_level = 0
    try:
        async with db.begin_nested():
            flood_result = await db.execute(
                text("""
                    SELECT risk_level
                    FROM flood_risk_zones
                    WHERE scenario = '24h_200mm'
                      AND ST_Within(
                        ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geometry,
                        geometry::geometry
                      )
                    ORDER BY risk_level DESC
                    LIMIT 1
                """),
                {"lat": lat, "lng": lng},
            )
            flood_row = flood_result.fetchone()
            flood_risk_level = flood_row.risk_level if flood_row else 0
    except Exception:
        # flood_risk_zones 圖資尚未匯入，查詢失敗屬預期情形，降級為 0 不影響主要流程
        flood_risk_level = 0

    return flood_risk_level


@router.post("/properties", response_model=PropertyResponse, status_code=201)
@limiter.limit("20/minute")
async def create_property(
    request: Request,
    property_data: PropertyCreate,
    db: AsyncSession = Depends(get_db),
    device_id: str = Depends(get_device_id),
):
    location = from_shape(
        Point(property_data.longitude, property_data.latitude), srid=4326
    )
    # 座標若不落在任何行政區內（海上、國外）直接拒絕，不寫入
    district_name = await resolve_district_or_reject(
        db, property_data.latitude, property_data.longitude
    )
    flood_risk_level = await lookup_flood_risk(
        db, property_data.latitude, property_data.longitude
    )

    prop = Property(
        device_id=device_id,
        name=property_data.name,
        type=property_data.type,
        location=location,
        address=property_data.address,
        floor_level=property_data.floor_level or 1,
        alert_enabled=property_data.alert_enabled,
        district_name=district_name,
        flood_risk_level=flood_risk_level,
        custom_type_name=property_data.custom_type_name if property_data.type == "custom" else None,
        priority_stars=property_data.priority_stars or 5,
    )
    db.add(prop)
    await db.commit()
    await db.refresh(prop)

    # 測站覆蓋僅作提示，不阻擋新增：使用者仍可登記，但需知道風險評估不會生效
    response = to_response(prop)
    if not await has_nearby_station(db, property_data.latitude, property_data.longitude):
        response.station_warning = (
            "此位置 10 公里內無雨量觀測站，系統將無法為此財產提供風險評估。"
        )
    return response


@router.get("/properties", response_model=list[PropertyResponse])
async def list_properties(
    db: AsyncSession = Depends(get_db),
    device_id: str = Depends(get_device_id),
):
    result = await db.execute(
        select(Property).where(Property.device_id == device_id)
    )
    props = result.scalars().all()
    responses = []
    for p in props:
        shape = to_shape(p.location)
        rainfall_row = await lookup_rainfall(db, shape.y, shape.x)
        responses.append(to_response(p, rainfall_row))
    return responses


@router.get("/properties/{property_id}", response_model=PropertyResponse)
async def get_property(
    property_id: UUID,
    db: AsyncSession = Depends(get_db),
    device_id: str = Depends(get_device_id),
):
    result = await db.execute(
        select(Property).where(
            Property.id == property_id,
            Property.device_id == device_id,
        )
    )
    prop = result.scalar_one_or_none()
    if not prop:
        raise HTTPException(status_code=404, detail="找不到這個財產")
    shape = to_shape(prop.location)
    rainfall_row = await lookup_rainfall(db, shape.y, shape.x)
    return to_response(prop, rainfall_row)


@router.put("/properties/{property_id}", response_model=PropertyResponse)
async def update_property(
    property_id: UUID,
    property_data: PropertyCreate,
    db: AsyncSession = Depends(get_db),
    device_id: str = Depends(get_device_id),
):
    result = await db.execute(
        select(Property).where(
            Property.id == property_id,
            Property.device_id == device_id,
        )
    )
    prop = result.scalar_one_or_none()
    if not prop:
        raise HTTPException(status_code=404, detail="找不到這個財產")

    # 編輯時同樣驗證：座標改到海上或國外一律拒絕
    district_name = await resolve_district_or_reject(
        db, property_data.latitude, property_data.longitude
    )
    flood_risk_level = await lookup_flood_risk(
        db, property_data.latitude, property_data.longitude
    )

    prop.name = property_data.name
    prop.type = property_data.type
    prop.location = from_shape(
        Point(property_data.longitude, property_data.latitude), srid=4326
    )
    prop.address = property_data.address
    prop.floor_level = property_data.floor_level or 1
    prop.alert_enabled = property_data.alert_enabled
    prop.district_name = district_name
    prop.flood_risk_level = flood_risk_level
    prop.custom_type_name = property_data.custom_type_name if property_data.type == "custom" else None
    prop.priority_stars = property_data.priority_stars or 5

    await db.commit()
    await db.refresh(prop)

    response = to_response(prop)
    if not await has_nearby_station(db, property_data.latitude, property_data.longitude):
        response.station_warning = (
            "此位置 10 公里內無雨量觀測站，系統將無法為此財產提供風險評估。"
        )
    return response


@router.delete("/properties/{property_id}")
async def delete_property(
    property_id: UUID,
    db: AsyncSession = Depends(get_db),
    device_id: str = Depends(get_device_id),
):
    result = await db.execute(
        select(Property).where(
            Property.id == property_id,
            Property.device_id == device_id,
        )
    )
    prop = result.scalar_one_or_none()
    if not prop:
        raise HTTPException(status_code=404, detail="找不到這個財產")

    await db.delete(prop)
    await db.commit()
    return {"message": "財產已刪除"}
