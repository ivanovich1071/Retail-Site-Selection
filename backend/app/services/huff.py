import logging
import math
from typing import List, Dict, Optional

from backend.app.core.config import settings

logger = logging.getLogger(__name__)


class HuffService:
    """
    Huff gravity model for retail market share estimation.

    P(i,j) = (A_j^α / T_ij^β) / Σ_k (A_k^α / T_ik^β)

    Where:
        A_j = attractiveness (store area in m²)
        T_ij = travel time (minutes) from population centroid i to store j
        α = attractiveness exponent (default 1.0)
        β = distance decay (default 2.0 — higher = stronger decay)
    """

    def __init__(self, beta: Optional[float] = None, alpha: float = 1.0):
        self.beta = beta or settings.HUFF_BETA
        self.alpha = alpha

    def calculate_market_share(
        self,
        candidate_area_sqm: float,
        candidate_travel_times: List[float],  # seconds from each population zone
        population_zones: List[Dict],          # [{"population": N, "travel_time_s": T}, ...]
        all_stores: List[Dict],                # [{"area_sqm": A, "travel_time_s": T}, ...]
    ) -> Dict:
        """
        Returns market share and estimated customer count.
        candidate_travel_times: travel times in seconds from each zone to the candidate.
        all_stores: existing stores (competitors + our stores) with their travel times from each zone.
        """
        if not population_zones:
            return {"market_share": 0.0, "estimated_customers": 0}

        total_population = sum(z["population"] for z in population_zones)
        total_captured = 0.0

        for zone in population_zones:
            pop = zone["population"]
            t_candidate = zone.get("travel_time_s", 600)

            if t_candidate <= 0:
                t_candidate = 60

            # Attractiveness of candidate
            a_candidate = (candidate_area_sqm ** self.alpha) / (t_candidate / 60) ** self.beta

            # Attractiveness of all existing stores for this zone
            a_others = 0.0
            for store in all_stores:
                t_store = store.get("travel_time_s", 600)
                if t_store <= 0:
                    t_store = 60
                area = store.get("area_sqm", 500)
                a_others += (area ** self.alpha) / (t_store / 60) ** self.beta

            denominator = a_candidate + a_others
            if denominator <= 0:
                continue

            prob = a_candidate / denominator
            total_captured += pop * prob

        market_share = total_captured / total_population if total_population > 0 else 0.0

        return {
            "market_share": round(market_share, 4),
            "market_share_pct": round(market_share * 100, 2),
            "estimated_customers": int(total_captured),
            "total_population": total_population,
        }

    def estimate_cannibalization(
        self,
        our_stores: List[Dict],  # [{"area_sqm": A, "distance_m": D}, ...]
        cannibalization_radius_m: int = None,
    ) -> float:
        """Returns fraction of revenue at risk from cannibalization."""
        radius = cannibalization_radius_m or settings.CANNIBALIZATION_RADIUS_M
        nearby = [s for s in our_stores if s.get("distance_m", 9999) < radius]
        if not nearby:
            return 0.0
        return min(len(nearby) * 0.15, 0.6)
