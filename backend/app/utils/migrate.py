"""
Auto-migration utility for SantoniBot.

Runs safe, idempotent SQL migrations on startup BEFORE create_all()
so that the ORM model always matches the DB schema.

PostgreSQL enums store UPPERCASE names (USUARIO, ADMINISTRADOR, etc.)
because the original schema was created with create_all() which used
Python enum NAMES, not values.
"""

import logging

from sqlalchemy import text

from app.database import engine

logger = logging.getLogger("santonibot.migrate")

# Each migration is a (description, SQL) tuple.
# All statements MUST be idempotent (safe to re-run).
_MIGRATIONS = [
    # --- 003: Vendedor role + org filtering + salesrep ---
    (
        "Add VENDEDOR to userrole enum",
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_enum
                WHERE enumlabel = 'VENDEDOR'
                AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'userrole')
            ) THEN
                ALTER TYPE userrole ADD VALUE 'VENDEDOR';
            END IF;
        END$$;
        """,
    ),
    (
        "Add allowed_org_ids column to users",
        """
        ALTER TABLE users ADD COLUMN IF NOT EXISTS allowed_org_ids VARCHAR(500);
        """,
    ),
    (
        "Add idempiere_salesrep_id column to users",
        """
        ALTER TABLE users ADD COLUMN IF NOT EXISTS idempiere_salesrep_id INTEGER;
        """,
    ),
    # --- 004: Sensitivity level per user ---
    (
        "Add sensitivity_level column to users",
        """
        ALTER TABLE users ADD COLUMN IF NOT EXISTS sensitivity_level INTEGER DEFAULT 0;
        """,
    ),
    # --- 005: Give all existing users access to all organizations and max sensitivity ---
    (
        "Set all users to all orgs and max sensitivity",
        """
        UPDATE users SET allowed_org_ids = NULL WHERE allowed_org_ids IS NOT NULL;
        UPDATE users SET sensitivity_level = 2 WHERE sensitivity_level < 2;
        """,
    ),
]


def run_startup_migrations() -> None:
    """Apply all pending idempotent migrations.

    Called from main.py lifespan BEFORE Base.metadata.create_all().
    Each migration runs in its own connection/transaction so that
    enum additions (which require COMMIT) work correctly.
    """
    for description, sql in _MIGRATIONS:
        try:
            with engine.connect() as conn:
                conn.execute(text(sql))
                conn.commit()
            logger.info("Migration OK: %s", description)
        except Exception as exc:
            logger.warning("Migration skipped (%s): %s", description, exc)
