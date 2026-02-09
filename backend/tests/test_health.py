"""Basic tests for SantoniBot API."""


def test_app_imports():
    """Verify the app module can be imported."""
    from app.config import get_settings

    settings = get_settings()
    assert settings.app_name == "SantoniBot"


def test_models_import():
    """Verify models can be imported."""
    from app.models import User, Conversation, Message, AuditLog

    assert User.__tablename__ == "users"
    assert Conversation.__tablename__ == "conversations"
    assert Message.__tablename__ == "messages"
    assert AuditLog.__tablename__ == "audit_logs"


def test_password_hashing():
    """Verify password hashing works correctly."""
    from app.services.auth import hash_password, verify_password

    hashed = hash_password("test123")
    assert verify_password("test123", hashed)
    assert not verify_password("wrong", hashed)
