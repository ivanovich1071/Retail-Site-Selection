"""Spatial feature extraction — density, walkability, parking, POI diversity."""
import logging
import math
from typing import Dict, Any

logger = logging.getLogger(__name__)


def shannon_diversity(category_counts: Dict[str, int]) -> float:
    """Shannon entropy of POI categories, normalised to 0..1."""
    total = sum(category_counts.values())
    if total <= 0:
        return 0.0
    k = len(category_counts)
    if k <= 1:
        return 0.0
    h = -sum((c / total) * math.log(c / total) for c in category_counts.values() if c > 0)
    return round(h / math.log(k), 4)


def walkability_score(
    intersection_count: int,
    poi_count: int,
    sidewalk_ratio: float = 0.5,
) -> float:
    """Composite 0..1 walkability from connectivity, density, and sidewalks."""
    conn = min(1.0, intersection_count / 50.0)      # ~50 intersections = max
    dens = min(1.0, poi_count / 100.0)
    walk = 0.4 * conn + 0.4 * dens + 0.2 * max(0.0, min(1.0, sidewalk_ratio))
    return round(walk, 4)


def extract_spatial_features(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Build the spatial feature subset from raw collected data.

    raw expects: population, density_per_sqkm, avg_income, intersection_count,
    poi_count, poi_categories (dict), parking_count, sidewalk_ratio, footfall.
    """
    poi_categories = raw.get("poi_categories", {}) or {}
    return {
        "population": int(raw.get("population", 0) or 0),
        "density_per_sqkm": float(raw.get("density_per_sqkm", 0.0) or 0.0),
        "avg_income": raw.get("avg_income"),
        "walkability": walkability_score(
            raw.get("intersection_count", 0),
            raw.get("poi_count", 0),
            raw.get("sidewalk_ratio", 0.5),
        ),
        "parking_count": int(raw.get("parking_count", 0) or 0),
        "poi_diversity": shannon_diversity(poi_categories),
        "footfall_index": round(float(raw.get("footfall", 0.0) or 0.0), 4),
    }
