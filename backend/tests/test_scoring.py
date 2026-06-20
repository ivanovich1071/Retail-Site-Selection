from backend.app.services.scoring import ScoringService


def make_scorer(**overrides):
    return ScoringService()


def base_kwargs():
    return dict(
        population_10min=10000,
        avg_salary=1500,
        competitors_count=3,
        nearest_competitor_m=600,
        isochrone_area_sqkm=3.14,
        parking_spaces=20,
        visibility_score=7.0,
        area_sqm=300,
        has_cannibalization=False,
    )


def test_score_in_range():
    scorer = make_scorer()
    result = scorer.calculate(**base_kwargs())
    assert 0 <= result["total_score"] <= 100


def test_cannibalization_penalty():
    scorer = make_scorer()
    without = scorer.calculate(**base_kwargs())["total_score"]
    with_cann = scorer.calculate(**{**base_kwargs(), "has_cannibalization": True})["total_score"]
    assert with_cann < without


def test_zero_population_does_not_crash():
    scorer = make_scorer()
    result = scorer.calculate(**{**base_kwargs(), "population_10min": 0})
    assert result["total_score"] >= 0


def test_many_competitors_lower_score():
    scorer = make_scorer()
    few = scorer.calculate(**{**base_kwargs(), "competitors_count": 2})["total_score"]
    many = scorer.calculate(**{**base_kwargs(), "competitors_count": 15})["total_score"]
    assert many < few


def test_component_keys_present():
    scorer = make_scorer()
    result = scorer.calculate(**base_kwargs())
    for key in ["score_demographics", "score_competitors", "score_accessibility", "score_visibility", "score_location"]:
        assert key in result
