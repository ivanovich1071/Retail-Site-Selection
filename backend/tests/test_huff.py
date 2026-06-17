import pytest
from backend.app.services.huff import HuffService


def test_market_share_between_0_and_1():
    huff = HuffService(beta=2.0)
    result = huff.calculate_market_share(
        candidate_area_sqm=300,
        candidate_travel_times=[300],
        population_zones=[{"population": 5000, "travel_time_s": 300}],
        all_stores=[{"area_sqm": 400, "travel_time_s": 450}],
    )
    assert 0 <= result["market_share"] <= 1


def test_larger_store_gets_more_share():
    huff = HuffService(beta=2.0)
    small = huff.calculate_market_share(
        candidate_area_sqm=100,
        candidate_travel_times=[300],
        population_zones=[{"population": 5000, "travel_time_s": 300}],
        all_stores=[{"area_sqm": 400, "travel_time_s": 450}],
    )
    large = huff.calculate_market_share(
        candidate_area_sqm=2000,
        candidate_travel_times=[300],
        population_zones=[{"population": 5000, "travel_time_s": 300}],
        all_stores=[{"area_sqm": 400, "travel_time_s": 450}],
    )
    assert large["market_share"] > small["market_share"]


def test_no_competition_high_share():
    huff = HuffService(beta=2.0)
    result = huff.calculate_market_share(
        candidate_area_sqm=500,
        candidate_travel_times=[300],
        population_zones=[{"population": 10000, "travel_time_s": 300}],
        all_stores=[],
    )
    assert result["market_share"] == pytest.approx(1.0)


def test_empty_zones_returns_zero():
    huff = HuffService()
    result = huff.calculate_market_share(500, [], [], [])
    assert result["market_share"] == 0.0
