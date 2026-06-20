from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class H3PolyfillRequest(BaseModel):
    polygon: Dict[str, Any] = Field(..., description="GeoJSON Polygon")
    resolution: int = Field(9, ge=0, le=15)


class H3CellData(BaseModel):
    h3_index: str
    resolution: int
    center_lat: float
    center_lon: float
    population: int = 0
    density_per_sqkm: float = 0.0
    avg_income: Optional[float] = None
    competitor_count: int = 0
    geometry: Optional[Dict[str, Any]] = None


class H3PolyfillResponse(BaseModel):
    cells: List[H3CellData]
    total_cells: int
    resolution: int
    geojson: Dict[str, Any]
