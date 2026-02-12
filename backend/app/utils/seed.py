import os
import secrets
import logging

from app.database import SessionLocal
from app.models.user import User, UserRole, Department
from app.services.auth import hash_password

logger = logging.getLogger("santonibot.seed")


def create_admin_user():
    """Create default super-admin user if none exists.

    Password is read from ADMIN_DEFAULT_PASSWORD env var.
    If not set, a random password is generated and logged ONCE.
    """
    db = SessionLocal()
    try:
        existing = db.query(User).filter(
            User.role == UserRole.SUPERADMINISTRADOR
        ).first()
        if existing:
            return

        password = os.environ.get("ADMIN_DEFAULT_PASSWORD", "")
        generated = False

        if not password:
            password = secrets.token_urlsafe(16)
            generated = True

        admin = User(
            email="admin@santonibot.local",
            username="admin",
            full_name="Administrador SantoniBot",
            hashed_password=hash_password(password),
            role=UserRole.SUPERADMINISTRADOR,
            department=Department.FINANZAS,
            is_active=True,
        )
        db.add(admin)
        db.commit()

        if generated:
            logger.warning(
                "Admin user created with generated password. "
                "Set ADMIN_DEFAULT_PASSWORD env var or change via API. "
                "Temporary password: %s",
                password,
            )
        else:
            logger.info("Admin user created from ADMIN_DEFAULT_PASSWORD env var.")
    finally:
        db.close()
