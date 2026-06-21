"""Mobility Engine API — trajectory cleaning, staypoints, OD matrix, footfall."""
from fastapi import APIRouter

from backend.app.schemas.mobility import (
    CleanRequest, StaypointRequest, ODRequest, FootfallRequest, GenericResult,
)
from backend.app.mobility.trajectory import clean_trajectory, trajectory_stats
from backend.app.mobility.staypoints import detect_staypoints, dwell_summary
from backend.app.mobility.od_matrix import build_od_matrix, top_flows
from backend.app.mobility.flow_analysis import footfall, zone_flow_profiles

router = APIRouter()


def _pts(items):
    return [p.model_dump() for p in items]


@router.post("/clean", response_model=GenericResult)
async def clean(req: CleanRequest):
    cleaned = clean_trajectory(_pts(req.points), req.max_speed_m_s, req.min_dist_m)
    return {"result": {"cleaned": cleaned, "stats": trajectory_stats(cleaned)}}


@router.post("/staypoints", response_model=GenericResult)
async def staypoints(req: StaypointRequest):
    stays = detect_staypoints(_pts(req.points), req.max_dist_m, req.min_duration_s)
    return {"result": {"staypoints": stays, "summary": dwell_summary(stays)}}


@router.post("/od-matrix", response_model=GenericResult)
async def od_matrix(req: ODRequest):
    trips = [_pts(t) for t in req.trips]
    od = build_od_matrix(trips, resolution=req.resolution)
    od["top_flows"] = top_flows(od)
    od["zone_profiles"] = zone_flow_profiles(od)
    return {"result": od}


@router.post("/footfall", response_model=GenericResult)
async def compute_footfall(req: FootfallRequest):
    trajs = [_pts(t) for t in req.trajectories]
    return {"result": footfall(trajs, req.lat, req.lon, req.radius_m)}
