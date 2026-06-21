import math

import pytest

from backend.app.competition.overlap import (
    circle_overlap_area, overlap_circles, pairwise_overlaps,
)
from backend.app.competition.cannibalization import estimate_cannibalization
from backend.app.competition.white_space import (
    saturation_index, score_cell, detect_white_space,
)
from backend.app.competition.market_graph import build_graph, competitive_pressure
from backend.app.competition.huff_engine import allocate_shares, calibrate_beta


# ── overlap ──────────────────────────────────────────────────────────
def test_disjoint_circles_no_overlap():
    assert circle_overlap_area(100, 100, 500) == 0.0


def test_identical_circles_full_overlap():
    area = math.pi * 100 ** 2
    assert circle_overlap_area(100, 100, 0) == pytest.approx(area)


def test_contained_circle():
    # small circle fully inside large one
    assert circle_overlap_area(50, 200, 10) == pytest.approx(math.pi * 50 ** 2)


def test_overlap_circles_ratios_between_0_and_1():
    m = overlap_circles(53.9, 27.56, 800, 53.905, 27.57, 800)
    assert 0 <= m["overlap_ratio"] <= 1
    assert 0 <= m["jaccard"] <= 1
    assert m["intersection_m2"] > 0


def test_pairwise_overlaps_skips_disjoint():
    zones = [
        {"id": "a", "lat": 53.9, "lon": 27.56, "radius_m": 300},
        {"id": "b", "lat": 53.95, "lon": 27.7, "radius_m": 300},  # far away
    ]
    assert pairwise_overlaps(zones) == []


# ── cannibalization ──────────────────────────────────────────────────
def test_no_own_stores_no_cannibalization():
    res = estimate_cannibalization(
        candidate={"lat": 53.9, "lon": 27.56, "area_sqm": 500},
        own_stores=[],
    )
    assert res["affected_stores"] == 0
    assert res["severity"] == "none"
    assert res["penalty_factor"] == 1.0


def test_close_own_store_triggers_cannibalization():
    res = estimate_cannibalization(
        candidate={"lat": 53.9, "lon": 27.56, "area_sqm": 1000, "catchment_radius_m": 800},
        own_stores=[{
            "id": 1, "lat": 53.9005, "lon": 27.561, "area_sqm": 500,
            "revenue_monthly": 100000, "catchment_radius_m": 800,
        }],
    )
    assert res["affected_stores"] == 1
    assert res["total_revenue_at_risk"] > 0
    assert res["penalty_factor"] < 1.0


# ── white-space ──────────────────────────────────────────────────────
def test_saturation_under_one_is_underserved():
    # high pop, low supply
    assert saturation_index(5000, 100) < 1.0


def test_zero_population_not_white_space():
    cell = score_cell({"population": 0, "competitor_count": 0})
    assert cell["white_space_score"] == 0.0
    assert cell["is_white_space"] is False


def test_detect_white_space_ranks_candidates():
    cells = [
        {"h3_index": "a", "population": 4000, "competitor_count": 0},  # underserved
        {"h3_index": "b", "population": 500, "competitor_count": 5},   # saturated
    ]
    res = detect_white_space(cells, min_score=20)
    assert res["candidates"]
    assert res["candidates"][0]["h3_index"] == "a"


# ── market graph ─────────────────────────────────────────────────────
def test_competitive_pressure_counts_neighbors():
    stores = [
        {"id": 1, "lat": 53.9, "lon": 27.56, "catchment_radius_m": 800},
        {"id": 2, "lat": 53.9008, "lon": 27.561, "catchment_radius_m": 800},
        {"id": 3, "lat": 53.99, "lon": 27.9, "catchment_radius_m": 800},  # isolated
    ]
    p = competitive_pressure(stores)
    assert p[1]["degree"] == 1
    assert p[3]["degree"] == 0


def test_build_graph_returns_nodes_and_edges():
    stores = [
        {"id": 1, "lat": 53.9, "lon": 27.56},
        {"id": 2, "lat": 53.9008, "lon": 27.561},
    ]
    g = build_graph(stores)
    assert len(g["nodes"]) == 2
    assert g["most_pressured"] in (1, 2)


# ── huff engine ──────────────────────────────────────────────────────
def test_allocate_shares_sum_to_population():
    stores = [{"id": 1, "area_sqm": 500}, {"id": 2, "area_sqm": 500}]
    zones = [{"population": 1000, "store_travel_times": {1: 300, 2: 300}}]
    alloc = allocate_shares(stores, zones)
    total = sum(s["customers"] for s in alloc["shares"].values())
    assert abs(total - 1000) <= 1
    # equal stores, equal times → ~50/50
    assert alloc["shares"][1]["market_share"] == pytest.approx(0.5, abs=0.01)


def test_calibrate_beta_recovers_known_beta():
    stores = [{"id": 1, "area_sqm": 800}, {"id": 2, "area_sqm": 400}]
    zones = [{"population": 1000, "store_travel_times": {1: 600, 2: 300}}]
    truth = allocate_shares(stores, zones, beta=2.5)
    observed = {sid: v["market_share"] for sid, v in truth["shares"].items()}
    best_beta, err = calibrate_beta(stores, zones, observed)
    assert abs(best_beta - 2.5) <= 0.5
    assert err < 1e-3


