from backend.app.simulation.scenarios import apply_scenario, run_scenario, run_scenarios


BASELINE = {
    "population_10min": 8000,
    "avg_salary": 1500,
    "competitors_count": 2,
    "nearest_competitor_m": 500,
    "isochrone_area_sqkm": 1.2,
    "parking_spaces": 20,
    "visibility_score": 6.0,
    "area_sqm": 400,
}


def test_competitor_opening_lowers_score():
    res = run_scenario(BASELINE, {"type": "competitor_opening", "count": 5, "distance_m": 100})
    assert res["scenario_score"] <= res["baseline_score"]
    assert res["impact"] in ("negative", "neutral")


def test_economic_shock_negative():
    res = run_scenario(BASELINE, {"type": "economic_shock", "income_factor": 0.6, "population_factor": 0.8})
    assert res["delta"] <= 0


def test_parking_increase_helps_or_neutral():
    res = run_scenario(BASELINE, {"type": "parking_change", "delta": 50})
    assert res["scenario_score"] >= res["baseline_score"] - 0.1


def test_apply_competitor_closing():
    s = apply_scenario(BASELINE, {"type": "competitor_closing", "count": 1})
    assert s["competitors_count"] == 1


def test_run_scenarios_ranks_best_worst():
    res = run_scenarios(BASELINE, [
        {"type": "competitor_opening", "count": 8, "distance_m": 50},
        {"type": "parking_change", "delta": 100},
    ])
    assert res["worst_case"]["delta"] <= res["best_case"]["delta"]
    assert len(res["results"]) == 2
