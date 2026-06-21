from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional


class HeatmapCell(BaseModel):
    h3_index: str
    population: int = 0
    competitor_count: int = 0
    supply_sqm: Optional[float] = None


class HeatmapRequest(BaseModel):
    cells: List[HeatmapCell]
    metric: str = Field("white_space", description="white_space | saturation | density")


class ScenarioSpec(BaseModel):
    type: str = Field(..., description="competitor_opening|competitor_closing|parking_change|economic_shock|visibility_change")
    # free-form params per type (count, distance_m, delta, income_factor, ...)
    model_config = {"extra": "allow"}


class SimulationRequest(BaseModel):
    baseline: Dict[str, Any]
    scenarios: List[Dict[str, Any]]


class GenericResult(BaseModel):
    result: Dict[str, Any]
