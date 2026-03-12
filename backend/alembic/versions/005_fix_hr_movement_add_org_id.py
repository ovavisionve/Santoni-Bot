"""Add ad_org_id column to adempiere.hr_movement.

The original migration 004 omitted this column, which is needed for
filtering ausentismo/attendance queries by organization.

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


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS adempiere.idx_hist_hrmov_org")
    op.execute("ALTER TABLE adempiere.hr_movement DROP COLUMN IF EXISTS ad_org_id")
