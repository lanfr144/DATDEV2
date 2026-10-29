"""
Structured JSON logs, same format as Units 01-03 (service = "books"), plus:
    env      dev / staging / prod   -> the logs of the 3 environments never mix
    version  APP_VERSION            -> which release produced the log (Unit 04)

The level threshold comes from the configuration (LOG_LEVEL): DEBUG in dev,
INFO in staging, WARNING in prod ("[PRODUCTION MODE] Logging minimal").
Destination: stdout (always) + MongoDB of the environment (if MONGO_HOST is set).
"""
import json
import logging
import sys
from datetime import datetime, timezone
from urllib.parse import quote_plus

from .settings import get_settings

logging.addLevelName(logging.WARNING, "WARN")
_collection = None


def logs_collection():
    global _collection
    s = get_settings()
    if _collection is None and s.MONGO_HOST:
        from pymongo import MongoClient
        uri = (f"mongodb://{quote_plus(s.MONGO_ROOT_USER)}:{quote_plus(s.MONGO_ROOT_PASSWORD)}"
               f"@{s.MONGO_HOST}:{s.MONGO_PORT}/?authSource=admin")
        _collection = MongoClient(uri, serverSelectionTimeoutMS=2000)[s.MONGO_DB].logs
    return _collection


def to_document(record: logging.LogRecord) -> dict:
    s = get_settings()
    doc = {
        "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc),
        "level": record.levelname,
        "service": "books",
        "env": s.APP_ENV,
        "version": s.APP_VERSION,
        "user_id": getattr(record, "user_id", "system"),
        "action": record.getMessage(),
    }
    doc.update(getattr(record, "fields", {}))
    return doc


class MongoHandler(logging.Handler):
    def emit(self, record):
        try:
            collection = logs_collection()
            if collection is not None:
                collection.insert_one(to_document(record))
        except Exception:
            pass        # logging must never break a request


class JsonLineFormatter(logging.Formatter):
    def format(self, record):
        doc = to_document(record)
        doc["timestamp"] = doc["timestamp"].isoformat().replace("+00:00", "Z")
        return json.dumps(doc, default=str)


def get_logger() -> logging.Logger:
    logger = logging.getLogger("bookandride")
    if not logger.handlers:
        logger.setLevel(get_settings().LOG_LEVEL)     # threshold of the environment
        logger.propagate = False
        stdout = logging.StreamHandler(sys.stdout)
        stdout.setFormatter(JsonLineFormatter())
        logger.addHandler(stdout)
        logger.addHandler(MongoHandler())
    return logger


def log_event(level: int, action: str, user_id: str = "system", **fields) -> None:
    get_logger().log(level, action, extra={"user_id": user_id, "fields": fields})
