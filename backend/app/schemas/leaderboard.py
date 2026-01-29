from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class LeaderboardEntry(BaseModel):
    bartender_name: str
    avg_score: float = Field(..., ge=0, le=100)
    shifts_count: int = Field(..., ge=0)
    last_shift_date: date | None = None


class LeaderboardResponse(BaseModel):
    bar_id: int
    start_date: date | None = None
    end_date: date | None = None
    entries: list[LeaderboardEntry]
