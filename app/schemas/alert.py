from pydantic import BaseModel, ConfigDict
from typing import Optional, Literal
from uuid import UUID
from datetime import datetime


class AlertBase(BaseModel):
    property_id: UUID
    level: Literal['notice', 'warning', 'emergency']
    message: str


class AlertCreate(AlertBase):
    pass


class AlertResponse(AlertBase):
    id: UUID
    created_at: datetime
    read_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)
