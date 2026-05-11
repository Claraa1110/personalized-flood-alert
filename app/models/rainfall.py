from datetime import datetime
from typing import Any, Optional
from sqlalchemy import BigInteger, String, Index
from sqlalchemy.orm import Mapped, mapped_column
from geoalchemy2 import Geography
from app.database import Base


class Rainfall(Base):
    __tablename__ = "rainfall_observations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(20))
    latitude: Mapped[float]
    longitude: Mapped[float]
    location: Mapped[Any] = mapped_column(
        Geography(geometry_type="POINT", srid=4326), nullable=True
    )
    rainfall_mm: Mapped[float]
    observed_at: Mapped[datetime]
    station_id: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    station_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    county_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    town_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    rainfall_1hr: Mapped[Optional[float]] = mapped_column(nullable=True)
    rainfall_3hr: Mapped[Optional[float]] = mapped_column(nullable=True)
    rainfall_24hr: Mapped[Optional[float]] = mapped_column(nullable=True)

    __table_args__ = (
        Index(
            "rainfall_observations_location_idx", "location", postgresql_using="gist"
        ),
    )
