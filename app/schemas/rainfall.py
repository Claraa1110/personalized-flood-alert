from pydantic import BaseModel, ConfigDict
from typing import Literal
from datetime import datetime


class RainfallBase(BaseModel):
    latitude: float
    longitude: float
    rainfall_mm: float
    observed_at: datetime
    source: Literal['qpe_grid', 'station']


class RainfallCreate(RainfallBase):
    pass


class RainfallResponse(RainfallBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
