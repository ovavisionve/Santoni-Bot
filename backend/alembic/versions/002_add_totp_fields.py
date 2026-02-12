"""Add TOTP 2FA fields to users table.

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


def upgrade() -> None:
    op.add_column("users", sa.Column("totp_secret", sa.String(64), nullable=True))
    op.add_column(
        "users",
        sa.Column("totp_enabled", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("users", "totp_enabled")
    op.drop_column("users", "totp_secret")
