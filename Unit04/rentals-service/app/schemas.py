from pydantic import BaseModel, Field


class RentalStart(BaseModel):
    bike_id: str = Field(pattern=r"^BIKE-\d{2,}$")    # e.g. BIKE-01


class RentalStop(BaseModel):
    rental_id: int
