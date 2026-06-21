"""What-if scenario engine.

A baseline state is the set of inputs to ScoringService.calculate (+ optional
Huff inputs). Scenarios mutate that state and recompute, returning a delta.
"""
import copy
import logging
from typing import Dict, Any, List

from backend.app.services.scoring import ScoringService

logger = logging.getLogger(__name__)

SCORING_KEYS = (
    "population_10min", "avg_salary", "competitors_count", "nearest_competitor_m",
    "isochrone_area_sqkm", "parking_spaces", "visibility_score", "area_sqm",
    "has_cannibalization",
)


def _score(state: Dict[str, Any]) -> Dict[str, Any]:
    scoring = ScoringService()
    kwargs = {k: state.get(k) for k in SCORING_KEYS if k in state}
    kwargs.setdefault("population_10min", 0)
    kwargs.setdefault("avg_salary", 1000)
    kwargs.setdefault("competitors_count", 0)
    kwargs.setdefault("isochrone_area_sqkm", 1.0)
    return scoring.calculate(**kwargs)


def apply_scenario(state: Dict[str, Any], scenario: Dict[str, Any]) -> Dict[str, Any]:
    """Mutate a copy of state per scenario type. Returns the new state."""
    s = copy.deepcopy(state)
    kind = scenario.get("type")

    if kind == "competitor_opening":
        s["competitors_count"] = s.get("competitors_count", 0) + scenario.get("count", 1)
        dist = scenario.get("distance_m")
        if dist is not None:
            cur = s.get("nearest_competitor_m")
            s["nearest_competitor_m"] = dist if cur is None else min(cur, dist)

    elif kind == "competitor_closing":
        s["competitors_count"] = max(0, s.get("competitors_count", 0) - scenario.get("count", 1))

    elif kind == "parking_change":
        s["parking_spaces"] = max(0, (s.get("parking_spaces") or 0) + scenario.get("delta", 0))

    elif kind == "economic_shock":
        factor = scenario.get("income_factor", 1.0)
        s["avg_salary"] = (s.get("avg_salary") or 1000) * factor
        pop_factor = scenario.get("population_factor", 1.0)
        s["population_10min"] = int((s.get("population_10min") or 0) * pop_factor)

    elif kind == "visibility_change":
        s["visibility_score"] = max(0.0, min(10.0, (s.get("visibility_score") or 5.0) + scenario.get("delta", 0)))

    else:
        logger.warning("Unknown scenario type: %s", kind)

    return s


def run_scenario(baseline: Dict[str, Any], scenario: Dict[str, Any]) -> Dict[str, Any]:
    """Run a single scenario and return before/after + delta."""
    base_score = _score(baseline)
    new_state = apply_scenario(baseline, scenario)
    new_score = _score(new_state)
    delta = round(new_score["total_score"] - base_score["total_score"], 1)
    return {
        "scenario": scenario,
        "baseline_score": base_score["total_score"],
        "scenario_score": new_score["total_score"],
        "delta": delta,
        "impact": "positive" if delta > 1 else "negative" if delta < -1 else "neutral",
        "baseline_breakdown": base_score,
        "scenario_breakdown": new_score,
    }


def run_scenarios(baseline: Dict[str, Any], scenarios: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Run several scenarios against one baseline, ranked by impact."""
    results = [run_scenario(baseline, sc) for sc in scenarios]
    results.sort(key=lambda r: r["delta"])
    return {
        "baseline_score": _score(baseline)["total_score"],
        "results": results,
        "worst_case": results[0] if results else None,
        "best_case": results[-1] if results else None,
    }
