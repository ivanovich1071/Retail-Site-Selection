"""Revenue prediction API layer — caches a loaded model in-process."""
import logging
from typing import Dict, Any, Optional

from backend.app.ml.feature_pipeline import raw_to_array, vector_to_array
from backend.app.ml.training import RevenueModel, load_model

logger = logging.getLogger(__name__)

_MODEL: Optional[RevenueModel] = None


def _heuristic(features: Dict[str, Any]) -> float:
    """Cold-start revenue proxy when no model is trained yet (monthly BYN)."""
    pop = float(features.get("population", 0) or 0)
    income = float(features.get("avg_income", 1000) or 1000)
    sat = float(features.get("saturation_index", 1.0) or 1.0)
    walk = float(features.get("walkability", 0.5) or 0.5)
    base = pop * 0.04 * (income / 1000.0)
    competition_factor = 1.0 / (1.0 + max(0.0, sat))
    return round(base * competition_factor * (0.7 + 0.6 * walk), 2)


def get_model() -> Optional[RevenueModel]:
    global _MODEL
    if _MODEL is None:
        _MODEL = load_model()
    return _MODEL


def set_model(model: RevenueModel) -> None:
    global _MODEL
    _MODEL = model


def predict_from_features(features: Dict[str, Any]) -> Dict[str, Any]:
    model = get_model()
    x = vector_to_array(features)
    if model is None:
        return {
            "predicted_revenue_monthly": _heuristic(features),
            "model": "heuristic",
            "confidence": 0.4,
        }
    pred = max(0.0, model.predict(x))
    return {
        "predicted_revenue_monthly": round(pred, 2),
        "model": model.backend,
        "confidence": 0.75,
    }


def predict_from_raw(raw: Dict[str, Any]) -> Dict[str, Any]:
    x, features = raw_to_array(raw)
    result = predict_from_features(features)
    result["features_used"] = features
    return result
