from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.score_result import ScoreResult
from app.models.shift import Shift
from app.models.user import User
from app.schemas.leaderboard import LeaderboardEntry, LeaderboardResponse


router = APIRouter(prefix="/leaderboard")


@router.get("", response_model=LeaderboardResponse)
def get_leaderboard(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    limit: int = Query(10, ge=1, le=100),
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = (
        db.query(
            Shift.bartender_name.label("bartender_name"),
            func.avg(ScoreResult.score_total).label("avg_score"),
            func.count(Shift.id).label("shifts_count"),
            func.max(Shift.shift_date).label("last_shift_date"),
        )
        .join(ScoreResult, ScoreResult.shift_id == Shift.id)
        .filter(Shift.bar_id == current.bar_id)
        .filter(Shift.bartender_name != "")
        .group_by(Shift.bartender_name)
        .order_by(func.avg(ScoreResult.score_total).desc())
        .limit(limit)
    )

    if start_date is not None:
        q = q.filter(Shift.shift_date >= start_date)
    if end_date is not None:
        q = q.filter(Shift.shift_date <= end_date)

    rows = q.all()

    entries = [
        LeaderboardEntry(
            bartender_name=r.bartender_name,
            avg_score=float(r.avg_score or 0.0),
            shifts_count=int(r.shifts_count or 0),
            last_shift_date=r.last_shift_date,
        )
        for r in rows
    ]

    return LeaderboardResponse(
        bar_id=current.bar_id,
        start_date=start_date,
        end_date=end_date,
        entries=entries,
    )
