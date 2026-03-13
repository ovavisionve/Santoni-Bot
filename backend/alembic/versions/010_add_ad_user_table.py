"""Add ad_user table to adempiere schema for historical data.

Stores iDempiere ad_user records locally so birthday queries,
contact lookups, etc. work against the local historical cache
without hitting iDempiere.

Revision ID: 010_add_ad_user_table
Revises: 009_all_ad_user_ids
Create Date: 2026-03-13
"""
from alembic import op
import sqlalchemy as sa

revision = "010_add_ad_user_table"
down_revision = "009_all_ad_user_ids"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET search_path TO adempiere, public")

    op.create_table(
        "ad_user",
        sa.Column("ad_user_id", sa.Integer, primary_key=True),
        sa.Column("ad_client_id", sa.Integer),
        sa.Column("ad_org_id", sa.Integer),
        sa.Column("isactive", sa.CHAR(1), server_default="Y"),
        sa.Column("name", sa.String(255)),
        sa.Column("c_bpartner_id", sa.Integer),
        sa.Column("birthday", sa.DateTime),
        sa.Column("email", sa.String(255)),
        sa.Column("phone", sa.String(60)),
        schema="adempiere",
    )

    op.create_index(
        "idx_hist_aduser_bp",
        "ad_user",
        ["c_bpartner_id"],
        schema="adempiere",
    )
    op.create_index(
        "idx_hist_aduser_birthday",
        "ad_user",
        ["birthday"],
        schema="adempiere",
    )


def downgrade() -> None:
    op.drop_index("idx_hist_aduser_birthday", table_name="ad_user", schema="adempiere")
    op.drop_index("idx_hist_aduser_bp", table_name="ad_user", schema="adempiere")
    op.drop_table("ad_user", schema="adempiere")
