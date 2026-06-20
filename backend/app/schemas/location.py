from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class LocationCreate(BaseModel):
    address: str
    name: Optional[str] = None
    area_sqm: Optional[float] = Field(None, ge=0)
    parking_spaces: Optional[int] = Field(None, ge=0)
    floor_number: Optional[int] = None
    visibility_score: Optional[float] = Field(None, ge=0, le=10)
    notes: Optional[str] = None


class LocationUpdate(BaseModel):
    name: Optional[str] = None
    area_sqm: Optional[float] = Field(None, ge=0)
    parking_spaces: Optional[int] = Field(None, ge=0)
    floor_number: Optional[int] = None
    visibility_score: Optional[float] = Field(None, ge=0, le=10)
    notes: Optional[str] = None
    status: Optional[str] = None


class LocationOut(BaseModel):
    id: int
    address: str
    name: Optional[str]
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    area_sqm: Optional[float]
    parking_spaces: Optional[int]
    floor_number: Optional[int]
    visibility_score: Optional[float]
    status: str
    notes: Optional[str]
    photo_path: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LocationStatusUpdate(BaseModel):
    status: str  # in_review | approved | rejected | draft
    comment: Optional[str] = None


class LocationListOut(BaseModel):
    items: List[LocationOut]
    total: int
    page: int
    page_size: int


class ScoringResultOut(BaseModel):
    id: int
    location_id: int
    total_score: float
    huff_market_share: Optional[float]
    cannibalization_risk: Optional[float]
    revenue_forecast: Optional[float]
    score_demographics: Optional[float]
    score_competitors: Optional[float]
    score_accessibility: Optional[float]
    score_visibility: Optional[float]
    score_location: Optional[float]
    calculated_at: datetime

    model_config = {"from_attributes": True}
