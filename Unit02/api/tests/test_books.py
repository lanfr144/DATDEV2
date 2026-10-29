"""Unit 02 - validation, query parameters, BackgroundTasks, search fallback."""
import pytest

from app import search


def test_create_returns_201_location_and_normalised_tags(client, dune):
    r = client.post("/books", json=dune)
    assert r.status_code == 201
    assert r.headers["location"] == f"/books/{r.json()['id']}"
    assert r.json()["tags"] == ["classic", "sci-fi"]      # lower-case, sorted
    assert r.json()["available"] is True                   # default value


@pytest.mark.parametrize("field, value", [
    ("title", ""),                 # min_length=1
    ("year", 1200),                # ge=1450
    ("year", 2999),                # field_validator: not in the future
    ("isbn", "12345"),             # pattern ISBN-13
    ("price", 0),                  # gt=0
    ("price", "cheap"),            # not a number
    ("tags", ["a", "b", "c", "d", "e", "f"]),   # max 5 tags (and min 2 characters)
])
def test_invalid_book_is_rejected_with_422(client, dune, field, value):
    r = client.post("/books", json={**dune, field: value})
    assert r.status_code == 422
    assert r.json()["detail"][0]["loc"][:2] == ["body", field]


def test_malformed_id_is_422_unknown_id_is_404(client):
    assert client.get("/books/not-an-id").status_code == 422          # Path(pattern=...)
    assert client.get("/books/0123456789abcdef01234567").status_code == 404


def test_query_parameters_filter_sort_and_paginate(client, dune):
    client.post("/books", json=dune)
    client.post("/books", json={**dune, "title": "Neuromancer", "author": "William Gibson",
                                "year": 1984, "isbn": "978-0441569595", "price": 8.5,
                                "tags": ["cyberpunk"]})
    client.post("/books", json={**dune, "title": "Foundation", "author": "Isaac Asimov",
                                "year": 1951, "isbn": "978-0553293357", "price": 7.99,
                                "available": False})
    titles = lambda **p: [b["title"] for b in client.get("/books", params=p).json()]
    assert titles(sort="-year") == ["Neuromancer", "Dune", "Foundation"]
    assert titles(min_year=1960) == ["Dune", "Neuromancer"]
    assert titles(tag="CYBERPUNK") == ["Neuromancer"]
    assert titles(available=False) == ["Foundation"]
    assert titles(sort="year", skip=1, limit=1) == ["Dune"]
    assert client.get("/books", params={"limit": 0}).status_code == 422
    assert client.get("/books", params={"sort": "isbn"}).status_code == 422   # Literal


def test_background_task_indexes_the_book(client, dune, monkeypatch):
    indexed = []
    monkeypatch.setattr(search, "index_book", lambda book_id, book: indexed.append(book_id))
    book_id = client.post("/books", json=dune).json()["id"]
    assert indexed == [book_id]      # TestClient runs background tasks before returning


def test_search_falls_back_to_mongodb_without_elasticsearch(client, dune):
    client.post("/books", json=dune)
    r = client.get("/books/search", params={"q": "herb"})
    assert r.json()["engine"] == "mongodb"
    assert [h["title"] for h in r.json()["hits"]] == ["Dune"]
    assert client.get("/books/search", params={"q": "x"}).status_code == 422   # min_length=2


def test_patch_put_delete(client, dune):
    url = client.post("/books", json=dune).headers["location"]
    assert client.patch(url, json={"price": 12.5}).json()["price"] == 12.5
    assert client.patch(url, json={"price": -1}).status_code == 422
    assert client.put(url, json={**dune, "title": "Dune II"}).json()["title"] == "Dune II"
    assert client.delete(url).status_code == 204
    assert client.delete(url).status_code == 404
