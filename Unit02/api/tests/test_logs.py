"""Unit 02 - the Unit 01 log features still work (non-regression)."""
import json
from pathlib import Path

SEED = Path(__file__).resolve().parents[2] / "mongo" / "logs.ndjson"


def test_requests_are_logged(client, mdb, dune):
    client.post("/books", json={**dune, "price": -5}, headers={"X-User-Id": "U7"})
    log = mdb.logs.find_one({"action": "validation_failed"})
    assert log["level"] == "WARN" and log["status"] == 422 and log["user_id"] == "U7"


def test_course_queries(client):
    for line in SEED.read_text().splitlines():
        client.post("/logs", json=json.loads(line))
    stats = client.get("/logs/stats", params={"now": "2025-09-18T10:00:00Z"}).json()
    assert stats["q1_errors_last_hours"]["count"] == 3
    assert stats["q3_services_with_warn"] == ["auth-api", "orders-api", "payment-api"]
