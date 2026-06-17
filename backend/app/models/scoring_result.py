from datetime import datetime
from typing import Optional

from sqlalchemy import Float, Integer, ForeignKey, DateTime, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from backend.app.core.database import Base


class ScoringResult(Base):
    __tablename__ = "scoring_results"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id", ondelete="CASCADE"), nullable=False, index=True)

    total_score: Mapped[float] = mapped_column(Float, nullable=False)
    huff_market_share: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cannibalization_risk: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    revenue_forecast: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Breakdown by scoring components
    score_demographics: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    score_competitors: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    score_accessibility: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    score_visibility: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    score_location: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Full calculation details
    raw_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    version: Mapped[str] = mapped_column(String(50), default="1.0")
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    location = relationship("Location", back_populates="scoring_results")
