"""
Tests for auth service: password hashing, JWT tokens, user authentication.
"""

import pytest
from datetime import timedelta
from unittest.mock import patch

from app.services.auth import (
    hash_password,
    verify_password,
    create_access_token,
    decode_token,
    authenticate_user,
)
from app.models.user import User


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

class TestPasswordHashing:
    """Tests for hash_password and verify_password functions."""

    def test_hash_password_returns_hash(self):
        """hash_password should return a bcrypt hash string."""
        hashed = hash_password("my_secret")
        assert hashed is not None
        assert hashed != "my_secret"
        assert len(hashed) > 0

    def test_verify_password_correct(self):
        """verify_password should return True for the correct password."""
        hashed = hash_password("correct_pass")
        assert verify_password("correct_pass", hashed) is True

    def test_verify_password_wrong(self):
        """verify_password should return False for the wrong password."""
        hashed = hash_password("correct_pass")
        assert verify_password("wrong_pass", hashed) is False

    def test_hash_password_unique_salts(self):
        """Two hashes of the same password should be different (different salts)."""
        hash1 = hash_password("same_password")
        hash2 = hash_password("same_password")
        assert hash1 != hash2
        # But both should verify
        assert verify_password("same_password", hash1) is True
        assert verify_password("same_password", hash2) is True

    def test_empty_password(self):
        """An empty password should still be hashable and verifiable."""
        hashed = hash_password("")
        assert verify_password("", hashed) is True
        assert verify_password("notempty", hashed) is False

    def test_unicode_password(self):
        """Unicode characters in password should work correctly."""
        hashed = hash_password("contrase\u00f1a_segura_\u00e9")
        assert verify_password("contrase\u00f1a_segura_\u00e9", hashed) is True


# ---------------------------------------------------------------------------
# JWT tokens
# ---------------------------------------------------------------------------

class TestJWTTokens:
    """Tests for create_access_token and decode_token functions."""

    def test_create_and_decode_token(self):
        """A created token should be decodable back to the original data."""
        data = {"sub": "42", "username": "admin", "role": "administrador"}
        token = create_access_token(data=data)
        payload = decode_token(token)

        assert payload is not None
        assert payload["sub"] == "42"
        assert payload["username"] == "admin"
        assert payload["role"] == "administrador"
        assert "exp" in payload

    def test_token_with_custom_expiry(self):
        """Token created with custom expiry should contain correct exp claim."""
        data = {"sub": "1"}
        token = create_access_token(data=data, expires_delta=timedelta(minutes=5))
        payload = decode_token(token)

        assert payload is not None
        assert "exp" in payload

    def test_decode_invalid_token(self):
        """decode_token should return None for an invalid token."""
        result = decode_token("not.a.valid.token")
        assert result is None

    def test_decode_empty_token(self):
        """decode_token should return None for an empty string."""
        result = decode_token("")
        assert result is None

    def test_decode_tampered_token(self):
        """decode_token should return None when token payload is tampered."""
        token = create_access_token(data={"sub": "1"})
        # Tamper with the payload by modifying a character
        parts = token.split(".")
        if len(parts) == 3:
            tampered_payload = parts[1] + "X"
            tampered_token = f"{parts[0]}.{tampered_payload}.{parts[2]}"
            result = decode_token(tampered_token)
            assert result is None

    def test_token_expired(self):
        """An expired token should fail to decode."""
        data = {"sub": "1"}
        token = create_access_token(
            data=data, expires_delta=timedelta(seconds=-10)
        )
        result = decode_token(token)
        assert result is None

    def test_token_preserves_all_claims(self):
        """All custom claims in data should be preserved in the token."""
        data = {
            "sub": "99",
            "username": "testuser",
            "role": "usuario",
            "department": "ventas",
        }
        token = create_access_token(data=data)
        payload = decode_token(token)

        assert payload is not None
        assert payload["sub"] == "99"
        assert payload["username"] == "testuser"
        assert payload["role"] == "usuario"
        assert payload["department"] == "ventas"


# ---------------------------------------------------------------------------
# authenticate_user
# ---------------------------------------------------------------------------

class TestAuthenticateUser:
    """Tests for authenticate_user function using real test DB."""

    def test_authenticate_success(self, db_session, regular_user):
        """authenticate_user should return the user with correct credentials."""
        result = authenticate_user(db_session, "vendedor1", "vende123")
        assert result is not None
        assert result.username == "vendedor1"
        assert result.id == regular_user.id

    def test_authenticate_wrong_password(self, db_session, regular_user):
        """authenticate_user should return None with wrong password."""
        result = authenticate_user(db_session, "vendedor1", "wrong_password")
        assert result is None

    def test_authenticate_user_not_found(self, db_session):
        """authenticate_user should return None for non-existent user."""
        result = authenticate_user(db_session, "nonexistent", "password")
        assert result is None

    def test_authenticate_inactive_user(self, db_session, inactive_user):
        """authenticate_user should return None for inactive users."""
        result = authenticate_user(db_session, "inactivo", "inactive123")
        assert result is None

    def test_authenticate_admin(self, db_session, admin_user):
        """authenticate_user should work for admin users."""
        result = authenticate_user(db_session, "admin", "admin123")
        assert result is not None
        assert result.role.value == "administrador"

    def test_authenticate_case_sensitive_username(self, db_session, regular_user):
        """Username lookup should be case-sensitive."""
        result = authenticate_user(db_session, "Vendedor1", "vende123")
        assert result is None

    def test_authenticate_empty_credentials(self, db_session):
        """authenticate_user should return None with empty credentials."""
        result = authenticate_user(db_session, "", "")
        assert result is None
