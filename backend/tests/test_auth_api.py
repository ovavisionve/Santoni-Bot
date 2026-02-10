"""
Tests for auth API endpoints: POST /api/auth/login, GET /api/auth/me.
"""

import pytest
from fastapi.testclient import TestClient

from app.models.user import User


# ---------------------------------------------------------------------------
# POST /api/auth/login
# ---------------------------------------------------------------------------

class TestLogin:
    """Tests for the login endpoint."""

    def test_login_success(self, client: TestClient, regular_user: User):
        """Successful login should return an access token."""
        response = client.post(
            "/api/auth/login",
            json={"username": "vendedor1", "password": "vende123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 0

    def test_login_admin(self, client: TestClient, admin_user: User):
        """Admin login should return a valid token."""
        response = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    def test_login_wrong_password(self, client: TestClient, regular_user: User):
        """Login with wrong password should return 401."""
        response = client.post(
            "/api/auth/login",
            json={"username": "vendedor1", "password": "wrong_password"},
        )
        assert response.status_code == 401
        assert "Credenciales incorrectas" in response.json()["detail"]

    def test_login_user_not_found(self, client: TestClient):
        """Login with non-existent user should return 401."""
        response = client.post(
            "/api/auth/login",
            json={"username": "ghost_user", "password": "whatever"},
        )
        assert response.status_code == 401

    def test_login_inactive_user(self, client: TestClient, inactive_user: User):
        """Login with inactive user should return 401."""
        response = client.post(
            "/api/auth/login",
            json={"username": "inactivo", "password": "inactive123"},
        )
        assert response.status_code == 401

    def test_login_missing_username(self, client: TestClient):
        """Login without username field should return 422 validation error."""
        response = client.post(
            "/api/auth/login",
            json={"password": "test"},
        )
        assert response.status_code == 422

    def test_login_missing_password(self, client: TestClient):
        """Login without password field should return 422 validation error."""
        response = client.post(
            "/api/auth/login",
            json={"username": "admin"},
        )
        assert response.status_code == 422

    def test_login_empty_body(self, client: TestClient):
        """Login with empty body should return 422."""
        response = client.post("/api/auth/login", json={})
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/auth/me
# ---------------------------------------------------------------------------

class TestGetMe:
    """Tests for the /api/auth/me endpoint."""

    def test_get_me_authenticated(self, client: TestClient, admin_user: User, admin_headers: dict):
        """Authenticated user should get their profile data."""
        response = client.get("/api/auth/me", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "admin"
        assert data["email"] == "admin@santoni.com"
        assert data["full_name"] == "Admin Santoni"
        assert data["role"] == "administrador"
        assert data["is_active"] is True

    def test_get_me_regular_user(self, client: TestClient, regular_user: User, regular_headers: dict):
        """Regular user should see their own profile."""
        response = client.get("/api/auth/me", headers=regular_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "vendedor1"
        assert data["department"] == "ventas"
        assert data["role"] == "usuario"

    def test_get_me_unauthenticated(self, client: TestClient):
        """Request without auth header should return 403 (HTTPBearer returns 403)."""
        response = client.get("/api/auth/me")
        assert response.status_code == 403

    def test_get_me_invalid_token(self, client: TestClient):
        """Request with invalid token should return 401."""
        headers = {"Authorization": "Bearer invalid.jwt.token"}
        response = client.get("/api/auth/me", headers=headers)
        assert response.status_code == 401

    def test_get_me_with_login_flow(self, client: TestClient, regular_user: User):
        """Full flow: login, then use token to access /me."""
        # Step 1: Login
        login_response = client.post(
            "/api/auth/login",
            json={"username": "vendedor1", "password": "vende123"},
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # Step 2: Use the token
        me_response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me_response.status_code == 200
        assert me_response.json()["username"] == "vendedor1"

    def test_get_me_supervisor_has_extra_departments(
        self, client: TestClient, supervisor_user: User, supervisor_headers: dict
    ):
        """Supervisor should have extra_departments in profile."""
        response = client.get("/api/auth/me", headers=supervisor_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "supervisor"
        assert data["extra_departments"] == "finanzas"
