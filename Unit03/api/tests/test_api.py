"""Monolith API (DATOP2 Unit 03 tests) + Unit 03 configuration behaviour."""
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.db import Base, SessionLocal, engine
from app.main import app
from app.models import Rental

Base.metadata.drop_all(bind=engine)   # every run starts with empty tables
KEY = {"X-API-Key": "test-api-key-123"}
DUNE = {"title": "Dune", "author": "Frank Herbert", "year": 1965,
        "isbn": "978-0441013593", "price": 9.99, "stock": 5}


def test_health_shows_the_environment():
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok", "env": "dev", "version": "1.0.0"}


def test_books_crud_with_api_key():
    with TestClient(app) as client:
        assert client.post("/books", json=DUNE).status_code == 401            # no key
        assert client.post("/books", json=DUNE, headers={"X-API-Key": "wrong-key"}).status_code == 401
        r = client.post("/books", json=DUNE, headers=KEY)
        assert r.status_code == 201
        book_id = r.json()["id"]
        assert r.headers["location"] == f"/books/{book_id}"
        assert client.post("/books", json=DUNE, headers=KEY).status_code == 409   # UNIQUE isbn
        assert client.get("/books", params={"search": "herbert"}).json()[0]["title"] == "Dune"
        assert client.put(f"/books/{book_id}", json={"stock": 10}, headers=KEY).json()["stock"] == 10
        assert client.delete(f"/books/{book_id}", headers=KEY).status_code == 204
        assert client.get(f"/books/{book_id}").status_code == 404
        r = client.post("/books", json={**DUNE, "title": "", "stock": -1}, headers=KEY)
        assert r.status_code == 422 and len(r.json()["detail"]) == 2


def test_rental_flow():
    with TestClient(app) as client:
        r = client.post("/rentals/start", json={"bike_id": "BIKE-01"})
        assert r.status_code == 201
        rid = r.json()["rental_id"]
        assert client.get(r.headers["location"]).json()["bike_id"] == "BIKE-01"
        assert client.post("/rentals/start", json={"bike_id": "BIKE-01"}).status_code == 409
        stop = client.post("/rentals/stop", json={"rental_id": rid}).json()
        assert stop == {"rental_id": rid, "duration_min": 1, "price_eur": 0.25}
        assert client.post("/rentals/stop", json={"rental_id": rid}).status_code == 409
        assert client.post("/rentals/start", json={"bike_id": "bike-1"}).status_code == 422


def test_my_rentals():
    with TestClient(app) as client:
        client.post("/rentals/start", json={"bike_id": "BIKE-42"}, headers={"X-User-Id": "7"})
        mine = client.get("/rentals/me", headers={"X-User-Id": "7"}).json()
        assert [r["bike_id"] for r in mine] == ["BIKE-42"]
        assert client.get("/rentals/999999").status_code == 404


def test_daily_cap_on_a_long_rental():
    """A rental of 1 day + 1 minute costs 12.25 (cap of 12 EUR per day)."""
    with TestClient(app) as client:
        rid = client.post("/rentals/start", json={"bike_id": "BIKE-77"}).json()["rental_id"]
        with SessionLocal() as db:               # pretend the rental started 24 h + 30 s ago
            db.get(Rental, rid).started_at = datetime.now(timezone.utc) - timedelta(days=1, seconds=30)
            db.commit()
        stop = client.post("/rentals/stop", json={"rental_id": rid}).json()
        assert stop["duration_min"] == 24 * 60 + 1 and stop["price_eur"] == 12.25


def test_debug_endpoints_exist_in_dev_and_secrets_are_masked():
    with TestClient(app) as client:
        assert client.get("/docs").status_code == 200                      # DEBUG true in dev
        cfg = client.get("/config").json()
        assert cfg["APP_ENV"] == "dev" and cfg["DEBUG"] is True
        assert cfg["API_KEY"] == "test... (masked)"
        assert "test-api-key-123" not in str(cfg) and "test-db-password" not in str(cfg)
