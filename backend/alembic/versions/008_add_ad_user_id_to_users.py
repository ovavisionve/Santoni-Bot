"""Add ad_user_id column to users table.

Links bot users to their iDempiere ad_user record for automatic
role/permission synchronization.

Revision ID: 008_ad_user_id
Revises: 007_bpl_city
Create Date: 2026-03-12
"""
from alembic import op
import sqlalchemy as sa

revision = "008_ad_user_id"
down_revision = "007_bpl_city"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("ad_user_id", sa.Integer(), nullable=True),
    )
    op.create_index("ix_users_ad_user_id", "users", ["ad_user_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_ad_user_id", table_name="users")
    op.drop_column("users", "ad_user_id")
