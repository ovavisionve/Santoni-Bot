from app.database import SessionLocal
from app.models.user import User, UserRole, Department
from app.services.auth import hash_password


def create_admin_user():
    """Create default admin user if none exists."""
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.role == UserRole.ADMINISTRADOR).first()
        if existing:
            return

        admin = User(
            email="admin@santonibot.local",
            username="admin",
            full_name="Administrador SantoniBot",
            hashed_password=hash_password("SantoniAdmin2026!"),
            role=UserRole.ADMINISTRADOR,
            department=Department.FINANZAS,
            is_active=True,
        )
        db.add(admin)
        db.commit()
        print("[SantoniBot] Admin user created: admin / SantoniAdmin2026!")
    finally:
        db.close()
