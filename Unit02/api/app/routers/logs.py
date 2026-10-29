"""
/logs - the DEVOP2 Unit 01 log exercise, exposed through the API.

    POST /logs          201  store a JSON log sent by a client (json.dumps + requests.post)
                        200  the same log was already stored (idempotent: no duplicate)
    GET  /logs          200  last logs, filters ?level= ?service= ?user_id=
    GET  /logs/stats    200  the three queries of the course:
                             Q1 number of ERRORs in the last 24 h
                             Q2 actions of one user (?user_id=U12345)
                             Q3 distinct services that reported a WARN

?now= fixes the reference time. The course dataset is from September 2025:
"the last 24 h" relative to the real clock would always be empty, so the
exercise imposes NOW = 2025-09-18T10:00:00Z (see mongo/queries.js).
"""
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request, Response, status
from pymongo.database import Database

from ..db import get_database
from ..schemas import LogIn

router = APIRouter(prefix="/logs", tags=["logs"])


def clean(doc: dict) -> dict:
    """Remove the ObjectId (not JSON serialisable) and print dates in ISO 8601."""
    doc.pop("_id", None)
    if isinstance(doc.get("timestamp"), datetime):
        doc["timestamp"] = doc["timestamp"].astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return doc


@router.post("", status_code=status.HTTP_201_CREATED)
def ingest_log(entry: LogIn, request: Request, response: Response,
               db: Database = Depends(get_database)):
    doc = entry.model_dump()                       # extra fields are kept
    doc["timestamp"] = entry.timestamp.astimezone(timezone.utc)   # real Date, not a string
    # Idempotent, like mongo/init/01-seed-logs.js: a client that retries after a
    # timeout (or a dataset sent twice) must not double the counts of /logs/stats.
    key = {k: doc[k] for k in ("timestamp", "service", "user_id", "action")}
    result = db.logs.update_one(key, {"$setOnInsert": doc}, upsert=True)
    if result.upserted_id is None:
        response.status_code = status.HTTP_200_OK
        request.state.action = "log_already_present"
    else:
        request.state.action = "log_ingested"
    return clean(doc)


@router.get("")
def list_logs(request: Request,
              level: Literal["INFO", "WARN", "ERROR"] | None = None,
              service: str | None = None, user_id: str | None = None,
              limit: int = Query(default=20, ge=1, le=200),
              db: Database = Depends(get_database)):
    request.state.action = "logs_listed"
    query = {k: v for k, v in {"level": level, "service": service, "user_id": user_id}.items() if v}
    return [clean(d) for d in db.logs.find(query).sort("timestamp", -1).limit(limit)]


@router.get("/stats")
def log_stats(request: Request, now: datetime | None = None,
              hours: int = Query(default=24, ge=1, le=24 * 30),
              user_id: str = "U12345",
              db: Database = Depends(get_database)):
    request.state.action = "log_stats"
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    since = now - timedelta(hours=hours)
    window = {"$gte": since, "$lt": now}           # [now - 24 h ; now[
    errors = list(db.logs.find({"level": "ERROR", "timestamp": window},
                               {"_id": 0}).sort("timestamp", 1))
    actions = list(db.logs.find({"user_id": user_id}, {"_id": 0}).sort("timestamp", 1))
    return {
        "window": {"from": clean({"timestamp": since})["timestamp"],
                   "to": clean({"timestamp": now})["timestamp"]},
        "q1_errors_last_hours": {"count": len(errors),
                                 "services": sorted({e["service"] for e in errors})},
        "q2_actions_of_user": {"user_id": user_id,
                               "actions": [clean(a)["action"] for a in actions]},
        "q3_services_with_warn": sorted(db.logs.distinct("service", {"level": "WARN"})),
    }
