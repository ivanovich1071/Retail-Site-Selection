from datetime import datetime
from typing import Optional

from geoalchemy2 import Geometry
from sqlalchemy import String, DateTime, Float
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from backend.app.core.database import Base


class Competitor(Base):
    __tablename__ = "competitors"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    brand_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    store_format: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # supermarket, discounter, etc.
    area_sqm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    geom = mapped_column(Geometry("POINT", srid=4326), nullable=False)

    # Data source tracking
    source: Mapped[str] = mapped_column(String(50), default="2gis")  # 2gis, osm, manual
    external_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
