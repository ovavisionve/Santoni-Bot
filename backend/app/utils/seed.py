import os
import logging

from app.database import SessionLocal
from app.models.user import User, UserRole, Department
from app.services.auth import hash_password

logger = logging.getLogger("santonibot.seed")


def create_admin_user():
    """Create default admin user if none exists.

    Password is read from ADMIN_DEFAULT_PASSWORD env var.
    If not set, defaults to 'SantoniAdmin2026!'.
    """
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.role == UserRole.ADMINISTRADOR).first()
        if existing:
            return

        password = os.environ.get("ADMIN_DEFAULT_PASSWORD", "SantoniAdmin2026!")
        generated = False

        if password == "SantoniAdmin2026!":
            generated = True

        admin = User(
            email="admin@santonibot.local",
            username="admin",
            full_name="Administrador SantoniBot",
            hashed_password=hash_password(password),
            role=UserRole.ADMINISTRADOR,
            department=Department.FINANZAS,
            is_active=True,
        )
        db.add(admin)
        db.commit()

        if generated:
            logger.warning(
                "Admin user created with default password 'SantoniAdmin2026!'. "
                "Set ADMIN_DEFAULT_PASSWORD env var to override. "
                "Change this password after first login.",
            )
        else:
            logger.info("Admin user created from ADMIN_DEFAULT_PASSWORD env var.")
    finally:
        db.close()
