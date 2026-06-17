import os
import shutil
from datetime import datetime

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.models.batch_job import BatchJob, BatchResult, BatchJobStatus
from backend.app.schemas.batch import BatchJobOut, BatchResultsPage, BatchResultOut
from backend.app.api.v1.endpoints.auth import get_current_user

router = APIRouter()


@router.post("/upload", response_model=BatchJobOut, status_code=202)
async def upload_batch_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    allowed = {".xlsx", ".xls", ".csv"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed:
        raise HTTPException(status_code=400, detail=f"File type not allowed. Use: {allowed}")

    upload_dir = os.path.join(settings.UPLOAD_DIR, "batch")
    os.makedirs(upload_dir, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(upload_dir, f"{timestamp}_{file.filename}")
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    job = BatchJob(
        user_id=current_user.id,
        file_name=file.filename,
        file_path=dest,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Dispatch Celery task
    from backend.app.tasks.batch_tasks import process_batch
    task = process_batch.delay(job.id, dest)
    job.celery_task_id = task.id
    await db.commit()

    return BatchJobOut.model_validate(job)


@router.get("", response_model=list[BatchJobOut])
async def list_batch_jobs(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(
        select(BatchJob)
        .where(BatchJob.user_id == current_user.id)
        .order_by(BatchJob.created_at.desc())
        .limit(50)
    )
    jobs = result.scalars().all()
    return [BatchJobOut.model_validate(j) for j in jobs]


@router.get("/{job_id}", response_model=BatchResultsPage)
async def get_batch_results(
    job_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    job = await db.get(BatchJob, job_id)
    if not job or job.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Batch job not found")

    count_result = await db.execute(
        select(func.count()).where(BatchResult.batch_job_id == job_id)
    )
    total = count_result.scalar()

    results_query = (
        select(BatchResult)
        .where(BatchResult.batch_job_id == job_id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    results_result = await db.execute(results_query)
    results = results_result.scalars().all()

    return BatchResultsPage(
        job=BatchJobOut.from_orm_with_progress(job),
        results=[BatchResultOut.model_validate(r) for r in results],
        total=total,
    )


@router.delete("/{job_id}", status_code=204)
async def cancel_batch_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    job = await db.get(BatchJob, job_id)
    if not job or job.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Batch job not found")

    if job.celery_task_id:
        from backend.celery_worker import celery_app
        celery_app.control.revoke(job.celery_task_id, terminate=True)

    job.status = BatchJobStatus.cancelled
    await db.commit()
