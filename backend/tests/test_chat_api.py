"""
Tests for chat API endpoints: POST /api/chat, GET /api/conversations,
GET /api/conversations/{id}, DELETE /api/conversations/{id}.

The Orchestrator (LLM) is mocked so no real API calls are made.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient

from app.models.user import User
from app.models.conversation import Conversation, Message


# ---------------------------------------------------------------------------
# POST /api/chat/  (send message - mocking the orchestrator)
# ---------------------------------------------------------------------------

class TestSendMessage:
    """Tests for the chat endpoint with mocked LLM."""

    @patch("app.api.routes.chat.orchestrator")
    def test_send_message_success(
        self, mock_orchestrator, client: TestClient, regular_user: User, regular_headers: dict
    ):
        """Sending a chat message should return a response with conversation_id."""
        mock_orchestrator.process = AsyncMock(
            return_value={
                "response": "Las ventas del mes ascienden a Bs. 2,500,000.00",
                "agent_used": "ventas",
                "metadata": {"classification": "ventas", "has_data": True},
            }
        )

        response = client.post(
            "/api/chat/",
            headers=regular_headers,
            json={"message": "Cuales son las ventas del mes?"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "message_id" in data
        assert "conversation_id" in data
        assert data["agent_used"] == "ventas"
        assert data["conversation_id"] > 0
        assert data["message_id"] > 0

    @patch("app.api.routes.chat.orchestrator")
    def test_send_message_creates_conversation(
        self, mock_orchestrator, client: TestClient, regular_user: User, regular_headers: dict, db_session
    ):
        """First message should create a new conversation."""
        mock_orchestrator.process = AsyncMock(
            return_value={
                "response": "Hola, soy SantoniBot.",
                "agent_used": "general",
                "metadata": {"classification": "general"},
            }
        )

        response = client.post(
            "/api/chat/",
            headers=regular_headers,
            json={"message": "Hola"},
        )
        assert response.status_code == 200
        conv_id = response.json()["conversation_id"]

        # Verify conversation was created in database
        conv = db_session.query(Conversation).filter(Conversation.id == conv_id).first()
        assert conv is not None
        assert conv.user_id == regular_user.id

    @patch("app.api.routes.chat.orchestrator")
    def test_send_message_existing_conversation(
        self, mock_orchestrator, client: TestClient, regular_user: User,
        regular_headers: dict, sample_conversation: Conversation
    ):
        """Sending a message to an existing conversation should reuse it."""
        mock_orchestrator.process = AsyncMock(
            return_value={
                "response": "El top de clientes es...",
                "agent_used": "ventas",
                "metadata": {"classification": "ventas"},
            }
        )

        response = client.post(
            "/api/chat/",
            headers=regular_headers,
            json={
                "message": "Top 10 clientes",
                "conversation_id": sample_conversation.id,
            },
        )
        assert response.status_code == 200
        assert response.json()["conversation_id"] == sample_conversation.id

    @patch("app.api.routes.chat.orchestrator")
    def test_send_message_wrong_conversation(
        self, mock_orchestrator, client: TestClient, admin_user: User,
        admin_headers: dict, sample_conversation: Conversation
    ):
        """Accessing another user's conversation should return 404."""
        response = client.post(
            "/api/chat/",
            headers=admin_headers,
            json={
                "message": "Hola",
                "conversation_id": sample_conversation.id,  # Belongs to regular_user
            },
        )
        assert response.status_code == 404

    def test_send_message_unauthenticated(self, client: TestClient):
        """Unauthenticated request should be rejected."""
        response = client.post(
            "/api/chat/",
            json={"message": "Hola"},
        )
        assert response.status_code == 403

    def test_send_message_missing_message(
        self, client: TestClient, regular_user: User, regular_headers: dict
    ):
        """Request without message field should return 422."""
        response = client.post(
            "/api/chat/",
            headers=regular_headers,
            json={},
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/chat/conversations  (list conversations)
# ---------------------------------------------------------------------------

class TestListConversations:
    """Tests for listing user conversations."""

    def test_list_conversations(
        self, client: TestClient, regular_user: User, regular_headers: dict,
        sample_conversation: Conversation
    ):
        """User should see their own conversations."""
        response = client.get(
            "/api/chat/conversations", headers=regular_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["id"] == sample_conversation.id
        assert "title" in data[0]
        assert "message_count" in data[0]

    def test_list_conversations_empty(
        self, client: TestClient, admin_user: User, admin_headers: dict
    ):
        """User with no conversations should get an empty list."""
        response = client.get(
            "/api/chat/conversations", headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_list_conversations_unauthenticated(self, client: TestClient):
        """Unauthenticated request should be rejected."""
        response = client.get("/api/chat/conversations")
        assert response.status_code == 403

    def test_list_conversations_isolation(
        self, client: TestClient, admin_user: User, admin_headers: dict,
        sample_conversation: Conversation
    ):
        """Admin should not see regular user's conversations in their list."""
        response = client.get(
            "/api/chat/conversations", headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        conv_ids = [c["id"] for c in data]
        assert sample_conversation.id not in conv_ids


# ---------------------------------------------------------------------------
# GET /api/chat/conversations/{id}  (get conversation detail)
# ---------------------------------------------------------------------------

class TestGetConversation:
    """Tests for getting a specific conversation with messages."""

    def test_get_conversation_detail(
        self, client: TestClient, regular_user: User, regular_headers: dict,
        sample_conversation: Conversation
    ):
        """User should see the full conversation with messages."""
        response = client.get(
            f"/api/chat/conversations/{sample_conversation.id}",
            headers=regular_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_conversation.id
        assert data["title"] == "Test conversation"
        assert "messages" in data
        assert len(data["messages"]) == 2  # user + assistant

    def test_get_conversation_not_found(
        self, client: TestClient, regular_user: User, regular_headers: dict
    ):
        """Getting a non-existent conversation should return 404."""
        response = client.get(
            "/api/chat/conversations/99999",
            headers=regular_headers,
        )
        assert response.status_code == 404

    def test_get_conversation_wrong_user(
        self, client: TestClient, admin_user: User, admin_headers: dict,
        sample_conversation: Conversation
    ):
        """User should not access another user's conversation."""
        response = client.get(
            f"/api/chat/conversations/{sample_conversation.id}",
            headers=admin_headers,
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/chat/conversations/{id}  (delete conversation)
# ---------------------------------------------------------------------------

class TestDeleteConversation:
    """Tests for deleting conversations.

    NOTE: The delete-success test creates a conversation *without* messages
    because the app's Conversation.messages relationship does not set
    ``passive_deletes=True``.  In SQLite (used for tests), SQLAlchemy
    tries to SET conversation_id=NULL on related messages before issuing
    the DELETE, which violates the NOT NULL constraint.  In PostgreSQL
    (production), the ON DELETE CASCADE at the DB level handles this.
    """

    def test_delete_conversation_success(
        self, client: TestClient, regular_user: User, regular_headers: dict,
        db_session,
    ):
        """User should be able to delete their own conversation (no messages)."""
        # Create a conversation without messages so SQLAlchemy's delete
        # does not trigger the NOT-NULL constraint on SQLite.
        conv = Conversation(user_id=regular_user.id, title="To be deleted")
        db_session.add(conv)
        db_session.commit()
        db_session.expire_all()

        response = client.delete(
            f"/api/chat/conversations/{conv.id}",
            headers=regular_headers,
        )
        assert response.status_code == 200
        assert "eliminada" in response.json()["detail"].lower()

    def test_delete_conversation_not_found(
        self, client: TestClient, regular_user: User, regular_headers: dict
    ):
        """Deleting a non-existent conversation should return 404."""
        response = client.delete(
            "/api/chat/conversations/99999",
            headers=regular_headers,
        )
        assert response.status_code == 404

    def test_delete_conversation_wrong_user(
        self, client: TestClient, admin_user: User, admin_headers: dict,
        sample_conversation: Conversation
    ):
        """User should not delete another user's conversation."""
        response = client.delete(
            f"/api/chat/conversations/{sample_conversation.id}",
            headers=admin_headers,
        )
        assert response.status_code == 404

    def test_delete_conversation_unauthenticated(
        self, client: TestClient, sample_conversation: Conversation
    ):
        """Unauthenticated request should be rejected."""
        response = client.delete(
            f"/api/chat/conversations/{sample_conversation.id}"
        )
        assert response.status_code == 403
