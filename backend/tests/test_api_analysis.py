"""Integration test for the analysis pipeline with external APIs mocked."""
from unittest.mock import patch, AsyncMock

from backend.tests.conftest import requires_db

FAKE_ISOCHRONES = {
    "features": [
        {
            "properties": {"value": 300, "area": 800_000, "total_pop": 3200},
            "geometry": {"type": "Polygon", "coordinates": [[[27.55, 53.89], [27.57, 53.89], [27.57, 53.91], [27.55, 53.91], [27.55, 53.89]]]},
        },
        {
            "properties": {"value": 600, "area": 2_500_000, "total_pop": 9800},
            "geometry": {"type": "Polygon", "coordinates": [[[27.54, 53.88], [27.58, 53.88], [27.58, 53.92], [27.54, 53.92], [27.54, 53.88]]]},
        },
    ]
}

FAKE_COMPETITORS = [
    {"id": "c1", "name": "Евроопт", "point": {"lat": 53.903, "lon": 27.565}},
    {"id": "c2", "name": "Хит!", "point": {"lat": 53.897, "lon": 27.558}},
]


@requires_db
class TestAnalysisByAddress:
    def test_by_address_full_pipeline(self, client):
        with patch(
            "backend.app.api.v1.endpoints.analysis.GeocodeService.geocode",
            new=AsyncMock(return_value=(27.5615, 53.9006)),
        ), patch(
            "backend.app.api.v1.endpoints.analysis.IsochroneService.get_isochrones",
            new=AsyncMock(return_value=FAKE_ISOCHRONES),
        ), patch(
            "backend.app.api.v1.endpoints.analysis.TwoGISClient.search_competitors",
            new=AsyncMock(return_value=FAKE_COMPETITORS),
        ):
            r = client.post(
                "/api/v1/analysis/by-address",
                json={"address": "пр. Независимости 95, Минск", "area_sqm": 400, "isochrone_minutes": [5, 10]},
            )

        assert r.status_code == 200, r.text
        data = r.json()
        assert data["latitude"] == 53.9006
        assert data["longitude"] == 27.5615
        assert len(data["isochrones"]) == 2
        assert len(data["competitors_nearby"]) == 2
        assert 0 <= data["scoring"]["total_score"] <= 100

    def test_geocode_failure_returns_422(self, client):
        from backend.app.core.exceptions import GeocodeError

        with patch(
            "backend.app.api.v1.endpoints.analysis.GeocodeService.geocode",
            new=AsyncMock(side_effect=GeocodeError("address not found")),
        ):
            r = client.post(
                "/api/v1/analysis/by-address",
                json={"address": "несуществующий адрес"},
            )
        assert r.status_code == 422


class TestH3Endpoints:
    """H3 endpoints need no DB — always run."""

    def test_polyfill(self, client):
        r = client.post(
            "/api/v1/h3/polyfill",
            json={
                "polygon": {"type": "Polygon", "coordinates": [[[27.50, 53.85], [27.60, 53.85], [27.60, 53.95], [27.50, 53.95], [27.50, 53.85]]]},
                "resolution": 7,
            },
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["total_cells"] > 0
        assert data["resolution"] == 7
        assert data["geojson"]["type"] == "FeatureCollection"

    def test_neighbors(self, client):
        # First get a valid cell from polyfill
        r = client.post(
            "/api/v1/h3/polyfill",
            json={
                "polygon": {"type": "Polygon", "coordinates": [[[27.50, 53.85], [27.60, 53.85], [27.60, 53.95], [27.50, 53.95], [27.50, 53.85]]]},
                "resolution": 7,
            },
        )
        cell = r.json()["cells"][0]["h3_index"]
        r2 = client.get(f"/api/v1/h3/neighbors/{cell}")
        assert r2.status_code == 200
        assert len(r2.json()) == 7  # center + 6 neighbors
