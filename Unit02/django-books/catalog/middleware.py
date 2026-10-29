"""
One JSON log per request, same format as the FastAPI service, written to the
SAME MongoDB collection with service="books-django": both frameworks feed the
same log pipeline (MongoDB -> shipper -> Elasticsearch -> Kibana).
Without MONGO_HOST (tests, laptop), the log only goes to stdout.
"""
import json
import os
import sys
import time
from datetime import datetime, timezone
from urllib.parse import quote_plus

_collection = None


def logs_collection():
    global _collection
    if _collection is None and os.getenv("MONGO_HOST"):
        from pymongo import MongoClient
        uri = "mongodb://{}:{}@{}:{}/?authSource=admin".format(
            quote_plus(os.environ["MONGO_ROOT_USER"]), quote_plus(os.environ["MONGO_ROOT_PASSWORD"]),
            os.environ["MONGO_HOST"], os.environ.get("MONGO_PORT", "27017"))
        _collection = MongoClient(uri, serverSelectionTimeoutMS=2000)[os.environ["MONGO_DB"]].logs
    return _collection


class JsonLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.perf_counter()
        response = self.get_response(request)
        if request.path != "/health/":
            code = response.status_code
            doc = {
                "timestamp": datetime.now(timezone.utc),
                "level": "ERROR" if code >= 500 else "WARN" if code >= 400 else "INFO",
                "service": "books-django",
                "user_id": request.headers.get("X-User-Id", "anonymous"),
                "action": f"{request.method.lower()}_{request.path.strip('/').split('/')[0] or 'root'}",
                "method": request.method, "path": request.path, "status": code,
                "duration_ms": round((time.perf_counter() - start) * 1000, 2),
            }
            print(json.dumps(doc, default=str), file=sys.stdout, flush=True)
            try:
                collection = logs_collection()
                if collection is not None:
                    collection.insert_one(doc)
            except Exception:
                pass    # never break the request because logging failed
        return response
