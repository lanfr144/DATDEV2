"""
Book&Ride - Unit 04 - rentals microservice (DATOP2 Unit 04), deployed in TWO
slots, blue and green, to practise the release strategies of DEVOP2 Unit 04:
blue/green, canary, rolling update and rollback (see ../scripts/).

Routes are prefixed with /rentals so the gateway forwards /rentals/... unchanged.
X-User-Id is mandatory: it is set by the gateway after checking X-API-Key.
This service publishes NO port: clients cannot bypass the gateway.

Every response carries X-App-Version and X-App-Color: the client (and the
canary analysis) can see which release answered.
"""
import logging
import math
import random
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from . import books_client
from .db import Base, engine, get_db
from .logs import log_event
from .models import Rental
from .pricing import calculate_price, price_detail
from .release import APP_VERSION, COLOR, FAULT_RATE, FEATURES
from .schemas import RentalStart, RentalStop


@asynccontextmanager
async def lifespan(app: FastAPI):
    # blue and green share the rentals database: the schema must stay compatible
    # between two versions that run at the same time (expand/contract, ADR-005).
    # Both slots start together: if the other one is creating the table at the
    # same moment, PostgreSQL may refuse once -> retry.
    for attempt in range(5):
        try:
            Base.metadata.create_all(bind=engine)
            break
        except Exception:
            if attempt == 4:
                raise
            time.sleep(1)
    log_event(logging.INFO, "app_started", features=[f for f, on in FEATURES.items() if on])
    yield


app = FastAPI(title="Book&Ride - rentals service", version=APP_VERSION, lifespan=lifespan)

# ---------- metrics: the "version" label lets Prometheus compare blue and green ----------
REQUESTS = Counter("http_requests_total", "HTTP requests",
                   ["method", "path", "status", "version", "color"])
LATENCY = Histogram("http_request_duration_seconds", "Request latency", ["path", "version"])
RENTALS_STARTED = Counter("rentals_started_total", "Rentals started", ["version"])
REVENUE = Counter("rentals_revenue_eur_total", "Revenue in euros", ["version"])


@app.middleware("http")
async def observe(request: Request, call_next):
    # the route template (/rentals/{rental_id}), not the URL: keeps the label set small
    with LATENCY.labels(request.url.path.split("/")[1] or "/", APP_VERSION).time():
        try:
            response = await call_next(request)
        except Exception as exc:
            log_event(logging.ERROR, "unhandled_exception", request.headers.get("x-user-id", "?"),
                      path=request.url.path, error=repr(exc))
            response = JSONResponse({"detail": "Internal server error"}, status_code=500)
    route = request.scope.get("route")
    path = route.path if route else request.url.path
    REQUESTS.labels(request.method, path, str(response.status_code), APP_VERSION, COLOR).inc()
    response.headers["X-App-Version"] = APP_VERSION
    response.headers["X-App-Color"] = COLOR
    if path not in ("/rentals/health", "/metrics"):
        code = response.status_code
        level = logging.ERROR if code >= 500 else logging.WARNING if code >= 400 else logging.INFO
        log_event(level, f"{request.method} {path}", request.headers.get("x-user-id", "?"),
                  status=code)
    return response


