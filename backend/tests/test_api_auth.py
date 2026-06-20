"""Integration tests for auth endpoints."""
from uuid import uuid4

from backend.tests.conftest import requires_db


@requires_db
class TestAuth:
    def test_register_login_me_flow(self, client):
        email = f"flow_{uuid4().hex[:8]}@eurotor.by"
        password = "pass12345"

        # Register
        r = client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password, "full_name": "Flow User"},
        )
        assert r.status_code == 201, r.text
        assert r.json()["email"] == email

        # Login
        r = client.post(
            "/api/v1/auth/token",
            data={"username": email, "password": password},
        )
        assert r.status_code == 200, r.text
        token = r.json()["access_token"]
        assert token

        # Me
        r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200, r.text
        assert r.json()["email"] == email

    def test_login_wrong_password(self, client):
        email = f"wrong_{uuid4().hex[:8]}@eurotor.by"
        client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "correct123"},
        )
        r = client.post(
            "/api/v1/auth/token",
            data={"username": email, "password": "incorrect"},
        )
        assert r.status_code == 400

    def test_me_without_token(self, client):
        r = client.get("/api/v1/auth/me")
        assert r.status_code == 401

    def test_duplicate_registration(self, client):
        email = f"dup_{uuid4().hex[:8]}@eurotor.by"
        body = {"email": email, "password": "pass12345"}
        r1 = client.post("/api/v1/auth/register", json=body)
        assert r1.status_code == 201
        r2 = client.post("/api/v1/auth/register", json=body)
        assert r2.status_code == 400
