from datetime import datetime
from typing import Optional

from geoalchemy2 import Geometry
from sqlalchemy import String, DateTime, Float
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from backend.app.core.database import Base


class OurStore(Base):
    __tablename__ = "our_stores"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    store_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, unique=True)
    store_format: Mapped[str] = mapped_column(String(100), nullable=False)  # Евроопт, Хит!, etc.
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    area_sqm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    revenue_monthly: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    geom = mapped_column(Geometry("POINT", srid=4326), nullable=False)

    opened_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
