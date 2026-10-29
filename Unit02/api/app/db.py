"""
MongoDB access (DEVOP2 Unit 01: "JSON + MongoDB = flexible storage").

One database, two collections:
    books : the business data of the API (one JSON document per book)
    logs  : the structured application logs (one JSON document per event)

The client is created once and shared (pymongo keeps a connection pool).
Tests call set_database() with a mongomock database: no MongoDB needed.
"""
from pymongo import ASCENDING, MongoClient
from pymongo.database import Database

from . import config

_database: Database | None = None


def get_database() -> Database:
    """FastAPI dependency (and helper for the log handler)."""
    global _database
    if _database is None:
        # serverSelectionTimeoutMS: fail after 3 s instead of the default 30 s
        client = MongoClient(config.mongo_url(), serverSelectionTimeoutMS=3000, tz_aware=True)
        _database = client[config.MONGO_DB]
    return _database


def set_database(database: Database | None) -> None:
    """Replace the database (used by the tests)."""
    global _database
    _database = database


def create_indexes(db: Database) -> None:
    """Idempotent: create_index does nothing if the index already exists."""
    # unique ISBN: inserting the same book twice -> DuplicateKeyError -> 409
    db.books.create_index([("isbn", ASCENDING)], unique=True)
    # indexes used by the three log queries of the course
    db.logs.create_index([("timestamp", ASCENDING)])
    db.logs.create_index([("level", ASCENDING), ("timestamp", ASCENDING)])
    db.logs.create_index([("user_id", ASCENDING)])
