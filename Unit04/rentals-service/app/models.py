from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class Rental(Base):
    __tablename__ = "rentals"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int]
    bike_id: Mapped[str] = mapped_column(String(20))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    stopped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    total_minutes: Mapped[int | None]
    price_eur: Mapped[float | None]
