"""Add all_ad_user_ids column to users table.

Stores ALL iDempiere ad_user_ids for a person (comma-separated).
Same person may have different user records across iDempiere clients,
each with different roles/permissions.  The sync uses all of them
to build the combined permission set.

Revision ID: 009_all_ad_user_ids
Revises: 008_ad_user_id
Create Date: 2026-03-12
"""
from alembic import op
import sqlalchemy as sa

revision = "009_all_ad_user_ids"
down_revision = "008_ad_user_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("all_ad_user_ids", sa.String(1000), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "all_ad_user_ids")
