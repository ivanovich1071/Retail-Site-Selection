"""GPS trajectory cleaning.

Removes noise from raw GPS tracks before staypoint/flow analysis:
* drops points with implausible instantaneous speed (jumps);
* removes duplicate/near-stationary jitter below a distance threshold;
* sorts chronologically.
"""
import logging
import math
from datetime import datetime
from typing import List, Dict, Any, Union

logger = logging.getLogger(__name__)

EARTH_R = 6_371_000.0
MAX_SPEED_M_S = 55.0  # ~200 km/h — anything faster is a GPS error


def _to_ts(t: Union[float, int, str]) -> float:
    if isinstance(t, (int, float)):
        return float(t)
    # ISO 8601
    return datetime.fromisoformat(t.replace("Z", "+00:00")).timestamp()


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_R * math.asin(math.sqrt(a))


def normalize_points(points: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Coerce timestamps to floats and sort chronologically."""
    out = []
    for p in points:
        if "lat" not in p or "lon" not in p:
            continue
        out.append({"lat": float(p["lat"]), "lon": float(p["lon"]), "t": _to_ts(p["t"])})
    out.sort(key=lambda p: p["t"])
    return out


def clean_trajectory(
    points: List[Dict[str, Any]],
    max_speed_m_s: float = MAX_SPEED_M_S,
    min_dist_m: float = 5.0,
) -> List[Dict[str, Any]]:
    """Return a cleaned, chronologically ordered trajectory."""
    pts = normalize_points(points)
    if len(pts) < 2:
        return pts

    cleaned = [pts[0]]
    for cur in pts[1:]:
        prev = cleaned[-1]
        dt = cur["t"] - prev["t"]
        d = haversine_m(prev["lat"], prev["lon"], cur["lat"], cur["lon"])
        if dt > 0 and (d / dt) > max_speed_m_s:
            continue  # speed spike → drop
        if d < min_dist_m and dt < 1:
            continue  # jitter / duplicate
        cleaned.append(cur)
    logger.debug("Cleaned trajectory %d → %d points", len(pts), len(cleaned))
    return cleaned


def trajectory_stats(points: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Total distance (m), duration (s), and mean speed (m/s)."""
    pts = normalize_points(points)
    if len(pts) < 2:
        return {"distance_m": 0.0, "duration_s": 0.0, "mean_speed_m_s": 0.0, "points": len(pts)}
    dist = sum(
        haversine_m(pts[i - 1]["lat"], pts[i - 1]["lon"], pts[i]["lat"], pts[i]["lon"])
        for i in range(1, len(pts))
    )
    dur = pts[-1]["t"] - pts[0]["t"]
    return {
        "distance_m": round(dist, 1),
        "duration_s": round(dur, 1),
        "mean_speed_m_s": round(dist / dur, 2) if dur > 0 else 0.0,
        "points": len(pts),
    }
