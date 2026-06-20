from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import os
import shutil

from backend.app.core.database import get_db
from backend.app.core.config import settings
from backend.app.models.location import Location
from backend.app.models.scoring_result import ScoringResult
from backend.app.schemas.location import LocationCreate, LocationUpdate, LocationOut, LocationListOut, ScoringResultOut
from backend.app.api.v1.endpoints.auth import get_current_user

router = APIRouter()


def _to_out(loc: Location) -> dict:
    d = {c.name: getattr(loc, c.name) for c in loc.__table__.columns if c.name not in ("geom", "building_polygon")}
    return d


@router.get("", response_model=LocationListOut)
async def list_locations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Location)
    if status:
        query = query.where(Location.status == status)

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar()

    query = query.offset((page - 1) * page_size).limit(page_size).order_by(Location.created_at.desc())
    result = await db.execute(query)
    locations = result.scalars().all()

    return {
        "items": [_to_out(loc) for loc in locations],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{location_id}", response_model=LocationOut)
async def get_location(location_id: int, db: AsyncSession = Depends(get_db)):
    loc = await db.get(Location, location_id)
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")
    return _to_out(loc)


@router.post("", response_model=LocationOut, status_code=201)
async def create_location(
    body: LocationCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    loc = Location(**body.model_dump(), created_by=current_user.id)
    db.add(loc)
    await db.commit()
    await db.refresh(loc)
    return _to_out(loc)


@router.patch("/{location_id}", response_model=LocationOut)
async def update_location(
    location_id: int,
    body: LocationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    loc = await db.get(Location, location_id)
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(loc, field, value)

    await db.commit()
    await db.refresh(loc)
    return _to_out(loc)


@router.delete("/{location_id}", status_code=204)
async def delete_location(
    location_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    loc = await db.get(Location, location_id)
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")
    await db.delete(loc)
    await db.commit()


@router.post("/{location_id}/photo")
async def upload_photo(
    location_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    loc = await db.get(Location, location_id)
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")

    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed")

    photo_dir = os.path.join(settings.UPLOAD_DIR, "photos")
    os.makedirs(photo_dir, exist_ok=True)
    ext = os.path.splitext(file.filename)[1]
    dest = os.path.join(photo_dir, f"location_{location_id}{ext}")

    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    loc.photo_path = dest
    await db.commit()
    return {"photo_path": dest}


@router.get("/{location_id}/scoring", response_model=ScoringResultOut)
async def get_scoring(location_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ScoringResult)
        .where(ScoringResult.location_id == location_id)
        .order_by(ScoringResult.calculated_at.desc())
        .limit(1)
    )
    scoring = result.scalar_one_or_none()
    if not scoring:
        raise HTTPException(status_code=404, detail="No scoring result found for this location")
    return scoring
