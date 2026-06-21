"""Cannibalization analysis — revenue transfer between own stores and a candidate.

When a new (candidate) store opens near existing own stores, it captures some of
their customers. We estimate, per existing store:

* shared-customer probability — Huff probability mass the candidate diverts in
  the overlapping catchment;
* revenue transfer — fraction of the existing store's revenue captured by the
  candidate, scaled by overlap and distance decay.

The model is intentionally simple and explainable (no ML), matching the
project's "AI augments, business rules decide" principle.
"""
import logging
from typing import List, Dict, Optional

from backend.app.core.config import settings
from backend.app.competition.overlap import overlap_circles

logger = logging.getLogger(__name__)


def huff_diversion(
    candidate_attr: float,
    existing_attr: float,
    beta: float = 2.0,
) -> float:
    """Share of the existing store's overlapping customers the candidate captures.

    Both attractiveness values already fold in distance decay (A/T^beta). The
    candidate's capture inside the shared zone is its Huff probability against
    the existing store.
    """
    denom = candidate_attr + existing_attr
    if denom <= 0:
        return 0.0
    return candidate_attr / denom


def _attractiveness(area_sqm: float, travel_time_s: float, alpha: float, beta: float) -> float:
    t_min = max(travel_time_s, 60) / 60.0
    return (max(area_sqm, 1.0) ** alpha) / (t_min ** beta)


def estimate_cannibalization(
    candidate: Dict,            # {lat, lon, area_sqm, catchment_radius_m, travel_time_s}
    own_stores: List[Dict],     # [{id, lat, lon, area_sqm, revenue_monthly, catchment_radius_m, travel_time_s}]
    beta: Optional[float] = None,
    alpha: float = 1.0,
    radius_m: Optional[int] = None,
) -> Dict:
    """Return per-store and aggregate cannibalization estimates."""
    beta = beta if beta is not None else settings.HUFF_BETA
    radius_m = radius_m or settings.CANNIBALIZATION_RADIUS_M

    cand_r = candidate.get("catchment_radius_m", radius_m)
    cand_attr_base = _attractiveness(
        candidate["area_sqm"], candidate.get("travel_time_s", 300), alpha, beta
    )

    per_store: List[Dict] = []
    total_transfer = 0.0
    total_at_risk_revenue = 0.0

    for s in own_stores:
        s_r = s.get("catchment_radius_m", radius_m)
        ov = overlap_circles(
            candidate["lat"], candidate["lon"], cand_r,
            s["lat"], s["lon"], s_r,
        )
        overlap_ratio = ov["overlap_ratio_other"]  # fraction of existing store's zone shared
        if overlap_ratio <= 0:
            continue

        s_attr = _attractiveness(s["area_sqm"], s.get("travel_time_s", 300), alpha, beta)
        diversion = huff_diversion(cand_attr_base, s_attr, beta)

        # Transfer = customers shared (overlap) × probability candidate wins them.
        transfer = round(overlap_ratio * diversion, 4)
        revenue = s.get("revenue_monthly") or 0.0
        lost_revenue = round(revenue * transfer, 2)

        per_store.append({
            "store_id": s.get("id"),
            "distance_m": ov["distance_m"],
            "overlap_ratio": overlap_ratio,
            "shared_customer_prob": round(diversion, 4),
            "revenue_transfer_ratio": transfer,
            "revenue_at_risk": lost_revenue,
            "within_cannibalization_radius": ov["distance_m"] < radius_m,
        })
        total_transfer += transfer
        total_at_risk_revenue += lost_revenue

    n = len(per_store)
    severity = "none"
    avg = total_transfer / n if n else 0.0
    if avg >= 0.3 or any(p["within_cannibalization_radius"] for p in per_store) and avg >= 0.2:
        severity = "high"
    elif avg >= 0.1:
        severity = "medium"
    elif avg > 0:
        severity = "low"

    return {
        "affected_stores": n,
        "avg_revenue_transfer_ratio": round(avg, 4),
        "total_revenue_at_risk": round(total_at_risk_revenue, 2),
        "severity": severity,
        "per_store": sorted(per_store, key=lambda p: -p["revenue_transfer_ratio"]),
        "penalty_factor": round(max(0.4, 1.0 - avg), 3),  # multiply candidate score by this
    }
