"""Add city column to adempiere.c_bpartner_location.

The local copy was missing the city column used by compras_productores
queries (bpl.city).

Revision ID: 007_bpl_city
Revises: 006_fact_acct_isactive
Create Date: 2026-03-12
"""
from alembic import op

revision = "007_bpl_city"
down_revision = "006_fact_acct_isactive"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE adempiere.c_bpartner_location
        ADD COLUMN IF NOT EXISTS city VARCHAR(60) DEFAULT ''
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE adempiere.c_bpartner_location DROP COLUMN IF EXISTS city")