@app.get("/metrics", include_in_schema=False)
def metrics():
    """Internal: scraped by Prometheus directly, NOT routed by the gateway."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/rentals/health", tags=["health"])
def health():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(status_code=503, detail="database unavailable")
    return {"status": "ok", "service": "rentals", "version": APP_VERSION, "color": COLOR}


@app.get("/rentals/version", tags=["health"])
def version():
    """Which release is running here, and with which features (semantic versioning)."""
    return {"version": APP_VERSION, "color": COLOR, "features": FEATURES}


@app.post("/rentals/start", status_code=status.HTTP_201_CREATED, tags=["rentals"])
def start_rental(payload: RentalStart, response: Response, db: Session = Depends(get_db),
                 x_user_id: int = Header()):
    book = None
    if payload.book_id is not None:          # service-to-service call, with timeout
        try:
            book = books_client.get_book(payload.book_id)
        except books_client.BooksUnavailable as exc:
            log_event(logging.WARNING, "books_unavailable", str(x_user_id),
                      book_id=payload.book_id, error=str(exc))
            # the CALLER decides what a failure of the other service means: here
            # the rental is refused (no half-done rental) and the client may retry
            raise HTTPException(status_code=503, detail="books service unavailable, retry later",
                                headers={"Retry-After": "5"})
        if book is None:
            raise HTTPException(status_code=404, detail=f"Book {payload.book_id} not found")
    busy = db.scalar(select(Rental).where(Rental.bike_id == payload.bike_id,
                                          Rental.stopped_at.is_(None)))
    if busy:
        raise HTTPException(status_code=409, detail=f"{payload.bike_id} is already rented")
    rental = Rental(user_id=x_user_id, bike_id=payload.bike_id,
                    started_at=datetime.now(timezone.utc))
    db.add(rental)
    db.commit()
    db.refresh(rental)
    RENTALS_STARTED.labels(APP_VERSION).inc()
    response.headers["Location"] = f"/rentals/{rental.id}"
    out = {"rental_id": rental.id, "bike_id": rental.bike_id, "user_id": rental.user_id,
           "started_at": rental.started_at.isoformat()}
    if book is not None:                      # data owned by books, copied for the answer only
        out["book"] = {"id": book["id"], "title": book["title"]}
    return out


def price_fields(price_eur: float | None, minutes: int | None) -> dict:
    """The JSON contract of the price, which CHANGES with the major version."""
    if FEATURES["price_cents"]:                                   # 2.0.0: breaking change
        out = {"price_cents": None if price_eur is None else round(price_eur * 100)}
    else:                                                          # 1.x
        out = {"price_eur": price_eur}
    if FEATURES["price_detail"] and minutes is not None:          # 1.1.0: added field
        out["price_detail"] = price_detail(minutes)
    return out


@app.post("/rentals/stop", tags=["rentals"])
def stop_rental(payload: RentalStop, db: Session = Depends(get_db), x_user_id: int = Header()):
    if FAULT_RATE and random.random() < FAULT_RATE:               # simulated bug of a bad release
        raise RuntimeError("simulated defect (FAULT_RATE)")
    rental = db.get(Rental, payload.rental_id)
    if rental is None or rental.user_id != x_user_id:   # you can only stop your own rental
        raise HTTPException(status_code=404, detail="Rental not found")
    if rental.stopped_at is not None:
        raise HTTPException(status_code=409, detail="Rental already stopped")
    now = datetime.now(timezone.utc)
    started = rental.started_at
    if started.tzinfo is None:                 # SQLite drops the timezone
        started = started.replace(tzinfo=timezone.utc)
    minutes = max(1, math.ceil((now - started).total_seconds() / 60))   # every started minute
    rental.stopped_at = now
    rental.total_minutes = minutes
    rental.price_eur = calculate_price(minutes)   # the DATABASE always stores euros
    db.commit()
    REVENUE.labels(APP_VERSION).inc(rental.price_eur)
    return {"rental_id": rental.id, "duration_min": minutes,
            **price_fields(rental.price_eur, minutes)}


def to_dict(r: Rental) -> dict:
    return {"rental_id": r.id, "bike_id": r.bike_id, "started_at": r.started_at,
            "stopped_at": r.stopped_at, **price_fields(r.price_eur, r.total_minutes)}


@app.get("/rentals", tags=["rentals"])
def my_rentals(db: Session = Depends(get_db), x_user_id: int = Header()):
    rentals = db.scalars(select(Rental).where(Rental.user_id == x_user_id)
                         .order_by(Rental.id)).all()
    return [to_dict(r) for r in rentals]


# declared last so that /rentals/health and /rentals/version are matched first
@app.get("/rentals/{rental_id}", tags=["rentals"])
def get_rental(rental_id: int, db: Session = Depends(get_db), x_user_id: int = Header()):
    rental = db.get(Rental, rental_id)
    if rental is None or rental.user_id != x_user_id:
        raise HTTPException(status_code=404, detail="Rental not found")
    return to_dict(rental)
