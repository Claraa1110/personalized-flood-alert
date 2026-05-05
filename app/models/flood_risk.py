from sqlalchemy import BigInteger, String, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column
from geoalchemy2 import Geography
from typing import Any
from app.database import Base


class FloodRiskZone(Base):
    __tablename__ = "flood_risk_zones"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    scenario: Mapped[str] = mapped_column(String(50))
    risk_level: Mapped[int] = mapped_column(Integer)
    geometry: Mapped[Any] = mapped_column(
        Geography(geometry_type="MULTIPOLYGON", srid=4326)
    )

    __table_args__ = (
        Index("flood_risk_zones_geometry_idx", "geometry", postgresql_using="gist"),
    )
