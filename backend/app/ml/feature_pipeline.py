"""Feature extraction for ML — turns a feature-store vector into an ordered
numeric array the model consumes. Keeps a canonical feature order so training
and inference agree.
"""
import logging
from typing import Dict, Any, List, Tuple

from backend.app.feature_store.pipeline import build_feature_vector

logger = logging.getLogger(__name__)

# Canonical model feature order. Non-numeric / id features are excluded.
MODEL_FEATURES: List[str] = [
    "population",
    "density_per_sqkm",
    "avg_income",
    "walkability",
    "parking_count",
    "poi_diversity",
    "footfall_index",
    "seasonality_amp",
    "weekday_peak_ratio",
    "competitor_count",
    "saturation_index",
    "nearest_competitor_m",
    "location_quotient",
    "cannibalization_risk",
]

# Fallback values when a feature is missing/None.
_DEFAULTS = {
    "avg_income": 1000.0,
    "saturation_index": 1.0,
    "nearest_competitor_m": 1000.0,
}


def vector_to_array(features: Dict[str, Any]) -> List[float]:
    """Map a feature dict to the canonical numeric array."""
    row = []
    for name in MODEL_FEATURES:
        val = features.get(name)
        if val is None:
            val = _DEFAULTS.get(name, 0.0)
        row.append(float(val))
    return row


def raw_to_array(raw: Dict[str, Any]) -> Tuple[List[float], Dict[str, Any]]:
    """Build feature vector from raw data, then to model array. Returns (array, features)."""
    vec = build_feature_vector(raw)
    features = vec["features"]
    return vector_to_array(features), features


def build_dataset(raws: List[Dict[str, Any]], targets: List[float]) -> Tuple[List[List[float]], List[float]]:
    """Assemble (X, y) for training from raw rows + revenue targets."""
    if len(raws) != len(targets):
        raise ValueError("raws and targets length mismatch")
    X = [raw_to_array(r)[0] for r in raws]
    return X, list(targets)
