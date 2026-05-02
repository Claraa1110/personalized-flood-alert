from uuid import UUID, uuid4
from typing import Optional
from datetime import datetime
from sqlalchemy import String, Text, JSON, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Alert(Base):
    __tablename__ = 'alerts'

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    property_id: Mapped[UUID] = mapped_column(nullable=False)
    level: Mapped[str] = mapped_column(String(20))
    message: Mapped[str] = mapped_column(Text)
    triggered_by: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    read_at: Mapped[Optional[datetime]]
