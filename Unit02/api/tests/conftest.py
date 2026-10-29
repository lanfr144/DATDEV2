"""Shared fixtures: an in-memory MongoDB (mongomock), Elasticsearch disabled."""
import mongomock
import pytest
from fastapi.testclient import TestClient

from app import config
from app import db as db_module
from app.db import create_indexes
from app.main import app


@pytest.fixture
def mdb(monkeypatch):
    monkeypatch.setattr(config, "ES_URL", "")      # no Elasticsearch in unit tests
    database = mongomock.MongoClient(tz_aware=True)["test"]
    create_indexes(database)
    db_module.set_database(database)
    yield database
    db_module.set_database(None)


@pytest.fixture
def client(mdb):
    with TestClient(app) as c:
        yield c


@pytest.fixture
def dune():
    return {"title": "Dune", "author": "Frank Herbert", "year": 1965,
            "isbn": "978-0441013593", "price": 9.99, "tags": ["Sci-Fi", "classic"]}
