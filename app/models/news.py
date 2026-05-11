from uuid import UUID, uuid4
from typing import Optional, Any
from datetime import datetime
from sqlalchemy import String, Text, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from geoalchemy2 import Geography
from app.database import Base


class News(Base):
    __tablename__ = "news_articles"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(500))
    url: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(100))
    published_at: Mapped[datetime]
    is_flood_related: Mapped[bool] = mapped_column(Boolean, default=False)
    locations: Mapped[Optional[list]] = mapped_column(JSON)
    severity: Mapped[Optional[str]] = mapped_column(String(20))
    location_geom: Mapped[Optional[Any]] = mapped_column(
        Geography(geometry_type="POINT", srid=4326), nullable=True
    )
