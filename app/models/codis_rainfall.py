from sqlalchemy import BigInteger, String, Float, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional
from datetime import datetime
from app.database import Base

class CodisRawRainfall(Base):
    __tablename__ = 'codis_raw_rainfall'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    flood_event_id: Mapped[int] = mapped_column(BigInteger)
    station_id: Mapped[str] = mapped_column(String(20))
    station_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    distance_km: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    obs_time: Mapped[datetime] = mapped_column(DateTime)
    rainfall_mm: Mapped[float] = mapped_column(Float, default=0.0)

    __table_args__ = (
        UniqueConstraint('flood_event_id', 'station_id', 'obs_time',
                         name='codis_unique'),
    )
