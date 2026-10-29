"""
Structured JSON logs (DEVOP2 Unit 01: "Logs = time-stamped records of events").

Every log is a JSON document with the metadata seen in the course:
    timestamp  when            (real BSON Date in MongoDB, ISO 8601 on stdout)
    level      how serious     INFO / WARN / ERROR
    service    who emitted it  books-api
    user_id    for whom        X-User-Id header, "anonymous" otherwise
    action     what happened   book_created, book_not_found, ...
    + context  method, path, status, duration_ms, ... (free fields)

The same document is written to two places:
    - MongoDB (collection logs)  -> can be queried later (Unit 01 queries)
    - stdout, one JSON per line  -> `docker compose logs api` (12-factor)
A logging failure must never break the API: errors are swallowed.
"""
import json
import logging
import sys
from datetime import datetime, timezone

from . import config
from .db import get_database

# The course dataset uses WARN, Python calls it WARNING: align the names.
logging.addLevelName(logging.WARNING, "WARN")


class MongoHandler(logging.Handler):
    """logging.Handler that inserts each record into the `logs` collection."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            get_database().logs.insert_one(to_document(record))
        except Exception:
            # MongoDB down: the event is still on stdout, the request goes on.
            self.handleError(record)


class JsonLineFormatter(logging.Formatter):
    """One JSON object per line (NDJSON), like the course's logs.ndjson."""

    def format(self, record: logging.LogRecord) -> str:
        doc = to_document(record)
        doc["timestamp"] = doc["timestamp"].isoformat().replace("+00:00", "Z")
        return json.dumps(doc, default=str)


def to_document(record: logging.LogRecord) -> dict:
    doc = {
        "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc),
        "level": record.levelname,
        "service": config.SERVICE_NAME,
        "user_id": getattr(record, "user_id", "system"),
        "action": record.getMessage(),
    }
    doc.update(getattr(record, "fields", {}))
    return doc


def get_logger() -> logging.Logger:
    logger = logging.getLogger("bookandride")
    if not logger.handlers:  # configure once, even if imported many times
        logger.setLevel(logging.INFO)
        logger.propagate = False
        stdout = logging.StreamHandler(sys.stdout)
        stdout.setFormatter(JsonLineFormatter())
        mongo = MongoHandler()
        mongo.handleError = lambda record: None  # silent: stdout already has it
        logger.addHandler(stdout)
        logger.addHandler(mongo)
    return logger


def log_event(level: int, action: str, user_id: str = "system", **fields) -> None:
    """Shortcut: log_event(logging.INFO, "book_created", "U1", book_id="...")."""
    get_logger().log(level, action, extra={"user_id": user_id, "fields": fields})
