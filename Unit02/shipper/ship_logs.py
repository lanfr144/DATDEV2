"""
Book&Ride - Unit 02 - log shipper: MongoDB -> Elasticsearch (_bulk API).

Plays the role of the "collector" of the ELK pipeline (Logstash / Beats /
Elastic Agent in production): every SHIP_INTERVAL seconds it reads the NEW
documents of the MongoDB `logs` collection and sends them to Elasticsearch
with ONE _bulk request (NDJSON: one action line + one document line).

    MongoDB (system of record) --ship_logs.py--> Elasticsearch --> Kibana

Design choices:
    - Checkpoint = the last shipped ObjectId, saved in MongoDB (shipper_state).
      ObjectIds grow with time, so "_id > checkpoint" = the new logs.
      A restart of the shipper continues where it stopped.
    - Elasticsearch _id = MongoDB _id: sending the same log twice overwrites
      it instead of creating a duplicate (idempotent, at-least-once delivery).
    - timestamp -> @timestamp (Kibana convention), and a `message` sentence
      for full-text search ("payment" matches "payment-api").
    - Heartbeat file touched at every loop: the Docker healthcheck checks it.
"""
import json
import logging
import os
import time
from datetime import timezone
from pathlib import Path
from urllib.parse import quote_plus

import requests
from pymongo import MongoClient

logging.basicConfig(level=logging.INFO, format='{"level":"%(levelname)s","service":"shipper","action":"%(message)s"}')
log = logging.getLogger("shipper")

ES_URL = os.environ["ES_URL"]
ES_AUTH = (os.environ["ES_USER"], os.environ["ES_PASSWORD"])
ES_CA = os.getenv("ES_CA_CERT") or True
LOGS_INDEX = os.getenv("LOGS_INDEX", "logs-bookandride")
INTERVAL = float(os.getenv("SHIP_INTERVAL", "5"))
BATCH = int(os.getenv("SHIP_BATCH", "500"))
HEARTBEAT = Path(os.getenv("HEARTBEAT_FILE", "/tmp/heartbeat"))


def mongo_db():
    user = quote_plus(os.environ["MONGO_ROOT_USER"])
    password = quote_plus(os.environ["MONGO_ROOT_PASSWORD"])
    uri = f"mongodb://{user}:{password}@{os.environ['MONGO_HOST']}:{os.environ['MONGO_PORT']}/?authSource=admin"
    return MongoClient(uri, serverSelectionTimeoutMS=5000, tz_aware=True)[os.environ["MONGO_DB"]]


def to_es(doc: dict) -> dict:
    out = {k: v for k, v in doc.items() if k not in ("_id", "timestamp")}
    out["@timestamp"] = doc["timestamp"].astimezone(timezone.utc).isoformat()
    out["message"] = f"{doc.get('service')} {doc.get('action')} user={doc.get('user_id')}"
    return out


def ship_once(db) -> int:
    state = db.shipper_state.find_one({"_id": LOGS_INDEX}) or {}
    query = {"_id": {"$gt": state["last_id"]}} if "last_id" in state else {}
    docs = list(db.logs.find(query).sort("_id", 1).limit(BATCH))
    if not docs:
        return 0
    lines = []
    for d in docs:
        lines.append(json.dumps({"index": {"_index": LOGS_INDEX, "_id": str(d["_id"])}}))
        lines.append(json.dumps(to_es(d), default=str))
    r = requests.post(f"{ES_URL}/_bulk", data="\n".join(lines) + "\n", auth=ES_AUTH,
                      verify=ES_CA, timeout=10,
                      headers={"Content-Type": "application/x-ndjson"})
    r.raise_for_status()
    if r.json().get("errors"):
        first = next(i for i in r.json()["items"] if i["index"].get("error"))
        raise RuntimeError(f"bulk error: {first['index']['error']}")
    # checkpoint saved only AFTER Elasticsearch confirmed: no log is lost
    db.shipper_state.update_one({"_id": LOGS_INDEX}, {"$set": {"last_id": docs[-1]["_id"]}},
                                upsert=True)
    return len(docs)


def main() -> None:
    db = mongo_db()
    log.info(f"started index={LOGS_INDEX} interval={INTERVAL}s")
    while True:
        try:
            n = ship_once(db)
            if n:
                log.info(f"shipped {n} logs")
            HEARTBEAT.touch()            # healthy only if the loop really works
        except Exception as exc:         # ES or MongoDB down: retry at the next loop
            log.warning(f"ship_failed {exc}")
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
