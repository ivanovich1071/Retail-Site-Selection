"""Competition Intelligence API — overlap, cannibalization, white-space, graph."""
from fastapi import APIRouter

from backend.app.schemas.competition import (
    OverlapRequest, CannibalizationRequest, WhiteSpaceRequest,
    MarketGraphRequest, GenericResult,
)
from backend.app.competition.overlap import pairwise_overlaps
from backend.app.competition.cannibalization import estimate_cannibalization
from backend.app.competition.white_space import detect_white_space
from backend.app.competition.market_graph import build_graph

router = APIRouter()


@router.post("/overlap", response_model=GenericResult)
async def compute_overlap(req: OverlapRequest):
    zones = [z.model_dump() for z in req.zones]
    return {"result": {"overlaps": pairwise_overlaps(zones)}}


@router.post("/cannibalization", response_model=GenericResult)
async def compute_cannibalization(req: CannibalizationRequest):
    result = estimate_cannibalization(
        candidate=req.candidate.model_dump(),
        own_stores=[s.model_dump() for s in req.own_stores],
        beta=req.beta,
        alpha=req.alpha,
    )
    return {"result": result}


@router.post("/white-space", response_model=GenericResult)
async def compute_white_space(req: WhiteSpaceRequest):
    result = detect_white_space(
        cells=[c.model_dump() for c in req.cells],
        min_score=req.min_score,
        sqm_per_capita=req.sqm_per_capita,
        limit=req.limit,
    )
    # all_cells can be huge; drop from API payload, keep summary + candidates.
    result.pop("all_cells", None)
    return {"result": result}


@router.post("/market-graph", response_model=GenericResult)
async def compute_market_graph(req: MarketGraphRequest):
    result = build_graph(
        stores=[s.model_dump() for s in req.stores],
        min_overlap=req.min_overlap,
    )
    return {"result": result}
