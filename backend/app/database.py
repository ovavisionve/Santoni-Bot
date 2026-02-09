from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config import get_settings

settings = get_settings()

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
