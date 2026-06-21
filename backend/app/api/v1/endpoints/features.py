"""Feature Store API — build vectors, browse the feature registry."""
from typing import List, Optional

from fastapi import APIRouter, Query

from backend.app.schemas.features import (
    FeatureVectorRequest, FeatureVectorResponse, FeatureSpecOut,
)
from backend.app.feature_store.pipeline import (
    build_feature_vector, get_cached_vector, cache_vector,
)
from backend.app.feature_store.registry import registry

router = APIRouter()


@router.get("/registry", response_model=List[FeatureSpecOut])
async def list_features(group: Optional[str] = Query(None, description="spatial|temporal|competition")):
    return [s.__dict__ for s in registry.list(group)]


@router.post("/vector", response_model=FeatureVectorResponse)
async def make_vector(req: FeatureVectorRequest):
    if req.entity_id:
        cached = await get_cached_vector(req.entity_id)
        if cached:
            return {**cached, "cached": True}

    vector = build_feature_vector(req.raw)
    if req.entity_id:
        await cache_vector(req.entity_id, vector)
    return {**vector, "cached": False}
