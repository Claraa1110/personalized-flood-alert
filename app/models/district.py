from typing import Optional, Any
from sqlalchemy import String, Index
from sqlalchemy.orm import Mapped, mapped_column
from geoalchemy2 import Geometry
from app.database import Base


class District(Base):
    __tablename__ = "districts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    town_id: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    town_code: Mapped[Optional[str]] = mapped_column(String(20))
    town_name: Mapped[str] = mapped_column(String(50), nullable=False)
    town_eng: Mapped[Optional[str]] = mapped_column(String(100))
    county_id: Mapped[str] = mapped_column(String(10), nullable=False)
    county_code: Mapped[Optional[str]] = mapped_column(String(20))
    county_name: Mapped[str] = mapped_column(String(50), nullable=False)
    geometry: Mapped[Any] = mapped_column(
        Geometry(geometry_type="MULTIPOLYGON", srid=4326)
    )

    __table_args__ = (
        Index("districts_geometry_idx", "geometry", postgresql_using="gist"),
    )
