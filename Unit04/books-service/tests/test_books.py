"""books service: CRUD without API key (checked by the gateway, see smoke_test.sh)."""
from fastapi.testclient import TestClient

from app.db import Base, engine
from app.main import app

Base.metadata.drop_all(bind=engine)
DUNE = {"title": "Dune", "author": "Frank Herbert", "year": 1965,
        "isbn": "978-0441013593", "price": 9.99, "stock": 5}


def test_health():
    with TestClient(app) as client:
        assert client.get("/health").json()["service"] == "books"


def test_books_crud():
    with TestClient(app) as client:
        r = client.post("/books", json=DUNE)
        assert r.status_code == 201 and r.headers["location"] == f"/books/{r.json()['id']}"
        assert client.post("/books", json=DUNE).status_code == 409
        assert client.put(r.headers["location"], json={"stock": 1}).json()["stock"] == 1
        assert client.delete(r.headers["location"]).status_code == 204
        assert client.post("/books", json={**DUNE, "year": 2999}).status_code == 422
