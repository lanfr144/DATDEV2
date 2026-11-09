"""rentals -> books: the synchronous call between services and its failures.

httpx.get is replaced by a fake: no books service is needed, and we can make
it answer 200, 404, a 500 or raise a timeout at will.
"""
import httpx
import pytest
from fastapi.testclient import TestClient

from app import books_client
from app.main import app

USER = {"X-User-Id": "1"}


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def fake_books(monkeypatch, *, status=200, exc=None):
    calls = []

    def fake_get(url, timeout):
        calls.append((url, timeout))
        if exc:
            raise exc
        return httpx.Response(status, json={"id": 7, "title": "Dune"},
                              request=httpx.Request("GET", url))
    monkeypatch.setattr(books_client.httpx, "get", fake_get)
    return calls


def test_existing_book_is_added_to_the_rental(client, monkeypatch):
    calls = fake_books(monkeypatch)
    r = client.post("/rentals/start", json={"bike_id": "BIKE-70", "book_id": 7}, headers=USER)
    assert r.status_code == 201 and r.json()["book"] == {"id": 7, "title": "Dune"}
    url, timeout = calls[0]
    assert url.endswith("/books/7") and timeout == 2.0          # always a timeout


def test_unknown_book_gives_404(client, monkeypatch):
    fake_books(monkeypatch, status=404)
    r = client.post("/rentals/start", json={"bike_id": "BIKE-71", "book_id": 999}, headers=USER)
    assert r.status_code == 404


@pytest.mark.parametrize("failure", [{"exc": httpx.ConnectError("refused")},
                                     {"exc": httpx.ReadTimeout("too slow")},
                                     {"status": 500}])
def test_books_down_gives_503_and_no_rental(client, monkeypatch, failure, request):
    bike = f"BIKE-72{request.node.callspec.indices['failure']}"   # one bike per case
    fake_books(monkeypatch, **failure)
    r = client.post("/rentals/start", json={"bike_id": bike, "book_id": 7}, headers=USER)
    assert r.status_code == 503 and r.headers["retry-after"] == "5"
    # nothing half-done: the bike is still free once books is back
    fake_books(monkeypatch)
    assert client.post("/rentals/start", json={"bike_id": bike, "book_id": 7},
                       headers=USER).status_code == 201


def test_no_book_no_call(client, monkeypatch):
    calls = fake_books(monkeypatch)
    assert client.post("/rentals/start", json={"bike_id": "BIKE-73"}, headers=USER).status_code == 201
    assert calls == []
