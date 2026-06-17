from datetime import datetime
from typing import Optional

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, String, Float, Integer, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base


class DemographicsZone(Base):
    __tablename__ = "demographics_zones"
    __table_args__ = (
        UniqueConstraint("region_code", "data_year", name="uq_demographics_region_year"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # Belstat region identifier (e.g. "919071" = г. Минск)
    region_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    region_name: Mapped[str] = mapped_column(String(255), nullable=False)
    district: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    population: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    population_density: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_salary: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    median_age: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Geometry is optional — Belstat records have no polygon; spatial records do
    geom = mapped_column(Geometry("MULTIPOLYGON", srid=4326), nullable=True)

    data_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, default=func.now(), onupdate=func.now()
    )
