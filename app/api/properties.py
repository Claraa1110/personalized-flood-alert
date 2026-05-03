from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import Point
from app.dependencies import get_db
from app.models.property import Property
from app.schemas.property import PropertyCreate, PropertyResponse

router = APIRouter()

DEFAULT_USER_ID = UUID("00000000-0000-0000-0000-000000000001")


def to_response(prop: Property) -> PropertyResponse:
    shape = to_shape(prop.location)
    return PropertyResponse(
        id=prop.id,
        name=prop.name,
        type=prop.type,
        address=prop.address,
        floor_level=prop.floor_level,
        alert_enabled=prop.alert_enabled,
        created_at=prop.created_at,
        latitude=shape.y,
        longitude=shape.x,
    )


@router.post("/properties", response_model=PropertyResponse, status_code=201)
async def create_property(
    property_data: PropertyCreate,
    db: AsyncSession = Depends(get_db),
    x_test_user_id: UUID = Header(default=DEFAULT_USER_ID),
):
    location = from_shape(Point(property_data.longitude, property_data.latitude), srid=4326)

    prop = Property(
        user_id=x_test_user_id,
        name=property_data.name,
        type=property_data.type,
        location=location,
        address=property_data.address,
        floor_level=property_data.floor_level or 1,
        alert_enabled=property_data.alert_enabled,
    )
    db.add(prop)
    await db.commit()
    await db.refresh(prop)
    return to_response(prop)


@router.get("/properties", response_model=list[PropertyResponse])
async def list_properties(
    db: AsyncSession = Depends(get_db),
    x_test_user_id: UUID = Header(default=DEFAULT_USER_ID),
):
    result = await db.execute(
        select(Property).where(Property.user_id == x_test_user_id)
    )
    props = result.scalars().all()
    return [to_response(p) for p in props]


@router.get("/properties/{property_id}", response_model=PropertyResponse)
async def get_property(
    property_id: UUID,
    db: AsyncSession = Depends(get_db),
    x_test_user_id: UUID = Header(default=DEFAULT_USER_ID),
):
    result = await db.execute(
        select(Property).where(
            Property.id == property_id,
            Property.user_id == x_test_user_id,
        )
    )
    prop = result.scalar_one_or_none()
    if not prop:
        raise HTTPException(status_code=404, detail="找不到這個財產")
    return to_response(prop)
