from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Literal
from uuid import UUID
from datetime import datetime


class PropertyBase(BaseModel):
    name: str
    type: Literal['house', 'car', 'warehouse', 'other']
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    address: Optional[str] = None
    floor_level: Optional[int] = Field(default=1, ge=1)
    alert_enabled: bool = True


class PropertyCreate(PropertyBase):
    pass


class PropertyResponse(PropertyBase):
    id: UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
