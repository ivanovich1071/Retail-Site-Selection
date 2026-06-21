from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional


class PredictRequest(BaseModel):
    raw: Dict[str, Any] = Field(..., description="Raw collected data for feature extraction")


class PredictResponse(BaseModel):
    predicted_revenue_monthly: float
    model: str
    confidence: float
    features_used: Optional[Dict[str, Any]] = None


class ExplainRequest(BaseModel):
    raw: Dict[str, Any]
    top_k: int = 8


class TrainRequest(BaseModel):
    rows: List[Dict[str, Any]] = Field(..., description="Raw feature rows")
    targets: List[float] = Field(..., description="Observed monthly revenue per row")
    save: bool = True


class TrainResponse(BaseModel):
    backend: str
    n_rows: int
    saved_path: Optional[str] = None


class GenericResult(BaseModel):
    result: Dict[str, Any]
