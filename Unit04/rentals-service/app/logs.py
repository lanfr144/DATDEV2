"""
JSON logs of the rentals service, same format as all the Units (Mongo + stdout).
Two release fields are added to each log: version and color. This is what
makes a canary analysis possible: "errors per version" is one MongoDB query.
"""
import json
import logging
import os
import sys
from datetime import datetime, timezone
from urllib.parse import quote_plus

from .release import APP_VERSION, COLOR

logging.addLevelName(logging.WARNING, "WARN")
_collection = None


def logs_collection():
    global _collection
    if _collection is None and os.getenv("MONGO_HOST"):
        from pymongo import MongoClient
        uri = (f"mongodb://{quote_plus(os.environ['MONGO_ROOT_USER'])}:"
               f"{quote_plus(os.environ['MONGO_ROOT_PASSWORD'])}@{os.environ['MONGO_HOST']}:"
               f"{os.getenv('MONGO_PORT', '27017')}/?authSource=admin")
        _collection = MongoClient(uri, serverSelectionTimeoutMS=2000)[os.getenv("MONGO_DB", "logs")].logs
    return _collection


def log_event(level: int, action: str, user_id: str = "system", **fields) -> None:
    if level < logging.getLevelName(os.getenv("LOG_LEVEL", "INFO")):
        return
    doc = {"timestamp": datetime.now(timezone.utc), "level": logging.getLevelName(level),
           "service": "rentals", "version": APP_VERSION, "color": COLOR,
           "user_id": user_id, "action": action, **fields}
    print(json.dumps(doc, default=str), file=sys.stdout, flush=True)
    try:
        collection = logs_collection()
        if collection is not None:
            collection.insert_one(doc)
    except Exception:
        pass        # logging must never break a request
