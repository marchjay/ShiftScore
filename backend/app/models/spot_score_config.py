from __future__ import annotations

from datetime import datetime
import enum

from sqlalchemy import DateTime, Enum, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SpotCapMode(str, enum.Enum):
    manual = "manual"
    auto = "auto"


class SpotScoreConfig(Base):
    __tablename__ = "spot_score_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    bar_id: Mapped[int] = mapped_column(ForeignKey("bars.id"), index=True)
    spot_id: Mapped[int] = mapped_column(ForeignKey("spots.id"), unique=True, index=True)

    cap_mode: Mapped[SpotCapMode] = mapped_column(Enum(SpotCapMode), default=SpotCapMode.manual)

    sales_volume_low: Mapped[float] = mapped_column(Float)
    sales_volume_high: Mapped[float] = mapped_column(Float)
    pct_of_bar_sales_low: Mapped[float] = mapped_column(Float)
    pct_of_bar_sales_high: Mapped[float] = mapped_column(Float)
    tip_pct_low: Mapped[float] = mapped_column(Float)
    tip_pct_high: Mapped[float] = mapped_column(Float)
    sales_per_hour_low: Mapped[float] = mapped_column(Float)
    sales_per_hour_high: Mapped[float] = mapped_column(Float)

    # Auto-caps metadata (optional)
    computed_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    sample_size: Mapped[int | None] = mapped_column(default=None)
    window_days: Mapped[int | None] = mapped_column(default=None)
    low_percentile: Mapped[float | None] = mapped_column(default=None)
    high_percentile: Mapped[float | None] = mapped_column(default=None)
