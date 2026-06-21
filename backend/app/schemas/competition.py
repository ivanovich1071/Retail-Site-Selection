from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class StoreZone(BaseModel):
    id: Any
    lat: float
    lon: float
    radius_m: float = 800.0


class OverlapRequest(BaseModel):
    zones: List[StoreZone] = Field(..., min_length=2)


class CandidateStore(BaseModel):
    lat: float
    lon: float
    area_sqm: float = 500.0
    catchment_radius_m: float = 800.0
    travel_time_s: float = 300.0


class OwnStore(BaseModel):
    id: Any
    lat: float
    lon: float
    area_sqm: float = 500.0
    revenue_monthly: Optional[float] = None
    catchment_radius_m: float = 800.0
    travel_time_s: float = 300.0


class CannibalizationRequest(BaseModel):
    candidate: CandidateStore
    own_stores: List[OwnStore] = Field(default_factory=list)
    beta: Optional[float] = None
    alpha: float = 1.0


class WhiteSpaceCell(BaseModel):
    h3_index: Optional[str] = None
    population: int = 0
    competitor_count: int = 0
    supply_sqm: Optional[float] = None
    center_lat: Optional[float] = None
    center_lon: Optional[float] = None


class WhiteSpaceRequest(BaseModel):
    cells: List[WhiteSpaceCell]
    min_score: float = 40.0
    sqm_per_capita: float = 0.6
    limit: Optional[int] = None


class GraphStore(BaseModel):
    id: Any
    lat: float
    lon: float
    catchment_radius_m: float = 800.0


class MarketGraphRequest(BaseModel):
    stores: List[GraphStore]
    min_overlap: float = 0.05


class GenericResult(BaseModel):
    result: Dict[str, Any]
