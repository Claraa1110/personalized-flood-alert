from uuid import UUID, uuid4
from typing import Optional, Any
from datetime import datetime
from sqlalchemy import String, Integer, Index, func
from sqlalchemy.orm import Mapped, mapped_column
from geoalchemy2 import Geography
from app.database import Base


class Property(Base):
    __tablename__ = "properties"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(String(100))
    type: Mapped[str] = mapped_column(String(20))
    location: Mapped[Any] = mapped_column(Geography(geometry_type="POINT", srid=4326))
    address: Mapped[Optional[str]]
    floor_level: Mapped[int] = mapped_column(default=1)
    alert_enabled: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    district_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    flood_risk_level: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    custom_type_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    __table_args__ = (
        Index("properties_location_idx", "location", postgresql_using="gist"),
    )
