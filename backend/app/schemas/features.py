from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional


class FeatureVectorRequest(BaseModel):
    raw: Dict[str, Any] = Field(..., description="Raw collected data for feature extraction")
    entity_id: Optional[str] = Field(None, description="Cache key (e.g. location id or h3 index)")


class FeatureVectorResponse(BaseModel):
    version: str
    features: Dict[str, Any]
    groups: Dict[str, List[str]]
    cached: bool = False


class FeatureSpecOut(BaseModel):
    name: str
    group: str
    dtype: str
    source: str
    version: str
    description: str
