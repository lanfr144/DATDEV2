from pydantic import BaseModel, Field


class RentalStart(BaseModel):
    bike_id: str = Field(pattern=r"^BIKE-\d{2,}$")    # e.g. BIKE-01
    # optional: borrow a book of the cafe for the ride. rentals then ASKS books
    # whether it exists (synchronous HTTP call between services, books_client.py)
    book_id: int | None = Field(default=None, ge=1)


class RentalStop(BaseModel):
    rental_id: int
