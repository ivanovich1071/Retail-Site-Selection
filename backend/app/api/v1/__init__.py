from fastapi import APIRouter
from backend.app.api.v1.endpoints import (
    locations, analysis, batch, reports, auth, demographics, config, h3,
    competition, mobility, features,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(locations.router, prefix="/locations", tags=["Locations"])
api_router.include_router(analysis.router, prefix="/analysis", tags=["Analysis"])
api_router.include_router(batch.router, prefix="/batch", tags=["Batch"])
api_router.include_router(reports.router, prefix="/reports", tags=["Reports"])
api_router.include_router(demographics.router, prefix="/demographics", tags=["Demographics"])
api_router.include_router(config.router, prefix="/config", tags=["Config"])
api_router.include_router(h3.router, prefix="/h3", tags=["H3 Spatial"])
api_router.include_router(competition.router, prefix="/competition", tags=["Competition"])
api_router.include_router(mobility.router, prefix="/mobility", tags=["Mobility"])
api_router.include_router(features.router, prefix="/features", tags=["Feature Store"])
