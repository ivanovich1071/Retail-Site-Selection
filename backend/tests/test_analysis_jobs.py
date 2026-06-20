"""Integration tests for the job-based analysis pipeline."""
from unittest.mock import patch, AsyncMock

from backend.tests.conftest import requires_db

FAKE_ISO = {
    "features": [
        {"properties": {"value": 300, "area": 800_000, "total_pop": 3200},
         "geometry": {"type": "Polygon", "coordinates": [[[27.55, 53.89], [27.57, 53.89], [27.57, 53.91], [27.55, 53.91], [27.55, 53.89]]]}},
        {"properties": {"value": 600, "area": 2_500_000, "total_pop": 9800},
         "geometry": {"type": "Polygon", "coordinates": [[[27.54, 53.88], [27.58, 53.88], [27.58, 53.92], [27.54, 53.92], [27.54, 53.88]]]}},
    ]
}
FAKE_COMP = [{"id": "c1", "name": "Евроопт", "point": {"lat": 53.903, "lon": 27.565}}]


def _patches():
    return (
        patch("backend.app.orchestrator.analysis_orchestrator.GeocodeService.geocode",
              new=AsyncMock(return_value=(27.5615, 53.9006))),
        patch("backend.app.orchestrator.analysis_orchestrator.IsochroneService.get_isochrones",
              new=AsyncMock(return_value=FAKE_ISO)),
        patch("backend.app.orchestrator.analysis_orchestrator.TwoGISClient.search_competitors",
              new=AsyncMock(return_value=FAKE_COMP)),
    )


@requires_db
class TestAnalysisJobs:
    def test_start_runs_to_completion(self, client):
        p1, p2, p3 = _patches()
        with p1, p2, p3:
            r = client.post(
                "/api/v1/analysis/start",
                json={"address": "пр. Независимости 95", "area_sqm": 400, "isochrone_minutes": [5, 10]},
            )
            assert r.status_code == 202, r.text
            job_id = r.json()["id"]

            # Background task completed before TestClient returned the response.
            r2 = client.get(f"/api/v1/analysis/jobs/{job_id}")
            assert r2.status_code == 200
            data = r2.json()
            assert data["status"] == "completed"
            assert data["progress_pct"] == 100
            assert data["result"]["scoring"]["total_score"] >= 0

    def test_start_requires_input(self, client):
        r = client.post("/api/v1/analysis/start", json={})
        assert r.status_code == 422

    def test_polygon_job(self, client):
        p1, p2, p3 = _patches()
        with p1, p2, p3:
            r = client.post(
                "/api/v1/analysis/start",
                json={"polygon": {"type": "Polygon", "coordinates": [[[27.55, 53.89], [27.57, 53.89], [27.57, 53.91], [27.55, 53.89]]]}},
            )
            assert r.status_code == 202
            job_id = r.json()["id"]
            data = client.get(f"/api/v1/analysis/jobs/{job_id}").json()
            assert data["status"] == "completed"

    def test_list_jobs(self, client):
        r = client.get("/api/v1/analysis/jobs")
        assert r.status_code == 200
        assert "items" in r.json() and "total" in r.json()

    def test_get_missing_job(self, client):
        r = client.get("/api/v1/analysis/jobs/99999999")
        assert r.status_code == 404

    def test_recalculate(self, client):
        p1, p2, p3 = _patches()
        with p1, p2, p3:
            r = client.post("/api/v1/analysis/start", json={"address": "ул. Тестовая 1"})
            job_id = r.json()["id"]
            r2 = client.post(f"/api/v1/analysis/jobs/{job_id}/recalculate")
            assert r2.status_code == 202
            assert r2.json()["id"] != job_id


@requires_db
class TestLocationStatusWorkflow:
    def test_valid_transition(self, client, auth_headers):
        loc = client.post("/api/v1/locations", json={"address": "ул. Воркфлоу 1"}, headers=auth_headers).json()
        r = client.patch(
            f"/api/v1/locations/{loc['id']}/status",
            json={"status": "in_review", "comment": "на проверку"},
            headers=auth_headers,
        )
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "in_review"

    def test_invalid_transition(self, client, auth_headers):
        loc = client.post("/api/v1/locations", json={"address": "ул. Воркфлоу 2"}, headers=auth_headers).json()
        # draft → approved is not allowed (must go through in_review)
        r = client.patch(
            f"/api/v1/locations/{loc['id']}/status",
            json={"status": "approved"},
            headers=auth_headers,
        )
        assert r.status_code == 422

    def test_status_requires_auth(self, client):
        r = client.patch("/api/v1/locations/1/status", json={"status": "approved"})
        assert r.status_code == 401
