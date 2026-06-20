from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, Float, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base


class H3Cell(Base):
    __tablename__ = "h3_cells"

    h3_index: Mapped[str] = mapped_column(String(16), primary_key=True)
    resolution: Mapped[int] = mapped_column(Integer, index=True)
    center_lat: Mapped[float] = mapped_column(Float)
    center_lon: Mapped[float] = mapped_column(Float)
    population: Mapped[int] = mapped_column(Integer, default=0)
    density_per_sqkm: Mapped[float] = mapped_column(Float, default=0.0)
    avg_income: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    competitor_count: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
