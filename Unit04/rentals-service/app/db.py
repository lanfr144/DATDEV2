import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# PostgreSQL in Docker (DATABASE_URL built by docker-compose.yml from .env),
# SQLite file as a fallback for quick local tests
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./dev.db")

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
