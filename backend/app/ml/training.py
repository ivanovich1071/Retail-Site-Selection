"""Revenue model training.

Uses CatBoost when available; otherwise fits a closed-form ridge linear
regression (pure Python) so the pipeline trains and persists without heavy
deps. Models are persisted as JSON (linear) or .cbm (CatBoost) under
settings.ML_MODEL_DIR.
"""
import json
import logging
import os
from typing import List, Dict, Any, Optional

from backend.app.core.config import settings
from backend.app.ml.feature_pipeline import MODEL_FEATURES

logger = logging.getLogger(__name__)


def _standardize(X: List[List[float]]):
    n_feat = len(X[0]) if X else 0
    means = [0.0] * n_feat
    stds = [1.0] * n_feat
    n = len(X)
    for j in range(n_feat):
        col = [row[j] for row in X]
        m = sum(col) / n
        var = sum((c - m) ** 2 for c in col) / n
        means[j] = m
        stds[j] = (var ** 0.5) or 1.0
    Xs = [[(row[j] - means[j]) / stds[j] for j in range(n_feat)] for row in X]
    return Xs, means, stds


def _ridge_fit(X: List[List[float]], y: List[float], lam: float = 1.0) -> List[float]:
    """Closed-form ridge regression with intercept. Returns weights [b0, w...]."""
    Xs = [[1.0] + row for row in X]  # bias column
    n_feat = len(Xs[0])
    # Normal equations: (X^T X + lam I) w = X^T y  (no reg on bias)
    XtX = [[0.0] * n_feat for _ in range(n_feat)]
    Xty = [0.0] * n_feat
    for i in range(len(Xs)):
        xi = Xs[i]
        yi = y[i]
        for a in range(n_feat):
            Xty[a] += xi[a] * yi
            for b in range(n_feat):
                XtX[a][b] += xi[a] * xi[b]
    for a in range(1, n_feat):
        XtX[a][a] += lam
    return _solve(XtX, Xty)


def _solve(A: List[List[float]], b: List[float]) -> List[float]:
    """Gaussian elimination with partial pivoting."""
    n = len(b)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(M[r][col]))
        M[col], M[piv] = M[piv], M[col]
        if abs(M[col][col]) < 1e-12:
            M[col][col] = 1e-12
        pivval = M[col][col]
        for r in range(n):
            if r == col:
                continue
            factor = M[r][col] / pivval
            for c in range(col, n + 1):
                M[r][c] -= factor * M[col][c]
    return [M[r][n] / M[r][r] for r in range(n)]


class RevenueModel:
    """Wrapper around CatBoost or the linear fallback."""

    def __init__(self, backend: str, payload: Dict[str, Any], native=None):
        self.backend = backend
        self.payload = payload
        self._native = native

    def predict(self, x: List[float]) -> float:
        if self.backend == "catboost" and self._native is not None:
            return float(self._native.predict([x])[0])
        # linear: standardize then dot with weights
        means = self.payload["means"]
        stds = self.payload["stds"]
        w = self.payload["weights"]
        xs = [1.0] + [(x[j] - means[j]) / stds[j] for j in range(len(x))]
        return float(sum(wi * xi for wi, xi in zip(w, xs)))


def train(
    X: List[List[float]],
    y: List[float],
    prefer_catboost: bool = True,
) -> RevenueModel:
    """Fit a revenue model. Tries CatBoost, falls back to ridge."""
    if not X:
        raise ValueError("empty training set")

    if prefer_catboost:
        try:
            from catboost import CatBoostRegressor
            model = CatBoostRegressor(iterations=200, depth=6, learning_rate=0.1, verbose=False)
            model.fit(X, y)
            logger.info("Trained CatBoost revenue model on %d rows", len(X))
            return RevenueModel("catboost", {"features": MODEL_FEATURES}, native=model)
        except Exception as e:  # noqa: BLE001
            logger.info("CatBoost unavailable, using ridge fallback (%s)", e)

    Xs, means, stds = _standardize(X)
    weights = _ridge_fit(Xs, y)
    payload = {"weights": weights, "means": means, "stds": stds, "features": MODEL_FEATURES}
    logger.info("Trained ridge revenue model on %d rows", len(X))
    return RevenueModel("linear", payload)


def save_model(model: RevenueModel, name: str = "revenue") -> str:
    os.makedirs(settings.ML_MODEL_DIR, exist_ok=True)
    if model.backend == "catboost" and model._native is not None:
        path = os.path.join(settings.ML_MODEL_DIR, f"{name}.cbm")
        model._native.save_model(path)
    else:
        path = os.path.join(settings.ML_MODEL_DIR, f"{name}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"backend": model.backend, "payload": model.payload}, f)
    return path


def load_model(name: str = "revenue") -> Optional[RevenueModel]:
    cbm = os.path.join(settings.ML_MODEL_DIR, f"{name}.cbm")
    js = os.path.join(settings.ML_MODEL_DIR, f"{name}.json")
    if os.path.exists(cbm):
        try:
            from catboost import CatBoostRegressor
            m = CatBoostRegressor()
            m.load_model(cbm)
            return RevenueModel("catboost", {"features": MODEL_FEATURES}, native=m)
        except Exception as e:  # noqa: BLE001
            logger.warning("Failed to load CatBoost model (%s)", e)
    if os.path.exists(js):
        with open(js, encoding="utf-8") as f:
            data = json.load(f)
        return RevenueModel(data["backend"], data["payload"])
    return None
