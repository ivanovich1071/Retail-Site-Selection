"""Extended Huff engine with calibration support.

Wraps the base HuffService with:
* multi-store probability allocation across a candidate set (not just one);
* beta calibration from observed market shares (grid search on log-loss-ish
  squared error), so the distance-decay can be fit to real revenue data.
"""
import logging
from typing import List, Dict, Optional, Tuple

from backend.app.services.huff import HuffService

logger = logging.getLogger(__name__)


def allocate_shares(
    stores: List[Dict],          # [{id, area_sqm, travel_time_s}]
    population_zones: List[Dict],  # [{population, store_travel_times: {store_id: seconds}}]
    beta: float = 2.0,
    alpha: float = 1.0,
) -> Dict:
    """Allocate each zone's population across all stores by Huff probability."""
    captured: Dict = {s["id"]: 0.0 for s in stores}
    total_pop = sum(z["population"] for z in population_zones) or 0

    for zone in population_zones:
        pop = zone["population"]
        times = zone.get("store_travel_times", {})
        attrs = {}
        for s in stores:
            t = times.get(s["id"], s.get("travel_time_s", 600))
            t_min = max(t, 60) / 60.0
            attrs[s["id"]] = (max(s["area_sqm"], 1.0) ** alpha) / (t_min ** beta)
        denom = sum(attrs.values())
        if denom <= 0:
            continue
        for sid, a in attrs.items():
            captured[sid] += pop * (a / denom)

    return {
        "total_population": total_pop,
        "shares": {
            sid: {
                "customers": int(c),
                "market_share": round(c / total_pop, 4) if total_pop else 0.0,
            }
            for sid, c in captured.items()
        },
    }


def calibrate_beta(
    stores: List[Dict],
    population_zones: List[Dict],
    observed_shares: Dict,        # {store_id: observed_market_share}
    beta_grid: Optional[List[float]] = None,
    alpha: float = 1.0,
) -> Tuple[float, float]:
    """Grid-search beta minimising squared error vs observed shares.

    Returns (best_beta, best_error).
    """
    beta_grid = beta_grid or [round(b * 0.25, 2) for b in range(2, 17)]  # 0.5 .. 4.0
    best_beta, best_err = beta_grid[0], float("inf")
    for beta in beta_grid:
        alloc = allocate_shares(stores, population_zones, beta=beta, alpha=alpha)
        err = 0.0
        for sid, obs in observed_shares.items():
            pred = alloc["shares"].get(sid, {}).get("market_share", 0.0)
            err += (pred - obs) ** 2
        if err < best_err:
            best_err, best_beta = err, beta
    logger.info("Calibrated Huff beta=%s (sq.err=%.5f)", best_beta, best_err)
    return best_beta, round(best_err, 6)


class HuffEngine(HuffService):
    """HuffService + multi-store allocation and calibration."""

    def allocate(self, stores, population_zones, alpha: float = 1.0) -> Dict:
        return allocate_shares(stores, population_zones, beta=self.beta, alpha=alpha)

    def calibrate(self, stores, population_zones, observed_shares, alpha: float = 1.0) -> float:
        best_beta, _ = calibrate_beta(stores, population_zones, observed_shares, alpha=alpha)
        self.beta = best_beta
        return best_beta
