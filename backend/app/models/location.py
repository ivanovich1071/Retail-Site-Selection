import enum
from datetime import datetime
from typing import Optional

from geoalchemy2 import Geometry
from sqlalchemy import String, Enum, DateTime, Float, Integer, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from backend.app.core.database import Base


class LocationStatus(str, enum.Enum):
    draft = "draft"
    in_review = "in_review"
    approved = "approved"
    rejected = "rejected"
    opened = "opened"


class Location(Base):
    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # GIS fields
    geom = mapped_column(Geometry("POINT", srid=4326), nullable=True)
    building_polygon = mapped_column(Geometry("POLYGON", srid=4326), nullable=True)

    # Physical parameters
    area_sqm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    parking_spaces: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    floor_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    visibility_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0-10

    # Workflow
    status: Mapped[LocationStatus] = mapped_column(Enum(LocationStatus), default=LocationStatus.draft)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    photo_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Relationships
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_by_user = relationship("User", back_populates="locations")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    scoring_results = relationship("ScoringResult", back_populates="location", lazy="select")
