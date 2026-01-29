from __future__ import annotations

from sqlalchemy import Float, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ScoreResult(Base):
    __tablename__ = "score_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    shift_id: Mapped[int] = mapped_column(ForeignKey("shifts.id"), unique=True, index=True)
    score_total: Mapped[float] = mapped_column(Float)
    score_version: Mapped[str] = mapped_column(String(32), default="v1")
    breakdown_json: Mapped[dict] = mapped_column(JSON, default=dict)
