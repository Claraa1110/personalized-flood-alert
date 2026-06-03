from sqlalchemy import BigInteger, String, Float, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional
from app.database import Base


class WraAlertThreshold(Base):
    __tablename__ = "wra_alert_thresholds"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    county_name: Mapped[str] = mapped_column(String(50))
    district_name: Mapped[str] = mapped_column(String(50))
    area_name: Mapped[str] = mapped_column(String(50))
    threshold_1h_lv2: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    threshold_1h_lv1: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    threshold_3h_lv2: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    threshold_3h_lv1: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    threshold_6h_lv2: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    threshold_6h_lv1: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    __table_args__ = (
        UniqueConstraint("county_name", "district_name", "area_name", name="uq_wra_thresholds_location"),
        Index("idx_wra_thresholds_location", "county_name", "district_name", "area_name"),
    )
