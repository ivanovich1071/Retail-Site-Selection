"""Competition feature extraction — saturation, LQ, nearest competitor, risk."""
import logging
from typing import Dict, Any, List

from backend.app.competition.white_space import saturation_index
from backend.app.competition.cannibalization import estimate_cannibalization

logger = logging.getLogger(__name__)


def location_quotient(local_per_capita: float, region_per_capita: float) -> float:
    """LQ > 1 → more retail supply per capita than the region (saturated)."""
    if region_per_capita <= 0:
        return 0.0
    return round(local_per_capita / region_per_capita, 4)


def extract_competition_features(raw: Dict[str, Any]) -> Dict[str, Any]:
    """raw expects: population, supply_sqm or competitor_count, competitor_distances
    (list[m]), local_per_capita, region_per_capita, candidate, own_stores.
    """
    pop = int(raw.get("population", 0) or 0)
    supply = raw.get("supply_sqm")
    if supply is None:
        supply = (raw.get("competitor_count", 0) or 0) * 400.0

    distances: List[float] = raw.get("competitor_distances", []) or []
    nearest = round(min(distances), 1) if distances else None

    cann_risk = 0.0
    if raw.get("candidate") and raw.get("own_stores"):
        cann = estimate_cannibalization(raw["candidate"], raw["own_stores"])
        cann_risk = cann["avg_revenue_transfer_ratio"]

    return {
        "competitor_count": int(raw.get("competitor_count", 0) or 0),
        "saturation_index": saturation_index(pop, supply),
        "nearest_competitor_m": nearest,
        "location_quotient": location_quotient(
            raw.get("local_per_capita", 0.0), raw.get("region_per_capita", 0.0)
        ),
        "cannibalization_risk": cann_risk,
    }
