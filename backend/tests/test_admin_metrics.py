"""
Tests for GET /api/admin/metrics endpoint.
"""

import pytest
from fastapi.testclient import TestClient

from app.models.user import User


class TestMetricsEndpoint:
    """Tests for the admin metrics dashboard endpoint."""

    def test_admin_can_access_metrics(
        self, client: TestClient, admin_user: User, admin_headers: dict
    ):
        response = client.get("/api/admin/metrics", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "period_days" in data
        assert data["period_days"] == 7
        assert "daily_messages" in data
        assert "daily_conversations" in data
        assert "top_users" in data
        assert "department_breakdown" in data
        assert "avg_messages_per_conversation" in data

    def test_metrics_custom_days(
        self, client: TestClient, admin_user: User, admin_headers: dict
    ):
        response = client.get(
            "/api/admin/metrics?days=30", headers=admin_headers
        )
        assert response.status_code == 200
        assert response.json()["period_days"] == 30

    def test_metrics_invalid_days(
        self, client: TestClient, admin_user: User, admin_headers: dict
    ):
        response = client.get(
            "/api/admin/metrics?days=0", headers=admin_headers
        )
        assert response.status_code == 422

    def test_regular_user_cannot_access_metrics(
        self, client: TestClient, regular_user: User, regular_headers: dict
    ):
        response = client.get("/api/admin/metrics", headers=regular_headers)
        assert response.status_code == 403

    def test_supervisor_cannot_access_metrics(
        self, client: TestClient, supervisor_user: User, supervisor_headers: dict
    ):
        response = client.get("/api/admin/metrics", headers=supervisor_headers)
        assert response.status_code == 403

    def test_unauthenticated_cannot_access_metrics(self, client: TestClient):
        response = client.get("/api/admin/metrics")
        assert response.status_code == 403

    def test_metrics_with_data(
        self, client: TestClient, admin_user: User, admin_headers: dict,
        sample_conversation,
    ):
        """Metrics should reflect existing data."""
        response = client.get("/api/admin/metrics", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        # sample_conversation has 2 messages, so there should be some data
        assert isinstance(data["daily_messages"], list)
        assert isinstance(data["department_breakdown"], list)
