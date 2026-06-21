from pydantic import BaseModel, Field
from typing import List, Dict, Any, Union, Optional


class TrajPoint(BaseModel):
    lat: float
    lon: float
    t: Union[float, int, str]


class CleanRequest(BaseModel):
    points: List[TrajPoint]
    max_speed_m_s: float = 55.0
    min_dist_m: float = 5.0


class StaypointRequest(BaseModel):
    points: List[TrajPoint]
    max_dist_m: float = 50.0
    min_duration_s: float = 300.0


class ODRequest(BaseModel):
    trips: List[List[TrajPoint]] = Field(..., description="List of trips; each a list of staypoints")
    resolution: int = Field(8, ge=0, le=15)


class FootfallRequest(BaseModel):
    trajectories: List[List[TrajPoint]]
    lat: float
    lon: float
    radius_m: float = 100.0


class GenericResult(BaseModel):
    result: Dict[str, Any]
