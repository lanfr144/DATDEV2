"""
Pydantic models = the JSON contract of the API, now with full validation
(DATOP2 Unit 02b "FastAPI with POST, validation & testing").

Invalid data never reaches MongoDB: FastAPI answers 422 with the exact field
and reason (loc / msg / type). The same rules are written as a DRF serializer
in django-books/catalog/serializers.py, for comparison.
"""
from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator

ISBN_PATTERN = r"^97[89]-?\d{1,5}-?\d{1,7}-?\d{1,7}-?\d$"   # ISBN-13, hyphens optional
Tag = Annotated[str, Field(min_length=2, max_length=20)]


class BookIn(BaseModel):
    """Body of POST /books and PUT /books/{id}."""
    title: str = Field(min_length=1, max_length=200)
    author: str = Field(min_length=1, max_length=100)
    year: int = Field(ge=1450, description="Publication year (printing press: 1450)")
    isbn: str = Field(pattern=ISBN_PATTERN)
    price: float = Field(gt=0, le=1000, description="Price in euros")
    tags: list[Tag] = Field(default_factory=list, max_length=5)
    available: bool = True

    # same rule as validate_published() of the DATOP2 Django lab
    @field_validator("year")
    @classmethod
    def not_in_the_future(cls, value: int) -> int:
        if value > date.today().year:
            raise ValueError("The publication year cannot be in the future")
        return value

    # "Python", "python " and "PYTHON" are the same tag; duplicates removed
    @field_validator("tags")
    @classmethod
    def normalise_tags(cls, tags: list[str]) -> list[str]:
        return sorted({t.strip().lower() for t in tags})

    model_config = {"json_schema_extra": {"example": {
        "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593",
        "price": 9.99, "tags": ["sci-fi", "classic"], "available": True}}}


class BookPatch(BaseModel):
    """Body of PATCH /books/{id}: every field optional, same constraints."""
    title: str | None = Field(default=None, min_length=1, max_length=200)
    price: float | None = Field(default=None, gt=0, le=1000)
    tags: list[Tag] | None = Field(default=None, max_length=5)
    available: bool | None = None


class BookOut(BookIn):
    id: str


class SearchHit(BookOut):
    score: float | None = None   # relevance computed by Elasticsearch (None = MongoDB fallback)


class SearchResult(BaseModel):
    engine: Literal["elasticsearch", "mongodb"]
    total: int
    hits: list[SearchHit]


class LogIn(BaseModel):
    """A log sent by a client (same fields as the course's logs.ndjson)."""
    timestamp: datetime
    level: Literal["INFO", "WARN", "ERROR"]
    service: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    action: str = Field(min_length=1)

    model_config = {"extra": "allow"}
