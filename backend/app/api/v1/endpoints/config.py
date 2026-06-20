from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional

from backend.app.core.redis import cache_get, cache_set

router = APIRouter()

SCORING_WEIGHTS_KEY = "config:scoring_weights"
HUFF_PARAMS_KEY = "config:huff_params"


class ScoringWeights(BaseModel):
    demographics: float = Field(0.30, ge=0, le=1)
    competitors: float = Field(0.25, ge=0, le=1)
    accessibility: float = Field(0.20, ge=0, le=1)
    visibility: float = Field(0.15, ge=0, le=1)
    location: float = Field(0.10, ge=0, le=1)


class HuffParams(BaseModel):
    beta: float = Field(2.0, ge=0.1, le=10.0)
    cannibalization_radius_m: int = Field(800, ge=100, le=5000)


class ConfigResponse(BaseModel):
    scoring_weights: ScoringWeights
    huff_params: HuffParams


@router.get("/scoring-weights", response_model=ConfigResponse)
async def get_config():
    weights = await cache_get(SCORING_WEIGHTS_KEY)
    huff = await cache_get(HUFF_PARAMS_KEY)
    return ConfigResponse(
        scoring_weights=ScoringWeights(**(weights or {})),
        huff_params=HuffParams(**(huff or {})),
    )


@router.patch("/scoring-weights", response_model=ConfigResponse)
async def update_config(
    scoring_weights: Optional[ScoringWeights] = None,
    huff_params: Optional[HuffParams] = None,
):
    if scoring_weights:
        await cache_set(SCORING_WEIGHTS_KEY, scoring_weights.model_dump(), ttl_seconds=86400 * 365)
    if huff_params:
        await cache_set(HUFF_PARAMS_KEY, huff_params.model_dump(), ttl_seconds=86400 * 365)

    w = await cache_get(SCORING_WEIGHTS_KEY)
    h = await cache_get(HUFF_PARAMS_KEY)
    return ConfigResponse(
        scoring_weights=ScoringWeights(**(w or {})),
        huff_params=HuffParams(**(h or {})),
    )
