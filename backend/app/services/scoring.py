import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Default weights (sum to 1.0); can be overridden via settings/config
DEFAULT_WEIGHTS = {
    "demographics": 0.30,
    "competitors": 0.25,
    "accessibility": 0.20,
    "visibility": 0.15,
    "location": 0.10,
}


class ScoringService:
    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or DEFAULT_WEIGHTS

    def calculate(
        self,
        population_10min: int,
        avg_salary: float,
        competitors_count: int,
        nearest_competitor_m: Optional[float],
        isochrone_area_sqkm: float,
        parking_spaces: Optional[int],
        visibility_score: Optional[float],
        area_sqm: Optional[float],
        has_cannibalization: bool = False,
    ) -> Dict[str, Any]:
        """
        Calculates a 0–100 composite score and component breakdown.
        Returns dict with total_score and individual component scores.
        """
        # --- Demographics (0-100) ---
        # Population density proxy: people per km²
        density = population_10min / max(isochrone_area_sqkm, 0.01)
        score_demo = min(density / 50, 1.0) * 60  # 50 ppl/km² → 60 pts
        salary_bonus = min(avg_salary / 2000, 1.0) * 40  # 2000 BYN → 40 pts
        score_demographics = min(score_demo + salary_bonus, 100)

        # --- Competitors (0-100): fewer → higher score, but some presence is OK ---
        if competitors_count == 0:
            score_competitors = 70  # no competition but also no proven demand
        elif competitors_count <= 3:
            score_competitors = 100
        elif competitors_count <= 6:
            score_competitors = 75
        elif competitors_count <= 10:
            score_competitors = 50
        else:
            score_competitors = 25

        # Penalty if nearest competitor is very close
        if nearest_competitor_m and nearest_competitor_m < 200:
            score_competitors *= 0.6

        # --- Accessibility (0-100): parking and area ---
        score_accessibility = 50.0  # baseline
        if parking_spaces is not None:
            score_accessibility += min(parking_spaces / 50, 1.0) * 30
        if area_sqm:
            if area_sqm >= 300:
                score_accessibility += 20
            elif area_sqm >= 150:
                score_accessibility += 10
        score_accessibility = min(score_accessibility, 100)

        # --- Visibility (0-100): direct input 0–10 scaled ---
        score_visibility = (visibility_score or 5.0) * 10

        # --- Location (0-100): placeholder for TKP-45 compliance, etc. ---
        score_location = 70.0  # default until TKP data is integrated

        # Weighted composite
        total = (
            score_demographics * self.weights["demographics"]
            + score_competitors * self.weights["competitors"]
            + score_accessibility * self.weights["accessibility"]
            + score_visibility * self.weights["visibility"]
            + score_location * self.weights["location"]
        )

        # Cannibalization penalty: own store within 800 m
        if has_cannibalization:
            total *= 0.75

        total = max(0.0, min(100.0, total))

        return {
            "total_score": round(total, 1),
            "score_demographics": round(score_demographics, 1),
            "score_competitors": round(score_competitors, 1),
            "score_accessibility": round(score_accessibility, 1),
            "score_visibility": round(score_visibility, 1),
            "score_location": round(score_location, 1),
            "has_cannibalization": has_cannibalization,
        }
