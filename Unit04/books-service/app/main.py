"""
Book&Ride - Unit 04 - books service = the Unit 03 monolith WITHOUT the rentals
module (extracted into rentals-service/, see ADR-004). Behind the gateway.

Kept from Unit 03: configuration per environment (APP_ENV, config.yaml,
secrets from the environment), JSON logs -> MongoDB, /health with the DB.

Behaviour that changes with the environment (same code, same image):
    DEBUG true  -> /docs, /redoc and GET /config (masked) are available
    DEBUG false -> they are switched off (smaller attack surface in prod)
    LOG_LEVEL   -> DEBUG (dev), INFO (staging), WARNING (prod)
"""
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from . import models  # noqa: F401  (registers the tables in Base.metadata)
from .db import Base, engine
from .logs import log_event
from .routers import books
from .settings import get_settings

settings = get_settings()     # invalid configuration -> the app refuses to start


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)     # create the tables if they don't exist
    log_event(logging.WARNING if settings.APP_ENV == "prod" else logging.INFO,
              "app_started", debug=settings.DEBUG, log_level=settings.LOG_LEVEL)
    yield


app = FastAPI(
    title=f"Book&Ride books service ({settings.APP_ENV})", version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,          # no Swagger UI in prod
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
)


@app.middleware("http")
async def json_access_log(request: Request, call_next):
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception as exc:
        log_event(logging.ERROR, "unhandled_exception", request.headers.get("x-user-id", "anonymous"),
                  path=request.url.path, error=repr(exc))
        return JSONResponse({"detail": "Internal server error"}, status_code=500)
    if request.url.path != "/health":
        code = response.status_code
        level = logging.ERROR if code >= 500 else logging.WARNING if code >= 400 else logging.INFO
        log_event(level, f"{request.method} {request.url.path}",
                  request.headers.get("x-user-id", "anonymous"), status=code,
                  duration_ms=round((time.perf_counter() - start) * 1000, 2))
    return response


@app.get("/health", tags=["health"])
def health():
    # /health also checks the database: if PostgreSQL is down, the API answers 503
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(status_code=503, detail="database unavailable")
    return {"status": "ok", "service": "books", "env": settings.APP_ENV, "version": settings.APP_VERSION}


@app.get("/config", tags=["health"])
def show_config():
    """Debug helper: the configuration actually loaded, secrets masked. 404 in prod."""
    if not settings.DEBUG:
        raise HTTPException(status_code=404, detail="Not Found")
    return settings.describe()


app.include_router(books.router)
