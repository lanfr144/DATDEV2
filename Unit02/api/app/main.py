"""
Book&Ride - Unit 02 - books API (FastAPI) + logs MongoDB -> Elasticsearch -> Kibana.

Kept from Unit 01: REST /books, JSON logs of every request in MongoDB, /logs/stats.
New in Unit 02:
    DATOP2 U02 (framework) : full Pydantic validation, Path/Query constraints,
                             BackgroundTasks, tests with TestClient (tests/)
    DEVOP2 U02 (ELK)       : books indexed in Elasticsearch (/books/search),
                             logs shipped from MongoDB to Elasticsearch by the
                             `shipper` service, dashboards in Kibana

Run locally:   uvicorn app.main:app --port $API_PORT   (from the api/ folder)
Run in Docker: docker compose up -d --wait              (from Unit02/)
"""
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from . import config, search
from .db import create_indexes, get_database
from .logs import log_event
from .routers import books, logs


_indexes_ready = False


def ensure_indexes() -> None:
    """Create the indexes once. Called at start-up AND by /health: if MongoDB
    was not reachable at start-up, the first successful healthcheck does it."""
    global _indexes_ready
    if not _indexes_ready:
        create_indexes(get_database())
        _indexes_ready = True


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        ensure_indexes()
        log_event(logging.INFO, "app_started", version=config.APP_VERSION)
    except Exception as exc:  # MongoDB not ready yet: /health will retry
        log_event(logging.WARNING, "mongo_unavailable_at_startup", error=str(exc))
    yield


app = FastAPI(title="Book&Ride - books API (Unit 02)", version=config.APP_VERSION,
              lifespan=lifespan)
app.include_router(books.router)
app.include_router(logs.router)


@app.middleware("http")
async def json_access_log(request: Request, call_next):
    """One JSON log per request. The level follows the status code:
    2xx/3xx -> INFO, 4xx -> WARN (client error), 5xx -> ERROR (server error)."""
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception as exc:  # unexpected bug: log it as ERROR, answer a JSON 500
        log_event(logging.ERROR, "unhandled_exception",
                  request.headers.get("x-user-id", "anonymous"),
                  method=request.method, path=request.url.path, error=repr(exc))
        return JSONResponse({"detail": "Internal server error"}, status_code=500)
    if request.url.path != "/health":  # the healthcheck runs every 5 s: no noise
        code = response.status_code
        level = logging.ERROR if code >= 500 else logging.WARNING if code >= 400 else logging.INFO
        default = "validation_failed" if code == 422 else "http_request"
        log_event(level, getattr(request.state, "action", default),
                  request.headers.get("x-user-id", "anonymous"),
                  method=request.method, path=request.url.path, status=code,
                  duration_ms=round((time.perf_counter() - start) * 1000, 2))
    return response


@app.get("/", tags=["health"])
def root():
    return {"service": config.SERVICE_NAME, "version": config.APP_VERSION, "docs": "/docs"}


@app.get("/health", tags=["health"])
def health():
    """Used by the Docker HEALTHCHECK: 200 only if MongoDB answers a ping."""
    try:
        get_database().command("ping")
        ensure_indexes()
    except Exception:
        raise HTTPException(status_code=503, detail="MongoDB unavailable")
    # Elasticsearch is optional: the API stays healthy without it (degraded search)
    return {"status": "ok", "service": config.SERVICE_NAME, "version": config.APP_VERSION,
            "search_engine": "elasticsearch" if search.enabled() else "mongodb"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=config.API_PORT)
