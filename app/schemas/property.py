from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Literal
from uuid import UUID
from datetime import datetime


class PropertyBase(BaseModel):
    name: str
    type: Literal["house", "car", "warehouse", "other"]
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    address: Optional[str] = None
    floor_level: Optional[int] = Field(default=1, ge=1)
    alert_enabled: bool = True


class PropertyCreate(PropertyBase):
    pass


class PropertyResponse(BaseModel):
    id: UUID
    name: str
    type: str
    address: Optional[str] = None
    floor_level: int
    alert_enabled: bool
    created_at: datetime
    latitude: float
    longitude: float
    district_name: Optional[str] = None
    flood_risk_level: Optional[int] = None
    rainfall_now_mm: Optional[float] = None
    rainfall_1hr_mm: Optional[float] = None
    rainfall_24hr_mm: Optional[float] = None
    model_config = ConfigDict(from_attributes=True)
