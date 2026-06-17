import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.models.location import Location
from backend.app.api.v1.endpoints.auth import get_current_user

router = APIRouter()


@router.post("/{location_id}/generate")
async def generate_report(
    location_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Enqueue PDF report generation for a location."""
    loc = await db.get(Location, location_id)
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")

    from backend.app.tasks.report_tasks import generate_pdf_report
    task = generate_pdf_report.delay(location_id)
    return {"task_id": task.id, "status": "queued"}


@router.get("/{location_id}/download")
async def download_report(
    location_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    pdf_path = os.path.join(settings.UPLOAD_DIR, "reports", f"location_{location_id}.pdf")
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="Report not yet generated. Call /generate first.")
    return FileResponse(pdf_path, media_type="application/pdf", filename=f"report_location_{location_id}.pdf")
