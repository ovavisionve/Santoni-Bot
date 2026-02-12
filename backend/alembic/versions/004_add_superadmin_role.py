"""Add superadministrador role to userrole enum.

Revision ID: 004_superadmin
Revises: 003_branding
Create Date: 2026-02-12
"""
from alembic import op

revision = "004_superadmin"
down_revision = "003_branding"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add the new enum value to PostgreSQL's userrole type
    # NOTE: DB enum uses uppercase names (USUARIO, SUPERVISOR, ADMINISTRADOR)
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'SUPERADMINISTRADOR'")

    # Promote the existing seed admin user to superadministrador
    op.execute(
        "UPDATE users SET role = 'SUPERADMINISTRADOR' "
        "WHERE username = 'admin' AND role = 'ADMINISTRADOR'"
    )


def downgrade() -> None:
    # Demote superadmin back to admin
    op.execute(
        "UPDATE users SET role = 'ADMINISTRADOR' "
        "WHERE role = 'SUPERADMINISTRADOR'"
    )
    # Note: PostgreSQL does not support removing enum values directly.
    # The 'superadministrador' value will remain in the enum type but
    # won't be used after downgrade.
