from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_owner
from app.db.session import get_db
from app.models.score_result import ScoreResult
from app.models.shift import Shift
from app.models.spot_score_config import SpotScoreConfig
from app.models.user import User, UserRole
from app.schemas.shifts import ShiftCreateIn, ShiftDeleteOut, ShiftOut, ShiftUpdateIn
from app.services.scoring import compute_shift


router = APIRouter(prefix="/shifts")


def _get_shift_or_404(db: Session, shift_id: int) -> Shift:
    shift = db.query(Shift).filter(Shift.id == shift_id).first()
    if shift is None:
        raise HTTPException(status_code=404, detail="Shift not found")
    return shift


def _ensure_can_view_shift(current: User, shift: Shift) -> None:
    if shift.bar_id != current.bar_id:
        raise HTTPException(status_code=403, detail="Not allowed")

    if current.role == UserRole.owner:
        return

    # MVP mapping: shifts are keyed by bartender_name; later we will store bartender_user_id.
    if shift.bartender_name != current.name:
        raise HTTPException(status_code=403, detail="Not allowed")


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


@router.get("/{shift_id}", response_model=ShiftOut)
def get_shift_detail(
    shift_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    shift = _get_shift_or_404(db, shift_id)
    _ensure_can_view_shift(current, shift)

    score = db.query(ScoreResult).filter(ScoreResult.shift_id == shift.id).first()
    return ShiftOut.from_orm_with_score(shift, score)


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


@router.patch("/{shift_id}", response_model=ShiftOut)
def update_shift(
    shift_id: int,
    payload: ShiftUpdateIn,
    owner: User = Depends(require_owner),
    db: Session = Depends(get_db),
):
    shift = _get_shift_or_404(db, shift_id)
    if shift.bar_id != owner.bar_id:
        raise HTTPException(status_code=403, detail="Not allowed")

    new_bar_id = shift.bar_id
    new_spot_id = payload.spot_id if payload.spot_id is not None else shift.spot_id
    new_bartender_name = payload.bartender_name if payload.bartender_name is not None else shift.bartender_name
    new_shift_date = payload.shift_date if payload.shift_date is not None else shift.shift_date
    new_personal_sales_volume = (
        payload.personal_sales_volume if payload.personal_sales_volume is not None else shift.personal_sales_volume
    )
    new_total_bar_sales = payload.total_bar_sales if payload.total_bar_sales is not None else shift.total_bar_sales
    new_personal_tips = payload.personal_tips if payload.personal_tips is not None else shift.personal_tips
    new_hours_worked = payload.hours_worked if payload.hours_worked is not None else shift.hours_worked
    new_transactions_count = (
        payload.transactions_count if payload.transactions_count is not None else shift.transactions_count
    )

    cfg = db.query(SpotScoreConfig).filter(SpotScoreConfig.spot_id == new_spot_id).first()
    if cfg is None:
        raise HTTPException(status_code=400, detail="SpotScoreConfig missing for this spot")

    computed_shift, score = compute_shift(
        ShiftCreateIn(
            bar_id=new_bar_id,
            spot_id=new_spot_id,
            bartender_name=new_bartender_name,
            shift_date=new_shift_date,
            personal_sales_volume=new_personal_sales_volume,
            total_bar_sales=new_total_bar_sales,
            personal_tips=new_personal_tips,
            hours_worked=new_hours_worked,
            transactions_count=new_transactions_count,
        ),
        cfg,
    )

    shift.spot_id = computed_shift.spot_id
    shift.bartender_name = computed_shift.bartender_name
    shift.shift_date = computed_shift.shift_date
    shift.personal_sales_volume = computed_shift.personal_sales_volume
    shift.total_bar_sales = computed_shift.total_bar_sales
    shift.personal_tips = computed_shift.personal_tips
    shift.hours_worked = computed_shift.hours_worked
    shift.transactions_count = computed_shift.transactions_count
    shift.pct_of_bar_sales = computed_shift.pct_of_bar_sales
    shift.tip_pct = computed_shift.tip_pct
    shift.sales_per_hour = computed_shift.sales_per_hour
    db.add(shift)

    score_result = db.query(ScoreResult).filter(ScoreResult.shift_id == shift.id).first()
    if score_result is None:
        score_result = ScoreResult(shift_id=shift.id, score_total=score.score_total, score_version=score.score_version, breakdown_json=score.breakdown)
    else:
        score_result.score_total = score.score_total
        score_result.score_version = score.score_version
        score_result.breakdown_json = score.breakdown
    db.add(score_result)

    db.commit()
    db.refresh(shift)
    return ShiftOut.from_orm_with_score(shift, score_result)


@router.delete("/{shift_id}", response_model=ShiftDeleteOut)
def delete_shift(
    shift_id: int,
    owner: User = Depends(require_owner),
    db: Session = Depends(get_db),
):
    shift = _get_shift_or_404(db, shift_id)
    if shift.bar_id != owner.bar_id:
        raise HTTPException(status_code=403, detail="Not allowed")

    score_result = db.query(ScoreResult).filter(ScoreResult.shift_id == shift.id).first()
    if score_result is not None:
        db.delete(score_result)

    db.delete(shift)
    db.commit()

    return ShiftDeleteOut(deleted=True)
