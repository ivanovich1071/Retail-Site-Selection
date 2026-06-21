"""Prediction explainability.

Uses SHAP when available; otherwise computes per-feature contributions via
leave-one-out perturbation against the model's own baseline (mean-imputed
feature). Returns a SHAP-style waterfall the frontend can render.
"""
import logging
from typing import Dict, Any, List

from backend.app.ml.feature_pipeline import MODEL_FEATURES, vector_to_array
from backend.app.ml.inference import get_model, predict_from_features

logger = logging.getLogger(__name__)


def _baseline_row(x: List[float]) -> List[float]:
    """Baseline = model means if linear, else the input itself (no shift)."""
    model = get_model()
    if model is not None and model.backend == "linear":
        return list(model.payload["means"])
    return list(x)


def explain(features: Dict[str, Any], top_k: int = 8) -> Dict[str, Any]:
    """Return ranked feature contributions toward the prediction."""
    x = vector_to_array(features)
    base = predict_from_features(features)["predicted_revenue_monthly"]

    model = get_model()
    # Try SHAP for native models.
    if model is not None and model.backend == "catboost" and model._native is not None:
        try:
            import shap
            explainer = shap.TreeExplainer(model._native)
            vals = explainer.shap_values([x])[0]
            contribs = [
                {"feature": MODEL_FEATURES[i], "contribution": round(float(vals[i]), 2)}
                for i in range(len(MODEL_FEATURES))
            ]
            return _format(contribs, base, "shap", top_k)
        except Exception as e:  # noqa: BLE001
            logger.info("SHAP unavailable, using perturbation (%s)", e)

    # Perturbation: replace each feature with baseline, measure delta.
    baseline = _baseline_row(x)
    contribs = []
    for i, name in enumerate(MODEL_FEATURES):
        perturbed = list(x)
        perturbed[i] = baseline[i]
        feat_perturbed = {n: perturbed[j] for j, n in enumerate(MODEL_FEATURES)}
        pred_wo = predict_from_features(feat_perturbed)["predicted_revenue_monthly"]
        contribs.append({"feature": name, "contribution": round(base - pred_wo, 2)})
    return _format(contribs, base, "perturbation", top_k)


def _format(contribs: List[Dict[str, Any]], base: float, method: str, top_k: int) -> Dict[str, Any]:
    ranked = sorted(contribs, key=lambda c: -abs(c["contribution"]))
    return {
        "prediction": base,
        "method": method,
        "top_features": ranked[:top_k],
        "all_contributions": ranked,
    }
