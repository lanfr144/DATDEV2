"""
Pydantic models = the JSON contract of the API (DATOP2 Unit 01: REST + JSON).

FastAPI uses them to:
    - read and validate the JSON body (invalid -> 422 Unprocessable Entity),
    - serialise the response (only the declared fields are returned),
    - document the API automatically on /docs.
Validation is kept light here; Unit 02 adds the full Field(...) constraints.
"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class BookIn(BaseModel):
    """Body of POST /books and PUT /books/{id} (PUT = full replacement)."""
    title: str = Field(min_length=1)
    author: str = Field(min_length=1)
    year: int
    isbn: str = Field(min_length=10, max_length=17)

    model_config = {"json_schema_extra": {"example": {
        "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593"}}}


class BookPatch(BaseModel):
    """Body of PATCH /books/{id}: every field is optional (partial update)."""
    title: str | None = Field(default=None, min_length=1)
    author: str | None = Field(default=None, min_length=1)
    year: int | None = None


class BookOut(BookIn):
    id: str  # MongoDB ObjectId as a string (24 hexadecimal characters)


class LogIn(BaseModel):
    """A log sent by a client (same fields as the course's logs.ndjson).

    extra="allow": any additional context field (order_id, amount, ...) is
    kept, exactly like a MongoDB document with a flexible schema.
    """
    timestamp: datetime
    level: Literal["INFO", "WARN", "ERROR"]
    service: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    action: str = Field(min_length=1)

    model_config = {"extra": "allow"}
