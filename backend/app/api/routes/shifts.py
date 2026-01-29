from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_owner
from app.db.session import get_db
from app.models.score_result import ScoreResult
from app.models.shift import Shift
from app.models.spot_score_config import SpotScoreConfig
from app.models.user import User, UserRole
from app.schemas.shifts import ShiftCreateIn, ShiftOut
from app.services.scoring import compute_shift


router = APIRouter(prefix="/shifts")


@router.post("", response_model=ShiftOut)
def create_shift(payload: ShiftCreateIn, owner: User = Depends(require_owner), db: Session = Depends(get_db)):
    if payload.bar_id != owner.bar_id:
        raise HTTPException(status_code=403, detail="Not allowed")

    cfg = (
        db.query(SpotScoreConfig)
        .filter(SpotScoreConfig.spot_id == payload.spot_id)
        .first()
    )
    if cfg is None:
        raise HTTPException(status_code=400, detail="SpotScoreConfig missing for this spot")

    shift, score = compute_shift(payload, cfg)
    db.add(shift)
    db.flush()

    score_result = ScoreResult(
        shift_id=shift.id,
        score_total=score.score_total,
        score_version=score.score_version,
        breakdown_json=score.breakdown,
    )
    db.add(score_result)
    db.commit()
    db.refresh(shift)

    return ShiftOut.from_orm_with_score(shift, score_result)


@router.get("", response_model=list[ShiftOut])
def list_shifts(
    bar_id: int = Query(...),
    limit: int = Query(25, ge=1, le=200),
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if bar_id != current.bar_id:
        raise HTTPException(status_code=403, detail="Not allowed")

    shifts = (
        db.query(Shift)
        .filter(Shift.bar_id == bar_id)
        .order_by(Shift.id.desc())
        .limit(limit)
        .all()
    )

    if current.role == UserRole.employee:
        # MVP mapping: shifts are keyed by bartender_name; later we will store bartender_user_id.
        shifts = [s for s in shifts if s.bartender_name == current.name]

    shift_ids = [s.id for s in shifts]
    scores = (
        db.query(ScoreResult)
        .filter(ScoreResult.shift_id.in_(shift_ids))
        .all()
        if shift_ids
        else []
    )
    score_by_shift_id = {s.shift_id: s for s in scores}

    return [ShiftOut.from_orm_with_score(s, score_by_shift_id.get(s.id)) for s in shifts]
