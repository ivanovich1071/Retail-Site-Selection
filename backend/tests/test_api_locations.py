"""Integration tests for location CRUD endpoints."""
from backend.tests.conftest import requires_db


@requires_db
class TestLocations:
    def test_list_locations_returns_pagination_shape(self, client):
        r = client.get("/api/v1/locations")
        assert r.status_code == 200, r.text
        data = r.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert isinstance(data["items"], list)

    def test_create_requires_auth(self, client):
        r = client.post("/api/v1/locations", json={"address": "ул. Тестовая 1"})
        assert r.status_code == 401

    def test_create_get_delete_flow(self, client, auth_headers):
        # Create
        r = client.post(
            "/api/v1/locations",
            json={"address": "пр. Независимости 100, Минск", "name": "Тест-объект", "area_sqm": 350},
            headers=auth_headers,
        )
        assert r.status_code == 201, r.text
        loc = r.json()
        loc_id = loc["id"]
        assert loc["address"] == "пр. Независимости 100, Минск"

        # Get
        r = client.get(f"/api/v1/locations/{loc_id}")
        assert r.status_code == 200
        assert r.json()["id"] == loc_id

        # Delete
        r = client.delete(f"/api/v1/locations/{loc_id}", headers=auth_headers)
        assert r.status_code == 204

        # Confirm gone
        r = client.get(f"/api/v1/locations/{loc_id}")
        assert r.status_code == 404

    def test_get_missing_location(self, client):
        r = client.get("/api/v1/locations/99999999")
        assert r.status_code == 404
