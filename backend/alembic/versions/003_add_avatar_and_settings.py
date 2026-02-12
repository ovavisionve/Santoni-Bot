"""Add avatar_url to users and create app_settings table.

Revision ID: 003_branding
Revises: 002_totp
Create Date: 2026-02-12
"""
from alembic import op
import sqlalchemy as sa

revision = "003_branding"
down_revision = "002_totp"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Avatar for users
    op.add_column("users", sa.Column("avatar_url", sa.String(500), nullable=True))

    # App-wide settings (branding, logo, etc.)
    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(100), primary_key=True),
        sa.Column("value", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("app_settings")
    op.drop_column("users", "avatar_url")
