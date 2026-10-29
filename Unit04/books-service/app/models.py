"""
Relational model (SQLAlchemy 2): the books now live in PostgreSQL (see ADR-003).
Compared with the MongoDB documents of Units 01-02: a fixed schema, real
types, constraints enforced by the database (UNIQUE isbn) and transactions.
"""
from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class Book(Base):
    __tablename__ = "books"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    author: Mapped[str] = mapped_column(String(100))
    year: Mapped[int]
    isbn: Mapped[str] = mapped_column(String(17), unique=True)   # UNIQUE -> 409 on duplicate
    price: Mapped[float] = mapped_column(Numeric(7, 2, asdecimal=False))
    stock: Mapped[int] = mapped_column(default=0)

