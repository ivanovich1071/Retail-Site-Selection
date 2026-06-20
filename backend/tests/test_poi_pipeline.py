"""Tests for the POI normalization/dedup pipeline (no network)."""
from backend.app.spatial.poi_pipeline import (
    normalize_poi, deduplicate, normalize_and_dedupe, _haversine_m,
)


def test_normalize_node():
    el = {
        "type": "node", "id": 1, "lat": 53.9, "lon": 27.56,
        "tags": {"shop": "supermarket", "name": "Евроопт", "addr:street": "пр. Независимости"},
    }
    poi = normalize_poi(el)
    assert poi["brand_name"] == "Евроопт"
    assert poi["store_format"] == "supermarket"
    assert poi["external_id"] == "node/1"
    assert poi["source"] == "osm"
    assert "пр. Независимости" in poi["address"]


def test_normalize_way_with_center():
    el = {"type": "way", "id": 9, "center": {"lat": 53.91, "lon": 27.55}, "tags": {"shop": "mall"}}
    poi = normalize_poi(el)
    assert poi["store_format"] == "hypermarket"
    assert poi["latitude"] == 53.91


def test_normalize_missing_coords_returns_none():
    assert normalize_poi({"type": "node", "id": 2, "tags": {"shop": "convenience"}}) is None


def test_unknown_tag_maps_to_other():
    el = {"type": "node", "id": 3, "lat": 53.9, "lon": 27.5, "tags": {"shop": "bakery", "name": "X"}}
    assert normalize_poi(el)["store_format"] == "other"


def test_deduplicate_same_name_close():
    pois = [
        {"brand_name": "Евроопт", "latitude": 53.9000, "longitude": 27.5600},
        {"brand_name": "евроопт", "latitude": 53.90003, "longitude": 27.5600},  # ~3m, dup
        {"brand_name": "Евроопт", "latitude": 53.9100, "longitude": 27.5700},  # far, kept
    ]
    out = deduplicate(pois)
    assert len(out) == 2


def test_haversine_reasonable():
    d = _haversine_m(53.9, 27.56, 53.9, 27.57)
    assert 600 < d < 750  # ~0.01 deg lon at this latitude


def test_normalize_and_dedupe_pipeline():
    elements = [
        {"type": "node", "id": 1, "lat": 53.9, "lon": 27.56, "tags": {"shop": "supermarket", "name": "A"}},
        {"type": "node", "id": 2, "lat": 53.90001, "lon": 27.56, "tags": {"shop": "supermarket", "name": "A"}},
        {"type": "node", "id": 3, "tags": {"shop": "convenience"}},  # no coords, dropped
    ]
    out = normalize_and_dedupe(elements)
    assert len(out) == 1
