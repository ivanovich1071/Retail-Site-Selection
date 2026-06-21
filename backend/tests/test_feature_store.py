from backend.app.feature_store.spatial_features import (
    shannon_diversity, walkability_score, extract_spatial_features,
)
from backend.app.feature_store.temporal_features import (
    seasonality_amplitude, weekday_peak_ratio, extract_temporal_features,
)
from backend.app.feature_store.competition_features import (
    location_quotient, extract_competition_features,
)
from backend.app.feature_store.pipeline import build_feature_vector
from backend.app.feature_store.registry import registry, FeatureSpec


# ── spatial ──────────────────────────────────────────────────────────
def test_shannon_diversity_bounds():
    assert shannon_diversity({}) == 0.0
    assert shannon_diversity({"a": 10}) == 0.0           # single category
    even = shannon_diversity({"a": 5, "b": 5})
    assert even == 1.0                                    # perfectly even → max
    skew = shannon_diversity({"a": 9, "b": 1})
    assert 0 < skew < 1


def test_walkability_monotonic():
    low = walkability_score(0, 0, 0)
    high = walkability_score(50, 100, 1.0)
    assert high > low
    assert 0 <= high <= 1


def test_extract_spatial_features_keys():
    feats = extract_spatial_features({"population": 1000, "poi_count": 20})
    assert "walkability" in feats
    assert feats["population"] == 1000


# ── temporal ─────────────────────────────────────────────────────────
def test_seasonality_amplitude():
    assert seasonality_amplitude([]) == 0.0
    assert seasonality_amplitude([100, 100, 100]) == 0.0
    assert seasonality_amplitude([50, 150]) > 0


def test_weekday_peak_ratio():
    r = weekday_peak_ratio({"mon": 100, "tue": 100, "sat": 50, "sun": 50})
    assert r == 2.0


# ── competition ──────────────────────────────────────────────────────
def test_location_quotient():
    assert location_quotient(1.2, 0.6) == 2.0
    assert location_quotient(0.6, 0) == 0.0


def test_extract_competition_features():
    feats = extract_competition_features({
        "population": 3000, "competitor_count": 2,
        "competitor_distances": [120, 400],
    })
    assert feats["nearest_competitor_m"] == 120
    assert feats["competitor_count"] == 2


# ── pipeline + registry ──────────────────────────────────────────────
def test_build_feature_vector_groups():
    raw = {"population": 2000, "poi_count": 30, "monthly_demand": [80, 120],
           "competitor_count": 1, "competitor_distances": [300]}
    vec = build_feature_vector(raw)
    assert vec["version"] == "1.0"
    assert "population" in vec["features"]
    assert vec["groups"]["spatial"]
    assert vec["groups"]["competition"]


def test_registry_validate_flags_unknown():
    assert registry.validate({"population": 1, "bogus_feat": 2}) == ["bogus_feat"]


def test_registry_register_and_get():
    spec = FeatureSpec("test_feat", "spatial", "float", "test")
    registry.register(spec)
    assert registry.get("test_feat").group == "spatial"
