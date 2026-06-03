from sqlalchemy import BigInteger, String, Float, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional
from datetime import datetime
from app.database import Base


class FloodEvent(Base):
    __tablename__ = "flood_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # 來源新聞
    news_article_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    news_title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    news_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # 淹水事件資訊（LLM 抽取）
    location_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    county_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    district_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    village_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # 座標（從 districts 表查詢）
    lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    lng: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # 估計淹水時間（news_time 往前 N 小時）
    est_flood_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # 資料品質
    confidence: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # 後續填入（第 3-6 週）
    rainfall_1h: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rainfall_3h: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rainfall_6h: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    wra_threshold_1h: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    wra_threshold_3h: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    wra_threshold_6h: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    needs_adjustment: Mapped[Optional[bool]] = mapped_column(nullable=True)
