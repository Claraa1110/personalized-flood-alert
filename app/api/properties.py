from uuid import UUID
from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from app.dependencies import get_db
from app.models.property import Property
from app.schemas.property import PropertyCreate, PropertyResponse

router = APIRouter()

DEFAULT_USER_ID = UUID("00000000-0000-0000-0000-000000000001")


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
    return prop
