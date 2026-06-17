"""
Demographics API endpoints.

GET  /api/v1/demographics/regions        → all regions summary
GET  /api/v1/demographics/region/{code}  → single region detail
POST /api/v1/demographics/refresh        → trigger Belstat pull (admin)
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.services.demographics import get_demographics_service

router = APIRouter()
logger = logging.getLogger(__name__)


class RegionSummary(BaseModel):
    region_code: str
    region_name: str
    population: Optional[float]
    density_per_km2: Optional[float]
    last_refreshed: Optional[str]


class RefreshResult(BaseModel):
    updated: int
    failed: int
    message: str


@router.get("/regions", response_model=List[RegionSummary])
async def list_regions(db: AsyncSession = Depends(get_db)):
    """Return cached population & density for all registered regions."""
    svc = get_demographics_service(db=db)
    return svc.get_all_regions_summary()


@router.get("/region/{region_code}", response_model=RegionSummary)
async def get_region(region_code: str, db: AsyncSession = Depends(get_db)):
    from backend.app.integrations.belstat_client import REGIONS

    if region_code not in REGIONS:
        raise HTTPException(status_code=404, detail=f"Region code {region_code!r} not registered")

    svc = get_demographics_service(db=db)
    pop = svc.get_population_for_region(region_code)
    den = svc.get_density_for_region(region_code)
    return RegionSummary(
        region_code=region_code,
        region_name=REGIONS[region_code],
        population=pop,
        density_per_km2=den,
        last_refreshed=svc._last_refresh.isoformat() if svc._last_refresh else None,
    )


@router.post("/refresh", response_model=RefreshResult)
async def trigger_refresh(
    background_tasks: BackgroundTasks,
    codes: Optional[List[str]] = Query(default=None, description="Region codes; omit for all"),
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger a Belstat data refresh in the background.
    Returns immediately; refresh runs asynchronously.
    """
    svc = get_demographics_service(db=db)

    async def _refresh():
        await svc.refresh_from_belstat(region_codes=codes or None)

    background_tasks.add_task(_refresh)
    return RefreshResult(
        updated=0,
        failed=0,
        message="Refresh started in background. Check /regions after ~30 seconds.",
    )
