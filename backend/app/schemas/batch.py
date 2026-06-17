from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class BatchJobOut(BaseModel):
    id: int
    file_name: str
    status: str
    total_rows: int
    processed_rows: int
    failed_rows: int
    progress_pct: float = 0.0
    created_at: datetime
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_progress(cls, job):
        obj = cls.model_validate(job)
        if job.total_rows > 0:
            obj.progress_pct = round(job.processed_rows / job.total_rows * 100, 1)
        return obj


class BatchResultOut(BaseModel):
    id: int
    address: str
    score: Optional[float]
    huff_share: Optional[float]
    priority: Optional[str]
    error_message: Optional[str]

    model_config = {"from_attributes": True}


class BatchResultsPage(BaseModel):
    job: BatchJobOut
    results: List[BatchResultOut]
    total: int
