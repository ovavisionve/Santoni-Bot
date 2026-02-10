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
