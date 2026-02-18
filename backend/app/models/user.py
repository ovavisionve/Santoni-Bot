import enum
from datetime import datetime

from sqlalchemy import String, Boolean, DateTime, Integer, Enum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserRole(str, enum.Enum):
    USUARIO = "usuario"
    SUPERVISOR = "supervisor"
    ADMINISTRADOR = "administrador"


class Department(str, enum.Enum):
    FINANZAS = "finanzas"
    CONTABILIDAD = "contabilidad"
    VENTAS = "ventas"
    RRHH = "rrhh"
    PRODUCCION = "produccion"
    COMPRAS_INSUMOS = "compras_insumos"
    COMPRAS_PRODUCTORES = "compras_productores"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole), default=UserRole.USUARIO
    )
    department: Mapped[Department] = mapped_column(Enum(Department))
    # Supervisors can access multiple departments
    extra_departments: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    # iDempiere organization IDs (comma-separated, e.g. "1000000,1000001")
    # NULL = all organizations (for admins), otherwise only listed orgs
    allowed_org_ids: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    totp_secret: Mapped[str | None] = mapped_column(String(64), nullable=True)
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="user"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="user")

    @property
    def allowed_departments(self) -> list[str]:
        """Return all departments this user can access."""
        deps = [self.department.value]
        if self.role == UserRole.ADMINISTRADOR:
            return [d.value for d in Department]
        if self.extra_departments:
            deps.extend(
                d.strip() for d in self.extra_departments.split(",") if d.strip()
            )
        return deps

    @property
    def org_ids(self) -> list[int] | None:
        """Return iDempiere org IDs this user can access, or None for all."""
        if not self.allowed_org_ids:
            return None
        return [
            int(x.strip()) for x in self.allowed_org_ids.split(",")
            if x.strip().isdigit()
        ]


# Avoid circular import issues
from app.models.conversation import Conversation  # noqa: E402
from app.models.audit import AuditLog  # noqa: E402
