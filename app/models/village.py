from sqlalchemy import BigInteger, String, Index
from sqlalchemy.orm import Mapped, mapped_column
from geoalchemy2 import Geography
from typing import Any
from app.database import Base


class Village(Base):
    __tablename__ = "villages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    county_name: Mapped[str] = mapped_column(String(50))
    district_name: Mapped[str] = mapped_column(String(50))
    village_name: Mapped[str] = mapped_column(String(50))
    geometry: Mapped[Any] = mapped_column(
        Geography(geometry_type="MULTIPOLYGON", srid=4326)
    )

    __table_args__ = (
        Index("villages_geometry_idx", "geometry", postgresql_using="gist"),
    )
