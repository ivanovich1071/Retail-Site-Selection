import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Enum, DateTime, Integer, ForeignKey, JSON, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from backend.app.core.database import Base


class BatchJobStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class BatchJob(Base):
    __tablename__ = "batch_jobs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    celery_task_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    status: Mapped[BatchJobStatus] = mapped_column(Enum(BatchJobStatus), default=BatchJobStatus.pending)
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    processed_rows: Mapped[int] = mapped_column(Integer, default=0)
    failed_rows: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="batch_jobs")
    results = relationship("BatchResult", back_populates="job", lazy="select")


class BatchResult(Base):
    __tablename__ = "batch_results"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    batch_job_id: Mapped[int] = mapped_column(ForeignKey("batch_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    location_id: Mapped[Optional[int]] = mapped_column(ForeignKey("locations.id"), nullable=True)

    address: Mapped[str] = mapped_column(String(500), nullable=False)
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    huff_share: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    priority: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # high/medium/low
    error_message: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    raw_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    job = relationship("BatchJob", back_populates="results")
