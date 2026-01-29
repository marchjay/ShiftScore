from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_owner
from app.db.session import get_db
from app.models.bar import Bar
from app.models.user import User
from app.schemas.bars import BarCreateIn, BarOut, BarUpdateIn


router = APIRouter(prefix="/bars")


@router.get("", response_model=list[BarOut])
def list_bars(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    bars = db.query(Bar).filter(Bar.id == current.bar_id).order_by(Bar.id.asc()).all()
    return [BarOut.model_validate(b) for b in bars]


@router.post("", response_model=BarOut)
def create_bar(payload: BarCreateIn, owner: User = Depends(require_owner)):
    # In this MVP, bars are created via /api/auth/bootstrap.
    # Keeping this endpoint owner-only but disabled avoids accidental multi-bar creation.
    raise HTTPException(status_code=400, detail="Create bars via /api/auth/bootstrap")


@router.patch("/{bar_id}", response_model=BarOut)
def update_bar(bar_id: int, payload: BarUpdateIn, owner: User = Depends(require_owner), db: Session = Depends(get_db)):
    bar = db.query(Bar).filter(Bar.id == bar_id).first()
    if bar is None:
        raise HTTPException(status_code=404, detail="Bar not found")

    if bar.id != owner.bar_id:
        raise HTTPException(status_code=403, detail="Not allowed")

    if payload.name is not None:
        bar.name = payload.name
    if payload.timezone is not None:
        bar.timezone = payload.timezone

    db.commit()
    db.refresh(bar)
    return BarOut.model_validate(bar)
