"""Add VENDEDOR role to userrole enum, allowed_org_ids and idempiere_salesrep_id columns.

Revision ID: 003_vendedor
Revises: 002_totp
Create Date: 2026-02-22
"""
from alembic import op
import sqlalchemy as sa

revision = "003_vendedor"
down_revision = "002_totp"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add VENDEDOR to the userrole enum.
    # PostgreSQL requires ALTER TYPE ... ADD VALUE which cannot run inside a
    # transaction block, so we must commit any open transaction first.
    # Note: the DB was created with create_all() which stored enum NAMES
    # (UPPERCASE), so we add 'VENDEDOR' in uppercase.
    op.execute("COMMIT")
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'VENDEDOR'")

    # allowed_org_ids: iDempiere org filter (added in org-filtering feature)
    op.add_column(
        "users",
        sa.Column("allowed_org_ids", sa.String(500), nullable=True),
    )

    # idempiere_salesrep_id: links vendedor users to their iDempiere salesperson
    op.add_column(
        "users",
        sa.Column("idempiere_salesrep_id", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "idempiere_salesrep_id")
    op.drop_column("users", "allowed_org_ids")
    # PostgreSQL does not support removing values from an enum type.
    # To fully downgrade, you would need to recreate the enum and migrate data.
