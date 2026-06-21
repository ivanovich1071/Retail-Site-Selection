"""Temporal feature extraction — seasonality and weekday/weekend patterns.

Inputs are simple demand series (e.g. footfall counts) keyed by month or by
weekday. Produces normalised amplitude/ratio features for the feature store.
"""
import logging
from statistics import mean
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


def seasonality_amplitude(monthly: List[float]) -> float:
    """Relative seasonal swing: (max-min)/mean, clamped to a sane range."""
    vals = [v for v in monthly if v is not None]
    if len(vals) < 2 or mean(vals) == 0:
        return 0.0
    return round((max(vals) - min(vals)) / mean(vals), 4)


def weekday_peak_ratio(by_weekday: Dict[str, float]) -> float:
    """Mean weekday demand / mean weekend demand (Sat, Sun)."""
    weekend_keys = {"sat", "sun", "saturday", "sunday"}
    weekday, weekend = [], []
    for k, v in by_weekday.items():
        (weekend if k.lower() in weekend_keys else weekday).append(v)
    if not weekend or mean(weekend) == 0 or not weekday:
        return 0.0
    return round(mean(weekday) / mean(weekend), 4)


def extract_temporal_features(raw: Dict[str, Any]) -> Dict[str, Any]:
    """raw expects: monthly_demand (list[12]), weekday_demand (dict)."""
    monthly = raw.get("monthly_demand", []) or []
    weekday = raw.get("weekday_demand", {}) or {}
    return {
        "seasonality_amp": seasonality_amplitude(monthly),
        "weekday_peak_ratio": weekday_peak_ratio(weekday),
    }
