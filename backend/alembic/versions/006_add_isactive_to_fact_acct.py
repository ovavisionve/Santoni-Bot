"""Add isactive column to adempiere.fact_acct.

The local historical copy of fact_acct was missing the isactive column,
which is used in contabilidad queries (fa.isactive = 'Y').
All fact_acct records in iDempiere are active, so default to 'Y'.

Revision ID: 006_fact_acct_isactive
Revises: 005_hr_movement_org
Create Date: 2026-03-12
"""
from alembic import op

revision = "006_fact_acct_isactive"
down_revision = "005_hr_movement_org"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE adempiere.fact_acct
        ADD COLUMN IF NOT EXISTS isactive CHAR(1) DEFAULT 'Y'
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE adempiere.fact_acct DROP COLUMN IF EXISTS isactive")
