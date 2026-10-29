"""
PostgreSQL access with SQLAlchemy 2 (DATOP2 Unit 03: ONE database for the monolith).

The URL is no longer read directly from DATABASE_URL: it is built by the
configuration loader (settings.py) from the block of APP_ENV + the secret
DB_PASSWORD. Tests use DB_URL=sqlite:///... (see tests/conftest.py).
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .settings import get_settings

DATABASE_URL = get_settings().database_url

# SQLite refuses by default to be used from several threads (FastAPI runs "def" endpoints in a thread pool)
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
# pool_pre_ping: test the connection before using it (survives a database restart)
engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency: one database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
