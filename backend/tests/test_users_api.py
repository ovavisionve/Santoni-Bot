"""
Tests for user CRUD API endpoints: /api/users.
All user management endpoints require admin role.
"""

import pytest
from fastapi.testclient import TestClient

from app.models.user import User


# ---------------------------------------------------------------------------
# GET /api/users  (list users - admin only)
# ---------------------------------------------------------------------------

class TestListUsers:
    """Tests for listing all users (admin-only endpoint)."""

    def test_list_users_as_admin(
        self, client: TestClient, admin_user: User, admin_headers: dict
    ):
        """Admin should be able to list all users."""
        response = client.get("/api/users/", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        # The admin user should be in the list
        usernames = [u["username"] for u in data]
        assert "admin" in usernames

    def test_list_users_as_regular_user_denied(
        self, client: TestClient, regular_user: User, regular_headers: dict
    ):
        """Regular user should be denied access to user list (403)."""
        response = client.get("/api/users/", headers=regular_headers)
        assert response.status_code == 403

    def test_list_users_as_supervisor_denied(
        self, client: TestClient, supervisor_user: User, supervisor_headers: dict
    ):
        """Supervisor (non-admin) should be denied access to user list (403)."""
        response = client.get("/api/users/", headers=supervisor_headers)
        assert response.status_code == 403

    def test_list_users_unauthenticated(self, client: TestClient):
        """Unauthenticated request should be rejected."""
        response = client.get("/api/users/")
        assert response.status_code == 403

    def test_list_users_includes_multiple(
        self, client: TestClient, admin_user: User, regular_user: User, admin_headers: dict
    ):
        """Admin should see all created users in the list."""
        response = client.get("/api/users/", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        usernames = [u["username"] for u in data]
        assert "admin" in usernames
        assert "vendedor1" in usernames


# ---------------------------------------------------------------------------
# POST /api/users  (create user - admin only)
# ---------------------------------------------------------------------------

class TestCreateUser:
    """Tests for creating new users."""

    def test_create_user_success(
        self, client: TestClient, admin_user: User, admin_headers: dict
    ):
        """Admin should be able to create a new user."""
        response = client.post(
            "/api/users/",
            headers=admin_headers,
            json={
                "email": "nuevo@santoni.com",
                "username": "nuevo_user",
                "full_name": "Nuevo Usuario",
                "password": "Nuevo123!",
                "role": "usuario",
                "department": "produccion",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "nuevo_user"
        assert data["email"] == "nuevo@santoni.com"
        assert data["department"] == "produccion"
        assert data["role"] == "usuario"
        assert data["is_active"] is True
        assert "id" in data

    def test_create_user_duplicate_username(
        self, client: TestClient, admin_user: User, regular_user: User, admin_headers: dict
    ):
        """Creating user with existing username should return 400."""
        response = client.post(
            "/api/users/",
            headers=admin_headers,
            json={
                "email": "different@santoni.com",
                "username": "vendedor1",  # Already exists
                "full_name": "Duplicate User",
                "password": "Pass123!",
                "role": "usuario",
                "department": "ventas",
            },
        )
        assert response.status_code == 400
        assert "Username ya registrado" in response.json()["detail"]

    def test_create_user_duplicate_email(
        self, client: TestClient, admin_user: User, regular_user: User, admin_headers: dict
    ):
        """Creating user with existing email should return 400."""
        response = client.post(
            "/api/users/",
            headers=admin_headers,
            json={
                "email": "vendedor@santoni.com",  # Already exists
                "username": "different_user",
                "full_name": "Duplicate Email",
                "password": "Pass123!",
                "role": "usuario",
                "department": "ventas",
            },
        )
        assert response.status_code == 400
        assert "Email ya registrado" in response.json()["detail"]

    def test_create_user_invalid_role(
        self, client: TestClient, admin_user: User, admin_headers: dict
    ):
        """Creating user with invalid role should return 400."""
        response = client.post(
            "/api/users/",
            headers=admin_headers,
            json={
                "email": "new@santoni.com",
                "username": "newuser",
                "full_name": "New User",
                "password": "Pass123!",
                "role": "superadmin",  # Invalid
                "department": "ventas",
            },
        )
        assert response.status_code == 400
        assert "Rol inv\u00e1lido" in response.json()["detail"]

    def test_create_user_invalid_department(
        self, client: TestClient, admin_user: User, admin_headers: dict
    ):
        """Creating user with invalid department should return 400."""
        response = client.post(
            "/api/users/",
            headers=admin_headers,
            json={
                "email": "new@santoni.com",
                "username": "newuser",
                "full_name": "New User",
                "password": "Pass123!",
                "role": "usuario",
                "department": "marketing",  # Invalid
            },
        )
        assert response.status_code == 400
        assert "Departamento inv\u00e1lido" in response.json()["detail"]

    def test_create_user_non_admin_denied(
        self, client: TestClient, regular_user: User, regular_headers: dict
    ):
        """Non-admin user should not be able to create users."""
        response = client.post(
            "/api/users/",
            headers=regular_headers,
            json={
                "email": "new@santoni.com",
                "username": "newuser",
                "full_name": "New User",
                "password": "Pass123!",
                "role": "usuario",
                "department": "ventas",
            },
        )
        assert response.status_code == 403

    def test_create_supervisor_with_extra_departments(
        self, client: TestClient, admin_user: User, admin_headers: dict
    ):
        """Admin should be able to create supervisor with extra departments."""
        response = client.post(
            "/api/users/",
            headers=admin_headers,
            json={
                "email": "super@santoni.com",
                "username": "super_new",
                "full_name": "New Supervisor",
                "password": "Pass123!",
                "role": "supervisor",
                "department": "ventas",
                "extra_departments": "finanzas,contabilidad",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["role"] == "supervisor"
        assert data["extra_departments"] == "finanzas,contabilidad"


# ---------------------------------------------------------------------------
# GET /api/users/{user_id}  (get single user - admin only)
# ---------------------------------------------------------------------------

class TestGetUser:
    """Tests for getting a single user by ID."""

    def test_get_user_by_id(
        self, client: TestClient, admin_user: User, regular_user: User, admin_headers: dict
    ):
        """Admin should be able to get a user by ID."""
        response = client.get(
            f"/api/users/{regular_user.id}", headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "vendedor1"
        assert data["id"] == regular_user.id

    def test_get_user_not_found(
        self, client: TestClient, admin_user: User, admin_headers: dict
    ):
        """Getting a non-existent user should return 404."""
        response = client.get("/api/users/99999", headers=admin_headers)
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /api/users/{user_id}  (update user - admin only)
# ---------------------------------------------------------------------------

class TestUpdateUser:
    """Tests for updating user data."""

    def test_update_user_full_name(
        self, client: TestClient, admin_user: User, regular_user: User, admin_headers: dict
    ):
        """Admin should be able to update a user's full name."""
        response = client.patch(
            f"/api/users/{regular_user.id}",
            headers=admin_headers,
            json={"admin_password": "admin123", "full_name": "Carlos Actualizado"},
        )
        assert response.status_code == 200
        assert response.json()["full_name"] == "Carlos Actualizado"

    def test_update_user_role(
        self, client: TestClient, admin_user: User, regular_user: User, admin_headers: dict
    ):
        """Admin should be able to change a user's role."""
        response = client.patch(
            f"/api/users/{regular_user.id}",
            headers=admin_headers,
            json={"admin_password": "admin123", "role": "supervisor"},
        )
        assert response.status_code == 200
        assert response.json()["role"] == "supervisor"

    def test_update_user_deactivate(
        self, client: TestClient, admin_user: User, regular_user: User, admin_headers: dict
    ):
        """Admin should be able to deactivate a user."""
        response = client.patch(
            f"/api/users/{regular_user.id}",
            headers=admin_headers,
            json={"admin_password": "admin123", "is_active": False},
        )
        assert response.status_code == 200
        assert response.json()["is_active"] is False

    def test_update_user_not_found(
        self, client: TestClient, admin_user: User, admin_headers: dict
    ):
        """Updating a non-existent user should return 404."""
        response = client.patch(
            "/api/users/99999",
            headers=admin_headers,
            json={"admin_password": "admin123", "full_name": "Nobody"},
        )
        assert response.status_code == 404

    def test_update_user_invalid_role(
        self, client: TestClient, admin_user: User, regular_user: User, admin_headers: dict
    ):
        """Updating with an invalid role should return 400."""
        response = client.patch(
            f"/api/users/{regular_user.id}",
            headers=admin_headers,
            json={"admin_password": "admin123", "role": "superadmin"},
        )
        assert response.status_code == 400

    def test_update_user_non_admin_denied(
        self, client: TestClient, regular_user: User, regular_headers: dict
    ):
        """Non-admin should not be able to update users."""
        response = client.patch(
            f"/api/users/{regular_user.id}",
            headers=regular_headers,
            json={"admin_password": "dummy", "full_name": "Hacker"},
        )
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# DELETE /api/users/{user_id}  (delete user - admin only)
# ---------------------------------------------------------------------------

class TestDeleteUser:
    """Tests for deleting users."""

    def test_delete_user_success(
        self, client: TestClient, admin_user: User, regular_user: User, admin_headers: dict
    ):
        """Admin should be able to delete a user."""
        response = client.delete(
            f"/api/users/{regular_user.id}", headers=admin_headers
        )
        assert response.status_code == 200
        assert "eliminado" in response.json()["detail"].lower()

        # Verify user is actually deleted
        get_response = client.get(
            f"/api/users/{regular_user.id}", headers=admin_headers
        )
        assert get_response.status_code == 404

    def test_delete_user_not_found(
        self, client: TestClient, admin_user: User, admin_headers: dict
    ):
        """Deleting a non-existent user should return 404."""
        response = client.delete("/api/users/99999", headers=admin_headers)
        assert response.status_code == 404

    def test_delete_self_denied(
        self, client: TestClient, admin_user: User, admin_headers: dict
    ):
        """Admin should not be able to delete themselves."""
        response = client.delete(
            f"/api/users/{admin_user.id}", headers=admin_headers
        )
        assert response.status_code == 400
        assert "s\u00ed mismo" in response.json()["detail"].lower()

    def test_delete_user_non_admin_denied(
        self, client: TestClient, regular_user: User, admin_user: User, regular_headers: dict
    ):
        """Non-admin should not be able to delete users."""
        response = client.delete(
            f"/api/users/{admin_user.id}", headers=regular_headers
        )
        assert response.status_code == 403
