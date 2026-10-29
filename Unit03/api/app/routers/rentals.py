import math
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Rental
from ..pricing import calculate_price
from ..schemas import RentalStart, RentalStop

router = APIRouter(prefix="/rentals", tags=["rentals"])


def _to_dict(r: Rental) -> dict:
    return {"rental_id": r.id, "user_id": r.user_id, "bike_id": r.bike_id,
            "started_at": r.started_at, "stopped_at": r.stopped_at,
            "price_eur": r.price_eur}


@router.post("/start", status_code=status.HTTP_201_CREATED)
def start_rental(payload: RentalStart, response: Response, db: Session = Depends(get_db),
                 x_user_id: int = Header(default=1)):
    # X-User-Id header (default 1): temporary, the gateway will set it in Unit 04
    # a bike cannot be rented twice at the same time
    busy = db.scalar(select(Rental).where(Rental.bike_id == payload.bike_id,
                                          Rental.stopped_at.is_(None)))
    if busy:
        raise HTTPException(status_code=409, detail=f"{payload.bike_id} is already rented")
    rental = Rental(user_id=x_user_id, bike_id=payload.bike_id,
                    started_at=datetime.now(timezone.utc))   # always store UTC
    db.add(rental)
    db.commit()
    db.refresh(rental)
    response.headers["Location"] = f"/rentals/{rental.id}"   # 201 + Location (cheat sheet)
    return {"rental_id": rental.id, "bike_id": rental.bike_id,
            "started_at": rental.started_at.isoformat()}


@router.post("/stop")
def stop_rental(payload: RentalStop, db: Session = Depends(get_db)):
    rental = db.get(Rental, payload.rental_id)
    if rental is None:
        raise HTTPException(status_code=404, detail="Rental not found")
    if rental.stopped_at is not None:
        raise HTTPException(status_code=409, detail="Rental already stopped")
    now = datetime.now(timezone.utc)
    started = rental.started_at
    if started.tzinfo is None:                 # SQLite drops the timezone
        started = started.replace(tzinfo=timezone.utc)
    # every started minute counts: 61 seconds = 2 minutes
    minutes = max(1, math.ceil((now - started).total_seconds() / 60))
    rental.stopped_at = now
    rental.total_minutes = minutes
    rental.price_eur = calculate_price(minutes)
    db.commit()
    return {"rental_id": rental.id, "duration_min": minutes, "price_eur": rental.price_eur}


@router.get("")
def list_rentals(db: Session = Depends(get_db)):
    rentals = db.scalars(select(Rental).order_by(Rental.id)).all()
    return [_to_dict(r) for r in rentals]


# Stretch goal: rental history of the current user.
# Must be declared BEFORE "/{rental_id}": otherwise "me" would match {rental_id} -> 422.
@router.get("/me")
def my_rentals(db: Session = Depends(get_db), x_user_id: int = Header(default=1)):
    rentals = db.scalars(select(Rental).where(Rental.user_id == x_user_id)
                         .order_by(Rental.id)).all()
    return [_to_dict(r) for r in rentals]


# Target of the Location header returned by POST /rentals/start
@router.get("/{rental_id}")
def get_rental(rental_id: int, db: Session = Depends(get_db)):
    rental = db.get(Rental, rental_id)
    if rental is None:
        raise HTTPException(status_code=404, detail="Rental not found")
    return _to_dict(rental)
