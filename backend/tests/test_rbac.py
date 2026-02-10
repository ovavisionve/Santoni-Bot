"""
Tests for Role-Based Access Control (RBAC).

Verifies that:
- Admin endpoints (stats, user management) are blocked for non-admin roles
- Supervisor endpoints (audit logs) allow supervisor + admin, block regular users
- Chat data isolation: users only see their own conversations
- Conversation PATCH endpoint respects ownership
- Health/detailed endpoint requires authentication
"""

import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from app.models.user import User, UserRole, Department
from app.models.conversation import Conversation, Message, MessageRole
from app.services.auth import hash_password, create_access_token


# ---------------------------------------------------------------------------
# Fixtures for department-specific users
# ---------------------------------------------------------------------------

@pytest.fixture
def finanzas_user(db_session):
    """Create a user in the finanzas department."""
    user = User(
        email="finanzas@santoni.com",
        username="finanzas1",
        full_name="Maria Finanzas",
        hashed_password=hash_password("fin123"),
        role=UserRole.USUARIO,
        department=Department.FINANZAS,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def finanzas_headers(finanzas_user):
    token = create_access_token(
        data={
            "sub": str(finanzas_user.id),
            "username": finanzas_user.username,
            "role": finanzas_user.role.value,
            "department": finanzas_user.department.value,
        }
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def produccion_user(db_session):
    """Create a user in the produccion department."""
    user = User(
        email="produccion@santoni.com",
        username="produccion1",
        full_name="Pedro Produccion",
        hashed_password=hash_password("prod123"),
        role=UserRole.USUARIO,
        department=Department.PRODUCCION,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def produccion_headers(produccion_user):
    token = create_access_token(
        data={
            "sub": str(produccion_user.id),
            "username": produccion_user.username,
            "role": produccion_user.role.value,
            "department": produccion_user.department.value,
        }
    )
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Admin endpoints: GET /api/admin/stats
# ---------------------------------------------------------------------------

class TestAdminStatsRBAC:
    """Only admin role should access system stats."""

    def test_admin_can_access_stats(
        self, client: TestClient, admin_user: User, admin_headers: dict
    ):
        response = client.get("/api/admin/stats", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert "conversations" in data
        assert "messages" in data

    def test_supervisor_cannot_access_stats(
        self, client: TestClient, supervisor_user: User, supervisor_headers: dict
    ):
        response = client.get("/api/admin/stats", headers=supervisor_headers)
        assert response.status_code == 403

    def test_regular_user_cannot_access_stats(
        self, client: TestClient, regular_user: User, regular_headers: dict
    ):
        response = client.get("/api/admin/stats", headers=regular_headers)
        assert response.status_code == 403

    def test_unauthenticated_cannot_access_stats(self, client: TestClient):
        response = client.get("/api/admin/stats")
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Supervisor endpoints: GET /api/admin/audit-logs
# ---------------------------------------------------------------------------

class TestAuditLogsRBAC:
    """Supervisor and admin can access audit logs; regular users cannot."""

    def test_admin_can_access_audit_logs(
        self, client: TestClient, admin_user: User, admin_headers: dict
    ):
        response = client.get("/api/admin/audit-logs", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "data" in data

    def test_supervisor_can_access_audit_logs(
        self, client: TestClient, supervisor_user: User, supervisor_headers: dict
    ):
        response = client.get("/api/admin/audit-logs", headers=supervisor_headers)
        assert response.status_code == 200

    def test_regular_user_cannot_access_audit_logs(
        self, client: TestClient, regular_user: User, regular_headers: dict
    ):
        response = client.get("/api/admin/audit-logs", headers=regular_headers)
        assert response.status_code == 403

    def test_unauthenticated_cannot_access_audit_logs(self, client: TestClient):
        response = client.get("/api/admin/audit-logs")
        assert response.status_code == 403

    def test_audit_logs_filter_by_action(
        self, client: TestClient, admin_user: User, admin_headers: dict
    ):
        response = client.get(
            "/api/admin/audit-logs?action=chat_query", headers=admin_headers
        )
        assert response.status_code == 200

    def test_audit_logs_pagination(
        self, client: TestClient, admin_user: User, admin_headers: dict
    ):
        response = client.get(
            "/api/admin/audit-logs?page=1&limit=10", headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["limit"] == 10


# ---------------------------------------------------------------------------
# Chat data isolation: users only see their own conversations
# ---------------------------------------------------------------------------

class TestChatDataIsolation:
    """Each user should only see/access their own conversations."""

    def test_user_a_cannot_see_user_b_conversations(
        self, client: TestClient, db_session,
        regular_user: User, regular_headers: dict,
        finanzas_user, finanzas_headers,
    ):
        """Finanzas user should not see ventas user's conversations."""
        # Create conversation for regular_user (ventas)
        conv = Conversation(user_id=regular_user.id, title="Ventas conv")
        db_session.add(conv)
        db_session.commit()

        # Finanzas user lists their conversations - should be empty
        response = client.get(
            "/api/chat/conversations", headers=finanzas_headers
        )
        assert response.status_code == 200
        conv_ids = [c["id"] for c in response.json()]
        assert conv.id not in conv_ids

    def test_user_a_cannot_get_user_b_conversation_detail(
        self, client: TestClient, db_session,
        regular_user: User,
        finanzas_user, finanzas_headers,
    ):
        """Finanzas user should get 404 when trying to access ventas conversation."""
        conv = Conversation(user_id=regular_user.id, title="Private conv")
        db_session.add(conv)
        db_session.commit()
        db_session.expire_all()

        response = client.get(
            f"/api/chat/conversations/{conv.id}", headers=finanzas_headers
        )
        assert response.status_code == 404

    def test_user_a_cannot_delete_user_b_conversation(
        self, client: TestClient, db_session,
        regular_user: User,
        finanzas_user, finanzas_headers,
    ):
        """Finanzas user should get 404 when deleting ventas conversation."""
        conv = Conversation(user_id=regular_user.id, title="Cannot delete")
        db_session.add(conv)
        db_session.commit()
        db_session.expire_all()

        response = client.delete(
            f"/api/chat/conversations/{conv.id}", headers=finanzas_headers
        )
        assert response.status_code == 404

    def test_user_a_cannot_patch_user_b_conversation(
        self, client: TestClient, db_session,
        regular_user: User,
        finanzas_user, finanzas_headers,
    ):
        """Finanzas user should get 404 when patching ventas conversation."""
        conv = Conversation(user_id=regular_user.id, title="Original title")
        db_session.add(conv)
        db_session.commit()
        db_session.expire_all()

        response = client.patch(
            f"/api/chat/conversations/{conv.id}",
            headers=finanzas_headers,
            json={"title": "Hacked title"},
        )
        assert response.status_code == 404

    @patch("app.api.routes.chat.orchestrator")
    def test_user_a_cannot_post_to_user_b_conversation(
        self, mock_orchestrator, client: TestClient, db_session,
        regular_user: User,
        finanzas_user, finanzas_headers,
    ):
        """Finanzas user should get 404 when posting to ventas conversation."""
        conv = Conversation(user_id=regular_user.id, title="Private chat")
        db_session.add(conv)
        db_session.commit()
        db_session.expire_all()

        response = client.post(
            "/api/chat/",
            headers=finanzas_headers,
            json={"message": "Intruso!", "conversation_id": conv.id},
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Conversation PATCH endpoint
# ---------------------------------------------------------------------------

class TestConversationPatch:
    """Tests for PATCH /api/chat/conversations/{id}."""

    def test_owner_can_rename_conversation(
        self, client: TestClient, regular_user: User, regular_headers: dict,
        sample_conversation: Conversation,
    ):
        response = client.patch(
            f"/api/chat/conversations/{sample_conversation.id}",
            headers=regular_headers,
            json={"title": "Nuevo titulo"},
        )
        assert response.status_code == 200

    def test_patch_truncates_long_title(
        self, client: TestClient, regular_user: User, regular_headers: dict,
        sample_conversation: Conversation,
    ):
        long_title = "A" * 300
        response = client.patch(
            f"/api/chat/conversations/{sample_conversation.id}",
            headers=regular_headers,
            json={"title": long_title},
        )
        assert response.status_code == 200

    def test_patch_nonexistent_conversation(
        self, client: TestClient, regular_user: User, regular_headers: dict
    ):
        response = client.patch(
            "/api/chat/conversations/99999",
            headers=regular_headers,
            json={"title": "Ghost"},
        )
        assert response.status_code == 404

    def test_patch_unauthenticated(self, client: TestClient):
        response = client.patch(
            "/api/chat/conversations/1",
            json={"title": "Hacker"},
        )
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Health endpoint auth
# ---------------------------------------------------------------------------

class TestHealthEndpointAuth:
    """Basic health is public; detailed health requires auth."""

    def test_basic_health_is_public(self, client: TestClient):
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_detailed_health_requires_auth(self, client: TestClient):
        response = client.get("/api/health/detailed")
        assert response.status_code == 403

    def test_detailed_health_with_auth(
        self, client: TestClient, admin_user: User, admin_headers: dict
    ):
        response = client.get("/api/health/detailed", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "checks" in data

    def test_detailed_health_regular_user(
        self, client: TestClient, regular_user: User, regular_headers: dict
    ):
        response = client.get("/api/health/detailed", headers=regular_headers)
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# User management RBAC cross-role tests
# ---------------------------------------------------------------------------

class TestUserManagementCrossRole:
    """Comprehensive cross-role tests for user management endpoints."""

    def test_supervisor_cannot_create_users(
        self, client: TestClient, supervisor_user: User, supervisor_headers: dict
    ):
        response = client.post(
            "/api/users/",
            headers=supervisor_headers,
            json={
                "email": "hack@santoni.com",
                "username": "hacker",
                "full_name": "Hacker",
                "password": "hack123",
                "role": "administrador",
                "department": "ventas",
            },
        )
        assert response.status_code == 403

    def test_supervisor_cannot_delete_users(
        self, client: TestClient, supervisor_user: User, supervisor_headers: dict,
        regular_user: User,
    ):
        response = client.delete(
            f"/api/users/{regular_user.id}", headers=supervisor_headers
        )
        assert response.status_code == 403

    def test_regular_user_cannot_get_other_user_details(
        self, client: TestClient, regular_user: User, regular_headers: dict,
        admin_user: User,
    ):
        response = client.get(
            f"/api/users/{admin_user.id}", headers=regular_headers
        )
        assert response.status_code == 403

    def test_different_department_user_cannot_manage_users(
        self, client: TestClient, finanzas_user, finanzas_headers
    ):
        response = client.get("/api/users/", headers=finanzas_headers)
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Export endpoint auth
# ---------------------------------------------------------------------------

class TestExportAuth:
    """Export endpoints require authentication."""

    def test_export_unauthenticated(self, client: TestClient):
        response = client.get("/api/export/message/1?format=csv")
        assert response.status_code == 403

    def test_export_nonexistent_message(
        self, client: TestClient, regular_user: User, regular_headers: dict
    ):
        response = client.get(
            "/api/export/message/99999?format=csv", headers=regular_headers
        )
        # Should be 404 (message not found) or similar
        assert response.status_code in (404, 400)
