"""White-space detection — under-served areas with demand but weak supply.

Operates on H3 hex cells carrying population/density and competitor counts. For
each cell we compute a Location Quotient-style saturation index and flag cells
where demand (population) is high relative to supply (retail floor / competitor
count) — candidate zones for a new store.
"""
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Belarus retail benchmark: ~0.6 m² of grocery floor per capita (ТКП-45 ballpark).
DEFAULT_SQM_PER_CAPITA = 0.6
# Assumed average competitor sales floor when only counts are known.
ASSUMED_STORE_SQM = 400.0


def saturation_index(
    population: int,
    supply_sqm: float,
    sqm_per_capita: float = DEFAULT_SQM_PER_CAPITA,
) -> float:
    """Ratio of actual supply to demand-implied supply.

    < 1.0 → under-served (white space). > 1.0 → saturated.
    Returns a large number when there is supply but ~no population.
    """
    demand_sqm = population * sqm_per_capita
    if demand_sqm <= 0:
        return float("inf") if supply_sqm > 0 else 1.0
    return round(supply_sqm / demand_sqm, 4)


def score_cell(
    cell: Dict[str, Any],
    sqm_per_capita: float = DEFAULT_SQM_PER_CAPITA,
    assumed_store_sqm: float = ASSUMED_STORE_SQM,
) -> Dict[str, Any]:
    """Annotate one cell with saturation + white-space score (0..100)."""
    pop = int(cell.get("population", 0) or 0)
    supply = cell.get("supply_sqm")
    if supply is None:
        supply = (cell.get("competitor_count", 0) or 0) * assumed_store_sqm

    sat = saturation_index(pop, supply, sqm_per_capita)

    # White-space opportunity: high when demand exists and saturation is low.
    if pop <= 0:
        ws = 0.0
    elif sat == float("inf"):
        ws = 0.0
    else:
        deficit = max(0.0, 1.0 - sat)          # 0..1, how far below balanced supply
        demand_weight = min(1.0, pop / 3000.0)  # cap at ~3k pop per hex
        ws = round(deficit * demand_weight * 100, 1)

    return {
        **cell,
        "supply_sqm": round(supply, 1),
        "saturation_index": sat if sat != float("inf") else None,
        "white_space_score": ws,
        "is_white_space": ws >= 40.0,
    }


def detect_white_space(
    cells: List[Dict[str, Any]],
    min_score: float = 40.0,
    sqm_per_capita: float = DEFAULT_SQM_PER_CAPITA,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    """Score all cells and return ranked white-space candidates."""
    scored = [score_cell(c, sqm_per_capita) for c in cells]
    candidates = [c for c in scored if c["white_space_score"] >= min_score]
    candidates.sort(key=lambda c: -c["white_space_score"])
    if limit:
        candidates = candidates[:limit]

    total_pop = sum(int(c.get("population", 0) or 0) for c in scored)
    served = [c for c in scored if c["saturation_index"] and c["saturation_index"] >= 1.0]
    return {
        "total_cells": len(scored),
        "white_space_cells": len(candidates),
        "total_population": total_pop,
        "saturated_cells": len(served),
        "candidates": candidates,
        "all_cells": scored,
    }
