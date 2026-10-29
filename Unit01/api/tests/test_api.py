"""
Unit 01 tests - no MongoDB needed: mongomock is an in-memory MongoDB.

Run: cd api && pytest -q
"""
import json
from pathlib import Path

import mongomock
import pytest
from fastapi.testclient import TestClient

from app import db as db_module
from app.db import create_indexes
from app.main import app

SEED = Path(__file__).resolve().parents[2] / "mongo" / "logs.ndjson"
DUNE = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593"}


@pytest.fixture
def mdb():
    database = mongomock.MongoClient(tz_aware=True)["test"]
    create_indexes(database)
    db_module.set_database(database)
    yield database
    db_module.set_database(None)


@pytest.fixture
def client(mdb):
    with TestClient(app) as c:
        yield c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_crud_cycle_with_all_http_methods(client):
    # POST -> 201 + Location
    r = client.post("/books", json=DUNE, headers={"X-User-Id": "U1"})
    assert r.status_code == 201
    book_id = r.json()["id"]
    assert r.headers["location"] == f"/books/{book_id}"
    # GET one / GET list with a filter
    assert client.get(f"/books/{book_id}").json()["title"] == "Dune"
    assert len(client.get("/books", params={"author": "Frank Herbert"}).json()) == 1
    # PATCH = partial, PUT = full replacement
    assert client.patch(f"/books/{book_id}", json={"year": 1966}).json()["year"] == 1966
    r = client.put(f"/books/{book_id}", json={**DUNE, "title": "Dune (new edition)"})
    assert r.status_code == 200 and r.json()["year"] == 1965
    # DELETE -> 204 without body, then 404
    r = client.delete(f"/books/{book_id}")
    assert r.status_code == 204 and r.content == b""
    assert client.get(f"/books/{book_id}").status_code == 404


def test_error_status_codes(client):
    client.post("/books", json=DUNE)
    assert client.post("/books", json=DUNE).status_code == 409             # same ISBN
    assert client.post("/books", json={"title": "x"}).status_code == 422   # missing fields
    assert client.get("/books/not-an-object-id").status_code == 404        # bad id: 404, not 500
    assert client.get("/books/0123456789abcdef01234567").status_code == 404


def test_every_request_is_logged_as_json_in_mongo(client, mdb):
    client.post("/books", json=DUNE, headers={"X-User-Id": "U42"})
    client.get("/books/0123456789abcdef01234567", headers={"X-User-Id": "U42"})
    created = mdb.logs.find_one({"action": "book_created"})
    assert created["level"] == "INFO" and created["user_id"] == "U42"
    assert created["status"] == 201 and created["service"] == "books-api"
    missing = mdb.logs.find_one({"action": "book_not_found"})
    assert missing["level"] == "WARN" and missing["status"] == 404


def test_course_queries_on_the_seed_dataset(client):
    # json.loads on each NDJSON line, then POST: the client side of the course
    for line in SEED.read_text().splitlines():
        assert client.post("/logs", json=json.loads(line)).status_code == 201
    # sent a second time: 200, no duplicate
    assert client.post("/logs", json=json.loads(SEED.read_text().splitlines()[0])).status_code == 200
    stats = client.get("/logs/stats", params={"now": "2025-09-18T10:00:00Z"}).json()
    assert stats["q1_errors_last_hours"]["count"] == 3
    assert stats["q2_actions_of_user"]["actions"][0] == "create_order_retry"
    assert stats["q3_services_with_warn"] == ["auth-api", "orders-api", "payment-api"]


def test_invalid_log_level_is_rejected(client):
    bad = {"timestamp": "2025-09-18T10:00:00Z", "level": "DEBUG", "service": "x",
           "user_id": "U1", "action": "y"}
    assert client.post("/logs", json=bad).status_code == 422
