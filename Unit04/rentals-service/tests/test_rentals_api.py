"""rentals service: business flow + release behaviour (versions, headers, faults)."""
import pytest
from fastapi.testclient import TestClient

from app import main
from app.db import Base, engine
from app.main import app

Base.metadata.drop_all(bind=engine)
USER = {"X-User-Id": "1"}          # in production this header is added by the gateway


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def start_and_stop(client, bike):
    rid = client.post("/rentals/start", json={"bike_id": bike}, headers=USER).json()["rental_id"]
    return client.post("/rentals/stop", json={"rental_id": rid}, headers=USER)


def test_rental_flow_and_ownership(client):
    r = client.post("/rentals/start", json={"bike_id": "BIKE-01"}, headers=USER)
    assert r.status_code == 201
    rid = r.json()["rental_id"]
    assert r.headers["location"] == f"/rentals/{rid}"
    assert client.get(r.headers["location"], headers=USER).status_code == 200
    assert client.get(r.headers["location"], headers={"X-User-Id": "2"}).status_code == 404
    assert client.post("/rentals/stop", json={"rental_id": rid}, headers={"X-User-Id": "2"}).status_code == 404
    assert client.post("/rentals/stop", json={"rental_id": rid}, headers=USER).json()["price_eur"] == 0.25


def test_user_header_required(client):
    assert client.post("/rentals/start", json={"bike_id": "BIKE-02"}).status_code == 422


def test_every_response_says_which_release_answered(client):
    r = client.get("/rentals/version")
    assert r.headers["x-app-version"] == "1.0.0" and r.headers["x-app-color"] == "blue"
    assert r.json()["features"] == {"price_detail": False, "price_cents": False}


def test_minor_version_adds_a_field(client, monkeypatch):
    monkeypatch.setitem(main.FEATURES, "price_detail", True)          # behaves like 1.1.0
    body = start_and_stop(client, "BIKE-11").json()
    assert body["price_eur"] == 0.25                                   # old field still there
    assert body["price_detail"]["remaining_minutes"] == 1


def test_major_version_breaks_the_contract(client, monkeypatch):
    monkeypatch.setitem(main.FEATURES, "price_cents", True)           # behaves like 2.0.0
    body = start_and_stop(client, "BIKE-20").json()
    assert "price_eur" not in body and body["price_cents"] == 25       # old clients break


def test_fault_injection_gives_500_and_is_logged(client, monkeypatch, capsys):
    monkeypatch.setattr(main, "FAULT_RATE", 1.0)                      # every stop fails
    r = start_and_stop(client, "BIKE-50")
    assert r.status_code == 500 and r.json() == {"detail": "Internal server error"}
    assert '"level": "ERROR"' in capsys.readouterr().out


def test_metrics_have_a_version_label(client):
    client.get("/rentals/version")
    body = client.get("/metrics").text
    assert 'version="1.0.0"' in body and "rentals_started_total" in body
