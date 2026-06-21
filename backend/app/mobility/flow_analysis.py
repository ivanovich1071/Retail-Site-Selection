"""Directional flow & footfall analysis around a point.

Derives retail-relevant signals from trajectories and OD matrices:
* footfall — number of distinct trajectories passing within a radius of a point;
* directional balance — net inflow vs outflow for a zone (commuter ratio);
* peak-hour profile — passes bucketed by hour of day.
"""
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import List, Dict, Any

from backend.app.mobility.trajectory import normalize_points, haversine_m

logger = logging.getLogger(__name__)


def footfall(
    trajectories: List[List[Dict[str, Any]]],
    lat: float,
    lon: float,
    radius_m: float = 100.0,
) -> Dict[str, Any]:
    """Count trajectories that pass within radius_m of (lat, lon)."""
    passing = 0
    total_passes = 0
    hourly: Dict[int, int] = defaultdict(int)
    for traj in trajectories:
        pts = normalize_points(traj)
        hit = False
        for p in pts:
            if haversine_m(lat, lon, p["lat"], p["lon"]) <= radius_m:
                total_passes += 1
                hr = datetime.fromtimestamp(p["t"], tz=timezone.utc).hour
                hourly[hr] += 1
                hit = True
        if hit:
            passing += 1
    peak_hour = max(hourly.items(), key=lambda kv: kv[1])[0] if hourly else None
    return {
        "unique_trajectories": passing,
        "total_passes": total_passes,
        "hourly_profile": dict(sorted(hourly.items())),
        "peak_hour": peak_hour,
    }


def commuter_ratio(inflow: int, outflow: int) -> Dict[str, Any]:
    """Net directional balance for a zone.

    ratio > 0 → net attractor (destination); < 0 → net origin (residential).
    """
    total = inflow + outflow
    if total == 0:
        return {"net_flow": 0, "balance_ratio": 0.0, "type": "inactive"}
    balance = (inflow - outflow) / total
    if balance > 0.2:
        kind = "destination"
    elif balance < -0.2:
        kind = "origin"
    else:
        kind = "balanced"
    return {
        "net_flow": inflow - outflow,
        "balance_ratio": round(balance, 3),
        "type": kind,
    }


def zone_flow_profiles(od: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Commuter ratio for every zone in an OD matrix."""
    inflow, outflow = od.get("inflow", {}), od.get("outflow", {})
    return {
        z: commuter_ratio(inflow.get(z, 0), outflow.get(z, 0))
        for z in od.get("zones", [])
    }
