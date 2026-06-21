"""Analytics API — heatmap (district saturation/white-space) + scenario simulation."""
from fastapi import APIRouter

from backend.app.schemas.analytics import (
    HeatmapRequest, SimulationRequest, GenericResult,
)
from backend.app.competition.white_space import score_cell
from backend.app.spatial.h3_indexing import h3_to_geojson
from backend.app.simulation.scenarios import run_scenarios

router = APIRouter()


@router.post("/heatmap", response_model=GenericResult)
async def heatmap(req: HeatmapRequest):
    """Build a GeoJSON heatmap from H3 cells, valued by the chosen metric."""
    features = []
    values = []
    for c in req.cells:
        cell = c.model_dump()
        scored = score_cell(cell)
        if req.metric == "saturation":
            val = scored["saturation_index"] or 0.0
        elif req.metric == "density":
            val = scored["population"]
        else:  # white_space
            val = scored["white_space_score"]
        values.append(val)
        try:
            geom = h3_to_geojson(c.h3_index)
        except Exception:  # noqa: BLE001
            geom = None
        features.append({
            "type": "Feature",
            "properties": {
                "h3_index": c.h3_index,
                "value": val,
                "white_space_score": scored["white_space_score"],
                "saturation_index": scored["saturation_index"],
                "population": scored["population"],
            },
            "geometry": geom,
        })

    return {"result": {
        "metric": req.metric,
        "geojson": {"type": "FeatureCollection", "features": features},
        "min": min(values) if values else 0,
        "max": max(values) if values else 0,
        "count": len(features),
    }}


@router.post("/simulation/run", response_model=GenericResult)
async def simulate(req: SimulationRequest):
    return {"result": run_scenarios(req.baseline, req.scenarios)}
