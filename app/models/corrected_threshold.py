from sqlalchemy import BigInteger, String, Float
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional
from app.database import Base

class CorrectedThreshold(Base):
    __tablename__ = 'corrected_thresholds'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    county_name: Mapped[str] = mapped_column(String(50))
    district_name: Mapped[str] = mapped_column(String(50))

    # 原始 WRA 門檻
    original_1h: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    original_3h: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    original_6h: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # 實際致災雨量（最小值）
    min_rainfall_1h: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    min_rainfall_3h: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    min_rainfall_6h: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # 校正後門檻（致災雨量 × 0.9）
    corrected_1h: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    corrected_3h: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    corrected_6h: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # 事件數量和調降幅度
    event_count: Mapped[int] = mapped_column(BigInteger, default=1)
    adjustment_rate_1h: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
