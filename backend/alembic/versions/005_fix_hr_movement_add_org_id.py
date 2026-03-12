"""Fix historical schema: add hr_movement.ad_org_id + widen fact_acct numeric columns.

1. hr_movement was missing ad_org_id (needed for org filter in ausentismo queries)
2. fact_acct numeric columns were NUMERIC(20,2) but iDempiere stores values with
   much higher precision (up to 24 decimal places from reconversion periods).

Revision ID: 005_hr_movement_org
Revises: 004_historical
Create Date: 2026-03-12
"""
from alembic import op

revision = "005_hr_movement_org"
down_revision = "004_historical"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add ad_org_id to hr_movement (was missing in 004)
    op.execute("""
        ALTER TABLE adempiere.hr_movement
        ADD COLUMN IF NOT EXISTS ad_org_id INTEGER
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_hist_hrmov_org
        ON adempiere.hr_movement(ad_org_id)
    """)

    # Widen fact_acct numeric columns to handle iDempiere's full precision
    # Original: NUMERIC(20,2) - fails on values like 0.000006313498800000000000
    for col in ("amtsourcedr", "amtsourcecr", "amtacctdr", "amtacctcr"):
        op.execute(f"""
            ALTER TABLE adempiere.fact_acct
            ALTER COLUMN {col} TYPE NUMERIC(38,12)
        """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS adempiere.idx_hist_hrmov_org")
    op.execute("ALTER TABLE adempiere.hr_movement DROP COLUMN IF EXISTS ad_org_id")
    for col in ("amtsourcedr", "amtsourcecr", "amtacctdr", "amtacctcr"):
        op.execute(f"""
            ALTER TABLE adempiere.fact_acct
            ALTER COLUMN {col} TYPE NUMERIC(20,2)
        """)
