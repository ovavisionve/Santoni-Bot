"""Add TOTP 2FA and account lockout fields to users table.

Revision ID: 002_totp
Revises: 001_initial
Create Date: 2026-02-12
"""
from alembic import op
import sqlalchemy as sa

revision = "002_totp"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def _column_exists(table, column):
    """Check if a column already exists in a table."""
    bind = op.get_bind()
    result = bind.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = :table "
            "AND column_name = :column"
        ),
        {"table": table, "column": column},
    )
    return result.fetchone() is not None


def upgrade() -> None:
    if not _column_exists("users", "totp_secret"):
        op.add_column("users", sa.Column("totp_secret", sa.String(64), nullable=True))
    if not _column_exists("users", "totp_enabled"):
        op.add_column(
            "users",
            sa.Column("totp_enabled", sa.Boolean(), nullable=False, server_default="false"),
        )
    if not _column_exists("users", "failed_login_attempts"):
        op.add_column(
            "users",
            sa.Column(
                "failed_login_attempts",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
        )
    if not _column_exists("users", "locked_until"):
        op.add_column(
            "users",
            sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    op.drop_column("users", "locked_until")
    op.drop_column("users", "failed_login_attempts")
    op.drop_column("users", "totp_enabled")
    op.drop_column("users", "totp_secret")
