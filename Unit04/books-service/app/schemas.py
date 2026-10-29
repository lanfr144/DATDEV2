"""Pydantic contract - same validation rules as Unit 02, adapted to the SQL model."""
from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator

ISBN_PATTERN = r"^97[89]-?\d{1,5}-?\d{1,7}-?\d{1,7}-?\d$"


class BookIn(BaseModel):              # body of POST /books
    title: str = Field(min_length=1, max_length=200)
    author: str = Field(min_length=1, max_length=100)
    year: int = Field(ge=1450)
    isbn: str = Field(pattern=ISBN_PATTERN)
    price: float = Field(gt=0, le=1000)
    stock: int = Field(default=0, ge=0)

    @field_validator("year")
    @classmethod
    def not_in_the_future(cls, value: int) -> int:
        if value > date.today().year:
            raise ValueError("The publication year cannot be in the future")
        return value


class BookUpdate(BaseModel):          # every field optional: send only what changes
    title: str | None = Field(default=None, min_length=1, max_length=200)
    price: float | None = Field(default=None, gt=0, le=1000)
    stock: int | None = Field(default=None, ge=0)


class BookOut(BookIn):
    model_config = ConfigDict(from_attributes=True)   # read from SQLAlchemy objects
    id: int

