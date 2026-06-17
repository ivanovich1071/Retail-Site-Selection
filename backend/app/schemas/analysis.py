from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class AnalysisByAddressRequest(BaseModel):
    address: str
    area_sqm: Optional[float] = Field(None, ge=10, le=100000)
    parking_spaces: Optional[int] = Field(None, ge=0)
    visibility_score: Optional[float] = Field(None, ge=0, le=10)
    isochrone_minutes: List[int] = [5, 10, 15]
    include_huff: bool = True


class AnalysisByPolygonRequest(BaseModel):
    polygon: Dict[str, Any]  # GeoJSON Polygon: {type: "Polygon", coordinates: [[[lon,lat],...]]}
    area_sqm: Optional[float] = Field(None, ge=10, le=100000)
    parking_spaces: Optional[int] = Field(None, ge=0)
    visibility_score: Optional[float] = Field(None, ge=0, le=10)
    isochrone_minutes: List[int] = [5, 10, 15]
    include_huff: bool = True


class IsochroneData(BaseModel):
    minutes: int
    geometry: Dict[str, Any]  # GeoJSON polygon
    area_sqkm: float
    population: Optional[int]


class CompetitorInfo(BaseModel):
    id: int
    brand_name: str
    store_format: Optional[str]
    distance_m: float
    latitude: float
    longitude: float


class AnalysisResult(BaseModel):
    address: str
    latitude: float
    longitude: float
    building_polygon: Optional[Dict[str, Any]]  # GeoJSON
    isochrones: List[IsochroneData]
    competitors_nearby: List[CompetitorInfo]
    population_in_isochrone: Dict[str, int]  # {"5min": 5000, "10min": 12000, ...}
    avg_salary: Optional[float]
    scoring: "ScoringBreakdown"
    huff_market_share: Optional[float]
    cannibalization_risk: Optional[float]


class ScoringBreakdown(BaseModel):
    total_score: float = Field(ge=0, le=100)
    score_demographics: float
    score_competitors: float
    score_accessibility: float
    score_visibility: float
    score_location: float
    details: Dict[str, Any] = {}


AnalysisResult.model_rebuild()
