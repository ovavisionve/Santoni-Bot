"""Initial schema: users, conversations, messages, audit_logs.

Revision ID: 001_initial
Revises: (none)
Create Date: 2026-02-10
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def _table_exists(name):
    """Check if a table already exists in the database."""
    bind = op.get_bind()
    result = bind.execute(
        sa.text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = :name"
        ),
        {"name": name},
    )
    return result.fetchone() is not None


def _enum_exists(name):
    """Check if a PostgreSQL enum type already exists."""
    bind = op.get_bind()
    result = bind.execute(
        sa.text("SELECT 1 FROM pg_type WHERE typname = :name"),
        {"name": name},
    )
    return result.fetchone() is not None


def _create_enum_if_not_exists(name, values):
    """Create a PostgreSQL enum type only if it doesn't already exist."""
    if not _enum_exists(name):
        enum = postgresql.ENUM(*values, name=name, create_type=False)
        enum.create(op.get_bind())


def _index_exists(name):
    """Check if an index already exists."""
    bind = op.get_bind()
    result = bind.execute(
        sa.text("SELECT 1 FROM pg_indexes WHERE indexname = :name"),
        {"name": name},
    )
    return result.fetchone() is not None


def upgrade() -> None:
    # --- Create enum types (idempotent) ---
    _create_enum_if_not_exists(
        "userrole", ("usuario", "supervisor", "administrador")
    )
    _create_enum_if_not_exists(
        "department",
        (
            "finanzas",
            "contabilidad",
            "ventas",
            "rrhh",
            "produccion",
            "compras_insumos",
            "compras_productores",
        ),
    )
    _create_enum_if_not_exists(
        "messagerole", ("user", "assistant", "system")
    )

    # --- Users ---
    if not _table_exists("users"):
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("email", sa.String(255), nullable=False),
            sa.Column("username", sa.String(100), nullable=False),
            sa.Column("full_name", sa.String(255), nullable=False),
            sa.Column("hashed_password", sa.String(255), nullable=False),
            sa.Column(
                "role",
                postgresql.ENUM(
                    "usuario", "supervisor", "administrador",
                    name="userrole", create_type=False,
                ),
                nullable=False,
            ),
            sa.Column(
                "department",
                postgresql.ENUM(
                    "finanzas", "contabilidad", "ventas", "rrhh",
                    "produccion", "compras_insumos", "compras_productores",
                    name="department", create_type=False,
                ),
                nullable=False,
            ),
            sa.Column("extra_departments", sa.String(500), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
        )
    if not _index_exists("ix_users_email"):
        op.create_index("ix_users_email", "users", ["email"], unique=True)
    if not _index_exists("ix_users_username"):
        op.create_index("ix_users_username", "users", ["username"], unique=True)

    # --- Conversations ---
    if not _table_exists("conversations"):
        op.create_table(
            "conversations",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column(
                "title",
                sa.String(255),
                nullable=False,
                server_default="Nueva conversación",
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(
                ["user_id"], ["users.id"], ondelete="CASCADE"
            ),
        )
    if not _index_exists("ix_conversations_user_id"):
        op.create_index("ix_conversations_user_id", "conversations", ["user_id"])

    # --- Messages ---
    if not _table_exists("messages"):
        op.create_table(
            "messages",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("conversation_id", sa.Integer(), nullable=False),
            sa.Column(
                "role",
                postgresql.ENUM(
                    "user", "assistant", "system",
                    name="messagerole", create_type=False,
                ),
                nullable=False,
            ),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("agent_used", sa.String(100), nullable=True),
            sa.Column("metadata_json", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(
                ["conversation_id"], ["conversations.id"], ondelete="CASCADE"
            ),
        )
    if not _index_exists("ix_messages_conversation_id"):
        op.create_index(
            "ix_messages_conversation_id", "messages", ["conversation_id"]
        )

    # --- Audit logs ---
    if not _table_exists("audit_logs"):
        op.create_table(
            "audit_logs",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("action", sa.String(100), nullable=False),
            sa.Column("resource", sa.String(100), nullable=False),
            sa.Column("detail", sa.Text(), nullable=True),
            sa.Column("agent_used", sa.String(100), nullable=True),
            sa.Column("ip_address", sa.String(45), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(
                ["user_id"], ["users.id"], ondelete="SET NULL"
            ),
        )
    if not _index_exists("ix_audit_logs_user_id"):
        op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    if not _index_exists("ix_audit_logs_action"):
        op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    if not _index_exists("ix_audit_logs_created_at"):
        op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("users")
    # Drop enums (PostgreSQL-specific)
    op.execute("DROP TYPE IF EXISTS messagerole")
    op.execute("DROP TYPE IF EXISTS userrole")
    op.execute("DROP TYPE IF EXISTS department")
