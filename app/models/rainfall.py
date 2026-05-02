from datetime import datetime
from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Rainfall(Base):
    __tablename__ = 'rainfall_observations'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(20))
    latitude: Mapped[float]
    longitude: Mapped[float]
    rainfall_mm: Mapped[float]
    observed_at: Mapped[datetime]
