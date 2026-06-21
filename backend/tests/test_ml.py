from backend.app.ml.feature_pipeline import vector_to_array, raw_to_array, build_dataset, MODEL_FEATURES
from backend.app.ml.training import train, _ridge_fit, save_model, load_model
from backend.app.ml.inference import predict_from_raw, predict_from_features, set_model
from backend.app.ml.explainability import explain


def test_vector_to_array_length_and_order():
    arr = vector_to_array({"population": 100, "walkability": 0.5})
    assert len(arr) == len(MODEL_FEATURES)
    assert arr[0] == 100.0


def test_raw_to_array():
    arr, feats = raw_to_array({"population": 500, "poi_count": 10})
    assert len(arr) == len(MODEL_FEATURES)
    assert "walkability" in feats


def test_ridge_fits_linear_relationship():
    # y = 3*x0 + 2  → ridge should recover roughly
    X = [[float(i)] for i in range(20)]
    y = [3 * i + 2 for i in range(20)]
    w = _ridge_fit([[x[0]] for x in X], y, lam=0.01)
    assert abs(w[0] - 2) < 1.0   # intercept
    assert abs(w[1] - 3) < 0.5   # slope


def test_train_and_predict_linear():
    raws = [
        {"population": p, "avg_income": 1000, "competitor_count": 1}
        for p in (500, 1000, 2000, 3000, 4000)
    ]
    targets = [p * 0.05 for p in (500, 1000, 2000, 3000, 4000)]
    X, y = build_dataset(raws, targets)
    model = train(X, y, prefer_catboost=False)
    assert model.backend == "linear"
    pred = model.predict(vector_to_array({"population": 2500, "avg_income": 1000, "competitor_count": 1}))
    assert pred > 0


def test_heuristic_prediction_when_no_model():
    set_model(None)
    res = predict_from_features({"population": 3000, "avg_income": 1500, "saturation_index": 0.5})
    assert res["model"] == "heuristic"
    assert res["predicted_revenue_monthly"] > 0


def test_explain_returns_contributions():
    set_model(None)
    _, feats = raw_to_array({"population": 2000, "competitor_count": 3})
    exp = explain(feats, top_k=5)
    assert "top_features" in exp
    assert len(exp["top_features"]) <= 5


def test_save_and_load_roundtrip(tmp_path, monkeypatch):
    from backend.app.core.config import settings
    monkeypatch.setattr(settings, "ML_MODEL_DIR", str(tmp_path))
    raws = [{"population": p} for p in (100, 500, 1000)]
    X, y = build_dataset(raws, [10, 50, 100])
    model = train(X, y, prefer_catboost=False)
    path = save_model(model, "test_rev")
    assert path
    loaded = load_model("test_rev")
    assert loaded is not None
    assert loaded.backend == "linear"
