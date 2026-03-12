"""Add ad_user_id and allowed_capabilities columns to users table.

Links bot users to their iDempiere ad_user record for automatic
role/permission synchronization.  allowed_capabilities stores the
granular capability IDs derived from iDempiere window access.

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
    op.add_column(
        "users",
        sa.Column("allowed_capabilities", sa.String(2000), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "allowed_capabilities")
    op.drop_index("ix_users_ad_user_id", table_name="users")
    op.drop_column("users", "ad_user_id")
