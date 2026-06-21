"""Service-area overlap between catchment zones.

Overlap is the share of one zone's area that is also covered by another zone.
We support two backends:

1. Shapely (accurate polygon intersection) when available.
2. Circle approximation (lens area of two disks) as a dependency-free fallback
   when only centres + radii are known.

Areas are computed in an approximate local planar projection (metres) good
enough for urban catchments (< a few km).
"""
import logging
import math
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

EARTH_R = 6_371_000.0


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_R * math.asin(math.sqrt(a))


def circle_overlap_area(r1: float, r2: float, d: float) -> float:
    """Area of intersection (lens) of two circles, radii r1/r2, centre distance d."""
    if d >= r1 + r2:
        return 0.0
    if d <= abs(r1 - r2):
        return math.pi * min(r1, r2) ** 2
    r1s, r2s = r1 * r1, r2 * r2
    a1 = r1s * math.acos((d * d + r1s - r2s) / (2 * d * r1))
    a2 = r2s * math.acos((d * d + r2s - r1s) / (2 * d * r2))
    a3 = 0.5 * math.sqrt(
        max(0.0, (-d + r1 + r2) * (d + r1 - r2) * (d - r1 + r2) * (d + r1 + r2))
    )
    return a1 + a2 - a3


def overlap_circles(
    lat1: float, lon1: float, r1_m: float,
    lat2: float, lon2: float, r2_m: float,
) -> Dict[str, float]:
    """Overlap metrics for two circular catchments."""
    d = haversine_m(lat1, lon1, lat2, lon2)
    inter = circle_overlap_area(r1_m, r2_m, d)
    a1 = math.pi * r1_m ** 2
    a2 = math.pi * r2_m ** 2
    union = a1 + a2 - inter
    return {
        "distance_m": round(d, 1),
        "intersection_m2": round(inter, 1),
        "overlap_ratio": round(inter / a1, 4) if a1 else 0.0,        # of zone 1
        "overlap_ratio_other": round(inter / a2, 4) if a2 else 0.0,  # of zone 2
        "jaccard": round(inter / union, 4) if union else 0.0,
    }


def _shapely_geom(geojson: Dict[str, Any]):
    from shapely.geometry import shape
    return shape(geojson)


def overlap_polygons(geojson_a: Dict[str, Any], geojson_b: Dict[str, Any]) -> Optional[Dict[str, float]]:
    """Accurate overlap for two GeoJSON polygons. Returns None if Shapely missing.

    Uses an equirectangular metre projection around the combined centroid so
    ratios/Jaccard are area-correct; absolute m² are approximate.
    """
    try:
        from shapely.ops import transform
    except Exception as e:  # noqa: BLE001
        logger.warning("Shapely unavailable for polygon overlap (%s)", e)
        return None

    geom_a = _shapely_geom(geojson_a)
    geom_b = _shapely_geom(geojson_b)

    cx = (geom_a.centroid.x + geom_b.centroid.x) / 2
    cy = (geom_a.centroid.y + geom_b.centroid.y) / 2
    mx = 111_320.0 * math.cos(math.radians(cy)) or 1e-9
    my = 110_540.0

    def to_m(x, y, z=None):
        return ((x - cx) * mx, (y - cy) * my)

    pa = transform(to_m, geom_a)
    pb = transform(to_m, geom_b)
    inter = pa.intersection(pb).area
    union = pa.union(pb).area
    return {
        "intersection_m2": round(inter, 1),
        "overlap_ratio": round(inter / pa.area, 4) if pa.area else 0.0,
        "overlap_ratio_other": round(inter / pb.area, 4) if pb.area else 0.0,
        "jaccard": round(inter / union, 4) if union else 0.0,
    }


def pairwise_overlaps(zones: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Compute circle overlaps for every pair in a list of {id, lat, lon, radius_m}."""
    out: List[Dict[str, Any]] = []
    for i in range(len(zones)):
        for j in range(i + 1, len(zones)):
            a, b = zones[i], zones[j]
            m = overlap_circles(
                a["lat"], a["lon"], a["radius_m"],
                b["lat"], b["lon"], b["radius_m"],
            )
            if m["intersection_m2"] > 0:
                out.append({"a": a["id"], "b": b["id"], **m})
    return out
