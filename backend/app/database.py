import logging

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger("santonibot.database")

# Internal SantoniBot database
engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# iDempiere database (read-only)
idempiere_engine = create_engine(
    settings.idempiere_database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    connect_args={"options": "-c statement_timeout=120000"},  # 120s timeout per query
)
IdempiereSession = sessionmaker(
    autocommit=False, autoflush=False, bind=idempiere_engine
)


# Enforce read-only on iDempiere connections
@event.listens_for(idempiere_engine, "connect")
def set_idempiere_readonly(dbapi_connection, connection_record):
    """Set iDempiere connections to read-only at the database level."""
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute("SET default_transaction_read_only = ON")
        cursor.close()
    except Exception as e:
        logger.warning("Could not set iDempiere read-only mode: %s", e)


# Historical data session: queries local DB's "adempiere" schema
# for data before the cutoff date (avoids hitting iDempiere for old data).
# Uses the SAME SQL as iDempiere queries because both have "adempiere.*" tables.
HistoricalSession = sessionmaker(
    autocommit=False, autoflush=False, bind=engine
)


@event.listens_for(engine, "connect")
def set_historical_search_path(dbapi_connection, connection_record):
    """Ensure the adempiere schema is in the search path for the local DB.
    This allows queries with 'adempiere.table_name' to resolve to the local copy."""
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute("SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'adempiere'")
        if cursor.fetchone():
            cursor.execute("SET search_path TO public, adempiere")
        cursor.close()
    except Exception as e:
        logger.debug("Could not set search_path for historical schema: %s", e)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_idempiere_db():
    db = IdempiereSession()
    try:
        yield db
    finally:
        db.close()
