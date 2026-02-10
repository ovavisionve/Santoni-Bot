"""
Shared test fixtures for SantoniBot backend tests.

Uses SQLite in-memory database for speed and isolation.
Overrides FastAPI dependencies to use test DB and avoid external services.
"""

import os

# Set fake environment variables BEFORE any app imports so that modules
# instantiating LLM clients at import-time (e.g. chat.py -> Orchestrator)
# do not fail due to missing API keys.
os.environ.setdefault("GROQ_API_KEY", "test-fake-groq-key-for-pytest")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-fake-anthropic-key-for-pytest")
os.environ.setdefault("SECRET_KEY", "test-secret-key-minimum-32-characters-long")

import pytest
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from unittest.mock import patch

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.models.user import User, UserRole, Department
from app.models.conversation import Conversation, Message, MessageRole
from app.models.audit import AuditLog
from app.services.auth import hash_password, create_access_token


# ---------------------------------------------------------------------------
# Test database setup (SQLite in-memory)
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite://"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


# Enable foreign key support in SQLite
@event.listens_for(test_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


# ---------------------------------------------------------------------------
# Create test app with overridden lifespan to avoid real DB connections
# ---------------------------------------------------------------------------

@asynccontextmanager
async def _test_lifespan(app: FastAPI):
    """Test lifespan that creates tables on the test engine only."""
    Base.metadata.create_all(bind=test_engine)
    yield


def _create_test_app() -> FastAPI:
    """
    Import the real app but replace its lifespan so it does not try
    to connect to PostgreSQL during startup.
    """
    # Patch the lifespan and seed functions BEFORE the app object is used
    # by the TestClient. We re-use the already-created app from main.py
    # but swap its lifespan.
    from app.main import app as real_app
    real_app.router.lifespan_context = _test_lifespan
    return real_app


test_app = _create_test_app()


# ---------------------------------------------------------------------------
# Database session fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def db_session() -> Session:
    """Create a fresh database for each test function."""
    Base.metadata.create_all(bind=test_engine)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


# ---------------------------------------------------------------------------
# FastAPI test client
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def client(db_session: Session) -> TestClient:
    """
    FastAPI TestClient that overrides the get_db dependency to use
    the in-memory SQLite test database.
    """

    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    test_app.dependency_overrides[get_db] = _override_get_db
    with TestClient(test_app, raise_server_exceptions=False) as c:
        yield c
    test_app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# User fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def admin_user(db_session: Session) -> User:
    """Create an admin user with access to all departments."""
    user = User(
        email="admin@santoni.com",
        username="admin",
        full_name="Admin Santoni",
        hashed_password=hash_password("admin123"),
        role=UserRole.ADMINISTRADOR,
        department=Department.VENTAS,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def supervisor_user(db_session: Session) -> User:
    """Create a supervisor user with access to ventas and finanzas."""
    user = User(
        email="supervisor@santoni.com",
        username="supervisor",
        full_name="Supervisor Ventas",
        hashed_password=hash_password("super123"),
        role=UserRole.SUPERVISOR,
        department=Department.VENTAS,
        extra_departments="finanzas",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def regular_user(db_session: Session) -> User:
    """Create a regular user with access only to ventas."""
    user = User(
        email="vendedor@santoni.com",
        username="vendedor1",
        full_name="Carlos Vendedor",
        hashed_password=hash_password("vende123"),
        role=UserRole.USUARIO,
        department=Department.VENTAS,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def rrhh_user(db_session: Session) -> User:
    """Create a regular user with access only to rrhh."""
    user = User(
        email="rrhh@santoni.com",
        username="rrhh1",
        full_name="Ana RRHH",
        hashed_password=hash_password("rrhh123"),
        role=UserRole.USUARIO,
        department=Department.RRHH,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def inactive_user(db_session: Session) -> User:
    """Create an inactive user."""
    user = User(
        email="inactive@santoni.com",
        username="inactivo",
        full_name="Usuario Inactivo",
        hashed_password=hash_password("inactive123"),
        role=UserRole.USUARIO,
        department=Department.VENTAS,
        is_active=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Auth token fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def admin_token(admin_user: User) -> str:
    """JWT token for admin user."""
    return create_access_token(
        data={
            "sub": str(admin_user.id),
            "username": admin_user.username,
            "role": admin_user.role.value,
            "department": admin_user.department.value,
        }
    )


@pytest.fixture
def supervisor_token(supervisor_user: User) -> str:
    """JWT token for supervisor user."""
    return create_access_token(
        data={
            "sub": str(supervisor_user.id),
            "username": supervisor_user.username,
            "role": supervisor_user.role.value,
            "department": supervisor_user.department.value,
        }
    )


@pytest.fixture
def regular_token(regular_user: User) -> str:
    """JWT token for regular user."""
    return create_access_token(
        data={
            "sub": str(regular_user.id),
            "username": regular_user.username,
            "role": regular_user.role.value,
            "department": regular_user.department.value,
        }
    )


@pytest.fixture
def rrhh_token(rrhh_user: User) -> str:
    """JWT token for RRHH user."""
    return create_access_token(
        data={
            "sub": str(rrhh_user.id),
            "username": rrhh_user.username,
            "role": rrhh_user.role.value,
            "department": rrhh_user.department.value,
        }
    )


# ---------------------------------------------------------------------------
# Auth headers helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def admin_headers(admin_token: str) -> dict:
    """Authorization headers for admin user."""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def supervisor_headers(supervisor_token: str) -> dict:
    """Authorization headers for supervisor user."""
    return {"Authorization": f"Bearer {supervisor_token}"}


@pytest.fixture
def regular_headers(regular_token: str) -> dict:
    """Authorization headers for regular user."""
    return {"Authorization": f"Bearer {regular_token}"}


@pytest.fixture
def rrhh_headers(rrhh_token: str) -> dict:
    """Authorization headers for RRHH user."""
    return {"Authorization": f"Bearer {rrhh_token}"}


# ---------------------------------------------------------------------------
# Conversation / message fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_conversation(db_session: Session, regular_user: User) -> Conversation:
    """Create a sample conversation with messages."""
    conv = Conversation(
        user_id=regular_user.id,
        title="Test conversation",
    )
    db_session.add(conv)
    db_session.commit()
    db_session.refresh(conv)

    user_msg = Message(
        conversation_id=conv.id,
        role=MessageRole.USER,
        content="Cuales son las ventas del mes?",
    )
    db_session.add(user_msg)

    assistant_msg = Message(
        conversation_id=conv.id,
        role=MessageRole.ASSISTANT,
        content="Las ventas del mes son de Bs. 1,500,000.00",
        agent_used="ventas",
    )
    db_session.add(assistant_msg)
    db_session.commit()

    # Expire all objects so that lazy-loaded relationships are not in the
    # session identity map.  This prevents SQLAlchemy from trying to handle
    # cascading deletes (set FK=NULL) on loaded messages when the route
    # handler calls db.delete(conversation).  The database-level
    # ON DELETE CASCADE will handle the messages instead.
    db_session.expire_all()

    return conv
