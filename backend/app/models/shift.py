from __future__ import annotations

from datetime import date

from sqlalchemy import Date, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Shift(Base):
    __tablename__ = "shifts"

    id: Mapped[int] = mapped_column(primary_key=True)
    bar_id: Mapped[int] = mapped_column(ForeignKey("bars.id"), index=True)
    spot_id: Mapped[int] = mapped_column(ForeignKey("spots.id"), index=True)
    bartender_name: Mapped[str] = mapped_column(String(100), default="")  # MVP: no auth yet
    shift_date: Mapped[date] = mapped_column(Date)

    # Raw inputs (v1)
    personal_sales_volume: Mapped[float] = mapped_column(Float)
    total_bar_sales: Mapped[float] = mapped_column(Float)
    personal_tips: Mapped[float] = mapped_column(Float)
    hours_worked: Mapped[float] = mapped_column(Float)
    transactions_count: Mapped[int | None] = mapped_column(Integer, default=None)

    # Derived (v1)
    pct_of_bar_sales: Mapped[float] = mapped_column(Float)
    tip_pct: Mapped[float] = mapped_column(Float)
    sales_per_hour: Mapped[float] = mapped_column(Float)
