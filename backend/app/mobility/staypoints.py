"""Staypoint detection and dwell-time estimation.

A staypoint is a spatial cluster where the moving object remained within
`max_dist_m` for at least `min_duration_s` — i.e. a stop (shopping, dwelling).
Classic Li et al. (2008) algorithm.
"""
import logging
from typing import List, Dict, Any

from backend.app.mobility.trajectory import normalize_points, haversine_m

logger = logging.getLogger(__name__)


def detect_staypoints(
    points: List[Dict[str, Any]],
    max_dist_m: float = 50.0,
    min_duration_s: float = 300.0,
) -> List[Dict[str, Any]]:
    """Return staypoints with centroid, arrival/departure, and dwell time."""
    pts = normalize_points(points)
    n = len(pts)
    stays: List[Dict[str, Any]] = []
    i = 0
    while i < n:
        j = i + 1
        while j < n:
            d = haversine_m(pts[i]["lat"], pts[i]["lon"], pts[j]["lat"], pts[j]["lon"])
            if d > max_dist_m:
                break
            j += 1
        # cluster is pts[i:j]
        dwell = pts[j - 1]["t"] - pts[i]["t"]
        if dwell >= min_duration_s and (j - i) >= 2:
            cluster = pts[i:j]
            clat = sum(p["lat"] for p in cluster) / len(cluster)
            clon = sum(p["lon"] for p in cluster) / len(cluster)
            stays.append({
                "lat": round(clat, 6),
                "lon": round(clon, 6),
                "arrival_t": pts[i]["t"],
                "departure_t": pts[j - 1]["t"],
                "dwell_time_s": round(dwell, 1),
                "num_points": len(cluster),
            })
            i = j
        else:
            i += 1
    logger.debug("Detected %d staypoints from %d points", len(stays), n)
    return stays


def dwell_summary(staypoints: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate dwell statistics across staypoints."""
    if not staypoints:
        return {"count": 0, "total_dwell_s": 0.0, "mean_dwell_s": 0.0, "max_dwell_s": 0.0}
    dwells = [s["dwell_time_s"] for s in staypoints]
    return {
        "count": len(staypoints),
        "total_dwell_s": round(sum(dwells), 1),
        "mean_dwell_s": round(sum(dwells) / len(dwells), 1),
        "max_dwell_s": round(max(dwells), 1),
    }
